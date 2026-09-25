# -*- coding: utf-8 -*-
"""build/qfwd_adapter.py — 전방 원장(QFWD) 어댑터 · 끼움 일곱만 둔다 — 규칙 수는 하나도 바꾸지 않는다.

근본 이유 — 배치 Q 카드(Q07 · Q08 · Q06)와 EG30 V0 은 얼린 코드(1d81f083)로만 결정해야 전방 기록이 «그 규칙» 의 기록이 된다.
  얼린 모듈을 고치면 표본 안 판과 전방 판이 두 벌이 된다(이 랩이 되풀이한 결함). 그래서 차이는 모두 여기 끼움으로 둔다.
  끼움이 규칙 수를 바꾸지 않았다는 증거는 짝맞춤 시험 하나다 — 표본 안 판에 전방과 같은 끼움 경로를 태워도 얼린 굽기와
  비트 단위로 같은 목표 해시가 나와야 한다(하나라도 다르면 원장을 열지 않는다).

사전등록: build/PREREG-2026-09-26-QFWD.md §2 · §3 · §4 (설계 명세 scratchpad/qfwd_spec.md §1 을 코드로 옮겼다).

뿌리(build_root) — 작업 사본을 읽지 않는다. 판 커밋 V 의 data/ 를 git archive 로 꺼내고 코드 핀의 build/ 와 이 어댑터를 같은 임시 뿌리에 푼 뒤
  P3 고정 입력 9 를 코드 핀의 blob 으로 덮는다(sha1 단언). 얼린 코드를 뿌리의 build/ 에서 돌리므로 HERE · ROOT · DATA 가 저절로 뿌리를 가리킨다.
  [선언] git archive 는 core.autocrlf=false 로 부른다 — blob 바이트 그대로(Windows 의 autocrlf 가 CRLF 로 바꾸면 얼린 blob 단언이 깨진다).
끼움 일곱(모두 자식 과정 안의 대입이거나 임시 뿌리의 변환 · 얼린 파일은 편집하지 않는다):
  ① 기간 연장 — qg_lab.F1M = m · qbatch_core.HOLD1 = q_bmrot_leg.HOLD1 = m+1 · eg_q5.F1_ = m(굽기만)
  ② Q07 편입을 [m] 으로 — q_ltd.formations = lambda ctx: [m]
  ③ Q07 새 단위 — 얼린 적합 ∪ 앞서 기록한 fits/Q07-*.json 에 없는 key_mx 단위만 비엄격 적합 한 번 · 부모가 기록하고 다시 적합하지 않는다
     [선언] key_mx 만 적합한다(V1 = LTD 대 M_−i · C3 = β) — key_spx(A4)는 적합하지 않아 A1~A4 는 원장 팔이 아니다.
     [선언] 새 적합은 자식 결과 옆 파일(allow_nan=True · 얼린 묶음 파일과 같은 쓰기)로 넘긴다 — 결과 JSON 은 NaN 을 쓰지 않기 때문이다.
  ④ x-bmrot verify_pins 생략(안의 repro_gate 가 수익을 계산한다 — 울타리로도 막는다)
  ⑤ 새 달 Eg — eg_q5 --pit-gics 로 굽고 m 달만 쓴다(P3 파일은 바이트 그대로 되돌린다) · 결정 때 Wd.eg_scores("pitgics") 표에 더한다
  ⑥ 스냅숏 경로 = build_root + cut_and_blank ⑥-cut(d_m 뒤 날짜는 가격 격자에 없다) · ⑥b(index_history 에 m 이 없으면 빈 행 → 랩의 이월)
     [선언] bench_px.json 의 n 도 자른 길이로 맞춘다(얼린 코드는 읽지 않는다 · 모양만).
     [선언] _pit_px_cache.json 과 index_history.months 는 전방에서만 d_m · m 에서 자른다(짝으로) — 짝맞춤 B 는 캐시에서 d_next 하루만 빼고
       명단은 그대로 둔다(cut_and_blank 주석 · 표본 안 index_history 의 미래 멤버 기간과 잘린 캐시가 맞대이면 얼린 load_prices 의
       재사용 검사가 승계 형제를 빼서 x-bmrot 이 갈린다 — 실측). 전방 변환 그대로의 표본 안 결과는 짝맞춤 F 가 달 목록으로 남긴다.
  ⑦ QF06 x-bmrot 격자 빈 자리 — d_next 를 pxd_dates · pit_px.dates 끝에 붙이고 sd 목록마다 null(그날 가격은 읽지 않는다)
울타리(fence) — 자식 과정에서 수익 엔진(경로 · 펀드 · 평가 · 교체 장부 · 공개 회계)을 부르면 예외가 난다. 표본 안 수익 · 초과 · IR 을
  계산하지도 찍지도 않는다. 짝맞춤은 목표 해시 · 신호 달 목록 · 상태에서 나온 개수만 비교한다.

  python build/qfwd_adapter.py selftest                          # 합성 자료만 — 자르기/빈 자리 · blob sha1 · 울타리 · canon/seal · 해시 조립
  python build/qfwd_adapter.py parity [--tier ABF|A|B|F] [--workers 3] [--months 2020-03,2026-06] [--out PATH] [--keep]
                                                                 # A 틀 동일성 · B 전방 경로(얼린 목표와 비트 단위) · F 전방 판 보기(오류 0 · 차이는 달 목록)
  python build/qfwd_adapter.py parity-summary [PATH]             # 결과 → 마크다운(러너 잡 요약용 · 해시 앞 16자와 개수만)
  python build/qfwd_adapter.py probe-refit [--month 2026-06]     # ③ 적합 경로 재현 점검(그달 45 단위를 다시 적합 · 얼린 적합과 비교)
  python build/qfwd_adapter.py pins [--write]                    # 등록 때 data/_qfwd/pins.json(한 번만)
  python build/qfwd_adapter.py amend --prereg DOC --why TXT [--parity data/_qfwd/amend/parity-<n>.json] [--write]
                                                                 # 수정 등록 핀 사슬의 다음 고리(한 번 쓰기 · 등록과 같은 두 커밋)
  python <root>/build/qfwd_adapter.py --child job.json           # 내부
"""
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import bisect, hashlib, io, json, os, platform, queue, shutil, subprocess, tarfile, tempfile, threading, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# ── 핀(사전등록 §2 와 같다) ────────────────────────────────────────────────
CODE_PIN = "1d81f083a404c68e23d15a649ef6f0a340d4d95c"
BUILD_TREE = "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8"          # git rev-parse 1d81f083:build
P1_PRICE, P1_BASE = "940f0bda99ae1cc99299a43a06b30b9fa267d734", "bef4eea8c98572bd05815d44bd0744d9ce7ed370"
SNAP_FILES = ("data/stocks.json", "data/pit_px.json", "data/sd")    # = qbatch_run.SNAP_FILES
P3 = {   # 모든 뿌리에 코드 핀에서 덮는 고정 입력(핀의 blob id)
    "data/_q07_ltd_fits.json":              "1c670bc0a7d76b23fd1e916f842cfb8a20c3295d",
    "data/_eg_q5_scores_pitgics.json":      "21f43d226463f3978982acc077fbca1576780f33",
    "data/_eg_q5_scores_pitgics_pre.json":  "cb96d4bf7cd35786c0b69d369df0a317db137373",
    "data/_eg_q5_scores.json":              "2868509a502b5104e49d378457451f80eb694d17",
    "data/pit_gics_sectors.json":           "4b20f0e6a02595ec81db4ceaa877afe5628201e8",
    "data/pit_gics.json":                   "f4163293cc92f1386ef5c5f31521d6d302a5c228",
    "data/mech_episodes.json":              "d67a2a74b486aff7f3a46d0f2a9bebe104df669f",
    "data/_eg_best.json":                   "cc58f30c84886554c76fecf6df5dc85974eb09f1",
    "data/_eg30plus.json":                  "c205f1365e924ebf097b200042133369d7de3f3d"}
FROZEN_BLOBS = {  # 자식이 root/build 에서 단언(sha1(b"blob %d\0" + 바이트))
    "build/qbatch_core.py": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "build/q_ltd.py": "2a379df3cc1cde7297be085d0dd4763fbef6f5b6",
    "build/q_netper.py": "29cc446faff92cdd192bde8638425beac9515b29", "build/q_corrsurp.py": "d32a270e2db0682f8b940ffe647607d15b57ba52",
    "build/q_switch.py": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5", "build/q_bmrot_leg.py": "6dea37bc9c470a8a50ebd7a9462cbb3b67e3ead2",
    "build/eg30plus.py": "5688b266adece152d2dc72f911bb7a6ac977d628", "build/qg_lab.py": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea",
    "build/pit_panel.py": "ae044a5d3b8af4b6b8aee12d3879f5c97d4885fb", "build/pit_quarantine.py": "329e5d9ff15be4c07052921dfff9a41afbcc2513",
    "build/stoploss.py": "e2408e98d03216146cf809d6643c68947130c727", "build/tech_backtest.py": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
    "build/rally_pattern.py": "25bbe121aec76be3a54c62a5bb5567c63666cbfa", "build/index_members.py": "7850ef55f5b89583b24e190b250a14c897c93395",
    "build/pit_backtest.py": "54c00f490ee46fc884556ea1f0f97943e986321c", "build/eg_q5.py": "46d012ac28d4164aa68a38ddcf3e732c507d341a",
    "build/pit_gics.py": "ed945d3ca2d1253c02601058dc4d3092c00e81f7", "build/mech_episodes.py": "161080fd9244c060a7a94c559044de3e3ddcc27c"}
