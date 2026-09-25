# -*- coding: utf-8 -*-
"""build/qfwd_judge.py — 전방 원장(QFWD) 판정기 · 관문 날짜 전에는 개월 수 · 사건 수 · 무결성만 찍는다.

근본 이유 — 전방 기록을 관문 전에 들여다보면, 보는 순간부터 그 규칙은 «전방을 보고 고친 규칙» 이 된다(계획: 전방을 보고
  새로 만든 규칙은 오염된 것으로 본다). 그래서 --status 는 수익 · 초과 · t 를 한 글자도 내지 않고 센 것만 낸다.
  관문(FF1 2028-11-01 · FF2 2029-11-01 부터 분기마다 2031-11-01 까지)에서만 --gate 가 숫자를 내고 judge/<관문>-<관문 날짜>.json
  을 한 번 쓴다. 날짜 · 개월 · 사건 최소가 안 되면 숫자 없이 거절한다(종료 2).
[선언] 관문 창과 보기 횟수는 고정이다(검토 2026-09-25) —
  · 창 = 전방 1개월(2026-11) ~ 관문 날짜의 앞 달(FF1 = 정확히 2026-11 ~ 2028-10 · FF2 2029-11-01 = ~ 2029-10 · 2030-02-01 = ~ 2030-01 …).
    그 뒤에 실현된 달 · 사건은 보지 않는다. 창의 달이 다 실현되기 전에는 숫자 없이 거절한다(다음 날 다시 돌 수 있다).
  · 관문 날짜 하나에 판정 파일 하나 — judge/<관문>-<관문 날짜>.json 이 이미 있거나 더 늦은 관문 날짜의 파일이 있으면 거절한다
    (FF1 한 번 · FF2 최대 9번 = 등록한 보기 수).
  · 사건(급락 다리 · 반등)은 창 끝 날(d_m) 포착 판의 ^GSPC 로 · 창 끝까지 자른 계열에서 센다 — 언제 돌려도 같은 수가 나온다.

통계는 얼린 모듈 그대로다(복제하면 표가 갈린다) — eg30plus.nw_t · down_t · mech_episodes.zigzag · rebounds ·
  q_switch.sleeve_daily · _close_terms · month_growth · mix_ex_closed · fund_ex_closed.
  [선언] 관문 · 상태 · 자가 시험은 작업 사본이 아니라 코드 핀 1d81f083 의 build/ 를 임시 뿌리에 풀어(얼린 blob 18 단언) 그 모듈을 부르고,
  numpy · scipy · pandas · 파이썬 판이 환경 핀과 같은지 단언한다(2028~2031 에 작업 사본이 바뀌어도 판정 코드는 그대로다).
  ForwardFrame 은 시장 · 장부 기록으로 q_switch.Frame 의 자리(months · hold · day · i0 · T · mstart · gIX · years · dates)를 채운다.
  첫 달은 ENTRY_DAY 를 수익 0 인 첫 칸으로 둔다(진입 10bp 가 1개월째에 한 번 붙는다).

펀드 회계(판정기 정의 · 원장은 계산하지 않는다) — 장부 b · 비용 c · 달 h: 월초 0.9/0.1 · 날마다 ixv *= 1+spy_r · slv *= g_c ·
  월말 v = ixv + slv, v −= c·2·|slv/v − 0.1|·v · X_h = (v − Π(1+spy_r))×100 = qbatch_core.fund_from_path = q_switch.fund_ex_closed.
FF0 — 지배 결정이 늦음 · 미커밋 · 핀 불일치 · 대체 판 · 막힘 대체 · 없음인 보유월은 그 카드의 X 를 주 대조로 채운다. [선언] 급락 다리 ·
  반등 구간의 과반 승(FF2 c)도 같은 대체를 일간 경로에서 한다(그달의 날마다 대조의 일간 성장 · QF06 은 D 혼합의 일간 경로).
V0(EG30) — 관문이 없다. 관문 날짜마다 D0 · T+1 × 10 · 20bp 의 X · 하락월 X · H · 12개월 토막 · 급락 · 반등 구간을 보고만 한다.

  python build/qfwd_judge.py                      # --status (개수만)
  python build/qfwd_judge.py --gate FF1 [--card QF07|QF06|QF08]
  python build/qfwd_judge.py --selftest           # 합성 계열만 — 배관 · 닫힌 식 대조 · 관문 전 거절 · 창 고정 · FF0 일간 대체
"""
from __future__ import annotations
import datetime
import io
import json
import math
import os
import subprocess
import sys
import tempfile

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import qfwd_check as QC           # noqa: E402
import qfwd_ledger as L           # noqa: E402  달력 · 장부 표 · 체결 계획(표준 라이브러리)

FROZEN_STATS = {
    "build/eg30plus.py": "5688b266adece152d2dc72f911bb7a6ac977d628",
    "build/q_switch.py": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
    "build/qbatch_core.py": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d",
    "build/mech_episodes.py": "161080fd9244c060a7a94c559044de3e3ddcc27c"}
MECH_P3 = ("data/mech_episodes.json", "d67a2a74b486aff7f3a46d0f2a9bebe104df669f")
GATES = {"FF1": ["2028-11-01"],
         "FF2": ["2029-11-01", "2030-02-01", "2030-05-01", "2030-08-01", "2030-11-01",
                 "2031-02-01", "2031-05-01", "2031-08-01", "2031-11-01"]}
N_MIN = {"FF1": 24, "FF2": 36}
EV_MIN = {"crash": 3, "rebound": 3, "crash_m": 4, "surge_m": 4, "down": 10}
Q06_MIN = {"defense": 6, "defense_down": 2}
LATE_BLOCK, FIRST_N = 3, 36
LATE_KINDS = ("늦음", "미커밋", "대체 판", "막힘 대체", "없음")   # [DECL] FF2 를 막는 «늦은 결정» 의 갈래
HD = HU = 0.10
REB_TD, REB_WIN, REB_MIN = 63, 63, 3
ZZ_START = "2016-08-31"
C10, C20 = 0.0010, 0.0020
BETA = {"QF07": {"rule": "cards.Q07.rule.eval.sleeve_beta", "ref": "V0.eval.sleeve_beta",
                 "C3": "cards.Q07.controls.C3.eval.sleeve_beta"},
        "QF08": {"rule": "cards.Q08.rule.eval.sleeve_beta", "ref": "V0.eval.sleeve_beta",
                 "C3": "cards.Q08.controls.C3.eval.sleeve_beta"},
        "QF06": {"rule": "cards.Q06.rule.eval.sleeve_beta"},       # [DECL] QF06 의 H 는 Q06 표본 안 슬리브 베타로
        "V0": {"rule": "V0.eval.sleeve_beta"}}
QBATCH_BLOB = "01fefbf447fc699c8b4c9578a0ce9c2e0ca780f7"   # 사전등록 §2.1 — 결과 커밋 e19d13ad 의 data/_qbatch.json · β̂ 는 이 blob 에서만 읽는다
RULE_BOOK = {"QF07": "Q07V1", "QF08": "Q08V1"}
C3_BOOK = {"QF07": "Q07C3", "QF08": "Q08C3"}
_FROZEN_ROOT = None


def frozen_root(repo=REPO):
    """코드 핀의 build/ 를 임시 뿌리에 풀고(얼린 blob 18 단언) sys.path 맨 앞에 둔다 · 환경 핀 단언 — 한 과정에 한 번."""
    global _FROZEN_ROOT
    if _FROZEN_ROOT:
        return _FROZEN_ROOT
    import qfwd_adapter as A
    bad_mod = [m for m in ("eg30plus", "q_switch", "qbatch_core", "mech_episodes", "qg_lab") if m in sys.modules]
    if bad_mod:
        raise SystemExit("🚨 판정기 — 얼린 모듈이 이미 다른 곳에서 불려 있다: %s" % bad_mod)
    tmp = tempfile.mkdtemp(prefix="qfwd_judge_")
    import atexit
    atexit.register(QC.rmtree, tmp)
    A._archive_extract(repo, A.CODE_PIN, ["build/"], tmp)
    bad = []
    for rel, want in A.FROZEN_BLOBS.items():
        with io.open(os.path.join(tmp, *rel.split("/")), "rb") as fh:
            if A.blob_sha1(fh.read()) != want:
                bad.append(rel)
    if bad:
        raise SystemExit("🚨 판정기 — 코드 핀 뿌리의 얼린 blob 이 핀과 다르다: %s" % bad)
    import numpy
    import scipy
    import pandas
    env = {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__,
           "python": tuple(sys.version_info[:2])}
    wrong = [k for k in ("numpy", "scipy", "pandas", "python") if env[k] != A.ENV_PIN[k]]
    if wrong:
        raise SystemExit("🚨 판정기 — 환경 핀 불일치 %s (핀 %s)" % ({k: env[k] for k in wrong}, {k: A.ENV_PIN[k] for k in wrong}))
    sys.path.insert(0, os.path.join(tmp, "build"))
    _FROZEN_ROOT = tmp
    return tmp


