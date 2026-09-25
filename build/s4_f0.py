# -*- coding: utf-8 -*-
"""build/s4_f0.py — EGFF F0(사전등록 PREREG-2026-09-25-EGFF §8) → data/_s4_f0.json · 수익 없음 · 겹침 통계 없음

F0 는 1단계(겹침) 전에 커밋한다. 문턱 셋이 모두 넘어야 build/s4_overlap.py 가 돈다.
  (i)   Eg 입력 (CIK · 태그 · 기간) 칸의 ≥ 0.98 이 companyfacts 원본의 제출 기록(accn · filed)에 맞는다 — 못 맞는 칸 목록을 싣는다.
        칸 = 최신판(data/fx · fx_pit) 파일에서 eg_q5 가 읽는 칸(Firm: asset · debt · eq 의 i(없으면 q) · ni q · ni a · cfo a /
        load_fund: sh 의 i·q(비면 a) · sh 가 시작하기 전의 sho). 맞음 = 주 CIK · 최신판 태그의 원장 기록 가운데 값이 같은 것이 있다.
  (ii)  sh 분할 되맞춤: 재작성이 아닌 칸에서 |log ME_V − log ME_LF| ≤ 0.01 인 칸이 ≥ 99%.
        칸 = (종목, 월말 2009-01 ~ 2026-07) 에서 두 경로(P-V · 최신판)가 같은 기간말 · 같은 필드(sh · 앞 잇기 sho) · 최신판 태그의
        SEC 관측을 고른 것(야후 메움 · 형제 태그 제외). 같은 월말 · 같은 가격이라 ME 비 = 주식수 비다.
        재작성이 아님 = 그 칸 기록 값(단위 사고 정리 뒤)이 서로 같거나 알려진 실제 분할비의 곱(연속 구간)만큼만 다르다(±0.5%) —
        되맞춤 규칙(filed 기준)을 쓰지 않고 가른다(순환 없음).
  (iii) 재현 단언: 이 실행이 뿌리에서 **직접 다시 구운** 공급자 latest 점수의 sha256 = 얼린 _eg_q5_scores_pitgics.json(P1 판)의 sha256
        = 배치 Q 의 값(s4_overlap.BATCHQ_REF). 같은 실행이 v · ff · vs 도 다시 굽고 뿌리 · 저장소의 점수 파일과 바이트로 맞춘다
        (미리 구운 파일을 믿지 않는다 · 2026-09-26 적대 검토).
뿌리 고정: 뿌리의 build · data 나무 해시(s4_overlap.tree_digest)를 굽기 앞뒤로 재 같음을 보이고 F0 에 적는다 — 1단계 관문 ④ 가 같은 해시를
  요구한다. snap_wt(배치 Q 의 P1 판)의 모든 파일이 뿌리에 바이트로 같은지도 적는다(snap_wt 는 읽기만 한다).
보고만(문턱 없음): 태그 규칙(형제 메움 v 대 엄격 vs)별 «빈티지 ≠ 최신» 칸 수 · 첫 가용일 > 기간말 + 90일 칸 수와 그 지연 구간(≤200 · 201~300 ·
  >300일)과 >300일 무리의 갈래 · 형제 태그 메움의 크기 · Q4 3개월 사실 가용률 · 기울기 회귀 표본의 2026 전 떠난 이름 · QFWD V0 입력 경로 대조(§7) ·
  공급자별 편입 후보 수(점수가 선 이름 수 — 점수 값은 보지 않는다) · P-V sh 최신 관측이 앞 기간말로 물러난 월말 수.
🚨 점수끼리 비교하지 않는다(겹침 · 스피어만은 1단계 — F0 커밋 뒤 s4_overlap.py). 점수 파일은 sha256 · 이름 수만 싣는다. 수익은 계산하지 않는다.

  python build/s4_f0.py --root <P1 뿌리> [--ref <얼린 점수 파일>] [--snap <snap_wt>] [--out data/_s4_f0.json]
     뿌리 = snap_wt 의 복사본 + build/eg_q5_vintage.py · data/_fxv(저장소와 바이트 동일) · 굽은 점수(_v · _ff · _vs). 저장소 = 이 스크립트의 저장소.
"""
from __future__ import annotations
import bisect, datetime as dt, gzip, hashlib, io, json, math, os, shutil, subprocess, sys, tarfile, tempfile, time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import s4_overlap as S4                                         # noqa: E402  tree_digest · BATCHQ_REF · BASIS · TWINS (뿌리 경로를 넣기 전에)

PREREG = "build/PREREG-2026-09-25-EGFF.md"
P1_BASE = "bef4eea8c98572bd05815d44bd0744d9ce7ed370"          # 배치 Q 의 가격 밖 판(fx · fx_pit)
TH_MATCH, TH_ME, ME_TOL, SPLIT_TOL = 0.98, 0.99, 0.01, math.log(1.005)
M0, M1 = "2009-01", "2026-07"                                  # eg_q5 의 state 가 쓰이는 월말 범위(회귀 2010-01 의 t−12 ~ 형성 끝)
QFWD_EX = {"m": "2026-08", "commit": "41a173034d42b13738dfedf56d6ae4941862749e", "past_ym": "2019-12"}
SUPPLIERS = ("latest", "v", "ff", "vs")
BAKE_ENV = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "PYTHONIOENCODING": "utf-8"}
GT10 = math.log(1.10)
LATE_BUCKETS = ((200, "le200"), (300, "d201_300"), (None, "gt300"))


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def rj(p):
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def git(args, repo):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True, check=True).stdout


def pe_plus(pe, days=90):
    return (dt.date.fromisoformat(pe) + dt.timedelta(days=days)).isoformat()


def days_between(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def clean(a):
    return [x for x in (a or []) if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float))]


def pct(xs, q):
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else None


def lf_fields(tg):
    """eg_q5 / load_fund 이 읽는 (필드, 키, 버킷, [(기간말, 값)], 위 끝) — 최신판 파일 한 개.
    위 끝 = 그 필드를 읽는 기간말의 상한(sho 는 sh 의 첫 기간말 — load_fund 이 그 앞만 잇는다 · 나머지는 None)."""
    out = []
    for k in ("asset", "debt", "eq"):
        v = tg.get(k) or {}
        b = "i" if v.get("i") else ("q" if v.get("q") else None)
        if b:
            out.append((k, k, b, clean(v.get(b)), None))
    for k, b in (("ni", "q"), ("ni", "a"), ("cfo", "a")):
        v = tg.get(k) or {}
        if v.get(b):
            out.append((k + "_" + b, k, b, clean(v.get(b)), None))
    v = tg.get("sh") or {}
    b = "i" if v.get("i") else ("q" if v.get("q") else None)
    prim = clean(v.get(b)) if b else []
    if not prim:
        b = "a" if v.get("a") else None
        prim = clean(v.get("a")) if b else []
    if b:
        out.append(("sh", "sh", b, prim, None))
    v = tg.get("sho") or {}
    b2 = "i" if v.get("i") else ("q" if v.get("q") else None)
    first = min(d for d, _v in prim) if prim else None
    if b2:
        sho = clean(v.get(b2))
        if prim:
            sho = [x for x in sho if x[0] < first]
        out.append(("sho", "sho", b2, sho, first))
    return out


def split_set(spl):
    """알려진 실제 분할비(연속 구간의 곱)와 역수 — 재작성 판정용."""
    qs = [x["q"] for x in sorted(spl, key=lambda x: x["s"]) if x.get("q") not in (None, 1.0)]
    s = {1.0}
    for i in range(len(qs)):
        p = 1.0
        for j in range(i, len(qs)):
            p *= qs[j]
            s.add(p)
            s.add(1.0 / p)
    return sorted(s)


def ratio_class(vals, sset):
    """기록 값들 → 'same' | 'split' | 'restated'."""
    base = vals[0]
    if all(v == base for v in vals):
        return "same"
    if not base or any(not v for v in vals):
        return "restated"
    for v in vals[1:]:
        r = v / base
        if r <= 0 or min(abs(math.log(r / s)) for s in sset) > SPLIT_TOL:
            return "restated"
    return "split"