ENV_PIN = {"python": (3, 12), "numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6",
           "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
# pandas 는 선택이 아니다: eg30plus → qg_lab → stoploss → rally_pattern 이 부른다(_qbatch.json.versions = pandas 3.0.6).
EST_HASH_PIN = "d150aaab6bf031159a6203586f4edd42a530a94a1a0a37a56af3740c407b146f"   # q_ltd.EST_HASH(판 의존)
FITS_MANIFEST_PIN = "d89f00d2a7fc501251bd0c8a0112b8a01bf64d810e0741ad1abeca60c2fb7655"
M0_FWD, ENTRY_DAY = "2026-09", "2026-10-30"
SPDR9 = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
PREREG = "build/PREREG-2026-09-26-QFWD.md"
QFWD_FILES = ("build/qfwd_adapter.py", "build/qfwd_ledger.py", "build/qfwd_check.py", "build/qfwd_judge.py", ".github/workflows/qfwd-ledger.yml")
ADAPTER_REL_ = "build/qfwd_adapter.py"
LEDGER_FILES = ("decisions.jsonl", "books.jsonl", "market.jsonl", "px_capture.jsonl", "calendar.jsonl")
QFWD_DIR = os.path.join("data", "_qfwd")
PARITY_OUT = os.path.join(QFWD_DIR, "parity.json")
AMEND_DIR = os.path.join(QFWD_DIR, "amend")       # 수정 등록 핀 사슬 — amend/pins-<n>.json · amend/parity-<n>.json(한 번 쓰기)
FORM0_IS, HOLD1_IS = "2016-08", "2026-08"          # 표본 안 기본값(qbatch_core.FORM0 · HOLD1)
Q06_SIGNAL = ("2016-11", "2018-03", "2018-04", "2018-10", "2018-11", "2019-01", "2020-05", "2020-07", "2020-09", "2020-10", "2020-11",
              "2021-01", "2021-03", "2021-12", "2022-01", "2022-02", "2022-03", "2022-04", "2022-05", "2022-07", "2026-06", "2026-07")
PARITY = {  # 명세 §6 표 그대로 — 부모가 저장소 HEAD 의 data/_qbatch.json 과 한 번 더 맞춘다(_wants)
    "Q07_V1": "c1ff6f6f017e4ecb2936005ce0a160f95daa5ea23d8fe14d2c7a0aa648f658f8",
    "Q07_C3": "f2fe91afd089dd517727093ffd38bc5ce01b4827f5dfe9d1f320eb1941fd5bd0",
    "Q07_est": EST_HASH_PIN, "Q07_fits": FITS_MANIFEST_PIN, "Q07_units": 3688,
    "Q08_V1": "976e2216f81a6677c2cd7f752d4549e6a92e0a774b541b75ce702ef503c69519",
    "Q08_C3": "f3e0aa36b1d02d523d85612ce90d22c4a43a4fed54f1bf1eee07edd4970442e3",
    "XBM": "34cc8bb5c4ec6ad30d678f5b5fa695b3d0caab679d35e0c36b969a3368c63e2e",
    "XBM_px": "d7ddb2001cc8f556f80078adfaf37c1e1e504d33a7d521dd36c88763b94a6deb",
    "XBM_cache_blob": "f8c1a16ba22c89f54999cf4291807feb30c53225",
    "XBM_pub_blob": "cc67b1bb142593d60e8143643aae578a146bd7da",
    "Q06": "3cb8cc4aafa13b23814285a13708dda1c43ba9f4bb47a899fe90c1b36a394dab",
    "V0_BL": "132008e66ddf2ef85ea3acf408ae213641f92a0a0a4f7ea3118b6963d2a3c077",
    "V0_LT": "ec0a2aa43f1efffa3d59b5d5b78268153a2bf7f36947ab2ed6345c61c0370202",
    "Q06_signal": list(Q06_SIGNAL),
    "Q06_n_switch": {"st": 23, "s1": 25, "s2": 18},
    "Q06_n_low": {"s1": 35, "s2": 13}}
CUT_FILES = ("data/stocks.json", "data/pit_px.json", "data/assets.json", "data/bench_px.json", "data/_pit_px_cache.json",
             "data/index_history.json")      # + data/sd/ — 짝맞춤 B 가 달마다 원본으로 되돌리는 것
TIMEOUT = {"archive": 600, "bake_eg": 600, "decide": 1800, "parityA": 1800, "parityB_month": 1800}
# [선언] 자식 시간 제한의 합(뿌리 600 + 굽기 600 + 결정 1800 = 50분)은 원장의 실행 예산(qfwd_ledger.BUDGET_SEC)이 다시 자르고,
#   예산은 워크플로 잡 시간(90분)보다 20분 넘게 짧다 — 잡이 잘려 시도 기록 없이 사라지는 일이 없다(검토 2026-09-25).
CARD_ORDER = ("V0", "QF07", "QF08", "QF06")
FENCE = {
    "qbatch_core": ("stock_path", "fund_from_path", "etf_path", "evaluate", "blind_smoke", "Ctx.V0", "Ctx.stock_fr", "Ctx.etf_fr"),
    "qg_lab": ("World.sleeve", "World.evaluate"),
    "eg30plus": ("World.run", "quick", "summary", "step_stats", "mech_frame", "placebos"),
    "q_bmrot_leg": ("leg_path", "leg", "pub_path", "repro_gate", "gate_variants", "monthly_of", "_diff", "dry", "run"),
    "q_switch": ("stock_book", "path_book", "switch_fr", "mix_fr", "blend_fr", "perm_test", "class_s", "offense_v0", "defense",
                 "defense_bmrot", "tbill_book", "spy_book", "run", "dry"),
    "q_ltd": ("run", "dry", "diag", "gauss_calib"),
    "q_netper": ("run", "dry"),
    "q_corrsurp": ("run", "dry")}
FROZEN_MODS = ("qbatch_core", "qg_lab", "eg30plus", "q_bmrot_leg", "q_switch", "q_ltd", "q_netper", "q_corrsurp")


# ── 작은 도구(표준 라이브러리만) ─────────────────────────────────────────────
def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7]) + k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def months_between(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def quarterly_forms_is():
    """표본 안 편입 41 — qbatch_core.quarterly_forms() 기본값(2016-08 + 분기말 · 보유 끝 2026-08)."""
    ms = months_between(FORM0_IS, mshift(HOLD1_IS, -1))
    return [m for j, m in enumerate(ms) if j == 0 or int(m[5:7]) % 3 == 0]


def blob_sha1(b):
    """git blob id — sha1(b"blob <n>\\0" + 바이트)."""
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    """원장 정본 모양 — 키 정렬 · 비ASCII 그대로 · 빈칸 없음 · NaN 금지(결측 = null)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def seal(rec, seq, prev):
    """사슬 봉인 — seq · prev 를 넣고 sha = sha256(canon(sha 뺀 기록))."""
    r = {k: v for k, v in rec.items() if k != "sha"}
    r["seq"], r["prev"] = int(seq), prev
    r["sha"] = sha256_hex(canon(r).encode("utf-8"))
    return r


def lt_thash(T):
    """q_ltd.thash · q_netper.thash 와 같은 식(JSON 으로 오간 목표에 그대로 쓴다)."""
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def bl_thash_parts(parts):
    """q_bmrot_leg.thash 를 달별 조각으로 — parts[m] = {키: round(w, 12)}(반올림은 자식이 원래 자료형으로 했다)."""
    return hashlib.sha256(json.dumps({m: {"w": parts[m]} for m in sorted(parts)}, sort_keys=True).encode()).hexdigest()


def sw_hash_obj(o):
    """q_switch.hash_obj 와 같은 식."""
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def env_report():
    """판 기록 — 버전은 불러오지 않고 설치 정보로 읽는다(부모는 numpy 를 불러오지 않는다)."""
    from importlib import metadata
    out = {"python": platform.python_version(), "hashseed": os.environ.get("PYTHONHASHSEED"),
           "blas": os.environ.get("OPENBLAS_NUM_THREADS"), "platform": platform.platform()}
    for n in ("numpy", "scipy", "pandas"):
        try:
            out[n] = metadata.version(n)
        except Exception:
            out[n] = None
    return out


def _rjson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _wjson(path, obj, compact=True, allow_nan=True):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        if compact:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=allow_nan))
        else:
            f.write(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=allow_nan) + "\n")
    os.replace(tmp, path)


def _rbytes(path):
    with open(path, "rb") as f:
        return f.read()


def _wbytes(path, b):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b)


def _git_text(args, repo=REPO, check=True):
    r = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "core.eol=lf"] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("git %s 실패: %s" % (" ".join(args[:2]), (r.stderr or "")[:300]))
    return (r.stdout or "").strip()


def _git_bytes(args, repo=REPO):
    r = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "core.eol=lf"] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s 실패: %s" % (" ".join(args[:2]), r.stderr.decode("utf-8", "replace")[:300]))
    return r.stdout


def _prefetch(repo, commit, paths):
    """부분 복제(blob:none)일 때만 — commit 의 paths 아래 없는 blob 을 한 번에 받는다(qfwd_check.prefetch · 부모 쪽 전용).
    전체 복제이거나 qfwd_check 를 못 부르면(자식 뿌리) 아무것도 안 한다 — git archive 가 게으른 받기로 하나씩 가져온다."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import qfwd_check as _QC
    except Exception:
        return 0
    return _QC.prefetch(repo, [commit], list(paths))


def _archive_extract(repo, commit, paths, dest, timeout=None):
    """git archive(원 blob 바이트) → tar 파일(시간 제한 · 관이 막혀 멈추지 않게) → 표준 tarfile 로 dest 에 푼다 · 푼 파일 수."""
    timeout = timeout or TIMEOUT["archive"]
    _prefetch(repo, commit, paths)
    fd, tp = tempfile.mkstemp(prefix="qfwd_ar_", suffix=".tar", dir=os.path.dirname(os.path.abspath(dest)))
    os.close(fd)
    try:
        cmd = ["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive", "--format=tar", "-o", tp, commit, "--"] + list(paths)
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError("git archive %s %s 시간 초과(%ds)" % (commit[:8], paths, timeout))
        if r.returncode != 0:
            raise RuntimeError("git archive %s %s 실패: %s" % (commit[:8], paths, r.stderr.decode("utf-8", "replace")[:300]))
        n = 0
        with tarfile.open(tp, mode="r:") as tf:
            for ti in tf:
                tf.extract(ti, dest, filter="data")
                n += 1 if ti.isfile() else 0
        return n
    finally:
        try:
            os.remove(tp)
        except OSError:
            pass


# ── ⑥ 뿌리 ───────────────────────────────────────────────────────────────
def build_root(data_commit, code_pin, tmpdir, *, price_commit=None, repo=REPO, timeout=None):
    """tmpdir/root = <data_commit>:data/ (+ price_commit 의 가격 판) + P3 덮어쓰기 + <code_pin>:build/ + 돌고 있는 어댑터.
    timeout = git archive 한 번의 시간 제한(원장이 실행 예산으로 자른다).
    돌려준다: (root, 보고{data_commit, price_commit, tree_data, p3_ok, frozen_ok, n_files, adapter_blob})."""
    t0 = time.time()
    root = os.path.join(tmpdir, "root")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)
    if _git_text(["rev-parse", "%s:build" % code_pin], repo) != BUILD_TREE and code_pin == CODE_PIN:
        raise RuntimeError("코드 핀의 build 트리가 %s 가 아니다" % BUILD_TREE[:12])
    n = _archive_extract(repo, data_commit, ["data/"], root, timeout=timeout)
    qd = os.path.join(root, "data", "_qfwd")
    if os.path.isdir(qd):
        shutil.rmtree(qd)                       # 원장 기록 자신은 결정 입력이 아니다
    if price_commit:
        shutil.rmtree(os.path.join(root, "data", "sd"), ignore_errors=True)
        n += _archive_extract(repo, price_commit, list(SNAP_FILES), root, timeout=timeout)
    p3_ok = True
    for rel, want in P3.items():
        b = _git_bytes(["cat-file", "blob", "%s:%s" % (code_pin, rel)], repo)
        if blob_sha1(b) != want:
            raise RuntimeError("P3 %s blob %s ≠ %s" % (rel, blob_sha1(b)[:12], want[:12]))
        _wbytes(os.path.join(root, *rel.split("/")), b)
        p3_ok = p3_ok and blob_sha1(_rbytes(os.path.join(root, *rel.split("/")))) == want
    bd = os.path.join(root, "build")
    if os.path.exists(bd):
        shutil.rmtree(bd)
    _archive_extract(repo, code_pin, ["build/"], root)
    me = _rbytes(os.path.abspath(__file__))
    _wbytes(os.path.join(bd, "qfwd_adapter.py"), me)
    frozen_ok = all(blob_sha1(_rbytes(os.path.join(root, *rel.split("/")))) == want for rel, want in FROZEN_BLOBS.items())
    if not (p3_ok and frozen_ok):
        raise RuntimeError("뿌리 단언 실패(p3 %s · 얼린 blob %s)" % (p3_ok, frozen_ok))
    os.makedirs(os.path.join(tmpdir, "tmp"), exist_ok=True)
    rep = {"data_commit": data_commit, "price_commit": price_commit, "tree_data": _git_text(["rev-parse", "%s:data" % data_commit], repo),
           "code_pin": code_pin, "p3_ok": p3_ok, "frozen_ok": frozen_ok, "n_files": n, "adapter_blob": blob_sha1(me),
           "sec": round(time.time() - t0, 1)}
    if price_commit:
        rep["tree_price"] = {p: _git_text(["rev-parse", "%s:%s" % (price_commit, p)], repo) for p in SNAP_FILES}
    return root, rep


def compare_tree(root, other, sub="data"):
    """두 뿌리의 sub/ 를 줄바꿈(CRLF → LF)만 맞춰 비교 — P1 뿌리 = $TEMP/snap_wt 확인용(기록만)."""
    def walk(base):
        out = {}
        b0 = os.path.join(base, sub)
        for dp, _dn, fn in os.walk(b0):
            for f in fn:
                p = os.path.join(dp, f)
                out[os.path.relpath(p, base).replace("\\", "/")] = p
        return out
    a, b = walk(root), walk(other)
    same, diff = 0, []
    for rel in sorted(set(a) & set(b)):
        x, y = _rbytes(a[rel]), _rbytes(b[rel])
        if x == y or x.replace(b"\r\n", b"\n") == y.replace(b"\r\n", b"\n"):
            same += 1
        else:
            diff.append(rel)
    return {"n_root": len(a), "n_other": len(b), "same": same, "diff": diff[:20], "n_diff": len(diff),
            "only_root": sorted(set(a) - set(b))[:20], "n_only_root": len(set(a) - set(b)),
            "only_other": sorted(set(b) - set(a))[:20], "n_only_other": len(set(b) - set(a))}


# ── ⑥-cut · ⑥b · ⑦ ──────────────────────────────────────────────────────
def cut_and_blank(root, m, d_m, d_next, *, carry_ih=True, src=None, blank=True, cache="cut", ih_cut=None):
    """월 m 의 뿌리 변환(모든 카드 공용) — ⑥-cut: d_m 뒤 날짜를 가격 격자에서 없앤다 · ⑥b: index_history 이월 행 · ⑦: d_next 빈 자리.
    src 가 있으면 그 뿌리의 원본 파일을 읽어 root 에 쓴다(짝맞춤 B 가 달마다 원본으로 되돌리는 방식). 돌려준다: 보고.
    cache — _pit_px_cache.json(x-bmrot 의 편출 가격 지도 · pit_backtest.load_prices) 처리:
      "cut"(전방) = 종목마다 날짜 ≤ d_m 만 · "blank"(짝맞춤 B) = d_next 하루만 뺀다(⑦ — 그날 가격은 어느 출처에서도 읽지 않는다).
      [선언] 짝맞춤 B 가 캐시를 자르지 않는 이유: load_prices 의 재사용(①) · 꼬리 절단(②) · 크기(③) · CIK 승계 검사는 캐시 계열을
      index_history 의 멤버 기간과 맞댄다. 표본 안 판의 index_history 는 m 뒤 멤버 기간(미래)을 담고 있고 얼린 굽기는 그 판에서
      자르지 않은 캐시로 검사했다 — 캐시만 자르면 승계 형제(BBWI · CPRI · LUMN · UA)가 «재사용 의심» 으로 빠져 x-bmrot 목표가
      갈린다(2026-09-25 짝맞춤 B 실측: 2016-08 KORS · LB · UA.C · 2020-03 CTL · ALLE). 전방 판에는 d_m 뒤 멤버 기간이 없으므로
      제때 고른 판에서 "cut" 은 d_m 뒤 값(보통 없음 · 늦은 판이나 장중 막대)만 없앤다.
    ih_cut — index_history.months 에서 m 뒤 달을 없앤다(⑥-cut 의 멤버십 쪽 · 기본 = cache 가 "cut" 일 때).
      [선언] 늦게 고른 판도 제때 판처럼 «m 까지의 명단» 만 보게 한다(판 V 가 d_m 뒤 며칠을 담으면 index_history 는 m+1 달을 가질 수
      있다 — 매주 토 갱신이 그달 명단을 먼저 싣는다). 캐시 "cut" 과 짝으로만 쓴다(한쪽만 자르면 위 재사용 검사가 갈린다).
      짝맞춤 F(전방 판 보기)가 표본 안 120달에서 이 짝을 태워 얼린 목표와의 차이를 달 목록으로 남긴다."""
    if cache not in ("cut", "blank"):
        raise ValueError("cache %r" % cache)
    if ih_cut is None:
        ih_cut = cache == "cut"
    drop_off_grid = cache == "cut"
    # [선언] 전방 판 보기에서는 격자 길이가 다른 sd 의 종목을 stocks.json 명단에서 빼고 그 sd 를 뿌리에 두지 않는다 —
    #   얼린 pit_panel.load_world 는 길이를 보지 않고 sd 를 읽어 날짜가 어긋난 가격을 조용히 쓰기 때문이다(pit_backtest.load_prices 만 뺀다).
    #   제때 판은 원장의 검증 2(모든 sd 길이 = 격자)를 넘으므로 아무것도 빠지지 않는다 — 원장의 막힘 대체(degraded)에서만 이름이 빠지고
    #   원장이 그 이름을 기록한다. P1 판(짝맞춤)에는 그런 sd 가 0 개다(2026-09-25 실측).
    src = src or root
    rp = lambda rel: os.path.join(src, *rel.split("/"))
    wp = lambda rel: os.path.join(root, *rel.split("/"))
    assert d_m[:7] == m, "d_m %s 이 %s 달이 아니다" % (d_m, m)
    assert (not blank) or (d_next and d_next > d_m and d_next[:7] > m), "d_next %s 가 d_m %s 뒤 다음 달이 아니다" % (d_next, d_m)
    rewritten = []
    S = _rjson(rp("data/stocks.json"))
    D = list(S["pxd_dates"])
    assert d_m in D, "d_m %s 이 pxd_dates 에 없다" % d_m
    n = D.index(d_m) + 1
    tail = [d_next] if blank else []
    S["pxd_dates"] = D[:n] + tail
    # sd/<t>.json — 격자 길이 목록(pxd · vd · hd · ld)
    sdn, sd_fields, sd_off = 0, set(), []
    tick = {s["t"] for s in S.get("stocks") or []}
    sdir = os.path.join(src, "data", "sd")
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".json"):
            continue
        d = _rjson(os.path.join(sdir, fn))
        if len(d.get("pxd") or []) != len(D):
            sd_off.append(fn[:-5])              # 격자 길이가 다른 sd
            if drop_off_grid and fn[:-5] in tick:
                p_ = os.path.join(root, "data", "sd", fn)
                if os.path.exists(p_):
                    os.remove(p_)
                continue
        for k, v in d.items():
            if isinstance(v, list) and len(v) == len(D):
                d[k] = v[:n] + ([None] if blank else [])
                sd_fields.add(k)
        _wjson(os.path.join(root, "data", "sd", fn), d)
        sdn += 1
    dropped = sorted(t for t in sd_off if t in tick) if drop_off_grid else []
    if dropped:
        S["stocks"] = [s for s in S["stocks"] if s["t"] not in set(dropped)]
    _wjson(wp("data/stocks.json"), S)
    rewritten.append("data/stocks.json")
    # pit_px.json — dates · p(짧은 배열은 NaN 으로 읽힌다)
    P = _rjson(rp("data/pit_px.json"))
    assert P.get("dates") == D, "pit_px.json 격자 ≠ pxd_dates"
    P["dates"] = D[:n] + tail
    for k, obj in P["px"].items():
        i0 = int(obj.get("i0") or 0)
        obj["p"] = list(obj.get("p") or [])[:max(0, n - i0)]
    _wjson(wp("data/pit_px.json"), P)
    rewritten.append("data/pit_px.json")
    # assets.json — dates · px · open 자르기 · macro · div 는 날짜 ≤ d_m · n_days
    A = _rjson(rp("data/assets.json"))
    ad = list(A["dates"])
    na = bisect.bisect_right(ad, d_m)
    for blk in ("px", "open"):
        for k, s in (A.get(blk) or {}).items():
            assert len(s) == len(ad), "assets.%s.%s 길이 ≠ dates" % (blk, k)
            A[blk][k] = s[:na]
    for blk in ("macro", "div"):
        for k, s in (A.get(blk) or {}).items():
            A[blk][k] = {dd: v for dd, v in s.items() if dd <= d_m}
    A["dates"] = ad[:na]
    if "n_days" in A:
        A["n_days"] = na
    _wjson(wp("data/assets.json"), A)
    rewritten.append("data/assets.json")
    # bench_px.json — dates · series[*].px
    B = _rjson(rp("data/bench_px.json"))
    bd = list(B["dates"])
    nb = bisect.bisect_right(bd, d_m)
    for k, s in B["series"].items():
        assert len(s["px"]) == len(bd), "bench_px.%s 길이 ≠ dates" % k
        s["px"] = s["px"][:nb]
    B["dates"] = bd[:nb]
    if B.get("n") == len(bd):
        B["n"] = nb
    _wjson(wp("data/bench_px.json"), B)
    rewritten.append("data/bench_px.json")
    # _pit_px_cache.json — "cut": 종목 사전마다 날짜 ≤ d_m · "blank": d_next 하루만 뺀다
    C = _rjson(rp("data/_pit_px_cache.json"))
    if cache == "cut":
        keep = lambda dd: dd <= d_m
    else:
        keep = lambda dd: dd != d_next
    n_cache_drop = 0
    C2 = {}
    for t, ser in C.items():
        if isinstance(ser, dict):
            s2 = {dd: v for dd, v in ser.items() if keep(dd)}
            n_cache_drop += len(ser) - len(s2)
            C2[t] = s2
        else:
            C2[t] = ser
    _wjson(wp("data/_pit_px_cache.json"), C2)
    rewritten.append("data/_pit_px_cache.json")
    # ⑥-cut(멤버십) · ⑥b index_history 이월
    H = _rjson(rp("data/index_history.json"))
    months = H.get("months") or {}
    ih_drop = sorted(k for k in months if k > m) if ih_cut else []
    for k in ih_drop:
        del months[k]
    if m in months:
        ih = "m"
    elif carry_ih and mshift(m, -1) in months:
        months[m] = {}
        ih = "m-1"
    else:
        raise RuntimeError("index_history 에 %s 도 %s 도 없다" % (m, mshift(m, -1)))
    if ih == "m-1" or ih_drop:
        H["months"] = months
        _wjson(wp("data/index_history.json"), H)
        rewritten.append("data/index_history.json")
    elif os.path.abspath(src) != os.path.abspath(root):
        shutil.copyfile(rp("data/index_history.json"), wp("data/index_history.json"))
    return {"n_cut": n, "d_m": d_m, "d_next": d_next if blank else None, "ih": ih, "files_rewritten": rewritten,
            "sd_n": sdn, "sd_fields": sorted(sd_fields), "n_assets": na, "n_bench": nb, "cache": cache, "n_cache_drop": n_cache_drop,
            "ih_cut": bool(ih_cut), "ih_drop": ih_drop, "sd_off_grid": sd_off[:50], "n_sd_off_grid": len(sd_off),
            "dropped_off_grid": dropped}