def _frozen(name):
    """얼린 모듈을 코드 핀 뿌리에서 부른다(다른 곳에서 불렸으면 멈춘다)."""
    import importlib
    root = frozen_root()
    mod = importlib.import_module(name)
    if not os.path.abspath(mod.__file__).startswith(os.path.abspath(root)):
        raise SystemExit("🚨 판정기 — %s 가 코드 핀 뿌리가 아닌 %s 에서 불렸다" % (name, mod.__file__))
    return mod


def sigma_pre(repo=REPO):
    """P3 mech_episodes.json(코드 핀의 blob)의 σ_pre — SPY TR 월 수익 표준편차(2006-02 ~ 2016-08)."""
    oid = QC.rev_blob(repo, QC.CODE_PIN, MECH_P3[0])
    if oid != MECH_P3[1]:
        raise SystemExit("🚨 판정기 — %s:%s blob %s ≠ P3 %s" % (QC.CODE_PIN[:8], MECH_P3[0], oid, MECH_P3[1][:12]))
    return float(json.loads(QC.git(repo, "show", "%s:%s" % (QC.CODE_PIN, MECH_P3[0])))["sigma_pre"])


def qbatch_pinned(repo=REPO):
    """β̂ 의 정본 — 작업 사본이 아니라 핀 blob(QBATCH_BLOB)을 git 에서 읽는다(작업 사본의 _qbatch.json 이 뒤에 바뀌어도 같다)."""
    raw = subprocess.run(["git", "cat-file", "blob", QBATCH_BLOB], cwd=repo, capture_output=True).stdout
    if not raw:
        raise RuntimeError("_qbatch.json 핀 blob %s 을 git 에서 읽지 못했다" % QBATCH_BLOB[:12])
    return json.loads(raw.decode("utf-8"))


def _get(o, path):
    for k in path.split("."):
        if not isinstance(o, dict) or k not in o:
            return None
        o = o[k]
    return o


def gate_window(gd):
    """관문 날짜 gd 의 보유월 창 — FWD_M1 ~ gd 앞 달."""
    out, h, last = [], L.FWD_M1, L.mshift(gd[:7], -1)
    while h <= last:
        out.append(h)
        h = L.mshift(h, 1)
    return out


# ── 기록 → 판정 입력 ────────────────────────────────────────────────────────
class Fwd:
    """다섯 기록 파일 → 결정 · 시장 · 장부 표(열쇠마다 첫 줄). tcommit = {결정 seq: 커밋 시각(초)} — 없으면 t_eff 를 모른다(미커밋).
    hold_until — 보유월을 그 달까지만(관문 창)."""

    def __init__(self, recs, pins=None, tcommit=None, hold_until=None):
        self.pins = pins or {}
        self.recs = recs
        self.dec, self.mday, self.mmon, self.brow = {}, {}, {}, {}
        for r in recs["decisions.jsonl"]:
            if r.get("kind") == "decision":
                self.dec.setdefault((r["card"], r["m"]), r)
        for r in recs["market.jsonl"]:
            if r.get("kind") == "day":
                self.mday.setdefault(r["d"], r)
            elif r.get("kind") == "month":
                self.mmon.setdefault(r["h"], r)
        for r in recs["books.jsonl"]:
            if r.get("kind") == "month":
                self.brow.setdefault((r["book"], r["h"]), r)
        self.caps = {}
        for r in recs.get("px_capture.jsonl") or []:
            self.caps.setdefault(r.get("d"), r)
        self.tc = tcommit or {}
        self.twit = QC.witness_times(recs["decisions.jsonl"])
        hs, h = [], L.FWD_M1
        while h in self.mmon and all((b, h) in self.brow for b in L.BOOKS) and (hold_until is None or h <= hold_until):
            hs.append(h)
            h = L.mshift(h, 1)
        self.hold = hs

    @classmethod
    def load(cls, repo=REPO, qdir=None, hold_until=None):
        qdir = qdir or os.path.join(repo, QC.QREL)
        pins = QC.load_pins(repo, qdir) or {}
        ch = QC.chain_all(qdir, pins)
        errs = [e for r in ch.values() for e in r["errs"]] + QC.dup_check(ch)
        if errs:
            raise SystemExit("🚨 판정기 — 사슬 결함: %s" % errs[0])
        L.apply_calendar(ch["calendar.jsonl"]["recs"])
        rel = os.path.relpath(qdir, repo).replace(os.sep, "/")
        try:
            tc = {s: ct for s, (_c, ct) in QC.commit_map(repo, rel + "/decisions.jsonl", QC.main_ref(repo),
                                                          ch["decisions.jsonl"]["recs"]).items()}
        except Exception:
            tc = {}
        return cls({k: v["recs"] for k, v in ch.items()}, pins, tc, hold_until)

    def t_eff(self, r):
        t = QC.t_eff_ts(r, self.tc.get(r["seq"]), self.twit)
        return None if t is None else datetime.datetime.fromtimestamp(t, L.UTC)

    def governing(self, card, h):
        """보유월 h 를 다스리는 결정 달 — Q 카드는 h 앞의 마지막 분기 편입(2026-09 부터) · QF06 은 h − 1."""
        if L.CARDS[card]["due"] == "M":
            return L.mshift(h, -1)
        m = L.mshift(h, -1)
        while not L.is_formation(m):
            m = L.mshift(m, -1)
        return max(m, L.FIRST_M)

    def bad_decision(self, card, m):
        """FF0 — None 이면 온전 · 아니면 사유(없음 · 미커밋 · 늦음 · 핀 불일치 · 대체 판 · 막힘 대체)."""
        r = self.dec.get((card, m))
        if r is None:
            return "없음"
        te = self.t_eff(r)
        if te is None:
            return "미커밋"
        lim = L.pts(L.PRE_RECON_UNTIL) if m == L.FIRST_M else L.pts(r["deadline"])
        if (te > lim) if m == L.FIRST_M else (te >= lim):
            return "늦음"
        code = r.get("code") or {}
        ads = set(self.pins.get("adapter_blobs") or
                  ([(self.pins.get("qfwd_files") or {}).get(QC.ADAPTER_REL)] if (self.pins.get("qfwd_files") or {}).get(QC.ADAPTER_REL)
                   else []))
        if code.get("pin") != QC.CODE_PIN or (ads and code.get("adapter_blob") not in ads):
            return "핀 불일치"
        s = r.get("snap") or {}
        if s.get("fallback_from") or s.get("skipped"):
            return "대체 판"
        if s.get("degraded"):
            return "막힘 대체"
        return None

    def late_count(self, card):
        """첫 36개월(보유월 기준)을 다스리는 결정 가운데 늦은 것(LATE_KINDS) — 3 이상이면 FF2 를 막는다."""
        last_m = L.mshift(L.FWD_M1, FIRST_N - 2)
        if self.hold:                                   # 실현된 보유월을 다스리는 결정까지만(뒤 달은 아직 마감 전일 수 있다)
            last_m = min(last_m, self.governing(card, self.hold[-1]))
        else:
            return 0
        n, m = 0, L.ENTRY_M[L.CARDS[card]["due"]]
        while m <= last_m:
            if L.CARDS[card]["due"] == "M" or L.is_formation(m):
                if self.bad_decision(card, m) in LATE_KINDS:
                    n += 1
            m = L.mshift(m, 1)
        return n

    def states(self):
        """QF06 결정 달 → (st, s1, s2) — 1 = 공격(V0) · 0 = 수비(XBM)."""
        out = {}
        for (c, m), r in self.dec.items():
            s = r.get("states") or {}
            if c == "QF06" and "st" in s:
                out[m] = (int(s["st"]), int(s.get("s1", s["st"])), int(s.get("s2", s["st"])))
        return out


