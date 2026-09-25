# -*- coding: utf-8 -*-
"""build/qfwd_ledger.py — 전방 원장(QFWD) · 판 고르기 → 결정 → 일간 가격 포착 → 월 실현 · 판정은 하지 않는다.

근본 이유 — 배치 Q 의 카드(QF07 · QF08 · QF06)와 EG30 V0 이 «그 규칙» 으로 앞으로 어떻게 가는지를 남기려면, 누가 언제 다시 돌려도
  같은 판 · 같은 결정 · 같은 체결일이 나와야 한다. 그래서 모든 것을 git 이력과 이미 쓴 기록에서만 끌어낸다.
  · 판 V_m = d_m 미국 마감 뒤 origin/main 첫 부모 이력에서 검증을 통과하는 가장 이른 커밋(작업 사본을 읽지 않는다) — 이 실행이 본
    끝(tip)을 기록해 누구나 같은 끝에서 다시 고른다 · 결정 무리(분기 · QF06)는 따로 · 예정 밖 휴장은 기록(calendar.jsonl) ·
    온전한 판 없이 5거래일이면 막힘 대체 · 자식은 실행 예산(70분) 안에서.
  · 결정은 얼린 코드(1d81f083)를 어댑터 자식 프로세스로만 돌린다 — 이 파일은 표준 라이브러리만 쓰고 numpy 를 부르지 않는다.
  · 기록은 해시 사슬 · 추가만(data/_qfwd/*.jsonl) · 한 번 쓰는 파일(eg/ · fits/). 재계산이 어긋나도 원 기록을 지킨다
    (forward_weekly 와 같은 규약).
  · 장부 엔진은 qg_lab.sleeve 의 뜻(값 공간 · 마지막 가격 들고 가기 · 되맞춤 날 비용 = c × 거래율)을 그대로 옮긴다.
    비용 c 별 경로는 저장하지 않는다 — g_c = g0 × (1 − c·tau) (q_switch.Book 의 통찰: 상대 비중과 tau 는 비용과 무관).
  · 수익 · 비중을 화면에 찍지 않는다 — --status 는 개수와 날짜만(판정기는 관문 날짜에만 숫자를 낸다).

사양: 스크래치 qfwd_spec.md §2 · 계획 rbatch_forward_plan.md(FORWARD PLAN). [DECL] 은 build/PREREG-2026-09-26-QFWD.md 에 옮긴다.

  python build/qfwd_ledger.py --auto [--fetch] [--keep]      # 크론 — 결정 → 포착 → 실현(멱등)
  python build/qfwd_ledger.py --status                       # 개수만
  python build/qfwd_ledger.py --dry                          # 판 고르기와 검증만 — 자식 · 쓰기 없음
  python build/qfwd_ledger.py --rehearse 2026-08 [--out DIR] # 과거 달 결정만(스크래치) — 포착 · 실현 금지
  python build/qfwd_ledger.py --rehearse 2026-06,2026-07,2026-08 --qdir <스크래치> [--keep] [--cron-delay 120] [--no-events]
                             [--withhold-fits K] [--tips-today]
                                                             # 기록판 되풀이 — 그 시각의 origin/main 끝을 되짚고(병합에 흔들리지 않게)
                                                             #   크론 + 지연 · 사건 실행을 흉내 내 판 V 고르기 · 결정 · 사슬 기록 →
                                                             #   qfwd_check(되풀이) · 변조 점검 → 기록 지움(포착 · 실현 금지)
  python build/qfwd_ledger.py --calendar-add closed|early DATE 사유 [--src URL]      # 달력 줄(예정 밖 휴장 · 조기 폐장) — 사람이 커밋
  python build/qfwd_ledger.py --calendar-add utc_offset D0 D1 4|5 사유 [--src URL]   # 서머타임 법이 바뀌면
  python build/qfwd_ledger.py --recheck                      # 실현 달을 최신 판으로 다시 재서 1bp 넘는 차이만 WARN
  python build/qfwd_ledger.py --selftest [--git] [--e2e]     # 달력 · 사슬 · 엔진(= qg_lab.sleeve) · 체결일 · 포착 기준점
                                                             #   [--git 실제 이력 판 고르기 · --e2e 합성 저장소 크론 흉내]
  python build/qfwd_ledger.py --auto --now 2026-11-03T00:00:00Z --qdir <스크래치>   # 시험 전용(data/_qfwd 에는 안 쓴다)
"""
from __future__ import annotations
import collections
import datetime
import glob
import io
import json
import math
import os
import socket
import subprocess
import sys
import tempfile

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import qfwd_check as QC          # noqa: E402  정본 · 봉인 · 사슬 · git

CODE_PIN, BUILD_TREE = QC.CODE_PIN, QC.BUILD_TREE
QDIR = os.path.join(REPO, "data", "_qfwd")
QREL = QC.QREL

# ── 카드 · 장부 · 날짜 (사양 §2.1) ──────────────────────────────────────────
CARDS = {  # card → 결정 주기 · 카드 마감 · 주 체결 행 · 주 대조
    "V0":   {"due": "Q", "deadline": "open_next",          "main": "D0", "control": None, "adopt": False},
    "QF07": {"due": "Q", "deadline": "open_next",          "main": "D0", "control": "V0", "adopt": True},
    "QF08": {"due": "Q", "deadline": "open_next",          "main": "D0", "control": "V0", "adopt": False},
    "QF06": {"due": "M", "deadline": "close_next_minus30", "main": "T1", "control": "D",  "adopt": True}}
ORDER = ("V0", "QF07", "QF08", "QF06")
TARGET_OF = {"V0": "V0", "QF06": "XBM"}                  # 목표가 하나인 카드의 목표 이름
BOOKS = {  # book → (원천 카드, 목표 이름, 주기, 체결 행)
    "V0.D0": ("V0", "V0", "Q", "D0"),       "V0.T1": ("V0", "V0", "Q", "T1"),
    "Q07V1.D0": ("QF07", "V1", "Q", "D0"), "Q07V1.T1": ("QF07", "V1", "Q", "T1"),
    "Q07C3.D0": ("QF07", "C3", "Q", "D0"), "Q07C3.T1": ("QF07", "C3", "Q", "T1"),
    "Q08V1.D0": ("QF08", "V1", "Q", "D0"), "Q08V1.T1": ("QF08", "V1", "Q", "T1"),
    "Q08C3.D0": ("QF08", "C3", "Q", "D0"), "Q08C3.T1": ("QF08", "C3", "Q", "T1"),
    "XBM.D0": ("QF06", "XBM", "M", "D0"),  "XBM.T1": ("QF06", "XBM", "M", "T1")}
FIRST_M, ENTRY_DAY, FWD_M1 = "2026-09", "2026-10-30", "2026-11"
ENTRY_M = {"Q": "2026-09", "M": "2026-10"}          # [DECL] Q 장부는 2026-09 목표로 · M 장부(XBM)는 2026-10 목표로 진입
PRE_RECON_UNTIL = "2026-10-29T23:59:59Z"            # [DECL] 2026-09(기록 전용)는 이때까지 재구성할 수 있다
COSTS = (0.0, 0.0010, 0.0020)
SPDR9 = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
SNAP_PATHS = ("data/stocks.json", "data/pit_px.json", "data/assets.json", "data/bench_px.json",
              "data/index_history.json", "data/sd")
DEC_PATHS = SNAP_PATHS + ("data/_pit_px_cache.json",)
# [DECL] 결정 판의 검증 0 «입력 파일 존재» — 어댑터 ⑥ 이 바꾸는 입력(qfwd_adapter.CUT_FILES + data/sd)이 모두 있어야 한다.
#   없는 판은 자식 오류(세 번 뒤 대체 · 이탈)가 아니라 검증 거절이다. 실측: _pit_px_cache.json 은 2026-09-23(a2a9c154)에야
#   저장소에 들어왔다 — 그 앞 판은 얼린 x-bmrot(pit_backtest.load_prices)이 읽을 입력이 없다(2026-09-25 되풀이에서 찾은 통합 결함).
BLOB_PATHS = ("data/stocks.json", "data/pit_px.json", "data/assets.json", "data/bench_px.json",
              "data/index_history.json", "data/_pit_px_cache.json", "data/rf_monthly.json")