# ── 자식 과정(부모 쪽) ─────────────────────────────────────────────────────
def _child_env(tmpdir):
    env = {k: v for k, v in os.environ.items() if k.upper() != "Q07_FITS" and not k.upper().startswith("QBATCH_")}
    t = os.path.join(tmpdir, "tmp")
    os.makedirs(t, exist_ok=True)
    env.update({"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "PYTHONIOENCODING": "utf-8", "TEMP": t, "TMP": t, "TMPDIR": t})
    return env


def _run_child(root, tmpdir, job, timeout, tag):
    """job.json 을 쓰고 root/build/qfwd_adapter.py --child 를 cwd=root 로 돌린다. 로그는 tmpdir/child-<tag>.log(커밋하지 않는다)."""
    tag = "".join(c if (c.isalnum() or c in "-_") else "_" for c in tag)
    jp, out, log = (os.path.join(tmpdir, "%s-%s.%s" % (a, tag, b)) for a, b in (("job", "json"), ("out", "json"), ("child", "log")))
    for p in (out, out + ".fits.json"):
        if os.path.exists(p):
            os.remove(p)
    _wjson(jp, dict(job, out=out), compact=False, allow_nan=False)
    t0 = time.time()
    try:
        with open(log, "w", encoding="utf-8") as lf:
            r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(root, "build", "qfwd_adapter.py"), "--child", jp],
                               cwd=root, env=_child_env(tmpdir), stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "timeout %ds" % timeout, "outcome": "timeout", "log": log, "sec": round(time.time() - t0, 1)}
    res = _child_result(rc, _rjson(out) if os.path.exists(out) else None)
    res["log"], res["sec_wall"] = log, round(time.time() - t0, 1)
    return res


def _child_result(rc, res):
    """자식의 종료 코드 · 결과 파일(없으면 None) → 결과.
    [선언] 신호로 죽은 자식(rc < 0 — Linux 러너의 메모리 부족 SIGKILL 은 파이썬 MemoryError 가 아니다)은 outcome «memory» —
      원장은 같은 판으로 다시 한다(오류 셈에 넣지 않는다 · 사전등록 §5 · 검토 2026-09-25)."""
    killed = rc < 0
    if res is None:
        res = {"ok": False, "why": "결과 파일 없음(rc %d%s)" % (rc, " · 신호로 죽음" if killed else ""),
               "outcome": "memory" if killed else "error"}
    res["rc"] = rc
    if rc != 0 and res.get("ok"):
        res["ok"], res["why"] = False, "rc %d" % rc
    if killed and not res.get("ok"):
        res["outcome"] = "memory"
    return res


def _grid_of(root):
    D = _rjson(os.path.join(root, "data", "stocks.json"))["pxd_dates"]
    return D[-2], D[-1]


def bake_eg(root, m, d_m, d_next, tmpdir, *, timeout=None, tag=None):
    """⑤ 굽기 — 자른 뿌리에서 eg_q5 --pit-gics(F1_ = m) · months[m] 만 · P3 파일은 바이트 그대로 되돌린다.
    돌려준다: {"ok", "m", "scores", "n", "fin_lookups", "sec"}."""
    p3 = os.path.join(root, "data", "_eg_q5_scores_pitgics.json")
    raw = _rbytes(p3)
    assert blob_sha1(raw) == P3["data/_eg_q5_scores_pitgics.json"], "굽기 전 P3 Eg 파일이 핀과 다르다"
    try:
        r = _run_child(root, tmpdir, {"op": "bake_eg", "m": m, "d_m": d_m, "d_next": d_next}, timeout or TIMEOUT["bake_eg"],
                       tag or "bake-%s" % m)
    finally:
        if blob_sha1(_rbytes(p3)) != P3["data/_eg_q5_scores_pitgics.json"]:
            _wbytes(p3, raw)                    # 자식이 죽어 못 되돌렸으면 부모가 되돌린다
            r_fix = True
        else:
            r_fix = False
    if r_fix and isinstance(r, dict):
        r["p3_restored_by_parent"] = True
    return r


def eg_record(bake, snap=None, adapter_blob=None, env=None):
    """eg/<m>-<V8>.json 모양(원장이 쓴다 · 짝맞춤은 임시로 쓴다)."""
    sc = bake["scores"]
    return {"v": 1, "m": bake["m"], "snap": snap, "code_pin": CODE_PIN, "adapter_blob": adapter_blob, "env": env,
            "n": len(sc), "fin_lookups": bake.get("fin_lookups"), "scores": sc, "sha": sha256_hex(canon(sc).encode("utf-8"))}


def decide(cards, m, root, tmpdir, *, fwd_eg=None, fwd_fits=None, mode="forward", d_m=None, d_next=None, timeout=None, tag=None,
           refit_probe=False, no_new_fits=False, withhold_fits=0):
    """결정 자식 하나(World 하나 · 카드 순서 V0 → QF07 → QF08 → QF06). cut_and_blank 뒤의 뿌리를 받는다.
    fwd_eg = {달: eg 파일 경로}(V0 가 쓰는 모든 전방 편입의 Eg) · fwd_fits = [fits/Q07-*.json 경로].
    withhold_fits = K(되풀이 전용 · 원장 실행은 넘기지 않는다) — 그달 key_mx 단위 가운데 이름순 첫 K 를 얼린 적합에서 빼 «새 단위» 로
      만든다 → ③ 의 새 적합 · 기록 · 다시 읽기 경로를 실제 자료로 끝까지 태운다(검토 2026-09-25 — 그 경로는 한 번도 돌지 않았다).
    돌려준다: {"ok", "cards": {카드: {"targets", "targets_sha", "diag", "states"?}}, "new_fits": {...}|None, "new_fits_manifest", "env", "sec"}."""
    if isinstance(cards, str):
        cards = [cards]
    cards = [c for c in CARD_ORDER if c in set(cards)]
    if d_m is None or d_next is None:
        d_m, d_next = _grid_of(root)
    job = {"op": "decide", "m": m, "d_m": d_m, "d_next": d_next, "cards": cards, "mode": mode,
           "fwd_eg": {k: os.path.abspath(v) for k, v in sorted((fwd_eg or {}).items())},
           "fwd_fits": [os.path.abspath(p) for p in (fwd_fits or [])], "refit_probe": bool(refit_probe),
           "no_new_fits": bool(no_new_fits), "withhold_fits": int(withhold_fits or 0)}
    t0 = time.time()
    r = _run_child(root, tmpdir, job, timeout or TIMEOUT["decide"], tag or "decide-%s" % m)
    if not r.get("ok"):
        return r
    for c, rec in r["cards"].items():
        rec["targets_sha"] = {nm: sha256_hex(canon(t).encode("utf-8")) for nm, t in rec["targets"].items()}
    nf = None
    if r.get("new_fits_file"):
        with open(r["new_fits_file"], encoding="utf-8") as f:
            nf = json.load(f)
    return {"ok": True, "m": m, "mode": mode, "cards": r["cards"], "new_fits": nf, "new_fits_manifest": r.get("new_fits_manifest"),
            "n_new_fits": r.get("n_new_fits", 0), "env": r.get("env"), "sec": round(time.time() - t0, 1), "sec_child": r.get("sec"),
            "log": r.get("log")}


# ── 자식 과정(자식 쪽) ─────────────────────────────────────────────────────
def _wall(name):
    def fenced(*a, **k):
        raise RuntimeError("QFWD fence: 수익 계산 금지 — %s" % name)
    fenced.qfwd_fence = name
    return fenced


def _fence(mods):
    """울타리 — FENCE 의 속성을 모두 예외로 바꾼다(없는 속성은 닫힌 실패). 바꾼 개수."""
    n = 0
    for mname, attrs in FENCE.items():
        mod = mods[mname]
        for a in attrs:
            owner, _, leaf = a.rpartition(".")
            tgt = getattr(mod, owner) if owner else mod
            if not hasattr(tgt, leaf):
                raise RuntimeError("QFWD fence: %s.%s 가 없다" % (mname, a))
            setattr(tgt, leaf, _wall("%s.%s" % (mname, a)))
            n += 1
    return n


def _skip_pins(ctx):
    return {"skipped": "QFWD ④"}