def bench_series(repo=REPO, fw=None, end_day=None):
    """지그재그 입력 ^GSPC PR — end_day 가 있으면 그날 포착 판(기록의 snap.commit)의 bench_px 를 그날까지 잘라서(관문 — 언제 돌려도 같다) ·
    없으면 가장 새 포착 판(상태 — 개수만). 포착 기록이 없으면 origin/main 끝에서 거슬러 첫 판."""
    cands = []
    if fw is not None and fw.caps:
        if end_day and end_day in fw.caps:
            cands.append(fw.caps[end_day]["snap"]["commit"])
        elif not end_day:
            cands.append(fw.caps[max(fw.caps)]["snap"]["commit"])
    if not cands and not end_day:
        ref = QC.main_ref(repo)
        cands = QC.git(repo, "log", "--first-parent", "--format=%H", "-n", "50", ref, "--", "data/bench_px.json", check=False).split()
    for c in cands:
        try:
            B = json.loads(QC.git(repo, "show", "%s:data/bench_px.json" % c))
        except Exception:
            continue
        D, P = list(B["dates"]), list(B["series"]["spx"]["px"])
        if end_day:
            k = sum(1 for d in D if d <= end_day)
            D, P = D[:k], P[:k]
        if P and P[-1] is not None:
            return D, P, c
    return None, None, None


def events(fw, D, P, sig):
    """사건 수(개수만) — 급락 다리 · 반등 · CRASH-M · SURGE-M · S&P 하락월 · QF06 수비 달."""
    ME = _frozen("mech_episodes")
    ev = {"crash": 0, "rebound": 0, "crash_m": 0, "surge_m": 0, "down": 0, "defense": 0, "defense_down": 0,
          "legs": [], "rebs": []}
    if D:
        legs, op = ME.zigzag(D, P, HD, HU, ZZ_START, D[-1])
        fl = [x for x in legs if x[0] == "crash" and x[1] >= L.ENTRY_DAY]
        rb = [r for r in ME.rebounds(D, P, legs, op, REB_TD) if any(r["a"] == x[2] for x in fl)]
        ev.update(crash=len(fl), rebound=len(rb), legs=[(x[1], x[2]) for x in fl], rebs=[(r["a"], r["b"]) for r in rb])
    st = fw.states()
    for h in fw.hold:
        mm = fw.mmon[h]
        ev["crash_m"] += mm["spy_m"] <= -sig
        ev["surge_m"] += mm["spy_m"] >= sig
        ev["down"] += mm["spx_m"] < 0
        s = st.get(L.mshift(h, -1))
        if s is not None and s[0] == 0:
            ev["defense"] += 1
            ev["defense_down"] += mm["spx_m"] < 0
    return ev


def gate_date(gate, today):
    """오늘 열 수 있는 관문 날짜(가장 최근) · 없으면 None."""
    ok = [g for g in GATES[gate] if g <= today]
    return ok[-1] if ok else None


def gate_allowed(gate, today, n_months, ev, card=None, blocked=False):
    """(허용, 사유) — 사유에는 숫자를 넣지 않는다(관문 전에는 아무 수도 내지 않는다)."""
    if gate_date(gate, today) is None:
        return False, "관문 날짜 전이다"
    if n_months < N_MIN[gate]:
        return False, "실현 개월이 모자란다"
    if gate == "FF2":
        if any(ev.get(k, 0) < v for k, v in EV_MIN.items()):
            return False, "사건 최소를 못 채웠다"
        if card == "QF06" and any(ev.get(k, 0) < v for k, v in Q06_MIN.items()):
            return False, "상관 놀람 카드의 수비 달 최소를 못 채웠다"
        if blocked:
            return False, "무결성 규칙 — 첫 서른여섯 달의 늦은 결정이 셋 이상이다"
    return True, "열림"


def judge_file_check(qdir, gate, gd):
    """(허용, 사유 · 경로) — 관문 날짜 하나에 판정 파일 하나 · 더 늦은 관문 날짜의 판정이 있으면 거절(숫자 없음)."""
    jd = os.path.join(qdir, "judge")
    p = os.path.join(jd, "%s-%s.json" % (gate, gd))
    if os.path.exists(p):
        return False, "이 관문 날짜는 이미 판정했다", p
    done = []
    if os.path.isdir(jd):
        for f in os.listdir(jd):
            if f.endswith(".json") and f[:3] in ("FF1", "FF2") and len(f) >= 19:
                done.append(f[4:14])
    if done and max(done) > gd:
        return False, "더 늦은 관문 날짜의 판정이 이미 있다", p
    return True, "열림", p


# ── ForwardFrame · 장부 (numpy) ─────────────────────────────────────────────
class ForwardFrame:
    """q_switch.Frame 의 자리를 전방 기록으로 — 첫 칸은 ENTRY_DAY(수익 0 · 진입 비용만)."""

    def __init__(self, fw):
        import numpy as np
        self.hold = list(fw.hold)
        self.months = [L.mshift(h, -1) for h in self.hold]
        days, mstart, spy, spx, rf_d = [], [], [], [], []
        for k, h in enumerate(self.hold):
            mstart.append(len(days))
            ds = L.month_tds(h)
            mm = fw.mmon[h]
            rfd = (1.0 + mm["rf_h"]) ** (1.0 / mm["n_h"]) - 1.0
            if k == 0:
                days.append(L.ENTRY_DAY)
                spy.append(0.0)
                spx.append(0.0)
                rf_d.append(0.0)
            for d in ds:
                days.append(d)
                spy.append(fw.mday[d]["spy"]["r"])
                spx.append(fw.mday[d]["spx"]["r"])
                rf_d.append(rfd)
        self.dates = days
        self.T = len(days)
        self.i0 = 0
        self.day = np.arange(1, self.T + 1)
        self.mstart = np.array(mstart, int)
        self.spy_r, self.spx_r, self.rf_d = np.array(spy), np.array(spx), np.array(rf_d)
        self.gIX = {"TR": np.array([1.0 + fw.mmon[h]["spy_m"] for h in self.hold]),
                    "PR": np.array([1.0 + fw.mmon[h]["spx_m"] for h in self.hold])}
        self.rf = np.array([fw.mmon[h]["rf_h"] for h in self.hold])
        self.dmask = self.gIX["PR"] < 1.0
        self.years = (self.T - 1) / 252.0
        self.pos = {d: j for j, d in enumerate(days)}
        mends = list(self.mstart[1:] - 1) + [self.T - 1]
        self.mend = np.array(mends, int)

    def day_mask(self, month_mask):
        """보유월 마스크 → 일간 마스크(그달의 모든 칸 · 첫 달은 ENTRY_DAY 칸 포함)."""
        import numpy as np
        out = np.zeros(self.T, bool)
        for k, b in enumerate(month_mask):
            a = int(self.mstart[k])
            e = int(self.mstart[k + 1]) if k + 1 < len(self.hold) else self.T
            out[a:e] = bool(b)
        return out


class FBook:
    """기록된 장부 월 줄 → q_switch.Book 모양(lg0 · lf[c] · cash · 회전)."""

    def __init__(self, name, fw, F):
        import numpy as np
        g, tau = [], []
        for k, h in enumerate(F.hold):
            r = fw.brow[(name, h)]
            gg = list(r["g0"])
            tt = [0.0] * len(gg)
            for e in r["reb"]:
                tt[e["i"]] = e["tau"]
            if k == 0 and r["days"][0] != L.ENTRY_DAY:
                gg, tt = [1.0] + gg, [0.0] + tt          # T+1 장부 — 진입일 칸은 비어 있다
            g += gg
            tau += tt
        if len(g) != F.T:
            raise SystemExit("🚨 판정기 — 장부 %s 일수 %d ≠ 틀 %d" % (name, len(g), F.T))
        self.name, self.cash = name, False
        self.g0 = np.array(g)
        self.lg0 = np.log(self.g0)
        self.tau = np.array(tau)
        self.lf = {c: np.log(1.0 - c * self.tau) for c in (C10, C20)}
        self.turn = float(self.tau.sum() / 2.0 / F.years)


def tbill(F):
    import numpy as np
    bk = FBook.__new__(FBook)
    bk.name, bk.cash = "T-bill", True
    bk.g0 = 1.0 + F.rf_d
    bk.lg0 = np.log(bk.g0)
    bk.tau = np.zeros(F.T)
    bk.lf = {C10: np.zeros(F.T), C20: np.zeros(F.T)}
    bk.turn = 0.0
    return bk


def fund_daily(F, lg, c):
    """펀드 일간 경로(월초 0.9/0.1 · 월말 되돌림 비용) — 구간 초과(급락 다리 · 반등)용. 첫 칸 앞 = 1."""
    import numpy as np
    fp = np.empty(F.T)
    v = 1.0
    ends = set(int(x) for x in F.mend)
    ixv, slv = 0.9 * v, 0.1 * v
    for j in range(F.T):
        ixv *= 1.0 + F.spy_r[j]
        slv *= math.exp(lg[j])
        v = ixv + slv
        if j in ends:
            v -= c * 2.0 * abs(slv / v - 0.1) * v
            ixv, slv = 0.9 * v, 0.1 * v
        fp[j] = v
    return fp