RF_WAIT_TD = 10
REJECT_KEEP = 5
ERR_FALLBACK = 3                # [DECL] 같은 판 · 같은 카드 무리에서 자식 오류가 이만큼이면 다음 유효 판으로(대체 · FF0 늦음 취급)
TO_FALLBACK = 6                 # [DECL] 시간 초과 · 메모리 부족은 같은 판으로 다시 하되 이만큼 쌓이면 대체한다(무한 재시도 방지 · 검토 2026-09-25)
K_DEGRADE = 5                   # [DECL] 유효 판 없이 이만큼(거래일) 지나면 막힘 대체(degraded) 검증으로 고른다 — 영원히 안 낫는 구멍 대비
CAL_CHECK_FROM = "2026-09-01"
FROZEN_EG_LAST = "2026-07"      # 얼린 Eg 표의 마지막 달 — 이 달 이하를 되풀이할 때는 얼린 달을 지우고 구운 것을 넣는다
ENV_PIN_FALLBACK = {"python": (3, 12), "numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
BUDGET_SEC = 4200               # [DECL] 한 실행의 자식 예산(70분) — 워크플로 잡 시간 90분보다 20분 짧다. 남은 예산이 MIN_CHILD_SEC 보다
MIN_CHILD_SEC = 600             #   적으면 새 자식을 띄우지 않고(«예산 소진» 기록 · 다음 실행) · 자식 시간 제한은 남은 예산으로 자른다
GROUPS = {"Q": ("V0", "QF07", "QF08"), "M": ("QF06",)}    # [DECL] 결정 무리 — 따로 판을 고르고 따로 자식을 돌리고 따로 오류를 센다
CRON_DELAY_MIN = 120            # 되풀이 흉내의 크론 지연(분) — 이 저장소의 예약 실행은 실측 1:45~2:30 늦게 뜬다(검토 2026-09-25)
EVENT_DELAY_MIN = 15            # 되풀이 흉내의 사건 실행 지연(분) — refresh-stocks · refresh-assets 완료(workflow_run) 뒤


class CalendarError(Exception):
    pass


class IntegrityError(Exception):
    pass


class ChildError(Exception):
    """자식 실패 — outcome 은 시도 기록의 결과 이름('error' · 'timeout'). 어댑터가 돌려준 outcome 이 'timeout' · 'memory' 면
    'timeout'(같은 판으로 다시 · 오류 세 번 뒤 다음 판으로 넘어가는 셈에 넣지 않는다 — 사양 §2.3)."""

    def __init__(self, msg, outcome="error"):
        super().__init__(msg)
        self.outcome = outcome


def _child_outcome(r):
    o = (r or {}).get("outcome") if isinstance(r, dict) else None
    return "timeout" if o in ("timeout", "memory") else "error"


def group_of(cards):
    """카드 목록 → 결정 무리('Q' 분기 · 'M' QF06). 섞여 있으면 'Q'(옛 모양 · 쓰지 않는다)."""
    cs = set(cards or ())
    return "M" if cs and cs <= set(GROUPS["M"]) else "Q"


def attempt_group(a):
    return a.get("group") or group_of(a.get("cards"))


CRON_UTC = ((2, 40), (5, 40), (8, 40), (10, 40), (15, 40), (16, 40), (23, 40))   # = .github/workflows/qfwd-ledger.yml 의 cron


# ── 시각 ────────────────────────────────────────────────────────────────────
UTC = datetime.timezone.utc
KST = datetime.timezone(datetime.timedelta(hours=9))
_NOW = None                      # --now (시험 전용)


def now_utc():
    if _NOW is not None:
        return _NOW
    return datetime.datetime.now(UTC).replace(microsecond=0)


def iso(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pts(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def kst(t):
    return t.astimezone(KST).strftime("%m-%d %H:%M KST")


# ── NYSE 달력 (규칙으로 만든다 · 2026~2032 · [DECL]) ────────────────────────
CAL_Y0, CAL_Y1 = 2026, 2032
EXTRA_CLOSED = {}                # 'YYYY-MM-DD': 사유 — 예정 밖 휴장(국가 애도일 · 폭풍 등)
EXTRA_EARLY = {}                 # 'YYYY-MM-DD': 사유 — 예정 밖 조기 폐장(13:00 ET)
UTC_OFFSETS = []                 # [(d0, d1, 시간)] — 미국 서머타임 법이 바뀌면 그 기간의 ET = UTC − 시간
# [DECL] 예정 밖 휴장 · 조기 폐장 · 서머타임 변경은 코드가 아니라 기록 data/_qfwd/calendar.jsonl(해시 사슬 · 추가만)에 적는다 —
#   `qfwd_ledger.py --calendar-add closed|early DATE 사유 [--src URL]` · `--calendar-add utc_offset D0 D1 4|5 사유`.
#   코드(핀)에 두면 휴장 하루가 원장 전체를 멈춘다(고치면 핀이 깨진다 · 검토 2026-09-25). 휴장 줄은 qfwd_check --full 이 SPY 와 대조한다
#   (그날 SPY 종가가 있으면 위반). 판 하나의 SPY 날짜가 달력과 어긋나면 그 판만 거절한다(사유 «calendar») — 원장 전체를 멈추지 않는다.
_DAY = datetime.timedelta(days=1)
_HOL, _EARLY = {}, {}


def apply_calendar(rows):
    """calendar.jsonl 의 줄 → 예정 밖 휴장 · 조기 폐장 · UTC 시차(열쇠마다 첫 줄 · 캐시를 비운다)."""
    EXTRA_CLOSED.clear()
    EXTRA_EARLY.clear()
    del UTC_OFFSETS[:]
    seen = set()
    for r in rows or ():
        k = (r.get("kind"), r.get("d"), r.get("d0"), r.get("d1"))
        if k in seen:
            continue
        seen.add(k)
        if r.get("kind") == "closed" and r.get("d"):
            EXTRA_CLOSED[r["d"]] = r.get("why") or "calendar.jsonl"
        elif r.get("kind") == "early" and r.get("d"):
            EXTRA_EARLY[r["d"]] = r.get("why") or "calendar.jsonl"
        elif r.get("kind") == "utc_offset" and r.get("off") in (4, 5):
            UTC_OFFSETS.append((r["d0"], r["d1"], int(r["off"])))
    _HOL.clear()
    _EARLY.clear()


def _dd(s):
    return datetime.date.fromisoformat(s)


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7]) + k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def easter(y):
    """익명 그레고리력 부활절 계산."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mo = (h + l_ - 7 * m + 114) // 31
    da = (h + l_ - 7 * m + 114) % 31 + 1
    return datetime.date(y, mo, da)


def _nth(y, mo, wd, n):
    d = datetime.date(y, mo, 1)
    return d + datetime.timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))


def _last(y, mo, wd):
    d = (datetime.date(y + (mo == 12), mo % 12 + 1, 1)) - _DAY
    return d - datetime.timedelta(days=(d.weekday() - wd) % 7)


def _obs(d):
    """토 → 금 · 일 → 월."""
    if d.weekday() == 5:
        return d - _DAY
    if d.weekday() == 6:
        return d + _DAY
    return d


def holidays(y):
    if y not in _HOL:
        if not CAL_Y0 <= y <= CAL_Y1:
            raise CalendarError("달력 범위 밖 %d (%d~%d)" % (y, CAL_Y0, CAL_Y1))
        h = {}
        ny = datetime.date(y, 1, 1)
        if ny.weekday() == 6:
            h[ny + _DAY] = "New Year (obs)"
        elif ny.weekday() < 5:
            h[ny] = "New Year"                      # 토요일이면 쉬지 않는다(NYSE)
        h[_nth(y, 1, 0, 3)] = "MLK"
        h[_nth(y, 2, 0, 3)] = "Presidents"
        h[easter(y) - 2 * _DAY] = "Good Friday"
        h[_last(y, 5, 0)] = "Memorial"
        h[_obs(datetime.date(y, 6, 19))] = "Juneteenth"
        h[_obs(datetime.date(y, 7, 4))] = "Independence"
        h[_nth(y, 9, 0, 1)] = "Labor"
        h[_nth(y, 11, 3, 4)] = "Thanksgiving"
        h[_obs(datetime.date(y, 12, 25))] = "Christmas"
        out = {d.isoformat(): v for d, v in h.items()}
        out.update({k: v for k, v in EXTRA_CLOSED.items() if k[:4] == str(y)})
        _HOL[y] = out
    return _HOL[y]


def early_closes(y):
    if y not in _EARLY:
        hol = holidays(y)
        e = {(_nth(y, 11, 3, 4) + _DAY).isoformat()}
        for d in (datetime.date(y, 12, 24), datetime.date(y, 7, 3)):
            if d.weekday() < 5 and d.isoformat() not in hol:
                e.add(d.isoformat())
        e |= {k for k in EXTRA_EARLY if k[:4] == str(y)}
        _EARLY[y] = e
    return _EARLY[y]


def is_td(d):
    x = _dd(d)
    return x.weekday() < 5 and d not in holidays(x.year)


def next_td(d):
    x = _dd(d) + _DAY
    while not is_td(x.isoformat()):
        x += _DAY
    return x.isoformat()


def prev_td(d):
    x = _dd(d) - _DAY
    while not is_td(x.isoformat()):
        x -= _DAY
    return x.isoformat()


def tds(a, b):
    out, x, z = [], _dd(a), _dd(b)
    while x <= z:
        s = x.isoformat()
        if is_td(s):
            out.append(s)
        x += _DAY
    return out


def month_tds(m):
    y, mo = int(m[:4]), int(m[5:7])
    last = datetime.date(y + (mo == 12), mo % 12 + 1, 1) - _DAY
    return tds("%s-01" % m, last.isoformat())


def d_m(m):
    return month_tds(m)[-1]


def td_add(d, n):
    for _ in range(n):
        d = next_td(d)
    return d


def is_edt(d):
    x = _dd(d)
    return _nth(x.year, 3, 6, 2) <= x < _nth(x.year, 11, 6, 1)


def et_offset(d):
    """d 의 ET = UTC − 시간 — 달력 줄(utc_offset)이 덮으면 그 값 · 아니면 현행 법(3월 둘째 일 ~ 11월 첫 일 전 4시간)."""
    for d0, d1, off in UTC_OFFSETS:
        if d0 <= d <= d1:
            return off
    return 4 if is_edt(d) else 5


def _et(d, hh, mm):
    x = _dd(d)
    off = et_offset(d)
    return datetime.datetime(x.year, x.month, x.day, hh, mm, tzinfo=UTC) + datetime.timedelta(hours=off)


def open_utc(d):
    return _et(d, 9, 30)


def close_utc(d):
    return _et(d, 13, 0) if d in early_closes(_dd(d).year) else _et(d, 16, 0)


def deadline(card, m):
    dn = next_td(d_m(m))
    if CARDS[card]["deadline"] == "open_next":
        return open_utc(dn)
    return close_utc(dn) - datetime.timedelta(minutes=30)


def first_close_after(d0, t):
    """d0 이상인 첫 거래일 가운데 종가 시각이 t 보다 뒤인 날."""
    d = d0 if is_td(d0) else next_td(d0)
    while close_utc(d) <= t:
        d = next_td(d)
    return d


def is_formation(m):
    return int(m[5:7]) % 3 == 0


def due_cards(m):
    return [c for c in ORDER if CARDS[c]["due"] == "M" or is_formation(m)]


def book_months(card, upto):
    """장부가 쓰는 그 카드의 결정 달 — 진입 달부터 upto 까지."""
    cad = CARDS[card]["due"]
    m, out = ENTRY_M[cad], []
    while m <= upto:
        if cad == "M" or is_formation(m):
            out.append(m)
        m = mshift(m, 1)
    return out


def plan(card, m, row):
    """결정 (card, m) 의 장부 행 row(D0 · T1) 체결 계획 — 예정일 · 마감 · 늦을 때 기준일."""
    cad = CARDS[card]["due"]
    if cad == "Q" and m == ENTRY_M["Q"]:
        sched = ENTRY_DAY if row == "D0" else next_td(ENTRY_DAY)
        return {"sched": sched, "cutoff": pts(PRE_RECON_UNTIL), "dnext": None, "pre": True}
    dm = d_m(m)
    dn = next_td(dm)
    if row == "D0":
        return {"sched": dm, "cutoff": open_utc(dn), "dnext": dn, "pre": False}
    return {"sched": dn, "cutoff": close_utc(dn) - datetime.timedelta(minutes=30), "dnext": dn, "pre": False}


def resolve(pl, t_eff):
    """(day, late_exec, status). t_eff 가 없으면 (None, False, 'pending')."""
    if t_eff is None:
        return None, False, "pending"
    if t_eff <= pl["cutoff"]:
        return pl["sched"], False, "resolved"
    if pl["pre"]:
        return None, False, "entry_failed"
    return first_close_after(pl["dnext"], t_eff), True, "resolved"


# ── git · 판 자료 ───────────────────────────────────────────────────────────
class Git:
    def __init__(self, repo=REPO):
        self.repo = repo
        self._p = {}
        self._fp = {}

    def run(self, *args, check=True):
        return QC.git(self.repo, *args, check=check)

    def ok(self, *args):
        return QC.git_ok(self.repo, *args)

    def first_parent(self, ref):
        if ref not in self._fp:
            out = self.run("log", "--first-parent", "--reverse", "--format=%H %ct", ref, check=False)
            self._fp[ref] = [(h, int(t)) for h, t in (ln.split() for ln in out.splitlines() if ln.strip())]
        return self._fp[ref]

    def _proc(self, which):
        p = self._p.get(which)
        if p is None or p.poll() is not None:
            p = subprocess.Popen(["git", "cat-file", which], cwd=self.repo, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._p[which] = p
        return p

    def check(self, name):
        p = self._proc("--batch-check")
        p.stdin.write((name + "\n").encode("utf-8"))
        p.stdin.flush()
        ln = p.stdout.readline().decode("utf-8").strip()
        parts = ln.split()
        if len(parts) != 3 or parts[1] == "missing":
            return None
        return parts[0], parts[1], int(parts[2])

    def read(self, oid):
        p = self._proc("--batch")
        p.stdin.write((oid + "\n").encode("utf-8"))
        p.stdin.flush()
        hdr = p.stdout.readline().decode("utf-8").split()
        if len(hdr) != 3:
            raise IntegrityError("git 객체 없음 %s" % oid)
        n = int(hdr[2])
        data = p.stdout.read(n)
        p.stdout.read(1)
        return data

    def ls_tree(self, oid):
        out = {}
        for ln in self.run("ls-tree", oid).splitlines():
            meta, name = ln.split("\t", 1)
            out[name] = meta.split()[2]
        return out

    def close(self):
        for p in self._p.values():
            try:
                p.stdin.close()
                p.wait(timeout=5)
            except Exception:
                pass
        self._p = {}


class Store:
    """blob id 로 캐시한 판 자료 — 대부분의 커밋은 이 파일들을 안 건드린다."""

    def __init__(self, git):
        self.g = git
        self._ids = {}
        self._doc = collections.OrderedDict()
        self._tree = {}
        self._sdlen = {}
        self._sdpx = collections.OrderedDict()

    def ids(self, commit):
        if commit not in self._ids:
            out = {}
            for p in BLOB_PATHS + ("data/sd", "data"):
                r = self.g.check("%s:%s" % (commit, p))
                out[p] = r[0] if r else None
            self._ids[commit] = out
        return self._ids[commit]

    def doc(self, oid):
        if oid in self._doc:
            self._doc.move_to_end(oid)
            return self._doc[oid]
        d = json.loads(self.g.read(oid).decode("utf-8"))
        self._doc[oid] = d
        while len(self._doc) > 10:
            self._doc.popitem(last=False)
        return d

    def tree(self, oid):
        if oid not in self._tree:
            self._tree[oid] = self.g.ls_tree(oid)
        return self._tree[oid]

    def _sd_parse(self, oid):
        import array
        d = json.loads(self.g.read(oid).decode("utf-8"))
        px = d.get("pxd") or []
        a = array.array("d", (math.nan if v is None else float(v) for v in px))
        self._sdlen[oid] = len(px)
        self._sdpx[oid] = a
        while len(self._sdpx) > 1200:
            self._sdpx.popitem(last=False)
        return a

    def sd_len(self, oid):
        if oid is None:
            return None
        if oid not in self._sdlen:
            self._sd_parse(oid)
        return self._sdlen[oid]

    def sd_px(self, oid):
        if oid in self._sdpx:
            self._sdpx.move_to_end(oid)
            return self._sdpx[oid]
        return self._sd_parse(oid)


class Snap:
    """한 커밋의 자료 판(읽기 전용)."""

    def __init__(self, store, commit, ct):
        self.st, self.commit, self.ct = store, commit, ct
        self.ids = store.ids(commit)
        self._c = {}

    def key(self, paths=SNAP_PATHS):
        return tuple(self.ids.get(p) for p in paths)

    def _memo(self, k, fn):
        if k not in self._c:
            self._c[k] = fn()
        return self._c[k]

    def missing(self, paths=SNAP_PATHS):
        return [p for p in paths if not self.ids.get(p)]

    def stocks(self):
        return self.st.doc(self.ids["data/stocks.json"])

    def dates(self):
        return self._memo("S", lambda: list(self.stocks()["pxd_dates"]))

    def didx(self):
        return self._memo("Si", lambda: {d: i for i, d in enumerate(self.dates())})

    def tickers(self):
        return self._memo("T", lambda: [s["t"] for s in self.stocks()["stocks"]])

    def tset(self):
        return self._memo("Ts", lambda: set(self.tickers()))

    def assets(self):
        return self.st.doc(self.ids["data/assets.json"])

    def aidx(self):
        return self._memo("Ai", lambda: {d: i for i, d in enumerate(self.assets()["dates"])})

    def spy_days(self):
        def f():
            A = self.assets()
            return [d for d, p in zip(A["dates"], A["px"]["SPY"]) if p is not None]
        return self._memo("spy", f)

    def bench(self):
        return self.st.doc(self.ids["data/bench_px.json"])

    def bidx(self):
        return self._memo("Bi", lambda: {d: i for i, d in enumerate(self.bench()["dates"])})

    def pit(self):
        return self.st.doc(self.ids["data/pit_px.json"])

    def pidx(self):
        return self._memo("Pi", lambda: {d: i for i, d in enumerate(self.pit().get("dates") or [])})

    def quarantine(self):
        return self._memo("Q", lambda: set((self.pit().get("quarantine") or {}).keys()))

    def ih_months(self):
        return self._memo("ih", lambda: set((self.st.doc(self.ids["data/index_history.json"]).get("months") or {}).keys()))

    def rf(self):
        oid = self.ids.get("data/rf_monthly.json")
        return (self.st.doc(oid).get("monthly") or {}) if oid else {}

    def sd(self):
        return self.st.tree(self.ids["data/sd"])

    def src(self, k):
        """가격 계열의 원천 — 'sd' · 'pit' · None (사양 §2.7)."""
        cache = self._c.setdefault("src", {})
        if k in cache:
            return cache[k]
        s = None
        if k in self.tset():
            oid = self.sd().get(k + ".json")
            if oid and self.st.sd_len(oid) == len(self.dates()):
                s = "sd"
        if s is None:
            px = self.pit().get("px") or {}
            if k in px and k not in self.quarantine():
                s = "pit"
        cache[k] = s
        return s

    def price(self, k, d):
        """이 판 안의 k 의 d 종가(> 0) · 없으면 None. sd 는 stocks 격자 · pit_px 는 제 날짜 격자로 찾는다
        (온전한 판에서는 둘이 같다 — 막힘 대체 포착에서 두 격자가 어긋나도 날짜가 밀리지 않게)."""
        s = self.src(k)
        if s == "sd":
            j = self.didx().get(d)
            if j is None:
                return None
            v = self.st.sd_px(self.sd()[k + ".json"])[j]
        elif s == "pit":
            j = self.pidx().get(d)
            if j is None:
                return None
            o = self.pit()["px"][k]
            i0, arr = int(o.get("i0") or 0), o.get("p") or []
            v = arr[j - i0] if 0 <= j - i0 < len(arr) else None
            v = math.nan if v is None else float(v)
        else:
            return None
        return v if (v == v and v > 0) else None

    def mkt(self, which, d):
        if which == "spy":
            j = self.aidx().get(d)
            v = self.assets()["px"]["SPY"][j] if j is not None else None
        else:
            j = self.bidx().get(d)
            v = self.bench()["series"]["spx"]["px"][j] if j is not None else None
        return float(v) if (v is not None and v > 0) else None


# ── 장부 엔진 (qg_lab.sleeve 의 뜻 · 값 공간) ─────────────────────────────────
def run_book(days, w0, cash0, caps, rebs, rf_h, n_h, pseudo_first=False):
    """한 장부의 한 달.

    days       그달 거래일(D0 첫 달은 ENTRY_DAY 를 앞에 붙인다 — pseudo_first)
    w0, cash0  월초 몫(합 = 1)
    caps       {날: 포착 줄} — r(null 이면 마지막 가격을 들고 간다) · ok_buy
    rebs       {날: {"w": 목표 몫, ...}} — 그날 종가 수익 뒤에 되맞춘다
    → g0(비용 전 일간 성장) · reb(i, tau, dropped, cash_after) · w_end · cash_end · missing
    """
    v = {k: float(x) for k, x in w0.items()}
    cash = float(cash0)
    V = sum(v.values()) + cash
    rf_d = (1.0 + rf_h) ** (1.0 / n_h) - 1.0
    g0, reb, missing = [], [], {}
    for i, d in enumerate(days):
        if pseudo_first and i == 0:
            g0.append(1.0)                     # 진입일 — 수익 없음(펀드 1개월은 이 종가에서 시작)
        else:
            cap = caps[d]
            r = cap["r"]
            Vold = V
            for k in v:
                if k not in r:
                    raise IntegrityError("포착 %s 에 보유 %s 가 없다(키 집합 결함)" % (d, k))
                x = r[k]
                if x is None:
                    missing[k] = missing.get(k, 0) + 1
                else:
                    v[k] *= 1.0 + x
            cash *= 1.0 + rf_d
            V = sum(v.values()) + cash
            g0.append(V / Vold)
        e = rebs.get(d)
        if e is not None:
            okb = caps[d]["ok_buy"] if d in caps else {}
            wt = e["w"]
            w = {k: float(x) for k, x in wt.items() if okb.get(k)}
            dropped = sorted(k for k in wt if not okb.get(k))
            keys = set(w) | set(v)
            tau = sum(abs(w.get(k, 0.0) - v.get(k, 0.0) / V) for k in keys)
            v = {k: x * V for k, x in w.items()}
            cash = V * (1.0 - sum(w.values()))
            reb.append({"i": i, "d": d, "tau": tau, "dropped": dropped, "cash_after": cash / V})
    return {"g0": g0, "reb": reb, "w_end": {k: x / V for k, x in sorted(v.items())}, "cash_end": cash / V,
            "missing": missing}


def g_cost(g0, reb, c):
    """비용 c 경로 — 되맞춤 날만 g0 × (1 − c·tau)."""
    g = list(g0)
    for e in reb:
        g[e["i"]] *= 1.0 - c * e["tau"]
    return g


def capture_row(d, snap, keys, okb_keys, base):
    """포착 한 줄(판 V_d 안에서만 잰 수익) · 새 기준점.

    r_k = p(d)/p(base_k) − 1 (둘 다 > 0 일 때) · 아니면 null — null 이면 장부는 마지막 가격을 들고 가고 다음 유효 포착이
    base 부터의 움직임을 통째로 실현한다. ok_buy_k = p(d) 가 있고 (기준점이 없거나 r_k 가 섰을 때) [DECL: 기준 가격이 판에서
    사라진 날은 그 이름을 사지 않는다 — 두 장부가 한 기준점을 나눠 쓰므로].
    """
    p = prev_td(d)
    r, bout, src_pit, none, okb = {}, {}, [], [], {}
    for k in sorted(keys):
        s = snap.src(k)
        if s is None:
            none.append(k)
            r[k] = None
            if k in okb_keys:
                okb[k] = False
            continue
        if s == "pit":
            src_pit.append(k)
        pd = snap.price(k, d)
        b = base.get(k)
        if b is not None:
            pb = snap.price(k, b)
            r[k] = (pd / pb - 1.0) if (pd is not None and pb is not None) else None
            if b != p:
                bout[k] = b
        else:
            r[k] = None
        if k in okb_keys:
            okb[k] = pd is not None and (b is None or r[k] is not None)
    nb = dict(base)
    for k in keys:
        if r.get(k) is not None or okb.get(k):
            nb[k] = d
    row = {"kind": "day", "d": d, "prev": p, "snap": {"commit": snap.commit, "commit_time": QC.ts_iso(snap.ct)},
           "r": r, "base": bout, "src_pit": src_pit, "none": none, "ok_buy": okb, "n": len(r)}
    return row, nb


def bases_from(caps):
    base = {}
    for c in caps:
        for k, x in c["r"].items():
            if x is not None:
                base[k] = c["d"]
        for k, x in (c.get("ok_buy") or {}).items():
            if x:
                base[k] = c["d"]
    return base


# ── 기록 ────────────────────────────────────────────────────────────────────
class Records:
    def __init__(self, qdir, pins, write):
        self.qdir, self.pins, self.write = qdir, pins or {}, write
        self.recs, self.last = {}, {}
        for name in QC.JSONL:
            res = QC.chain_file(qdir, name, self.pins)
            if res["errs"]:
                raise IntegrityError("; ".join(res["errs"][:3]))
            self.recs[name], self.last[name] = res["recs"], res["last"]
        dv = QC.dup_check({n: {"recs": self.recs[n]} for n in QC.JSONL})
        if dv:
            raise IntegrityError(dv[0])
        apply_calendar(self.recs["calendar.jsonl"])
        self.added = collections.Counter()
        self.ver = collections.Counter()
        self.runner = "gha" if os.environ.get("GITHUB_ACTIONS") == "true" else "local"
        self.run_id = os.environ.get("GITHUB_RUN_ID") or "%s-%d" % (socket.gethostname(), os.getpid())

    def append(self, name, rec):
        if not self.write:
            raise IntegrityError("쓰기 금지 모드에서 %s 에 쓰려 했다" % name)
        full = {"v": 1, "t_rec": iso(now_utc()), "runner": self.runner, "run_id": self.run_id}
        full.update(rec)
        s = QC.seal(full, len(self.recs[name]), self.last[name])
        line = QC.canon(s) + "\n"
        os.makedirs(self.qdir, exist_ok=True)
        with io.open(os.path.join(self.qdir, name), "a", encoding="utf-8", newline="") as fh:
            fh.write(line)
        self.recs[name].append(s)
        self.last[name] = s["sha"]
        self.added[name] += 1
        self.ver[name] += 1
        if name == "calendar.jsonl":
            apply_calendar(self.recs[name])
        return s


def write_once(path, obj):
    """한 번 쓰는 파일 — 있으면 같은 내용인지만 본다(다르면 무결성 위반)."""
    if os.path.exists(path):
        old = json.load(io.open(path, encoding="utf-8"))
        if QC.file_sha(old) != QC.file_sha(obj):
            raise IntegrityError("한 번 쓰는 파일 %s 가 이미 다른 내용으로 있다" % path)
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(QC.fcanon(obj) + "\n")
    return True


# ── 원장 ────────────────────────────────────────────────────────────────────
class Ledger:
    def __init__(self, repo=REPO, qdir=None, write=False, adapter=None, keep=False, out=print):
        self.repo = repo
        self.qdir = qdir or os.path.join(repo, "data", "_qfwd")
        self.write, self.keep, self.say = write, keep, out
        self.git = Git(repo)
        self.st = Store(self.git)
        self.ref = QC.main_ref(repo)
        # [DECL] 이 실행이 본 origin/main 끝(SHA) — 판 고르기는 이 끝의 첫 부모 이력에서만 한다. 결정 줄에 snap.tip 으로 남겨
        #   뒤에 사람이 병합(foxtrot)으로 첫 부모 이력을 바꿔도 누구나 같은 끝에서 같은 판을 다시 고른다(검토 2026-09-25).
        self.tip = QC.git(repo, "rev-parse", self.ref, check=False).strip() or self.ref
        self.pins = QC.load_pins(repo, self.qdir)
        self.R = Records(self.qdir, self.pins, write)
        self._adapter = adapter
        self._snaps, self._valid = {}, {}
        self._tc = None
        self._partial = QC.is_partial(repo)
        self._fetched = set()
        self.notes = []
        self.alarms = []
        self.last_out = None
        self.last_outs = {}
        self.n_child = 0
        self.now = now_utc()
        self._t0 = datetime.datetime.now(UTC)

    def close(self):
        self.git.close()

    # ── 예산 ──
    def budget_left(self):
        return BUDGET_SEC - (datetime.datetime.now(UTC) - self._t0).total_seconds()

    def child_timeout(self, name):
        """자식 시간 제한 = min(어댑터 기본값, 남은 예산 − 60초)."""
        A = self.adapter()
        base = (getattr(A, "TIMEOUT", None) or {}).get(name) or 1800
        return max(60, int(min(base, self.budget_left() - 60)))

    # ── 편의(열쇠마다 첫 줄 — 뒤 줄로 앞 기록을 덮지 못한다) ──
    @property
    def dec(self):
        v = self.R.ver["decisions.jsonl"]
        if getattr(self, "_dec_v", None) != v:
            d = {}
            for r in self.R.recs["decisions.jsonl"]:
                if r.get("kind") == "decision":
                    d.setdefault((r["card"], r["m"]), r)
            self._dec = d
            self._dec_v = v
        return self._dec

    def attempts(self):
        return [r for r in self.R.recs["decisions.jsonl"] if r.get("kind") == "attempt"]

    def caps(self):
        out = {}
        for r in self.R.recs["px_capture.jsonl"]:
            out.setdefault(r["d"], r)
        return out

    def mkt_days(self):
        out = {}
        for r in self.R.recs["market.jsonl"]:
            if r.get("kind") == "day":
                out.setdefault(r["d"], r)
        return out

    def mkt_months(self):
        out = {}
        for r in self.R.recs["market.jsonl"]:
            if r.get("kind") == "month":
                out.setdefault(r["h"], r)
        return out

    def month_rows(self):
        out = {}
        for r in self.R.recs["books.jsonl"]:
            if r.get("kind") == "month":
                out.setdefault((r["book"], r["h"]), r)
        return out

    def adapter(self):
        if self._adapter is None:
            import qfwd_adapter as A
            self._adapter = A
        return self._adapter

    def snap(self, c, ct):
        if c not in self._snaps:
            if self._partial and c not in self._fetched:
                self._fetched.add(c)
                QC.prefetch(self.repo, [c], list(DEC_PATHS) + ["data/rf_monthly.json"])   # 부분 복제 — 이 판의 입력 blob 을 한 번에
            self._snaps[c] = Snap(self.st, c, ct)
        return self._snaps[c]

    def blob_work(self, rel):
        return QC.work_blob(self.repo, rel)

    def rel(self, path):
        return os.path.relpath(path, self.repo).replace(os.sep, "/")

    # ── 커밋 시각 · t_eff ──
    def commit_times(self):
        """decisions.jsonl seq → origin/main 에서 닿는 병합 아닌 커밋 가운데 그 줄(같은 seq · sha)을 처음 담은 커밋의 시각."""
        if self._tc is None:
            rel = self.rel(os.path.join(self.qdir, "decisions.jsonl"))
            try:
                self._tc = {s: ct for s, (_c, ct) in QC.commit_map(self.repo, rel, self.ref,
                                                                   self.R.recs["decisions.jsonl"]).items()}
            except Exception:
                self._tc = {}
        return self._tc

    def t_eff(self, rec):
        """t_eff = max(t_decided, 커밋 시각[, runner local 이면 gha witness 시각]) — 모르면 None(체결일 미확정)."""
        if rec is None:
            return None
        t = QC.t_eff_ts(rec, self.commit_times().get(rec["seq"]), QC.witness_times(self.R.recs["decisions.jsonl"]))
        return None if t is None else datetime.datetime.fromtimestamp(t, UTC)

    # ── 달력 대조 ──
    def cal_check(self, snap, lo):
        """판의 SPY 날짜 ↔ 규칙 달력 — 어긋나면 사유 문자열(그 판만 거절한다) · 맞으면 None."""
        spy = snap.spy_days()
        if not spy:
            return None
        hi = spy[-1]
        if hi < lo:
            return None
        cal = set(tds(lo, hi))
        got = {d for d in spy if lo <= d <= hi}
        extra, miss = sorted(got - cal), sorted(cal - got)
        if extra or miss:
            return ("calendar: 판 %s 의 SPY 날짜 ≠ NYSE 달력 — 달력에 없는 거래일 %s · SPY 에 없는 달력 거래일 %s"
                    % (snap.commit[:12], extra[:3], miss[:3]))
        return None

    def calendar_alarm(self):
        """끝(tip) 판의 SPY 날짜가 달력과 어긋나면 경보 — 예정 밖 휴장이면 사람이 --calendar-add 로 달력 줄을 더한다."""
        fp = self.git.first_parent(self.tip)
        if not fp:
            return None
        s = self.snap(*fp[-1])
        if s.missing(("data/assets.json",)):
            return None
        try:
            return self.cal_check(s, CAL_CHECK_FROM)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            return None

    # ── 검증 ──
    def _grid(self, snap):
        k = ("grid", snap.ids["data/stocks.json"], snap.ids["data/pit_px.json"], snap.ids["data/sd"])
        if k not in self._valid:
            S = snap.dates()
            why = None
            pd = snap.pit().get("dates") or []
            if pd != S:
                diff = sorted(set(pd) ^ set(S))
                why = "grid: pit_px 격자(%d · 끝 %s) ≠ pxd_dates(%d · 끝 %s) · 어긋난 날 %s" % (
                    len(pd), pd[-1] if pd else "-", len(S), S[-1] if S else "-", diff[:2])
            else:
                sdm = snap.sd()
                bad = [t for t in snap.tickers() if self.st.sd_len(sdm.get(t + ".json")) != len(S)]
                if bad:
                    why = "grid: sd %d개 길이 ≠ %d (첫 %s)" % (len(bad), len(S), bad[0])
            self._valid[k] = why
        return self._valid[k]

    def sd_off_grid(self, snap):
        """stocks 명단 가운데 sd 길이가 격자와 다른 종목(막힘 대체 결정에서 빠질 이름 — 어댑터 ⑥ 이 뺀다)."""
        S = snap.dates()
        sdm = snap.sd()
        return sorted(t for t in snap.tickers() if self.st.sd_len(sdm.get(t + ".json")) != len(S))

    def degraded_ok(self, d):
        """[DECL] 막힘 대체를 열 수 있는가 — 기준 날 d 종가 뒤 K_DEGRADE 거래일 종가가 지났을 때."""
        return self.now >= close_utc(td_add(d, K_DEGRADE))

    def valid_decision(self, snap, m, degraded=False):
        key = ("dec", m, bool(degraded), snap.key(DEC_PATHS))
        if key in self._valid:
            return self._valid[key]
        res = self._valid_decision(snap, m, degraded)
        self._valid[key] = res
        return res

    def _valid_decision(self, snap, m, degraded=False):
        """결정 판 검증. degraded=True(막힘 대체) — 검증 1(마지막 261 SPY 일 ⊆ 격자)의 구멍과 sd 길이 어긋남을 허용하고 기록한다
        (d_m 은 격자에 있어야 한다 · pit_px 격자 = pxd_dates 는 얼린 pit_panel 이 요구하므로 그대로 · 달력 · 종가 · 명단도 그대로)."""
        miss = snap.missing(DEC_PATHS)
        if miss:
            return {"ok": False, "why": "파일 없음 %s" % miss[0], "checks": {}}
        dm = d_m(m)
        lo = min(CAL_CHECK_FROM, "%s-01" % m)
        cw = self.cal_check(snap, lo)
        if cw:
            return {"ok": False, "why": cw, "checks": {}}
        spy = snap.spy_days()
        pos = {d: i for i, d in enumerate(spy)}
        if dm not in pos:
            return {"ok": False, "why": "win261: SPY 에 d_m %s 종가 없음" % dm, "checks": {}}
        j = pos[dm]
        if j < 260:
            return {"ok": False, "why": "win261: SPY 이력 %d일 < 261" % (j + 1), "checks": {}}
        S = set(snap.didx())
        lack = [d for d in spy[j - 260:j + 1] if d not in S]
        deg = {}
        if lack:
            if not degraded or dm not in S:
                return {"ok": False, "why": "win261: 격자에 SPY 거래일 %d개 없음(첫 %s)" % (len(lack), lack[0]), "checks": {}}
            deg["grid_lack"] = lack[:20]
            deg["n_grid_lack"] = len(lack)
        A, ai = snap.assets(), snap.aidx()[dm]
        for X in ("SPY",) + SPDR9:
            s = A["px"].get(X)
            if s is None or s[ai] is None:
                return {"ok": False, "why": "close_dm: %s 의 d_m 종가 없음" % X, "checks": {}}
        if snap.mkt("spx", dm) is None:
            return {"ok": False, "why": "close_dm: ^GSPC d_m 종가 없음", "checks": {}}
        ms = snap.ih_months()
        ih = "m" if m in ms else ("m-1" if mshift(m, -1) in ms else None)
        if ih is None:
            return {"ok": False, "why": "ih: index_history 에 %s · %s 없음" % (m, mshift(m, -1)), "checks": {}}
        last_m = max(d for d in spy if d[:7] == m)
        if last_m != dm:
            return {"ok": False, "why": "calendar: SPY 의 %s 마지막 거래일 %s ≠ 달력 %s" % (m, last_m, dm), "checks": {}}
        g = self._grid(snap)
        if g:
            if not degraded or not g.startswith("grid: sd "):
                return {"ok": False, "why": g, "checks": {}}
            off = self.sd_off_grid(snap)
            deg["sd_drop"] = off[:50]
            deg["n_sd_drop"] = len(off)
        chk = {"win261": not deg.get("grid_lack"), "grid": not deg.get("sd_drop"), "close_dm": True, "ih": ih, "calendar": True}
        return {"ok": True, "why": None, "checks": chk, "degraded": deg or None}

    def valid_capture(self, snap, d, degraded=False):
        key = ("cap", d, bool(degraded), snap.key())
        if key in self._valid:
            return self._valid[key]
        res = self._valid_capture(snap, d, degraded)
        self._valid[key] = res
        return res

    def _valid_capture(self, snap, d, degraded=False):
        """포착 판 검증. degraded=True(막힘 대체) — (a) 격자에 d · 앞 날이 있을 것과 (b) 격자 일치를 풀고, SPY · ^GSPC 의 d · 앞 날
        종가(c)만 요구한다. 가격이 없는 이름은 null(장부는 마지막 가격으로 든다 · 다음 유효 포착이 기준점부터 통째로 실현)."""
        miss = snap.missing()
        if miss:
            return {"ok": False, "why": "파일 없음 %s" % miss[0], "checks": {}}
        cw = self.cal_check(snap, min(CAL_CHECK_FROM, d))
        if cw:
            return {"ok": False, "why": cw, "checks": {}}
        p = prev_td(d)
        for x in (d, p):
            if snap.mkt("spy", x) is None or snap.mkt("spx", x) is None:
                return {"ok": False, "why": "c: SPY · ^GSPC %s 종가 없음" % x, "checks": {}}
        di = snap.didx()
        deg = {}
        if d not in di or p not in di:
            if not degraded:
                return {"ok": False, "why": "a: 격자에 %s 또는 %s 없음" % (d, p), "checks": {}}
            deg["grid_lack"] = [x for x in (p, d) if x not in di]
        g = self._grid(snap)
        if g:
            if not degraded:
                return {"ok": False, "why": g, "checks": {}}
            deg["grid"] = g[:160]
        return {"ok": True, "why": None, "checks": {"grid": not deg}, "degraded": deg or None}

    # ── 판 고르기 ──
    def _select(self, kind, arg, after, until, skip=(), ref=None, degraded=False):
        """가장 이른 유효 판(끝 ref 의 첫 부모 이력 · 커밋 시각 창 (after, until]). rejects = 처음 걸러진 REJECT_KEEP 개(커밋 · 사유) ·
        reject_kinds = 걸러진 모든 후보의 사유 갈래별 개수(갈래 = 사유의 ':' 앞 — win261 · grid · close_dm · ih · calendar · a · c ·
        파일 없음 <경로> · 판 읽기 실패). skipped = 건너뛴(오류 대체) 판 전부.
        [DECL] «판 읽기 실패» 는 판 자료 자체의 결정적 결함(JSON · 열쇠 · 모양)만이다 — git · 메모리 같은 일시 실패는 다시 올려 이 실행을
          멈춘다(한 번의 일시 실패로 더 늦은 판이 기록되고 재선택이 영구히 어긋나는 것을 막는다 · 검토 2026-09-25)."""
        n, rej, skipped = 0, [], []
        kinds = collections.Counter()
        for c, ct in self.git.first_parent(ref or self.tip):
            if ct <= after or ct > until:
                continue
            n += 1
            snap = self.snap(c, ct)
            try:
                v = (self.valid_decision(snap, arg, degraded) if kind == "dec" else self.valid_capture(snap, arg, degraded))
            except (ValueError, KeyError, TypeError, IndexError, AttributeError) as e:
                v = {"ok": False, "why": "판 읽기 실패: %s %s" % (type(e).__name__, str(e)[:120]), "checks": {}}
            if v["ok"]:
                if c in skip:
                    skipped.append(c)
                    continue
                return {"commit": c, "ct": ct, "snap": snap, "checks": v["checks"], "n_cands": n,
                        "rejects": rej, "reject_kinds": dict(sorted(kinds.items())),
                        "fallback_from": skipped[0] if skipped else None, "skipped": skipped,
                        "degraded": v.get("degraded"), "tip": ref or self.tip}
            kinds[str(v["why"]).split(":")[0].strip()] += 1
            if len(rej) < REJECT_KEEP:
                rej.append({"commit": c[:12], "why": v["why"]})
        return {"commit": None, "n_cands": n, "rejects": rej, "reject_kinds": dict(sorted(kinds.items())),
                "fallback_from": skipped[0] if skipped else None, "skipped": skipped, "degraded": None, "tip": ref or self.tip}

    def select_decision(self, m, skip=(), until_ts=None, ref=None):
        """규칙 V — 온전한 판이 없고 막힘 대체가 열렸으면(d_m 뒤 K_DEGRADE 거래일) 막힘 대체 검증으로 다시 고른다."""
        after = int(close_utc(d_m(m)).timestamp())
        until = until_ts if until_ts is not None else int(self.now.timestamp())
        sel = self._select("dec", m, after, until, skip, ref)
        if not sel["commit"] and self.degraded_ok(d_m(m)):
            sel2 = self._select("dec", m, after, until, skip, ref, degraded=True)
            if sel2["commit"]:
                sel2["rejects_normal"] = sel["reject_kinds"]
                return sel2
        return sel

    def select_capture(self, d, until_ts=None, ref=None):
        after = int(close_utc(d).timestamp())
        until = until_ts if until_ts is not None else int(self.now.timestamp())
        sel = self._select("cap", d, after, until, (), ref)
        if not sel["commit"] and self.degraded_ok(d):
            sel2 = self._select("cap", d, after, until, (), ref, degraded=True)
            if sel2["commit"]:
                return sel2
        return sel

    # ── 결정 ──
    def _attempt(self, cards, m, outcome, snap, detail, group=None):
        """시도 기록. 오류 · 시간 초과는 매번(대체 셈에 쓴다) · 판 없음 · 마감 지남 · 예산 소진은 상태가 바뀔 때만."""
        g = group or group_of(cards)
        same = [a for a in self.attempts() if a["m"] == m and attempt_group(a) == g and a["outcome"] == outcome
                and a.get("snap") == snap and (outcome != "deadline_passed" or a.get("cards") == list(cards))]
        if same and outcome not in ("error", "timeout"):
            return None
        rec = {"kind": "attempt", "cards": list(cards), "group": g, "m": m, "t": iso(now_utc()), "outcome": outcome,
               "snap": snap, "detail": (detail or "")[:300]}
        return self.R.append("decisions.jsonl", rec)

    def eg_path(self, m, commit):
        return os.path.join(self.qdir, "eg", "%s-%s.json" % (m, commit[:8]))

    def fits_path(self, m, commit):
        return os.path.join(self.qdir, "fits", "Q07-%s-%s.json" % (m, commit[:8]))

    def fwd_eg_map(self, m, cur=None):
        out, dec = {}, self.dec
        mm = FIRST_M
        while mm <= m:
            if is_formation(mm):
                if cur and cur[0] == mm:
                    out[mm] = cur[1]
                else:
                    r = dec.get(("V0", mm))
                    f = r and ((r.get("inputs") or {}).get("eg") or {}).get(mm, {}).get("file")
                    p = os.path.join(self.repo, f) if f else None
                    if p and f.startswith(QREL + "/"):
                        p = os.path.join(self.qdir, f[len(QREL) + 1:])
                    if p and os.path.exists(p):
                        out[mm] = p
                    else:
                        cands = sorted(glob.glob(os.path.join(self.qdir, "eg", "%s-*.json" % mm)))
                        if cands:
                            out[mm] = cands[0]
            mm = mshift(mm, 1)
        if cur:
            out[cur[0]] = cur[1]          # 되풀이(FIRST_M 앞 달)에서도 그달 구운 Eg 는 반드시 넘긴다
        return out

    def qrel_of(self, path):
        """기록에 남길 경로 — data/_qfwd/… (시험 qdir 이면 그 안의 상대 경로에 같은 접두사)."""
        return QREL + "/" + os.path.relpath(path, self.qdir).replace(os.sep, "/")

    def env_check(self):
        A = self.adapter()
        pin = getattr(A, "ENV_PIN", None)
        if pin is None:
            pin = ENV_PIN_FALLBACK
        code = ("import json,sys\nout={'python':list(sys.version_info[:2])}\n"
                "for m in ('numpy','scipy','pandas'):\n"
                "    try:\n        out[m]=__import__(m).__version__\n    except Exception as e:\n        out[m]=None\n"
                "print(json.dumps(out))\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")
        try:
            got = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return False, "환경 조사 실패"
        bad = []
        if "python" in pin and tuple(got.get("python") or ()) != tuple(pin["python"]):
            bad.append("python %s ≠ %s" % (got.get("python"), pin.get("python")))
        for m in ("numpy", "scipy", "pandas"):
            if m in pin and got.get(m) != pin[m]:
                bad.append("%s %s ≠ %s" % (m, got.get(m), pin[m]))
        return (not bad), " · ".join(bad)

    def run_child(self, cards, m, snap, tmp, mode=None, eg_dir=None, fits_extra=None, withhold=0):
        """뿌리 → ⑥⑦ → (분기 무리 · 편입이면) ⑤ 굽기 → 결정 자식. mode 가 없으면 달로 정한다 — 얼린 Eg 표 안의 달(≤ FROZEN_EG_LAST ·
        되풀이 전용)은 'parityB'(얼린 그달 Eg 를 지우고 구운 것을 넣는다), 전방 달은 'forward'.
        [DECL] QF06 무리 자식에는 Eg 를 넘기지 않는다(쓰지 않는다 · 분기 무리의 Eg 굽기 실패가 QF06 을 막지 않게).
        자식 시간 제한은 남은 실행 예산으로 자른다. withhold(되풀이 전용) — ③ 새 적합 · 기록 · 다시 읽기 경로를 실제 자료로 태운다."""
        A = self.adapter()
        if mode is None:
            mode = "parityB" if m <= FROZEN_EG_LAST else "forward"
        t_start = datetime.datetime.now(UTC)
        dm = d_m(m)
        dn = next_td(dm)
        br = A.build_root(snap.commit, CODE_PIN, tmp, timeout=self.child_timeout("archive"))
        root, rrep = (br[0], br[1]) if isinstance(br, (tuple, list)) else (br, {})
        cut = A.cut_and_blank(root, m, dm, dn)
        cur = None
        sec = {"root": (datetime.datetime.now(UTC) - t_start).total_seconds()}
        quarterly = any(CARDS[c]["due"] == "Q" for c in cards)
        if is_formation(m) and quarterly:
            ep = os.path.join(eg_dir, "eg-%s-%s.json" % (m, snap.commit[:8])) if eg_dir else self.eg_path(m, snap.commit)
            if not os.path.exists(ep):
                t1 = datetime.datetime.now(UTC)
                b = A.bake_eg(root, m, dm, dn, tmp, timeout=self.child_timeout("bake_eg"))
                sec["bake"] = (datetime.datetime.now(UTC) - t1).total_seconds()
                if not b or b.get("ok") is False or not b.get("scores"):
                    raise ChildError("Eg 굽기 실패: %s" % str((b or {}).get("why"))[:240], outcome=_child_outcome(b))
                sc = b["scores"]
                env = b.get("env") or (A.env_report() if hasattr(A, "env_report") else {})
                if hasattr(A, "eg_record"):
                    doc = A.eg_record(b, snap=snap.commit, adapter_blob=self.blob_work(QC.ADAPTER_REL), env=env)
                else:
                    doc = {"v": 1, "m": m, "snap": snap.commit, "code_pin": CODE_PIN,
                           "adapter_blob": self.blob_work(QC.ADAPTER_REL), "env": env,
                           "n": len(sc), "fin_lookups": b.get("fin_lookups"), "scores": sc, "sha": QC.obj_sha(sc)}
                if doc.get("sha") != QC.obj_sha(sc) or doc.get("m") != m:
                    raise ChildError("Eg 기록 모양이 다르다(m · sha)")
                write_once(ep, doc)
            cur = (m, ep)
        if not quarterly:
            fwd_eg = {}
        else:
            fwd_eg = self.fwd_eg_map(m, cur) if eg_dir is None else ({m: cur[1]} if cur else {})
        fwd_fits = (sorted(glob.glob(os.path.join(self.qdir, "fits", "Q07-*.json"))) + list(fits_extra or [])) if "QF07" in cards else []
        t1 = datetime.datetime.now(UTC)
        kw = {"withhold_fits": withhold} if (withhold and "QF07" in cards) else {}
        res = A.decide(list(cards), m, root, tmp, fwd_eg=fwd_eg, fwd_fits=fwd_fits, mode=mode, timeout=self.child_timeout("decide"),
                       **kw)
        t_end = datetime.datetime.now(UTC)
        sec["decide"] = (t_end - t1).total_seconds()
        if _NOW is not None:      # 시험 · 되풀이 흉내 — 흉내 크론 시각 + 실제로 걸린 시간(초 내림)
            t_dec = now_utc() + datetime.timedelta(seconds=int((t_end - t_start).total_seconds()))
        else:
            t_dec = t_end.replace(microsecond=0)
        if not res or not res.get("ok"):
            raise ChildError("자식 실패: %s" % str((res or {}).get("why"))[:240], outcome=_child_outcome(res))
        for c in cards:
            co = (res.get("cards") or {}).get(c) or {}
            tg = co.get("targets")
            if isinstance(tg, dict) and isinstance(tg.get("w"), dict):
                co["targets"] = tg = {TARGET_OF[c]: tg}          # 맨 목표 하나 → {이름: 목표}
            if not tg or any(not isinstance((t or {}).get("w"), dict) for t in tg.values()):
                raise ChildError("자식 결과에 %s 목표 없음" % c)
            need = {BOOKS[b][1] for b in BOOKS if BOOKS[b][0] == c}
            if not need <= set(tg):
                raise ChildError("자식 결과 %s 목표 이름 %s ≠ 장부 %s" % (c, sorted(tg), sorted(need)))
        readback = None
        if kw and res.get("new_fits"):
            # 되풀이 전용 — 방금 받은 새 적합을 fits 파일 모양으로 쓰고, 같은 뿌리에서 그 파일만으로 다시 결정한다(다시 적합 0 · 목표 같음)
            nf = res["new_fits"]
            fits = (nf.get("fits") if isinstance(nf, dict) and "fits" in nf else nf) or {}
            fp = os.path.join(tmp, "readback-fits.json")
            write_once(fp, {"v": 1, "m": m, "snap": snap.commit, "est_hash": getattr(A, "EST_HASH_PIN", None),
                            "manifest": res.get("new_fits_manifest"), "n": len(fits), "fits": fits})
            r2 = A.decide(["QF07"], m, root, tmp, fwd_eg=fwd_eg, fwd_fits=fwd_fits + [fp], mode=mode,
                          timeout=self.child_timeout("decide"), withhold_fits=withhold, tag="readback-%s" % m)
            d2 = ((r2.get("cards") or {}).get("QF07") or {}) if r2 and r2.get("ok") else {}
            dg2 = d2.get("diag") or {}
            readback = {"ok": bool(r2 and r2.get("ok")), "n_new_fits": dg2.get("n_new_fits"),
                        "from_file": (dg2.get("withheld") or {}).get("from_file"),
                        "targets_same": bool(d2) and all(QC.obj_sha(d2["targets"][k]) == QC.obj_sha(res["cards"]["QF07"]["targets"][k])
                                                         for k in ("V1", "C3"))}
        return {"res": res, "cut": cut, "root_rep": rrep, "fwd_eg": fwd_eg, "fwd_fits": fwd_fits, "t_decided": t_dec,
                "mode": mode, "sec": {k: round(v, 1) for k, v in sec.items()}, "readback": readback}

    def decide_pass(self):
        m = FIRST_M
        while True:
            dm = d_m(m)
            if close_utc(dm) >= self.now:
                break
            self.decide_month(m)
            m = mshift(m, 1)

    def decide_month(self, m):
        """[DECL] 두 무리(분기 V0 · QF07 · QF08 / QF06)를 따로 — 판 고르기 · 자식 · 오류 셈 · 대체가 무리마다 따로다.
        분기 무리의 Eg 굽기 · Q07 적합 실패가 QF06 을 마감 뒤로 밀거나 대체 판으로 넘기지 않는다(검토 2026-09-25)."""
        for g in ("Q", "M"):
            pend = [c for c in due_cards(m) if c in GROUPS[g] and (c, m) not in self.dec]
            if pend:
                self._decide_group(m, pend, g)

    def _decide_group(self, m, pend, g):
        dls = {c: deadline(c, m) for c in pend}
        att = [a for a in self.attempts() if a["m"] == m and attempt_group(a) == g]
        ne = collections.Counter(a.get("snap") for a in att if a["outcome"] == "error")
        nt = collections.Counter(a.get("snap") for a in att if a["outcome"] == "timeout")
        bad = {c for c in set(ne) | set(nt) if c and (ne[c] >= ERR_FALLBACK or nt[c] >= TO_FALLBACK)}
        sel = self.select_decision(m, skip=bad)
        passed = [c for c in pend if self.now >= dls[c]]
        if not sel["commit"]:
            self._attempt(pend, m, "no_valid_snapshot", None,
                          "후보 %d · 갈래 %s · 첫 거절 %s" % (sel["n_cands"], " · ".join("%s %d" % kv for kv in
                                                                          sorted((sel.get("reject_kinds") or {}).items())),
                                                        "; ".join(r["why"] for r in sel["rejects"][:1])), g)
            if passed:
                self._attempt(passed, m, "deadline_passed", None, "유효 판 없이 마감이 지났다", g)
            self.notes.append("결정 %s %s 대기 — 유효 판 없음(후보 %d)" % (m, g, sel["n_cands"]))
            return
        snap = sel["snap"]
        if self.budget_left() < MIN_CHILD_SEC:
            self._attempt(pend, m, "budget", snap.commit, "실행 예산 소진(남은 %d초) — 다음 실행" % self.budget_left(), g)
            self.notes.append("결정 %s %s 미룸 — 실행 예산 소진" % (m, g))
            return
        env_ok, env_why = self.env_check()
        if not env_ok:
            raise IntegrityError("환경 핀 불일치 — %s" % env_why)
        tmp = tempfile.mkdtemp(prefix="qfwd_")
        self.n_child += 1
        try:
            out = self.run_child(pend, m, snap, tmp, withhold=getattr(self, "withhold", 0))
        except subprocess.TimeoutExpired as e:
            self._attempt(pend, m, "timeout", snap.commit, "시간 초과 %s" % str(e)[:200], g)
            self.notes.append("결정 %s %s 시간 초과 — 같은 판으로 다시" % (m, g))
            return
        except MemoryError:
            self._attempt(pend, m, "timeout", snap.commit, "MemoryError", g)
            return
        except (IntegrityError, CalendarError):
            raise
        except Exception as e:
            why = "%s: %s" % (type(e).__name__, e)
            outcome = getattr(e, "outcome", None) or ("timeout" if ("Timeout" in why or "MemoryError" in why) else "error")
            self._attempt(pend, m, outcome, snap.commit, why, g)
            if passed:
                self._attempt(passed, m, "deadline_passed", snap.commit, "자식 실패로 마감이 지났다", g)
            self.notes.append("결정 %s %s %s — %s" % (m, g, outcome, why[:120]))
            return
        finally:
            if not self.keep:
                QC.rmtree(tmp)
        self.last_out = out
        self.last_outs[g] = out
        self._write_decisions(m, pend, sel, out, dls, g)

    def _write_decisions(self, m, pend, sel, out, dls, g=None):
        res, snap = out["res"], sel["snap"]
        dm, dn = d_m(m), next_td(d_m(m))
        t_dec = out["t_decided"]
        A = self.adapter()
        fits_in = []
        for p in out["fwd_fits"]:
            j = json.load(io.open(p, encoding="utf-8"))
            fits_in.append({"file": self.qrel_of(p), "sha": QC.file_sha(j), "n": j.get("n", len(j.get("fits") or {}))})
        new_fits = None
        if "QF07" in pend:
            nf = res.get("new_fits")
            fits = (nf.get("fits") if isinstance(nf, dict) and "fits" in nf else nf) or {}
            if fits:
                d7 = (res["cards"]["QF07"].get("diag") or {})
                doc = {"v": 1, "m": m, "snap": snap.commit,
                       "est_hash": (nf.get("est_hash") if isinstance(nf, dict) else None) or d7.get("est_hash")
                       or getattr(A, "EST_HASH_PIN", None),
                       "manifest": res.get("new_fits_manifest") or (nf.get("manifest") if isinstance(nf, dict) and "fits" in nf
                                                                    else None),
                       "n": len(fits), "fits": fits}
                fp = self.fits_path(m, snap.commit)
                write_once(fp, doc)
                new_fits = {"file": self.qrel_of(fp), "sha": QC.file_sha(doc), "n": len(fits)}
        eg_in = {}
        for mm, p in sorted(out["fwd_eg"].items()):
            eg_in[mm] = {"file": self.qrel_of(p), "sha": QC.file_sha(json.load(io.open(p, encoding="utf-8")))}
        ids = snap.ids
        base = {
            "m": m, "d_m": dm, "d_next": dn, "phase": "pre" if m == FIRST_M else "fwd", "group": g or group_of(pend),
            "t_decided": iso(t_dec),
            "snap": {"commit": snap.commit, "commit_time": QC.ts_iso(snap.ct), "tree_data": ids.get("data"),
                     "tip": sel.get("tip") or self.tip, "checks": sel["checks"], "cut": dm, "blank": dn, "n_cands": sel["n_cands"],
                     "rejects": sel["rejects"], "reject_kinds": sel.get("reject_kinds") or {},
                     "fallback_from": sel.get("fallback_from"), "skipped": sel.get("skipped") or [],
                     "degraded": sel.get("degraded")},
            "code": {"pin": CODE_PIN, "build_tree": BUILD_TREE, "adapter_blob": self.blob_work(QC.ADAPTER_REL),
                     "ledger_blob": self.blob_work("build/qfwd_ledger.py")},
            "env": res.get("env") or {},
            "inputs": {"blobs_V": {p.split("/", 1)[1]: ids.get(p) for p in BLOB_PATHS}, "p3": getattr(A, "P3", None),
                       "eg": eg_in, "fits": fits_in},
            "cut_report": out.get("cut"), "mode": out.get("mode") or "forward"}
        for c in ORDER:
            if c not in pend:
                continue
            co = res["cards"][c]
            tg = co["targets"]
            row = dict(base, kind="decision", card=c, deadline=iso(dls[c]), late=t_dec >= dls[c],
                       reconstructed=bool(m == FIRST_M and t_dec >= dls[c]),
                       targets=tg, targets_sha={k: QC.obj_sha(v) for k, v in sorted(tg.items())},
                       diag=co.get("diag") or {})
            if c == "QF06":
                row["states"] = co.get("states")
            if c == "QF07":
                row["new_fits"] = new_fits
            self.R.append("decisions.jsonl", row)

    # ── witness(runner local 줄의 공개 시각 증거) ──
    def witness_pass(self):
        """[DECL] gha 실행만 — origin/main 에 올라온 runner = local 결정 줄 가운데 witness 가 없는 것을 «본 시각» 으로 적는다.
        local 줄의 t_eff 는 그 시각까지 늦춰진다(커밋 시각은 사용자 PC 시계라 증거가 약하다 · 검토 2026-09-25)."""
        if self.R.runner != "gha" or not self.write:
            return 0
        tc = self.commit_times()
        seen = set(QC.witness_times(self.R.recs["decisions.jsonl"]))
        of = sorted(r["seq"] for r in self.R.recs["decisions.jsonl"]
                    if r.get("kind") == "decision" and r.get("runner") != "gha" and r["seq"] in tc and r["seq"] not in seen)
        if of:
            self.R.append("decisions.jsonl", {"kind": "witness", "of": of, "tip": self.tip})
            self.notes.append("witness — runner local 결정 줄 %d개를 gha 가 봤다" % len(of))
        return len(of)

    # ── 체결 사건 ──
    def events(self, book):
        card, tname, _cad, row = BOOKS[book]
        dec = self.dec
        upto = None
        m = FIRST_M
        while close_utc(d_m(m)) < self.now:
            upto = m
            m = mshift(m, 1)
        if upto is None:
            return []
        evs = []
        for m in book_months(card, upto):
            pl = plan(card, m, row)
            rec = dec.get((card, m))
            te = self.t_eff(rec)
            day, late, status = resolve(pl, te)
            lb = None
            if status == "pending":
                if self.now > pl["cutoff"]:
                    if pl["pre"]:
                        status = "entry_failed"
                    else:
                        lb = first_close_after(pl["dnext"], self.now)
                else:
                    lb = pl["sched"]
            evs.append({"book": book, "card": card, "target": tname, "m": m, "sched": pl["sched"], "cutoff": pl["cutoff"],
                        "rec": rec, "t_eff": te, "day": day, "lb": lb, "late_exec": late, "status": status})
        for e in evs:
            if e["status"] == "resolved" and any(x["m"] > e["m"] and x["status"] == "resolved" and x["day"] <= e["day"]
                                                 for x in evs):
                e["status"] = "superseded"          # [DECL] 늦게 체결될 결정보다 뒤 결정이 먼저 체결되면 앞 것은 버린다
        return evs

    def held_reason(self, d):
        for card in ORDER:
            for m in book_months(card, d[:7]):
                if (card, m) in self.dec:
                    continue
                for row in ("D0", "T1"):
                    pl = plan(card, m, row)
                    if pl["sched"] == d and self.now <= pl["cutoff"]:
                        return "%s %s 결정 대기(%s 마감 %s)" % (card, m, row, iso(pl["cutoff"]))
        return None

    def last_realized(self):
        mr = self.month_rows()
        hs = sorted({h for (_b, h) in mr})
        return hs[-1] if hs else None

    def keyset(self, d):
        mr = self.month_rows()
        lr = self.last_realized()
        held = set()
        if lr:
            for b in BOOKS:
                held |= set((mr.get((b, lr)) or {}).get("w_end") or {})
        start = next_td(d_m(lr)) if lr else ENTRY_DAY
        tk, okb = set(), set()
        for b in BOOKS:
            for e in self.events(b):
                if e["rec"] is None or e["status"] in ("entry_failed", "superseded"):
                    continue
                if e["day"] is not None and e["day"] < start:
                    continue
                ks = set((e["rec"]["targets"].get(e["target"]) or {}).get("w") or {})
                tk |= ks
                if e["day"] == d or (e["day"] is None and e["lb"] is not None and e["lb"] <= d):
                    okb |= ks
        return held | tk | okb, okb

    # ── 포착 ──
    def capture_pass(self):
        caps = self.R.recs["px_capture.jsonl"]
        d = next_td(caps[-1]["d"]) if caps else ENTRY_DAY
        base = bases_from(caps)
        n = 0
        while close_utc(d) < self.now:
            why = self.held_reason(d)
            if why:
                self.notes.append("포착 %s 보류 — %s" % (d, why))
                break
            sel = self.select_capture(d)
            if not sel["commit"]:
                self.notes.append("포착 %s 대기 — 유효 판 없음(후보 %d · 갈래 %s)" % (d, sel["n_cands"], sel.get("reject_kinds")))
                break
            snap = sel["snap"]
            keys, okb = self.keyset(d)
            row, base = capture_row(d, snap, keys, okb, base)
            row["snap"]["tip"] = sel.get("tip") or self.tip
            if sel.get("degraded"):
                row["degraded"] = sel["degraded"]           # [DECL] 막힘 대체 포착 — 값이 없는 이름은 null(마지막 가격으로 든다)
                self.notes.append("포착 %s — 막힘 대체 판 %s" % (d, snap.commit[:12]))
            p = row["prev"]
            mk = {"kind": "day", "d": d, "prev": p, "snap": row["snap"]}
            if sel.get("degraded"):
                mk["degraded"] = True
            for w in ("spy", "spx"):
                a, b = snap.mkt(w, d), snap.mkt(w, p)
                mk[w] = {"px": a, "r": (a / b - 1.0) if (a and b) else None}
            self.R.append("px_capture.jsonl", row)
            self.R.append("market.jsonl", mk)
            n += 1
            d = next_td(d)
        return n

    # ── 실현 ──
    def resolve_rf(self, h, caps):
        dh = d_m(h)
        c = caps[dh]["snap"]["commit"]
        fp = self.git.first_parent(self.ref)
        pos = {x: i for i, (x, _t) in enumerate(fp)}
        ct = dict(fp).get(c)
        s0 = self.snap(c, ct or 0)
        rf = s0.rf()
        if h in rf:
            return float(rf[h]), c, False
        seen = {s0.ids.get("data/rf_monthly.json")}
        for x, t in fp[pos.get(c, len(fp)) + 1:]:
            if t > int(self.now.timestamp()):
                break
            s = self.snap(x, t)
            oid = s.ids.get("data/rf_monthly.json")
            if oid in seen or not oid:
                continue
            seen.add(oid)
            r2 = s.rf()
            if h in r2:
                return float(r2[h]), x, False
        if self.now < close_utc(td_add(dh, RF_WAIT_TD)):
            return None
        last = max(k for k in rf if k <= h)
        return float(rf[last]), c, True

    def _market_month(self, h, rf_h, rf_src, rf_stale, n_h):
        mdays = self.mkt_days()
        days = month_tds(h)
        g = [1.0 + mdays[d]["spy"]["r"] for d in days]
        gx = [1.0 + mdays[d]["spx"]["r"] for d in days]
        return {"kind": "month", "h": h, "n_h": n_h, "days": [days[0], days[-1]], "rf_h": rf_h, "rf_src": rf_src, "rf_stale": rf_stale,
                "spy_m": _prod(g) - 1.0, "spx_m": _prod(gx) - 1.0}

    def realize_pass(self):
        """보유월 h 의 12 장부 줄 → 시장 월 줄. [DECL] 앞 실행이 중간에 죽어(커밋 단계는 이미 봉인한 줄을 올린다) 장부 줄 일부만 있거나
        장부는 다 있고 시장 월 줄만 없으면, 같은 입력으로 빠진 줄만 채운다(rf 는 이미 쓴 장부 줄의 값을 그대로) — 멈추지 않는다."""
        caps = self.caps()
        n = 0
        h = FWD_M1
        while close_utc(d_m(h)) < self.now:
            mr = self.month_rows()
            mm = self.mkt_months()
            have = [b for b in BOOKS if (b, h) in mr]
            if len(have) == len(BOOKS) and h in mm:
                h = mshift(h, 1)
                continue
            if len(have) == len(BOOKS):
                r0 = mr[(have[0], h)]
                self.R.append("market.jsonl", self._market_month(h, r0["rf_h"], r0.get("rf_src"), r0.get("rf_stale"), r0["n_h"]))
                self.notes.append("실현 %s — 장부 줄은 있고 시장 월 줄이 없어 채웠다(중단된 실행 복구)" % h)
                n += 1
                h = mshift(h, 1)
                continue
            dh = d_m(h)
            if dh not in caps:
                self.notes.append("실현 %s 대기 — %s 포착 전" % (h, dh))
                break
            evs = {b: self.events(b) for b in BOOKS}
            block = sorted({(e["card"], e["m"]) for b in BOOKS for e in evs[b]
                            if e["status"] == "pending" and e["lb"] is not None and e["lb"] <= dh})
            if block:
                self.notes.append("실현 %s 보류 — 체결일 미확정 %s" % (h, ", ".join("%s %s" % x for x in block)))
                break
            if have:
                r0 = mr[(have[0], h)]
                rf_h, rf_src, rf_stale = r0["rf_h"], r0.get("rf_src"), r0.get("rf_stale")
                self.notes.append("실현 %s — 장부 줄 %d/%d 만 있어 빠진 줄을 같은 입력으로 채운다(중단된 실행 복구)"
                                  % (h, len(have), len(BOOKS)))
            else:
                rf = self.resolve_rf(h, caps)
                if rf is None:
                    self.notes.append("실현 %s 보류 — rf_monthly 에 %s 없음(최대 %d거래일 기다림)" % (h, h, RF_WAIT_TD))
                    break
                rf_h, rf_src, rf_stale = rf
            n_h = len(month_tds(h))
            rows = []
            for b in BOOKS:
                if b in have:
                    continue
                prev = mr.get((b, mshift(h, -1)))
                if h != FWD_M1 and prev is None:
                    raise IntegrityError("실현 %s %s — 앞 달 줄이 없다" % (b, h))
                w0 = prev["w_end"] if prev else {}
                c0 = prev["cash_end"] if prev else 1.0
                rows.append(self._book_row(b, h, w0, c0, caps, evs[b], rf_h, rf_src, rf_stale, n_h))
            for r in rows:
                self.R.append("books.jsonl", r)
            self.R.append("market.jsonl", self._market_month(h, rf_h, rf_src, rf_stale, n_h))
            n += 1
            h = mshift(h, 1)
        return n

    def _book_row(self, b, h, w0, c0, caps, evs, rf_h, rf_src, rf_stale, n_h):
        _card, tname, _cad, row = BOOKS[b]
        pseudo = (h == FWD_M1 and row == "D0")
        days = ([ENTRY_DAY] if pseudo else []) + month_tds(h)
        dset = set(days)
        rebs, meta, skipped = {}, {}, []
        for e in evs:
            if e["status"] == "resolved" and e["day"] in dset:
                rebs[e["day"]] = {"w": e["rec"]["targets"][tname]["w"]}
                meta[e["day"]] = e
            elif e["status"] in ("superseded", "entry_failed") and e["sched"] in dset:
                skipped.append({"card": e["card"], "m": e["m"], "why": e["status"],
                                "seq": e["rec"]["seq"] if e["rec"] else None})
        out = run_book(days, w0, c0, caps, rebs, rf_h, n_h, pseudo_first=pseudo)
        reb = []
        for x in out["reb"]:
            e = meta[x["d"]]
            rec = e["rec"]
            reb.append(dict(x, src={"card": e["card"], "m": e["m"], "seq": rec["seq"], "target": tname,
                                    "sha": rec["targets_sha"][tname]},
                            sched=e["sched"], late_exec=bool(e["late_exec"])))
        used = [caps[d]["seq"] for d in days if d in caps and not (pseudo and d == ENTRY_DAY)]
        return {"kind": "month", "book": b, "h": h, "days": days, "g0": out["g0"], "reb": reb, "w_end": out["w_end"],
                "cash_end": out["cash_end"], "missing": out["missing"], "rf_h": rf_h, "n_h": n_h, "rf_src": rf_src,
                "rf_stale": rf_stale, "cap": [min(used), max(used)] if used else None, "skipped": skipped}

    # ── 한 바퀴 ──
    def auto(self):
        self.witness_pass()
        self.decide_pass()
        c = self.capture_pass()
        r = self.realize_pass()
        why = self.calendar_alarm()
        if why:
            self.alarms.append("🚨 %s — 예정 밖 휴장 · 조기 폐장이면 `python build/qfwd_ledger.py --calendar-add closed|early DATE 사유 "
                               "--src URL` 로 달력 줄을 더하고(추가만 · 사람이 커밋) 다시 돌린다. 그때까지 어긋난 판은 거절된다" % why)
        return c, r


def _prod(xs):
    p = 1.0
    for x in xs:
        p *= x
    return p


# ── 전제 (사양 §2.9 0단계) ────────────────────────────────────────────────
def preconditions(repo, qdir, out):
    """(ok, why). pins 가 없으면 (None, '미등록')."""
    pins = QC.load_pins(repo, qdir)
    if pins is None:
        return None, "미등록 — 원장 닫힘(data/_qfwd/pins.json 없음)"
    pp = QC.qpath(qdir, pins.get("parity_file") or (QREL + "/parity.json"))
    if not os.path.exists(pp):
        return False, "%s 없음 — 짝맞춤 시험 전에는 원장을 열지 않는다" % pins.get("parity_file")
    par = json.load(io.open(pp, encoding="utf-8"))
    if not par.get("ok"):
        return False, "parity.ok = false — 원장을 열지 않는다"
    ad = QC.rev_blob(repo, "HEAD", QC.ADAPTER_REL)
    if par.get("adapter_blob") != ad:
        return False, "parity.adapter_blob ≠ HEAD 어댑터 blob"
    if pins.get("parity_sha") not in (QC.raw_sha(pp), QC.file_sha(par)):
        return False, "%s sha ≠ 핀의 parity_sha" % pins.get("parity_file")
    qf = pins.get("qfwd_files") or {}
    for rel in QC.QFWD_FILES:
        if QC.rev_blob(repo, "HEAD", rel) != qf.get(rel) or QC.work_blob(repo, rel) != qf.get(rel):
            return False, "%s blob ≠ pins(수정 등록 고리 없이 핀 파일을 고쳤다)" % rel
    pv = QC.pin_chain_check(repo, pins, qdir, head=True)
    if pv:
        return False, "핀 사슬 — " + pv[0]
    if not QC.git_ok(repo, "rev-parse", "--verify", "--quiet", "origin/main"):
        return False, "origin/main 없음(--fetch)"
    rel = os.path.relpath(qdir, repo).replace(os.sep, "/")
    if not QC.git_ok(repo, "diff", "--quiet", "origin/main", "--", rel + "/"):
        return False, "data/_qfwd 가 origin/main 과 다르다 — 낡은 체크아웃에서 갈래를 만들지 않는다"
    if QC.git(repo, "status", "--porcelain", "--untracked-files=all", "--", rel + "/", check=False).strip():
        return False, "data/_qfwd 에 커밋 안 된 파일이 있다"
    ch = QC.chain_all(qdir, pins)
    errs = [e for r in ch.values() for e in r["errs"]] + QC.dup_check(ch)
    if errs:
        return False, "사슬 — " + errs[0]
    px = QC.prefix_check(repo, None, rel)
    if px["viol"]:
        return False, "접두사 — " + px["viol"][0]
    im = QC.immut_check(repo, rel)
    if im:
        return False, "한 번 쓰는 파일 — " + im[0]
    return True, "ok"


def calendar_add(row, qdir=None, repo=REPO, out=print):
    """달력 줄 하나를 더한다(사람 명령 · runner local · 추가만). 사람이 커밋 · 푸시한다(§7.6 수동 절차 — 병합 금지 · --rebase).
    [DECL] 예정 밖 휴장(closed) · 조기 폐장(early)은 NYSE 공지가 근거다(--src 에 URL) · 휴장 줄은 qfwd_check --full 이 SPY 와 대조한다."""
    q = os.path.abspath(qdir or QDIR)
    k = row.get("kind")
    try:
        if k in ("closed", "early"):
            datetime.date.fromisoformat(row["d"])
        elif k == "utc_offset":
            datetime.date.fromisoformat(row["d0"])
            datetime.date.fromisoformat(row["d1"])
            if row["off"] not in (4, 5) or row["d0"] > row["d1"]:
                raise ValueError("off ∈ {4, 5} · d0 ≤ d1")
        else:
            raise ValueError("kind 는 closed · early · utc_offset")
    except (KeyError, ValueError) as e:
        out("🚨 달력 줄 모양이 틀렸다 — %s" % e)
        return 2
    pins = QC.load_pins(repo, q)
    if pins is None:
        out("🚨 미등록 — 달력 줄은 등록 뒤에만 더한다")
        return 1
    if q == os.path.abspath(QDIR):
        rel = os.path.relpath(q, repo).replace(os.sep, "/")
        if not QC.git_ok(repo, "diff", "--quiet", "origin/main", "--", rel + "/"):
            out("🚨 data/_qfwd 가 origin/main 과 다르다 — 먼저 git pull --rebase(병합 금지)")
            return 1
    R = Records(q, pins, write=True)
    keyset = {QC.row_key("calendar.jsonl", r) for r in R.recs["calendar.jsonl"]}
    if QC.row_key("calendar.jsonl", dict(row)) in keyset:
        out("달력 줄이 이미 있다 — 아무것도 안 한다")
        return 0
    s = R.append("calendar.jsonl", dict(row))
    out("달력 줄 seq %d 을 더했다(%s) — `git add data/_qfwd/calendar.jsonl` 뒤 커밋 · git pull --rebase · git push(병합 금지)"
        % (s["seq"], k))
    return 0


# ── 상태 · 건식 · 되풀이 · 재측정 ──────────────────────────────────────────
def status(L):
    say = L.say
    now = L.now
    say("QFWD 원장 상태 — %s (%s)%s" % (iso(now), kst(now), "" if L.pins else " · 미등록"))
    for name in QC.JSONL:
        rs = L.R.recs[name]
        say("  %-18s %5d줄 · 마지막 seq %s · 사슬 OK" % (name, len(rs), rs[-1]["seq"] if rs else "-"))
    dec = L.dec
    m, due = FIRST_M, []
    while close_utc(d_m(m)) < now:
        due += [(c, m) for c in due_cards(m)]
        m = mshift(m, 1)
    for c in ORDER:
        rows = [dec[(c, mm)] for (cc, mm) in due if cc == c and (cc, mm) in dec]
        te = [(r, L.t_eff(r)) for r in rows]
        late = sum(1 for r, t in te if t is not None and t >= pts(r["deadline"]))
        pend_c = sum(1 for r, t in te if t is None)
        say("  %-5s 결정 %d · 제때 %d · 늦음 %d · 재구성 %d · 커밋 대기 %d · 빠짐 %d · 마지막 %s"
            % (c, len(rows), len(rows) - late - pend_c, late, sum(1 for r in rows if r.get("reconstructed")), pend_c,
               sum(1 for (cc, mm) in due if cc == c and (cc, mm) not in dec), max((r["m"] for r in rows), default="-")))
    caps = L.R.recs["px_capture.jsonl"]
    hs = sorted({r["h"] for r in L.R.recs["books.jsonl"] if r.get("kind") == "month"})
    say("  포착 마지막 %s · 실현 달 %d (마지막 %s)" % (caps[-1]["d"] if caps else "-", len(hs), hs[-1] if hs else "-"))
    wit = QC.witness_times(L.R.recs["decisions.jsonl"])
    say("  막힘 대체 — 결정 %d · 포착 %d · 대체 판(오류 · 시간 초과) 결정 %d · runner local 결정 %d(witness %d) · 달력 줄 %d"
        % (sum(1 for r in dec.values() if (r.get("snap") or {}).get("degraded")), sum(1 for r in caps if r.get("degraded")),
           sum(1 for r in dec.values() if (r.get("snap") or {}).get("skipped") or (r.get("snap") or {}).get("fallback_from")),
           sum(1 for r in dec.values() if r.get("runner") != "gha"),
           sum(1 for r in dec.values() if r.get("runner") != "gha" and r["seq"] in wit), len(L.R.recs["calendar.jsonl"])))
    nxt = m
    for c in due_cards(nxt):
        dl = deadline(c, nxt)
        say("  다음 %-5s %s — d_m %s · 마감 %s (%s)" % (c, nxt, d_m(nxt), iso(dl), kst(dl)))
    t30 = now - datetime.timedelta(days=30)
    att = [a for a in L.attempts() if pts(a["t"]) >= t30]
    say("  최근 30일 시도 기록 %d (판 없음 %d · 오류 %d · 시간 초과 %d · 마감 지남 %d)"
        % (len(att), sum(a["outcome"] == "no_valid_snapshot" for a in att), sum(a["outcome"] == "error" for a in att),
           sum(a["outcome"] == "timeout" for a in att), sum(a["outcome"] == "deadline_passed" for a in att)))
    seen = {}
    for r in dec.values():
        if pts(r["t_decided"]) >= t30:
            seen[(r["m"], r["snap"]["commit"])] = r["snap"]
    why = collections.Counter(x["why"].split(":")[0] for s in seen.values() for x in s.get("rejects") or [])
    say("  최근 30일 판 거절 %d (결정 판 %d개 앞의 후보) %s"
        % (sum(max(0, s.get("n_cands", 1) - 1) for s in seen.values()), len(seen),
           " · ".join("%s %d" % kv for kv in sorted(why.items()))))


def dry(L):
    say = L.say
    say("QFWD 건식 — %s · 판 고르기와 검증만(자식 · 쓰기 없음)" % iso(L.now))
    m = FIRST_M
    say("  끝(tip) %s · 달력 %s" % (L.tip[:12], L.calendar_alarm() or "끝 판 SPY 날짜와 일치"))
    while close_utc(d_m(m)) < L.now:
        for g in ("Q", "M"):
            pend = [c for c in due_cards(m) if c in GROUPS[g] and (c, m) not in L.dec]
            if not pend:
                continue
            sel = L.select_decision(m)
            if sel["commit"]:
                say("  결정 %s %s ← 판 %s (후보 %d · 거절 %d%s)" % (m, "/".join(pend), sel["commit"][:12], sel["n_cands"],
                                                            len(sel["rejects"]), " · 막힘 대체 %s" % sel["degraded"] if sel.get("degraded") else ""))
            else:
                say("  결정 %s %s — 유효 판 없음(후보 %d · 갈래 %s) %s" % (m, "/".join(pend), sel["n_cands"], sel.get("reject_kinds"),
                                                                "; ".join(r["why"] for r in sel["rejects"][:2])))
        m = mshift(m, 1)
    caps = L.R.recs["px_capture.jsonl"]
    d = next_td(caps[-1]["d"]) if caps else ENTRY_DAY
    k = 0
    while close_utc(d) < L.now and k < 5:
        why = L.held_reason(d)
        sel = L.select_capture(d)
        say("  포착 %s — %s" % (d, why or ("판 %s" % sel["commit"][:12] if sel["commit"] else "유효 판 없음(후보 %d)" % sel["n_cands"])))
        d, k = next_td(d), k + 1
    if close_utc(d) >= L.now:
        say("  다음 포착 %s — 종가 %s" % (d, iso(close_utc(d))))


def rehearse(L, M, out_dir=None):
    """과거 달 M 의 결정만(스크래치) — 개수와 targets_sha 만 찍는다. 포착 · 실현은 하지 않는다. 무리(분기 · QF06)마다 자식 하나."""
    say = L.say
    sel = L.select_decision(M)
    if not sel["commit"]:
        say("되풀이 %s — 유효 판 없음(후보 %d) %s" % (M, sel["n_cands"], "; ".join(r["why"] for r in sel["rejects"][:3])))
        return 2
    snap = sel["snap"]
    out_dir = out_dir or os.path.join(tempfile.gettempdir(), "qfwd_scratch")
    od = os.path.join(out_dir, "rehearse-%s-%s" % (M, snap.commit[:8]))
    os.makedirs(od, exist_ok=True)
    mode = "parityB" if M <= FROZEN_EG_LAST else "forward"
    doc = {"v": 1, "rehearse": M, "mode": mode, "snap": {"commit": snap.commit, "checks": sel["checks"], "tip": sel.get("tip"),
                                                         "n_cands": sel["n_cands"], "rejects": sel["rejects"]}, "cards": {}}
    say("되풀이 %s · 판 %s (후보 %d · 거절 %d) · 방식 %s" % (M, snap.commit[:12], sel["n_cands"], len(sel["rejects"]), mode))
    for g in ("Q", "M"):
        pend = [c for c in due_cards(M) if c in GROUPS[g]]
        if not pend:
            continue
        tmp = tempfile.mkdtemp(prefix="qfwd_rh_")
        try:
            out = L.run_child(pend, M, snap, tmp, mode=mode, eg_dir=od, withhold=getattr(L, "withhold", 0))
        finally:
            if not L.keep:
                QC.rmtree(tmp)
        res = out["res"]
        nf = res.get("new_fits")
        nfits = (nf.get("fits") if isinstance(nf, dict) and "fits" in nf else nf) or {}
        if nfits:
            write_once(os.path.join(od, "fits-Q07-%s.json" % M), {"v": 1, "m": M, "snap": snap.commit, "n": len(nfits), "fits": nfits})
        doc["t_decided_" + g] = iso(out["t_decided"])
        doc["cut_report"] = out.get("cut")
        for c in pend:
            co = res["cards"][c]
            tg = co["targets"]
            doc["cards"][c] = {"targets": tg, "targets_sha": {k: QC.obj_sha(v) for k, v in tg.items()},
                               "diag": co.get("diag"), "states": co.get("states")}
            for k, v in sorted(tg.items()):
                say("  %-5s %-4s 이름 %3d · targets_sha %s" % (c, k, len((v or {}).get("w") or {}), QC.obj_sha(v)[:16]))
        if out.get("readback"):
            say("  ③ 다시 읽기 %s" % out["readback"])
        say("  무리 %s · 새 적합 %d · 걸린 초 %s" % (g, len(nfits), out.get("sec")))
    say("  기록 %s" % od)
    with io.open(os.path.join(od, "decision.json"), "w", encoding="utf-8", newline="") as fh:
        fh.write(QC.canon(doc) + "\n")
    return 0


def cron_times(after, until, delay_min=0):
    """after 뒤 · until 까지 시작하는 원장 크론 시각(CRON_UTC + delay_min 분) — 오래된 것부터."""
    out = []
    day = (after - datetime.timedelta(minutes=delay_min)).date()
    while True:
        for hh, mm in CRON_UTC:
            t = datetime.datetime(day.year, day.month, day.day, hh, mm, tzinfo=UTC) + datetime.timedelta(minutes=delay_min)
            if t > until:
                return out
            if t > after:
                out.append(t)
        day += _DAY


def event_times(repo, ref, after, until, delay_min=EVENT_DELAY_MIN):
    """사건 실행 흉내 — refresh-stocks · refresh-assets 가 끝난 뒤(workflow_run) = 그 잡이 data/stocks.json · assets.json 을 바꾼 커밋 시각
    + delay_min 분. ref 에서 닿는 모든 커밋(병합으로 둘째 부모가 된 봇 커밋 포함)."""
    out = QC.git(repo, "log", "--format=%ct", ref, "--", "data/stocks.json", "data/assets.json", check=False).split()
    ts = sorted({int(x) + 60 * delay_min for x in out if x.isdigit()})
    return [datetime.datetime.fromtimestamp(t, UTC) for t in ts if after.timestamp() < t <= until.timestamp()]


def rehearse_records(months, qdir, keep=False, adapter=None, out=print, max_child=3, tamper=True, delay_min=CRON_DELAY_MIN,
                     events=True, withhold=0, tips="reconstructed"):
    """되풀이(기록판) — 과거 달 months 의 결정을 실행 흉내로 «그때 원장이 했을 그대로» 돌려 스크래치 qdir 에 사슬 기록을 쓰고
    qfwd_check(되풀이)로 점검한 뒤 지운다(--keep 이면 남긴다). 포착 · 실현은 하지 않는다(표본 안 장부 수익 금지 · 사양 §0.2).

    실행 흉내 — d_m 마감 뒤 ① 크론 시각(CRON_UTC)에 실측 지연 delay_min(기본 120분)을 더한 시각 ② 사건 실행(refresh-stocks ·
      refresh-assets 커밋 + 15분 · workflow_run)마다 now = 그 시각으로 두고 결정 단계만 돈다.
    끝(tip) — tips="reconstructed"(기본): 그 시각의 origin/main 끝을 이력에서 되짚는다(QC.tip_at — 병합으로 둘째 부모가 된 봇 커밋도
      그때는 끝이었다). "today": 오늘의 첫 부모 이력(옛 방식 · 사람의 병합이 그때 보였던 판을 지운다 — 검토 2026-09-25).
      그 시각까지 올라온 커밋 가운데 검증을 넘는 가장 이른 커밋을 고르고(규칙 V), 없으면 시도 기록을 남긴다.
      t_decided = 흉내 시각 + 실제로 걸린 시간. 얼린 Eg 표 안의 달(≤ FROZEN_EG_LAST)은 mode parityB(그달 Eg 만 구운 것으로).
    withhold = K(선택) — QF07 의 key_mx 단위 가운데 K 를 얼린 적합에서 빼 ③ 새 적합 · 기록(fits/) · 다시 읽기를 실제 자료로 태운다.
    되풀이 핀 — pins.rehearsal = true · prereg 'REHEARSE|…'(genesis 가 실제 원장과 절대 겹치지 않는다) · qfwd 파일은 작업 사본 blob.
    찍는 것 — 개수 · 해시 앞 16자 · 시각 · 걸린 초만(수익 · 비중 없음)."""
    global _NOW
    qdir = os.path.abspath(qdir)
    real = os.path.abspath(QDIR)
    if qdir == real or qdir.startswith(real + os.sep) or not os.path.relpath(qdir, REPO).startswith(".."):
        out("🚨 되풀이 기록은 저장소 밖 스크래치에만 쓴다(%s 거부)" % qdir)
        return 1
    if os.path.exists(qdir) and os.listdir(qdir):
        out("🚨 되풀이 기록 폴더 %s 가 비어 있지 않다" % qdir)
        return 1
    pp = os.path.join(real, "parity.json")
    if not os.path.exists(pp):
        out("🚨 data/_qfwd/parity.json 없음 — 짝맞춤 시험 전에는 되풀이도 하지 않는다")
        return 1
    par = json.load(io.open(pp, encoding="utf-8"))
    ad = QC.work_blob(REPO, QC.ADAPTER_REL)
    if not par.get("ok") or par.get("adapter_blob") != ad:
        out("🚨 parity.ok %s · parity.adapter_blob %s ≠ 작업 사본 어댑터 %s — 짝맞춤을 다시 돌릴 것"
            % (par.get("ok"), str(par.get("adapter_blob"))[:12], str(ad)[:12]))
        return 1
    os.makedirs(qdir, exist_ok=True)
    with io.open(pp, "rb") as fh:
        raw = fh.read()
    with io.open(os.path.join(qdir, "parity.json"), "wb") as fh:
        fh.write(raw)
    prereg = "REHEARSE|" + QC.PREREG_DEFAULT
    pins = {"v": 1, "rehearsal": True, "prereg": prereg, "code_pin": CODE_PIN, "build_tree": BUILD_TREE,
            "qfwd_files": {rel: QC.work_blob(REPO, rel) for rel in QC.QFWD_FILES},
            "genesis": {n: QC.genesis(prereg, n) for n in QC.JSONL},
            "parity_sha": QC.raw_sha(os.path.join(qdir, "parity.json"))}
    write_once(os.path.join(qdir, "pins.json"), pins)
    old_now, rc = _NOW, 0
    real_now = datetime.datetime.now(UTC).replace(microsecond=0)
    L = Ledger(repo=REPO, qdir=qdir, write=True, adapter=adapter, keep=keep, out=out)
    L.withhold = int(withhold or 0)
    allc = sorted((int(ct), h) for h, ct in (ln.split() for ln in QC.git(REPO, "log", "--format=%H %ct", L.ref).splitlines()
                                             if ln.strip()))
    import bisect

    def tip_at(t):
        j = bisect.bisect_right(allc, (int(t.timestamp()), "~"))
        return allc[j - 1][1] if j else L.tip
    tip_today = L.tip
    out("되풀이 방식 — 끝 %s · 크론 지연 %d분 · 사건 실행 %s · withhold %d"
        % ("그 시각의 origin/main 끝(되짚음)" if tips == "reconstructed" else "오늘의 첫 부모 이력", delay_min,
           "켬(+%d분)" % EVENT_DELAY_MIN if events else "끔", L.withhold))
    summary = []
    try:
        for M in months:
            dm = d_m(M)
            pend0 = due_cards(M)
            ts = cron_times(close_utc(dm), real_now, delay_min)
            if events:
                ts = sorted(set(ts) | set(event_times(REPO, L.ref, close_utc(dm), real_now)))
            n0 = L.n_child
            first_cand, done_at, k = {}, {}, 0
            for t in ts:
                pend = [c for c in pend0 if (c, M) not in L.dec]
                if not pend:
                    break
                _NOW = t
                L.now = t
                L.tip = tip_at(t) if tips == "reconstructed" else tip_today
                k += 1
                for g in ("Q", "M"):
                    if g not in first_cand and any(c in GROUPS[g] for c in pend) and \
                            L.select_decision(M, until_ts=int(t.timestamp()))["n_cands"]:
                        first_cand[g] = t
                L.decide_month(M)
                for g in ("Q", "M"):
                    if g not in done_at and all((c, M) in L.dec for c in pend0 if c in GROUPS[g]) and \
                            any(c in GROUPS[g] for c in pend0):
                        done_at[g] = t
                if L.n_child - n0 >= max_child + 2:
                    out("  %s — 자식 %d번 · 멈춤" % (M, L.n_child - n0))
                    break
            _NOW = None
            rows = [L.dec[(c, M)] for c in pend0 if (c, M) in L.dec]
            att = [a for a in L.attempts() if a["m"] == M]
            oc = collections.Counter("%s/%s" % (attempt_group(a), a["outcome"]) for a in att)
            out("되풀이 %s — d_m %s · 마감 %s · 실행 %d번 흉내 · 첫 후보가 보인 실행 %s · 결정 실행 %s · 시도 기록 %s"
                % (M, dm, " / ".join("%s %s" % (c, iso(deadline(c, M))) for c in pend0), k,
                   " · ".join("%s %s" % (g, iso(t)) for g, t in sorted(first_cand.items())) or "-",
                   " · ".join("%s %s" % (g, iso(t)) for g, t in sorted(done_at.items())) or "없음",
                   " · ".join("%s %d" % kv for kv in sorted(oc.items())) or "0"))
            if len(rows) < len(pend0):
                rc = 1
                for a in att[-3:]:
                    out("    시도 %s %s %s — %s" % (attempt_group(a), a["outcome"], (a.get("snap") or "-")[:12], a.get("detail", "")[:200]))
            if not rows:
                summary.append({"m": M, "ok": False})
                continue
            for g in ("Q", "M"):
                rg = [r for r in rows if r["card"] in GROUPS[g]]
                if not rg:
                    continue
                r0 = rg[0]
                sn = r0["snap"]
                out("  [%s] 판 V %s (커밋 %s · 끝 %s · 후보 %d · 거절 %d) · 방식 %s · ih %s · 자른 격자 %s일 · 멤버십 자른 달 %s · t_decided %s%s"
                    % (g, sn["commit"][:12], sn["commit_time"], (sn.get("tip") or "-")[:12], sn["n_cands"], len(sn["rejects"]),
                       r0.get("mode"), sn["checks"].get("ih"), (r0.get("cut_report") or {}).get("n_cut"),
                       (r0.get("cut_report") or {}).get("ih_drop"), r0["t_decided"],
                       " · 막힘 대체 %s" % sn["degraded"] if sn.get("degraded") else ""))
                for rj in sn["rejects"]:
                    out("    거절 %s — %s" % (rj["commit"], rj["why"][:150]))
                out("    거절 갈래 %s" % " · ".join("%s %d" % kv for kv in sorted((sn.get("reject_kinds") or {}).items())))
                for r in rg:
                    tg = r["targets"]
                    out("  %-5s 늦음 %-5s · %s" % (r["card"], r["late"], " · ".join(
                        "%s 이름 %d sha %s" % (nm, len(tg[nm]["w"]), r["targets_sha"][nm][:16]) for nm in sorted(tg))))
                    if r["card"] == "QF07":
                        dg = r.get("diag") or {}
                        out("        QF07 key_mx 단위 %s · 새 적합 %s · 적합 파일 %s · withhold %s"
                            % (dg.get("n_mx"), dg.get("n_new_fits"), (r.get("new_fits") or {}).get("file", "-"), dg.get("withheld")))
                    if r["card"] == "QF06":
                        st = r.get("states") or {}
                        out("        QF06 상태 st %s · s1 %s · s2 %s (1 = OFFENSE · 0 = DEFENSE · 다음 달 위치) · 역사 %s달"
                            % (st.get("st"), st.get("s1"), st.get("s2"), st.get("n_hist")))
                eg = (r0.get("inputs") or {}).get("eg") or {}
                if eg:
                    out("  Eg 입력 %s" % " · ".join("%s %s sha %s" % (mm, x["file"].rsplit("/", 1)[-1], x["sha"][:16])
                                                    for mm, x in sorted(eg.items())))
            for g, lo in sorted(L.last_outs.items()):
                out("  [%s] 자식 걸린 초 %s · 자식 %s초%s" % (g, lo.get("sec"), (lo.get("res") or {}).get("sec"),
                                                      " · ③ 다시 읽기 %s" % lo["readback"] if lo.get("readback") else ""))
            L.last_outs = {}
            summary.append({"m": M, "ok": len(rows) == len(pend0), "cards": [r["card"] for r in rows],
                            "late": [r["card"] for r in rows if r["late"]]})
    finally:
        _NOW = old_now
        L.close()
    okc, summ = QC.run_checks(REPO, full=True, qdir=qdir, out=out, rehearsal=True)
    rc = rc or (0 if okc else 1)
    if tamper and okc:
        rc = rc or _rehearse_tamper(qdir, out)
    out("되풀이 요약 — 달 %d · 결정 달 %d · 사슬 줄 %s · 점검 %s"
        % (len(months), sum(1 for x in summary if x["ok"]), summ.get("rows"), "통과" if okc else "위반"))
    if keep:
        out("  기록 남김 %s" % qdir)
    else:
        QC.rmtree(qdir)
        out("  되풀이 기록 지움(%s · 남은 것 %s)" % (qdir, "없음" if not os.path.exists(qdir) else "있음 🚨"))
    return rc


def _rehearse_tamper(qdir, out):
    """되풀이 기록의 사본을 변조해 qfwd_check 가 잡는지 — 결정 줄 숫자 한 자 · 가운데 결정 줄 삭제 · Eg 파일 점수 하나.
    원 기록은 건드리지 않는다. 0 = 모두 잡음."""
    import shutil
    fails, cases = 0, []
    lines = io.open(os.path.join(qdir, "decisions.jsonl"), encoding="utf-8").read().split("\n")[:-1]
    j = next((i for i, ln in enumerate(lines[:-1]) if '"kind":"decision"' in ln), None)
    if j is not None:
        ln = lines[j]
        k = ln.index('"targets":') + len('"targets":')
        pos = next(i for i in range(k, len(ln)) if ln[i] in "123456789")
        bad = ln[:pos] + ("1" if ln[pos] != "1" else "2") + ln[pos + 1:]
        cases.append(("결정 줄 숫자 한 자", lambda q: _tamper_line(q, j, bad), ("sha 불일치", "정본 아님")))
        cases.append(("가운데 결정 줄 삭제", lambda q: _tamper_line(q, j, None), ("사슬 끊김",)))
    egs = sorted(glob.glob(os.path.join(qdir, "eg", "*.json")))
    if egs:
        rel = os.path.relpath(egs[0], qdir)

        def _eg(q, rel=rel):
            p = os.path.join(q, rel)
            d = json.load(io.open(p, encoding="utf-8"))
            t0 = sorted(d["scores"])[0]
            d["scores"][t0] = (d["scores"][t0] or 0.0) + 1e-6
            with io.open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(QC.fcanon(d) + "\n")
        cases.append(("Eg 파일 점수 하나", _eg, ("sha 불일치",)))
    for name, fn, want in cases:
        q2 = qdir + "_tamper"
        QC.rmtree(q2)
        shutil.copytree(qdir, q2)
        try:
            fn(q2)
            okc, summ = QC.run_checks(REPO, full=False, qdir=q2, out=lambda *_: None, rehearsal=True, reselect=False)
            hit = (not okc) and any(w in v for v in summ["viol"] for w in want)
            out("  변조 점검 — %s → %s" % (name, "잡음" if hit else "못 잡음 🚨"))
            fails += 0 if hit else 1
        finally:
            QC.rmtree(q2)
    return 1 if fails else 0


def _tamper_line(q, j, new):
    p = os.path.join(q, "decisions.jsonl")
    lines = io.open(p, encoding="utf-8").read().split("\n")[:-1]
    if new is None:
        del lines[j]
    else:
        lines[j] = new
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")


def recheck(L):
    """실현 달 — 최신 유효 판으로 장부 월 성장 · 시장 월을 다시 재서 1bp 넘게 어긋나면 WARN(차이만) · 원 기록 유지."""
    say = L.say
    mr = L.month_rows()
    mm = L.mkt_months()
    fp = L.git.first_parent(L.tip)
    nw = 0
    for h in sorted(mm):
        dh = d_m(h)
        snap = None
        for c, ct in reversed(fp):
            if ct <= int(close_utc(dh).timestamp()):
                break
            s = L.snap(c, ct)
            try:
                if L.valid_capture(s, dh)["ok"]:
                    snap = s
                    break
            except CalendarError:
                continue
        if snap is None:
            say("  %s 다시 잴 유효 판 없음" % h)
            continue
        days = month_tds(h)
        for w, fld in (("spy", "spy_m"), ("spx", "spx_m")):
            px = [(snap.mkt(w, d), snap.mkt(w, prev_td(d))) for d in days]
            if any(a is None or b is None for a, b in px):
                say("  %s %s 다시 잴 시장 가격이 판에 없다" % (h, w))
                continue
            dx = (_prod([a / b for a, b in px]) - 1.0 - mm[h][fld]) * 1e4
            if abs(dx) > 1.0:
                say("WARN market.%s %s %+.2fbp" % (w, h, dx))
                nw += 1
        for b in BOOKS:
            row = mr.get((b, h))
            if not row:
                continue
            pmo = mr.get((b, mshift(h, -1)))
            w0 = pmo["w_end"] if pmo else {}
            c0 = pmo["cash_end"] if pmo else 1.0
            pseudo = row["days"][0] == ENTRY_DAY and h == FWD_M1 and BOOKS[b][3] == "D0"
            keys = set(w0) | {k for e in row["reb"] for k in (L.dec[(e["src"]["card"], e["src"]["m"])]["targets"]
                                                               [e["src"]["target"]]["w"])}
            rc, lastv = {}, {}
            for k in keys:
                lastv[k] = None
            d0 = prev_td(days[0])
            for k in keys:
                lastv[k] = d0 if snap.price(k, d0) is not None else None
            for d in row["days"]:
                if pseudo and d == ENTRY_DAY:
                    continue
                r, ok = {}, {}
                for k in keys:
                    pd, b0 = snap.price(k, d), lastv[k]
                    pb = snap.price(k, b0) if b0 else None
                    r[k] = (pd / pb - 1.0) if (pd and pb) else None
                    ok[k] = pd is not None
                    if pd is not None:
                        lastv[k] = d
                rc[d] = {"r": r, "ok_buy": ok}
            if pseudo:
                rc[ENTRY_DAY] = {"r": {}, "ok_buy": {k: snap.price(k, ENTRY_DAY) is not None for k in keys}}
            rebs = {e["d"]: {"w": L.dec[(e["src"]["card"], e["src"]["m"])]["targets"][e["src"]["target"]]["w"]}
                    for e in row["reb"]}
            try:
                o = run_book(row["days"], w0, c0, rc, rebs, row["rf_h"], row["n_h"], pseudo_first=pseudo)
            except IntegrityError as e:
                say("  %s %s 다시 재기 실패 — %s" % (b, h, e))
                continue
            dd = (_prod(o["g0"]) - _prod(row["g0"])) * 1e4
            if abs(dd) > 1.0:
                say("WARN %s %s %+.2fbp" % (b, h, dd))
                nw += 1
    say("재측정 — 실현 달 %d · WARN %d (원 기록은 그대로)" % (len(mm), nw))
    return 0


# ── 자가 시험 ───────────────────────────────────────────────────────────────
NYSE_2026 = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
             "2026-09-07", "2026-11-26", "2026-12-25"]
NYSE_2027 = ["2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05",
             "2027-09-06", "2027-11-25", "2027-12-24"]
EARLY_2026, EARLY_2027 = ["2026-11-27", "2026-12-24"], ["2027-11-26"]


class _FakeSnap:
    """합성 판 — {키: {날: 가격}} · 원천은 모두 'sd'."""

    def __init__(self, commit, ct, px):
        self.commit, self.ct, self.px = commit, ct, px

    def src(self, k):
        return "sd" if k in self.px else None

    def price(self, k, d):
        v = (self.px.get(k) or {}).get(d)
        return v if (v is not None and v == v and v > 0) else None


def _selftest_engine(ok):
    """엔진 = qg_lab.World.sleeve(얇은 틀 · q_bmrot_leg._Book 과 같은 방식) — 합성 가격 · 비용 0 · 10 · 20bp."""
    import random
    import numpy as np
    import qg_lab as QL
    rnd = random.Random(20260925)
    dates = tds("2026-10-01", "2027-03-31")
    di = {d: i for i, d in enumerate(dates)}
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    keys = ["K%d" % j for j in range(8)]
    PX = {}
    for j, k in enumerate(keys):
        p, a = 50.0 + 10 * j, []
        for i, d in enumerate(dates):
            p *= math.exp(rnd.gauss(0.0003, 0.02))
            a.append(p)
        PX[k] = np.array(a)
    PX["K3"][di["2026-11-10"]:di["2026-11-13"]] = np.nan         # 구멍 — 마지막 가격을 들고 간다
    PX["K5"][di["2027-01-20"]:] = np.nan                          # 편출 — 다음 되맞춤에 마지막 값으로 판다
    PX["K7"][di["2026-12-31"]] = np.nan                           # 되맞춤 날 가격 없음 — 사지 않는다
    RF = {"2026-11": 0.0035, "2026-12": 0.0033, "2027-01": 0.0031, "2027-02": 0.0030, "2027-03": 0.0029}

    def tgt(ks, cashy=0.0):
        w = [rnd.random() + 0.2 for _ in ks]
        s = sum(w) / (1.0 - cashy)
        return {"w": {k: x / s for k, x in zip(ks, w)}, "names": {k: k for k in ks}}
    T = {"2026-10": tgt(keys[:6]), "2026-12": tgt(["K0", "K2", "K5", "K6", "K7"], 0.05)}

    class Stub:
        def __init__(self):
            self.PX, self.me, self.RF, self.dates = PX, me, RF, dates
            self.months = ["2026-10", "2026-11", "2026-12", "2027-01", "2027-02"]

        def weights(self, cand, m):
            return dict(T[m]["w"]), dict(T[m]["names"])

    stub = Stub()
    old = QL.COST
    ref = {}
    try:
        for c in COSTS:
            QL.COST = c
            ref[c] = QL.World.sleeve(stub, {"reb": 3})[0]
    finally:
        QL.COST = old
    snap = _FakeSnap("f" * 40, 0, {k: {d: (None if PX[k][i] != PX[k][i] else float(PX[k][i]))
                                        for i, d in enumerate(dates)} for k in keys})
    base, caps = {}, {}
    rebday = {ENTRY_DAY: T["2026-10"], d_m("2026-12"): T["2026-12"]}
    for d in [ENTRY_DAY] + tds("2026-11-01", "2027-03-31"):
        okb = set(rebday[d]["w"]) if d in rebday else set()
        row, base = capture_row(d, snap, set(keys), okb, base)
        caps[d] = row
    w, cash = {}, 1.0
    mine = {c: [] for c in COSTS}
    daylist = []
    for h in ("2026-11", "2026-12", "2027-01", "2027-02", "2027-03"):
        pseudo = h == FWD_M1
        days = ([ENTRY_DAY] if pseudo else []) + month_tds(h)
        rebs = {d: {"w": rebday[d]["w"]} for d in days if d in rebday}
        o = run_book(days, w, cash, caps, rebs, RF[h], len(month_tds(h)), pseudo_first=pseudo)
        ok(abs(sum(o["w_end"].values()) + o["cash_end"] - 1.0) < 1e-12, "엔진 %s 끝 몫 합 = 1" % h)
        for c in COSTS:
            mine[c] += g_cost(o["g0"], o["reb"], c)
        daylist += days
        w, cash = o["w_end"], o["cash_end"]
    for c in COSTS:
        cum, worst = 1.0, 0.0
        for d, g in zip(daylist, mine[c]):
            cum *= g
            worst = max(worst, abs(cum / ref[c][di[d]] - 1.0))
        ok(worst < 1e-12, "엔진 = qg_lab.sleeve (비용 %gbp · 최대 상대오차 %.1e)" % (c * 1e4, worst))


def _selftest_capture(ok):
    """포착 기준점 — 구멍은 다음 유효 포착이 통째로 실현 · 판에서 기준 가격이 사라지면 사지 않는다."""
    d0, d1, d2, d3 = "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"
    s1 = _FakeSnap("a" * 40, 1, {"A": {d0: 10.0, d1: 11.0}, "B": {d0: 20.0, d1: None}})
    r1, b1 = capture_row(d1, s1, {"A", "B"}, set(), {"A": d0, "B": d0})
    ok(abs(r1["r"]["A"] - 0.1) < 1e-15 and r1["r"]["B"] is None and b1["B"] == d0 and b1["A"] == d1,
       "구멍 → r null · 기준점 유지")
    s2 = _FakeSnap("b" * 40, 2, {"A": {d0: 10.0, d1: 11.0, d2: 12.1}, "B": {d0: 20.0, d1: 21.0, d2: 23.0}})
    r2, b2 = capture_row(d2, s2, {"A", "B"}, set(), b1)
    ok(abs(r2["r"]["B"] - 0.15) < 1e-15 and r2["base"] == {"B": d0} and b2["B"] == d2,
       "다음 유효 포착이 기준점부터 통째로 실현(base 기록)")
    s3 = _FakeSnap("c" * 40, 3, {"A": {d2: None, d3: 13.0}, "B": {d2: 23.0, d3: 24.0}, "C": {d3: 5.0}})
    r3, b3 = capture_row(d3, s3, {"A", "B", "C", "Z"}, {"A", "C", "Z"}, b2)
    ok(r3["r"]["A"] is None and r3["ok_buy"]["A"] is False and b3["A"] == d2,
       "기준 가격이 판에서 사라진 이름은 사지 않는다(ok_buy false · 기준점 유지)")
    ok(r3["ok_buy"]["C"] is True and b3["C"] == d3 and r3["r"]["C"] is None, "처음 사는 이름 → 기준점 = 산 날")
    ok(r3["none"] == ["Z"] and r3["ok_buy"]["Z"] is False, "계열 없는 이름 → none · 사지 않는다")
    caps = [r1, r2, r3]
    for i, c in enumerate(caps):
        c["seq"] = i
    ok(bases_from(caps) == b3, "기록에서 기준점 복원 = 누적 기준점")


def _selftest_exec(ok):
    """체결일 — 제때 · 늦음(첫 종가 뒤) · T+1 · 사전 진입 · 대체."""
    pl = plan("QF07", "2026-12", "D0")
    ok(pl["sched"] == "2026-12-31" and iso(pl["cutoff"]) == "2027-01-04T14:30:00Z", "D0 계획 — d_m 종가 · 다음 개장 마감")
    ok(resolve(pl, pts("2027-01-04T14:29:00Z"))[:2] == ("2026-12-31", False), "D0 제때 → d_m")
    ok(resolve(pl, pts("2027-01-04T15:00:00Z"))[:2] == ("2027-01-04", True), "D0 늦음 → 그날 종가(첫 종가 뒤)")
    ok(resolve(pl, pts("2027-01-04T21:30:00Z"))[:2] == ("2027-01-05", True), "D0 늦음(종가 뒤) → 다음 거래일")
    pl = plan("QF06", "2026-11", "T1")
    ok(pl["sched"] == "2026-12-01" and iso(pl["cutoff"]) == "2026-12-01T20:30:00Z", "T1 계획 — 다음 거래일 · 마감 30분 전")
    ok(resolve(pl, pts("2026-12-01T20:40:00Z"))[:2] == ("2026-12-01", True), "T1 30분 안 → 그날 종가 · late_exec")
    pl = plan("QF06", "2026-10", "D0")
    ok(pl["sched"] == ENTRY_DAY and iso(pl["cutoff"]) == "2026-11-02T14:30:00Z", "XBM 진입 = 2026-10 목표 · ENTRY_DAY")
    pl = plan("V0", "2026-09", "T1")
    ok(pl["pre"] and pl["sched"] == "2026-11-02", "Q 사전 진입 T1 = 2026-11-02")
    ok(resolve(pl, pts("2026-10-29T23:59:59Z"))[2] == "resolved" and resolve(pl, pts("2026-10-30T00:00:00Z"))[2] == "entry_failed",
       "사전 진입 — PRE_RECON_UNTIL 넘으면 entry_failed")
    ok(iso(deadline("QF07", "2026-09")) == "2026-10-01T13:30:00Z" and iso(deadline("QF06", "2026-09")) == "2026-10-01T19:30:00Z",
       "첫 결정 마감 — 개장 13:30Z · 마감 30분 전 19:30Z (EDT)")
    ok(iso(deadline("V0", "2026-10")) == "2026-11-02T14:30:00Z" and iso(deadline("QF06", "2026-10")) == "2026-11-02T20:30:00Z",
       "2026-10 마감 — EST 로 한 시간 뒤")
    ok(iso(close_utc("2026-11-27")) == "2026-11-27T18:00:00Z" and iso(close_utc("2026-12-24")) == "2026-12-24T18:00:00Z",
       "조기 폐장 13:00 ET")
    ok(first_close_after("2026-11-26", pts("2026-11-25T23:00:00Z")) == "2026-11-27", "휴장일 건너뛰기")


def _selftest_calendar(ok):
    h26 = sorted(holidays(2026))
    h27 = sorted(holidays(2027))
    ok(h26 == NYSE_2026, "NYSE 2026 휴장 %d일 = 공표" % len(h26))
    ok(h27 == NYSE_2027, "NYSE 2027 휴장 %d일 = 공표" % len(h27))
    ok(sorted(early_closes(2026)) == EARLY_2026 and sorted(early_closes(2027)) == EARLY_2027, "조기 폐장 2026 · 2027")
    ok(is_edt("2026-03-09") and not is_edt("2026-03-06") and is_edt("2026-10-30") and not is_edt("2026-11-02"),
       "서머타임 2026 — 3-08 ~ 11-01")
    ok(is_edt("2027-03-15") and not is_edt("2027-03-12") and is_edt("2027-11-05") and not is_edt("2027-11-08"),
       "서머타임 2027 — 3-14 ~ 11-07")
    ok(d_m("2026-09") == "2026-09-30" and d_m("2026-10") == "2026-10-30" and next_td(ENTRY_DAY) == "2026-11-02",
       "d_m · 진입 · T+1")
    ok(len(month_tds("2026-11")) == 20 and len(tds("2026-01-01", "2026-12-31")) == 251, "2026 거래일 251 · 11월 20")
    try:
        holidays(2040)
        ok(False, "달력 범위 밖 → 멈춤")
    except CalendarError:
        ok(True, "달력 범위 밖 → 멈춤")
    apply_calendar([{"kind": "closed", "d": "2026-11-30", "why": "시험"}, {"kind": "early", "d": "2026-11-25", "why": "시험"},
                    {"kind": "utc_offset", "d0": "2027-11-08", "d1": "2027-11-30", "off": 4, "why": "시험"}])
    try:
        ok(d_m("2026-11") == "2026-11-27" and not is_td("2026-11-30") and iso(close_utc("2026-11-25")) == "2026-11-25T18:00:00Z"
           and iso(open_utc("2027-11-09")) == "2027-11-09T13:30:00Z" and iso(open_utc("2027-12-01")) == "2027-12-01T14:30:00Z",
           "달력 줄 — 예정 밖 휴장(d_m 이 당겨진다) · 조기 폐장 · UTC 시차가 코드 핀 없이 적용된다")
    finally:
        apply_calendar([])
    ok(d_m("2026-11") == "2026-11-30" and iso(close_utc("2026-11-25")) == "2026-11-25T21:00:00Z", "달력 줄 비우면 규칙 달력으로 돌아온다")


def _selftest_records(ok):
    tmp = tempfile.mkdtemp(prefix="qfwd_led_")
    try:
        pins = {"prereg": "build/PREREG-test.md", "genesis": {n: QC.genesis("build/PREREG-test.md", n) for n in QC.JSONL}}
        R = Records(tmp, pins, write=True)
        a = R.append("market.jsonl", {"kind": "day", "d": "2026-11-02", "spy": {"px": 700.1, "r": 0.001}})
        R.append("market.jsonl", {"kind": "day", "d": "2026-11-03", "spy": {"px": 701.0, "r": None}})
        R2 = Records(tmp, pins, write=False)
        ok(len(R2.recs["market.jsonl"]) == 2 and R2.recs["market.jsonl"][0]["sha"] == a["sha"], "기록 왕복 · 사슬 다시 읽기")
        p = os.path.join(tmp, "market.jsonl")
        txt = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8", newline="").write(txt.replace("700.1", "700.2"))
        try:
            Records(tmp, pins, write=False)
            ok(False, "변조한 기록 → 원장이 열리지 않는다")
        except IntegrityError:
            ok(True, "변조한 기록 → 원장이 열리지 않는다")
        io.open(p, "w", encoding="utf-8", newline="").write(txt.replace("\n", "\r\n"))
        ok(len(Records(tmp, pins, write=False).recs["market.jsonl"]) == 2, "CRLF 작업 사본도 같은 사슬로 읽는다")
        try:
            write_once(os.path.join(tmp, "eg", "x.json"), {"a": 1})
            write_once(os.path.join(tmp, "eg", "x.json"), {"a": 1})
            write_once(os.path.join(tmp, "eg", "x.json"), {"a": 2})
            ok(False, "한 번 쓰는 파일 — 다른 내용 거부")
        except IntegrityError:
            ok(True, "한 번 쓰는 파일 — 같은 내용은 통과 · 다른 내용 거부")
    finally:
        QC.rmtree(tmp)


def _selftest_git(ok):
    """실제 이력(git 만) — 판 고르기 · 거절 사유 · 달력 대조. 수익은 읽지 않는다."""
    L = Ledger(repo=REPO, write=False, out=lambda *_: None)
    try:
        fp = L.git.first_parent(L.tip)
        ok(len(fp) > 10, "첫 부모 이력 %d커밋 (%s · 끝 %s)" % (len(fp), L.ref, L.tip[:12]))
        tip = L.snap(*fp[-1])
        cw = L.cal_check(tip, "2026-01-02")
        ok(cw is None, "NYSE 달력 = 끝 판 assets SPY 날짜(2026-01-02 ~ %s)%s" % (tip.spy_days()[-1], (" — " + cw) if cw else ""))
        g = L._grid(tip)
        print("     HEAD 격자: %s" % (g or "일치"))
        first_ct = fp[0][1]
        days = [d for d in tds("2026-09-01", "2026-09-30")
                if close_utc(d).timestamp() > first_ct and close_utc(d) < L.now]
        n_ok = 0
        for d in days:
            sel = L.select_capture(d)
            if sel["commit"]:
                n_ok += 1
                t0 = close_utc(d).timestamp()
                cands = [(c, ct) for c, ct in fp if t0 < ct <= L.now.timestamp()]
                j = [c for c, _ct in cands].index(sel["commit"])
                ok(sel["ct"] > t0 and all(not L.valid_capture(L.snap(c, ct), d)["ok"] for c, ct in cands[:j]),
                   "포착 %s — 고른 판(후보 %d번째)보다 이른 후보는 모두 무효" % (d, j + 1))
            print("     포착 %s → %s · 후보 %d · 거절 %s" % (d, sel["commit"][:12] if sel["commit"] else "없음",
                                                     sel["n_cands"], [r["why"][:50] for r in sel["rejects"][:2]]))
        ok(n_ok > 0, "포착 판 고르기 — %d/%d일 유효 · 고른 판보다 이른 후보는 모두 무효" % (n_ok, len(days)))
        sel = L.select_decision("2026-08", until_ts=int(L.now.timestamp()))
        print("     결정 2026-08(가장 이른 유효 판 · 얕은 복제면 경계 커밋 뒤에서만 고른다) → %s · 후보 %d · 거절 %s"
              % (sel["commit"][:12] if sel["commit"] else "없음", sel["n_cands"], [r["why"][:60] for r in sel["rejects"][:3]]))
        ok(sel["n_cands"] > 0, "결정 판 고르기 돈다(후보 %d)" % sel["n_cands"])
    finally:
        L.close()


class _StubAdapter:
    """합성 어댑터(시험 전용) — 뿌리 · 자르기 · Eg · 결정을 흉내 낸다. 얼린 코드는 부르지 않는다."""
    P3 = {"data/_stub.json": "0" * 40}
    EST_HASH_PIN = "e" * 64

    def __init__(self, keys, fail=()):
        self.keys, self.fail, self.calls = list(keys), set(fail), []
        self.ENV_PIN = {"python": tuple(sys.version_info[:2])}

    def build_root(self, commit, pin, tmp, **k):
        return os.path.join(tmp, "root"), {"data_commit": commit}

    def cut_and_blank(self, root, m, dm, dn, **k):
        return {"d_m": dm, "d_next": dn, "ih": "m-1", "n_cut": 1}

    def bake_eg(self, root, m, dm, dn, tmp, **k):
        return {"ok": True, "m": m, "scores": {t: round(0.01 * i, 6) for i, t in enumerate(self.keys)},
                "n": len(self.keys), "fin_lookups": 0}

    def _tg(self, seed, n):
        import random
        r = random.Random(seed)
        ks = r.sample(self.keys, n)
        w = [r.random() + 0.2 for _ in ks]
        s = sum(w)
        return {"w": {k: x / s for k, x in sorted(zip(ks, w))}, "names": {k: k for k in sorted(ks)}}

    def decide(self, cards, m, root, tmp, fwd_eg=None, fwd_fits=None, mode="forward", **k):
        self.calls.append((m, tuple(cards), sorted(fwd_eg or {}), len(fwd_fits or [])))
        if (m, tuple(cards)) in self.fail:
            self.fail.discard((m, tuple(cards)))
            return {"ok": False, "why": "RuntimeError: 합성 실패(한 번)"}
        out = {}
        for j, c in enumerate(cards):
            sd = int(m[:4]) * 100 + int(m[5:7]) * 10 + ORDER.index(c)
            if c == "V0":
                out[c] = {"targets": self._tg(sd, 4), "diag": {"n": 4}}
            elif c in ("QF07", "QF08"):
                out[c] = {"targets": {"V1": self._tg(sd + 1, 4), "C3": self._tg(sd + 2, 4)},
                          "diag": {"est_hash": self.EST_HASH_PIN}}
            else:
                st = int(m[5:7]) % 2
                out[c] = {"targets": {"XBM": self._tg(sd + 3, 3)},
                          "states": {"st": st, "s1": 1, "s2": st, "signal": st == 0}}
        nf = {"U-%s" % m: {"theta": 0.5, "D_all": [1.0, float("nan")]}} if "QF07" in cards else None
        return {"ok": True, "cards": out, "new_fits": nf, "new_fits_manifest": ("m" * 64) if nf else None,
                "env": {"python": "stub"}, "sec": 0.01}


def _selftest_e2e(ok):
    """합성 git 저장소 · 합성 어댑터 — 2026-09-28 ~ 2026-12-04 크론을 흉내 내 결정 → 포착 → 첫 실현까지.
    자식 실패 한 번(재시도) · 무효 판 한 번(거절 기록) · 미커밋 줄의 체결일 보류 · qfwd_check --full(판 재선택 포함)."""
    import random
    global _NOW
    tmp = tempfile.mkdtemp(prefix="qfwd_e2e_")
    old_now = _NOW
    try:
        def sh(*args, when=None):
            env = dict(os.environ)
            if when:
                env.update(GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
            r = subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True, encoding="utf-8", env=env)
            if r.returncode:
                raise RuntimeError(r.stderr[:300])
            return r.stdout

        sh("init", "-q", "-b", "main")
        sh("config", "user.name", "qfwd-e2e")
        sh("config", "user.email", "qfwd@e2e.invalid")
        sh("config", "core.autocrlf", "false")
        rnd = random.Random(11)
        pre, x = [], datetime.date(2025, 8, 1)
        while x < datetime.date(2026, 1, 1):
            if x.weekday() < 5 and x.isoformat() not in ("2025-09-01", "2025-11-27", "2025-12-25"):
                pre.append(x.isoformat())
            x += _DAY
        allD = pre + tds("2026-01-02", "2026-12-31")
        sdk, pitk = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"], ["PPP", "QQX"]
        mk = ["SPY"] + list(SPDR9)
        px = {}
        for k in sdk + pitk + mk + ["^GSPC"]:
            p, row = 50.0 + rnd.random() * 50, {}
            for d in allD:
                p *= math.exp(rnd.gauss(0.0003, 0.015))
                row[d] = round(p, 4)
            px[k] = row
        px["DDD"] = {d: (None if "2026-11-10" <= d <= "2026-11-12" else v) for d, v in px["DDD"].items()}

        def wj(rel, obj):
            pth = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            with io.open(pth, "w", encoding="utf-8", newline="") as fh:
                fh.write(json.dumps(obj, separators=(",", ":")))

        def data_commit(last, when, lag_pit=False):
            S = [d for d in allD if d <= last]
            wj("data/stocks.json", {"pxd_dates": S, "stocks": [{"t": t} for t in sdk]})
            for t in sdk:
                wj("data/sd/%s.json" % t, {"pxd": [px[t][d] for d in S]})
            P = S[:-1] if lag_pit else S
            wj("data/pit_px.json", {"dates": P, "px": {t: {"i0": 0, "p": [px[t][d] for d in P]} for t in pitk},
                                    "quarantine": {}})
            wj("data/assets.json", {"dates": S, "px": {t: [px[t][d] for d in S] for t in mk}})
            wj("data/bench_px.json", {"dates": S, "series": {"spx": {"px": [px["^GSPC"][d] for d in S]}}})
            ms = sorted({d[:7] for d in S})
            wj("data/index_history.json", {"months": {m: {} for m in ms[:-1]}})
            wj("data/rf_monthly.json", {"monthly": {m: 0.003 for m in ms}})
            wj("data/_pit_px_cache.json", {})
            sh("add", "-A")
            sh("commit", "-q", "-m", "data %s" % last, when=when)
            sh("update-ref", "refs/remotes/origin/main", "HEAD")

        for rel in QC.QFWD_FILES:
            pth = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            io.open(pth, "w", encoding="utf-8", newline="").write("# %s\n" % rel)
        q = os.path.join(tmp, "data", "_qfwd")
        os.makedirs(q, exist_ok=True)
        blobs = {rel: sh("hash-object", rel).strip() for rel in QC.QFWD_FILES}
        par = {"v": 1, "ok": True, "adapter_blob": blobs[QC.ADAPTER_REL]}
        write_once(os.path.join(q, "parity.json"), par)
        prereg = "build/PREREG-e2e.md"
        with io.open(os.path.join(tmp, prereg), "w", encoding="utf-8", newline="") as fh:
            fh.write("# e2e 사전등록\n")
        write_once(os.path.join(q, "pins.json"), {"v": 1, "prereg": prereg, "prereg_blob": sh("hash-object", prereg).strip(),
                                                   "code_pin": CODE_PIN, "build_tree": BUILD_TREE,
                                                   "qfwd_files": blobs, "parity_sha": QC.file_sha(par),
                                                   "genesis": {n: QC.genesis(prereg, n) for n in QC.JSONL}})
        data_commit("2026-09-25", "2026-09-26T01:00:00Z")
        stub = _StubAdapter(sdk + pitk, fail={("2026-10", ("QF06",))})
        events = []
        d = datetime.date(2026, 9, 28)
        while d <= datetime.date(2026, 12, 3):
            ds = d.isoformat()
            if is_td(ds):
                c0 = close_utc(ds)
                if ds == "2026-10-30":
                    events.append((c0 + datetime.timedelta(minutes=40), "data", ds, True))
                events.append((c0 + datetime.timedelta(minutes=70), "data", ds, False))
            events.append((datetime.datetime(d.year, d.month, d.day, 23, 40, tzinfo=UTC), "run", None, False))
            events.append((datetime.datetime(d.year, d.month, d.day, 3, 40, tzinfo=UTC) + _DAY, "run", None, False))
            d += _DAY
        notes = {}
        foxtrot = {}
        gha0 = os.environ.get("GITHUB_ACTIONS")
        try:
            for t, kind, ds, lag in sorted(events):
                if kind == "data":
                    data_commit(ds, iso(t), lag_pit=lag)
                    continue
                if t >= pts("2026-10-01T00:00:00Z"):
                    os.environ["GITHUB_ACTIONS"] = "true"
                else:
                    os.environ.pop("GITHUB_ACTIONS", None)
                _NOW = t
                led = Ledger(repo=tmp, qdir=q, write=True, adapter=stub, out=lambda *_: None)
                led.auto()
                notes[iso(t)] = list(led.notes)
                led.close()
                if sh("status", "--porcelain", "--", "data/_qfwd").strip():
                    sh("add", "-A", "data/_qfwd")
                    sh("commit", "-q", "-m", "chore(qfwd)", when=iso(t + datetime.timedelta(minutes=3)))
                    sh("update-ref", "refs/remotes/origin/main", "HEAD")
                if iso(t) == "2026-10-01T03:40:00Z" and not foxtrot:
                    # 사람이 옛 판(B~1)에서 커밋하고 'git pull'(병합)로 봇 커밋 B 를 둘째 부모로 민다
                    foxtrot["B"] = sh("rev-parse", "HEAD").strip()
                    sh("checkout", "-q", "-b", "hum", "HEAD~1")
                    with io.open(os.path.join(tmp, "README.md"), "w", encoding="utf-8", newline="") as fh:
                        fh.write("사람 편집\n")
                    sh("add", "README.md")
                    sh("commit", "-q", "-m", "human edit", when="2026-10-01T05:00:00Z")
                    sh("merge", "-q", "--no-ff", "--no-edit", "main", when="2026-10-01T06:00:00Z")
                    foxtrot["M"] = sh("rev-parse", "HEAD").strip()
                    sh("checkout", "-q", "main")
                    sh("reset", "-q", "--hard", foxtrot["M"])
                    sh("branch", "-q", "-D", "hum")
                    sh("update-ref", "refs/remotes/origin/main", "HEAD")
        finally:
            if gha0 is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = gha0
        _NOW = None
        R = Records(q, QC.load_pins(tmp, q), write=False)
        dec = [r for r in R.recs["decisions.jsonl"] if r["kind"] == "decision"]
        att = [r for r in R.recs["decisions.jsonl"] if r["kind"] == "attempt"]
        got = sorted((r["card"], r["m"]) for r in dec)
        ok(got == sorted([("V0", "2026-09"), ("QF07", "2026-09"), ("QF08", "2026-09"), ("QF06", "2026-09"),
                          ("QF06", "2026-10"), ("QF06", "2026-11")]), "e2e 결정 6줄 — 첫 분기 넷 · QF06 10 · 11월")
        ok(not any(r["late"] for r in dec) and all(r["phase"] == ("pre" if r["m"] == FIRST_M else "fwd") for r in dec),
           "e2e 모두 제때 · phase")
        ok([a["outcome"] for a in att] == ["error"] and att[0]["m"] == "2026-10" and att[0].get("group") == "M",
           "e2e 자식 실패 한 번(QF06 무리) → attempt/error 한 줄 → 다음 크론 재시도")
        wit = [r for r in R.recs["decisions.jsonl"] if r["kind"] == "witness"]
        loc = sorted(r["seq"] for r in dec if r.get("runner") == "local")
        ok(len(loc) == 4 and len(wit) == 1 and wit[0]["of"] == loc and wit[0]["runner"] == "gha"
           and wit[0]["t_rec"] == "2026-10-01T03:40:00Z", "e2e witness — 사람 대체(local) 결정 넷을 첫 gha 실행이 한 줄로 봤다")
        fpm = sh("log", "--first-parent", "--format=%H", "origin/main").split()
        cmap = QC.commit_map(tmp, "data/_qfwd/decisions.jsonl", "origin/main", R.recs["decisions.jsonl"])
        ok(foxtrot.get("B") and foxtrot["B"] not in fpm and cmap.get(wit[0]["seq"], ("",))[0] == foxtrot["B"]
           and all(cmap.get(s_, ("", 0))[1] < pts("2026-10-01T05:00:00Z").timestamp() for s_ in loc),
           "e2e 병합(foxtrot) — 봇 커밋이 둘째 부모로 밀려도 줄의 커밋은 그대로(witness 줄 = 봇 커밋 B)")
        r10 = next(r for r in dec if r["card"] == "QF06" and r["m"] == "2026-10")
        ok(bool(r10["snap"]["rejects"]) and "grid" in r10["snap"]["rejects"][0]["why"]
           and r10["t_decided"] == "2026-10-31T03:40:00Z", "e2e 무효 판(격자 어긋남) 거절 기록 · 재시도 판으로 결정")
        ok(any("QF06 2026-10 결정 대기" in n for n in notes.get("2026-10-30T23:40:00Z", [])),
           "e2e 결정 실패 동안 ENTRY_DAY 포착 보류")
        ok(len(os.listdir(os.path.join(q, "eg"))) == 1 and len(os.listdir(os.path.join(q, "fits"))) == 1,
           "e2e Eg 파일 1 · 적합 파일 1")
        ok(stub.calls[0][2] == ["2026-09"] and all(c[2] == ["2026-09"] for c in stub.calls if c[1] != ("QF06",))
           and all(c[2] == [] for c in stub.calls if c[1] == ("QF06",)) and any(c[1] == ("QF06",) for c in stub.calls)
           and all(c[1] in (("V0", "QF07", "QF08"), ("QF06",)) for c in stub.calls),
           "e2e 무리 따로 — 분기 자식에 전방 Eg 2026-09 · QF06 자식은 따로 · Eg 없음")
        caps = R.recs["px_capture.jsonl"]
        want = tds(ENTRY_DAY, "2026-12-03")
        ok([c["d"] for c in caps] == want, "e2e 포착 %d일 연속(ENTRY_DAY ~ 12-03)" % len(want))
        bm = list(R.recs["books.jsonl"])
        ok(sorted(r["book"] for r in bm) == sorted(BOOKS) and all(r["h"] == FWD_M1 for r in bm),
           "e2e 첫 실현 — 12장부 · 2026-11")
        ok(any("실현 2026-11 보류" in n for n in notes.get("2026-11-30T23:40:00Z", []))
           and any(r.get("kind") == "month" for r in R.recs["market.jsonl"]), "e2e 미커밋 결정의 체결일 보류 → 다음 크론에 실현")
        bb = {r["book"]: r for r in bm}
        ok(bb["V0.D0"]["reb"][0]["d"] == ENTRY_DAY and bb["V0.T1"]["reb"][0]["d"] == "2026-11-02"
           and bb["V0.D0"]["days"][0] == ENTRY_DAY and bb["V0.D0"]["g0"][0] == 1.0, "e2e 진입 — D0 ENTRY_DAY · T1 11-02")
        ok([e["d"] for e in bb["XBM.D0"]["reb"]] == [ENTRY_DAY, "2026-11-30"]
           and [e["d"] for e in bb["XBM.T1"]["reb"]] == ["2026-11-02"], "e2e XBM — D0 진입 + 11월 말 · T1 은 12월로")
        ok(all(abs(sum(r["w_end"].values()) + r["cash_end"] - 1) < 1e-12 for r in bm), "e2e 끝 몫 합 = 1")
        ok(all(r["missing"].get("DDD", 3) == 3 for r in bm if r["missing"]), "e2e 구멍 사흘 — 든 장부는 들고 간 날 3")
        okc, summ = QC.run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=True)
        ok(okc and summ["reselect"] >= 1 and summ["late"] == 0 and summ["checked"] == len(dec),
           "e2e qfwd_check --full 통과(판 재선택 %d · 대조 %d)" % (summ["reselect"], summ["checked"]))
        if not okc:
            for v in summ["viol"][:5]:
                print("      " + v)
        import qfwd_judge as J
        fw = J.Fwd.load(tmp)
        F = J.ForwardFrame(fw)
        ok(fw.hold == [FWD_M1] and all(J.FBook(b, fw, F).g0.shape[0] == F.T for b in BOOKS),
           "e2e 판정기 입력 — 틀 · 12장부 모양")
        _NOW = pts("2026-12-04T05:00:00Z")
        led = Ledger(repo=tmp, qdir=q, write=False, adapter=stub, out=lambda *_: None)
        lines = []
        led.say = lines.append
        status(led)
        led.close()
        ok(len(lines) > 5 and any("포착 마지막 2026-12-03" in ln for ln in lines), "e2e --status 돈다(개수만)")
    finally:
        _NOW = old_now
        QC.rmtree(tmp)


def _selftest_degraded(ok):
    """막힘 대체 — sd 하나가 끝내 격자와 어긋나면(재실행으로 안 낫는 구멍) K_DEGRADE 거래일 뒤 그 판으로 결정(빠질 이름 기록) ·
    포착도 SPY · ^GSPC 만 요구하는 대체 검증으로 · 재선택이 같은 판을 다시 고른다. 합성 저장소 · 합성 어댑터."""
    import random
    global _NOW
    tmp = tempfile.mkdtemp(prefix="qfwd_deg_")
    old_now = _NOW
    try:
        def sh(*args, when=None):
            env = dict(os.environ)
            if when:
                env.update(GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
            r = subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True, encoding="utf-8", env=env)
            if r.returncode:
                raise RuntimeError(r.stderr[:300])
            return r.stdout

        sh("init", "-q", "-b", "main")
        sh("config", "user.name", "qfwd-deg")
        sh("config", "user.email", "qfwd@deg.invalid")
        sh("config", "core.autocrlf", "false")
        rnd = random.Random(5)
        pre, x = [], datetime.date(2025, 8, 1)
        while x < datetime.date(2026, 1, 1):
            if x.weekday() < 5 and x.isoformat() not in ("2025-09-01", "2025-11-27", "2025-12-25"):
                pre.append(x.isoformat())
            x += _DAY
        allD = pre + tds("2026-01-02", "2026-12-31")
        sdk, mk = ["AAA", "BBB", "FFF"], ["SPY"] + list(SPDR9)
        px = {}
        for k in sdk + mk + ["^GSPC"]:
            p, row = 50.0 + rnd.random() * 50, {}
            for d in allD:
                p *= math.exp(rnd.gauss(0.0003, 0.015))
                row[d] = round(p, 4)
            px[k] = row

        def wj(rel, obj):
            pth = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            with io.open(pth, "w", encoding="utf-8", newline="") as fh:
                fh.write(json.dumps(obj, separators=(",", ":")))

        def data_commit(last, when, off=None):
            S = [d for d in allD if d <= last]
            wj("data/stocks.json", {"pxd_dates": S, "stocks": [{"t": t} for t in sdk]})
            for t in sdk:
                a = [px[t][d] for d in S]
                wj("data/sd/%s.json" % t, {"pxd": a[:-1] if t == off else a})
            wj("data/pit_px.json", {"dates": S, "px": {}, "quarantine": {}})
            wj("data/assets.json", {"dates": S, "px": {t: [px[t][d] for d in S] for t in mk}})
            wj("data/bench_px.json", {"dates": S, "series": {"spx": {"px": [px["^GSPC"][d] for d in S]}}})
            ms = sorted({d[:7] for d in S})
            wj("data/index_history.json", {"months": {m: {} for m in ms[:-1]}})
            wj("data/rf_monthly.json", {"monthly": {m: 0.003 for m in ms}})
            wj("data/_pit_px_cache.json", {})
            sh("add", "-A")
            sh("commit", "-q", "-m", "data %s" % last, when=when)
            sh("update-ref", "refs/remotes/origin/main", "HEAD")
            return sh("rev-parse", "HEAD").strip()

        for rel in QC.QFWD_FILES:
            pth = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            io.open(pth, "w", encoding="utf-8", newline="").write("# %s\n" % rel)
        prereg = "build/PREREG-deg.md"
        io.open(os.path.join(tmp, prereg), "w", encoding="utf-8", newline="").write("# 막힘 대체 시험\n")
        q = os.path.join(tmp, "data", "_qfwd")
        os.makedirs(q, exist_ok=True)
        blobs = {rel: sh("hash-object", rel).strip() for rel in QC.QFWD_FILES}
        par = {"v": 1, "ok": True, "adapter_blob": blobs[QC.ADAPTER_REL]}
        write_once(os.path.join(q, "parity.json"), par)
        write_once(os.path.join(q, "pins.json"), {"v": 1, "prereg": prereg, "prereg_blob": sh("hash-object", prereg).strip(),
                                                   "code_pin": CODE_PIN, "build_tree": BUILD_TREE, "qfwd_files": blobs,
                                                   "parity_sha": QC.file_sha(par),
                                                   "genesis": {n: QC.genesis(prereg, n) for n in QC.JSONL}})
        data_commit("2026-09-25", "2026-09-26T01:00:00Z")
        firsts = {}
        for ds in tds("2026-09-30", "2026-10-09"):
            c = data_commit(ds, iso(close_utc(ds) + datetime.timedelta(minutes=70)), off="FFF")
            firsts.setdefault(ds, c)
        stub = _StubAdapter(sdk + ["X1", "X2", "X3"])
        _NOW = pts("2026-10-02T00:00:00Z")
        L = Ledger(repo=tmp, qdir=q, write=False, adapter=stub, out=lambda *_: None)
        s1 = L.select_decision("2026-09")
        L.close()
        ok(s1["commit"] is None and s1["reject_kinds"].get("grid"), "막힘 대체 전 — sd 가 어긋난 판은 모두 거절(갈래 grid)")
        _NOW = close_utc(td_add("2026-09-30", K_DEGRADE)) + datetime.timedelta(minutes=1)
        L = Ledger(repo=tmp, qdir=q, write=True, adapter=stub, out=lambda *_: None)
        s2 = L.select_decision("2026-09")
        s3 = L.select_capture("2026-10-01")
        ok(s2["commit"] == firsts["2026-09-30"] and (s2["degraded"] or {}).get("sd_drop") == ["FFF"],
           "막힘 대체 — d_m 뒤 %d거래일이 지나면 첫 판으로 · 빠질 이름(FFF) 기록" % K_DEGRADE)
        ok(s3["commit"] is None, "막힘 대체 포착 — 그날 뒤 %d거래일 전에는 열리지 않는다" % K_DEGRADE)
        L.decide_month("2026-09")
        dec = [r for r in L.R.recs["decisions.jsonl"] if r.get("kind") == "decision"]
        ok(len(dec) == 4 and all((r["snap"].get("degraded") or {}).get("sd_drop") == ["FFF"] for r in dec),
           "막힘 대체 결정 넷 — 판 기록에 degraded(sd_drop) 가 남는다")
        L.close()
        _NOW = close_utc(td_add("2026-10-01", K_DEGRADE)) + datetime.timedelta(minutes=1)
        L = Ledger(repo=tmp, qdir=q, write=False, adapter=stub, out=lambda *_: None)
        s4 = L.select_capture("2026-10-01")
        row, _b = capture_row("2026-10-01", s4["snap"], {"AAA", "FFF"}, set(), {"AAA": "2026-09-30", "FFF": "2026-09-30"})
        L.close()
        ok(s4["commit"] == firsts["2026-10-01"] and (s4["degraded"] or {}).get("grid") and row["r"]["FFF"] is None
           and row["r"]["AAA"] is not None, "막힘 대체 포착 — 어긋난 sd 이름은 null(마지막 가격으로 든다) · 나머지는 잰다")
        sh("add", "-A", "data/_qfwd")
        sh("commit", "-q", "-m", "chore(qfwd)", when=iso(_NOW))
        sh("update-ref", "refs/remotes/origin/main", "HEAD")
        _NOW = None
        okc, summ = QC.run_checks(tmp, full=True, out=lambda *_: None, code_pin_check=False, reselect=True)
        ok(okc and summ["reselect"] >= 1, "막힘 대체 — qfwd_check --full 재선택이 같은 대체 판을 다시 고른다(%s)" % (summ["viol"][:1] or "위반 0"))
    finally:
        _NOW = old_now
        QC.rmtree(tmp)


def selftest(with_git=False, e2e=False):
    fails = []

    def ok(cond, what):
        print(("  ✓ " if cond else "  ✗ ") + what)
        if not cond:
            fails.append(what)
    import qfwd_adapter as A
    ok(set(DEC_PATHS) == set(A.CUT_FILES) | {"data/sd"} and set(SNAP_PATHS) <= set(DEC_PATHS),
       "결정 판 입력 파일 = 어댑터 ⑥ 이 바꾸는 파일(CUT_FILES + sd) · 포착 검증은 그 부분집합")
    wf = io.open(os.path.join(REPO, ".github", "workflows", "qfwd-ledger.yml"), encoding="utf-8").read()
    ok(all("'%d %d * * *'" % (mm, hh) in wf for hh, mm in CRON_UTC) and wf.count("- cron:") == len(CRON_UTC)
       and "workflow_run" in wf,
       "되풀이 흉내(CRON_UTC) = 워크플로 cron %d · 사건 실행(workflow_run) 있음" % len(CRON_UTC))
    ok(A.TIMEOUT["archive"] + A.TIMEOUT["bake_eg"] + A.TIMEOUT["decide"] + 120 <= BUDGET_SEC
       and "timeout-minutes: %d" % 90 in wf and BUDGET_SEC <= 90 * 60 - 1200,
       "자식 시간 제한 합 ≤ 실행 예산(%d초) ≤ 잡 시간(90분) − 20분" % BUDGET_SEC)
    _selftest_calendar(ok)
    _selftest_exec(ok)
    _selftest_records(ok)
    _selftest_capture(ok)
    _selftest_engine(ok)
    if with_git:
        _selftest_git(ok)
    if e2e:
        _selftest_e2e(ok)
        _selftest_degraded(ok)
    print("qfwd_ledger selftest: %s (%d 실패)" % ("통과" if not fails else "실패", len(fails)))
    return 0 if not fails else 1


# ── 실행 ────────────────────────────────────────────────────────────────────
def _arg(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv=None):
    global _NOW
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest(with_git="--git" in argv, e2e="--e2e" in argv)
    if "--now" in argv:
        _NOW = pts(_arg(argv, "--now"))
    qdir = _arg(argv, "--qdir")
    qdir = os.path.abspath(qdir) if qdir else None
    if _NOW is not None and (qdir is None or os.path.abspath(qdir) == os.path.abspath(QDIR)):
        if "--auto" in argv:
            print("🚨 --now 는 시험 전용이다 — data/_qfwd 에 쓰지 않는다(--qdir 스크래치를 줄 것)")
            return 1
    if "--fetch" in argv:
        QC.git(REPO, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main", check=False)
    keep = "--keep" in argv
    if "--calendar-add" in argv:
        i = argv.index("--calendar-add")
        kind = argv[i + 1] if len(argv) > i + 1 else ""
        try:
            if kind == "utc_offset":
                row = {"kind": kind, "d0": argv[i + 2], "d1": argv[i + 3], "off": int(argv[i + 4]), "why": argv[i + 5]}
            else:
                row = {"kind": kind, "d": argv[i + 2], "why": argv[i + 3]}
        except (IndexError, ValueError):
            print("사용: --calendar-add closed|early DATE 사유 [--src URL] · --calendar-add utc_offset D0 D1 4|5 사유 [--src URL]")
            return 2
        if _arg(argv, "--src"):
            row["src"] = _arg(argv, "--src")
        return calendar_add(row, qdir)
    if "--rehearse" in argv and qdir:
        ms = [x.strip() for x in _arg(argv, "--rehearse").split(",") if x.strip()]
        return rehearse_records(ms, qdir, keep=keep, delay_min=int(_arg(argv, "--cron-delay", CRON_DELAY_MIN)),
                                events="--no-events" not in argv, withhold=int(_arg(argv, "--withhold-fits", 0)),
                                tips="today" if "--tips-today" in argv else "reconstructed")
    if "--auto" in argv:
        q = os.path.abspath(qdir or QDIR)
        inside = not os.path.relpath(q, REPO).startswith("..")
        if q == os.path.abspath(QDIR):
            # [DECL] 원장 폴더에 쓰는 실행은 --qdir 로 같은 곳을 가리켜도 전제를 모두 본다(검토 2026-09-25)
            okp, why = preconditions(REPO, q, print)
            if okp is None:
                print("QFWD 원장: %s" % why)
                return 0
            if not okp:
                print("🚨 QFWD 원장 전제 실패 — %s" % why)
                return 1
        elif inside:
            print("🚨 --qdir 는 data/_qfwd 이거나 저장소 밖 스크래치여야 한다(%s)" % q)
            return 1
        try:
            L = Ledger(repo=REPO, qdir=q, write=True, keep=keep)
        except IntegrityError as e:
            print("🚨 QFWD 원장 사슬 — %s" % e)
            return 1
        try:
            L.auto()
        except (IntegrityError, CalendarError) as e:
            print("🚨 QFWD 원장 멈춤 — %s" % e)
            return 1
        finally:
            L.close()
        add = L.R.added
        print("QFWD 원장 %s — 끝 %s · 더한 줄: 결정 %d · 포착 %d · 시장 %d · 장부 %d · 달력 %d · 남은 예산 %d초"
              % (iso(L.now), L.tip[:12], add["decisions.jsonl"], add["px_capture.jsonl"], add["market.jsonl"], add["books.jsonl"],
                 add["calendar.jsonl"], L.budget_left()))
        for n in L.notes:
            print("  · " + n)
        for a_ in L.alarms:
            print(a_)
        return 1 if L.alarms else 0     # 경보(달력 어긋남)는 잡을 붉게 — 이미 봉인한 줄은 뒤 단계가 올린다
    try:
        L = Ledger(repo=REPO, qdir=qdir, write=False, keep=keep)
    except IntegrityError as e:
        print("🚨 QFWD 원장 사슬 — %s" % e)
        return 1
    try:
        if "--status" in argv:
            status(L)
            return 0
        if "--dry" in argv:
            dry(L)
            return 0
        if "--rehearse" in argv:
            return rehearse(L, _arg(argv, "--rehearse"), _arg(argv, "--out"))
        if "--recheck" in argv:
            return recheck(L)
    except CalendarError as e:
        print("🚨 %s" % e)
        return 1
    finally:
        L.close()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