def _assert_env():
    import numpy, scipy, pandas
    bad = []
    if tuple(sys.version_info[:2]) != ENV_PIN["python"]:
        bad.append("python %d.%d" % tuple(sys.version_info[:2]))
    for nm, mod in (("numpy", numpy), ("scipy", scipy), ("pandas", pandas)):
        if mod.__version__ != ENV_PIN[nm]:
            bad.append("%s %s ≠ %s" % (nm, mod.__version__, ENV_PIN[nm]))
    for k in ("PYTHONHASHSEED", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(k) != ENV_PIN[k]:
            bad.append("%s=%s" % (k, os.environ.get(k)))
    if sys.flags.hash_randomization:
        bad.append("hash_randomization")
    if bad:
        raise RuntimeError("QFWD 환경 핀 불일치: " + " · ".join(bad))
    return {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__,
            "hashseed": os.environ.get("PYTHONHASHSEED"), "blas": os.environ.get("OPENBLAS_NUM_THREADS"), "platform": platform.platform()}


def _assert_frozen(build_dir):
    bad = [rel for rel, want in FROZEN_BLOBS.items()
           if blob_sha1(_rbytes(os.path.join(os.path.dirname(build_dir), *rel.split("/")))) != want]
    if bad:
        raise RuntimeError("얼린 blob 불일치: %s" % bad)


def _import_frozen():
    import importlib
    return {n: importlib.import_module(n) for n in FROZEN_MODS}


def _bl_part(T):
    """q_bmrot_leg.thash 한 달 조각 — 원래 자료형 그대로 round(·, 12)(numpy float64 의 반올림은 파이썬 float 과 다를 수 있다)."""
    return {k: float(round(v, 12)) for k, v in sorted(T["w"].items())}


def _tj(T):
    """목표 {"w", "names"} → JSON 원형(float · str)."""
    return {"w": {k: float(v) for k, v in T["w"].items()}, "names": {k: str(v) for k, v in T["names"].items()}}


def _child(job_path):
    with open(job_path, encoding="utf-8") as f:
        job = json.load(f)
    out = job["out"]
    t0 = time.time()
    try:
        res = _child_run(job)
        res.setdefault("ok", True)
    except BaseException as e:                  # 닫힌 실패 — 무엇이든 결과 파일에 ok=false 로 남긴다
        traceback.print_exc()
        res = {"ok": False, "why": ("%s: %s" % (type(e).__name__, e))[:300],
               "outcome": "memory" if isinstance(e, MemoryError) else "error"}     # 원장: timeout · memory 는 같은 V 로 다시
    res["sec"] = round(time.time() - t0, 1)
    try:
        txt = json.dumps(res, allow_nan=False, sort_keys=True)
    except ValueError:
        txt = json.dumps({"ok": False, "why": "결과에 NaN · Inf 가 있다", "outcome": "error"}, sort_keys=True)
        res = {"ok": False}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    return 0 if res.get("ok") else 3


def _child_run(job):
    build_dir = os.path.dirname(os.path.abspath(__file__))
    if build_dir not in sys.path:
        sys.path.insert(0, build_dir)
    op = job["op"]
    env = _assert_env()
    _assert_frozen(build_dir)
    if op == "bake_eg":
        sys.argv = ["eg_q5.py", "--pit-gics"]   # ⑤ — eg_q5 는 불러올 때 PIT_GICS 를 읽는다
    mods = _import_frozen()
    nf = _fence(mods)
    LT = mods["q_ltd"]
    if LT.EST_HASH != EST_HASH_PIN:
        raise RuntimeError("q_ltd.EST_HASH %s ≠ 핀 %s(판 차이)" % (LT.EST_HASH[:16], EST_HASH_PIN[:16]))
    print("QFWD 자식 %s · 울타리 %d · 환경 %s/%s/%s" % (op, nf, env["numpy"], env["scipy"], env["pandas"]), flush=True)
    if op == "parityA":
        res = _op_parityA(mods, job)
    elif op == "bake_eg":
        res = _op_bake(mods, job)
    elif op == "decide":
        res = _op_decide(mods, job)
    else:
        raise RuntimeError("모르는 작업 %s" % op)
    res["env"] = env
    res["fence_n"] = nf
    return res


def _op_parityA(mods, job):
    """Tier A — P1 뿌리 · 자르지 않음 · 끼움은 ④ 와 울타리만 · 표본 안 기본값(F1M 2026-07 · HOLD1 2026-08)."""
    import numpy as np
    Q, BL, SW, CS, LT, NP = (mods[n] for n in ("qbatch_core", "q_bmrot_leg", "q_switch", "q_corrsurp", "q_ltd", "q_netper"))
    BL.verify_pins = _skip_pins                  # ④
    sec, got, parts = {}, {}, {}
    t = time.time()
    ctx = Q.Ctx()
    Wd = ctx.Wd
    V0 = ctx.V0_targets
    got["V0_BL"], got["V0_LT"] = BL.thash(V0), LT.thash(V0)
    parts["V0"] = {m: {"t": _tj(V0[m]), "bl": _bl_part(V0[m])} for m in sorted(V0)}
    sec["world_v0"] = round(time.time() - t, 1)
    print("  A · V0 %d 편입" % len(V0), flush=True)
    t = time.time()
    TX, _logx = BL.targets(Wd)
    got["XBM"], got["XBM_px"] = BL.thash(TX), BL.pxhash(Wd, TX)
    got["XBM_cache_blob"] = BL._blob(os.path.join("data", "_pit_px_cache.json"))
    got["XBM_pub_blob"] = BL._blob(os.path.join("data", "strategy_charts.json"))
    parts["XBM"] = {m: {"bl": _bl_part(TX[m]), "n": len(TX[m]["w"])} for m in sorted(TX)}
    sec["xbm"] = round(time.time() - t, 1)
    print("  A · x-bmrot %d 달" % len(TX), flush=True)
    t = time.time()
    st, s1, s2, mon, _sig = CS.states(ctx)
    F = SW.frame(ctx)
    pos = SW.pos_from_monthly(F, st)
    pos_s = "".join(map(str, pos.tolist()))
    got["Q06"] = SW.hash_obj({"pos": pos_s, "src": {"v0": BL.thash(V0), "bmrot": BL.thash(TX)}})
    counts = {}
    for k, m in enumerate(F.months):
        b = int(F.mstart[k + 1]) if k + 1 < len(F.months) else int(F.T)
        counts[m] = b - int(F.mstart[k])
    assert "".join(str(int(st[m])) * counts[m] for m in F.months) == pos_s, "위치 벡터 재구성 실패"
    got["Q06_signal"] = [m for m in F.months if st[m] == 0]
    nsw = {}
    for nm, s in (("st", st), ("s1", s1), ("s2", s2)):
        p = SW.pos_from_monthly(F, s)
        nxt = np.append(p[1:], p[-1])
        nsw[nm] = int((nxt != p).sum())
    got["Q06_n_switch"] = nsw
    low = {"s1": [m for m in F.months if s1[m] == 0], "s2": [m for m in F.months if s2[m] == 0]}
    got["Q06_n_low"] = {k: len(v) for k, v in low.items()}
    parts["Q06"] = {"months": list(F.months), "counts": counts, "st": {m: int(st[m]) for m in F.months},
                    "s1": {m: int(s1[m]) for m in F.months}, "s2": {m: int(s2[m]) for m in F.months}, "low": low}
    sec["q06"] = round(time.time() - t, 1)
    print("  A · Q06 %d 달 · 신호 %d" % (len(F.months), len(got["Q06_signal"])), flush=True)
    t = time.time()
    _rows, fits, stt = LT.fit_all(ctx, verbose=False, strict=True)
    sq = LT.signals(ctx, fits)
    T7, rec = LT.build_targets(ctx, sq)
    gap = LT.v0_check(ctx)
    got["Q07_V1"], got["Q07_C3"] = LT.thash(T7["V1"]), LT.thash(T7["C3"])
    got["Q07_est"], got["Q07_fits"], got["Q07_units"] = LT.EST_HASH, stt.get("manifest"), stt.get("units")
    got["Q07_forms"] = [r["m"] for r in rec]
    got["Q07_v0_gap_ok"] = bool(gap < 1e-12)
    parts["Q07_V1"] = {m: _tj(T7["V1"][m]) for m in sorted(T7["V1"])}
    parts["Q07_C3"] = {m: _tj(T7["C3"][m]) for m in sorted(T7["C3"])}
    sec["q07"] = round(time.time() - t, 1)
    print("  A · Q07 %d 편입 · 단위 %d" % (len(rec), stt.get("units") or 0), flush=True)
    t = time.time()
    T8v, _ = NP.build_q08(ctx, "V1")
    T8c, _ = NP.build_q08(ctx, "C3")
    got["Q08_V1"], got["Q08_C3"] = NP.thash(T8v), NP.thash(T8c)
    parts["Q08_V1"] = {m: _tj(T8v[m]) for m in sorted(T8v)}
    parts["Q08_C3"] = {m: _tj(T8c[m]) for m in sorted(T8c)}
    sec["q08"] = round(time.time() - t, 1)
    print("  A · Q08 %d 편입" % len(T8v), flush=True)
    _wjson(job["parts"], parts, allow_nan=False)
    return {"ok": True, "got": got, "sec_by": sec}


def _op_bake(mods, job):
    """⑤ 굽기 — sys.argv 는 이미 --pit-gics(불러오기 전) · eg_q5.F1_ = m(①) · main() → months[m] · P3 파일 되돌림 + blob 단언."""
    import importlib
    m = job["m"]
    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    p3 = os.path.join(data, "_eg_q5_scores_pitgics.json")
    bak = os.path.join(data, "_eg_q5_scores_pitgics.p3.json")
    raw = _rbytes(p3)
    want = P3["data/_eg_q5_scores_pitgics.json"]
    if blob_sha1(raw) != want:
        raise RuntimeError("굽기 전 P3 Eg 파일 blob 불일치")
    _wbytes(bak, raw)
    EQ = importlib.import_module("eg_q5")
    if not EQ.PIT_GICS or EQ.PRE_FROM is not None:
        raise RuntimeError("eg_q5 가 --pit-gics 로 불러와지지 않았다")
    EQ.F1_ = m                                    # ①(굽기)
    try:
        rc = EQ.main()
        doc = _rjson(p3)
        sc = (doc.get("months") or {}).get(m)
        if sc is None:
            raise RuntimeError("굽기 결과에 %s 달이 없다" % m)
        fin, nmon, rng = doc.get("fin_lookups"), len(doc.get("months") or {}), doc.get("pit_gics_range")
    finally:
        _wbytes(p3, raw)
        if blob_sha1(_rbytes(p3)) != want:
            raise RuntimeError("P3 Eg 파일을 되돌리지 못했다")
        os.remove(bak)
    print("  굽기 %s · %d종 · 달 %d" % (m, len(sc), nmon), flush=True)
    return {"ok": True, "m": m, "scores": sc, "n": len(sc), "fin_lookups": fin, "n_months": nmon, "pit_gics_range": rng, "rc": rc}


def _load_eg(path, mm):
    d = _rjson(path)
    if d.get("m") != mm:
        raise RuntimeError("Eg 파일 %s 의 달 %s ≠ %s" % (os.path.basename(path), d.get("m"), mm))
    sc = d["scores"]
    if "sha" in d and d["sha"] != sha256_hex(canon(sc).encode("utf-8")):
        raise RuntimeError("Eg 파일 %s 의 sha 가 점수와 다르다" % os.path.basename(path))
    return sc


def _known_fits(LT, paths):
    """③ 해석기의 이미 있는 적합 — 얼린 묶음(_pinned · est_hash 단언) ∪ 기록된 fits/Q07-*.json(각각 est_hash · 지문 단언)."""
    pin = LT._pinned()
    if pin is None:
        raise RuntimeError("얼린 적합 묶음(_q07_ltd_fits.json)이 없다")
    known = dict(pin)
    info = {"pinned": len(pin), "files": []}
    file_units = {}
    for p in paths:
        d = _rjson(p)
        if d.get("est_hash") != EST_HASH_PIN:
            raise RuntimeError("적합 파일 %s 의 est_hash 가 핀과 다르다" % os.path.basename(p))
        fs = d.get("fits") or {}
        if d.get("manifest") is not None and LT.manifest(fs) != d["manifest"]:
            raise RuntimeError("적합 파일 %s 의 지문이 내용과 다르다" % os.path.basename(p))
        clash = 0
        for k, v in fs.items():
            file_units.setdefault(k, v)
            if k in known:
                clash += 1
                continue
            known[k] = v
        info["files"].append({"file": os.path.basename(p), "n": len(fs), "clash": clash})
    info["_file_units"] = file_units
    return known, info


def _op_decide(mods, job):
    import numpy as np
    Q, QL, E, BL, CS, LT, NP = (mods[n] for n in ("qbatch_core", "qg_lab", "eg30plus", "q_bmrot_leg", "q_corrsurp", "q_ltd", "q_netper"))
    m, d_m, d_next, mode = job["m"], job["d_m"], job["d_next"], job["mode"]
    if mode not in ("forward", "parityB"):
        raise RuntimeError("모르는 mode %s" % mode)
    cards = [c for c in CARD_ORDER if c in set(job["cards"])]
    if set(job["cards"]) - set(CARD_ORDER):
        raise RuntimeError("모르는 카드 %s" % sorted(set(job["cards"]) - set(CARD_ORDER)))
    m1 = mshift(m, 1)
    sec = {}
    # ① 기간 연장(World 전) · ④
    QL.F1M = m
    Q.HOLD1 = m1
    BL.HOLD1 = m1
    BL.verify_pins = _skip_pins
    t = time.time()
    ctx = Q.Ctx()
    Wd = ctx.Wd
    sec["world"] = round(time.time() - t, 1)
    # ⑤ 주입 — 어떤 score() 호출보다 먼저
    tab = Wd.eg_scores("pitgics")
    fwd = {mm: _load_eg(p, mm) for mm, p in sorted((job.get("fwd_eg") or {}).items())}
    if mode == "parityB":
        if set(fwd) - {m}:
            raise RuntimeError("짝맞춤 B 는 그달 Eg 하나만 넣는다")
        if m in fwd:
            if m not in tab:
                raise RuntimeError("얼린 Eg 에 %s 가 없다" % m)
            del tab[m]
    clash = sorted(set(fwd) & set(tab))
    if clash:
        raise RuntimeError("전방 Eg 달이 얼린 달과 겹친다: %s" % clash)
    for mm, sc in fwd.items():
        if mm <= m:
            tab[mm] = sc
    # 격자 단언
    if Wd.months[-1] != m:
        raise RuntimeError("World 마지막 편입월 %s ≠ %s" % (Wd.months[-1], m))
    if Wd.dates[Wd.me[m]] != d_m:
        raise RuntimeError("월말 자리 %s ≠ d_m %s" % (Wd.dates[Wd.me[m]], d_m))
    if Wd.dates[-1] != d_next or Wd.me.get(m1) != len(Wd.dates) - 1:
        raise RuntimeError("빈 자리 %s ≠ d_next %s" % (Wd.dates[-1], d_next))
    nb = sum(1 for v in Wd.PX.values() if not np.isnan(v[-1]))
    if nb:
        raise RuntimeError("빈 자리에 가격이 %d 개 있다" % nb)
    quarterly = [c for c in cards if c != "QF06"]
    V0 = None
    out = {}
    if quarterly:
        fm = E.formations(Wd)
        if m not in fm:
            raise RuntimeError("%s 는 편입월이 아니다" % m)
        miss = [x for x in fm if x not in tab]
        if miss:
            raise RuntimeError("Eg 가 없는 편입월: %s" % miss[:6])
        t = time.time()
        V0 = ctx.V0_targets
        sec["v0"] = round(time.time() - t, 1)
    new_fits = None
    for c in cards:
        t = time.time()
        if c == "V0":
            T = V0[m]
            w = T["w"]
            rec = {"targets": {"V0": _tj(T)}, "diag": {"n": len(w), "sum_w": float(sum(w.values())), "max_w": float(max(w.values())),
                                                      "n_forms": len(V0)}}
            if mode == "parityB":
                rec["bl"] = {"V0": _bl_part(T)}
        elif c == "QF07":
            rec, new_fits = _card_qf07(E, LT, ctx, m, job.get("fwd_fits") or [], mode, probe=bool(job.get("refit_probe")),
                                       no_new=bool(job.get("no_new_fits")), withhold=int(job.get("withhold_fits") or 0))
        elif c == "QF08":
            fm8 = NP.formations(ctx)
            if fm8[-1] != m:
                raise RuntimeError("q_netper 편입 끝 %s ≠ %s" % (fm8[-1], m))
            P = NP.prep_q08(ctx, m)
            tg = {}
            for v in ("V1", "C3"):
                ks = NP.pick_q08(P, v)
                if not (len(ks) == NP.KEEP == len(set(ks))):
                    raise RuntimeError("Q08 %s 이름 수 %d" % (v, len(ks)))
                tg[v] = NP._cap_target(P, ks)
                NP._assert_priced(ctx, {m: tg[v]})
            rec = {"targets": {v: _tj(tg[v]) for v in ("V1", "C3")},
                   "diag": {"n_U": P["n_U"], "N": P["N"], "rho_bar": float(P["rho_bar"]), "miss": {str(k): int(v) for k, v in P["miss"].items()},
                            "fp_fallback": P["fp_fallback"], "outnet": list(P["outnet"]), "dup_tickers": P["dup_tickers"], "med2": P["med2"]}}
        else:   # QF06
            st, s1, s2, mon, _sig = CS.states(ctx)
            hist = [mon[k][0] for k in sorted(mon) if "2009-01" <= k <= m]
            TX, logx = BL.targets(ctx.Wd)
            if logx[-1]["m"] != m or m not in TX:
                raise RuntimeError("x-bmrot 목표 끝 %s ≠ %s" % (logx[-1]["m"], m))
            A = ctx.A
            dfii = ((A.A.get("macro") or {}).get("DFII10")) or {}
            rec = {"targets": {"XBM": _tj(TX[m])},
                   "states": {"st": int(st[m]), "s1": int(s1[m]), "s2": int(s2[m]), "ms": float(mon[m][0]), "cs": float(mon[m][1]),
                              "p80": float(np.percentile(hist, 80)), "n_hist": len(hist), "signal": bool(st[m] == 0), "high": bool(s1[m] == 0)},
                   "diag": {"xbm": logx[-1], "dfii10_last_obs": max((dd for dd in dfii if dd <= d_m), default=None),
                            "assets_last": A.dates[-1]}}
            if mode == "parityB":
                rec["bl"] = {"XBM": _bl_part(TX[m])}
        sec[c] = round(time.time() - t, 1)
        out[c] = rec
        print("  결정 %s %s · %.0f초" % (m, c, sec[c]), flush=True)
    res = {"ok": True, "m": m, "mode": mode, "cards": out, "sec_by": sec, "n_new_fits": 0, "new_fits_file": None, "new_fits_manifest": None}
    if new_fits:
        fp = job["out"] + ".fits.json"
        with open(fp, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(new_fits, sort_keys=True, allow_nan=True))
        res.update(n_new_fits=len(new_fits), new_fits_file=fp, new_fits_manifest=LT.manifest(new_fits))
    return res


def _card_qf07(E, LT, ctx, m, fwd_fits, mode, probe=False, no_new=False, withhold=0):
    """QF07 — q_ltd.run() 1678~1682행을 ② ③ 으로(편입 [m] · key_mx 적합 해석기).
    probe(짝맞춤 B 에서만 · 선택): 그달 key_mx 단위를 «새 단위» 로 보고 비엄격 적합을 실제로 돌려 얼린 적합과 같은지 본다(③ 적합 경로의 재현 점검).
    withhold(되풀이 전용): 그달 key_mx 가운데 이름순 첫 K 를 얼린 적합에서 뺀다 — 새 적합으로 돌려주므로(probe 와 달리) 부모가 fits/ 에
      한 번 쓰고 뒤 결정이 그 파일에서 읽는 전방 경로가 실제로 돈다. 뺀 단위가 얼린 적합과 같았는지(sec 빼고)도 센다."""
    if m not in E.formations(ctx.Wd):
        raise RuntimeError("%s 는 편입월이 아니다(Q07)" % m)
    if probe and mode != "parityB":
        raise RuntimeError("refit probe 는 짝맞춤 B 에서만")
    if withhold and (probe or no_new):
        raise RuntimeError("withhold_fits 는 probe · no_new_fits 와 함께 쓸 수 없다")
    LT.formations = lambda _ctx: [m]              # ②
    known, kinfo = _known_fits(LT, fwd_fits)
    file_units = kinfo.pop("_file_units", {})
    st_box = {}

    def _fit_all_fwd(_ctx, verbose=True, strict=False):   # ③
        rows, units = LT.prep(_ctx)
        mx = {r["key_mx"] for mm in rows for r in rows[mm]["names"] if r["key_mx"]}
        if probe:
            st_box["probe_pinned"] = {k: known[k] for k in mx if k in known}
            for k in mx:
                known.pop(k, None)
        if withhold:
            wk = sorted(k for k in mx if k in known)[:withhold]
            st_box["withheld"] = {k: known.pop(k) for k in wk}
            st_box["from_file"] = sorted(k for k in wk if k in file_units)
            for k in st_box["from_file"]:
                known[k] = file_units[k]           # 앞서 기록한 fits/ 파일이 뺀 단위를 채운다(다시 읽기 경로)
        new = sorted(mx - set(known))
        if new and no_new:
            raise RuntimeError("새 적합 금지(no_new_fits) 인데 새 단위 %d" % len(new))
        if new:
            nw = set(new)
            fits_new, est = LT.estimate([u for u in units if u[0] in nw], strict=False, verbose=True)
        else:
            fits_new, est = {}, {"units": 0, "todo": 0}
        fits = {k: (known.get(k) or fits_new[k]) for k in mx}
        st_box.update(n_mx=len(mx), n_new=len(new), new=fits_new, estimate=est)
        return rows, fits, dict(est, manifest=None)
    LT.fit_all = _fit_all_fwd
    _rows, fits, _st = _fit_all_fwd(ctx)
    sig = LT.signals(ctx, fits)
    T, rec = LT.build_targets(ctx, sig)
    gap = LT.v0_check(ctx)
    if not gap < 1e-12:
        raise RuntimeError("V0 구성 재현 실패(Q07)")
    if list(T["V1"]) != [m] or len(rec) != 1:
        raise RuntimeError("Q07 편입이 [m] 이 아니다")
    r0, dg = rec[0], sig[m]["_diag"]
    est = {k: v for k, v in (st_box.get("estimate") or {}).items() if k in ("units", "todo", "nproc", "serial", "sec")}
    diag = {"miss_V1": r0["miss_V1"], "miss_C3": r0["miss_C3"], "ols_V1": dg["ols"]["V1"], "miss_beta": dg["miss_beta"],
            "miss_ltd": dg["miss_ltd"], "n_mx": st_box["n_mx"], "n_new_fits": st_box["n_new"], "v0_gap": float(gap),
            "est_hash": LT.EST_HASH, "known": kinfo, "estimate": est}
    if withhold:
        wh, nw = st_box.get("withheld") or {}, st_box["new"] or {}
        strip = lambda r: {k: v for k, v in r.items() if k != "sec"}
        diag["withheld"] = {"n": len(wh), "refit": sum(1 for k in wh if k in nw), "from_file": len(st_box.get("from_file") or []),
                            "same_ex_sec": sum(1 for k in wh if k in nw and json.dumps(strip(wh[k]), sort_keys=True)
                                               == json.dumps(strip(nw[k]), sort_keys=True))}
    if probe:
        pin, nw = st_box["probe_pinned"], st_box["new"] or {}
        strip = lambda r: {k: v for k, v in r.items() if k != "sec"}        # 적합 결과의 sec 는 걸린 시간이다
        same = sorted(k for k in pin if k in nw and json.dumps(strip(pin[k]), sort_keys=True) == json.dumps(strip(nw[k]), sort_keys=True))
        diag["refit_probe"] = {"n_pinned": len(pin), "n_refit": len(nw), "same_ex_sec": len(same),
                               "diff": sorted(set(pin) - set(same))[:10]}
        return {"targets": {"V1": _tj(T["V1"][m]), "C3": _tj(T["C3"][m])}, "diag": diag}, None
    return {"targets": {"V1": _tj(T["V1"][m]), "C3": _tj(T["C3"][m])}, "diag": diag}, (st_box["new"] or None)


# ── 짝맞춤 시험 ────────────────────────────────────────────────────────────
def _qbatch(repo=REPO):
    return json.loads(_git_bytes(["cat-file", "blob", "HEAD:data/_qbatch.json"], repo).decode("utf-8"))


def _wants(repo=REPO):
    """PARITY(명세 §6) 를 저장소 HEAD 의 data/_qbatch.json 과 한 번 더 맞춘다 — 어긋나면 멈춘다."""
    c = _qbatch(repo)["cards"]
    q7, q8, q6 = c["Q07"], c["Q08"], c["Q06"]
    src = {"Q07_V1": q7["targets_hash"], "Q07_V1_log": q7["log"]["controls"]["V1"]["hash"], "Q07_C3": q7["log"]["controls"]["C3"]["hash"],
           "Q07_est": q7["log"]["est_hash"], "Q07_fits": q7["log"]["fits_manifest"], "Q07_units": q7["log"]["estimate"]["units"],
           "Q08_V1": q8["targets_hash"], "Q08_V1_log": q8["log"]["hashes"]["V1"], "Q08_C3": q8["log"]["hashes"]["C3"],
           "XBM": q6["log"]["defense_pins"]["targets_hash"], "XBM_px": q6["log"]["defense_pins"]["px_hash"],
           "XBM_cache_blob": q6["log"]["defense_pins"]["cache_blob"], "XBM_pub_blob": q6["log"]["defense_pins"]["pub_blob"],
           "Q06": q6["targets_hash"], "Q06_signal": list(q6["log"]["signal_months"]),
           "Q06_n_switch": {"st": q6["log"]["n_switch"], "s1": q6["log"]["twins"]["T1_highMS"]["n_switch"],
                            "s2": q6["log"]["twins"]["T2_highMS_cs_le1"]["n_switch"]}}
    bad = []
    for k, v in src.items():
        kk = k.replace("_log", "")
        if PARITY[kk] != v:
            bad.append(k)
    if bad:
        raise SystemExit("🚨 PARITY 상수가 data/_qbatch.json 과 다르다: %s" % bad)
    w = dict(PARITY)
    w["Q07_forms"] = [r["m"] for r in q7["log"]["formations"]]
    if w["Q07_forms"] != quarterly_forms_is():
        raise SystemExit("🚨 _qbatch.json Q07 편입 목록이 quarterly_forms 와 다르다")
    return w


def _chk(got, want):
    return {"got": got, "want": want, "ok": bool(got == want)}


def _q06_pos_counts(D):
    """P1 격자(pxd_dates)로 q_switch.Frame 의 달별 수익일 수 — 보유월 m+1 의 거래일 수(편입월 2016-08 ~ 2026-07)."""
    me = {}
    for i, d in enumerate(D):
        me[d[:7]] = i
    months = months_between(FORM0_IS, mshift(HOLD1_IS, -1))
    ends = [me[m] for m in months] + [me[HOLD1_IS]]
    return {m: ends[k + 1] - ends[k] for k, m in enumerate(months)}


def _tier_a(root, tmpdir, wants, parts_path):
    t0 = time.time()
    r = _run_child(root, tmpdir, {"op": "parityA", "parts": parts_path}, TIMEOUT["parityA"], "parityA")
    if not r.get("ok"):
        return {"ok": False, "why": r.get("why"), "log": r.get("log")}, None
    g = r["got"]
    chk = {k: _chk(g.get(k), wants[k]) for k in ("V0_BL", "V0_LT", "XBM", "XBM_px", "XBM_cache_blob", "XBM_pub_blob", "Q06", "Q06_signal",
                                                 "Q06_n_switch", "Q06_n_low", "Q07_V1", "Q07_C3", "Q07_est", "Q07_fits", "Q07_units",
                                                 "Q07_forms", "Q08_V1", "Q08_C3")}
    chk["Q07_v0_gap_ok"] = _chk(g.get("Q07_v0_gap_ok"), True)
    parts = _rjson(parts_path)
    # 조립 자기 점검 — 부모가 달별 조각으로 다시 만든 해시 == 자식이 얼린 함수로 낸 해시(Tier B 조립의 정당성)
    D = _rjson(os.path.join(root, "data", "stocks.json"))["pxd_dates"]
    cnt = _q06_pos_counts(D)
    asm = {"V0_BL": bl_thash_parts({m: p["bl"] for m, p in parts["V0"].items()}),
           "V0_LT": lt_thash({m: p["t"] for m, p in parts["V0"].items()}),
           "XBM": bl_thash_parts({m: p["bl"] for m, p in parts["XBM"].items()}),
           "Q07_V1": lt_thash(parts["Q07_V1"]), "Q07_C3": lt_thash(parts["Q07_C3"]),
           "Q08_V1": lt_thash(parts["Q08_V1"]), "Q08_C3": lt_thash(parts["Q08_C3"])}
    pos_s = "".join(str(parts["Q06"]["st"][m]) * cnt[m] for m in parts["Q06"]["months"])
    asm["Q06"] = sw_hash_obj({"pos": pos_s, "src": {"v0": asm["V0_BL"], "bmrot": asm["XBM"]}})
    for k, v in asm.items():
        chk["assembly_" + k] = _chk(v, g.get(k))
    chk["assembly_Q06_counts"] = _chk(cnt, parts["Q06"]["counts"])
    ok = all(v["ok"] for v in chk.values())
    return {"ok": ok, "checks": chk, "sec": round(time.time() - t0, 1), "sec_by": r.get("sec_by"), "env": r.get("env")}, parts


def _tier_b(p1root, base, wants, workers, months, parts_a, eg_frozen, log_every=1, variant="B"):
    """Tier B — 달마다 원본으로 되돌리고 ⑥-cut · ⑦ → (편입이면) ⑤ 굽기 → 전방과 같은 결정 자식(mode parityB).
    [선언] 자식 배치는 원장과 같다 — 편입 달은 분기 카드(V0 · QF07 · QF08) 자식 하나와 QF06 자식 하나를 따로 돌린다
      (원장은 두 카드 무리를 따로 결정한다 · 한쪽의 실패가 다른 쪽의 마감을 늦추지 않게 · 검토 2026-09-25).
    variant "B" = 캐시 «blank» · index_history 그대로(얼린 목표와 비트 단위로 같아야 한다 — 짝맞춤의 관문).
    variant "F" = 전방 판 보기 — 캐시 «cut» + index_history 를 m 까지로(원장이 실제로 쓰는 변환 · ih_cut). 표본 안 판은 d_m 뒤 멤버십과
      캐시를 담고 있어 얼린 목표와 다를 수 있다 — 차이는 관문이 아니라 «달 목록» 으로 기록한다(선언 · 오류 0 만 요구)."""
    t0 = time.time()
    cache = "blank" if variant == "B" else "cut"
    D = _rjson(os.path.join(p1root, "data", "stocks.json"))["pxd_dates"]
    last = {}
    for i, d in enumerate(D):
        last[d[:7]] = i
    forms = set(quarterly_forms_is())
    plan = []
    for m in months:
        i = last[m]
        plan.append((m, D[i], D[i + 1]))
    pris = os.path.join(base, "pristine")
    if not os.path.isdir(pris):
        for rel in CUT_FILES:
            _wbytes(os.path.join(pris, *rel.split("/")), _rbytes(os.path.join(p1root, *rel.split("/"))))
        shutil.copytree(os.path.join(p1root, "data", "sd"), os.path.join(pris, "data", "sd"))
    roots = []
    for w in range(workers):
        wd = os.path.join(base, "%s%d" % ("w" if variant == "B" else "f", w))
        os.makedirs(wd, exist_ok=True)
        r = os.path.join(wd, "root")
        shutil.copytree(p1root, r)
        roots.append((r, wd))
    # 편입 달(오래 걸린다)을 먼저 · 뒤 달일수록 오래 걸린다 → 큰 것부터 나눠 준다(일꾼 균형)
    qq = queue.Queue()
    for item in sorted(plan, key=lambda x: (x[0] not in forms, [-int(c) for c in x[0].replace("-", "")])):
        qq.put(item)
    results, lock = {}, threading.Lock()

    def work(w):
        r, wd = roots[w]
        while True:
            try:
                m, d_m, d_next = qq.get_nowait()
            except queue.Empty:
                return
            t1 = time.time()
            rec = {"m": m, "d_m": d_m, "d_next": d_next}
            try:
                rec["cut"] = cut_and_blank(r, m, d_m, d_next, src=pris, cache=cache)
                fe = {}
                if m in forms:
                    b = bake_eg(r, m, d_m, d_next, wd, timeout=TIMEOUT["parityB_month"], tag="bake-%s" % m)
                    if not b.get("ok"):
                        raise RuntimeError("굽기: %s" % b.get("why"))
                    rec["eg"] = {"n": b["n"], "same": bool(b["scores"] == eg_frozen.get(m)), "n_frozen": len(eg_frozen.get(m) or {}),
                                 "fin_lookups": b.get("fin_lookups")}
                    if not rec["eg"]["same"]:
                        fz = eg_frozen.get(m) or {}
                        rec["eg"]["only_baked"] = sorted(set(b["scores"]) - set(fz))[:10]
                        rec["eg"]["only_frozen"] = sorted(set(fz) - set(b["scores"]))[:10]
                        rec["eg"]["n_value_diff"] = sum(1 for k in set(fz) & set(b["scores"]) if fz[k] != b["scores"][k])
                    ep = os.path.join(wd, "eg-%s.json" % m)
                    _wjson(ep, eg_record(b), allow_nan=False)
                    fe = {m: ep}
                rec["cards"], rec["sec_child"], rec["n_new_fits"] = {}, {}, 0
                groups = ([("q", ["V0", "QF07", "QF08"])] if m in forms else []) + [("m", ["QF06"])]
                for gname, cards in groups:
                    d = decide(cards, m, r, wd, fwd_eg=(fe if gname == "q" else {}), fwd_fits=[], mode="parityB", d_m=d_m,
                               d_next=d_next, timeout=TIMEOUT["parityB_month"], tag="decide-%s-%s" % (m, gname),
                               no_new_fits=(variant == "B"))
                    if not d.get("ok"):
                        raise RuntimeError("결정(%s): %s" % (gname, d.get("why")))
                    rec["cards"].update(d["cards"])
                    rec["sec_child"][gname] = d.get("sec_child")
                    rec["n_new_fits"] += int(d.get("n_new_fits") or 0)
                rec["ok"] = True
            except Exception as e:
                rec["ok"], rec["why"] = False, ("%s: %s" % (type(e).__name__, e))[:300]
            rec["sec"] = round(time.time() - t1, 1)
            with lock:
                results[m] = rec
                k = len(results)
                if log_every and (k % log_every == 0 or not rec["ok"]):
                    print("  %s [w%d] %s %s %.0f초 · %d/%d · 경과 %.0f분" % (variant, w, m, "ok" if rec["ok"] else "실패 " + rec.get("why", "")[:120],
                                                                      rec["sec"], k, len(plan), (time.time() - t0) / 60), flush=True)

    ths = [threading.Thread(target=work, args=(w,), daemon=True) for w in range(workers)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    if variant == "F":
        return _tier_f_judge(results, months, forms, wants, parts_a, D, t0, workers, eg_frozen)
    return _tier_b_judge(results, months, forms, wants, parts_a, D, t0, workers)


def _tier_f_judge(results, months, forms, wants, parts_a, D, t0, workers, eg_frozen):
    """Tier F(전방 판 보기) — 오류 0 만 관문이다. 얼린 목표와 다른 달은 카드별 «달 목록» 으로만 남긴다(값 · 비중 없음)."""
    full = list(months) == months_between(FORM0_IS, mshift(HOLD1_IS, -1))
    fm = [m for m in months if m in forms]
    errs = {m: r.get("why") for m, r in results.items() if not r.get("ok")}
    good = {m: r for m, r in results.items() if r.get("ok")}
    out = {"variant": "F", "cache": "cut", "ih_cut": True, "months": len(months), "forms": len(fm), "full": full,
           "workers": workers, "errors": errs}
    div = {}
    if parts_a:
        def diff(name, getb, geta, ms):
            div[name] = [m for m in ms if m in good and getb(good[m]) != geta(m)]
        diff("V0", lambda r: r["cards"]["V0"]["targets"]["V0"], lambda m: parts_a["V0"].get(m, {}).get("t"), fm)
        diff("Q07_V1", lambda r: r["cards"]["QF07"]["targets"]["V1"], lambda m: parts_a["Q07_V1"].get(m), fm)
        diff("Q07_C3", lambda r: r["cards"]["QF07"]["targets"]["C3"], lambda m: parts_a["Q07_C3"].get(m), fm)
        diff("Q08_V1", lambda r: r["cards"]["QF08"]["targets"]["V1"], lambda m: parts_a["Q08_V1"].get(m), fm)
        diff("Q08_C3", lambda r: r["cards"]["QF08"]["targets"]["C3"], lambda m: parts_a["Q08_C3"].get(m), fm)
        diff("XBM", lambda r: r["cards"]["QF06"]["bl"]["XBM"], lambda m: parts_a["XBM"].get(m, {}).get("bl"), months)
        for s in ("st", "s1", "s2"):
            diff("Q06_" + s, lambda r, s=s: r["cards"]["QF06"]["states"][s], lambda m, s=s: parts_a["Q06"][s].get(m), months)
    out["divergent_months"] = div
    out["n_divergent"] = {k: len(v) for k, v in div.items()}
    out["eg_diff_months"] = [m for m in fm if not (good.get(m, {}).get("eg") or {}).get("same")]
    out["new_fits"] = {m: good[m].get("n_new_fits", 0) for m in fm if good.get(m, {}).get("n_new_fits")}
    out["ih_drop_months"] = sum(1 for m in good if (good[m].get("cut") or {}).get("ih_drop"))
    out["ih"] = sorted({(good[m]["cut"] or {}).get("ih") for m in good})
    if full and not errs:
        V0p = {m: good[m]["cards"]["V0"] for m in fm}
        got = {"V0_BL": bl_thash_parts({m: V0p[m]["bl"]["V0"] for m in fm}),
               "Q07_V1": lt_thash({m: good[m]["cards"]["QF07"]["targets"]["V1"] for m in fm}),
               "Q08_V1": lt_thash({m: good[m]["cards"]["QF08"]["targets"]["V1"] for m in fm}),
               "XBM": bl_thash_parts({m: good[m]["cards"]["QF06"]["bl"]["XBM"] for m in months})}
        stv = {m: good[m]["cards"]["QF06"]["states"] for m in months}
        cnt = _q06_pos_counts(D)
        pos_s = "".join(str(stv[m]["st"]) * cnt[m] for m in months)
        got["Q06"] = sw_hash_obj({"pos": pos_s, "src": {"v0": got["V0_BL"], "bmrot": got["XBM"]}})
        got["Q06_signal"] = [m for m in months if stv[m]["st"] == 0]
        out["hash_equal_frozen"] = {k: bool(v == wants[k]) for k, v in got.items()}
        out["signal_months_fwd_view"] = got["Q06_signal"]
    out["ok"] = bool(full and not errs)
    out["sec"] = round(time.time() - t0, 1)
    return out, results


def _tier_b_judge(results, months, forms, wants, parts_a, D, t0, workers):
    full = list(months) == months_between(FORM0_IS, mshift(HOLD1_IS, -1))
    fm = [m for m in months if m in forms]
    errs = {m: r.get("why") for m, r in results.items() if not r.get("ok")}
    good = {m: r for m, r in results.items() if r.get("ok")}
    out = {"months": len(months), "forms": len(fm), "full": full, "workers": workers, "errors": errs}
    chk = {}
    eg_bad = [m for m in fm if not (good.get(m, {}).get("eg") or {}).get("same")]
    out["eg"] = {"n": len(fm), "ok": len(fm) - len(eg_bad), "bad": eg_bad,
                 "detail": {m: good[m]["eg"] for m in eg_bad if m in good}}
    chk["eg_same"] = _chk(len(eg_bad), 0)
    nf_bad = [m for m in fm if (good.get(m, {}).get("cards", {}).get("QF07", {}).get("diag", {}).get("n_new_fits") != 0)]
    out["new_fits"] = {"n": len(fm), "zero": len(fm) - len(nf_bad), "bad": nf_bad}
    chk["q07_new_fits_zero"] = _chk(len(nf_bad), 0)
    ih = sorted({(good[m]["cut"] or {}).get("ih") for m in good})
    out["ih"] = ih
    # 달별 대조(Tier A 조각이 있으면) — 어느 달이 갈렸는지
    per = {}
    if parts_a:
        def mism(name, getb, geta, ms):
            bad = [m for m in ms if m in good and getb(good[m]) != geta(m)]
            per[name] = {"n": len([m for m in ms if m in good]), "bad": bad}
        mism("V0", lambda r: r["cards"]["V0"]["targets"]["V0"], lambda m: parts_a["V0"].get(m, {}).get("t"), fm)
        mism("V0_bl", lambda r: r["cards"]["V0"]["bl"]["V0"], lambda m: parts_a["V0"].get(m, {}).get("bl"), fm)
        mism("Q07_V1", lambda r: r["cards"]["QF07"]["targets"]["V1"], lambda m: parts_a["Q07_V1"].get(m), fm)
        mism("Q07_C3", lambda r: r["cards"]["QF07"]["targets"]["C3"], lambda m: parts_a["Q07_C3"].get(m), fm)
        mism("Q08_V1", lambda r: r["cards"]["QF08"]["targets"]["V1"], lambda m: parts_a["Q08_V1"].get(m), fm)
        mism("Q08_C3", lambda r: r["cards"]["QF08"]["targets"]["C3"], lambda m: parts_a["Q08_C3"].get(m), fm)
        mism("XBM_bl", lambda r: r["cards"]["QF06"]["bl"]["XBM"], lambda m: parts_a["XBM"].get(m, {}).get("bl"), months)
        for s in ("st", "s1", "s2"):
            mism("Q06_" + s, lambda r, s=s: r["cards"]["QF06"]["states"][s], lambda m, s=s: parts_a["Q06"][s].get(m), months)
        for k, v in per.items():
            chk["per_month_" + k] = _chk(v["bad"], [])
    out["per_month"] = per
    if full and not errs:
        V0p = {m: good[m]["cards"]["V0"] for m in fm}
        got = {"V0_BL": bl_thash_parts({m: V0p[m]["bl"]["V0"] for m in fm}),
               "V0_LT": lt_thash({m: V0p[m]["targets"]["V0"] for m in fm}),
               "Q07_V1": lt_thash({m: good[m]["cards"]["QF07"]["targets"]["V1"] for m in fm}),
               "Q07_C3": lt_thash({m: good[m]["cards"]["QF07"]["targets"]["C3"] for m in fm}),
               "Q08_V1": lt_thash({m: good[m]["cards"]["QF08"]["targets"]["V1"] for m in fm}),
               "Q08_C3": lt_thash({m: good[m]["cards"]["QF08"]["targets"]["C3"] for m in fm}),
               "XBM": bl_thash_parts({m: good[m]["cards"]["QF06"]["bl"]["XBM"] for m in months})}
        stv = {m: good[m]["cards"]["QF06"]["states"] for m in months}
        cnt = _q06_pos_counts(D)
        pos_s = "".join(str(stv[m]["st"]) * cnt[m] for m in months)
        got["Q06"] = sw_hash_obj({"pos": pos_s, "src": {"v0": got["V0_BL"], "bmrot": got["XBM"]}})
        got["Q06_signal"] = [m for m in months if stv[m]["st"] == 0]
        low = {"s1": [m for m in months if stv[m]["s1"] == 0], "s2": [m for m in months if stv[m]["s2"] == 0]}
        got["Q06_n_low"] = {k: len(v) for k, v in low.items()}
        for k in ("V0_BL", "V0_LT", "Q07_V1", "Q07_C3", "Q08_V1", "Q08_C3", "XBM", "Q06", "Q06_signal", "Q06_n_low"):
            chk[k] = _chk(got[k], wants[k])
        if parts_a:
            chk["Q06_low_lists"] = _chk(low, parts_a["Q06"]["low"])
        else:
            chk["Q06_low_lists"] = {"got": low, "want": None, "ok": True, "note": "Tier A 조각 없음 — 개수만 대조"}
        # 교체 수(상태에서 나온 개수) — 위치 벡터에서 nxt ≠ pos 의 수
        nsw = {}
        for s in ("st", "s1", "s2"):
            p = "".join(str(stv[m][s]) * cnt[m] for m in months)
            nsw[s] = sum(1 for j in range(len(p)) if (p[j + 1] if j + 1 < len(p) else p[-1]) != p[j])
        chk["Q06_n_switch"] = _chk(nsw, wants["Q06_n_switch"])
    elif not full:
        out["note"] = "부분 달 — 전체 해시 대조 없음(달별 대조만)"
    ok = bool(full and not errs and all(v["ok"] for v in chk.values()))
    out["checks"] = chk
    out["ok"] = ok
    out["sec"] = round(time.time() - t0, 1)
    out["sec_month"] = {m: good[m]["sec"] for m in sorted(good)}
    return out, results


def pairing_test(tier="ABF", workers=3, months=None, out=PARITY_OUT, keep=False, repo=REPO, parts_dir=None, snap_wt=None):
    """등록 전 짝맞춤 — 해시 · 목록 · 개수만. out 에 parity.json(수익 없음). 달을 좁히면(months) 부분 시험 — ok 는 거짓.
    tier: A(틀 동일성) · B(전방 경로 · 얼린 목표와 비트 단위) · F(전방 판 보기 — 오류 0 · 차이는 달 목록) — ok 는 셋 모두일 때만."""
    t0 = time.time()
    wants = _wants(repo)
    me = _rbytes(os.path.abspath(__file__))
    base = tempfile.mkdtemp(prefix="qfwd_par_")
    parts_dir = parts_dir or os.path.join(tempfile.gettempdir(), "qfwd_parity")
    os.makedirs(parts_dir, exist_ok=True)
    res = {"v": 1, "code_pin": CODE_PIN, "adapter_blob": blob_sha1(me), "p1": {"price": P1_PRICE, "base": P1_BASE},
           "env": env_report(), "tier": tier, "t_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print("QFWD 짝맞춤 %s · 임시 %s" % (tier, base), flush=True)
    try:
        p1dir = os.path.join(base, "p1")
        os.makedirs(p1dir)
        root, rep = build_root(P1_BASE, CODE_PIN, p1dir, price_commit=P1_PRICE, repo=repo)
        res["p1"]["root"] = rep
        print("  P1 뿌리 %d 파일 · %.0f초" % (rep["n_files"], rep["sec"]), flush=True)
        sw = snap_wt if snap_wt is not None else os.path.join(os.environ.get("TEMP") or tempfile.gettempdir(), "snap_wt")
        if sw and os.path.isdir(os.path.join(sw, "data")):
            cmp_ = compare_tree(root, sw)
            res["p1"]["vs_snap_wt"] = cmp_
            print("  P1 대 snap_wt: 같음 %d · 다름 %d · 뿌리에만 %d · snap_wt 에만 %d" % (cmp_["same"], cmp_["n_diff"], cmp_["n_only_root"],
                                                                                  cmp_["n_only_other"]), flush=True)
        parts_a = None
        pa = os.path.join(parts_dir, "tierA_parts.json")
        if "A" in tier:
            ta, parts_a = _tier_a(root, p1dir, wants, pa)
            res["tierA"] = ta
            _print_checks("A", ta)
        elif os.path.exists(pa):
            parts_a = _rjson(pa)
            res["tierA_parts_from"] = pa
        ms = months or months_between(FORM0_IS, mshift(HOLD1_IS, -1))
        eg_frozen = None
        if "B" in tier or "F" in tier:
            eg_frozen = _rjson(os.path.join(root, "data", "_eg_q5_scores_pitgics.json"))["months"]
        if "B" in tier:
            tb, rb = _tier_b(root, base, wants, workers, ms, parts_a, eg_frozen)
            res["tierB"] = tb
            _wjson(os.path.join(parts_dir, "tierB_results.json"), rb, allow_nan=False)
            _print_checks("B", tb)
        if "F" in tier:
            tf, rf = _tier_b(root, base, wants, workers, ms, parts_a, eg_frozen, variant="F")
            res["tierF"] = tf
            _wjson(os.path.join(parts_dir, "tierF_results.json"), rf, allow_nan=False)
            print("  Tier F(전방 판 보기): 오류 %d · ok %s · 얼린 목표와 다른 달 %s · Eg 다른 달 %d · 새 적합 달 %d · 멤버십 자른 달 %d"
                  % (len(tf.get("errors") or {}), tf.get("ok"), tf.get("n_divergent"), len(tf.get("eg_diff_months") or []),
                     len(tf.get("new_fits") or {}), tf.get("ih_drop_months") or 0), flush=True)
        need = [k for k in ("tierA", "tierB", "tierF") if k[-1] in tier]
        res["ok"] = bool(tier == "ABF" and all(res.get(k, {}).get("ok") for k in need))
        res["sec"] = round(time.time() - t0, 1)
        res["t"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        partial = bool(months) or tier != "ABF"
        dest = out if not (partial and os.path.normpath(out) == os.path.normpath(PARITY_OUT)) else os.path.join(parts_dir, "parity_partial.json")
        dest = dest if os.path.isabs(dest) else os.path.join(repo, dest)
        _wjson(dest, res, compact=False, allow_nan=False)
        print("QFWD 짝맞춤 %s → %s · ok %s · %.0f분" % (tier, dest, res["ok"], res["sec"] / 60), flush=True)
        return res
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def _print_checks(tag, t):
    chk = t.get("checks") or {}
    n_ok = sum(1 for v in chk.values() if v["ok"])
    print("  Tier %s: %d/%d 일치 · ok %s%s" % (tag, n_ok, len(chk), t.get("ok"), (" · 실패 " + str(t.get("why"))) if t.get("why") else ""), flush=True)
    for k, v in chk.items():
        g = v["got"]
        s = (g[:16] + "…") if isinstance(g, str) and len(g) > 20 else (("%d개" % len(g)) if isinstance(g, list) and len(g) > 6 else g)
        print("    %-24s %s  %s" % (k, "일치" if v["ok"] else "다름", s if not isinstance(s, dict) or len(str(s)) < 90 else "{…}"), flush=True)
    if t.get("errors"):
        print("    오류 달 %d: %s" % (len(t["errors"]), sorted(t["errors"])[:8]), flush=True)


def probe_refit(m="2026-06", repo=REPO, keep=False):
    """③ 적합 경로 점검(선택 · 기록만) — P1 뿌리의 편입 m 을 자르고 그달 key_mx 단위를 모두 비엄격으로 다시 적합해
    얼린 적합과 같은지(걸린 시간 sec 만 빼고) · 그 적합으로 낸 V1 · C3 목표가 Tier A 조각과 같은지 본다. 수익 없음."""
    base = tempfile.mkdtemp(prefix="qfwd_probe_")
    try:
        root, _rep = build_root(P1_BASE, CODE_PIN, base, price_commit=P1_PRICE, repo=repo)
        D = _rjson(os.path.join(root, "data", "stocks.json"))["pxd_dates"]
        last = {}
        for i, d in enumerate(D):
            last[d[:7]] = i
        d_m, d_next = D[last[m]], D[last[m] + 1]
        cut_and_blank(root, m, d_m, d_next, cache="blank")
        r = decide(["QF07"], m, root, base, mode="parityB", d_m=d_m, d_next=d_next, refit_probe=True, tag="probe-%s" % m)
        if not r.get("ok"):
            print("probe 실패: %s" % r.get("why"))
            return r
        dg = r["cards"]["QF07"]["diag"]
        pa = os.path.join(tempfile.gettempdir(), "qfwd_parity", "tierA_parts.json")
        same_t = None
        if os.path.exists(pa):
            P = _rjson(pa)
            same_t = {v: r["cards"]["QF07"]["targets"][v] == P["Q07_" + v].get(m) for v in ("V1", "C3")}
        out = {"m": m, "refit_probe": dg["refit_probe"], "n_mx": dg["n_mx"], "estimate": dg["estimate"], "targets_same_as_tierA": same_t,
               "sec": r["sec"]}
        print(json.dumps(out, ensure_ascii=False))
        return out
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


# ── 등록 핀(pins.json) ─────────────────────────────────────────────────────
def _head_blobs(repo, paths):
    out = {}
    for p in paths:
        b = _git_text(["rev-parse", "HEAD:%s" % p], repo, check=False)
        out[p] = b if len(b) == 40 else None
    return out


def _lf_sha(path):
    """파일 바이트 sha256 — CRLF 는 LF 로(qfwd_check.raw_sha 와 같다)."""
    return sha256_hex(_rbytes(path).replace(b"\r\n", b"\n"))


def pins(write=False, repo=REPO, prereg=PREREG):
    """data/_qfwd/pins.json — HEAD 의 qfwd 파일 blob · 사전등록 문서 blob · genesis(원장 파일 다섯) · parity sha. --write 는 한 번만(있으면 거부).
    [선언] 사전등록 문서 자신도 핀이다(prereg_blob) — 등록 뒤 문서를 고치면 점검기 · 원장이 멈춘다(고칠 길은 수정 등록 · amend)."""
    qf = _head_blobs(repo, QFWD_FILES)
    pb = _head_blobs(repo, [prereg])[prereg]
    gen = {f: sha256_hex(("QFWD|%s|%s|%s" % (prereg, CODE_PIN, f)).encode()) for f in LEDGER_FILES}
    pp = os.path.join(repo, PARITY_OUT)
    par = _rbytes(pp) if os.path.exists(pp) else None
    doc = {"v": 1, "prereg": prereg, "prereg_blob": pb, "code_pin": CODE_PIN, "build_tree": BUILD_TREE, "frozen_blobs": FROZEN_BLOBS,
           "p3": P3, "env": {k: (list(v) if isinstance(v, tuple) else v) for k, v in ENV_PIN.items()}, "qfwd_files": qf,
           "genesis": gen, "parity_sha": _lf_sha(pp) if par else None}
    miss = [p for p, b in qf.items() if b is None] + ([prereg] if pb is None else [])
    print("QFWD 핀: qfwd 파일 %d/%d · 사전등록 문서 %s · parity %s" % (len(qf) - sum(1 for b in qf.values() if b is None), len(qf),
                                                            "있음" if pb else "없음", "있음" if par else "없음"))
    if write:
        if miss or not par or not json.loads(par.decode("utf-8")).get("ok"):
            raise SystemExit("🚨 pins --write 거부 — HEAD 에 없는 파일 %s · parity.ok 거짓 또는 없음" % miss)
        if json.loads(par.decode("utf-8")).get("adapter_blob") != qf[ADAPTER_REL_]:
            raise SystemExit("🚨 pins --write 거부 — parity.adapter_blob ≠ HEAD 어댑터 blob(짝맞춤을 다시 돌릴 것)")
        dest = os.path.join(repo, QFWD_DIR, "pins.json")
        if os.path.exists(dest):
            raise SystemExit("🚨 %s 가 이미 있다 — 불변 파일이다" % dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(canon(doc) + "\n")
        print("→ %s" % dest)
    return doc


def amend(prereg, why, parity_path=None, write=False, repo=REPO):
    """수정 등록 핀 사슬의 다음 고리 — data/_qfwd/amend/pins-<n>.json(한 번 쓰기).
    [선언] 고리가 바꿀 수 있는 것은 qfwd 파일 다섯의 blob 뿐이다(코드 핀 · 얼린 blob · P3 · 환경 · genesis 는 pins.json 에만 있고 고리에는 없다).
      어댑터 blob 이 바뀌면 그 blob 으로 다시 돌린 짝맞춤(ok = 참 · adapter_blob 일치)을 amend/parity-<n>.json 으로 함께 올린다.
      고리마다 수정 등록 문서(새 PREREG · 사유)의 blob 을 핀으로 박는다. 이미 쓴 원장 줄은 다시 쓰지 않는다.
      절차는 등록과 같은 두 커밋이다: ① 새 코드 · 문서 · (필요하면) 새 parity 를 커밋 → ② 이 명령 --write 로 만든 고리를 커밋."""
    base_p = os.path.join(repo, QFWD_DIR, "pins.json")
    if not os.path.exists(base_p):
        raise SystemExit("🚨 pins.json 이 없다 — 등록 전에는 수정 등록이 없다")
    base = _rjson(base_p)
    ad = os.path.join(repo, AMEND_DIR)
    links = sorted(f for f in (os.listdir(ad) if os.path.isdir(ad) else []) if f.startswith("pins-") and f.endswith(".json"))
    prev = _rjson(os.path.join(ad, links[-1])) if links else base
    n = len(links) + 1
    qf = _head_blobs(repo, QFWD_FILES)
    pb = _head_blobs(repo, [prereg])[prereg]
    miss = [p for p, b in qf.items() if b is None] + ([prereg] if pb is None else [])
    prev_ad = (prev.get("qfwd_files") or {}).get(ADAPTER_REL_)
    par_rel, par_sha = prev.get("parity") or PARITY_OUT.replace(os.sep, "/"), prev.get("parity_sha")
    if qf.get(ADAPTER_REL_) != prev_ad:
        if not parity_path:
            raise SystemExit("🚨 어댑터 blob 이 바뀌었다 — 새 짝맞춤(--parity data/_qfwd/amend/parity-%03d.json)이 필요하다" % n)
        pp = os.path.join(repo, parity_path)
        pj = _rjson(pp) if os.path.exists(pp) else {}
        if not pj.get("ok") or pj.get("adapter_blob") != qf.get(ADAPTER_REL_):
            raise SystemExit("🚨 %s 가 ok 가 아니거나 adapter_blob 이 HEAD 어댑터와 다르다" % parity_path)
        par_rel, par_sha = parity_path.replace(os.sep, "/"), _lf_sha(pp)
    doc = {"v": 1, "kind": "amend", "n": n, "prev_sha": sha256_hex(canon(prev).encode("utf-8")), "prereg": prereg, "prereg_blob": pb,
           "why": why, "code_pin": CODE_PIN, "qfwd_files": qf, "parity": par_rel, "parity_sha": par_sha,
           "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print("QFWD 수정 등록 고리 %d — 바뀐 파일 %s · parity %s" % (n, sorted(p for p in qf if qf[p] != (prev.get("qfwd_files") or {}).get(p)),
                                                     par_rel))
    if write:
        if miss:
            raise SystemExit("🚨 amend --write 거부 — HEAD 에 없는 파일 %s" % miss)
        dest = os.path.join(repo, AMEND_DIR, "pins-%03d.json" % n)
        if os.path.exists(dest):
            raise SystemExit("🚨 %s 가 이미 있다" % dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(canon(doc) + "\n")
        print("→ %s" % dest)
    return doc


def parity_summary(path=PARITY_OUT):
    """짝맞춤 결과 → 마크다운(러너 잡 요약 $GITHUB_STEP_SUMMARY 용) — 대조 이름 · 일치 · 해시 앞 16자 · 개수만."""
    p = path if os.path.isabs(path) else os.path.join(REPO, path)
    if not os.path.exists(p):
        print("### QFWD 짝맞춤 — 결과 파일 없음 (%s)" % path)
        return 1
    r = _rjson(p)
    env = r.get("env") or {}
    print("### QFWD 짝맞춤 %s — ok %s · 어댑터 %s · %s · numpy %s · scipy %s"
          % (r.get("tier"), r.get("ok"), str(r.get("adapter_blob"))[:12], env.get("platform"), env.get("numpy"), env.get("scipy")))
    for tk in ("tierA", "tierB"):
        t = r.get(tk)
        if not t:
            continue
        chk = t.get("checks") or {}
        print("\n**%s** — %d/%d 일치 · ok %s\n\n| 대조 | 일치 | 값 |\n|---|---|---|" % (tk, sum(1 for v in chk.values() if v.get("ok")), len(chk),
                                                                          t.get("ok")))
        for k, v in chk.items():
            g = v.get("got")
            s = (g[:16] + "…") if isinstance(g, str) and len(g) > 20 else (("%d개" % len(g)) if isinstance(g, (list, dict)) else g)
            print("| %s | %s | %s |" % (k, "✓" if v.get("ok") else "✗", s))
    tf = r.get("tierF")
    if tf:
        print("\n**tierF** — 오류 %d · ok %s · 다른 달 수 %s" % (len(tf.get("errors") or {}), tf.get("ok"), tf.get("n_divergent")))
    return 0 if r.get("ok") or r.get("tier") == "A" and (r.get("tierA") or {}).get("ok") else 1


# ── selftest(합성 자료만) ───────────────────────────────────────────────────
def selftest():
    import types
    tests = {}
    tests["blob_empty"] = blob_sha1(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    tests["blob_hello"] = blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    tests["mshift"] = mshift("2026-12", 1) == "2027-01" and mshift("2026-01", -1) == "2025-12" and mshift("2026-09", 3) == "2026-12"
    tests["forms41"] = len(quarterly_forms_is()) == 41 and quarterly_forms_is()[0] == "2016-08" and quarterly_forms_is()[-1] == "2026-06"
    # canon · seal
    rec = {"b": 1.1, "a": "한글", "c": [None, 2]}
    s = seal(rec, 0, "g")
    tests["canon_order"] = canon(rec) == '{"a":"한글","b":1.1,"c":[null,2]}'
    tests["seal_sha"] = s["sha"] == sha256_hex(canon({k: v for k, v in s.items() if k != "sha"}).encode("utf-8")) and s["seq"] == 0 and s["prev"] == "g"
    tests["seal_roundtrip"] = canon(json.loads(canon(s))) == canon(s)
    try:
        canon({"x": float("nan")})
        tests["canon_nan_refused"] = False
    except ValueError:
        tests["canon_nan_refused"] = True
    tests["seal_tamper"] = seal(dict(s, b=1.2), 0, "g")["sha"] != s["sha"]
    # 해시 조립 = 얼린 식(합성)
    T = {"2020-03": {"w": {"B": 0.3333333333333333, "A": 0.6666666666666667}, "names": {"A": "A", "B": "B"}},
         "2020-06": {"w": {"C": 1.0}, "names": {"C": "C"}}}
    ref_bl = hashlib.sha256(json.dumps({m: {"w": {k: round(v, 12) for k, v in sorted(x["w"].items())}} for m, x in sorted(T.items())},
                                       sort_keys=True).encode()).hexdigest()
    tests["bl_assembly"] = bl_thash_parts({m: _bl_part(T[m]) for m in T}) == ref_bl
    tests["lt_assembly"] = lt_thash(json.loads(json.dumps(T))) == hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()
    tests["q06_counts"] = _q06_pos_counts(["2016-08-30", "2016-08-31", "2016-09-01", "2016-09-30"] +
                                          [d for m in months_between("2016-10", "2026-08") for d in (m + "-01", m + "-15")])["2016-08"] == 2
    # 자식 결과 — 신호로 죽음(rc < 0) = memory · 결과 없는 보통 실패 = error · 결과가 ok 여도 rc ≠ 0 이면 실패
    k1 = _child_result(-9, None)
    k2 = _child_result(1, None)
    k3 = _child_result(3, {"ok": True})
    k4 = _child_result(-9, {"ok": False, "outcome": "error"})
    tests["child_sigkill_memory"] = (k1["outcome"] == "memory" and not k1["ok"] and k2["outcome"] == "error" and not k3["ok"]
                                     and k4["outcome"] == "memory")
    tests["timeouts_fit_budget"] = TIMEOUT["archive"] + TIMEOUT["bake_eg"] + TIMEOUT["decide"] <= 3000
    # 울타리 — 가짜 모듈에 설치 · 부르면 예외 · 없는 속성은 닫힌 실패
    fake = {}
    for mname, attrs in FENCE.items():
        mod = types.ModuleType(mname)
        for a in attrs:
            owner, _, leaf = a.rpartition(".")
            if owner:
                if not hasattr(mod, owner):
                    setattr(mod, owner, type(owner, (), {}))
                setattr(getattr(mod, owner), leaf, lambda *x, **y: 1)
            else:
                setattr(mod, leaf, lambda *x, **y: 1)
        fake[mname] = mod
    n = _fence(fake)
    raised = 0
    for mname, attrs in FENCE.items():
        for a in attrs:
            owner, _, leaf = a.rpartition(".")
            f = getattr(getattr(fake[mname], owner) if owner else fake[mname], leaf)
            try:
                f()
            except RuntimeError as e:
                raised += "QFWD fence" in str(e)
    tests["fence_all_raise"] = raised == n == sum(len(v) for v in FENCE.values())
    try:
        _fence({k: types.ModuleType(k) for k in FENCE})
        tests["fence_missing_closed"] = False
    except RuntimeError:
        tests["fence_missing_closed"] = True
    # 자르기 · 빈 자리 · ⑥b — 합성 뿌리
    d = tempfile.mkdtemp(prefix="qfwd_st_")
    try:
        D = ["2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02"]
        wr = lambda rel, o: _wjson(os.path.join(d, *rel.split("/")), o)
        wr("data/stocks.json", {"pxd_dates": D, "stocks": [{"t": "AAA"}, {"t": "BAD"}]})
        wr("data/sd/AAA.json", {"t": "AAA", "pxd": [1, 2, 3, 4, 5], "vd": [1] * 5, "hd": [1] * 5, "ld": [1] * 5, "fundx_flags": [0] * 17})
        wr("data/sd/BAD.json", {"t": "BAD", "pxd": [1, 2, 3]})
        wr("data/pit_px.json", {"dates": D, "px": {"OLD": {"i0": 1, "p": [9, 9, 9, 9]}, "LATE": {"i0": 4, "p": [7]}}, "quarantine": {}})
        wr("data/assets.json", {"dates": D + ["2026-09-03"], "n_days": 6, "px": {"SPY": [1, 2, 3, 4, 5, 6]}, "open": {"SPY": [1] * 6},
                                "macro": {"DFII10": {"2026-08-28": 1.0, "2026-08-31": 1.1, "2026-09-01": 1.2}},
                                "div": {"SPY": {"2026-06-18": 0.5, "2026-09-18": 0.6}}})
        wr("data/bench_px.json", {"dates": D, "n": 5, "series": {"spx": {"px": [1, 2, 3, 4, 5]}, "ndx": {"px": [1, 2, 3, 4, 5]}}})
        wr("data/_pit_px_cache.json", {"OLD": {"2026-08-28": 1.0, "2026-09-01": 1.5, "2026-09-02": 2.0}})
        wr("data/index_history.json", {"months": {"2026-07": {"spx": ["AAA"]}, "2026-09": {"spx": ["AAA", "ZZZ"]}}})
        wr("data/sd/OFF.json", {"t": "OFF", "pxd": [1, 2, 3, 4]})
        rep = cut_and_blank(d, "2026-08", "2026-08-31", "2026-09-01")
        S = _rjson(os.path.join(d, "data", "stocks.json"))
        sd = _rjson(os.path.join(d, "data", "sd", "AAA.json"))
        P = _rjson(os.path.join(d, "data", "pit_px.json"))
        A = _rjson(os.path.join(d, "data", "assets.json"))
        B = _rjson(os.path.join(d, "data", "bench_px.json"))
        C = _rjson(os.path.join(d, "data", "_pit_px_cache.json"))
        H = _rjson(os.path.join(d, "data", "index_history.json"))
        tests["cut_grid"] = S["pxd_dates"] == ["2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01"] and P["dates"] == S["pxd_dates"]
        tests["cut_sd_blank"] = sd["pxd"] == [1, 2, 3, None] and sd["ld"] == [1, 1, 1, None] and len(sd["fundx_flags"]) == 17
        tests["cut_pitpx"] = P["px"]["OLD"]["p"] == [9, 9] and P["px"]["LATE"]["p"] == []
        tests["cut_assets"] = A["dates"] == D[:3] and A["px"]["SPY"] == [1, 2, 3] and A["n_days"] == 3 and \
            set(A["macro"]["DFII10"]) == {"2026-08-28", "2026-08-31"} and set(A["div"]["SPY"]) == {"2026-06-18"}
        tests["cut_bench"] = B["dates"] == D[:3] and B["series"]["spx"]["px"] == [1, 2, 3] and B["n"] == 3
        tests["cut_cache"] = C == {"OLD": {"2026-08-28": 1.0}}
        tests["ih_carry"] = rep["ih"] == "m-1" and H["months"].get("2026-08") == {}
        tests["ih_cut_fwd"] = rep["ih_cut"] and rep["ih_drop"] == ["2026-09"] and "2026-09" not in H["months"]
        tests["sd_off_grid_reported"] = (rep["sd_off_grid"] == ["BAD", "OFF"] and _rjson(os.path.join(d, "data", "sd", "OFF.json"))["pxd"] == [1, 2, 3, 4]
                                         and rep["dropped_off_grid"] == ["BAD"] and [s["t"] for s in S["stocks"]] == ["AAA"]
                                         and not os.path.exists(os.path.join(d, "data", "sd", "BAD.json")))
        # src 되돌리기 — 다른 뿌리에서 원본을 읽는다
        d2 = tempfile.mkdtemp(prefix="qfwd_st2_")
        try:
            shutil.copytree(os.path.join(d, "data"), os.path.join(d2, "data"))
            wr("data/index_history.json", {"months": {"2026-07": {"spx": ["AAA"]}, "2026-08": {"spx": ["AAA"]},
                                                      "2026-09": {"spx": ["AAA"]}}})
            wr("data/stocks.json", {"pxd_dates": D, "stocks": [{"t": "AAA"}]})
            wr("data/sd/AAA.json", {"t": "AAA", "pxd": [1, 2, 3, 4, 5], "vd": [1] * 5, "hd": [1] * 5, "ld": [1] * 5})
            wr("data/pit_px.json", {"dates": D, "px": {"OLD": {"i0": 1, "p": [9, 9, 9, 9]}}})
            wr("data/assets.json", {"dates": D, "px": {"SPY": [1, 2, 3, 4, 5]}, "open": {}, "macro": {}, "div": {}})
            wr("data/bench_px.json", {"dates": D, "series": {"spx": {"px": [1, 2, 3, 4, 5]}}})
            wr("data/_pit_px_cache.json", {})
            wr("data/_pit_px_cache.json", {"OLD": {"2026-08-28": 1.0, "2026-09-01": 1.5, "2026-09-02": 2.0}})
            rep2 = cut_and_blank(d2, "2026-08", "2026-08-28", "2026-09-01", src=d, cache="blank")
            C2 = _rjson(os.path.join(d2, "data", "_pit_px_cache.json"))
            tests["cache_blank_only_dnext"] = C2 == {"OLD": {"2026-08-28": 1.0, "2026-09-02": 2.0}} and rep2["n_cache_drop"] == 1
            S2 = _rjson(os.path.join(d2, "data", "stocks.json"))
            H2 = _rjson(os.path.join(d2, "data", "index_history.json"))
            tests["cut_from_src"] = S2["pxd_dates"] == ["2026-08-27", "2026-08-28", "2026-09-01"] and rep2["ih"] == "m" and "2026-08" in H2["months"]
            tests["ih_kept_blank"] = (not rep2["ih_cut"]) and rep2["ih_drop"] == [] and "2026-09" in H2["months"]
        finally:
            shutil.rmtree(d2, ignore_errors=True)
        try:
            cut_and_blank(d, "2026-08", "2026-08-31", "2026-08-31")
            tests["blank_must_be_next_month"] = False
        except AssertionError:
            tests["blank_must_be_next_month"] = True
    finally:
        shutil.rmtree(d, ignore_errors=True)
    ok = all(bool(v) for v in tests.values())
    return {"ok": ok, "tests": {k: bool(v) for k, v in tests.items()}}


def main(argv):
    if len(argv) >= 3 and argv[1] == "--child":
        return _child(argv[2])
    cmd = argv[1] if len(argv) > 1 else "selftest"
    if cmd == "selftest":
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if cmd == "parity":
        a = argv[2:]
        opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
        tier = opt("--tier", "ABF")
        ms = opt("--months")
        r = pairing_test(tier=tier, workers=int(opt("--workers", "3")), months=(ms.split(",") if ms else None),
                         out=opt("--out", PARITY_OUT), keep="--keep" in a, parts_dir=opt("--parts-dir"))
        # 종료 코드 — 돌린 층이 모두 통과해야 0(러너 Tier A 불일치도 붉게 · 검토 2026-09-25) · 달을 좁힌 부분 시험은 보고만
        if ms:
            return 0
        need = [k for k in ("tierA", "tierB", "tierF") if k[-1] in tier]
        return 0 if all((r.get(k) or {}).get("ok") for k in need) else 1
    if cmd == "parity-summary":
        return parity_summary(argv[2] if len(argv) > 2 else PARITY_OUT)
    if cmd == "pins":
        pins(write="--write" in argv)
        return 0
    if cmd == "amend":
        a = argv[2:]
        opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
        if not opt("--prereg") or not opt("--why"):
            print("사용: amend --prereg build/PREREG-…-QFWD-AMEND-<n>.md --why '사유' [--parity data/_qfwd/amend/parity-<n>.json] [--write]")
            return 2
        amend(opt("--prereg"), opt("--why"), parity_path=opt("--parity"), write="--write" in a)
        return 0
    if cmd == "probe-refit":
        a = argv[2:]
        r = probe_refit(a[a.index("--month") + 1] if "--month" in a else "2026-06", keep="--keep" in a)
        return 0 if (r.get("refit_probe") or {}).get("same_ex_sec") == (r.get("refit_probe") or {}).get("n_pinned") else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