def far(a, b):
    """두 값이 10% 넘게 다른가(부호가 다르거나 한쪽이 0 이면 참)."""
    if a == b:
        return False
    if not a or not b or (a > 0) != (b > 0):
        return True
    return abs(math.log(a / b)) > GT10


def tree_files(base, skip_top=(".git",)):
    """base 아래 모든 파일(__pycache__ · 맨 위 .git 제외) → {상대경로: sha256}."""
    out = {}
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d != "__pycache__" and not (dp == base and d in skip_top)]
        for fn in fns:
            if dp == base and fn in skip_top:
                continue
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, base).replace(os.sep, "/")] = sha_file(p)
    return out


def bake(root, s, tmpd):
    """뿌리의 eg_q5_vintage.py 로 공급자 s 를 임시 경로에 굽는다(뿌리 · 저장소에는 쓰지 않는다) → (점수 경로, 진단 경로, 초)."""
    out, dg = os.path.join(tmpd, "scores_%s.json" % s), os.path.join(tmpd, "diag_%s.json" % s)
    argv = [sys.executable, "-X", "utf8", os.path.join(root, "build", "eg_q5_vintage.py"), "--pit-gics", "--supplier", s,
            "--out", out, "--diag", dg]
    t = time.time()
    r = subprocess.run(argv, cwd=root, env=dict(os.environ, **BAKE_ENV), capture_output=True)
    if r.returncode != 0:
        raise SystemExit("🚨 굽기 실패(%s): %s" % (s, r.stderr.decode("utf-8", "replace")[-2000:]))
    return out, dg, round(time.time() - t, 1)


