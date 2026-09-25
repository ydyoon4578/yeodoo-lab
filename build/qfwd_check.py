# -*- coding: utf-8 -*-
"""build/qfwd_check.py — 전방 원장(QFWD) 무결성 점검 · 표준 라이브러리만 · 기록을 읽기만 하고 고치지 않는다.

근본 이유 — 전방 원장의 값은 «그때 그렇게 결정했고 그렇게 기록했다» 는 사실 하나다. 한 줄이라도 나중에 고치거나 지우면
  그 사실이 사라지고, 사라졌다는 흔적도 남지 않는다. 그래서 매일 git 이력에서 네 가지를 기계가 다시 본다
  (계획 «qfwd_check가 매일 네 가지를 본다» · 사양 §3).

검사
  ① 접두사 — 다섯 .jsonl 은 판이 바뀔 때마다 지운 줄이 0 이어야 한다(git diff --numstat). HEAD 의 사슬이 온전하다는 것과
     합치면 «추가만 했다» 가 증명된다. 한 번 쓰는 파일(pins · parity · eg/ · fits/ · judge/ · amend/)은 수정·삭제 이력이 0 이어야 한다.
  ② 사슬 — seq 연속 · prev 연결 · sha 정확 · 줄마다 정본(canon) 그대로 · 열쇠마다 한 줄(결정 = 카드 · 달 · 포착 = 날 · 장부 = 장부 · 달 …).
     [선언] 같은 열쇠의 두 번째 줄은 사슬이 맞아도 무결성 위반이다 — 읽는 쪽은 늘 첫 줄을 쓴다(뒤 줄로 앞 결정을 덮지 못한다).
  ③ 결정 시각 < 마감 — 줄을 처음 담은 커밋의 시각과 대조한다. 적은 시각이 커밋보다 300초 넘게 늦으면 위반(시각을 지어냈다),
     late=false 인데 t_eff 가 마감 뒤면 late_commit(FF0 이 늦음으로 센다). 늦음은 사실 보고이지 실패가 아니다.
     [선언] «줄을 처음 담은 커밋» = origin/main 에서 닿는 병합 아닌 커밋 가운데 그 줄(같은 seq · sha)을 처음 더한 것(-p 의 + 줄).
       사람이 'git pull'(병합)로 봇 커밋을 둘째 부모로 밀어내도 줄의 시각은 봇 커밋에 남는다(검토 2026-09-25 — 첫 부모 diff 로 재면
       병합 시각으로 밀려 late_commit 이 생겼다).
     [선언] runner = local 인 결정 줄은 커밋 시각이 사용자 PC 시계라 증거가 약하다 — 그 줄을 본 첫 gha 실행의 witness 줄 시각까지
       t_eff 에 넣는다(witness 가 없으면 t_eff 없음 = 미커밋 취급).
     그리고 판 시각: d_m 마감 < 판 커밋 시각(git 의 실제 값) ≤ t_decided — 어긋나면 위반.
  ④ 핀 — qfwd 파일 blob · 사전등록 문서 blob · 수정 등록 핀 사슬(amend/) · 결정 줄의 코드 핀과 어댑터 blob · 1d81f083:build 트리 ·
     입력 파일 sha · 판 커밋과 기록한 origin/main 끝(snap.tip)이 origin/main 조상.
     --full 은 마지막 세 결정 달의 판 고르기를 기록한 끝(snap.tip)의 첫 부모 이력에서 다시 돌려 기록한 판이 규칙의 판인지 본다
     (대체 판이면 건너뛴 판마다 오류 시도 셋 · 시간 초과 여섯 이상이 기록돼 있어야 한다 · 막힘 대체면 그 시각까지 온전한 판이 없어야 한다).
  ⑤ 달력 줄(calendar.jsonl) — 휴장 줄의 날은 origin/main 의 SPY 에 종가가 없어야 하고, 조기 폐장 줄의 날은 있어야 한다.
  ⑥ 생존(창 모드 · validate.yml 만) — 마감 + 1일이 지난 결정이 없거나 · 포착이 3거래일 넘게 밀렸거나 · data/_qfwd 커밋이 4거래일
     없으면 1 로 끝난다(원장이 멈춰도 사이트는 멀쩡해 보이는 것을 막는다). --full(원장 워크플로의 앞 · 뒤 점검)에는 걸지 않는다 —
     걸면 멈춘 원장이 다시 돌 길이 막힌다.

등록 전(data/_qfwd/pins.json 없음)에는 «미등록 — 건너뜀» 을 찍고 0 으로 끝난다.
⚠ Windows 작업 사본은 core.autocrlf 로 CRLF 가 될 수 있다 — 정본 비교는 CRLF 를 LF 로 읽은 뒤 한다(git blob 은 LF).
⚠ 부분 복제(filter: blob:none)면 필요한 blob 을 먼저 한 번에 받는다(prefetch) — 게으른 받기로 하나씩 받으면 수천 번 왕복한다.

  python build/qfwd_check.py              # 창 — 최근 8일 판만 + 생존(validate.yml)
  python build/qfwd_check.py --full       # 전 이력(원장 워크플로의 앞 · 뒤 점검)
  python build/qfwd_check.py --heads      # 사슬 머리(파일 · 줄 · 마지막 seq · sha) 마크다운 — 워크플로 잡 요약에 적어 git 밖에 남긴다
  python build/qfwd_check.py --selftest   # 임시 git 저장소에서 변조 · 병합 · 중복 · 핀 · 달력 · 생존을 잡는지
  python build/qfwd_check.py --full --qdir <스크래치> --rehearsal
                                          # 되풀이 기록(qfwd_ledger --rehearse M --qdir) — git 밖 기록이라 사슬 · 정본 · 입력 sha ·
                                          #   코드 핀 · 판 조상 · 판 시각 · 판 재선택만 본다(접두사 · 커밋 시각 대조는 해당 없음)
"""
from __future__ import annotations
import datetime
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
QREL = "data/_qfwd"
JSONL = ("decisions.jsonl", "books.jsonl", "market.jsonl", "px_capture.jsonl", "calendar.jsonl")
IMMUT_REL = ("data/_qfwd/pins.json", "data/_qfwd/parity.json", "data/_qfwd/eg", "data/_qfwd/fits", "data/_qfwd/judge",
             "data/_qfwd/amend")
QFWD_FILES = ("build/qfwd_adapter.py", "build/qfwd_ledger.py", "build/qfwd_check.py", "build/qfwd_judge.py",
              ".github/workflows/qfwd-ledger.yml")
ADAPTER_REL = "build/qfwd_adapter.py"
CODE_PIN = "1d81f083a404c68e23d15a649ef6f0a340d4d95c"
BUILD_TREE = "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8"
PREREG_DEFAULT = "build/PREREG-2026-09-26-QFWD.md"   # = qfwd_adapter.PREREG · 정본은 pins.json 의 prereg · genesis
WINDOW_DAYS = 8
COMMIT_SLACK = 300            # 초 — 적은 결정 시각이 커밋 시각보다 이만큼 넘게 늦으면 위반
RESELECT_LAST = 3
LIVE_GRACE_H = 24             # 생존 — 결정 마감 뒤 이만큼 지나도 결정이 없으면 경보
LIVE_CAP_TD = 3               # 생존 — 포착이 이만큼(거래일) 밀리면 경보
LIVE_COMMIT_TD = 4            # 생존 — data/_qfwd 커밋이 이만큼(거래일) 없으면 경보
CAL_KINDS = ("closed", "early", "utc_offset")


class IntegrityError(Exception):
    pass


# ── 정본 · 봉인 ─────────────────────────────────────────────────────────────
def canon(o):
    """사슬 줄의 정본 — 키 정렬 · 비ASCII 그대로 · 공백 없음 · NaN 금지(결측은 null)."""
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def rec_sha(rec):
    return hashlib.sha256(canon({k: v for k, v in rec.items() if k != "sha"}).encode("utf-8")).hexdigest()


def seal(rec, seq, prev):
    """seq · prev 를 붙이고 sha 를 봉인한 새 사전(원본은 그대로)."""
    r = {k: v for k, v in rec.items() if k != "sha"}
    r["seq"], r["prev"] = int(seq), prev
    r["sha"] = rec_sha(r)
    return r


def obj_sha(o):
    """목표 sha(targets_sha) — 정본 위에서 잰다. NaN 이면 거부한다(목표에 NaN 이 있을 수 없다)."""
    return hashlib.sha256(canon(o).encode("utf-8")).hexdigest()


def fcanon(o):
    """한 번 쓰는 파일(eg/ · fits/ · judge/)의 정본 — canon 과 같되 NaN 을 허용한다
    (q_ltd 적합 결과는 allow_nan=True 로 오가고 q_ltd.manifest 도 그렇게 잰다 — 바꾸면 지문이 갈린다)."""
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=True)


def file_sha(o):
    """한 번 쓰는 파일의 sha — 파싱한 값의 fcanon 위에서 잰다(줄바꿈 변환에 흔들리지 않는다)."""
    return hashlib.sha256(fcanon(o).encode("utf-8")).hexdigest()