def mix_daily(F, e, O, D, c):
    """정적 혼합 D(공격 몫 e)의 슬리브 일간 로그 성장 — 월 안 흘러감 · 월말(마지막 달 빼고) 다음 몫 e 로 되맞춤 비용을 그달 마지막 칸에.
    월 합 = log(q_switch.mix_ex_closed 의 슬리브 월 성장) — FF0 이 QF06 의 늦은 달을 D 로 채울 때 급락 · 반등 구간에도 같은 대체를 쓴다."""
    import numpy as np
    lO = O.lg0 + O.lf.get(c, 0.0)
    lD = D.lg0 + D.lf.get(c, 0.0)
    out = np.empty(F.T)
    nM = len(F.hold)
    for k in range(nM):
        a = int(F.mstart[k])
        b = int(F.mstart[k + 1]) if k + 1 < nM else F.T
        cO = np.exp(np.cumsum(lO[a:b]))
        cD = np.exp(np.cumsum(lD[a:b]))
        v = e * cO + (1.0 - e) * cD
        lg = np.diff(np.log(np.concatenate([[1.0], v])))
        if k + 1 < nM:
            g = float(v[-1])
            cost = c * ((0.0 if O.cash else abs(e * g - e * cO[-1])) + (0.0 if D.cash else abs((1 - e) * g - (1 - e) * cD[-1])))
            lg[-1] += math.log((g - cost) / g)
        out[a:b] = lg
    return out


def x_of(F, lg, c):
    import numpy as np
    SW = _frozen("q_switch")
    return SW.fund_ex_closed(F, np.exp(SW.month_sums(F, lg)), "TR", c)


def seg_wins(F, fp, segs):
    """구간 [a, b] 마다 펀드 − SPY TR (일간 경로) > 0 인가 — 보유 창 밖이면 뺀다."""
    out = []
    for a, b in segs:
        if a not in F.pos or b not in F.pos:
            continue
        ja, jb = F.pos[a], F.pos[b]
        f = fp[jb] / fp[ja] - 1.0
        s = float(math.prod(1.0 + x for x in F.spy_r[ja + 1:jb + 1])) - 1.0
        out.append(f - s > 0)
    return out


def blocks12(F, X):
    """겹치지 않는 12개월 토막(1개월째부터 · 완결만) — 승 = Π(1+펀드) > Π(1+SPY TR)."""
    fund = F.gIX["TR"] + X / 100.0
    w = []
    for k in range(0, len(X) - 11, 12):
        w.append(float(math.prod(fund[k:k + 12])) > float(math.prod(F.gIX["TR"][k:k + 12])))
    return w


def pos_T1(F, fw, st_of):
    """QF06 T+1 위치 — 수익일 j 의 위치 = T1 체결일이 j 앞인 가장 늦은 결정의 상태(그 전은 첫 결정의 상태 · [DECL])."""
    import numpy as np
    ex = []
    for h in F.hold:
        for e in fw.brow[("XBM.T1", h)]["reb"]:
            if e["src"]["card"] == "QF06" and e["src"]["m"] in st_of:
                ex.append((e["d"], e["src"]["m"]))
    ex.sort()
    if not ex:
        return None
    pos = np.empty(F.T, np.int8)
    k, cur = 0, st_of[ex[0][1]]
    for j, d in enumerate(F.dates):
        while k < len(ex) and ex[k][0] < d:
            cur = st_of[ex[k][1]]
            k += 1
        pos[j] = cur
    return pos


def pos_D0(F, st_of):
    """d_m 종가 행 — 보유월 h 의 모든 수익일 = 상태(h − 1) (pos_from_monthly 의 뜻)."""
    import numpy as np
    pos = np.empty(F.T, np.int8)
    for k, m in enumerate(F.months):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < len(F.months) else F.T
        pos[a:b] = st_of.get(m, 1)
    return pos


def sleeve_turn(pos, bO, bD, F, c):
    """교체 슬리브의 연 편도 회전 — q_switch.switch_fr 의 (own + 2·n_switch)/2/years."""
    import numpy as np
    SW = _frozen("q_switch")
    _lg, sw = SW.sleeve_daily(pos, bO, bD, c)
    nxt = np.append(pos[1:], pos[-1])
    own = 0.0
    for bk, flag in ((bO, 1), (bD, 0)):
        tt = (1.0 - np.exp(bk.lf[c])) / c
        own += float((tt * ((nxt == flag) & ~sw)).sum())
    return (own + 2.0 * int(sw.sum())) / 2.0 / F.years, int(sw.sum())