def main() -> int:
    t0 = time.time()
    if "--repo" in sys.argv:
        raise SystemExit("🚨 --repo 는 없다 — F0 는 이 스크립트의 랩 저장소에 쓴다")
    if not arg("--root"):
        raise SystemExit(__doc__)
    root = os.path.abspath(arg("--root"))
    repo = REPO
    snap = os.path.abspath(arg("--snap", os.path.join(tempfile.gettempdir(), "snap_wt")))
    ref = os.path.abspath(arg("--ref", os.path.join(snap, "data", "_eg_q5_scores_pitgics.json")))
    out_p = arg("--out", os.path.join(repo, "data", "_s4_f0.json"))
    # 뿌리의 복사본이 저장소와 같은가(돌린 코드 = 커밋할 코드)
    for rel in ("build/eg_q5_vintage.py", "data/_fxv/index.json", "data/_fxv/manifest.json"):
        a, b = os.path.join(root, *rel.split("/")), os.path.join(repo, *rel.split("/"))
        if sha_file(a) != sha_file(b):
            raise SystemExit("🚨 뿌리의 %s 가 저장소와 다르다" % rel)

    # ── 뿌리 고정: 나무 해시(앞) · snap_wt 대조 ─────────────────────────────
    tree_before = S4.tree_digest(root)
    sf, rf_ = tree_files(snap), tree_files(root)
    s_diff = sorted(p for p in sf if p in rf_ and rf_[p] != sf[p])
    s_miss = sorted(p for p in sf if p not in rf_)
    r_only = sorted(p for p in rf_ if p not in sf)
    r_only_sum = {"data/_fxv/g*.json.gz": sum(1 for p in r_only if p.startswith("data/_fxv/g") and p.endswith(".json.gz"))}
    r_only_sum["other"] = [p for p in r_only if not (p.startswith("data/_fxv/g") and p.endswith(".json.gz"))]
    try:
        snap_head = subprocess.run(["git", "-C", snap, "rev-parse", "HEAD"], capture_output=True).stdout.decode().strip() or None
    except Exception:
        snap_head = None
    if s_diff or s_miss:
        raise SystemExit("🚨 뿌리가 snap_wt 와 다르다 — 다름 %s · 없음 %s" % (s_diff[:5], s_miss[:5]))
    print("뿌리: 나무 %s… (%d파일) · snap_wt %d파일 모두 바이트 동일 · 뿌리에만 %d" % (tree_before[0][:16], tree_before[1], len(sf), len(r_only)))

    # ── (iii) 재현 단언 — 이 실행이 다시 굽는다(무거운 적재 전에 · 한 번에 하나) ─────
    tmpd = tempfile.mkdtemp(prefix="egff_f0bake_")
    try:
        baked = {}
        for s in SUPPLIERS:
            baked[s] = bake(root, s, tmpd)
            print("  굽기 %s · %.0f초 · %s…" % (s, baked[s][2], sha_file(baked[s][0])[:16]), flush=True)
        bsha = {s: sha_file(baked[s][0]) for s in SUPPLIERS}
        diags = {s: rj(baked[s][1]) for s in SUPPLIERS}
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    tree_after = S4.tree_digest(root)
    if tree_after != tree_before:
        raise SystemExit("🚨 굽기가 뿌리를 바꿨다(나무 해시 앞뒤 다름)")
    ref_sha = sha_file(ref)
    root_sc = {s: os.path.join(root, "data", "_eg_q5_scores_pitgics_%s.json" % s) for s in SUPPLIERS}
    repo_sc = {s: os.path.join(repo, "data", "_eg_q5_scores_pitgics_%s.json" % s) for s in SUPPLIERS if s != "latest"}
    root_eq = {s: (os.path.exists(root_sc[s]) and sha_file(root_sc[s]) == bsha[s]) for s in SUPPLIERS if os.path.exists(root_sc[s]) or s != "latest"}
    repo_eq = {s: (os.path.exists(p) and sha_file(p) == bsha[s]) for s, p in repo_sc.items()}
    if not all(root_eq.values()) or not all(repo_eq.values()):
        raise SystemExit("🚨 다시 구운 점수가 뿌리 · 저장소 파일과 다르다 — 뿌리 %s · 저장소 %s" % (root_eq, repo_eq))
    for s in SUPPLIERS:
        if diags[s]["scores_sha256"] != bsha[s]:
            raise SystemExit("🚨 진단 %s 의 점수 해시가 구운 파일과 다르다" % s)
        if s != "latest" and diags[s]["ledger_index_sha256"] != sha_file(os.path.join(root, "data", "_fxv", "index.json")):
            raise SystemExit("🚨 진단 %s 가 다른 원장으로 구워졌다" % s)
    F0_iii = {"rule": "이 실행이 뿌리에서 다시 구운 공급자 latest 점수 sha256 = 얼린 _eg_q5_scores_pitgics.json(P1 판 · 배치 Q 가 쓴 파일) sha256 "
                      "= 배치 Q 의 값(s4_overlap.BATCHQ_REF)",
              "ref_path_hint": "$TEMP/snap_wt/data/_eg_q5_scores_pitgics.json" if os.path.normcase(ref).startswith(os.path.normcase(snap)) else os.path.basename(ref),
              "ref_sha256": ref_sha, "batchq_pin": S4.BATCHQ_REF, "latest_sha256": bsha["latest"],
              "pass": ref_sha == bsha["latest"] == S4.BATCHQ_REF,
              "scores_sha256": {s: bsha[s] for s in ("v", "ff", "vs")},
              "rebaked_in_this_run": True, "bake_sec": {s: baked[s][2] for s in SUPPLIERS},
              "root_files_equal": root_eq, "repo_files_equal": repo_eq,
              "code": {"build/eg_q5_vintage.py": sha_file(os.path.join(repo, "build", "eg_q5_vintage.py")),
                       "build/eg_q5.py(P1 뿌리)": sha_file(os.path.join(root, "build", "eg_q5.py"))},
              "env": BAKE_ENV}
    print("F0 (iii) 재현 %s (다시 구운 latest %s… · ref %s… · 배치 Q %s…)" % ("통과" if F0_iii["pass"] else "실패", bsha["latest"][:16],
                                                                   ref_sha[:16], S4.BATCHQ_REF[:16]))

    sys.path.insert(0, os.path.join(root, "build"))
    import tech_backtest as TB            # noqa: E402  (뿌리의 얼린 판)
    import eg_q5_vintage as EV            # noqa: E402
    DATA = os.path.join(root, "data")
    IX = rj(os.path.join(DATA, "_fxv", "index.json"))
    CANDS = IX["candidates"]
    for g, v in IX["groups"].items():
        p = os.path.join(DATA, "_fxv", v["file"])
        if sha_file(p) != v["sha256"] or sha_file(os.path.join(repo, "data", "_fxv", v["file"])) != v["sha256"]:
            raise SystemExit("🚨 원장 파일 해시 불일치 — %s" % v["file"])
    LED = {g: rj(os.path.join(DATA, "_fxv", v["file"])) for g, v in IX["groups"].items()}
    MAN = rj(os.path.join(repo, "data", "_fxv", "manifest.json"))
    GFILED, GANN = {}, {}                          # 그룹 → 원장 기록의 filed 전부(정렬) · ni 연간 기간말 집합
    for g, L in LED.items():
        fs, an = set(), set()
        for key, rec in (L.get("keys") or {}).items():
            for b in ("q", "a", "i"):
                for pe, rows in (rec.get(b) or {}).items():
                    fs.update(r[4] for r in rows)
                    if b == "a" and key.startswith("ni:"):
                        an.add(pe)
        GFILED[g], GANN[g] = sorted(fs), an

    # 최신판 수집 시각(=그 판이 본 제출의 끝) — git 기록에서
    def commit_date(path):
        s = git(["log", "-1", "--format=%cI", P1_BASE, "--", path], repo).decode().strip()
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc).date().isoformat(), s
    cut = {"fx": commit_date("data/fx"), "fx_pit": commit_date("data/fx_pit")}

    # ── 칸 목록 ─────────────────────────────────────────────────────────
    FX = {}
    for sub in ("fx", "fx_pit"):
        dd = os.path.join(DATA, sub)
        for fn in sorted(os.listdir(dd)):
            if fn.endswith(".json") and fn[:-5] not in FX:
                FX[fn[:-5]] = (sub, rj(os.path.join(dd, fn)))
    cells = []           # (tk, sub, cik, field, key, tag, b, pe, v_lf, subs(원값 · 태그 순), 주 CIK·최신판 태그 기록, gid)
    for tk, (sub, j) in FX.items():
        tg = j.get("tags") or {}
        tx = "ifrs-full" if j.get("std") == "IFRS" else "us-gaap"
        ti = IX["tickers"].get(tk)
        L = LED[ti["gid"]] if ti else {"keys": {}, "primary": None}
        for field, k, b, ser, _hi in lf_fields(tg):
            src = (tg.get(k) or {}).get("src")
            recs = ((L["keys"].get("%s:%s:%s" % (k, tx, src)) or {}).get(b)) or {}
            for pe, v in ser:
                rows = recs.get(pe) or []
                rp = [r for r in rows if len(r) < 6 or r[5] == L["primary"]]
                cells.append((tk, sub, int(j["cik"]), field, k, src, b, pe, v, EV.ledger_subs(L, CANDS, k, tx, src, b, pe), rp,
                              ti["gid"] if ti else None))

    # ── (i) 제출 기록 맞춤 ─────────────────────────────────────────────
    n_i = len(cells)
    miss, n_any, n_latest, no_rec = [], 0, 0, 0
    by_field = {}
    for tk, sub, cik, field, k, src, b, pe, v, subs, rp, _g in cells:
        ok = any(r[1] == v for r in rp)
        lat = [r for r in rp if r[4] <= cut[sub][0]]
        n_any += ok
        n_latest += bool(lat) and lat[-1][1] == v
        no_rec += not rp
        f = by_field.setdefault("%s:%s" % (field, b), [0, 0])
        f[0] += 1
        f[1] += ok
        if not ok:
            miss.append({"t": tk, "cik": cik, "key": k, "tag": src, "b": b, "pe": pe, "lf": v,
                         "ledger": [[r[1], r[2], r[4]] for r in rp][:6], "why": "기록 없음" if not rp else "값 다름"})
    share_i = n_any / max(1, n_i)
    F0_i = {"rule": "칸의 주 CIK · 최신판 태그 원장 기록 가운데 값이 최신판과 같은 것이 있다(accn · filed 가 붙은 제출 기록)",
            "cells": n_i, "matched": n_any, "share": share_i, "threshold": TH_MATCH, "pass": share_i >= TH_MATCH,
            "matched_latest_at_fetch": n_latest,
            "latest_rule": "최신판 수집일(fx %s · fx_pit %s, 커밋 UTC 날짜) 이전 filed 중 마지막 기록의 값이 같다" % (cut["fx"][0], cut["fx_pit"][0]),
            "cells_without_record": no_rec, "by_field": {k: {"n": a, "matched": m} for k, (a, m) in sorted(by_field.items())},
            "misses": sorted(miss, key=lambda x: (x["t"], x["key"], x["b"], x["pe"]))}
    print("F0 (i) 칸 %d · 맞음 %d (%.4f) · 수집일 기준 최신과 같음 %d · 기록 없음 %d" % (n_i, n_any, share_i, n_latest, no_rec))

    # ── (ii) sh 분할 되맞춤 · ME ─────────────────────────────────────────
    S = rj(os.path.join(DATA, "stocks.json"))
    dates = S["pxd_dates"]
    mends = {}
    for d in dates:
        mends[d[:7]] = d
    tds = [mends[m] for m in sorted(mends) if M0 <= m <= M1]
    FUND = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])
    SUP = EV.Supplier("v", {}, FUND, data_dir=DATA)
    lf_fld = {}                                   # (종목, 기간말) → 최신판 계열에서 그 관측이 온 필드(sh · 앞 잇기 sho)
    for tk, sub, cik, field, k, src, b, pe, v, subs, rp, _g in cells:
        if field in ("sh", "sho"):
            lf_fld[(tk, pe)] = field
    subsmap = {(c, fld, pe): subs for c, fl in SUP.C.items() for fld in ("sh", "sho") for pe, subs in (fl.get(fld) or (None, []))[1]}
    cnt = {"both": 0, "same_pe": 0, "comparable": 0, "nonrestated": 0, "nonrestated_same": 0, "nonrestated_split": 0,
           "restated": 0, "ok": 0, "ok_same": 0, "ok_split": 0, "yahoo_or_other": 0, "field_mismatch": 0, "sibling_tag": 0, "diff_pe": 0}
    fails = []
    memo = {}
    back = {}                                     # 종목 → [물러난 월말 수, 그중 sh ↔ sho 필드가 바뀐 것, 첫 월말, 끝 월말]
    nr_cells = set()                              # 재작성 아닌 비교 칸(종목 · 기간말) — 칸 단위 몫(참고)
    for c in sorted(SUP.C):
        if c not in FUND or not FUND[c].get("sh"):
            continue
        sset = split_set(TB.SPLIT_KIND.get(c) or [])
        prev = None
        for td in tds:
            lf = TB.asof_all(FUND[c]["sh"], td)
            ep = bisect.bisect_right(SUP.EPOCH.get(c, []), td)
            if (c, ep) not in memo:
                memo[(c, ep)] = SUP.build_sh(c, td, parts=True)
            vs, info = memo[(c, ep)]
            vv = TB.asof_all(vs, td)
            if vv:                                # P-V 의 최신 관측이 앞 기간말로 물러났나(sh · sho 이음매를 날짜마다 다시 짓는 산물 포함)
                dv0 = vv[0][0]
                fld0 = (info.get(dv0) or (None, None, None, "yahoo", None))[3]
                if prev is not None and dv0 < prev[0]:
                    a = back.setdefault(c, [0, 0, td, td])
                    a[0] += 1
                    a[1] += fld0 != prev[1]
                    a[3] = td
                prev = (dv0, fld0)
            if not lf or not vv:
                continue
            cnt["both"] += 1
            (dl, xl), (dv, xv) = lf[0], vv[0]
            if dl != dv:
                cnt["diff_pe"] += 1
                continue
            cnt["same_pe"] += 1
            if (c, dl) not in lf_fld or dl not in info:
                cnt["yahoo_or_other"] += 1
                continue
            _v, fv, facv, fldv, tiv = info[dl]
            if lf_fld[(c, dl)] != fldv:
                cnt["field_mismatch"] += 1
                continue
            if tiv != 0:
                cnt["sibling_tag"] += 1
                continue
            cnt["comparable"] += 1
            recs = next(vs_ for _a, vs_, _f, t_ in subsmap[(c, fldv, dl)] if t_ == 0)
            cls = ratio_class(recs, sset)
            if cls == "restated":
                cnt["restated"] += 1
                continue
            cnt["nonrestated"] += 1
            cnt["nonrestated_" + cls] += 1
            nr_cells.add((c, dl))
            lr = abs(math.log(xv / xl)) if (xv and xl and xv > 0 and xl > 0) else float("inf")
            if lr <= ME_TOL:
                cnt["ok"] += 1
                cnt["ok_" + cls] += 1
            else:
                fails.append({"t": c, "td": td, "pe": dl, "sh_v": round(xv, 4), "sh_lf": round(xl, 4),
                              "log_ratio": round(math.log(xv / xl), 4) if (xv and xl and xv > 0 and xl > 0) else None,
                              "raw_v": _v, "filed_v": fv, "fac_v": round(facv, 6), "field": fldv, "class": cls, "records": recs,
                              "splits": [[x["s"], x["r"], x["kind"], x["q"]] for x in (TB.SPLIT_KIND.get(c) or [])]})
    share_ii = cnt["ok"] / max(1, cnt["nonrestated"])
    agg = {}                                      # 실패를 종목 · 기간말로 묶는다(같은 칸이 여러 월말에 되풀이된다)
    for f in fails:
        a = agg.setdefault((f["t"], f["pe"]), dict(f, n_months=0, td_first=f["td"]))
        a["n_months"] += 1
        a["td_last"] = f["td"]
    for a in agg.values():
        a.pop("td", None)
    fail_tk = sorted({a["t"] for a in agg.values()})
    F0_ii = {"rule": "|log ME_V − log ME_LF| ≤ %.2f · 칸 = 같은 월말에 두 경로가 같은 기간말 · 같은 필드(sh 또는 앞 잇기 sho) · 최신판 태그의 SEC 관측을 "
                     "고른 것 · 재작성 아님 = 그 칸 기록 값(단위 사고 정리 뒤)이 같거나 알려진 실제 분할비(연속 곱 · ±0.5%%)만큼만 다름" % ME_TOL,
             "unit_clean": {k: SUP.stat.get(k) for k in ("sh_unit_rescaled", "sh_unit_dropped", "sh_cells_dropped")},
             "months": [tds[0], tds[-1]], "counts": cnt, "share": share_ii, "threshold": TH_ME, "pass": share_ii >= TH_ME,
             "n_fail_cells": len(agg), "n_fail_tickers": len(fail_tk), "fail_tickers": fail_tk,
             "distinct_cells": {"note": "월말을 빼고 (종목 · 기간말) 칸으로 센 몫(참고 · 문턱은 위 월말 단위 share) — 칸은 그 칸의 모든 월말이 1% 안이면 맞음",
                                "n": len(nr_cells), "fail": len(agg),
                                "share": (len(nr_cells) - len(agg)) / max(1, len(nr_cells))},
             "fail_reading": ("남은 못 맞는 칸은 최신판(tech_backtest._rebase 의 매끄러움 추정)과 P-V(filed 기준 분할)가 분할 기준을 달리 본 자리다 — "
                              "이 빌드의 읽기(적대 검토가 DUK · WTW · TMUS 는 같게 읽었다): "
                              "DUK 2012-03 · 06(1:3 역분할과 Progress 합병이 한 분기 — 최신판이 이미 역분할 뒤인 446 에 1/3 을 한 번 더 곱했다) · "
                              "WTW 2015(2016-01 Willis 역분할 0.3775 — 최신판이 이미 되맞춰 다시 실린 69.0 에 한 번 더 곱했다) · "
                              "TMUS 2009~2011(MetroPCS 시절 주식수 — 최신판이 2013-05 1:2 역분할을 곱하지 않았다) — 이 셋은 P-V 쪽이 가격 기준과 맞는다. "
                              "HPE 2015~2016 은 **두 경로 모두 일관되지 않다**: split_kinds 가 2017-04-03 DXC 분사(1.3348 · 4/3 에 가깝다)를 «실제 분할» 로 "
                              "갈랐다(2017-09-01 Micro Focus 1.289 는 «분사형» 이라 두 경로 모두 곱한다). 가격 계열은 04-03 에 매끄러워(03-31 10.48 → 04-03 10.37 · "
                              "분사 조정됨) 사건 전 주식수는 모두 ×1.3348 이 더 필요하다. P-V 는 분할 기준일(같은 값을 실은 가장 늦은 filed)이 그 전인 기록"
                              "(뒤에 다시 실리지 않은 이 넷)에만 곱하고 그 뒤 같은 값으로 다시 실린 기록에는 곱하지 않아 한 계열 안에서 섞이며, 최신판은 이 칸들에 "
                              "1.3348 을 곱하지 않는다 — 못 맞는 이 넷은 P-V 쪽 배수(1.7206 = 1.3348 × 1.289)가 가격 기준과 맞고, 나머지 HPE 칸은 두 경로가 "
                              "같이 틀린다. 고치지 않고 선언만 한다(declared 참조)."),
             "fail_cells": sorted(agg.values(), key=lambda x: (-abs(x["log_ratio"] or 99), x["t"], x["pe"])),
             "v_latest_obs_moved_back": {
                 "rule": "종목마다 월말 순서로 P-V sh 계열의 최신 관측 기간말이 앞 월말보다 이른 기간말로 물러난 월말 수 · 그중 sh ↔ sho(또는 야후) 필드가 "
                         "바뀐 것(load_fund 의 «sh 가 시작하기 전만 sho» 를 날짜마다 다시 적용한 산물 — 실측 GOOGL 2023-09 ~ 2024-08) · 보고만",
                 "cell_months": sum(a[0] for a in back.values()), "field_switch": sum(a[1] for a in back.values()),
                 "tickers": len(back),
                 "top": [[t, a[0], a[1], a[2], a[3]] for t, a in sorted(back.items(), key=lambda kv: (-kv[1][0], kv[0]))[:25]]}}
    print("F0 (ii) 재작성 아닌 칸 %d · 1%% 안 %d (%.4f) · 못 맞는 칸 %d(%s) · 셈 %s"
          % (cnt["nonrestated"], cnt["ok"], share_ii, len(agg), fail_tk, cnt))
    del memo, SUP

    # ── 보고 1 · 2: 태그 규칙별 «빈티지 ≠ 최신» · 첫 가용일 > 기간말 + 90일(지연 구간 · 갈래) ─────
    def late_bucket(days):
        for hi, nm in LATE_BUCKETS:
            if hi is None or days <= hi:
                return nm

    rules = ("v", "vs")
    r1 = {r: {} for r in rules}
    r2 = {r: {} for r in rules}
    delays = {r: [] for r in rules}
    gt300 = {r: {"q4_3m_ni": 0, "periodic_filing_within_200d": 0, "no_filing_within_200d": 0} for r in rules}
    gt300_ex = {r: [] for r in rules}
    tagq = {"sibling_first_cells": 0, "sibling_first_far": 0, "by_key": {}, "examples": [], "vs_later_days": [],
            "late_only_under_vs": 0, "vs_no_lf_record": 0}
    for tk, sub, cik, field, k, src, b, pe, v, subs, rp, gid in cells:
        if not subs:
            continue
        key = "%s:%s:%s" % (field, src, b)
        y = pe[:4]
        pe90 = pe_plus(pe)
        firsts = {}
        for r in rules:
            sr = subs if r == "v" else [s_ for s_ in subs if s_[3] == 0]
            if not sr:
                tagq["vs_no_lf_record"] += 1
                continue
            first_av = min(s_[0][0] for s_ in sr)
            fv = EV.vintage_pick(sr, first_av, "v")          # 그 규칙이 그 칸을 처음 쓸 때의 값
            firsts[r] = (first_av, fv)
            lfs = next((s_ for s_ in sr if s_[3] == 0), None)
            a = r1[r].setdefault(key, {}).setdefault(y, [0, 0, 0, 0, 0])
            a[0] += 1
            a[1] += fv[0] != v                                  # 처음 가용한 값 ≠ 최신판
            a[2] += bool(lfs) and any(x != v for x in lfs[1])  # 최신판 태그의 어느 제출이든 최신판과 다른 값
            if field in ("sh", "sho") and fv[0] != v and fv[2] == 0:
                a[3] += ratio_class([fv[0], v], split_set(TB.SPLIT_KIND.get(tk) or [])) == "split"
            a[4] += fv[2] != 0                                  # 처음 가용한 값이 형제 태그에서 왔다(태그 갈아타기)
            e = r2[r].setdefault(key, {}).setdefault(y, [0, 0, 0, 0, 0])
            e[0] += 1
            if first_av > pe90:
                dd_ = days_between(pe, fv[1])
                e[1] += 1
                nm = late_bucket(dd_)
                e[{"le200": 2, "d201_300": 3, "gt300": 4}[nm]] += 1
                delays[r].append(dd_)
                if nm == "gt300":
                    fl = GFILED.get(gid) or []
                    lo_, hi_ = bisect.bisect_right(fl, pe), bisect.bisect_right(fl, pe_plus(pe, 200))
                    if field == "ni_q" and pe in (GANN.get(gid) or ()):
                        why = "q4_3m_ni"
                    elif hi_ > lo_:
                        why = "periodic_filing_within_200d"
                    else:
                        why = "no_filing_within_200d"
                    gt300[r][why] += 1
                    if len(gt300_ex[r]) < 400:
                        gt300_ex[r].append([tk, field, b, pe, fv[1], dd_, why])
        if "v" in firsts and "vs" in firsts:
            (fa_v, fv_v), (fa_s, _fv_s) = firsts["v"], firsts["vs"]
            if fv_v[2] != 0:                                    # P-V 가 형제 태그 값으로 시작한 칸(= P-VS 에서는 더 늦게 가용)
                tagq["sibling_first_cells"] += 1
                kk = tagq["by_key"].setdefault("%s:%s" % (field, b), [0, 0])
                kk[0] += 1
                if far(fv_v[0], v):
                    tagq["sibling_first_far"] += 1
                    kk[1] += 1
                    sib = [t for t in ([src] + [t for t in ((CANDS.get(k) or {}).get("ifrs-full" if tk and FX[tk][1].get("std") == "IFRS" else "us-gaap") or []) if t != src])]
                    tagq["examples"].append([tk, field, b, pe, v, fv_v[0], sib[fv_v[2]] if fv_v[2] < len(sib) else None, fv_v[1],
                                             None if (not v or not fv_v[0] or (v > 0) != (fv_v[0] > 0)) else round(abs(math.log(fv_v[0] / v)), 3)])
            if fa_s > fa_v:
                tagq["vs_later_days"].append(days_between(fa_v, fa_s))
            if fa_s > pe90 and not (fa_v > pe90):
                tagq["late_only_under_vs"] += 1
    for r in rules:
        delays[r].sort()
    tagq["vs_later_days"].sort()
    tagq["examples"].sort(key=lambda x: (x[8] is not None, -(x[8] or 0), x[0], x[3]))

    def r2doc(r):
        tot = [sum(x[i] for v in r2[r].values() for x in v.values()) for i in range(5)]
        dl = delays[r]
        return {"total": {"n": tot[0], "late": tot[1], "le200": tot[2], "d201_300": tot[3], "gt300": tot[4]},
                "by_key_year": {k: dict(sorted(v.items())) for k, v in sorted(r2[r].items())},
                "first_filed_minus_pe_days": {"n": len(dl), "p50": pct(dl, 0.5), "p90": pct(dl, 0.9), "max": dl[-1] if dl else None},
                "gt300_breakdown": gt300[r], "gt300_examples_head": gt300_ex[r][:40]}
    R1 = {"rule": "태그 규칙마다(v = 형제 태그 메움 · 결정 기준 / vs = 최신판 태그만 · 보고만) 칸마다 [n, 그 규칙이 처음 쓰는 값 ≠ 최신판, "
                  "최신판 태그의 어느 제출이든 ≠ 최신판, (sh·sho) 첫 값 ≠ 중 분할비만큼만 다른 것, 첫 값이 형제 태그에서 옴] · 연도 = 기간말 연도",
          **{r: {"by_key_year": {k: dict(sorted(v.items())) for k, v in sorted(r1[r].items())},
                 "total": [sum(x[i] for v in r1[r].values() for x in v.values()) for i in range(5)]} for r in rules}}
    R2 = {"rule": "태그 규칙마다 칸마다 [n, 첫 가용일 > 기간말 + 90일, 그중 첫 filed − 기간말 ≤ 200일, 201~300일, > 300일] · "
                  "XBRL 이전 대리 칸은 규칙상 기간말 + 90일이라 세지 않는다",
          "reading": ("🚨 이 칸들은 «평면 90일 규칙의 순수 선견» 만이 아니다. 지연 > 300일 무리는 대부분 그 값이 다음 해 제출의 비교기간으로 처음 태그된 "
                      "태깅 · 수록 산물이다 — 갈래(gt300_breakdown): q4_3m_ni = 연간 보고서의 Q4 3개월 순이익(2009~2011 블록 태깅 시기 · 예 AAPL "
                      "Q4 FY2009 는 2010-10-27 에 처음 태그) · periodic_filing_within_200d = 그 그룹이 기간말 + 200일 안에 다른 Eg 사실을 실은 제출을 "
                      "냈는데 이 칸은 후보 태그로 안 실렸다(후보 밖 태그 · 태그 도입 전 — 예 TSLA 2015-09-30 3개월 주식수는 2015-11-05 에 "
                      "WeightedAverageNumberOfShareOutstandingBasicAndDiluted 로 제때 냈다) · no_filing_within_200d = companyfacts 원장에 그 창의 "
                      "제출이 없다(수록 누락 또는 실제 늦은 제출 — 예 ADP 2010-05 10-Q 는 companyfacts 에 사실이 없다). ≤ 200일 무리가 늦은 제출 · "
                      "정정에 가깝다. 규칙은 바꾸지 않는다(§2 문구와 맞다) — 2단계가 돌면 Δ 주석에 이 단서를 붙인다."),
          "v": r2doc("v"), "vs": r2doc("vs")}
    TAGQ = {"rule": "형제 태그 메움(P-V)의 크기 — 칸마다 두 규칙의 첫 가용을 견준다: P-V 가 형제 태그 값으로 시작한 칸(= P-VS 에서는 더 늦게 가용) · "
                    "그 첫 값이 최신판과 10% 넘게(부호 다름 · 0 포함) 다른 칸 · P-VS 에서 늦어지는 날 수 · P-VS 에서만 기간말 + 90일 뒤에 가용한 칸",
            "sibling_first_cells": tagq["sibling_first_cells"], "sibling_first_far_gt10pct": tagq["sibling_first_far"],
            "by_key": {k: {"n": a, "far": f} for k, (a, f) in sorted(tagq["by_key"].items())},
            "vs_later": {"n": len(tagq["vs_later_days"]), "p50_days": pct(tagq["vs_later_days"], 0.5),
                         "p90_days": pct(tagq["vs_later_days"], 0.9)},
            "late_only_under_vs": tagq["late_only_under_vs"], "cells_without_lf_tag_record": tagq["vs_no_lf_record"],
            "examples_far": {"cols": ["t", "field", "b", "pe", "lf", "pv_first", "pv_first_tag", "filed", "abs_log_ratio(None=부호·0)"],
                             "rows": tagq["examples"][:60]},
            "supplier_stat": {"v": diags["v"]["supplier_stat"], "vs": diags["vs"]["supplier_stat"]}}
    print("보고: 형제 태그로 시작 %d 칸(10%% 넘게 다름 %d) · P-VS 에서 늦어짐 %d 칸(중앙 %s일) · 늦은 첫 가용 v %d / vs %d · v >300일 갈래 %s"
          % (TAGQ["sibling_first_cells"], TAGQ["sibling_first_far_gt10pct"], TAGQ["vs_later"]["n"], TAGQ["vs_later"]["p50_days"],
             R2["v"]["total"]["late"], R2["vs"]["total"]["late"], gt300["v"]))

    # ── 보고 3: Q4 3개월 사실 가용률 ──────────────────────────────────
    q4 = {}
    for tk, (sub, j) in FX.items():
        tg = j.get("tags") or {}
        ni = tg.get("ni") or {}
        src = ni.get("src")
        ti = IX["tickers"].get(tk)
        if not src or not ti:
            continue
        tx = "ifrs-full" if j.get("std") == "IFRS" else "us-gaap"
        K = LED[ti["gid"]]["keys"].get("ni:%s:%s" % (tx, src)) or {}
        lfq = {x[0] for x in clean(ni.get("q"))}
        for pe_a, ra in (K.get("a") or {}).items():
            if not ("2008" <= pe_a[:4] <= "2026"):
                continue
            rq = (K.get("q") or {}).get(pe_a) or []
            a = q4.setdefault(pe_a[:4], [0, 0, 0, 0])
            a[0] += 1
            a[1] += bool(rq)
            a[2] += bool(rq) and rq[0][2] == ra[0][2]     # 연간값을 처음 실은 그 제출(10-K 등)이 Q4 3개월 값도 실었다
            a[3] += pe_a in lfq
    R3 = {"rule": "회계연도(연간 순이익 기록이 있는 해 · 최신판 ni 태그)마다 [n, Q4 3개월 순이익 기록이 원장에 있다, 그 첫 기록이 연간값의 첫 제출과 "
                  "같은 accn, 최신판 ni q 에 있다]",
          "note": "Item 302(a) 분기 자료 요구가 2021 무렵 없어졌다는 기억은 미검증 — 이 표는 자료가 보여 주는 대로만 싣는다",
          "by_fy_year": {y: {"n": a[0], "q4_any": a[1], "q4_same_filing": a[2], "q4_in_lf": a[3],
                             "rate_any": round(a[1] / a[0], 4) if a[0] else None,
                             "rate_same_filing": round(a[2] / a[0], 4) if a[0] else None} for y, a in sorted(q4.items())}}

    # ── 보고 4: 기울기 생존 점검 · 공급자별 편입 후보 수 ─────────────────────
    def surv(dg):
        reg = dg["reg"]
        sh_ = [v["n_left"] / v["n"] for v in reg.values() if v["n"]]
        return {"months": len(reg),
                "n_left_min": min(v["n_left"] for v in reg.values()), "n_left_max": max(v["n_left"] for v in reg.values()),
                "share_left_median": sorted(sh_)[len(sh_) // 2] if sh_ else None,
                "n_median": sorted(v["n"] for v in reg.values())[len(reg) // 2],
                "monthly": {ym: [x["n"], x["n_left"], x["n_fxpit"]] for ym, x in reg.items()}}
    R4 = {"rule": "달마다 Eg 기울기 회귀 표본(랩 전 종목 · 금융 · 음(−)자본 제외 · 실현 변화가 선 이름) [n, 그중 마지막 가격이 %s 전인 이름, fx_pit 이름]"
                  % diags["latest"]["left_before"],
          **{s: surv(diags[s]) for s in SUPPLIERS}}
    NC = {"rule": "형성월마다 점수가 선 편입 후보 수(그때 S&P 500 ∪ NASDAQ 100 · 금융 제외 · 상태가 선 이름) — 점수 값은 보지 않는다",
          "by_supplier": {s: diags[s]["formations"] for s in SUPPLIERS},
          "mean": {s: round(sum(diags[s]["formations"].values()) / len(diags[s]["formations"]), 2) for s in SUPPLIERS}}

    # ── 보고 5: QFWD V0 입력 경로 대조(§7) ─────────────────────────────
    ex = QFWD_EX
    d_m = mends[ex["m"]]
    td_past = mends[ex["past_ym"]]
    tmp = tempfile.mkdtemp(prefix="egff_qfwd_")
    tb = git(["archive", "--format=tar", ex["commit"], "data/fx", "data/fx_pit"], repo)
    with tarfile.open(fileobj=io.BytesIO(tb)) as tf:
        tf.extractall(tmp, filter="data")
    rc = git(["log", "-1", "--format=%cI", ex["commit"], "--", "data/fx"], repo).decode().strip()
    Rdate = dt.datetime.fromisoformat(rc.replace("Z", "+00:00")).astimezone(dt.timezone.utc).date().isoformat()

    def compare(d, fxroot):
        c = {"equal": 0, "differ": 0, "differ_filed_after_R": 0, "differ_sibling_tag": 0, "fwd_only": 0, "fwd_only_no_record": 0,
             "pv_only": 0, "pv_only_filed_after_R": 0, "pv_only_sibling_tag": 0, "tickers": 0}
        ex_rows = []
        for sub in ("fx", "fx_pit"):
            dd = os.path.join(fxroot, "data", sub)
            for fn in sorted(os.listdir(dd)):
                tk = fn[:-5]
                ti = IX["tickers"].get(tk)
                if not ti or not fn.endswith(".json"):
                    continue
                j = rj(os.path.join(dd, fn))
                tg = j.get("tags") or {}
                tx = "ifrs-full" if j.get("std") == "IFRS" else "us-gaap"
                L = LED[ti["gid"]]
                c["tickers"] += 1
                for field, k, b, ser, hi in lf_fields(tg):
                    src = (tg.get(k) or {}).get("src")
                    fwd = {pe: v for pe, v in ser if pe_plus(pe) <= d}
                    for pe, v in fwd.items():
                        subs = EV.ledger_subs(L, CANDS, k, tx, src, b, pe)
                        r = EV.vintage_pick(subs, d, "v") if subs else None
                        if r is None:
                            c["fwd_only"] += 1
                            c["fwd_only_no_record"] += not subs
                        elif r[0] == v:
                            c["equal"] += 1
                        else:
                            c["differ"] += 1
                            c["differ_filed_after_R"] += r[1] > Rdate
                            c["differ_sibling_tag"] += r[2] != 0
                            if len(ex_rows) < 10:
                                ex_rows.append([tk, k, b, pe, v, r[0], r[1]])
                    # P-V 에만 있는 칸 — 판 R 의 기간 집합 범위 안(sho 는 sh 첫 기간말 앞)에서 R 이 아직 못 실은 기간(= R 뒤 제출)
                    recs = ((L["keys"].get("%s:%s:%s" % (k, tx, src)) or {}).get(b)) or {}
                    lo = min(x[0] for x in ser) if ser else None
                    for pe, rows in recs.items():
                        if pe in fwd or lo is None or pe < lo or (hi is not None and pe >= hi) or pe_plus(pe) > d:
                            continue
                        if not any(len(r) < 6 or r[5] == L["primary"] for r in rows):
                            continue                  # 선행 CIK 만 실은 기간 — 주 CIK 의 칸이 아니다(최신판 · P-V 모두 안 쓴다)
                        r = EV.vintage_pick(EV.ledger_subs(L, CANDS, k, tx, src, b, pe), d, "v")
                        if r:
                            c["pv_only"] += 1
                            c["pv_only_filed_after_R"] += r[1] > Rdate
                            c["pv_only_sibling_tag"] += r[2] != 0      # 판 R 의 태그로는 아직 없고 형제 태그가 먼저 실은 칸
        return c, ex_rows
    try:
        cmp_now, ex_now = compare(d_m, tmp)
        cmp_past, ex_past = compare(td_past, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    R5 = {"question": "QFWD 의 V0(build/qfwd_adapter.py ⑤ bake_eg)가 결정일에 읽는 재무 = 그 결정일의 P-V 인가",
          "code_path": [
              "build_root: 뿌리 = 판 커밋 V 의 data/(git archive) + P3 덮어쓰기 + 코드 핀 build/ — data/fx · fx_pit 은 판 V 의 파일이다",
              "bake_eg(⑤): 그 뿌리에서 얼린 eg_q5.py --pit-gics 를 F1_ = m 으로 한 번 굽고 months[m] 만 쓴다 — 회귀 2010-01 ~ m 과 형성 m 이 모두 판 V 의 fx 로 다시 계산된다",
              "판 V 의 fx = 토요일 SEC 갱신(refresh_facts) 시점 R 의 «filed 가 가장 늦은 값» · fx_pit = 2026-08-11 수집본(주간 갱신 대상 아님)",
              "형성월 예측변수 X_m: eg_q5 의 지연(분기 90일 · 연간 4개월 · 주식수 90일) 뒤 칸 = R 까지 제출된 최신값 — P-V(d_m)(가용일 ≤ d_m 중 최신)와 칸마다 같다. "
              "예외: (1) R 뒤 · d_m 전에 제출된 기록(주간 갱신 지연 — 전방이 못 본다) (2) d_m 당일 제출(P-V 는 다음 세션 규칙으로 뺀다 · R < d_m 이면 전방도 못 본다) "
              "(3) R 의 태그 재선택(refresh_facts.extract) — 아래 대조는 판 R 의 태그를 먼저 쓴다",
              "기울기: 전방은 b̄_m 을 판 V 의 fx 로 과거 달마다 다시 추정한다 — 과거 달 ym 의 입력이 «R 까지의 재작성이 반영된 값» 이다. "
              "결정일 기준으로는 시점정확(R 뒤 정보 없음)이지만, 표본 안 P-V 가 쓰는 «그 달 ym 의 빈티지» 와는 다르다 — 전방 V0 = P-V 가 아니라 «결정일 최신판» 이다"],
          "example": {"m": ex["m"], "d_m": d_m, "fx_commit": ex["commit"], "fx_commit_utc_date": Rdate,
                      "formation_cells": cmp_now, "formation_examples": ex_now,
                      "past_regression_month": ex["past_ym"], "past_td": td_past, "past_cells": cmp_past, "past_examples": ex_past,
                      "rule": "칸 = 판 R 의 fx · fx_pit 에서 eg_q5 가 읽는 칸 중 기간말 + 90일 ≤ 날짜 · 값 = 판 R 의 값 대 그 날짜의 P-V(판 R 의 태그 먼저 · 원장)"},
          "reading": ("형성월(%s): 같음 %d · 다름 %d · 전방만 %d · P-V 만 %d — 형성월 입력은 결정일 P-V 와 같다(차이는 R 뒤 제출 %d 칸). "
                      "과거 달(%s): 같음 %d · 다름 %d · 전방만(그때 아직 제출 전) %d — 전방이 다시 추정하는 기울기의 입력은 그 달의 빈티지가 아니다."
                      % (ex["m"], cmp_now["equal"], cmp_now["differ"], cmp_now["fwd_only"], cmp_now["pv_only"],
                         cmp_now["differ_filed_after_R"] + cmp_now["pv_only_filed_after_R"],
                         ex["past_ym"], cmp_past["equal"], cmp_past["differ"], cmp_past["fwd_only"]))}
    print("보고 QFWD: 형성월 %s · 과거 달 %s" % (cmp_now, cmp_past))

    # ── 모음 ──────────────────────────────────────────────────────────
    ok = F0_i["pass"] and F0_ii["pass"] and F0_iii["pass"]
    n404 = sum(1 for v in MAN["files"].values() if v.get("status") == 404)
    imap_now = os.path.join(repo, "data", "_issuer_map.json")
    imap_pin = IX["inputs"]["issuer_map_sha256"]
    nc = NC["mean"]
    stage1 = {"decision_basis": S4.BASIS, "report_only": list(S4.TWINS), "script": "build/s4_overlap.py",
              "declared": "2026-09-26 · F0 커밋 전 · 겹침 통계를 하나도 보기 전",
              "readings": {"v": "P-V — 형제 태그 메움(eg_q5_vintage.vintage_pick) · 결정 기준",
                           "ff": "P-FF — 최초 제출값(태그 규칙은 P-V 와 같다) · 보고만(§4)",
                           "vs": "P-VS — P-V 와 같되 최신판 태그만(엄격 태그 · §2 «태그마다» 문구 그대로) · 보고만(2026-09-26 선언)"},
              "anchor": "V0 자기 교체 척도 = 분기 간격 편입 쌍 39개(2016-09→12 ~ 2026-03→06) · 2016-08→09 한 달 쌍은 행에만 싣고 척도에서 뺀다",
              "scores_sha256": F0_iii["scores_sha256"], "root_tree_sha256": tree_before[0]}
    doc = {"note": "EGFF F0(사전등록 %s §8) — 수익 없음 · 겹침 통계 없음. pass 가 참이고 이 파일이 커밋돼 있어야 build/s4_overlap.py(1단계)가 돈다." % PREREG,
           "prereg": PREREG, "reg_commit": S4.REG_COMMIT, "pass": ok,
           "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "inputs": {"ledger_index_sha256": sha_file(os.path.join(DATA, "_fxv", "index.json")),
                      "manifest_sha256": sha_file(os.path.join(repo, "data", "_fxv", "manifest.json")),
                      "companyfacts_files": len(MAN["files"]), "companyfacts_404": n404,
                      "ledger_stats": {k: v for k, v in IX["stats"].items() if k != "pick_bad"},
                      "lf_fetch": {"fx": cut["fx"][1], "fx_pit": cut["fx_pit"][1]},
                      "issuer_map": {"sha256_pinned_in_index": imap_pin,
                                     "main_tree_now_equal": os.path.exists(imap_now) and sha_file(imap_now) == imap_pin,
                                     "note": "원장 재빌드(fxv_build build)는 배치 R 의 build/issuer_map.py · data/_issuer_map.json 에 기댄다 — "
                                             "이 F0 때 두 파일은 저장소에 커밋돼 있지 않았다. 원장은 이 해시의 지도로 지었다."},
                      "root": {"tree_sha256": tree_before[0], "tree_files": tree_before[1], "tree_bytes": tree_before[2],
                               "tree_rule": "s4_overlap.tree_digest — 뿌리 build · data 아래 모든 파일(__pycache__ 제외)의 «상대경로 sha256» 줄(정렬)의 sha256",
                               "unchanged_across_bakes": True,
                               "snap_wt": {"path_hint": "$TEMP/snap_wt", "head": snap_head, "files": len(sf),
                                           "identical_in_root": len(sf) - len(s_diff) - len(s_miss), "differ": s_diff, "missing_in_root": s_miss},
                               "root_only": r_only_sum,
                               "p1_root": "배치 Q 와 같은 P1 판($TEMP/snap_wt: bef4eea8 가격 밖 + 940f0bda 가격 + 얼린 배치 Q 파일)의 복사본 + EGFF 파일 · "
                                          "snap_wt 는 읽기만 했다"},
                      "supplier_v": diags["v"]["supplier_stat"], "supplier_ff": diags["ff"]["supplier_stat"],
                      "supplier_vs": diags["vs"]["supplier_stat"]},
           "f0_i_filing_match": F0_i, "f0_ii_sh_split": F0_ii, "f0_iii_repro": F0_iii,
           "stage1_plan": stage1,
           "report": {"vintage_ne_latest": R1, "first_avail_after_pe90": R2, "tag_rule": TAGQ, "q4_3m": R3, "slope_survivorship": R4,
                      "formation_counts": NC, "qfwd_v0_path": R5},
           "declared": [
               "범위: 칸 집합 = 최신판(P1 판 data/fx · fx_pit)의 칸. P-V 는 칸을 늘리지 않는다 — 차이는 «그 칸의 어느 제출값을 언제부터 쓰나» 뿐(재작성 · 늦은 제출). "
               "§2 의 발행사 그룹 · 선행 CIK 는 최신판 칸의 빈티지를 채우는 데만 쓰인다. 그래서 1단계는 LF 칸 집합 위의 재작성 · 시점 차이만 재고 LF 자신의 칸 공백"
               "(observations 의 XOM · DIS · APA · AVGO)은 재지 않는다 — §2 문구보다 좁다(RESULT 문서가 이 범위를 적는다).",
               "[결정 · 2026-09-26 · 겹침 전] 태그 규칙: P-V(결정 기준)는 최신판 태그가 그 기간말을 아직 싣지 않은 날에 같은 Eg 키의 다른 후보 태그(refresh_facts 순서)의 "
               "가용 기록을 쓴다(eg_q5_vintage.vintage_pick). 근거 — §1 «투자자는 그때까지 제출된 숫자만» · 그때의 refresh_facts.extract 는 가장 최근까지 보고된 태그"
               "(= 그 형제)를 골랐을 것이다. 이것은 §2 «태그마다» 문구를 넘는 읽기이고, extract 는 한 항목 안에서 태그를 섞지 않으며, 이 읽기는 V 대 LF 후보 수 진단"
               "(엄격 태그면 형성 첫 달에 이름이 수십 빠진다)을 본 뒤 골랐다 — V 를 LF 쪽으로 당겨 «재작성 둔감» 쪽에 유리할 수 있다(적대 검토). 그래서 엄격 태그 쌍둥이 "
               "P-VS(최신판 태그만)를 같이 굽고 1단계에서 보고만 한다(결정에 쓰지 않는다 · P-FF 와 같은 자리 · stage1_plan). 크기(report.tag_rule): P-V 가 형제 태그 값으로 "
               "시작한 칸 %d · 그중 최신판과 10%% 넘게(부호 · 0 포함) 다른 칸 %d(합병 전 껍데기 값 LIN · SW · PSKY · QRVO · 개념 갈아타기 LongTermDebt ↔ "
               "LongTermDebtNoncurrent · ProfitLoss ↔ NetIncomeLoss 등 — examples_far) · P-VS 에서 늦어지는 칸 %d(중앙 %s일 · 90%% %s일) · P-VS 에서만 기간말 + 90일 뒤 "
               "가용 %d · 편입 후보 월 평균 P-V %.2f · P-VS %.2f · LF %.2f(P-VS − P-V 월별 %d ~ %d)."
               % (TAGQ["sibling_first_cells"], TAGQ["sibling_first_far_gt10pct"], TAGQ["vs_later"]["n"], TAGQ["vs_later"]["p50_days"],
                  TAGQ["vs_later"]["p90_days"], TAGQ["late_only_under_vs"], nc["v"], nc["vs"], nc["latest"],
                  min(NC["by_supplier"]["vs"][m] - NC["by_supplier"]["v"][m] for m in NC["by_supplier"]["v"]),
                  max(NC["by_supplier"]["vs"][m] - NC["by_supplier"]["v"][m] for m in NC["by_supplier"]["v"])),
               "sh 기록 단위 사고(천주 ↔ 백만주)는 최신판 sh 계열 중앙값 기준으로 먼저 정리한다(Supplier._unit_clean — 최신판 _clean_units 와 같은 문턱 · 0.01~100배 밖 기록은 뺀다). "
               "달러 항목(asset · debt · eq · ni · cfo)은 최신판처럼 정리하지 않는다.",
               "sh 분할 되맞춤: 분사형 몫 r/q 는 기간말 뒤 전부 · 실제 분할 q 는 그 기록의 «분할 기준일» 뒤 것만 — 기준일 = 같은 칸에서 같은 값(±0.5%)을 실은 "
               "가장 늦은 filed(Supplier._basis · 기준만 뒤 제출이 확인한다 — 그 몫만큼 인자에 뒤 제출 정보가 든다). 효력일 전에 분할을 이미 반영해 낸 제출"
               "(SAB Topic 4C · 실측 AOS 2013-05-06)을 두 번 곱하지 않게 한다. 분할 판정(실제 · 분사형 · 섞임)은 최신판 tech_backtest.split_kinds 의 것을 그대로 쓴다(§2).",
               "알려진 작은 산물(고치지 않는다): ① HPE 2017-04-03 DXC 분사를 split_kinds 가 «실제 분할»(1.3348)로 갈라 P-V · 최신판 모두 일관되지 않다(f0_ii fail_reading) — "
               "한 종목만 손으로 고치면 §2 의 분할 경로 재사용을 어기고 재작성과 무관한 V−LF 차이를 더한다 · F0 (ii) 는 어느 쪽이든 넘는다. "
               "② load_fund 의 «sh 가 시작하기 전만 sho» 를 날짜마다 다시 적용해 sh 태그 이력이 늦게 실린 회사는 최신 관측이 앞 기간말로 물러난다"
               "(%d 종목 · %d 월말 · 그중 sh ↔ sho 필드가 바뀐 것 %d — f0_ii v_latest_obs_moved_back · 적대 검토 실측 GOOGL 2024-07 · 08 |log ME| 최대 약 0.019 · "
               "TSLA 2013-04). 그날의 랩 경로를 그날의 자료에 그대로 적용한 결과다."
               % (F0_ii["v_latest_obs_moved_back"]["tickers"], F0_ii["v_latest_obs_moved_back"]["cell_months"],
                  F0_ii["v_latest_obs_moved_back"]["field_switch"]),
               "선행 CIK 기록은 주 CIK 의 첫 정기보고 전 · 지도 효력 구간 안의 것만 받는다(fxv_build.group_ledger).",
               "늦은 첫 가용(report.first_avail_after_pe90 · P-V): %d 칸 = 첫 filed − 기간말 ≤ 200일 %d · 201~300일 %d · > 300일 %d. > 300일 무리는 대부분 "
               "태깅 · 수록 산물이지 늦은 공시가 아니다 — Q4 3개월 순이익 %d · 그 그룹이 기간말 + 200일 안에 다른 Eg 사실을 실은 제출을 냈는데 이 칸만 후보 태그로 "
               "안 실린 것 %d · 원장에 그 창의 제출이 없는 것 %d(companyfacts 누락 또는 실제 늦은 제출). 규칙은 바꾸지 않는다. 2단계가 돌면 Δ 주석에 "
               "«입력 재작성 누수» 만이 아니라 이 태깅 산물이 섞였다고 적는다."
               % (R2["v"]["total"]["late"], R2["v"]["total"]["le200"], R2["v"]["total"]["d201_300"], R2["v"]["total"]["gt300"],
                  R2["v"]["gt300_breakdown"]["q4_3m_ni"], R2["v"]["gt300_breakdown"]["periodic_filing_within_200d"],
                  R2["v"]["gt300_breakdown"]["no_filing_within_200d"]),
               "수익 울타리: eg_q5_vintage 는 --pit-gics 에서 얼린 코드가 계산만 하고 버리던 다음 달 수익 · 다리 · F4 를 계산하지 않는다(점수는 바이트 동일 — F0 (iii)).",
               "1단계 척도(보고만): V0 자기 교체 = 분기 간격 편입 쌍 39개 — 2016-08→09 한 달 쌍은 뺀다(§4 «정상 교체 한 분기»).",
               "뿌리 고정: 1단계는 inputs.root.tree_sha256 과 같은 뿌리에서만 돈다(s4_overlap 관문 ④ · 다른 World 입력으로 열리지 않게) · 저장소는 랩 저장소만(--repo 없음)."],
           "result_doc_must_carry": [
               "범위 — LF 칸 집합 위의 재작성 · 시점 차이만(LF 칸 공백 XOM 등은 재지 않는다)",
               "태그 규칙 결정(P-V = 형제 태그 메움 · 겹침 전 선언)과 P-VS 의 (a)(b)(c) 를 나란히",
               "늦은 첫 가용 > 300일 무리 = 태깅 · 수록 산물이 대부분 — 2단계 Δ 주석의 단서",
               "HPE · sh/sho 이음매 산물(작다)"],
           "observations": [
               "최신판 자체의 칸 공백(공급자와 무관): data/fx/XOM.json 은 2026-07 지주사 CIK 2115436 에서 와 관측이 두셋뿐이라 XOM 은 얼린 Eg 점수 120개월 어디에도 없다 · "
               "DIS(2024-01 부터) · APA(2023-05 부터) · AVGO(2019-03 부터) 도 후계 CIK 의 짧은 이력 때문에 늦게 들어온다. P-V 도 같은 칸 집합이라 같다."],
           "sec": round(time.time() - t0, 1)}
    s = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    with io.open(out_p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    print("→ %s · F0 %s · %.0f초" % (out_p, "통과" if ok else "실패", time.time() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