def raw_sha(path):
    """파일 바이트의 sha256 — CRLF 는 LF 로 읽는다(qfwd_adapter.pins 의 parity_sha 는 바이트 sha 다)."""
    return hashlib.sha256(io.open(path, "rb").read().replace(bytes([13, 10]), bytes([10]))).hexdigest()


def genesis(prereg, name, code_pin=CODE_PIN):
    return hashlib.sha256(("QFWD|%s|%s|%s" % (prereg, code_pin, name)).encode("utf-8")).hexdigest()


def rmtree(path):
    """임시 폴더 지우기 — Windows 에서 git 객체 파일은 읽기 전용이라 shutil.rmtree(ignore_errors) 가 조용히 남긴다."""
    import stat

    def _retry(fn, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    if not os.path.exists(path):
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry)
    else:
        shutil.rmtree(path, onerror=_retry)


def iso_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_ts(s):
    """'YYYY-MM-DDTHH:MM:SSZ' → 유닉스 초."""
    d = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    return int(d.timestamp())


def ts_iso(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── git ─────────────────────────────────────────────────────────────────────
def git(repo, *args, check=True):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("git %s 실패: %s" % (" ".join(args[:3]), (r.stderr or "").strip()[:300]))
    return r.stdout


def git_ok(repo, *args):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0


def main_ref(repo):
    """origin/main 이 있으면 그것, 없으면 HEAD(로컬 시험 저장소)."""
    return "origin/main" if git_ok(repo, "rev-parse", "--verify", "--quiet", "origin/main") else "HEAD"


def rev_blob(repo, ref, rel):
    out = git(repo, "rev-parse", "--verify", "--quiet", "%s:%s" % (ref, rel), check=False).strip()
    return out or None


def work_blob(repo, rel):
    p = os.path.join(repo, rel)
    if not os.path.exists(p):
        return None
    return git(repo, "hash-object", "--", rel).strip() or None


def commit_time(repo, c):
    out = git(repo, "show", "-s", "--format=%ct", c, check=False).strip()
    return int(out) if out.isdigit() else None


def tip_at(repo, ref, ts):
    """ts 시각의 origin/main 끝을 이력에서 되짚는다 — ref 에서 닿는 모든 커밋 가운데 커밋 시각 ≤ ts 인 가장 늦은 것.
    되풀이 · 실측 전용(실제 원장은 실행 때 origin/main 을 그대로 기록한다 · snap.tip). 사람 커밋의 시각은 푸시 시각보다 이를 수 있어
    근사다 — 병합으로 둘째 부모가 된 봇 커밋도 그 시각에는 끝이었다는 점을 살린다(오늘의 첫 부모 이력으로 재면 그것을 잃는다)."""
    out = git(repo, "log", "--format=%H %ct", ref, check=False)
    best = None
    for ln in out.splitlines():
        h, ct = ln.split()
        ct = int(ct)
        if ct <= ts and (best is None or ct > best[1]):
            best = (h, ct)
    return best[0] if best else None


# ── 부분 복제(blob:none) — 필요한 blob 을 한 번에 받는다 ─────────────────────
def is_partial(repo):
    """origin 이 약속 원격(partial clone)인가 — 전체 복제면 아래 받기는 모두 아무것도 안 한다."""
    return git(repo, "config", "--get", "remote.origin.promisor", check=False).strip() == "true"


def missing_objects(repo, oids):
    """oids 가운데 로컬에 없는 것 — GIT_NO_LAZY_FETCH=1(git ≥ 2.44)로 게으른 받기를 끄고 묻는다."""
    oids = sorted(set(oids))
    if not oids:
        return []
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    # 바이트로 넘긴다 — Windows 의 텍스트 모드는 표준 입력의 \n 을 \r\n 으로 바꿔 git 이 'oid\r' 를 읽는다(로컬 대체 실행 실측)
    r = subprocess.run(["git", "cat-file", "--batch-check"], cwd=repo, input=("\n".join(oids) + "\n").encode("ascii"),
                       capture_output=True, env=env)
    return [ln.split()[0] for ln in r.stdout.decode("utf-8", "replace").splitlines() if ln.rstrip().endswith(" missing")]


def fetch_objects(repo, oids, chunk=20000):
    """없는 blob 을 한 번의 요청(덩어리마다)으로 받는다 — git 의 게으른 받기(promisor fetch)와 같은 명령을 한 묶음으로 부른다."""
    n = 0
    oids = list(oids)
    for i in range(0, len(oids), chunk):
        part = oids[i:i + chunk]
        r = subprocess.run(["git", "-c", "fetch.negotiationAlgorithm=noop", "fetch", "--no-tags", "--no-write-fetch-head",
                            "--recurse-submodules=no", "--filter=blob:none", "--stdin", "origin"], cwd=repo,
                           input=("\n".join(part) + "\n").encode("ascii"), capture_output=True)
        if r.returncode != 0:
            raise RuntimeError("부분 복제 blob 받기 실패(%d개): %s" % (len(part), r.stderr.decode("utf-8", "replace").strip()[:300]))
        n += len(part)
    return n


def _ls(repo, treeish, paths=(), recursive=False):
    """ls-tree — 트리만 읽는다(부분 복제에서도 blob 을 받지 않는다) · [(종류, oid)]."""
    args = ["ls-tree"] + (["-r"] if recursive else []) + [treeish]
    if paths:
        args += ["--"] + list(paths)
    out = git(repo, *args, check=False)
    got = []
    for ln in out.splitlines():
        meta = ln.split("\t", 1)[0].split()
        if len(meta) == 3:
            got.append((meta[1], meta[2]))
    return got


def prefetch(repo, commits, paths):
    """부분 복제에서만 — commits 의 paths 아래 blob 가운데 없는 것을 한 번에 받는다 · 받은 수(전체 복제면 설정 한 번만 읽고 0).
    하위 트리는 트리 id 로 한 번씩만 펼친다(대부분 커밋이 같은 하위 트리를 나눠 쓴다)."""
    if not is_partial(repo):
        return 0
    oids, trees = set(), set()
    for c in commits:
        for kind, oid in _ls(repo, c, paths):
            if kind == "blob":
                oids.add(oid)
            elif kind == "tree":
                trees.add(oid)
    for t in trees:
        oids |= {oid for kind, oid in _ls(repo, t, recursive=True) if kind == "blob"}
    miss = missing_objects(repo, oids)
    return fetch_objects(repo, miss) if miss else 0


# ── 사슬 ────────────────────────────────────────────────────────────────────
def read_lines(path):
    """파일 → 줄 목록(끝 줄바꿈 필수 · CRLF 는 LF 로 읽는다). 없는 파일은 빈 목록."""
    if not os.path.exists(path):
        return [], []
    raw = io.open(path, "rb").read()
    if not raw:
        return [], []
    errs = []
    txt = raw.decode("utf-8")
    parts = txt.split("\n")
    if parts[-1] != "":
        errs.append("끝 줄바꿈 없음(쓰다 만 줄)")
    else:
        parts = parts[:-1]
    return [p[:-1] if p.endswith("\r") else p for p in parts], errs


def verify_chain(lines, gen, name="?"):
    """줄 목록 → {n, last, recs, errs}. errs 가 비어야 온전하다."""
    errs, recs, prev = [], [], gen
    for i, ln in enumerate(lines):
        try:
            rec = json.loads(ln)
        except Exception as e:
            errs.append("%s %d번 줄 JSON 아님(%s)" % (name, i, str(e)[:60]))
            break
        if not isinstance(rec, dict):
            errs.append("%s %d번 줄이 객체가 아님" % (name, i))
            break
        if canon(rec) != ln:
            errs.append("%s seq %d 정본 아님(손으로 고친 줄)" % (name, i))
        if rec.get("seq") != i:
            errs.append("%s %d번 줄 seq %r(연속 아님)" % (name, i, rec.get("seq")))
        if rec.get("prev") != prev:
            errs.append("%s seq %d prev 가 앞 줄 sha 와 다름(사슬 끊김)" % (name, i))
        if rec.get("sha") != rec_sha(rec):
            errs.append("%s seq %d sha 불일치(내용이 바뀜)" % (name, i))
        prev = rec.get("sha")
        recs.append(rec)
        if len(errs) > 20:
            break
    return {"n": len(recs), "last": prev, "recs": recs, "errs": errs}


def qpath(qdir, rel):
    """기록 속 경로(data/_qfwd/…) → 이 점검의 기록 폴더 안 경로(되풀이 · 시험 qdir 도 같은 접두사로 적는다)."""
    if rel.startswith(QREL + "/"):
        return os.path.join(qdir, *rel[len(QREL) + 1:].split("/"))
    return rel


def load_pins(repo, qdir=None):
    """핀 사슬 → 지금 효력이 있는 핀(사전). 없으면 None.
    pins.json(등록 · genesis · 코드 핀 · 얼린 blob · P3 · 환경) + amend/pins-<n>.json(수정 등록 고리 · qfwd 파일 blob · parity)의
    마지막 고리를 겹친다. 붙는 열쇠: links(고리 목록) · adapter_blobs(사슬의 모든 어댑터 blob · 결정 줄이 이 가운데 하나여야 한다) ·
    parity_file(지금 어댑터의 짝맞춤 파일 · data/_qfwd/… 경로) · _base(pins.json 원문)."""
    q = qdir or os.path.join(repo, QREL)
    p = os.path.join(q, "pins.json")
    if not os.path.exists(p):
        return None
    base = json.load(io.open(p, encoding="utf-8"))
    links = []
    ad = os.path.join(q, "amend")
    if os.path.isdir(ad):
        for f in sorted(os.listdir(ad)):
            if f.startswith("pins-") and f.endswith(".json"):
                d = json.load(io.open(os.path.join(ad, f), encoding="utf-8"))
                d["_file"] = f
                links.append(d)
    eff = dict(base)
    eff["_base"] = base
    eff["links"] = links
    last = links[-1] if links else base
    eff["qfwd_files"] = dict(last.get("qfwd_files") or {})
    eff["parity_file"] = (last.get("parity") if links else None) or (QREL + "/parity.json")
    eff["parity_sha"] = last.get("parity_sha") if links else base.get("parity_sha")
    eff["adapter_blobs"] = sorted({(x.get("qfwd_files") or {}).get(ADAPTER_REL) for x in [base] + links} - {None})
    return eff


def chain_file(qdir, name, pins):
    gen = (pins.get("genesis") or {}).get(name) or genesis(pins.get("prereg") or PREREG_DEFAULT, name,
                                                           pins.get("code_pin") or CODE_PIN)
    lines, errs = read_lines(os.path.join(qdir, name))
    res = verify_chain(lines, gen, name)
    res["errs"] = errs + res["errs"]
    res["genesis"] = gen
    return res


def chain_all(qdir, pins):
    return {name: chain_file(qdir, name, pins) for name in JSONL}


def row_key(name, r):
    """한 파일 안에서 한 줄만 있어야 하는 열쇠 — 없으면 None(시도 · witness 줄은 여러 번 있을 수 있다)."""
    k = r.get("kind")
    if name == "decisions.jsonl":
        return ("decision", r.get("card"), r.get("m")) if k == "decision" else None
    if name == "px_capture.jsonl":
        return ("day", r.get("d")) if k == "day" else None
    if name == "market.jsonl":
        if k == "day":
            return ("day", r.get("d"))
        if k == "month":
            return ("month", r.get("h"))
        return None
    if name == "books.jsonl":
        return ("month", r.get("book"), r.get("h")) if k == "month" else None
    if name == "calendar.jsonl":
        return (k, r.get("d"), r.get("d0"), r.get("d1"))
    return None


def dup_check(chains):
    """열쇠 중복 — 같은 결정 · 포착 · 장부 달이 두 번 기록되면 사슬이 맞아도 위반(읽는 쪽은 첫 줄만 쓴다)."""
    viol = []
    for name, ch in chains.items():
        seen = {}
        for r in ch["recs"]:
            k = row_key(name, r)
            if k is None:
                continue
            if k in seen:
                viol.append("%s 중복 줄 %s — seq %d 가 seq %d 와 같은 열쇠(앞 줄이 정본 · 뒤 줄은 무효)"
                            % (name, "/".join(str(x) for x in k if x is not None), r.get("seq"), seen[k]))
            else:
                seen[k] = r.get("seq")
    return viol


def first_by_key(name, recs):
    """열쇠마다 첫 줄 — 읽는 쪽(원장 · 판정기)이 쓰는 표. {열쇠: 줄}."""
    out = {}
    for r in recs:
        k = row_key(name, r)
        if k is not None and k not in out:
            out[k] = r
    return out


# ── 핀 사슬 · 사전등록 문서 ─────────────────────────────────────────────────
def pin_chain_check(repo, pins, qdir, head=True):
    """pins.json · amend/ 고리 — 번호 연속 · 앞 고리 sha · 코드 핀 · 어댑터가 바뀐 고리의 짝맞춤 · 문서 blob(head=True)."""
    viol = []
    base = pins.get("_base") or pins
    if head and not pins.get("rehearsal"):
        pb = base.get("prereg_blob")
        if not pb:
            viol.append("pins.json 에 prereg_blob 이 없다(사전등록 문서가 핀이 아니다)")
        elif rev_blob(repo, "HEAD", base.get("prereg") or PREREG_DEFAULT) != pb:
            viol.append("사전등록 문서 %s 의 HEAD blob ≠ pins.prereg_blob(등록 뒤 문서를 고쳤다)" % base.get("prereg"))
    prev, prev_ad = base, (base.get("qfwd_files") or {}).get(ADAPTER_REL)
    for i, ln in enumerate(pins.get("links") or [], 1):
        raw = {k: v for k, v in ln.items() if k != "_file"}
        tag = "수정 등록 고리 %s" % ln.get("_file")
        if raw.get("n") != i or ln.get("_file") != "pins-%03d.json" % i:
            viol.append("%s 번호가 %d 이 아니다(연속 아님)" % (tag, i))
        if raw.get("prev_sha") != hashlib.sha256(canon({k: v for k, v in prev.items() if k != "_file"}).encode("utf-8")).hexdigest():
            viol.append("%s prev_sha 가 앞 고리와 다르다(사슬 끊김)" % tag)
        if raw.get("code_pin") != CODE_PIN:
            viol.append("%s code_pin 이 %s 가 아니다(코드 핀은 바꿀 수 없다)" % (tag, CODE_PIN[:8]))
        if set(raw.get("qfwd_files") or {}) != set(QFWD_FILES):
            viol.append("%s qfwd_files 열쇠가 다섯 파일이 아니다" % tag)
        for fld in ("genesis", "frozen_blobs", "p3", "env", "build_tree"):
            if fld in raw:
                viol.append("%s 가 %s 를 담았다(바꿀 수 없는 핀)" % (tag, fld))
        ad = (raw.get("qfwd_files") or {}).get(ADAPTER_REL)
        if ad != prev_ad:
            pp = qpath(qdir, raw.get("parity") or "")
            pj = json.load(io.open(pp, encoding="utf-8")) if raw.get("parity") and os.path.exists(pp) else {}
            if not pj.get("ok") or pj.get("adapter_blob") != ad:
                viol.append("%s 어댑터가 바뀌었는데 짝맞춤 %s 가 ok 가 아니거나 blob 이 다르다" % (tag, raw.get("parity")))
            elif raw.get("parity_sha") != raw_sha(pp):
                viol.append("%s parity_sha ≠ %s" % (tag, raw.get("parity")))
        if head and rev_blob(repo, "HEAD", raw.get("prereg") or "") != raw.get("prereg_blob"):
            viol.append("%s 의 수정 등록 문서 %s HEAD blob ≠ 고리의 prereg_blob" % (tag, raw.get("prereg")))
        prev, prev_ad = raw, ad
    return viol


# ── 접두사 · 한 번 쓰는 파일 ────────────────────────────────────────────────
def log_versions(repo, rel, ref="HEAD", since=None):
    """첫 부모 이력에서 rel 을 바꾼 커밋들(오래된 것부터) — [{c, ct, add, dele}]. 병합은 첫 부모와 비교한다."""
    args = ["log", "--first-parent", "--diff-merges=first-parent", "--no-renames", "--reverse", "--numstat",
            "--format=C %H %ct"]
    if since:
        args.append("--since=%s" % since)
    out = git(repo, *args, ref, "--", rel, check=False)
    vs, cur = [], None
    for ln in out.splitlines():
        if ln.startswith("C "):
            _c, h, ct = ln.split(" ")
            cur = {"c": h, "ct": int(ct), "add": 0, "dele": 0, "bin": False}
            vs.append(cur)
        elif cur is not None and "\t" in ln:
            a, d, _p = ln.split("\t", 2)
            if a == "-" or d == "-":
                cur["bin"] = True
            else:
                cur["add"] += int(a)
                cur["dele"] += int(d)
    return vs


def prefix_check(repo, since=None, qrel=QREL):
    """{pairs, viol} — 판마다 지운 줄 0 · 작업 사본도 HEAD 에서 지운 줄 0."""
    pairs, viol = 0, []
    for name in JSONL:
        rel = "%s/%s" % (qrel, name)
        vs = log_versions(repo, rel, "HEAD", since)
        for j, v in enumerate(vs):
            if j > 0 or rev_blob(repo, v["c"] + "^", rel):
                pairs += 1                          # 앞 판이 있는 판만 쌍이다(처음 만든 판은 빼고 센다)
            if v["bin"] or v["dele"]:
                viol.append("%s 커밋 %s 가 %d줄을 지우거나 고쳤다" % (name, v["c"][:12], v["dele"]))
        if rev_blob(repo, "HEAD", rel):
            out = git(repo, "diff", "--numstat", "--no-renames", "HEAD", "--", rel, check=False).strip()
            if out:
                a, d, _p = out.split("\t", 2)
                if d == "-" or int(d):
                    viol.append("%s 작업 사본이 커밋본에서 %s줄을 지우거나 고쳤다" % (name, d))
    return {"pairs": pairs, "viol": viol}


def immut_check(repo, qrel=QREL):
    rels = ["%s/%s" % (qrel, x.split("/", 2)[2]) for x in IMMUT_REL]
    viol = []
    out = git(repo, "log", "--no-renames", "--diff-filter=MD", "--format=%H", "HEAD", "--", *rels, check=False)
    for h in out.split():
        viol.append("한 번 쓰는 파일을 고치거나 지운 커밋 %s" % h[:12])
    st = git(repo, "status", "--porcelain", "--no-renames", "--", *rels, check=False)
    for ln in st.splitlines():
        code = ln[:2]
        if code in ("??", "A ", "AM"):
            continue
        viol.append("한 번 쓰는 파일이 작업 사본에서 바뀜: %s" % ln.strip()[:120])
    return viol


# ── 결정 시각 ───────────────────────────────────────────────────────────────
def seq_commits(repo, rel, ref, since=None):
    """{(seq, sha): (커밋, 커밋 시각)} — ref 에서 닿는 병합 아닌 커밋 가운데 그 줄(같은 seq · sha)을 처음 더한 것.
    [선언] 병합 커밋은 보지 않는다 — 사람이 'git pull'(병합)로 봇 커밋을 둘째 부모로 밀어내도 줄은 봇 커밋의 + 줄로 남는다.
      병합이 스스로 새 줄을 만들었다면(있어서는 안 된다) 그 줄은 여기 없다 = 미커밋 취급(FF0 이 늦음으로 센다 · 보수 쪽)."""
    args = ["log", "--no-merges", "--topo-order", "--reverse", "-p", "--unified=0", "--no-renames", "--no-color",
            "--no-ext-diff", "--format=C %H %ct"]
    if since:
        args.append("--since=%s" % since)
    out = git(repo, *args, ref, "--", rel, check=False)
    first, cur = {}, None
    for ln in out.splitlines():
        if ln.startswith("C ") and len(ln) > 43 and ln[42] == " ":
            _c, h, ct = ln.split(" ")
            cur = (h, int(ct))
            continue
        if cur is None or not ln.startswith("+") or ln.startswith("+++"):
            continue
        try:
            r = json.loads(ln[1:])
        except Exception:
            continue
        if isinstance(r, dict) and "seq" in r and "sha" in r:
            first.setdefault((r["seq"], r["sha"]), cur)
    return first


def commit_map(repo, rel, ref, recs, since=None):
    """{seq: (커밋, 커밋 시각)} — 지금 기록(recs)의 줄 가운데 커밋에서 찾은 것만(같은 seq · sha)."""
    first = seq_commits(repo, rel, ref, since)
    return {r["seq"]: first[(r["seq"], r.get("sha"))] for r in recs if (r.get("seq"), r.get("sha")) in first}


def witness_times(recs):
    """{결정 seq: 그 줄을 본 첫 gha witness 줄의 시각(초)} — runner = local 인 결정 줄의 t_eff 에 넣는다."""
    out = {}
    for r in recs:
        if r.get("kind") == "witness" and r.get("runner") == "gha":
            for s in r.get("of") or []:
                out.setdefault(s, iso_ts(r["t_rec"]))
    return out


def t_eff_ts(rec, ct, twit):
    """t_eff(초) = max(t_decided, 커밋 시각[, runner = local 이면 witness 시각]) · 모르면 None."""
    if ct is None:
        return None
    t = max(iso_ts(rec["t_decided"]), int(ct))
    if rec.get("runner") != "gha":
        w = twit.get(rec["seq"])
        if w is None:
            return None
        t = max(t, w)
    return t


def _ledger():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import qfwd_ledger as L
    return L


def snap_time_check(repo, r, committed_git=True):
    """판 시각 — d_m 마감 < 판 커밋 시각 ≤ t_decided · 기록한 판 시각 = git 의 실제 커밋 시각."""
    L = _ledger()
    s = r.get("snap") or {}
    viol = []
    if not s.get("commit") or not s.get("commit_time") or not r.get("d_m"):
        return ["결정 seq %s 에 판 커밋 · 시각 · d_m 이 없다" % r.get("seq")]
    sc = iso_ts(s["commit_time"])
    if committed_git:
        real = commit_time(repo, s["commit"])
        if real is not None and real != sc:
            viol.append("결정 seq %d 판 %s 의 기록 시각 ≠ git 커밋 시각" % (r["seq"], s["commit"][:12]))
    if sc <= int(L.close_utc(r["d_m"]).timestamp()):
        viol.append("결정 seq %d(%s %s) 판 %s 가 d_m 마감 전 커밋이다" % (r["seq"], r.get("card"), r.get("m"), s["commit"][:12]))
    if iso_ts(r["t_decided"]) < sc:
        viol.append("결정 seq %d(%s %s) 의 t_decided 가 판 커밋보다 이르다" % (r["seq"], r.get("card"), r.get("m")))
    return viol


def deadline_check(repo, recs, ref, since=None, qrel=QREL, committed=True):
    """committed=False — git 에 없는 기록(되풀이): 모든 줄이 미커밋이다(커밋 시각 대조 없음 · 적은 시각의 늦음만 센다)."""
    rel = "%s/decisions.jsonl" % qrel
    sc = commit_map(repo, rel, ref, recs, since) if committed else {}
    twit = witness_times(recs)
    n_ref = 0
    if committed and rev_blob(repo, ref, rel):
        n_ref = git(repo, "show", "%s:%s" % (ref, rel), check=False).count("\n")
    res = {"checked": 0, "late": 0, "late_commit": 0, "pending": 0, "late_pending": 0, "witness_pending": 0, "viol": [],
           "late_rows": []}
    for r in recs:
        if r.get("kind") != "decision":
            continue
        res["viol"] += snap_time_check(repo, r)
        if r["seq"] not in sc:
            if r["seq"] >= n_ref:
                res["pending"] += 1                 # 아직 origin/main 에 없는 줄 — 커밋 시각이 없다
                if iso_ts(r["deadline"]) <= iso_ts(r["t_decided"]):
                    res["late_pending"] += 1         # 적은 시각만으로도 늦다(커밋 시각은 더 늦을 뿐이다)
                    res["late_rows"].append((r.get("card"), r.get("m"), "late_pending"))
            continue                                # 창 앞에 더한 줄(창 모드)
        c, ct = sc[r["seq"]]
        res["checked"] += 1
        td, dl = iso_ts(r["t_decided"]), iso_ts(r["deadline"])
        if td > ct + COMMIT_SLACK:
            res["viol"].append("결정 seq %d(%s %s) 의 t_decided 가 커밋 %s 보다 %d초 늦다 — 시각을 지어냈다"
                               % (r["seq"], r.get("card"), r.get("m"), c[:12], td - ct))
        te = t_eff_ts(r, ct, twit)
        if te is None:
            res["witness_pending"] += 1             # runner local — gha witness 전(판정기 · 원장은 미커밋 취급)
        if dl <= td:
            res["late"] += 1
            res["late_rows"].append((r.get("card"), r.get("m"), "late"))
        elif not r.get("late") and te is not None and te >= dl:
            res["late_commit"] += 1
            res["late_rows"].append((r.get("card"), r.get("m"), "late_commit"))
    return res


# ── 핀 ──────────────────────────────────────────────────────────────────────
def pins_check(repo, pins, chains, qdir, ref, code_pin_check=True, head=True):
    """head=False — 되풀이 전용(등록 전이라 qfwd 파일이 아직 HEAD 에 없다): 작업 사본 blob 만 핀과 맞춘다."""
    viol = []
    qf = pins.get("qfwd_files") or {}
    for rel in QFWD_FILES:
        want = qf.get(rel)
        if not want:
            viol.append("pins.qfwd_files 에 %s 없음" % rel)
            continue
        got = rev_blob(repo, "HEAD", rel) if head else want
        if got != want:
            viol.append("%s HEAD blob %s ≠ 핀 %s" % (rel, (got or "없음")[:12], want[:12]))
        wb = work_blob(repo, rel)
        if wb != want:
            viol.append("%s 작업 사본 blob %s ≠ 핀 %s" % (rel, (wb or "없음")[:12], want[:12]))
    if (pins.get("code_pin") or CODE_PIN) != CODE_PIN:
        viol.append("pins.code_pin %s ≠ %s" % (pins.get("code_pin"), CODE_PIN[:12]))
    if code_pin_check:
        bt = git(repo, "rev-parse", "--verify", "--quiet", "%s:build" % CODE_PIN, check=False).strip()
        if bt != BUILD_TREE:
            viol.append("git rev-parse %s:build = %s ≠ BUILD_TREE %s" % (CODE_PIN[:8], (bt or "없음")[:12], BUILD_TREE[:12]))
    viol += pin_chain_check(repo, pins, qdir, head=head)
    pp = qpath(qdir, pins.get("parity_file") or (QREL + "/parity.json"))
    if pins.get("parity_sha"):
        if not os.path.exists(pp):
            viol.append("%s 없음(핀에는 있다)" % pins.get("parity_file"))
        elif pins["parity_sha"] not in (raw_sha(pp), file_sha(json.load(io.open(pp, encoding="utf-8")))):
            viol.append("%s sha ≠ 핀의 parity_sha" % pins.get("parity_file"))
    ads = set(pins.get("adapter_blobs") or ([qf.get(ADAPTER_REL)] if qf.get(ADAPTER_REL) else []))
    dec = {r["seq"]: r for r in chains["decisions.jsonl"]["recs"] if r.get("kind") == "decision"}
    seen_files, anc = {}, {}
    for r in dec.values():
        code = r.get("code") or {}
        if code.get("pin") != CODE_PIN:
            viol.append("결정 seq %d code.pin 불일치" % r["seq"])
        if ads and code.get("adapter_blob") not in ads:
            viol.append("결정 seq %d adapter_blob 이 핀 사슬의 어느 어댑터도 아니다" % r["seq"])
        inp = r.get("inputs") or {}
        refs = [x for x in (inp.get("eg") or {}).values()] + list(inp.get("fits") or [])
        for x in refs:
            f = x.get("file")
            if not f:
                continue
            if f not in seen_files:
                fp = qpath(qdir, f) if f.startswith(QREL + "/") else (os.path.join(repo, f) if not os.path.isabs(f) else f)
                seen_files[f] = file_sha(json.load(io.open(fp, encoding="utf-8"))) if os.path.exists(fp) else None
            if seen_files[f] != x.get("sha"):
                viol.append("결정 seq %d 입력 %s sha 불일치(%s)" % (r["seq"], f, "파일 없음" if seen_files[f] is None else "바뀜"))
        s = r.get("snap") or {}
        for fld in ("commit", "tip"):
            c = s.get(fld)
            if c and c not in anc:
                anc[c] = git_ok(repo, "merge-base", "--is-ancestor", c, ref)
            if c and not anc[c]:
                viol.append("결정 seq %d 판 %s %s 가 %s 조상이 아님" % (r["seq"], fld, c[:12], ref))
    # 장부 줄의 src 가 가리키는 결정 · 목표 sha 가 실제와 같은가
    for r in chains["books.jsonl"]["recs"]:
        for rb in r.get("reb") or []:
            s = rb.get("src") or {}
            d = dec.get(s.get("seq"))
            if d is None:
                viol.append("장부 %s %s 되맞춤이 없는 결정 seq %r 를 가리킨다" % (r.get("book"), r.get("h"), s.get("seq")))
            elif (d.get("targets_sha") or {}).get(s.get("target")) != s.get("sha"):
                viol.append("장부 %s %s 되맞춤 목표 sha 가 결정 seq %d 와 다르다" % (r.get("book"), r.get("h"), d["seq"]))
    return viol


# ── 달력 줄 ─────────────────────────────────────────────────────────────────
def calendar_check(repo, ref, recs):
    """달력 줄(calendar.jsonl) — 모양 · 그리고 SPY 날짜와 맞는지(휴장 = 그날 SPY 종가 없음 · 조기 폐장 = 그날 거래됨)."""
    viol = []
    rows = list(recs)
    for r in rows:
        k = r.get("kind")
        if k not in CAL_KINDS:
            viol.append("달력 seq %s 모르는 종류 %r" % (r.get("seq"), k))
        elif k in ("closed", "early"):
            try:
                datetime.date.fromisoformat(r.get("d") or "")
            except ValueError:
                viol.append("달력 seq %s 날짜 모양이 아니다" % r.get("seq"))
        elif k == "utc_offset":
            if r.get("off") not in (4, 5) or not (r.get("d0") or "") <= (r.get("d1") or ""):
                viol.append("달력 seq %s utc_offset 은 off ∈ {4, 5} · d0 ≤ d1" % r.get("seq"))
    need = [r for r in rows if r.get("kind") in ("closed", "early")]
    if not need:
        return viol
    try:
        A = json.loads(git(repo, "show", "%s:data/assets.json" % ref))
        spy = {d for d, p in zip(A["dates"], A["px"]["SPY"]) if p is not None}
    except Exception as e:
        return viol + ["달력 대조용 %s:data/assets.json 을 못 읽었다(%s)" % (ref, str(e)[:80])]
    last = max(spy) if spy else ""
    for r in need:
        d = r.get("d") or ""
        if d > last:
            continue                                  # 아직 오지 않은 날(미리 알린 휴장)
        if r["kind"] == "closed" and d in spy:
            viol.append("달력 seq %d 휴장 %s 인데 SPY 에 그날 종가가 있다" % (r["seq"], d))
        if r["kind"] == "early" and d not in spy:
            viol.append("달력 seq %d 조기 폐장 %s 인데 SPY 에 그날이 없다" % (r["seq"], d))
    return viol


# ── 판 재선택 ───────────────────────────────────────────────────────────────
def reselect_check(repo, recs, n_last=RESELECT_LAST):
    """마지막 n 결정 달 — 기록한 판이 규칙의 판인가(qfwd_ledger 의 고르기를 기록한 origin/main 끝(snap.tip)의 첫 부모 이력에서
    그 결정 시각으로 다시 돈다 · 끝은 불변이라 뒤의 병합 · 푸시가 결과를 바꾸지 않는다).
    대체 판 — 건너뛴 판 없이 고르면 건너뛴 첫 판 · 건너뛰고 고르면 기록한 판 · 건너뛴 판마다 그 무리의 오류 시도 ≥ ERR_FALLBACK
      또는 시간 초과 ≥ TO_FALLBACK 이 결정 전에 기록돼 있어야 한다. 막힘 대체(degraded) — 온전한 판이 그 시각까지 없어야 한다."""
    L = _ledger()
    dec = [r for r in recs if r.get("kind") == "decision"]
    att = [r for r in recs if r.get("kind") == "attempt"]
    months = sorted({r["m"] for r in dec})[-n_last:]
    viol, n = [], 0
    led = L.Ledger(repo=repo, write=False)
    try:
        for m in months:
            rows = [r for r in dec if r["m"] == m]
            groups = {}
            for r in rows:
                groups.setdefault((L.group_of([r["card"]]), r["snap"]["commit"]), []).append(r)
            for (g, c), rr in sorted(groups.items()):
                s = rr[0]["snap"]
                tip = s.get("tip") or led.ref
                until = max(iso_ts(r["t_decided"]) for r in rr)
                led.now = datetime.datetime.fromtimestamp(until, datetime.timezone.utc)
                skipped = list(s.get("skipped") or ([s["fallback_from"]] if s.get("fallback_from") else []))
                n += 1
                sel0 = led.select_decision(m, until_ts=until, ref=tip)
                want0 = skipped[0] if skipped else c
                if sel0.get("commit") != want0:
                    viol.append("결정 %s %s 판 %s ≠ 끝 %s 에서 다시 고른 판 %s" % (m, g, want0[:12], tip[:12], (sel0.get("commit") or "없음")[:12]))
                    continue
                if skipped:
                    sel1 = led.select_decision(m, skip=set(skipped), until_ts=until, ref=tip)
                    if sel1.get("commit") != c:
                        viol.append("결정 %s %s 대체 판 %s ≠ 건너뛰고 다시 고른 판 %s" % (m, g, c[:12], (sel1.get("commit") or "없음")[:12]))
                    for sk in skipped:
                        ne = sum(1 for a in att if a.get("m") == m and L.attempt_group(a) == g and a.get("snap") == sk
                                 and a.get("outcome") == "error" and iso_ts(a["t"]) <= until)
                        nt = sum(1 for a in att if a.get("m") == m and L.attempt_group(a) == g and a.get("snap") == sk
                                 and a.get("outcome") == "timeout" and iso_ts(a["t"]) <= until)
                        if ne < L.ERR_FALLBACK and nt < L.TO_FALLBACK:
                            viol.append("결정 %s %s 가 판 %s 를 건너뛰었는데 오류 시도 %d · 시간 초과 %d 뿐이다"
                                        % (m, g, sk[:12], ne, nt))
                if bool(s.get("degraded")) != bool(sel0.get("degraded")):
                    viol.append("결정 %s %s 막힘 대체 표시(%s)가 다시 고른 판과 다르다" % (m, g, bool(s.get("degraded"))))
    finally:
        led.close()
    return {"n": n, "viol": viol}


# ── 생존(창 모드) ───────────────────────────────────────────────────────────
def liveness_check(repo, chains, ref, qrel=QREL, now=None):
    """원장이 멈췄는가 — 마감 + 1일 지난 결정 없음 · 포착 3거래일 밀림 · data/_qfwd 커밋 4거래일 없음(진입 뒤만)."""
    L = _ledger()
    L.apply_calendar(chains["calendar.jsonl"]["recs"])
    now = now or datetime.datetime.now(datetime.timezone.utc)
    viol = []
    dec = first_by_key("decisions.jsonl", chains["decisions.jsonl"]["recs"])
    m = L.FIRST_M
    while L.close_utc(L.d_m(m)) < now:
        for c in L.due_cards(m):
            if ("decision", c, m) not in dec and now > L.deadline(c, m) + datetime.timedelta(hours=LIVE_GRACE_H):
                viol.append("생존: %s %s 결정이 마감(%s) + %d시간이 지나도록 없다" % (c, m, L.iso(L.deadline(c, m)), LIVE_GRACE_H))
        m = L.mshift(m, 1)
    caps = [r for r in chains["px_capture.jsonl"]["recs"] if r.get("kind") == "day"]
    if now > L.close_utc(L.td_add(L.ENTRY_DAY, LIVE_CAP_TD)):
        nxt = L.next_td(caps[-1]["d"]) if caps else L.ENTRY_DAY
        if L.close_utc(L.td_add(nxt, LIVE_CAP_TD)) < now:
            viol.append("생존: 포착이 %s 에서 %d거래일 넘게 멈췄다" % (nxt, LIVE_CAP_TD))
        out = git(repo, "log", "-1", "--format=%ct", ref, "--", qrel, check=False).strip()
        if out.isdigit():
            d_last = datetime.datetime.fromtimestamp(int(out), datetime.timezone.utc).date().isoformat()
            if L.close_utc(L.td_add(d_last if L.is_td(d_last) else L.prev_td(d_last), LIVE_COMMIT_TD)) < now:
                viol.append("생존: data/_qfwd 커밋이 %s 뒤로 %d거래일 넘게 없다" % (d_last, LIVE_COMMIT_TD))
        else:
            viol.append("생존: data/_qfwd 커밋을 찾지 못했다")
    return viol


# ── 사슬 머리(잡 요약) ──────────────────────────────────────────────────────
def heads(repo=REPO, qdir=None, out=print):
    """사슬 머리 — git 밖(Actions 잡 요약)에 남겨 뒤의 이력 재작성과 대조할 닻으로 쓴다."""
    qdir = os.path.abspath(qdir or os.path.join(repo, QREL))
    pins = load_pins(repo, qdir)
    head = git(repo, "rev-parse", "HEAD", check=False).strip()
    out("### QFWD 사슬 머리 — %s · HEAD %s%s" % (iso_now(), head[:12], "" if pins else " · 미등록"))
    if not pins:
        return 0
    out("\n| 파일 | 줄 | 마지막 seq | 마지막 sha |\n|---|---|---|---|")
    for name, r in chain_all(qdir, pins).items():
        out("| %s | %d | %s | %s |" % (name, r["n"], r["recs"][-1]["seq"] if r["recs"] else "-", r["last"] if r["recs"] else "-"))
    return 0


# ── 실행 ────────────────────────────────────────────────────────────────────
def run_checks(repo=REPO, full=False, qdir=None, out=print, code_pin_check=True, reselect=True, now=None, rehearsal=False,
               liveness=None):
    """(ok, 요약 사전). ok=False 는 무결성 위반(또는 창 모드의 생존 경보)이다(늦음은 위반이 아니다).
    rehearsal=True — 되풀이 기록 폴더(저장소 밖 · 커밋하지 않는다 · pins.rehearsal = true): 사슬 · 정본 · 입력 sha · 코드 핀 ·
      판 조상 · 판 시각 · 판 재선택은 그대로 보고, git 에 없는 기록이라 뜻이 없는 접두사 · 한 번 쓰는 파일 · 커밋 시각 대조는 건너뛴다.
      qfwd 파일은 등록 전이라 HEAD 가 아닌 작업 사본 blob 만 핀과 맞춘다.
    liveness — 기본 = 창 모드이고 되풀이가 아닐 때."""
    qdir = os.path.abspath(qdir or os.path.join(repo, QREL))
    qrel = os.path.relpath(qdir, repo).replace(os.sep, "/")
    pins = load_pins(repo, qdir)
    if pins is None:
        out("QFWD 무결성: 미등록 — 건너뜀 (data/_qfwd/pins.json 없음)")
        return True, {"registered": False}
    if rehearsal:
        if not pins.get("rehearsal") or not qrel.startswith(".."):
            raise IntegrityError("되풀이 점검은 저장소 밖 · pins.rehearsal = true 인 기록 폴더에만 쓴다")
    elif pins.get("rehearsal"):
        raise IntegrityError("되풀이 핀(pins.rehearsal)이 원장 폴더에 있다")
    if liveness is None:
        liveness = (not full) and (not rehearsal)
    ref = main_ref(repo)
    since = None
    if not full:
        t0 = (now or datetime.datetime.now(datetime.timezone.utc)) - datetime.timedelta(days=WINDOW_DAYS)
        since = t0.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not rehearsal and is_partial(repo):
        cs = git(repo, "log", "--format=%H", "--full-history", ref, "--", qrel, check=False).split()
        if since:
            cs = git(repo, "log", "--format=%H", "--full-history", "--since=%s" % since, ref, "--", qrel, check=False).split()
        par = set()
        for c in cs:
            par |= set(git(repo, "rev-parse", c + "^@", check=False).split())
        prefetch(repo, list(dict.fromkeys(cs + sorted(par))), [qrel + "/"])
    viol = []
    ch = chain_all(qdir, pins)
    _ledger().apply_calendar(ch["calendar.jsonl"]["recs"])      # 판 시각 · 생존 점검이 쓰는 달력 = 기록된 달력 줄
    n_ok = sum(1 for r in ch.values() if not r["errs"])
    for r in ch.values():
        viol += r["errs"]
    viol += dup_check(ch)
    if rehearsal:
        px = {"pairs": 0, "viol": []}
        dl = deadline_check(repo, ch["decisions.jsonl"]["recs"], ref, None, qrel, committed=False)
    else:
        px = prefix_check(repo, since, qrel)
        viol += px["viol"]
        viol += immut_check(repo, qrel)
        dl = deadline_check(repo, ch["decisions.jsonl"]["recs"], ref, since, qrel)
    viol += dl["viol"]
    pv = pins_check(repo, pins, ch, qdir, ref, code_pin_check=code_pin_check, head=not rehearsal)
    viol += pv
    if full and not rehearsal:
        viol += calendar_check(repo, ref, ch["calendar.jsonl"]["recs"])
    rs = {"n": 0, "viol": []}
    if full and reselect and ch["decisions.jsonl"]["recs"]:
        try:
            rs = reselect_check(repo, ch["decisions.jsonl"]["recs"])
        except Exception as e:
            rs = {"n": 0, "viol": ["판 다시 고르기 실패: %s" % str(e)[:200]]}
        viol += rs["viol"]
    lv = []
    if liveness:
        try:
            lv = liveness_check(repo, ch, ref, qrel, now=now)
        except Exception as e:
            lv = ["생존 점검 실패: %s" % str(e)[:200]]
        viol += lv
    summ = {"registered": True, "chains_ok": n_ok, "chains": len(JSONL), "pairs": px["pairs"], "late": dl["late"],
            "late_commit": dl["late_commit"], "pending": dl["pending"], "late_pending": dl["late_pending"],
            "witness_pending": dl["witness_pending"], "checked": dl["checked"], "pins_ok": not pv, "reselect": rs["n"],
            "liveness": lv, "viol": viol, "mode": ("rehearsal-" if rehearsal else "") + ("full" if full else "window"),
            "rows": {k: v["n"] for k, v in ch.items()}}
    out("QFWD 무결성(%s%s): 사슬 %d/%d · 접두사 %s · 늦음 %d · 늦은 커밋 %d · 대조 %d · 미커밋 %d(그중 적은 시각부터 늦음 %d) · "
        "witness 대기 %d · 핀 %s%s%s"
        % ("되풀이 · " if rehearsal else "", "전 이력" if full else "최근 %d일" % WINDOW_DAYS, n_ok, len(JSONL),
           "해당 없음(git 밖 기록)" if rehearsal else "%d쌍" % px["pairs"], dl["late"], dl["late_commit"],
           dl["checked"], dl["pending"], dl["late_pending"], dl["witness_pending"], "일치" if not pv else "불일치 %d" % len(pv),
           (" · 판 재선택 %d" % rs["n"]) if full else "", (" · 생존 %s" % ("경보 %d" % len(lv) if lv else "정상")) if liveness else ""))
    for v in viol[:30]:
        out("  🚨 " + v)
    return (not viol), summ


# ── 자가 시험 ───────────────────────────────────────────────────────────────
def _sh(cwd, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (args[:2], r.stderr[:300]))
    return r.stdout


def _commit(cwd, msg, when):
    env = {"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when}
    _sh(cwd, "add", "-A")
    _sh(cwd, "commit", "-q", "-m", msg, env=env)
    return _sh(cwd, "rev-parse", "HEAD").strip()


def _append(path, gen_or_prev, seq, rec):
    r = seal(rec, seq, gen_or_prev)
    with io.open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(canon(r) + "\n")
    return r


def _wtxt(path, txt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(txt)


def selftest():
    fails = []

    def ok(cond, what):
        print(("  ✓ " if cond else "  ✗ ") + what)
        if not cond:
            fails.append(what)

    # 정본 · 봉인
    r = seal({"kind": "x", "a": 1.1, "b": [1, None], "k": "한글"}, 0, "g")
    ok(canon(json.loads(canon(r))) == canon(r) and r["sha"] == rec_sha(r), "정본 · 봉인 왕복")
    ok(genesis("p", "decisions.jsonl") == genesis("p", "decisions.jsonl") != genesis("p", "books.jsonl"), "genesis 결정적 · 파일별")
    try:
        canon({"x": float("nan")})
        ok(False, "NaN 거부")
    except ValueError:
        ok(True, "NaN 거부")
    g = genesis("p", "t")
    lines, prev = [], g
    for i in range(3):
        x = seal({"kind": "k", "i": i, "f": 0.1 * i}, i, prev)
        lines.append(canon(x))
        prev = x["sha"]
    ok(not verify_chain(lines, g)["errs"], "온전한 사슬 통과")
    bad = list(lines)
    bad[1] = bad[1].replace('"i":1', '"i":7')
    ok(any("sha" in e for e in verify_chain(bad, g)["errs"]), "고친 줄 → sha 불일치")
    ok(any("seq" in e or "prev" in e for e in verify_chain([lines[0], lines[2]], g)["errs"]), "지운 줄 → seq · prev 끊김")
    ok(any("정본" in e for e in verify_chain([lines[0].replace(",", ", ", 1)] + lines[1:], g)["errs"]), "정본 아닌 줄 → 잡음")
    # witness — runner local 줄은 gha witness 전에는 t_eff 가 없다
    loc = {"seq": 5, "t_decided": "2026-10-01T00:00:00Z", "runner": "local"}
    wt = witness_times([{"kind": "witness", "runner": "gha", "of": [5], "t_rec": "2026-10-01T03:00:00Z"},
                        {"kind": "witness", "runner": "local", "of": [5], "t_rec": "2026-10-01T00:10:00Z"}])
    ok(t_eff_ts(loc, iso_ts("2026-10-01T00:05:00Z"), {}) is None and t_eff_ts(loc, iso_ts("2026-10-01T00:05:00Z"), wt) ==
       iso_ts("2026-10-01T03:00:00Z") and t_eff_ts(dict(loc, runner="gha"), iso_ts("2026-10-01T00:05:00Z"), {}) ==
       iso_ts("2026-10-01T00:05:00Z"), "witness — local 줄의 t_eff 는 첫 gha witness 까지 · gha 줄은 커밋 시각")
    # 중복 열쇠
    chs = {n: {"recs": []} for n in JSONL}
    chs["decisions.jsonl"]["recs"] = [{"seq": 0, "kind": "decision", "card": "QF06", "m": "2026-09"},
                                      {"seq": 1, "kind": "attempt", "m": "2026-09"},
                                      {"seq": 2, "kind": "decision", "card": "QF06", "m": "2026-09"}]
    chs["books.jsonl"]["recs"] = [{"seq": 0, "kind": "month", "book": "V0.D0", "h": "2026-11"},
                                  {"seq": 1, "kind": "month", "book": "V0.T1", "h": "2026-11"}]
    dv = dup_check(chs)
    ok(len(dv) == 1 and "seq 2" in dv[0] and first_by_key("decisions.jsonl", chs["decisions.jsonl"]["recs"])
       [("decision", "QF06", "2026-09")]["seq"] == 0, "중복 결정 줄 → 위반 · 읽는 쪽은 첫 줄")

    # 임시 git 저장소 — 접두사 · 한 번 쓰는 파일 · 결정 시각 · 병합 · 핀 · 사전등록 문서 · 수정 등록 · 달력 · 생존
    tmp = tempfile.mkdtemp(prefix="qfwd_check_")
    try:
        _sh(tmp, "init", "-q", "-b", "main")
        _sh(tmp, "config", "user.name", "qfwd-selftest")
        _sh(tmp, "config", "user.email", "qfwd@selftest.invalid")
        _sh(tmp, "config", "core.autocrlf", "false")
        for rel in QFWD_FILES:
            _wtxt(os.path.join(tmp, rel), "# %s\n" % rel)
        prereg = "build/PREREG-test.md"
        _wtxt(os.path.join(tmp, prereg), "# 시험 사전등록\n")
        q = os.path.join(tmp, QREL)
        os.makedirs(os.path.join(q, "eg"), exist_ok=True)
        blobs = {rel: _sh(tmp, "hash-object", rel).strip() for rel in QFWD_FILES}
        gens = {n: genesis(prereg, n) for n in JSONL}
        eg = {"v": 1, "m": "2026-09", "scores": {"AAA": 0.1}}
        eg_rel = QREL + "/eg/2026-09-aaaaaaaa.json"
        _wtxt(os.path.join(tmp, eg_rel), canon(eg) + "\n")
        parity = {"v": 1, "ok": True, "adapter_blob": blobs[ADAPTER_REL]}
        _wtxt(os.path.join(q, "parity.json"), canon(parity) + "\n")
        pins = {"v": 1, "prereg": prereg, "prereg_blob": _sh(tmp, "hash-object", prereg).strip(), "code_pin": CODE_PIN,
                "build_tree": BUILD_TREE, "qfwd_files": blobs, "genesis": gens, "parity_sha": file_sha(parity)}
        _wtxt(os.path.join(q, "pins.json"), canon(pins) + "\n")
        for n in JSONL:
            _wtxt(os.path.join(q, n), "")
        days = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]
        _wtxt(os.path.join(tmp, "data", "assets.json"), json.dumps({"dates": days, "px": {"SPY": [1.0, None, 1.1, 1.2, 1.3]}}))
        c0 = _commit(tmp, "register", "2026-09-30T21:00:00Z")      # 2026-09-30 마감(20:00Z) 뒤
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c0)

        def drow(m, d_m_, t_dec, dl, snap, sct, late=False, card="QF06", runner="gha"):
            return {"v": 1, "kind": "decision", "card": card, "m": m, "d_m": d_m_, "t_decided": t_dec, "deadline": dl, "late": late,
                    "runner": runner, "code": {"pin": CODE_PIN, "adapter_blob": blobs[ADAPTER_REL]},
                    "snap": {"commit": snap, "commit_time": sct, "tip": snap},
                    "inputs": {"eg": {"2026-09": {"file": eg_rel, "sha": file_sha(eg)}}, "fits": []},
                    "targets_sha": {"XBM": "x"}, "t_rec": t_dec}

        dp = os.path.join(q, "decisions.jsonl")
        a = _append(dp, gens["decisions.jsonl"], 0, drow("2026-09", "2026-09-30", "2026-10-01T00:00:00Z", "2026-10-01T19:30:00Z",
                                                          c0, "2026-09-30T21:00:00Z"))
        cd0 = _commit(tmp, "d0", "2026-10-01T00:05:00Z")
        _wtxt(os.path.join(tmp, "data", "x.txt"), "data 10-30\n")
        cdat1 = _commit(tmp, "data", "2026-10-30T21:00:00Z")
        b = _append(dp, a["sha"], 1, drow("2026-10", "2026-10-30", "2026-10-31T00:00:00Z", "2026-11-02T20:30:00Z",
                                          cdat1, "2026-10-30T21:00:00Z"))
        c2 = _commit(tmp, "d1", "2026-10-31T00:04:00Z")
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c2)
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(okk and s["pairs"] == 2 and s["checked"] == 2 and s["late"] == 0, "온전한 원장 통과(접두사 2쌍 · 대조 2)")

        def expect_fail(label, needle, **kw):
            okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False, **kw)
            ok((not okk) and any(needle in v for v in s["viol"]), label)

        # (1) 작업 사본에서 고친 줄
        body = io.open(dp, encoding="utf-8").read()
        _wtxt(dp, body.replace('"m":"2026-09"', '"m":"2026-08"'))
        expect_fail("고친 줄(작업 사본) → 잡음", "지우거나 고쳤다")
        _sh(tmp, "checkout", "--", QREL + "/decisions.jsonl")
        # (2) 커밋된 지운 줄
        lines, _e = read_lines(dp)
        _wtxt(dp, lines[1] + "\n")
        _commit(tmp, "drop", "2026-11-01T01:00:00Z")
        expect_fail("지운 줄(커밋) → 잡음", "지우거나 고쳤다")
        _sh(tmp, "reset", "-q", "--hard", c2)
        # (3) 끊긴 사슬 — 추가만 했지만 prev 가 틀렸다
        _append(dp, "0" * 64, 2, drow("2026-11", "2026-11-30", "2026-12-01T00:00:00Z", "2026-12-01T19:30:00Z", cdat1,
                                      "2026-10-30T21:00:00Z"))
        expect_fail("끊긴 사슬 → 잡음", "사슬 끊김")
        _sh(tmp, "checkout", "--", QREL + "/decisions.jsonl")
        # (4) 고친 eg 파일(커밋)
        _wtxt(os.path.join(tmp, eg_rel), canon(dict(eg, scores={"AAA": 0.2})) + "\n")
        _commit(tmp, "egedit", "2026-11-01T02:00:00Z")
        expect_fail("고친 eg 파일 → 잡음", "한 번 쓰는 파일")
        _sh(tmp, "reset", "-q", "--hard", c2)
        # (5) 지어낸 시각 — 커밋보다 한 시간 뒤로 적은 결정
        _wtxt(os.path.join(tmp, "data", "x.txt"), "data 11-30\n")
        cdat2 = _commit(tmp, "data", "2026-11-30T22:00:00Z")
        c2b = cdat2
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c2b)
        _append(dp, b["sha"], 2, drow("2026-11", "2026-11-30", "2026-12-01T02:00:00Z", "2026-12-01T19:30:00Z", cdat2,
                                      "2026-11-30T22:00:00Z"))
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(okk and s["pending"] == 1 and s["checked"] == 2, "미커밋 줄 → 대조 보류 1(위반 아님)")
        c3 = _commit(tmp, "d2", "2026-12-01T01:00:00Z")
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c3)
        expect_fail("커밋보다 늦은 t_decided → 위반", "지어냈다")
        _sh(tmp, "reset", "-q", "--hard", c2b)
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c2b)
        # (6) late=false 인데 커밋이 마감 뒤 — 위반이 아니라 late_commit 보고
        _append(dp, b["sha"], 2, drow("2026-11", "2026-11-30", "2026-12-01T19:00:00Z", "2026-12-01T19:30:00Z", cdat2,
                                      "2026-11-30T22:00:00Z"))
        c4 = _commit(tmp, "d2b", "2026-12-01T19:40:00Z")
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c4)
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(okk and s["late_commit"] == 1, "마감 뒤 커밋 → late_commit 1(위반 아님)")
        # (7) 창 모드 — 오래된 판은 안 보고 창 안의 판만 센다
        okk, s = run_checks(tmp, full=False, out=lambda *_: None, code_pin_check=False, reselect=False, liveness=False,
                            now=datetime.datetime(2026, 12, 3, tzinfo=datetime.timezone.utc))
        ok(okk and s["pairs"] == 1 and s["checked"] == 1, "창 모드(8일) — 창 안 1쌍만")
        # (8) 병합(foxtrot) — 사람이 옛 판에서 커밋하고 origin/main 을 병합해도 줄의 커밋 시각은 봇 커밋에 남는다
        _sh(tmp, "checkout", "-q", "-b", "human", c0)
        _wtxt(os.path.join(tmp, "README.md"), "사람 편집\n")
        _commit(tmp, "human edit", "2026-12-01T20:00:00Z")
        _sh(tmp, "merge", "-q", "--no-ff", "--no-edit", "main", env={"GIT_COMMITTER_DATE": "2026-12-02T09:00:00Z",
                                                                      "GIT_AUTHOR_DATE": "2026-12-02T09:00:00Z"})
        cm = _sh(tmp, "rev-parse", "HEAD").strip()
        _sh(tmp, "update-ref", "refs/remotes/origin/main", cm)
        fp_now = _sh(tmp, "log", "--first-parent", "--format=%H", cm).split()
        mp = commit_map(tmp, QREL + "/decisions.jsonl", "origin/main", chain_all(q, load_pins(tmp, q))["decisions.jsonl"]["recs"])
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(cd0 not in fp_now and mp.get(0, ("", 0))[0] == cd0 and mp.get(2, ("", 0))[0] == c4 and okk and s["late_commit"] == 1
           and s["checked"] == 3, "병합(둘째 부모로 밀린 봇 커밋) — 줄의 커밋은 봇 커밋 그대로 · late_commit 이 새로 생기지 않는다")
        _sh(tmp, "checkout", "-q", "main")
        _sh(tmp, "reset", "-q", "--hard", c4)
        _sh(tmp, "update-ref", "refs/remotes/origin/main", c4)
        # (9) 중복 결정 줄(사슬은 맞다) → 위반
        last = chain_all(q, load_pins(tmp, q))["decisions.jsonl"]["last"]
        _append(dp, last, 3, drow("2026-11", "2026-11-30", "2026-12-01T19:10:00Z", "2026-12-01T19:30:00Z", cdat2,
                                  "2026-11-30T22:00:00Z"))
        expect_fail("같은 (카드 · 달) 두 번째 결정 줄 → 위반", "중복 줄")
        _sh(tmp, "checkout", "--", QREL + "/decisions.jsonl")
        # (10) 판 시각 — d_m 마감 전 판 · 기록 시각 ≠ git
        _append(dp, last, 3, drow("2026-12", "2026-12-31", "2027-01-01T00:00:00Z", "2027-01-04T20:30:00Z", cdat2,
                                  "2026-11-30T22:00:00Z"))
        expect_fail("d_m 마감 전 판으로 한 결정 → 위반", "마감 전 커밋")
        _sh(tmp, "checkout", "--", QREL + "/decisions.jsonl")
        # (11) 사전등록 문서를 고쳐 커밋 → 위반
        _wtxt(os.path.join(tmp, prereg), "# 시험 사전등록(고침)\n")
        _commit(tmp, "prereg edit", "2026-12-02T01:00:00Z")
        expect_fail("등록 뒤 사전등록 문서 편집 → 위반", "prereg_blob")
        _sh(tmp, "reset", "-q", "--hard", c4)
        # (12) 핀 — qfwd 파일을 바꾸면 잡음 → 수정 등록 고리로 풀린다 → 고리의 앞 sha 를 틀리면 잡음
        _wtxt(os.path.join(tmp, "build/qfwd_ledger.py"), "# build/qfwd_ledger.py\n# 고침\n")
        amd = "build/PREREG-test-AMEND-1.md"
        _wtxt(os.path.join(tmp, amd), "# 수정 등록 1\n")
        _commit(tmp, "amend code", "2026-12-02T02:00:00Z")
        expect_fail("핀 밖 원장 코드 → 잡음", "핀")
        qf2 = dict(blobs, **{"build/qfwd_ledger.py": _sh(tmp, "hash-object", "build/qfwd_ledger.py").strip()})
        link = {"v": 1, "kind": "amend", "n": 1, "prev_sha": hashlib.sha256(canon(pins).encode("utf-8")).hexdigest(),
                "prereg": amd, "prereg_blob": _sh(tmp, "hash-object", amd).strip(), "why": "시험", "code_pin": CODE_PIN,
                "qfwd_files": qf2, "parity": QREL + "/parity.json", "parity_sha": file_sha(parity), "t": "2026-12-02T02:05:00Z"}
        _wtxt(os.path.join(q, "amend", "pins-001.json"), canon(link) + "\n")
        _commit(tmp, "amend link", "2026-12-02T02:05:00Z")
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(okk, "수정 등록 고리 — 새 blob 이 핀이 되고 사슬이 통과")
        _wtxt(os.path.join(q, "amend", "pins-001.json"), canon(dict(link, prev_sha="0" * 64)) + "\n")
        expect_fail("고리 prev_sha 변조 → 잡음", "사슬 끊김")
        _sh(tmp, "checkout", "--", QREL + "/amend/pins-001.json")
        # (13) 달력 줄 — 휴장이라 적은 날에 SPY 종가가 있으면 위반 · 없는 날이면 통과
        cp = os.path.join(q, "calendar.jsonl")
        _append(cp, gens["calendar.jsonl"], 0, {"v": 1, "kind": "closed", "d": "2026-09-29", "why": "시험", "t_rec": "2026-12-02T03:00:00Z"})
        _commit(tmp, "cal ok", "2026-12-02T03:00:00Z")
        _sh(tmp, "update-ref", "refs/remotes/origin/main", "HEAD")
        okk, s = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False)
        ok(okk, "달력 휴장 줄 — SPY 에 없는 날은 통과")
        cl = chain_all(q, load_pins(tmp, q))["calendar.jsonl"]["last"]
        _append(cp, cl, 1, {"v": 1, "kind": "closed", "d": "2026-09-30", "why": "시험", "t_rec": "2026-12-02T03:10:00Z"})
        _commit(tmp, "cal bad", "2026-12-02T03:10:00Z")
        _sh(tmp, "update-ref", "refs/remotes/origin/main", "HEAD")
        expect_fail("달력 휴장 줄인데 SPY 에 그날 종가가 있다 → 위반", "휴장 2026-09-30")
        # (14) 생존 — 창 모드: 2026-09 분기 카드 결정이 없고 마감 + 1일이 지났다 → 경보 · 전 이력 모드는 걸지 않는다
        now = datetime.datetime(2026, 10, 5, tzinfo=datetime.timezone.utc)
        okk, s = run_checks(tmp, full=False, out=lambda *_: None, code_pin_check=False, reselect=False, now=now)
        ok((not okk) and any("생존" in v and "V0 2026-09" in v for v in s["viol"]), "생존 — 마감 지난 결정 없음 → 창 모드 경보")
        okk2, s2 = run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=False, now=now)
        ok(not any("생존" in v for v in s2["viol"]), "생존 — 전 이력 모드(원장 앞 · 뒤 점검)에는 걸지 않는다")
    finally:
        rmtree(tmp)
    print("qfwd_check selftest: %s (%d 실패)" % ("통과" if not fails else "실패", len(fails)))
    return 0 if not fails else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    repo = REPO
    if "--repo" in argv:
        repo = os.path.abspath(argv[argv.index("--repo") + 1])
    qdir = os.path.abspath(argv[argv.index("--qdir") + 1]) if "--qdir" in argv else None
    if "--heads" in argv:
        return heads(repo, qdir)
    try:
        okk, _s = run_checks(repo, full="--full" in argv, qdir=qdir, rehearsal="--rehearsal" in argv)
    except IntegrityError as e:
        print("🚨 QFWD 무결성: %s" % e)
        return 1
    return 0 if okk else 1


if __name__ == "__main__":
    sys.exit(main())