def _py(o):
    """numpy 값 → JSON 원형(bool · int · float · list)."""
    if isinstance(o, dict):
        return {str(k): _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            return o.item()
        except Exception:
            pass
    if isinstance(o, float) and o != o:
        return None
    return o


def _m(x, mask=None):
    import numpy as np
    x = np.asarray(x, float)
    if mask is not None:
        x = x[np.asarray(mask, bool)]
    return float(x.mean()) if len(x) else None


def card_stats(card, fw, F, betas, ev, sig, fp_segs=True):
    """카드 하나의 FF1 · FF2 통계 · 판정(관문에서만 부른다)."""
    import numpy as np
    E = _frozen("eg30plus")
    SW = _frozen("q_switch")
    B = {b: FBook(b, fw, F) for b in L.BOOKS}
    spy_ex = (F.gIX["TR"] - 1.0 - F.rf) * 100.0
    dm = F.dmask
    crash_m = (F.gIX["TR"] - 1.0) <= -sig
    surge_m = (F.gIX["TR"] - 1.0) >= sig
    out = {"card": card, "n": len(F.hold), "hold": [F.hold[0], F.hold[-1]]}
    bad = np.array([fw.bad_decision(card, fw.governing(card, h)) is not None for h in F.hold])
    bad_day = F.day_mask(bad)
    out["ff0_replaced"] = int(bad.sum())
    out["late_first36"] = fw.late_count(card)
    if card in ("QF07", "QF08"):
        rb, cb = RULE_BOOK[card], C3_BOOK[card]
        X = {(b, c): x_of(F, B[b].lg0 + B[b].lf[c], c) for b in (rb + ".D0", rb + ".T1", cb + ".D0", "V0.D0", "V0.T1")
             for c in (C10, C20)}
        br, bref, bc3 = (betas.get("rule"), betas.get("ref"), betas.get("C3"))
        xr = np.where(bad, X[("V0.D0", C10)], X[(rb + ".D0", C10)])
        xv = X[("V0.D0", C10)]
        xc = X[(cb + ".D0", C10)]
        dB = (xr - xv) - 0.1 * (br - bref) * spy_ex
        dBc = (xr - xc) - 0.1 * (br - bc3) * spy_ex
        H = xr - 0.1 * (br - 1.0) * spy_ex
        cum = float(np.prod(F.gIX["TR"] + xr / 100.0) - np.prod(F.gIX["TR"] + xv / 100.0))
        out.update(X_mean=_m(xr), X_nw_t=E.nw_t(xr), dB_mean=_m(dB), dB_nw_t=E.nw_t(dB), dB_down=_m(dB, dm),
                   dB_down_t=E.down_t(dB, dm), X_crash_m=_m(xr, crash_m), X_surge_m=_m(xr, surge_m), X_down=_m(xr, dm),
                   H_down=_m(H, dm), cum_FF1=cum, dBc3_down=_m(dBc, dm), V1_minus_C3=_m(xr - xc),
                   V1_minus_C3_nw_t=E.nw_t(xr - xc), V1_minus_V0=_m(xr - xv), V1_minus_V0_nw_t=E.nw_t(xr - xv))
        # FF0 일간 대체 — 늦은 달의 날마다 V0.D0 의 일간 성장(급락 · 반등 구간 과반 승에 쓴다)
        lg_rule = np.where(bad_day, B["V0.D0"].lg0 + B["V0.D0"].lf[C10], B[rb + ".D0"].lg0 + B[rb + ".D0"].lf[C10])
        x20 = np.where(bad, X[("V0.D0", C20)], X[(rb + ".D0", C20)])
        dB20 = (x20 - X[("V0.D0", C20)]) - 0.1 * (br - bref) * spy_ex
        xt = np.where(bad, X[("V0.T1", C10)], X[(rb + ".T1", C10)])
        dBt = (xt - X[("V0.T1", C10)]) - 0.1 * (br - bref) * spy_ex
        out.update(X20_mean=_m(x20), dB20_mean=_m(dB20), XT1_mean=_m(xt), dBT1_mean=_m(dBt),
                   turn=B[rb + ".D0"].turn, turn_V0=B["V0.D0"].turn)
    else:
        st = fw.states()
        s0 = {m: v[0] for m, v in st.items()}
        s1 = {m: v[1] for m, v in st.items()}
        s2 = {m: v[2] for m, v in st.items()}
        O, D = B["V0.T1"], B["XBM.T1"]
        pos = pos_T1(F, fw, s0)
        if pos is None:
            raise SystemExit("🚨 판정기 — XBM.T1 장부에 QF06 체결이 하나도 없다")
        res = {}
        for c in (C10, C20):
            lg, sw = SW.sleeve_daily(pos, O, D, c)
            xr = x_of(F, lg, c)
            e_f = float(pos.mean())
            xd = SW.mix_ex_closed(F, e_f, SW.month_growth(F, O, c), SW.month_growth(F, D, c), O.cash, D.cash, "TR", c)
            res[c] = (np.where(bad, xd, xr), xd, lg, e_f)
        xr, xd, lg_sw, e_f = res[C10]
        # FF0 일간 대체 — 늦은 달의 날마다 D 혼합의 일간 성장
        lg_rule = np.where(bad_day, mix_daily(F, e_f, O, D, C10), lg_sw)
        dD = xr - xd
        br = betas.get("rule")
        H = (xr - 0.1 * (br - 1.0) * spy_ex) if br is not None else None
        tw = {}
        for nm, so in (("T1", s1), ("T2", s2)):
            p = pos_T1(F, fw, so)
            lg, _ = SW.sleeve_daily(p, O, D, C10)
            tw[nm] = x_of(F, lg, C10)
        lgb, _ = SW.sleeve_daily(pos, O, tbill(F), C10)
        pd0 = pos_D0(F, s0)
        lgd, _ = SW.sleeve_daily(pd0, B["V0.D0"], B["XBM.D0"], C10)
        turn, n_sw = sleeve_turn(pos, O, D, F, C10)
        nxt = np.append(pos[1:], pos[-1])
        outs = list(np.flatnonzero((pos == 1) & (nxt == 0)))          # 공격 → 수비 교체 종가(틀 칸 번호)
        rm = [h for k, h in enumerate(F.hold)                         # q_switch.rebound_miss 와 같은 뜻 — 칸 = 거래일
              if surge_m[k] and any(0 <= int(F.mstart[k]) - int(o) <= REB_WIN for o in outs)]
        hp = {h: k for k, h in enumerate(F.hold)}
        rm_mean = _m([dD[hp[h]] for h in rm]) if rm else None
        cum = float(np.prod(F.gIX["TR"] + xr / 100.0) - np.prod(F.gIX["TR"] + xd / 100.0))
        out.update(X_mean=_m(xr), X_nw_t=E.nw_t(xr), dD_mean=_m(dD), dD_nw_t=E.nw_t(dD), dD_down=_m(dD, dm),
                   dD_down_t=E.down_t(dD, dm), X_crash_m=_m(xr, crash_m), X_surge_m=_m(xr, surge_m), X_down=_m(xr, dm),
                   H_down=_m(H, dm) if H is not None else None, cum_FF1=cum, e_fwd=e_f, n_switch=n_sw,
                   X20_mean=_m(res[C20][0]), dD20_mean=_m(res[C20][0] - res[C20][1]),
                   rule_minus_T1twin=_m(xr - tw["T1"]), rule_minus_T2twin=_m(xr - tw["T2"]),
                   tbill_arm_mean=_m(x_of(F, lgb, C10)), dm_close_row_mean=_m(x_of(F, lgd, C10)),
                   turn=turn, turn_V0=O.turn, rebound_miss={"months": rm, "n": len(rm), "mean_dD": rm_mean,
                                                            "applies": len(rm) >= REB_MIN,
                                                            "ok": None if len(rm) < REB_MIN else bool(rm_mean >= 0)})
    if fp_segs:
        fp = fund_daily(F, lg_rule, C10)
        cw, rw = seg_wins(F, fp, ev.get("legs") or []), seg_wins(F, fp, ev.get("rebs") or [])
        out.update(crash_wins=[int(sum(cw)), len(cw)], rebound_wins=[int(sum(rw)), len(rw)])
    bw = blocks12(F, xr)
    out["blocks12"] = [int(sum(bw)), len(bw)]
    out["_lg_rule_ff0"] = lg_rule                       # 자가 시험용(판정 파일에는 쓰지 않는다)
    return out


def v0_report(fw, F, beta_v0, ev, sig):
    """[DECL] V0(EG30) 자신의 전방 기록 — 관문 없음 · 보고만. D0 · T+1 × 10 · 20bp 마다 X · 하락월 X · H · 12개월 토막 · 급락 · 반등 구간.
    V0 는 대조가 없어 FF0 로 채우지 않는다 — 온전하지 않은 결정이 다스린 달 수를 따로 적는다."""
    import numpy as np
    E = _frozen("eg30plus")
    spy_ex = (F.gIX["TR"] - 1.0 - F.rf) * 100.0
    dm = F.dmask
    crash_m = (F.gIX["TR"] - 1.0) <= -sig
    surge_m = (F.gIX["TR"] - 1.0) >= sig
    out = {"card": "V0", "n": len(F.hold), "hold": [F.hold[0], F.hold[-1]], "beta": beta_v0,
           "bad_months": int(sum(1 for h in F.hold if fw.bad_decision("V0", fw.governing("V0", h)) is not None)),
           "late_first36": fw.late_count("V0"), "rows": {}}
    for row in ("D0", "T1"):
        bk = FBook("V0." + row, fw, F)
        for c in (C10, C20):
            lg = bk.lg0 + bk.lf[c]
            X = x_of(F, lg, c)
            H = (X - 0.1 * (beta_v0 - 1.0) * spy_ex) if beta_v0 is not None else None
            fp = fund_daily(F, lg, c)
            cw, rw = seg_wins(F, fp, ev.get("legs") or []), seg_wins(F, fp, ev.get("rebs") or [])
            bw = blocks12(F, X)
            out["rows"]["%s_%dbp" % (row, round(c * 1e4))] = {
                "X_mean": _m(X), "X_nw_t": E.nw_t(X), "X_down": _m(X, dm), "H_down": _m(H, dm) if H is not None else None,
                "X_crash_m": _m(X, crash_m), "X_surge_m": _m(X, surge_m), "blocks12": [int(sum(bw)), len(bw)],
                "crash_wins": [int(sum(cw)), len(cw)], "rebound_wins": [int(sum(rw)), len(rw)], "turn": bk.turn,
                "cum": float(np.prod(F.gIX["TR"] + X / 100.0) - np.prod(F.gIX["TR"]))}
    return out


def verdict(card, gate, s):
    """FF1 · FF2 판정(가) ~ (사) — 값이 없으면 그 항목은 통과로 치지 않는다."""
    def gt(x, y=0.0):
        return x is not None and x > y

    def ge(x, y=0.0):
        return x is not None and x >= y
    ff1 = gt(s.get("cum_FF1"))
    if gate == "FF1" or card == "QF08":
        return {"FF1": ff1, "pass": ff1 if card != "QF08" else None}
    maj = lambda w: w[1] > 0 and w[0] > w[1] / 2.0
    a = gt(s["X_mean"]) and ge(s["X_nw_t"], 1.0)
    if card == "QF07":
        b = ge(s["dB_nw_t"], 1.0) and gt(s["dB_down"])
        f = gt(s["X20_mean"]) and gt(s["dB20_mean"]) and gt(s["XT1_mean"]) and gt(s["dBT1_mean"]) and \
            s["turn"] <= 2.0 * s["turn_V0"]
        g = gt(s["dBc3_down"])
    else:
        b = ge(s["dD_nw_t"], 1.0) and gt(s["dD_down"])
        f = gt(s["X20_mean"]) and gt(s["dD20_mean"]) and s["turn"] <= 2.0 * s["turn_V0"]
        g = gt(s["rule_minus_T1twin"])
    c = gt(s["X_crash_m"]) and gt(s["X_surge_m"]) and maj(s.get("crash_wins", [0, 0])) and maj(s.get("rebound_wins", [0, 0]))
    d = ge(s["X_down"]) and gt(s["H_down"])
    e = maj(s["blocks12"])
    v = {"FF1": ff1, "a": a, "b": b, "c": c, "d": d, "e": e, "f": f, "g": g}
    if card == "QF06":
        rm = s.get("rebound_miss") or {}
        v["rebound_miss"] = rm.get("ok") is not False
    v["pass"] = all(v.values())
    return v


# ── 명령 ────────────────────────────────────────────────────────────────────
def status(repo=REPO, out=print):
    fw = Fwd.load(repo)
    n = len(fw.hold)
    out("QFWD 판정기 상태 — 개수만(관문 날짜 전에는 수익 · 초과 · t 를 찍지 않는다)")
    out("  실현 전방 개월 %d · FF1(24)까지 %d · FF2(36)까지 %d" % (n, max(0, 24 - n), max(0, 36 - n)))
    for card in ("QF07", "QF06", "QF08", "V0"):
        rep = sum(1 for h in fw.hold if fw.bad_decision(card, fw.governing(card, h)) is not None)
        lc = fw.late_count(card)
        out("  %-5s 늦은 결정(첫 36개월) %d · FF0 대체 달 %d · FF2 %s" % (card, lc, rep, "막힘" if lc >= LATE_BLOCK else "열림 가능"))
    D, P, c = bench_series(repo, fw)
    sig = sigma_pre(repo)
    ev = events(fw, D, P, sig)
    out("  사건(진입 뒤) — 급락 다리 %d/%d · 반등 %d/%d · CRASH-M %d/%d · SURGE-M %d/%d · S&P 하락월 %d/%d"
        % (ev["crash"], EV_MIN["crash"], ev["rebound"], EV_MIN["rebound"], ev["crash_m"], EV_MIN["crash_m"],
           ev["surge_m"], EV_MIN["surge_m"], ev["down"], EV_MIN["down"]))
    out("  QF06 수비 달 %d/%d · 그중 하락월 %d/%d · 지그재그 판 %s"
        % (ev["defense"], Q06_MIN["defense"], ev["defense_down"], Q06_MIN["defense_down"], (c or "-")[:12]))
    today = datetime.datetime.now(L.UTC).date().isoformat()
    for g in ("FF1", "FF2"):
        gd = gate_date(g, today)
        out("  관문 %s — %s" % (g, ("열 수 있는 날짜 %s(창 %s ~ %s)" % (gd, gate_window(gd)[0], gate_window(gd)[-1])) if gd
                               else "첫 날짜 %s 전" % GATES[g][0]))
    QC.run_checks(repo, full=False, out=out)
    return 0


def gate(g, card, repo=REPO, out=print, today=None, qdir=None):
    today = today or datetime.datetime.now(L.UTC).date().isoformat()
    gd = gate_date(g, today)
    if gd is None:
        out("관문 거절 — 관문 날짜 전이다 (아무 수도 찍지 않는다)")
        return 2
    qdir = qdir or os.path.join(repo, QC.QREL)
    okf, why, p = judge_file_check(qdir, g, gd)
    if not okf:
        out("관문 거절 — %s (아무 수도 찍지 않는다)" % why)
        return 2
    win = gate_window(gd)
    fw = Fwd.load(repo, qdir, hold_until=win[-1])
    if fw.hold != win:
        out("관문 거절 — 관문 창의 달이 아직 다 실현되지 않았다 (아무 수도 찍지 않는다)")
        return 2
    D, P, bc = bench_series(repo, fw, end_day=L.d_m(win[-1]))
    if not D:
        out("관문 거절 — 창 끝 날 포착 판의 ^GSPC 를 읽지 못했다 (아무 수도 찍지 않는다)")
        return 2
    sig = sigma_pre(repo)
    ev = events(fw, D, P, sig)
    cards = [card] if card else ["QF07", "QF06", "QF08"]
    okc = [c for c in cards if gate_allowed(g, today, len(fw.hold), ev, c, fw.late_count(c) >= LATE_BLOCK)[0]]
    v0_ok = len(fw.hold) >= N_MIN[g]
    if not okc and not v0_ok:
        out("관문 거절 — %s (아무 수도 찍지 않는다)" % gate_allowed(g, today, len(fw.hold), ev, cards[0],
                                                           fw.late_count(cards[0]) >= LATE_BLOCK)[1])
        return 2
    qb = qbatch_pinned(repo)
    F = ForwardFrame(fw)
    doc = {"v": 2, "gate": g, "date": today, "gate_date": gd, "window": [win[0], win[-1]], "n": len(fw.hold),
           "qbatch_blob": QBATCH_BLOB, "bench_commit": bc, "frozen_root_pin": QC.CODE_PIN,
           "events": {k: v for k, v in ev.items()}, "cards": {}, "refused": {}}
    for c in cards:
        if c not in okc:
            doc["refused"][c] = gate_allowed(g, today, len(fw.hold), ev, c, fw.late_count(c) >= LATE_BLOCK)[1]
    for c in okc:
        betas = {k: _get(qb, p_) for k, p_ in BETA[c].items()}
        s = card_stats(c, fw, F, betas, ev, sig)
        s.pop("_lg_rule_ff0", None)
        doc["cards"][c] = {"betas": betas, "stats": s, "verdict": verdict(c, g, s)}
    if v0_ok:
        doc["V0"] = v0_report(fw, F, _get(qb, BETA["V0"]["rule"]), ev, sig)
    doc["family_rule"] = "Q07 · Q08 가운데 하나만 채택 — Q08 은 측정 팔(관문 없음)"
    doc = _py(doc)
    L.write_once(p, doc)
    for c, x in doc["cards"].items():
        out("관문 %s %s — %s · %s" % (g, c, "통과" if x["verdict"].get("pass") else ("보고만" if c == "QF08" else "기각"),
                                    " · ".join("%s %s" % (k, "✓" if v else "✗") for k, v in x["verdict"].items() if k != "pass")))
    for c, why in doc["refused"].items():
        out("관문 %s %s — 열리지 않음(%s)" % (g, c, why))
    if "V0" in doc:
        out("관문 %s V0 — EG30 전방 기록 보고(관문 없음)" % g)
    out("→ %s" % os.path.relpath(p, repo))
    return 0


# ── 자가 시험 (합성 계열만) ─────────────────────────────────────────────────
def _synthetic(n_months=26, seed=7, late=None):
    """합성 기록 — 원장 엔진(run_book)으로 만든 12장부 · 시장 줄 · 결정 줄(QF06 상태 포함). 실제 가격은 읽지 않는다."""
    import random
    rnd = random.Random(seed)
    hold, h = [], L.FWD_M1
    for _ in range(n_months):
        hold.append(h)
        h = L.mshift(h, 1)
    days_all = [L.ENTRY_DAY] + [d for h in hold for d in L.month_tds(h)]
    keys = ["S%02d" % j for j in range(12)]
    rets = {k: {d: rnd.gauss(0.0004, 0.018) for d in days_all} for k in keys}
    mkt = {d: (rnd.gauss(0.0004, 0.011), rnd.gauss(0.0003, 0.011)) for d in days_all}
    recs = {n: [] for n in QC.JSONL}
    dec = {}
    seq = 0

    def target(ks):
        w = [rnd.random() + 0.3 for _ in ks]
        s = sum(w)
        return {"w": {k: x / s for k, x in zip(ks, w)}, "names": {k: k for k in ks}}
    months = sorted({L.mshift(hh, -1) for hh in hold} | {L.FIRST_M})
    for m in months:
        for c in L.due_cards(m):
            tg = {"V0": {"V0": target(rnd.sample(keys, 6))},
                  "QF07": {"V1": target(rnd.sample(keys, 6)), "C3": target(rnd.sample(keys, 6))},
                  "QF08": {"V1": target(rnd.sample(keys, 6)), "C3": target(rnd.sample(keys, 6))},
                  "QF06": {"XBM": target(rnd.sample(keys, 5))}}[c]
            dl = L.deadline(c, m)
            td = dl - datetime.timedelta(hours=10)
            if late and (c, m) in late:
                td = dl + datetime.timedelta(hours=1)
            r = {"kind": "decision", "card": c, "m": m, "seq": seq, "deadline": L.iso(dl), "t_decided": L.iso(td), "runner": "gha",
                 "code": {"pin": QC.CODE_PIN}, "snap": {"commit": "0" * 40, "fallback_from": None},
                 "targets": tg, "targets_sha": {k: QC.obj_sha(v) for k, v in tg.items()}}
            if c == "QF06":
                r["states"] = {"st": int(rnd.random() < 0.7), "s1": int(rnd.random() < 0.6), "s2": int(rnd.random() < 0.8)}
            recs["decisions.jsonl"].append(r)
            dec[(c, m)] = r
            seq += 1
    tc = {r["seq"]: int((L.pts(r["t_decided"]) + datetime.timedelta(minutes=3)).timestamp())
          for r in recs["decisions.jsonl"]}
    caps = {}
    for d in days_all:
        caps[d] = {"r": {k: rets[k][d] for k in keys}, "ok_buy": {k: True for k in keys}, "seq": 0}
        recs["market.jsonl"].append({"kind": "day", "d": d, "spy": {"r": mkt[d][0]}, "spx": {"r": mkt[d][1]}})
    state = {b: ({}, 1.0) for b in L.BOOKS}
    for h in hold:
        n_h = len(L.month_tds(h))
        rf_h = 0.003
        for b, (card, tname, _cad, row) in L.BOOKS.items():
            pseudo = h == L.FWD_M1 and row == "D0"
            days = ([L.ENTRY_DAY] if pseudo else []) + L.month_tds(h)
            rebs, meta = {}, {}
            for m in L.book_months(card, h):
                r = dec.get((card, m))
                if r is None:
                    continue
                pl = L.plan(card, m, row)
                te = max(L.pts(r["t_decided"]), datetime.datetime.fromtimestamp(tc[r["seq"]], L.UTC))
                day, lx, stt = L.resolve(pl, te)
                if stt == "resolved" and day in days:
                    rebs[day] = {"w": r["targets"][tname]["w"]}
                    meta[day] = (r, lx, pl)
            w0, c0 = state[b]
            o = L.run_book(days, w0, c0, caps, rebs, rf_h, n_h, pseudo_first=pseudo)
            reb = [dict(x, src={"card": card, "m": meta[x["d"]][0]["m"], "seq": meta[x["d"]][0]["seq"], "target": tname,
                                "sha": meta[x["d"]][0]["targets_sha"][tname]}, sched=meta[x["d"]][2]["sched"],
                        late_exec=meta[x["d"]][1]) for x in o["reb"]]
            recs["books.jsonl"].append({"kind": "month", "book": b, "h": h, "days": days, "g0": o["g0"], "reb": reb,
                                        "w_end": o["w_end"], "cash_end": o["cash_end"], "rf_h": rf_h, "n_h": n_h})
            state[b] = (o["w_end"], o["cash_end"])
        ds = L.month_tds(h)
        recs["market.jsonl"].append({"kind": "month", "h": h, "n_h": n_h, "rf_h": rf_h,
                                     "spy_m": math.prod(1 + mkt[d][0] for d in ds) - 1,
                                     "spx_m": math.prod(1 + mkt[d][1] for d in ds) - 1})
    return recs, tc


def selftest():
    import types
    import numpy as np
    fails = []

    def ok(cond, what):
        print(("  ✓ " if cond else "  ✗ ") + what)
        if not cond:
            fails.append(what)
    root = frozen_root()
    SW = _frozen("q_switch")
    Q = _frozen("qbatch_core")
    E = _frozen("eg30plus")
    ok(all(os.path.abspath(m.__file__).startswith(os.path.abspath(root)) for m in (SW, Q, E)),
       "얼린 통계 모듈을 코드 핀 뿌리(얼린 blob 18 단언)에서 불렀다 · 환경 핀 일치")
    qb = qbatch_pinned()
    ok(all(isinstance(_get(qb, p), float) for c in BETA for p in BETA[c].values()),
       "β̂ 경로 %d개 — 핀 blob %s 에 모두 있다(읽기만 · 값은 찍지 않는다)"
       % (sum(len(v) for v in BETA.values()), QBATCH_BLOB[:8]))
    recs, tc = _synthetic()
    fw = Fwd(recs, {}, tc)
    F = ForwardFrame(fw)
    ok(len(fw.hold) == 26 and F.T == 1 + sum(len(L.month_tds(h)) for h in fw.hold), "합성 26개월 · 틀 일수(진입일 칸 포함)")
    bk = FBook("Q07V1.D0", fw, F)
    bt = FBook("XBM.T1", fw, F)
    ok(abs(bk.tau[0] - 1.0) < 1e-12 and bt.tau[0] == 0.0 and abs(bt.tau[1] - 1.0) < 1e-12,
       "진입 — D0 은 ENTRY_DAY 에 tau 1 · T1 은 다음 날")
    # 펀드 회계 — 날마다 굴린 경로 = fund_ex_closed = qbatch_core.fund_from_path
    for c in (0.0, C10, C20):
        lg = bk.lg0 + (bk.lf[c] if c else 0.0)
        xc = SW.fund_ex_closed(F, np.exp(SW.month_sums(F, lg)), "TR", c)
        fp = fund_daily(F, lg, c)
        starts = np.concatenate([[1.0], fp[F.mend[:-1]]])
        xd = (fp[F.mend] / starts - F.gIX["TR"]) * 100.0
        ix = np.cumprod(np.concatenate([[1.0], 1.0 + F.spy_r]))
        G = types.SimpleNamespace(IX_TR=ix, IX_PR=ix, me={m: int(F.mstart[k]) for k, m in enumerate(F.months)})
        G.me[F.hold[-1]] = F.T
        path = {i: float(v) for i, v in enumerate(np.cumprod(np.concatenate([[1.0], np.exp(lg)])))}
        fr = Q.fund_from_path(G, {"path": path}, F.months, cost=c, basis="TR")
        ok(np.max(np.abs(xd - xc)) < 1e-10 and np.max(np.abs(fr["ex"] - xc)) < 1e-10,
           "펀드 회계 %gbp — 일간 경로 = fund_ex_closed = fund_from_path (최대차 %.1e)"
           % (c * 1e4, max(np.max(np.abs(xd - xc)), np.max(np.abs(fr["ex"] - xc)))))
    # 장부 월 성장 = 기록 g_c 의 곱
    r0 = fw.brow[("Q07V1.D0", L.FWD_M1)]
    g10 = math.prod(L.g_cost(r0["g0"], r0["reb"], C10))
    ok(abs(SW.month_growth(F, bk, C10)[0] - g10) < 1e-12, "month_growth = 기록 g_c 의 곱(첫 달)")
    # D 닫힌 식 = 날마다 굴린 혼합 · mix_daily 의 월 합 = mix_ex_closed
    O, D = FBook("V0.T1", fw, F), bt
    e = 0.63
    xd_closed = SW.mix_ex_closed(F, e, SW.month_growth(F, O, C10), SW.month_growth(F, D, C10), False, False, "TR", C10)
    vals = []
    for k in range(len(F.hold)):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < len(F.hold) else F.T
        cO = math.exp(float((O.lg0 + O.lf[C10])[a:b].sum()))
        cD = math.exp(float((D.lg0 + D.lf[C10])[a:b].sum()))
        g = e * cO + (1 - e) * cD
        cost = 0.0 if k + 1 == len(F.hold) else C10 * (abs(e * g - e * cO) + abs((1 - e) * g - (1 - e) * cD))
        vals.append(g - cost)
    ok(np.max(np.abs(SW.fund_ex_closed(F, np.array(vals), "TR", C10) - xd_closed)) < 1e-12, "D = mix_ex_closed(ē) 닫힌 식")
    xm = SW.fund_ex_closed(F, np.exp(SW.month_sums(F, mix_daily(F, e, O, D, C10))), "TR", C10)
    ok(np.max(np.abs(xm - xd_closed)) < 1e-10, "D 의 일간 경로(mix_daily) — 월 합 = mix_ex_closed (최대차 %.1e)"
       % np.max(np.abs(xm - xd_closed)))
    # 배관 — 두 카드 통계 · 판정 모양 · V0 보고
    ev = {"legs": [(F.dates[5], F.dates[40])], "rebs": [(F.dates[40], F.dates[90])]}
    s7 = card_stats("QF07", fw, F, {"rule": 1.05, "ref": 1.1, "C3": 0.9}, ev, 0.0429)
    s6 = card_stats("QF06", fw, F, {"rule": 1.0}, ev, 0.0429)
    s8 = card_stats("QF08", fw, F, {"rule": 1.0, "ref": 1.1, "C3": 0.9}, ev, 0.0429)
    v7, v6, v8 = verdict("QF07", "FF2", s7), verdict("QF06", "FF2", s6), verdict("QF08", "FF2", s8)
    ok(set(v7) >= {"FF1", "a", "b", "c", "d", "e", "f", "g", "pass"} and "rebound_miss" in v6 and v8["pass"] is None,
       "판정 모양 — QF07 (가)~(사) · QF06 + REBOUND-MISS · QF08 보고만")
    ok(s7["blocks12"][1] == 2 and s7["crash_wins"][1] == 1 and s7["ff0_replaced"] == 0, "12개월 토막 2 · 구간 1 · FF0 대체 0")
    v0 = v0_report(fw, F, 1.1, ev, 0.0429)
    ok(sorted(v0["rows"]) == ["D0_10bp", "D0_20bp", "T1_10bp", "T1_20bp"] and all(
        set(x) >= {"X_mean", "X_down", "H_down", "blocks12", "crash_wins", "rebound_wins"} for x in v0["rows"].values()),
       "V0 보고 — D0 · T+1 × 10 · 20bp 마다 X · 하락월 · H · 12개월 토막 · 구간(관문 없음)")
    # FF0 — 늦은 결정이 다스리는 달은 대조의 X 로 채운다 · 급락 · 반등 구간의 일간 경로도 같은 대체
    late = {("QF07", "2026-12"), ("QF07", "2027-03"), ("QF07", "2027-06"), ("QF06", "2027-01"), ("QF06", "2027-02")}
    recs2, tc2 = _synthetic(late=late)
    fw2 = Fwd(recs2, {}, tc2)
    F2 = ForwardFrame(fw2)
    s7b = card_stats("QF07", fw2, F2, {"rule": 1.05, "ref": 1.1, "C3": 0.9}, ev, 0.0429)
    B2 = {b: FBook(b, fw2, F2) for b in ("Q07V1.D0", "V0.D0")}
    xr = x_of(F2, B2["Q07V1.D0"].lg0 + B2["Q07V1.D0"].lf[C10], C10)
    xv = x_of(F2, B2["V0.D0"].lg0 + B2["V0.D0"].lf[C10], C10)
    badm = np.array([fw2.bad_decision("QF07", fw2.governing("QF07", h)) is not None for h in F2.hold])
    ok(s7b["ff0_replaced"] == 9 and s7b["late_first36"] == 3 and abs(s7b["X_mean"] - float(np.where(badm, xv, xr).mean())) < 1e-12,
       "FF0 — 늦은 결정 3 → 대체 9달 · 첫 36개월 늦음 3(FF2 막힘)")
    xd7 = x_of(F2, s7b["_lg_rule_ff0"], C10)
    ok(np.max(np.abs(xd7 - np.where(badm, xv, xr))) < 1e-10,
       "FF0 일간 대체(QF07) — 급락 · 반등 구간에 쓰는 일간 경로의 월 X = 대체한 월 X")
    s6b = card_stats("QF06", fw2, F2, {"rule": 1.0}, ev, 0.0429)
    bad6 = np.array([fw2.bad_decision("QF06", fw2.governing("QF06", h)) is not None for h in F2.hold])
    O2, D2 = FBook("V0.T1", fw2, F2), FBook("XBM.T1", fw2, F2)
    st2 = {m: v[0] for m, v in fw2.states().items()}
    pos2 = pos_T1(F2, fw2, st2)
    xsw = x_of(F2, SW.sleeve_daily(pos2, O2, D2, C10)[0], C10)
    xdm = SW.mix_ex_closed(F2, float(pos2.mean()), SW.month_growth(F2, O2, C10), SW.month_growth(F2, D2, C10), False, False, "TR", C10)
    ok(int(bad6.sum()) == 2 and np.max(np.abs(x_of(F2, s6b["_lg_rule_ff0"], C10) - np.where(bad6, xdm, xsw))) < 1e-10,
       "FF0 일간 대체(QF06) — 늦은 달의 날마다 D 혼합 · 월 X = 대체한 월 X")
    ok(fw2.governing("QF07", "2027-01") == "2026-12" and fw2.governing("QF07", "2026-12") == "2026-09"
       and fw2.governing("QF06", "2027-01") == "2026-12", "다스리는 결정 — 분기 편입 · QF06 은 전달")
    # 막힘 대체 · 대체 판 · local 미 witness 는 FF0
    r_deg = dict(recs["decisions.jsonl"][0], snap={"commit": "0" * 40, "degraded": {"sd_drop": ["X"]}})
    r_loc = dict(recs["decisions.jsonl"][1], runner="local")
    fw3 = Fwd(dict(recs, **{"decisions.jsonl": [r_deg, r_loc] + recs["decisions.jsonl"][2:]}), {}, tc)
    ok(fw3.bad_decision(r_deg["card"], r_deg["m"]) == "막힘 대체" and fw3.bad_decision(r_loc["card"], r_loc["m"]) == "미커밋",
       "FF0 — 막힘 대체 판 · witness 없는 local 결정은 온전하지 않다")
    # 관문 창 고정 — FF1 = 정확히 2026-11 ~ 2028-10 · 창 뒤 달은 보지 않는다
    ok(gate_window("2028-11-01")[0] == "2026-11" and gate_window("2028-11-01")[-1] == "2028-10" and len(gate_window("2028-11-01")) == 24
       and len(gate_window("2029-11-01")) == 36 and gate_window("2030-02-01")[-1] == "2030-01", "관문 창 — FF1 24 · FF2 36 · 분기마다 +3")
    recs40, tc40 = _synthetic(n_months=40)
    fw40 = Fwd(recs40, {}, tc40, hold_until=gate_window("2028-11-01")[-1])
    ok(fw40.hold == gate_window("2028-11-01"), "관문 창 — 40달이 실현돼 있어도 FF1 은 앞 24달만 본다")
    # 판정 파일 — 관문 날짜 하나에 하나 · 더 늦은 날짜가 있으면 거절
    jt = tempfile.mkdtemp(prefix="qfwd_jt_")
    try:
        a1 = judge_file_check(jt, "FF2", "2029-11-01")
        os.makedirs(os.path.join(jt, "judge"))
        io.open(os.path.join(jt, "judge", "FF2-2030-02-01.json"), "w", encoding="utf-8").write("{}\n")
        a2 = judge_file_check(jt, "FF2", "2030-02-01")
        a3 = judge_file_check(jt, "FF2", "2029-11-01")
        a4 = judge_file_check(jt, "FF2", "2030-05-01")
        ok(a1[0] and not a2[0] and not a3[0] and a4[0], "판정 파일 — 같은 관문 날짜 두 번 · 더 이른 날짜 뒤늦게 → 거절")
    finally:
        QC.rmtree(jt)
    # 관문 전 거절
    evok = dict(EV_MIN, **Q06_MIN)
    ok(not gate_allowed("FF1", "2027-06-01", 30, evok)[0], "FF1 날짜 전 → 거절")
    ok(not gate_allowed("FF1", "2028-11-01", 23, evok)[0] and gate_allowed("FF1", "2028-11-01", 24, evok)[0],
       "FF1 — 24개월 미만 거절 · 24개월 열림")
    ok(not gate_allowed("FF2", "2029-10-31", 40, evok)[0], "FF2 날짜 전 → 거절")
    ok(not gate_allowed("FF2", "2029-11-01", 36, dict(evok, surge_m=3))[0], "FF2 사건 최소 미달 → 거절")
    ok(not gate_allowed("FF2", "2030-02-01", 40, dict(evok, defense=5), "QF06")[0], "FF2 QF06 수비 달 미달 → 거절")
    ok(not gate_allowed("FF2", "2030-02-01", 40, evok, "QF07", blocked=True)[0], "FF2 늦은 결정 셋 → 거절")
    ok(gate_allowed("FF2", "2030-02-01", 40, evok, "QF06")[0] and gate_date("FF2", "2030-03-15") == "2030-02-01",
       "FF2 분기 관문 날짜")
    msgs = [gate_allowed(g, t, n, e2, cd, bl)[1] for g, t, n, e2, cd, bl in
            (("FF1", "2027-01-01", 0, {}, None, False), ("FF2", "2029-11-01", 1, {}, None, False),
             ("FF2", "2029-11-01", 40, {}, None, False), ("FF2", "2029-11-01", 40, evok, "QF07", True))]
    ok(not any(ch.isdigit() for m in msgs for ch in m), "거절 사유에는 숫자가 없다")
    lines = []
    rc = gate("FF1", "QF07", out=lines.append, today="2027-12-31")
    ok(rc == 2 and not any(ch.isdigit() for ln in lines for ch in ln), "--gate 날짜 전 → 종료 2 · 숫자 없음")
    print("qfwd_judge selftest: %s (%d 실패)" % ("통과" if not fails else "실패", len(fails)))
    return 0 if not fails else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    frozen_root()
    if "--gate" in argv:
        g = argv[argv.index("--gate") + 1]
        card = argv[argv.index("--card") + 1] if "--card" in argv else None
        if g not in GATES or (card and card not in ("QF07", "QF06", "QF08")):
            print("사용: --gate FF1|FF2 [--card QF07|QF06|QF08]")
            return 2
        return gate(g, card)
    return status()


if __name__ == "__main__":
    sys.exit(main())
