#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§A 내부자 PIT 백필 — SEC DERA Insider Transactions Data Sets 2011Q1..2026Q2 → 세계 발행사 그룹의 P/S 행 패널

무엇을·왜.
  RBATCH R1(기회주의 내부자 매도)의 표지·분류는 모두 «그 행이 언제 시장에 알려졌나» 와 «어느 발행사 그룹의 거래인가» 에
  걸린다. 이 파일은 그 두 가지를 못 박은 **행 패널** 하나를 만든다. 분류(루틴·기회주의)와 OS/RS 더미는 여기서 만들지
  않는다 — build/r_r1_flags.py 가 이 패널을 읽어 한 곳에서 만든다(같은 표지를 두 곳에서 만들면 갈린다).
  xcheck 명령이 그 파일을 이 패널에 돌려 정리 결과가 같은지와 월 OS·RS 종목 수(개수만)를 싣는다.

원천(판 고정).
  DERA 인덱스 페이지의 href 를 읽어 분기 ZIP 경로를 얻는다(최신 분기와 과거 분기의 경로가 다르다).
  ZIP 은 저장소 밖 RAW/ins 에 두고 data/_ins_pit/manifest.json(issuer_map.py 와 공유)의 sha256 과 맞춘다.
  RAW/dera 에 issuer_map.py 가 받아 둔 같은 ZIP 이 있으면 해시를 맞춘 뒤 하드링크한다(다시 받지 않는다).
  다시 받은 ZIP 의 해시가 manifest 와 다르면 멈춘다(과거 분기 2022 재추출 · 2025-07 AFF10B5ONE 소급 추가 전례).

쓰는 표 — SUBMISSION · REPORTINGOWNER · NONDERIV_TRANS · FOOTNOTES.
  세계 = data/_issuer_map.json 의 발행사 그룹(786개 · CIK 815개 · 선행 CIK 포함) 가운데 ISSUERCIK 가 든 제출.
  행 = NONDERIV_TRANS 의 TRANS_CODE ∈ {P, S}. 원 행 캐시(RAW/ins_cache · 각주 본문 포함)는 Form 4 · 4/A · 5 · 5/A 를 다 싣고,
  저장소 패널은 Form 4 · 4/A 만 싣는다(사양: 분류·표지에 Form 5 를 쓰지 않는다 — 연도별 개수만 센다).

행 단위 규칙(사양 §A · R1 params 그대로 — 여기서 문턱을 바꾸지 않는다).
  1 각주   행의 *_FN 열(12개 · 헤더 순서) 각주 ID → FOOTNOTES 본문을 이어 붙인다. 제출 단위로 잇지 않는다.
  2 강제 매도 STC_RX 를 **행에 연결된 각주에만** 건다(REMARKS 에는 걸지 않는다). 식은 build/r_r1_flags.py 에 한 벌(여기와
            ins_daily.py 는 import 한다). 2026-09-25 등록 전 수정: 'non-discretionary' 갈래는 원천징수·세금 맥락이 있어야 한다
            (r_r1_flags 선언 p). 옛 식의 판정은 감사 칸 stc_v1 로 싣는다. 두 판정은 원 행 캐시의 각주 본문에서 읽을 때마다 다시 건다
            (캐시 안의 stc 칸은 파싱 때 값이라 쓰지 않는다).
  3 10b5-1  PLAN_RX(명시적 부정문 NEG_RX 수보다 적중이 많을 때) 를 행 각주 + 제출 REMARKS 에 건다(p10 = 쌍둥이 T1·T2 용).
            각주만(p10f) · REMARKS 만(p10r) 도 따로 싣는다. 체크박스 AFF10B5ONE 은 aff 로 싣고, 2023-04-01 부터의 OR 는 쓰는 쪽이 한다.
  4 가용일  FILING_DATE **다음** NYSE 거래일(DERA 에는 접수 시각이 없다). 휴장 규칙 = refresh_events._holidays + ADHOC.
  5 버림    코드와 A/D 가 어긋난 행(P 는 A · S 는 D) · 날짜 없음 · TRANS_DATE > FILING_DATE · 보고자 없음 — 연도별로 센다.
  6 정정 중복 제출일 → 원본(4) 먼저 → 접수번호 → SK(수치) 순으로 훑어 (그룹, 보고자, 거래일, 코드, 수량, 단가) 가 앞선 **다른**
            제출에서 이미 나온 보고자는 지운다. 모든 보고자가 지워지면 행을 버리고, 일부만 새로우면 cnt = 0 으로 남긴다(표지에서는
            세지 않고 새 보고자의 분류 이력에만 붙인다 — 보고자 10인 상한으로 쪼갠 공동 제출 · 보고자를 더한 정정본). 같은 제출 안
            같은 값 두 행(직접·간접 로트)은 지우지 않는다.
  6b 4/A 정정 (r_r1_flags 선언 q — 2026-09-25 등록 전 수정 · 2026-09-26 개정) 4/A 행의 보고자가 여섯 칸 키로는 새로운데
            (그룹, 보고자, 거래일, 코드) 가 앞선 다른 제출의 행에서 이미 나왔으면 정정이다: 4/A 행은 cnt = 0 · corr = 2(그 보고자는 ocor —
            이력에 붙이지 않는다) · 짝지은 원 행은 corr = 1 · 🔒 sh · px · usd 는 제출된 그대로(등록 1차) · 고친 값은 shc · pxc · usdc
            (선언된 민감도 T1C 만) · av(가용일)는 원래대로. 짝은 ctgt 에 적는다.
  6c 거래일 정정 (선언 q2 — 2026-09-26 등록 전 수정) 4/A 행이 고치는 제출(DATE_OF_ORIG_SUB = orig)의 살아 있는 행과
            (그룹, 보고자 겹침, 코드, 수량, 단가 — 제출된 그대로 또는 앞 4/A 가 고친 값)가 같고 거래일만 다르면 cnt = 0 · corr = 3 ·
            겹친 보고자는 ocor · 원 행은 사건 ·
            가용일 · 라벨 그대로 · tdh = [고친 거래일, 4/A acc, sk](분류 이력만 고친 거래일을 쓴다).
            옛 규칙(4/A 가 자기 공시월의 새 사건)은 cnt6 · ocor 로 재현한다. 6 · 6b · 6c 모두 r_r1_flags.prepare 와 한 규칙이다
            (xcheck 가 행 · 칸마다 대조한다).
  7 공동 제출 행은 제출당 한 번(own 에 보고자 목록). 보고자 관계는 비트(1 이사 · 2 임원 · 4 10% 보유 · 8 기타).
  8 CIK 효력 구간 밖(그룹의 선행 CIK 가 효력 끝 뒤에 낸 제출 등) 행은 oiv = 1 로 표시만 하고 남긴다(개수를 센다).

세계(멤버-월). Section 16 적용 = 지도의 **등록 FPI 표지**(_issuer_map.json fpi_registered — 2026-09-25 권고 fpi_q: 직전 정기보고가
  10-Q 면 FPI 아님)가 1 이 아닌 멤버-월. 사양 칸(fpi)으로 센 세계는 *_spec 으로 옆에 싣는다. Stage M = 2016-08..2026-07 · 그달 비금융
  (issuer_map.sector_at — 위키 PIT → 수작업 표 → 비PIT 대체) · Section 16 적용 · 지도 F0 통과.

출력.
  data/_ins_pit/ps/ps_YYYY.json.gz   제출 연도별 정리된 P/S 행(Form 4 · 4/A) — cols 는 파일 머리. gzip mtime = 0(다시 빌드해도 같은 바이트).
  data/_ins_pit/density.json         연도별 개수 · 버림 · 지연 · 강제 매도(새 식 · 옛 식)·10b5-1 표지율 · 표류 · 공동 제출 · 4/A 정정 ·
                                     월별 S 행 발행사 수(세계 전체 · 그달 멤버 · Stage M 세계) · 매수 쪽 밀도 · 입력 해시.
  data/_ins_pit/cache_manifest.json  저장소 밖 원 행 캐시(RAW/ins_cache/<분기>.jsonl.gz)의 sha256.
  data/_ins_pit/xcheck_r1.json       (xcheck) r_r1_flags.py 대조 · 월 OS·RS 종목 수(개수만) · 분류 수 조정(reconcile).
  data/_ins_pit/cikmonth.json        (flags) 그룹 × 가용월 집계 = r_r1_flags.cikmonth_doc(희소) — r_stagem · r_p0_adapt 의 입력.
  data/_ins_pit/routine.json         (flags) 보고자 × 그룹 연도별 R/O/U/N = r_r1_flags.routine_doc.
  🚨 자료 빌드다 — 어떤 표지와 수익의 관계도 계산하지 않는다(P0 · Stage M 은 등록 뒤).

SEC 접속 — 모든 요청이 build/edgar.py 를 거친다(초당 8회 · gzip · 백오프). 🚨 SEC_UA 환경변수가 없으면 실행을 거부한다
  (issuer_map.py 를 import 하면 그쪽 검사도 같이 걸린다). UA 값은 어느 파일에도 적지 않는다.

사용:
    SEC_UA="이름 연락처" python build/ins_pit_build.py check     # index.json 1건 + submissions 1건 · HTTP 200 · gzip
    SEC_UA=...            python build/ins_pit_build.py fetch     # 인덱스 href → RAW/ins ZIP · 해시 대조 (--remote: HEAD 로 Last-Modified 대조)
    SEC_UA=...            python build/ins_pit_build.py build     # ZIP → 원 행 캐시 → 정리 → 패널 · density.json
    SEC_UA=...            python build/ins_pit_build.py xcheck    # r_r1_flags.py 대조 · 월 OS·RS 종목 수 · 분류 수 조정
    SEC_UA=...            python build/ins_pit_build.py flags     # cikmonth.json · routine.json(r_r1_flags 로 · 개수만)
    SEC_UA=...            python build/ins_pit_build.py all       # check · fetch · build · xcheck · flags
  (build · xcheck · flags 는 요청을 보내지 않는다 — 저장소 밖 캐시와 고정 ZIP 만 읽는다. SEC_UA 검사는 import 때 걸린다.)
"""
from __future__ import annotations

import bisect
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 🚨 SEC_UA 가 없으면 거부한다(edgar.py 는 없을 때 기본값으로 조용히 넘어가므로 import 전에 막는다).
if not (os.environ.get("SEC_UA") or "").strip():
    sys.exit("🚨 SEC_UA 환경변수가 없다 — SEC 요청의 User-Agent(이름 + 연락처)를 명시적으로 정해서 넘길 것. "
             "edgar.py 의 기본값은 쓰지 않는다.")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402
import issuer_map as IM  # noqa: E402  Manifest · dera_links · ins_manifest · _head · load_refs · member_months · sector_at
import refresh_events as REV  # noqa: E402  NYSE 휴장 규칙(_holidays · ADHOC) — 규칙은 한 곳에만
import r_r1_flags as R1  # noqa: E402  표지 식(강제 매도 · 10b5-1) · 정정 순서 · 분류 — 한 벌(여기서 다시 쓰지 않는다)

if edgar.UA != os.environ["SEC_UA"]:
    sys.exit("🚨 edgar.UA 가 SEC_UA 와 다르다 — edgar.py 가 환경변수를 읽지 않았다")

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUTD = os.path.join(DATA, "_ins_pit")
PANEL = os.path.join(OUTD, "ps")
DENS = os.path.join(OUTD, "density.json")
CMAN = os.path.join(OUTD, "cache_manifest.json")
XCHK = os.path.join(OUTD, "xcheck_r1.json")
IMAP = os.path.join(DATA, "_issuer_map.json")
RAW = IM.RAW
RAW_INS = os.path.join(RAW, "ins")
RAW_OLD = os.path.join(RAW, "dera")                 # issuer_map.py 가 받아 둔 같은 ZIP
CACHE = os.path.join(RAW, "ins_cache")

PARSE_VER = 2                                        # 원 행 캐시 형식 — 바꾸면 캐시를 다시 만든다(2: 글 칸의 CSV 따옴표 풀기)
FORMS = ("4", "4/A", "5", "5/A")                     # 원 행 캐시에 싣는 서식
FORMS4 = ("4", "4/A")                                # 패널(분류·표지)에 쓰는 서식
CODES = {"P": "A", "S": "D"}                         # 코드 → 맞는 A/D
DATA_START, DATA_END = "2011-01-01", "2026-06-30"    # DERA 2011Q1..2026Q2 의 FILING_DATE 범위
AFF_FROM = "2023-04-01"                              # 체크박스 의무(Form 4 개정 시행일)
STAGE_M = ("2016-08", "2026-07")                     # issuer_map coverage 의 Stage M 창
FIN = {"Financials"}
ROLE = (("Director", 1), ("Officer", 2), ("TenPercentOwner", 4), ("Other", 8))
INSIDER_BITS = 1 | 2 | 4                             # CMP 내부자(이사 · 임원 · 10% 보유)

# 강제 매도 · 10b5-1 — 🚨 식은 build/r_r1_flags.py 에 한 벌(여기서 다시 쓰지 않는다 · ins_daily.py 도 이 이름을 쓴다).
#   STC_RX 등록 식(선언 p · 'non-discretionary' 갈래는 원천징수·세금 맥락 필요) · STC_RX_V1 수정 전 식(감사 칸 stc_v1 전용).
STC_RX, STC_RX_V1, PLAN_RX, NEG_RX = R1.STC_RX, R1.STC_RX_V1, R1.PLAN_RX, R1.NEG_RX

PANEL_COLS = ["g", "cik", "acc", "sk", "doc", "fd", "av", "td", "c", "sh", "px", "usd", "own", "stc", "p10", "p10f", "p10r",
              "aff", "cnt", "oiv", "odup", "stc_v1", "corr", "ctgt", "shc", "pxc", "usdc", "ocor", "cnt6", "orig", "tdh"]
PANEL_NOTE = ("§A 정리된 P/S 행(Form 4 · 4/A) — build/ins_pit_build.py 머리말의 행 단위 규칙. 한 행 = NONDERIV_TRANS 한 행(제출당 한 번). "
              "g 발행사 그룹 · cik 발행사 CIK · acc 접수번호 · sk NONDERIV_TRANS_SK · doc 서식 · fd FILING_DATE · "
              "av 가용일(fd 다음 NYSE 거래일) · td TRANS_DATE · c 코드(P · S) · sh 수량 · px 단가(없으면 null) · usd sh×px(px ≤ 0 이면 null) · "
              "own [[보고자 CIK, 관계 비트]] (1 이사 · 2 임원 · 4 10% 보유 · 8 기타) · stc 강제 매도(행 각주 · 등록 식 r_r1_flags.STC_RX) · "
              "p10 10b5-1 정규식(행 각주 + REMARKS) · p10f 각주만 · p10r REMARKS 만 · aff 체크박스(1 · 0 · null) · "
              "cnt 1 = 표지에 센다 · 0 = 앞선 다른 제출이 이미 알린 거래(own 은 새 보고자만 — 분류 이력에만) · "
              "oiv 1 = 제출일이 그 CIK 의 효력 구간 밖 · odup = cnt 0 행에서 지운 보고자 [[CIK, 비트]] · "
              "stc_v1 = 수정 전 강제 매도 식(맨 'non-discretionary')의 판정(감사 전용) · "
              "🔒 sh · px · usd = 제출된 그대로(등록 1차 · 4/A 가 고쳐도 바꾸지 않는다 — r_r1_flags 선언 q 2026-09-26) · "
              "corr 0 = 보통 · 1 = 뒤 4/A 가 수량·단가를 고친 원 행(고친 값은 shc · pxc · usdc — 선언된 민감도 T1C 만 쓴다 · av 는 원래대로) · "
              "2 = 앞선 제출의 거래를 고친 4/A 행(사건 아님 · cnt 0 · 정정 보고자는 ocor [[CIK, 비트]] · 이력에 붙이지 않는다) · "
              "3 = 고치는 제출(orig = DATE_OF_ORIG_SUB)의 행을 거래일만 바꿔 다시 적은 4/A 행(선언 q2 · 사건 아님 · cnt 0 · 겹친 보고자는 ocor) · "
              "ctgt = 짝 [접수번호, sk](corr 1 → 고친 4/A 행 · corr 2 · 3 → 고쳐진 원 행 · null = 짝 없음) · "
              "tdh = 거래일이 고쳐진 원 행의 [고친 거래일, 4/A 접수번호, sk](분류 이력에만 쓴다 · 사건 · 라벨은 td 그대로) · "
              "orig = 4/A 의 DATE_OF_ORIG_SUB(4 는 null) · "
              "cnt6 = 옛 규칙(여섯 칸 키만 · 4/A 도 새 사건)의 cnt — 옛 규칙 = cnt6 · corr 2 · 3 행은 own + ocor. "
              "own + odup + ocor 가 원 보고자 — load_panel 이 되붙여 r_r1_flags.prepare 가 같은 cnt · corr · tdh 를 다시 만든다"
              "(짝은 ctgt 를 쓴다). 정렬 = 정정 중복 판정 순서(fd, 원본 먼저, acc, sk 수치).")
HEAVY = ("fn_text", "remarks", "owner_info", "title", "fn_ids", "deemed", "tft", "swap", "post", "di", "period", "ns16",
         "aff_raw", "sym")                           # 정리에 쓰지 않는 원 행 칸(lean 읽기에서 뺀다 — 메모리 · orig 는 선언 q2 가 쓴다)


# ════════════════════════════════════════════════════════════════════════
# 공용
# ════════════════════════════════════════════════════════════════════════
_now, _sha, _sha_file, _rj, _wj = IM._now, IM._sha, IM._sha_file, IM._rj, IM._wj
_ddate, _madd = IM._ddate, IM._madd


def _num(s):
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _cik(s):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


def _aff(s):
    s = (s or "").strip().lower()
    if s in ("1", "true", "y", "yes"):
        return 1
    if s in ("0", "false", "n", "no"):
        return 0
    return None


def _unq(s):
    """DERA TSV 는 따옴표가 든 글 칸을 CSV 식으로 감싼다(«"… (the ""Issuer"") …"» · 실측 P/S 행 각주 52,415건).
    구분자·줄바꿈은 칸 안에 없어서(62분기 전수 · 열 수 어긋난 줄 0) QUOTE_NONE 으로 읽고 칸마다 여기서 푼다.
    ⚠ 표지(강제 매도 · 10b5-1)는 풀기 전후가 한 행도 다르지 않았다(실측 475,958행) — 본문 충실도만의 문제다."""
    s = s or ""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        inner = s[1:-1]
        if '"' not in inner.replace('""', ""):
            return inner.replace('""', '"')
    return s


def _bits(rel: str) -> int:
    rel = rel or ""
    return sum(b for k, b in ROLE if k in rel)


def rel_of(bits: int) -> str:
    """비트 → DERA 식 관계 문자열(r_r1_flags 의 부분 문자열 판정이 그대로 먹는다)."""
    return ",".join(k for k, b in ROLE if bits & b)


# 표지 판정도 r_r1_flags 의 것 그대로(ins_daily.py 가 P.is_stc · P.is_stc_v1 · P.plan_hit 로 부른다)
is_stc, is_stc_v1, plan_hit = R1.is_stc, R1.is_stc_v1, R1.plan_hit


def flag_text(rec):
    """원 행 하나의 각주 본문으로 강제 매도 두 판정을 다시 건다(캐시 안의 stc 는 파싱 때 식의 값 — 쓰지 않는다)."""
    t = rec.get("fn_text") or ""
    rec["stc"] = 1 if is_stc(t) else 0
    rec["stc_v1"] = 1 if is_stc_v1(t) else 0
    return rec


def _int_or(x):
    """JSON 을 줄인다 — 정수값 float 는 int 로."""
    if x is None:
        return None
    return int(x) if float(x).is_integer() and abs(x) < 1e15 else x


def _k6(x):
    return None if x is None else round(float(x), 6)


def write_gz_json(path, obj):
    """결정적 gzip(mtime 0 · 파일 이름 없음) — 같은 내용이면 같은 바이트."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tmp = path + ".tmp"
    with open(tmp, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as f:
            f.write(s)
    os.replace(tmp, path)


def read_gz_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[i]


def _med(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def quarters():
    return list(IM._quarters())


# ════════════════════════════════════════════════════════════════════════
# NYSE 거래일(규칙 = refresh_events · 관측 격자 stocks.json pxd_dates 와 대조만 한다)
# ════════════════════════════════════════════════════════════════════════
class Cal:
    def __init__(self, y0=2008, y1=2032):
        days = []
        d, end = dt.date(y0, 1, 1), dt.date(y1, 12, 31)
        hol = {}
        while d <= end:
            if d.year not in hol:
                hol[d.year] = set(REV._holidays(d.year)) | {k for k in REV.ADHOC if k.startswith(str(d.year))}
            s = d.isoformat()
            if d.weekday() < 5 and s not in hol[d.year]:
                days.append(s)
            d += dt.timedelta(days=1)
        self.days = days
        self._first = {}

    def next_td(self, s: str) -> str:
        """s 보다 **뒤의** 첫 거래일(s 가 거래일이어도 다음 날)."""
        return self.days[bisect.bisect_right(self.days, s)]

    def first_td(self, y: int) -> str:
        if y not in self._first:
            self._first[y] = self.next_td("%04d-12-31" % (y - 1))
        return self._first[y]

    def check_observed(self, lo="2011-01-01"):
        """규칙 격자 대 관측 격자(stocks.json pxd_dates) — 관측 끝까지. 어긋난 날을 돌려준다."""
        S = _rj(os.path.join(DATA, "stocks.json")) or {}
        obs = sorted(x for x in (S.get("pxd_dates") or []) if x >= lo)
        if not obs:
            return {"observed": 0}
        hi = obs[-1]
        rule = [x for x in self.days if lo <= x <= hi]
        so, sr = set(obs), set(rule)
        return {"observed_range": [obs[0], hi], "n_observed": len(obs), "n_rule": len(rule),
                "rule_not_observed": sorted(sr - so), "observed_not_rule": sorted(so - sr)}


def months_ok(cal: Cal, start=DATA_START, end=DATA_END):
    """제출일 창 [start, end] 로 **다 찬** 가용월 — 그달 가용되는 모든 제출일이 창 안이다."""
    out = []
    ym = start[:7]
    while ym <= _madd(end[:7], 1):
        first = ym + "-01"
        # 그달 첫 가용일을 만드는 가장 이른 제출일 = 전달 마지막 거래일
        i = bisect.bisect_left(cal.days, first)
        prev_td = cal.days[i - 1]
        nxt = _madd(ym, 1) + "-01"
        j = bisect.bisect_left(cal.days, nxt)
        last_td = cal.days[j - 1]
        fmax = (dt.date.fromisoformat(last_td) - dt.timedelta(days=1)).isoformat()
        if start <= prev_td and fmax <= end:
            out.append(ym)
        ym = _madd(ym, 1)
    return out


# ════════════════════════════════════════════════════════════════════════
# 발행사 지도
# ════════════════════════════════════════════════════════════════════════
class Map:
    """data/_issuer_map.json — cik → 그룹 · CIK 효력 구간 · 멤버-월(그룹 · fpi · Stage M 자격)."""

    def __init__(self, path=IMAP):
        d = _rj(path)
        self.doc, self.sha = d, _sha_file(path)
        self.c2g, self.iv = {}, {}
        for g, v in d["groups"].items():
            for c, f, to, src, nm in v["ciks"]:
                if c in self.c2g and self.c2g[c] != g:
                    raise SystemExit("🚨 CIK %d 가 두 그룹(%s · %s)에 있다" % (c, self.c2g[c], g))
                self.c2g[c] = g
                self.iv[c] = (f, to)
        self.c2g_sha = _sha(json.dumps(sorted(self.c2g.items())).encode())
        # 등록 FPI 표지(지도의 fpi_registered — 2026-09-25 권고 fpi_q) · 사양 칸 fpi 는 *_spec 세계로 옆에 싣는다
        self.fpi_field = (d.get("fpi_registered") or {}).get("field") or "fpi"
        if self.fpi_field not in ("fpi", "fpi_q"):
            raise SystemExit("🚨 fpi_registered.field=%s 를 모른다" % self.fpi_field)
        self.idx = {}
        for t, runs in d["tm"].items():
            for a, b, g, p, cs, fpi, src, fpq in runs:
                ym = a
                while ym <= b:
                    self.idx[(t, ym)] = (g, fpq if self.fpi_field == "fpi_q" else fpi, fpi)
                    ym = _madd(ym, 1)
        self.months = sorted({ym for _, ym in self.idx})
        self.viol = {(x[0], x[1]) for x in (d.get("f0") or {}).get("violations") or []}
        self.viol_spec = {(x[0], x[1]) for x in ((d.get("f0") or {}).get("spec_flag") or {}).get("violations") or []} or self.viol

    def oiv(self, cik, fd):
        f, to = self.iv.get(cik, (None, None))
        return 1 if ((f and fd < f) or (to and fd > to)) else 0

    def members(self, R=None):
        """{월: {"all", "s16", "sm", "s16_spec", "sm_spec": {그룹}}} — s16 = 등록 표지 fpi != 1(null 포함 · issuer_map F0 와 같다) ·
        sm = Stage M 세계(창 안 · 그달 비금융 · s16 · F0 통과). *_spec = 사양 칸 fpi 로 센 같은 세계(비교용)."""
        out = {}
        for (t, ym), (g, fpi, fsp) in self.idx.items():
            if g is None:
                continue
            o = out.setdefault(ym, {"all": set(), "s16": set(), "sm": set(), "s16_spec": set(), "sm_spec": set()})
            o["all"].add(g)
            win = R is not None and STAGE_M[0] <= ym <= STAGE_M[1]
            nonfin = win and IM.sector_at(R, t, ym) not in FIN
            if fpi != 1:
                o["s16"].add(g)
                if nonfin and (t, ym) not in self.viol:
                    o["sm"].add(g)
            if fsp != 1:
                o["s16_spec"].add(g)
                if nonfin and (t, ym) not in self.viol_spec:
                    o["sm_spec"].add(g)
        return out


# ════════════════════════════════════════════════════════════════════════
# fetch — 인덱스 페이지 href → RAW/ins · 해시 대조
# ════════════════════════════════════════════════════════════════════════
def _link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def cmd_fetch(remote=False):
    man = IM.ins_manifest()
    links = IM.dera_links()                          # 인덱스 페이지 1건 — 분기마다 경로가 달라 훑는다
    rep = {"index_url": IM.DERA_INDEX, "fetched_at": _now(), "n_links": len(links), "quarters": {}}
    for key in quarters():
        url = links.get(key)
        if not url:
            raise SystemExit("🚨 인덱스 페이지에 %s 링크가 없다" % key)
        m = man.get(key)
        dst = os.path.join(RAW_INS, key + "_form345.zip")
        r = {"href": url}
        if m and m.get("url") != url:
            r["href_moved_from"] = m.get("url")      # 같은 판이 경로만 옮겨진 것(최신 분기 → 과거 분기 디렉터리)
        if os.path.exists(dst):
            sha = _sha_file(dst)
            r["how"] = "local"
        elif os.path.exists(os.path.join(RAW_OLD, key + "_form345.zip")):
            src = os.path.join(RAW_OLD, key + "_form345.zip")
            sha = _sha_file(src)
            if m and m["sha256"] != sha:
                raise SystemExit("🚨 %s RAW/dera ZIP 해시가 manifest 와 다르다" % key)
            r["how"] = _link_or_copy(src, dst)
        else:
            hd = IM._head(url)
            t0 = time.time()
            b = edgar.fetch_bytes(url, timeout=600)
            sha = _sha(b)
            if m and m["sha256"] != sha:
                raise SystemExit("🚨 고정 해시가 바뀌었다 — %s\n   manifest %s\n   지금     %s\n   원본이 다시 게시됐다. 빌드를 멈춘다."
                                 % (key, m["sha256"], sha))
            os.makedirs(RAW_INS, exist_ok=True)
            with open(dst + ".tmp", "wb") as f:
                f.write(b)
            os.replace(dst + ".tmp", dst)
            r["how"] = "download %.1fMB %.0fs" % (len(b) / 1e6, time.time() - t0)
            if not m:
                meta = {"url": url, "sha256": sha, "bytes": len(b), "fetched": _now(), "path": "ins/%s_form345.zip" % key}
                meta.update(hd)
                with zipfile.ZipFile(dst) as z:
                    meta["inner"] = {i.filename.split("/")[-1]: [i.file_size, "%04d-%02d-%02d" % i.date_time[:3]]
                                     for i in z.infolist()}
                man.put(key, meta)
        if m and m["sha256"] != sha:
            raise SystemExit("🚨 %s 로컬 ZIP 해시가 manifest 와 다르다 (%s)" % (key, dst))
        r["sha256_ok"] = True
        if remote:
            hd = IM._head(url)
            r["remote"] = hd
            if m and hd.get("last_modified") and hd.get("last_modified") != m.get("last_modified"):
                r["remote_last_modified_changed"] = [m.get("last_modified"), hd.get("last_modified")]
            if m and hd.get("content_length") and str(hd.get("content_length")) != str(m.get("bytes")):
                r["remote_size_changed"] = [m.get("bytes"), hd.get("content_length")]
        rep["quarters"][key] = r
    man.save()
    moved = [k for k, r in rep["quarters"].items() if r.get("href_moved_from")]
    chg = [k for k, r in rep["quarters"].items() if r.get("remote_last_modified_changed") or r.get("remote_size_changed")]
    print("✓ DERA %d분기 · 모두 해시 일치 · 경로 옮겨짐 %s · 원격 변경 %s" % (len(rep["quarters"]), moved or "없음",
                                                                (chg or "없음") if remote else "(HEAD 안 함)"))
    _wj(os.path.join(RAW, "_ins_fetch.json"), rep, indent=1)
    return rep


def zip_path(key, man):
    p = os.path.join(RAW_INS, key + "_form345.zip")
    if not os.path.exists(p):
        raise SystemExit("🚨 %s 가 없다 — fetch 를 먼저" % p)
    return p


# ════════════════════════════════════════════════════════════════════════
# 원 행 — 분기 ZIP → 세계 발행사의 P/S 행(각주 본문 포함) · 저장소 밖 캐시
# ════════════════════════════════════════════════════════════════════════
def _tsv(z, names, t):
    with z.open(names[t]) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t",
                                  quoting=csv.QUOTE_NONE)


def parse_zip(key, path, M: Map):
    """분기 ZIP → (원 행 목록, 개수). 원 행 = r_r1_flags.CACHE_FIELDS 이름 + 덧붙인 칸."""
    st = collections.Counter()
    with zipfile.ZipFile(path) as z:
        names = {n.split("/")[-1]: n for n in z.namelist()}
        sub = {}
        for r in _tsv(z, names, "SUBMISSION.tsv"):
            doc = (r.get("DOCUMENT_TYPE") or "").strip()
            if doc not in FORMS:
                continue
            ck = _cik(r.get("ISSUERCIK"))
            g = M.c2g.get(ck)
            if g is None:
                continue
            st["sub_world_" + doc] += 1
            sub[r["ACCESSION_NUMBER"]] = {
                "doc": doc, "fdate": _ddate(r.get("FILING_DATE")), "issuer_cik": ck, "gid": g,
                "sym": (r.get("ISSUERTRADINGSYMBOL") or "").strip(), "remarks": _unq((r.get("REMARKS") or "").strip()),
                "aff": _aff(r.get("AFF10B5ONE")), "aff_raw": (r.get("AFF10B5ONE") or "").strip() if "AFF10B5ONE" in r else None,
                "ns16": (r.get("NOT_SUBJECT_SEC16") or "").strip(), "period": _ddate(r.get("PERIOD_OF_REPORT")),
                "orig": _ddate(r.get("DATE_OF_ORIG_SUB"))}
        nd, need = [], set()
        fn_cols = None
        for r in _tsv(z, names, "NONDERIV_TRANS.tsv"):
            a = r.get("ACCESSION_NUMBER")
            if a not in sub:
                continue
            code = (r.get("TRANS_CODE") or "").strip().upper()
            if code not in CODES:
                continue
            if fn_cols is None:
                fn_cols = [k for k in r.keys() if k and k.endswith("_FN")]
            ids = []
            for k in fn_cols:
                v = r.get(k)
                if v:
                    for x in re.split(r"[,\s]+", v.strip()):
                        if x and x not in ids:
                            ids.append(x)
            need.update((a, x) for x in ids)
            nd.append((a, r, ids))
        fn = {}
        for r in _tsv(z, names, "FOOTNOTES.tsv"):
            k = (r.get("ACCESSION_NUMBER"), (r.get("FOOTNOTE_ID") or "").strip())
            if k in need:
                fn[k] = _unq(r.get("FOOTNOTE_TXT") or "")
        accs = {a for a, _, _ in nd}
        own = collections.defaultdict(list)
        for r in _tsv(z, names, "REPORTINGOWNER.tsv"):
            a = r.get("ACCESSION_NUMBER")
            if a not in accs:
                continue
            c = _cik(r.get("RPTOWNERCIK"))
            if c is None:
                st["owner_no_cik"] += 1
                continue
            rel = (r.get("RPTOWNER_RELATIONSHIP") or "").strip()
            lst = own[a]
            for o in lst:
                if o[0] == c:                        # 같은 보고자가 두 줄 — 관계를 합친다
                    o[1] = rel_of(_bits(o[1]) | _bits(rel)) if rel else o[1]
                    st["owner_dup_row"] += 1
                    break
            else:
                lst.append([c, rel, _unq((r.get("RPTOWNERNAME") or "").strip()), _unq((r.get("RPTOWNER_TITLE") or "").strip())])
    out = []
    for a, r, ids in nd:
        s = sub[a]
        miss = [x for x in ids if (a, x) not in fn]
        if miss:
            st["fn_id_missing"] += len(miss)
        txt = " ".join(fn[(a, x)] for x in ids if fn.get((a, x)))
        sh, px = _num(r.get("TRANS_SHARES")), _num(r.get("TRANS_PRICEPERSHARE"))
        try:
            sk = int((r.get("NONDERIV_TRANS_SK") or "").strip())
        except ValueError:
            sk = None
        rec = {"acc": a, "sk": sk, "doc": s["doc"], "fdate": s["fdate"], "issuer_cik": s["issuer_cik"], "gid": s["gid"],
               "sym": s["sym"], "tdate": _ddate(r.get("TRANS_DATE")), "deemed": _ddate(r.get("DEEMED_EXECUTION_DATE")),
               "code": (r.get("TRANS_CODE") or "").strip().upper(), "ad": (r.get("TRANS_ACQUIRED_DISP_CD") or "").strip().upper(),
               "tft": (r.get("TRANS_FORM_TYPE") or "").strip(), "swap": (r.get("EQUITY_SWAP_INVOLVED") or "").strip(),
               "shares": sh, "price": px, "post": _num(r.get("SHRS_OWND_FOLWNG_TRANS")),
               "di": (r.get("DIRECT_INDIRECT_OWNERSHIP") or "").strip(), "title": _unq((r.get("SECURITY_TITLE") or "").strip()),
               "fn_ids": ids, "fn_text": txt, "remarks": s["remarks"], "aff": s["aff"], "aff_raw": s["aff_raw"],
               "ns16": s["ns16"], "period": s["period"], "orig": s["orig"],
               "owners": [[o[0], o[1]] for o in own.get(a, [])],
               "owner_info": [[o[0], o[2], o[3]] for o in own.get(a, [])],
               "stc": 1 if is_stc(txt) else 0,          # 캐시 안 값은 파싱 때 식 — 읽을 때 flag_text 가 다시 건다
               "p10_rx": 1 if plan_hit(txt + " " + s["remarks"]) else 0,
               "p10f": 1 if plan_hit(txt) else 0, "p10r": 1 if plan_hit(s["remarks"]) else 0}
        out.append(rec)
        st["rows_" + s["doc"] + "_" + rec["code"]] += 1
    st["rows"] = len(out)
    return out, dict(st)


def _cache_path(key):
    return os.path.join(CACHE, key + ".jsonl.gz")


def load_or_parse(key, M: Map, man, cman, lean=False):
    """원 행 캐시 — 첫 줄 머리(ZIP 해시 · 형식 판 · 지도 CIK 해시)가 맞으면 읽고, 아니면 ZIP 을 다시 읽어 쓴다.
    읽을 때마다 강제 매도 두 판정(stc · stc_v1)을 각주 본문에서 다시 건다(flag_text). lean = 정리에 쓰지 않는 글 칸(HEAVY)을 뺀다."""
    m = man.get(key)
    zsha = m["sha256"]
    cp = _cache_path(key)
    head = {"key": key, "zip_sha256": zsha, "parse_ver": PARSE_VER, "c2g_sha256": M.c2g_sha}

    def fin(rows):
        for r in rows:
            flag_text(r)
            if lean:
                for k in HEAVY:
                    r.pop(k, None)
        return rows
    if os.path.exists(cp):
        with gzip.open(cp, "rt", encoding="utf-8") as f:
            h = json.loads(f.readline())
            if all(h.get(k) == v for k, v in head.items()):
                rows = [json.loads(line) for line in f]
                ent = cman.get(key) or {}
                if ent.get("sha256") and ent["sha256"] != _sha_file(cp):
                    raise SystemExit("🚨 원 행 캐시 %s 의 해시가 cache_manifest 와 다르다" % cp)
                return fin(rows), h["stats"], False
    p = zip_path(key, man)
    if _sha_file(p) != zsha:
        raise SystemExit("🚨 %s ZIP 해시가 manifest 와 다르다" % key)
    rows, st = parse_zip(key, p, M)
    head["stats"] = st
    os.makedirs(CACHE, exist_ok=True)
    tmp = cp + ".tmp"
    with open(tmp, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as g:
            g.write((json.dumps(head, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            for r in rows:
                g.write((json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    os.replace(tmp, cp)
    return fin(rows), st, True


# ════════════════════════════════════════════════════════════════════════
# 정리 — 버림 · 가용일 · 정정 중복 · 공동 제출
# ════════════════════════════════════════════════════════════════════════
def _eff(X):
    """짝 짓기에 쓰는 «지금 값» — 고친 값(corr = 1 의 shc · pxc)이 있으면 그것 · 아니면 제출된 그대로(r_r1_flags._eff 와 같다)."""
    return (X["shc"], X["pxc"]) if X["corr"] == 1 else (X["sh"], X["px"])


def clean(raw, cal: Cal, M: Map, date_corrections=True):
    """원 행(모든 분기) → (정리된 행 목록, 연도별 개수). 원 행은 바꾸지 않는다.
    규칙 = r_r1_flags.prepare 와 한 식(정정 중복 선언 c · 캐시 cnt 선언 k · 4/A 정정 선언 q · 거래일 정정 선언 q2). 원 행 레코드가
    캐시 정정 짝(corr = 2 · 3 · ctgt — load_panel 이 낸 패널 행)을 가져오면 그 짝을 쓴다 · corr 칸이 있으면 corr = 3 인 행만 거래일 정정.
    연도 = 제출 연도(정정 짝 원 행 수는 원 행 제출 연도). 🔒 sh · px · usd = 제출된 그대로(등록 1차) · 고친 값은 shc · pxc · usdc(선언 q)."""
    st = collections.defaultdict(collections.Counter)
    keep = []
    for r in raw:
        y = (r["fdate"] or "????")[:4]
        S = st[y]
        S["raw_" + r["doc"]] += 1
        if r["doc"] not in FORMS4:
            S["x_form5_" + r["code"]] += 1
            continue
        S["raw4_" + r["code"]] += 1
        if r["ad"] != CODES[r["code"]]:
            S["x_ad_mismatch"] += 1
            continue
        if not r["tdate"] or not r["fdate"]:
            S["x_no_date"] += 1
            continue
        if r["tdate"] > r["fdate"]:
            S["x_tdate_after_fdate"] += 1
            continue
        if not r["owners"]:
            S["x_no_owner"] += 1
            continue
        keep.append(r)
    keep.sort(key=lambda r: R1.dedupe_order(r["fdate"], r["doc"], r["acc"], r["sk"]))
    first = {}                                   # 여섯 칸 키 → 그 키를 처음 낸 접수번호
    seen4 = {}                                   # (그룹, 보고자, 거래일, 코드) → 처음 가용일(앞선 제출의 남은 행 · 보고용)
    live = collections.defaultdict(list)         # (그룹, 거래일, 코드) → 앞선 제출의 «살아 있는» 행 번호(정정 행 제외)
    live_fd = collections.defaultdict(list)      # (그룹, 제출일, 코드) → 같은 뜻(선언 q2 — 4/A 가 고치는 제출의 행)
    pos = {}                                     # (접수번호, SK 문자열) → 행 번호(캐시 짝)
    allown = []                                  # 행 번호 → 원 보고자 CIK 집합
    W = []                                       # 남은 행(작업용 사전)
    i = 0
    while i < len(keep):
        j = i
        while j < len(keep) and keep[j]["acc"] == keep[i]["acc"]:
            j += 1
        block, i = keep[i:j], j
        amend = block[0]["doc"] == "4/A"
        stat = []
        for r in block:
            new, old, cor = [], [], []
            for c, rel in r["owners"]:
                k6 = (r["gid"], c, r["tdate"], r["code"], _k6(r["shares"]), _k6(r["price"]))
                a0 = first.get(k6)
                if a0 is not None and a0 != r["acc"]:
                    old.append([c, _bits(rel)])          # 같은 제출 안 같은 값 두 행은 지우지 않는다(a0 == 이 제출)
                elif amend and (r["gid"], c, r["tdate"], r["code"]) in seen4:
                    cor.append([c, _bits(rel)])          # 선언 q — 앞선 제출이 알린 거래를 값만 고쳤다
                else:
                    new.append([c, _bits(rel)])
            w = {"r": r, "sh": r["shares"], "px": r["price"], "corr": 0, "shc": None, "pxc": None, "ctgt": None, "tdh": None,
                 "av": cal.next_td(r["fdate"]), "new": new, "old": old, "cor": cor, "dcor": []}
            stat.append(w)
        if amend:
            conf = set()                                 # 이 4/A 가 같은 값으로 다시 적어 확인한 원 행 — 짝에서 뺀다(«지금 값»)
            for w in stat:
                r = w["r"]
                if w["old"] and not w["cor"]:
                    oc = {c for c, _ in w["old"]}
                    for x in live.get((r["gid"], r["tdate"], r["code"]), ()):
                        es, ep = _eff(W[x])
                        if x not in conf and _k6(es) == _k6(r["shares"]) and _k6(ep) == _k6(r["price"]) and oc & allown[x]:
                            conf.add(x)
                            break
            used = set()
            for w in stat:
                r = w["r"]
                if not w["cor"]:
                    continue
                S = st[r["fdate"][:4]]
                cc = {c for c, _ in w["cor"]}
                tgt = None
                if r.get("corr") == 2:                   # 캐시(패널)가 정한 짝 — 다시 찾지 않는다
                    S["corr_from_cache"] += 1
                    ct = r.get("ctgt")
                    if ct:
                        ka = (str(ct[0]), str(ct[1]))
                        tgt = next((x for x in live.get((r["gid"], r["tdate"], r["code"]), ())
                                    if (W[x]["r"]["acc"], str(W[x]["r"]["sk"])) == ka), None)
                        if tgt is None:
                            S["corr_cache_target_missing"] += 1
                else:
                    for x in live.get((r["gid"], r["tdate"], r["code"]), ()):
                        if x not in conf and x not in used and cc & allown[x]:
                            tgt = x
                            break
                w["corr"] = 2
                if tgt is None:
                    S["corr_unpaired"] += 1
                    continue
                used.add(tgt)
                X = W[tgt]
                X["shc"], X["pxc"], X["corr"], X["ctgt"] = r["shares"], r["price"], 1, [r["acc"], r["sk"]]   # 🔒 원 행 값 그대로
                w["ctgt"] = [X["r"]["acc"], X["r"]["sk"]]
                S["corr_paired"] += 1
                if X["av"][:7] != w["av"][:7]:
                    S["corr_paired_later_month"] += 1   # 옛 규칙이면 원 행보다 뒤 달에 새 사건을 세웠다(검토 실측 310)
            # 선언 q2 — 거래일 정정(r_r1_flags.prepare 와 한 식 · 짝은 거래일 정정끼리만 하나씩 — used_d)
            used_d = set()
            for w in (stat if date_corrections else ()):
                r = w["r"]
                if w["cor"] or not w["new"]:
                    continue
                cin = r.get("corr")
                if cin is not None and cin != 3:
                    continue                             # 캐시(패널)가 거래일 정정이 아니라고 정했다
                S = st[r["fdate"][:4]]
                tgt = None
                if cin == 3:
                    S["dcorr_from_cache"] += 1
                    ct = r.get("ctgt")
                    if ct:
                        tgt = pos.get((str(ct[0]), str(ct[1])))
                        if tgt is not None and W[tgt]["corr"] in (2, 3):
                            tgt = None
                    if tgt is None:
                        S["dcorr_cache_target_missing"] += 1
                else:
                    if not r.get("orig"):
                        S["dcorr_no_orig"] += 1
                        continue
                    nc = {c for c, _ in w["new"]}
                    for x in live_fd.get((r["gid"], r["orig"], r["code"]), ()):
                        X = W[x]
                        if x in conf or x in used_d or X["r"]["tdate"] == r["tdate"] or not (nc & allown[x]):
                            continue
                        es, ep = _eff(X)                  # 제출된 그대로 또는 고친 값 — 둘 중 하나와 같으면(r_r1_flags.prepare 와 같다)
                        if ((_k6(X["sh"]) == _k6(r["shares"]) and _k6(X["px"]) == _k6(r["price"]))
                                or (_k6(es) == _k6(r["shares"]) and _k6(ep) == _k6(r["price"]))):
                            tgt = x
                            break
                    if tgt is None:
                        continue                         # 거래일 정정이 아니다 — 새 행
                w["corr"] = 3
                if tgt is None:
                    continue
                used_d.add(tgt)
                X = W[tgt]
                xo = allown[tgt]
                w["dcor"] = [o for o in w["new"] if o[0] in xo]
                w["new"] = [o for o in w["new"] if o[0] not in xo]
                X["tdh"] = [r["tdate"], r["acc"], r["sk"]]
                w["ctgt"] = [X["r"]["acc"], X["r"]["sk"]]
                S["dcorr_paired"] += 1
                S["dcorr_paired_later_month"] += 1 if X["av"][:7] != w["av"][:7] else 0
                S["dcorr_hist_year_change"] += 1 if X["r"]["tdate"][:4] != r["tdate"][:4] else 0
                y0, y1 = int(X["av"][:4]), int(w["av"][:4])
                S["dcorr_hist_early"] += 1 if any(X["av"] <= cal.first_td(yy) < w["av"] for yy in range(y0 + 1, y1 + 1)) else 0
        for w in stat:
            r = w["r"]
            S = st[r["fdate"][:4]]
            new, old, cor, dcor = w["new"], w["old"], w["cor"], w["dcor"]
            if not new and not cor and not dcor and w["corr"] != 3:
                S["x_dup_" + ("amend" if r["doc"] == "4/A" else "orig")] += 1
                continue
            own0 = {c for c, _ in r["owners"]}
            if cor:
                S["corr_rows"] += 1
                S["corr_rows_" + r["code"]] += 1
                # 검토 실측(310)과 같은 정의 — 그 거래 키를 처음 알린 제출보다 뒤 가용월(옛 규칙이면 그 달에 새 사건)
                fav = min(seen4[(r["gid"], c, r["tdate"], r["code"])] for c, _ in cor)
                S["corr_rows_later_month_than_first"] += 1 if w["av"][:7] > fav[:7] else 0
                S["corr_rows_with_new_owner"] += 1 if new else 0
                cnt, cnt6 = 0, (0 if old else 1)
            elif w["corr"] == 3:
                S["dcorr_rows"] += 1
                S["dcorr_rows_" + r["code"]] += 1
                S["dcorr_rows_with_new_owner"] += 1 if new else 0
                cnt, cnt6 = 0, (0 if old else 1)
            else:
                cnt = 0 if old else 1
                cnt6 = cnt
                if old:
                    S["dup_partial_owner"] += 1
            if r["doc"] == "4/A":
                if not cor and w["corr"] != 3:
                    S["amend_new_rows_v1"] += 1          # 옛 정의(정정 행이 아닌 남은 4/A 행 · 세지 않는 부분 중복 포함 · 보고용)
                if cnt:
                    S["amend_new_rows"] += 1             # 🔒 사건인 4/A 행(cnt = 1) — 2026-09-26 정의 수정(검토 지적)
            w["cnt"], w["cnt6"] = cnt, cnt6
            for c, _ in new + cor + dcor:
                first.setdefault((r["gid"], c, r["tdate"], r["code"], _k6(r["shares"]), _k6(r["price"])), r["acc"])
            for c in own0:
                seen4.setdefault((r["gid"], c, r["tdate"], r["code"]), w["av"])
            allown.append(own0)
            pos[(r["acc"], str(r["sk"]))] = len(W)
            if w["corr"] not in (2, 3):
                live[(r["gid"], r["tdate"], r["code"])].append(len(W))
                live_fd[(r["gid"], r["fdate"], r["code"])].append(len(W))
            W.append(w)
    out = []
    for w in W:
        r = w["r"]
        S = st[r["fdate"][:4]]
        sh, px = w["sh"], w["px"]
        usd = round(sh * px, 2) if (sh is not None and px is not None and px > 0) else None
        shc, pxc = (w["shc"], w["pxc"]) if w["corr"] == 1 else (None, None)
        usdc = round(shc * pxc, 2) if (shc is not None and pxc is not None and pxc > 0) else None
        oiv = M.oiv(r["issuer_cik"], r["fdate"])
        if oiv:
            S["oiv_rows"] += 1
        S["kept_" + r["code"]] += 1
        if w["corr"] == 1:
            S["corr_targets"] += 1
            S["corr_targets_sh_changed"] += 1 if _k6(shc) != _k6(sh) else 0
            S["corr_targets_px_changed"] += 1 if _k6(pxc) != _k6(px) else 0
        if w["tdh"]:
            S["dcorr_targets"] += 1
        if r["code"] == "S" and r["stc_v1"] and not r["stc"]:
            S["stc_v1_only_S"] += 1                      # 선언 p — 옛 식으로는 빠지던 매도 행(이제 남는다)
        S["stc_S"] += r["stc"] if r["code"] == "S" else 0
        S["stc_v1_S"] += r["stc_v1"] if r["code"] == "S" else 0
        out.append([r["gid"], r["issuer_cik"], r["acc"], r["sk"], r["doc"], r["fdate"], w["av"], r["tdate"],
                    r["code"], _int_or(sh), _int_or(px), _int_or(usd) if usd is not None else None, w["new"],
                    r["stc"], r["p10_rx"], r["p10f"], r["p10r"], r["aff"], w["cnt"], oiv, w["old"] or None,
                    r["stc_v1"], w["corr"], w["ctgt"], _int_or(shc), _int_or(pxc), _int_or(usdc) if usdc is not None else None,
                    (w["cor"] or w["dcor"]) or None, w["cnt6"], (r.get("orig") or None) if r["doc"] == "4/A" else None, w["tdh"]])
    return out, {y: dict(v) for y, v in sorted(st.items())}


C = {k: j for j, k in enumerate(PANEL_COLS)}


def write_panel(rows, pins):
    by = collections.defaultdict(list)
    for r in rows:
        by[r[C["fd"]][:4]].append(r)
    os.makedirs(PANEL, exist_ok=True)
    files = {}
    for y, rs in sorted(by.items()):
        p = os.path.join(PANEL, "ps_%s.json.gz" % y)
        write_gz_json(p, {"note": PANEL_NOTE, "cols": PANEL_COLS, "year": y, "pins": pins, "n": len(rs), "rows": rs})
        files[os.path.relpath(p, ROOT).replace("\\", "/")] = {"sha256": _sha_file(p), "bytes": os.path.getsize(p), "rows": len(rs)}
    for f in os.listdir(PANEL):                      # 지난 빌드의 남은 해 파일
        if f.startswith("ps_") and f[3:7] not in by:
            os.remove(os.path.join(PANEL, f))
    return files


def load_panel(years=None, path=PANEL):
    """쓰는 쪽 도우미 — 패널 행을 «정리 전» 형 사전으로(r_r1_flags.CACHE_FIELDS 이름 + av · cnt · oiv · p10f · p10r · …).
    clean() 이나 r_r1_flags.rows_from_records → prepare 에 다시 넣으면 같은 정리 · 정정이 나온다:
      owners = own + odup + ocor(원 보고자) · shares · price = 제출된 그대로(sh · px) · corr · ctgt = 캐시 정정 짝 · orig.
    등록 1차 값은 shares_eff · price_eff · usd(= 제출된 그대로 · 선언 q) · 고친 값(민감도 T1C)은 shares_c · price_c · usd_c ·
    거래일 정정(선언 q2)은 tdh · 세는 보고자는 own_bits(own)에 있다 — 패널을 그대로 읽는 쪽은 그 칸을 쓸 것."""
    out = []
    for f in sorted(os.listdir(path)):
        if not (f.startswith("ps_") and f.endswith(".json.gz")):
            continue
        if years and f[3:7] not in {str(y) for y in years}:
            continue
        d = read_gz_json(os.path.join(path, f))
        j = {k: i for i, k in enumerate(d["cols"])}
        for r in d["rows"]:
            corr = r[j["corr"]]
            sh, px = r[j["sh"]], r[j["px"]]
            out.append({"acc": r[j["acc"]], "sk": r[j["sk"]], "doc": r[j["doc"]], "fdate": r[j["fd"]], "issuer_cik": r[j["cik"]],
                        "gid": r[j["g"]], "tdate": r[j["td"]], "code": r[j["c"]], "ad": CODES[r[j["c"]]],
                        "shares": sh, "price": px, "shares_eff": sh, "price_eff": px, "usd": r[j["usd"]],
                        "shares_c": r[j["shc"]], "price_c": r[j["pxc"]], "usd_c": r[j["usdc"]], "orig": r[j["orig"]],
                        "tdh": r[j["tdh"]],
                        "owners": [[c, rel_of(b)] for c, b in r[j["own"]] + (r[j["odup"]] or []) + (r[j["ocor"]] or [])],
                        "own_bits": r[j["own"]],
                        "stc": r[j["stc"]], "stc_v1": r[j["stc_v1"]], "p10_rx": r[j["p10"]], "p10f": r[j["p10f"]], "p10r": r[j["p10r"]],
                        "aff": r[j["aff"]], "remarks": "", "fn_text": None,
                        "av": r[j["av"]], "cnt": r[j["cnt"]], "oiv": r[j["oiv"]], "corr": corr,
                        "ctgt": r[j["ctgt"]] if corr in (2, 3) else None, "cnt6": r[j["cnt6"]]})
    return out


# ════════════════════════════════════════════════════════════════════════
# 밀도 보고서(수익 없음)
# ════════════════════════════════════════════════════════════════════════
def density(rows, raw_by_q, st_clean, M: Map, cal: Cal, R):
    mem = M.members(R)
    mok = set(months_ok(cal))
    ins = lambda own: [c for c, b in own if b & INSIDER_BITS]
    off = lambda own: [c for c, b in own if b & 2]

    # ── 연도별(제출 연도) — 표지율 · 지연 · 공동 제출 ────────────────
    Y = collections.defaultdict(collections.Counter)
    lag = collections.defaultdict(list)
    sfil = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0, 0, 0, 0]))   # 임원 S 제출: 행, $, p10, 행 수(각주 없음), stc
    for r in rows:
        fd, av, td, code, own = r[C["fd"]], r[C["av"]], r[C["td"]], r[C["c"]], r[C["own"]]
        y = fd[:4]
        V = Y[y]
        V["rows_" + code] += 1
        if not r[C["cnt"]]:
            V["nocnt_" + code] += 1
            continue
        ii = ins(own)
        if not ii:
            V["noins_" + code] += 1
            continue
        if code == "P":
            V["P_ins"] += 1
            continue
        V["S_ins"] += 1
        lag[y].append((dt.date.fromisoformat(fd) - dt.date.fromisoformat(td)).days)
        if td < "2000-01-01":
            V["S_tdate_pre2000"] += 1
        stc, p10, p10f, p10r, aff = r[C["stc"]], r[C["p10"]], r[C["p10f"]], r[C["p10r"]], r[C["aff"]]
        V["S_stc"] += stc
        V["S_stc_v1"] += r[C["stc_v1"]]                     # 선언 p — 수정 전 식(감사)
        V["S_stc_v1_only"] += 1 if (r[C["stc_v1"]] and not stc) else 0
        V["S_corr1"] += 1 if r[C["corr"]] == 1 else 0       # 선언 q — 4/A 가 값을 고친 원 행(1차는 제출된 그대로)
        V["S_tdh"] += 1 if r[C["tdh"]] else 0               # 선언 q2 — 4/A 가 거래일을 고친 원 행(이력만 고친 거래일)
        V["S_p10_rx"] += p10
        V["S_p10_fn"] += p10f
        V["S_p10_rm"] += p10r
        if len(own) > 1:
            V["S_joint_rows"] += 1
        if fd >= AFF_FROM:
            V["S_post_box"] += 1
            V["S_box"] += 1 if aff == 1 else 0
            V["S_box_null"] += 1 if aff is None else 0
            V["S_or"] += 1 if (p10 or aff == 1) else 0
            V["S_rx_ne_box"] += 1 if bool(p10) != (aff == 1) else 0
            V["S_rx_only"] += 1 if (p10 and aff != 1) else 0
            V["S_box_only"] += 1 if (aff == 1 and not p10) else 0
        if off(own):
            V["S_off"] += 1
            if not p10:
                V["S_off_nop10"] += 1
                V["S_off_nop10_stc"] += stc
            f = sfil[y][r[C["acc"]]]
            f[0] += 1
            f[1] += r[C["usd"]] or 0.0
            f[2] = max(f[2], p10)
    by_year = {}
    for y in sorted(set(Y) | set(st_clean)):
        V, S0 = Y[y], st_clean.get(y, {})
        big = [f for f in sfil[y].values() if f[1] >= 100000]
        ls = lag[y]
        by_year[y] = {
            "clean": S0,
            "S_insider_rows": V["S_ins"], "P_insider_rows": V["P_ins"],
            "S_noninsider_rows": V["noins_S"], "P_noninsider_rows": V["noins_P"],
            "nocnt_rows": V["nocnt_S"] + V["nocnt_P"],
            "stc_rate": round(V["S_stc"] / V["S_ins"], 4) if V["S_ins"] else None,
            "stc_rows": V["S_stc"], "stc_rows_v1": V["S_stc_v1"], "stc_v1_only_kept": V["S_stc_v1_only"],
            "stc_rate_v1": round(V["S_stc_v1"] / V["S_ins"], 4) if V["S_ins"] else None,
            "corr_values_S_insider": V["S_corr1"], "corr_tdate_S_insider": V["S_tdh"],
            "p10_rx_rate": round(V["S_p10_rx"] / V["S_ins"], 4) if V["S_ins"] else None,
            "p10_fn_rate": round(V["S_p10_fn"] / V["S_ins"], 4) if V["S_ins"] else None,
            "p10_remarks_rate": round(V["S_p10_rm"] / V["S_ins"], 4) if V["S_ins"] else None,
            "box_from_2023_04": ({"rows": V["S_post_box"], "box_rate": round(V["S_box"] / V["S_post_box"], 4),
                                  "box_null": V["S_box_null"], "or_rate": round(V["S_or"] / V["S_post_box"], 4),
                                  "rx_ne_box_rate": round(V["S_rx_ne_box"] / V["S_post_box"], 4),
                                  "rx_only": V["S_rx_only"], "box_only": V["S_box_only"]} if V["S_post_box"] else None),
            "joint_rows_S": V["S_joint_rows"],
            "drift_officer_S_nop10_stc_share": round(V["S_off_nop10_stc"] / V["S_off_nop10"], 4) if V["S_off_nop10"] else None,
            "drift_officer_S_filings_ge100k_rx_hit": (round(sum(f[2] for f in big) / len(big), 4) if big else None),
            "drift_officer_S_filings_ge100k_n": len(big),
            "lag_days_S": {"p50": _pct(ls, .5), "p90": _pct(ls, .9), "p99": _pct(ls, .99), "max": max(ls) if ls else None,
                           "gt30": sum(1 for x in ls if x > 30), "gt365": sum(1 for x in ls if x > 365),
                           "tdate_pre2000": V["S_tdate_pre2000"]} if ls else None,
        }
    # 비평 실측과 같은 분기(2016Q3 · 2025Q3) — 표류 두 지표
    qdrift = {}
    for q, (a, b) in {"2016q3": ("2016-07-01", "2016-09-30"), "2025q3": ("2025-07-01", "2025-09-30")}.items():
        n0 = n1 = 0
        fil = collections.defaultdict(lambda: [0.0, 0])
        for r in rows:
            fd = r[C["fd"]]
            if not (a <= fd <= b) or r[C["c"]] != "S" or not r[C["cnt"]] or not off(r[C["own"]]):
                continue
            if not r[C["p10"]]:
                n0 += 1
                n1 += r[C["stc"]]
            f = fil[r[C["acc"]]]
            f[0] += r[C["usd"]] or 0.0
            f[1] = max(f[1], r[C["p10"]])
        big = [f for f in fil.values() if f[0] >= 100000]
        qdrift[q] = {"officer_S_nop10_stc_share": round(n1 / n0, 4) if n0 else None,
                     "officer_S_filings_ge100k_rx_hit": round(sum(f[1] for f in big) / len(big), 4) if big else None,
                     "n_filings_ge100k": len(big)}

    # ── 공동 제출(제출 단위 · S 가 든 Form 4) ───────────────────────
    jf = collections.defaultdict(lambda: [0, 0])
    seen = set()
    for r in rows:
        a = r[C["acc"]]
        if r[C["c"]] != "S" or a in seen:
            continue
        seen.add(a)
        v = jf[r[C["fd"]][:4]]
        v[0] += 1
        v[1] += 1 if len(r[C["own"]]) > 1 else 0
    joint = {y: {"S_filings": n, "joint": k, "share": round(k / n, 4) if n else None} for y, (n, k) in sorted(jf.items())}

    # ── 월별(가용월) 밀도 — S 행이 있는 발행사 그룹 수 ───────────────
    MS = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if not r[C["cnt"]]:
            continue
        own = r[C["own"]]
        if not ins(own):
            continue
        ym, g, code = r[C["av"]][:7], r[C["g"]], r[C["c"]]
        if code == "S":
            MS[ym]["S"].add(g)
            if not r[C["stc"]]:
                MS[ym]["S_nostc"].add(g)
            if off(own):
                MS[ym]["S_off"].add(g)
        else:
            MS[ym]["P"].add(g)
    # 제출월 기준(dens.py 와 같은 틀 · 모든 내부자 관계 · 그달 멤버) — 비평 실측 대조용
    FS = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if not r[C["cnt"]] or r[C["c"]] != "S":
            continue
        ym, g = r[C["fd"]][:7], r[C["g"]]
        FS[ym]["S_any"].add(g)
        if not r[C["stc"]]:
            FS[ym]["S_any_nostc"].add(g)
    by_month = {}
    for ym in sorted(MS):
        m = mem.get(ym)
        rec = {"ok": ym in mok,
               "world_S": len(MS[ym]["S"]), "world_S_nostc": len(MS[ym]["S_nostc"]), "world_P": len(MS[ym]["P"])}
        if m:
            s16, sm = m["s16"], m["sm"]
            rec.update({"mem_groups": len(m["all"]), "s16_groups": len(s16),
                        "s16_S": len(MS[ym]["S"] & s16), "s16_S_nostc": len(MS[ym]["S_nostc"] & s16),
                        "s16_S_officer": len(MS[ym]["S_off"] & s16), "s16_P": len(MS[ym]["P"] & s16)})
            if sm:
                rec.update({"sm_groups": len(sm), "sm_S": len(MS[ym]["S"] & sm), "sm_S_nostc": len(MS[ym]["S_nostc"] & sm),
                            "sm_P": len(MS[ym]["P"] & sm)})
            if m["s16_spec"] != s16 or m["sm_spec"] != sm:          # 사양 칸 fpi 로 센 세계가 다른 달(TEAM · NXPI)
                rec.update({"s16_spec_groups": len(m["s16_spec"]), "sm_spec_groups": len(m["sm_spec"])})
        if ym in FS and m:
            rec["filing_month_mem_S_any"] = len(FS[ym]["S_any"] & m["all"])
            rec["filing_month_mem_S_any_nostc"] = len(FS[ym]["S_any_nostc"] & m["all"])
        by_month[ym] = rec

    # ── 매수 쪽(INS1 매수 추종) F0 밀도 — Stage M 세계 · 다 찬 달 ─────
    pusd = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        if r[C["c"]] == "P" and r[C["cnt"]] and ins(r[C["own"]]):
            pusd[r[C["av"]][:7]][r[C["g"]]] += r[C["usd"]] or 0.0
    sm_ms = [ym for ym in sorted(by_month) if by_month[ym]["ok"] and "sm_groups" in by_month[ym]]
    top2 = []
    for ym in sm_ms:
        sm = mem[ym]["sm"]
        v = sorted((x for g, x in pusd[ym].items() if g in sm), reverse=True)
        if v and sum(v) > 0:
            top2.append(sum(v[:2]) / sum(v))
    sm_P = [by_month[ym]["sm_P"] for ym in sm_ms]
    sm_S = [by_month[ym]["sm_S_nostc"] for ym in sm_ms]
    buy = {"months": [sm_ms[0], sm_ms[-1], len(sm_ms)] if sm_ms else None,
           "groups_with_insider_P_median": _med(sm_P), "min": min(sm_P) if sm_P else None, "max": max(sm_P) if sm_P else None,
           "top2_share_of_P_usd_median": round(_med(top2), 4) if top2 else None,
           "top2_share_of_P_usd_p90": round(_pct(top2, .9), 4) if top2 else None}
    sell = {"months": [sm_ms[0], sm_ms[-1], len(sm_ms)] if sm_ms else None,
            "groups_with_insider_S_nostc_median": _med(sm_S), "min": min(sm_S) if sm_S else None,
            "max": max(sm_S) if sm_S else None}
    return {"by_year": by_year, "quarter_drift_vs_critique": qdrift, "joint_filings_S": joint, "by_month": by_month,
            "stage_m_sell_density": sell, "ins1_buy_density": buy, "months_ok": [min(mok), max(mok), len(mok)]}


# ════════════════════════════════════════════════════════════════════════
# build
# ════════════════════════════════════════════════════════════════════════
def cmd_build():
    t0 = time.time()
    M = Map()
    man = IM.ins_manifest()
    cman_doc = _rj(CMAN) or {"note": "저장소 밖 원 행 캐시(RAW/ins_cache/<분기>.jsonl.gz) 고정표 — 첫 줄 머리(ZIP 해시 · 형식 판 · 지도 CIK 해시) "
                                     "+ 한 줄 한 행(각주 본문 포함 · r_r1_flags.CACHE_FIELDS 이름). build/ins_pit_build.py 가 쓴다.",
                             "files": {}}
    cman = cman_doc["files"]
    cman_old = json.dumps(cman, sort_keys=True)
    cal = Cal()
    calchk = cal.check_observed()
    raw, qstats = [], {}
    n_new = 0
    for key in quarters():
        if not man.get(key):
            raise SystemExit("🚨 manifest 에 %s 가 없다 — fetch 를 먼저" % key)
        rows, st, new = load_or_parse(key, M, man, cman, lean=True)
        n_new += new
        cp = _cache_path(key)
        cman[key] = {"sha256": _sha_file(cp), "bytes": os.path.getsize(cp), "rows": len(rows),
                     "zip_sha256": man.get(key)["sha256"], "parse_ver": PARSE_VER}
        qstats[key] = st
        raw.extend(rows)
        print("  %s 원 행 %d %s" % (key, len(rows), "(새로 읽음)" if new else "(캐시)"), flush=True)
    if json.dumps(cman, sort_keys=True) != cman_old or cman_doc.get("c2g_sha256") != M.c2g_sha or not os.path.exists(CMAN):
        cman_doc["updated"] = _now()                 # 내용이 바뀔 때만 — 패널 pins 가 이 파일 해시를 싣는다(다시 빌드해도 같은 바이트)
        cman_doc["c2g_sha256"] = M.c2g_sha
        _wj(CMAN, cman_doc, indent=1)
    rows, st_clean = clean(raw, cal, M)
    print("정리: 원 행 %d → 패널 %d (%.0fs)" % (len(raw), len(rows), time.time() - t0), flush=True)
    pins = {"ins_manifest": _sha_file(IM.MAN_INS), "issuer_map": M.sha, "cache_manifest": _sha_file(CMAN),
            "script": _sha_file(os.path.abspath(__file__)), "r_r1_flags": _sha_file(R1.__file__)}
    files = write_panel(rows, pins)
    R = IM.load_refs()
    D = density(rows, qstats, st_clean, M, cal, R)
    tot = collections.Counter()
    for y, v in st_clean.items():
        tot.update(v)
    # 등록 전 수정 두 가지의 전후 개수(연도 = 제출 연도) — 강제 매도 식(선언 p) · 4/A 정정(선언 q)
    stc_chg = {y: {"S_rows_stc_new": v.get("stc_S", 0), "S_rows_stc_v1": v.get("stc_v1_S", 0),
                   "S_rows_no_longer_removed": v.get("stc_v1_only_S", 0),
                   "insider_S_stc_new": D["by_year"].get(y, {}).get("stc_rows"),
                   "insider_S_stc_v1": D["by_year"].get(y, {}).get("stc_rows_v1"),
                   "insider_S_no_longer_removed": D["by_year"].get(y, {}).get("stc_v1_only_kept")}
               for y, v in sorted(st_clean.items())}
    corr = {y: {k: v.get(k, 0) for k in ("corr_rows", "corr_rows_S", "corr_rows_P", "corr_rows_later_month_than_first",
                                         "corr_paired", "corr_paired_later_month",
                                         "corr_unpaired", "corr_rows_with_new_owner", "corr_targets", "corr_targets_sh_changed",
                                         "corr_targets_px_changed", "amend_new_rows", "amend_new_rows_v1", "corr_from_cache")}
            for y, v in sorted(st_clean.items())}
    dcorr = {y: {k: v.get(k, 0) for k in ("dcorr_rows", "dcorr_rows_S", "dcorr_rows_P", "dcorr_paired", "dcorr_paired_later_month",
                                          "dcorr_hist_year_change", "dcorr_hist_early", "dcorr_rows_with_new_owner",
                                          "dcorr_targets", "dcorr_no_orig", "dcorr_from_cache", "dcorr_cache_target_missing")}
             for y, v in sorted(st_clean.items())}
    doc = {"note": "§A 내부자 PIT 백필 밀도 보고서 — 개수·밀도만(수익 없음). 규칙은 build/ins_pit_build.py 머리말. "
                   "월 OS·RS 종목 수는 분류가 필요해 xcheck_r1.json(r_r1_flags.py 가 이 패널로 센다)에 싣는다.",
           "generated": _now(), "pins": pins, "inputs": R["inputs"],
           "regex": {"stc": STC_RX.pattern, "stc_v1_audit": STC_RX_V1.pattern, "plan": PLAN_RX.pattern, "neg": NEG_RX.pattern,
                     "shared_from": "build/r_r1_flags.py"},
           "calendar": {"rule": "refresh_events._holidays + ADHOC · 가용일 = FILING_DATE 다음 거래일", "vs_observed": calchk},
           "world": {"groups": len(M.doc["groups"]), "ciks": len(M.c2g), "fpi_flag": M.fpi_field},
           "panel_files": files, "panel_rows": len(rows), "raw_rows": len(raw),
           "stc_rule_change_2026_09_25": {"rule": "'non-discretionary' → '%s' (r_r1_flags 선언 p)" % R1.STC_ND,
                                          "by_filing_year": stc_chg,
                                          "total": {k: sum((v[k] or 0) for v in stc_chg.values()) for k in next(iter(stc_chg.values()))}},
           "corrections_4a_2026_09_25": {"rule": "r_r1_flags 선언 q · 머리말 6b — corr_rows = 사건에서 뺀 4/A 행(제출 연도) · "
                                                 "corr_rows_later_month_than_first = 그 거래 키를 처음 알린 제출보다 뒤 가용월(검토 정의) · "
                                                 "corr_paired_later_month = 짝지은 원 행보다 뒤 가용월(옛 규칙이면 그달 새 사건) · "
                                                 "corr_targets = 값이 고쳐진 원 행(원 행 제출 연도) · 🔒 2026-09-26: 원 행 sh · px · usd 는 "
                                                 "제출된 그대로(등록 1차) · 고친 값은 shc · pxc · usdc(선언된 민감도 T1C) · "
                                                 "amend_new_rows = 사건인 4/A 행(cnt = 1 · 2026-09-26 정의 수정 — 검토 지적) · "
                                                 "amend_new_rows_v1 = 옛 정의(정정 행이 아닌 남은 4/A 행 · 세지 않는 부분 중복 포함)",
                                         "by_filing_year": corr,
                                         "total": {k: sum(v[k] for v in corr.values()) for k in next(iter(corr.values()))}},
           "date_corrections_4a_2026_09_26": {"rule": "r_r1_flags 선언 q2 · 머리말 6c — dcorr_rows = 거래일만 고친 4/A 행(사건 아님 · 4/A 제출 "
                                                      "연도) · dcorr_paired_later_month = 원 행보다 뒤 가용월(옛 규칙이면 그달 새 사건) · "
                                                      "dcorr_hist_year_change = 고친 거래일이 다른 해(분류 이력의 해가 바뀐다) · "
                                                      "dcorr_hist_early = 원 행 가용일과 4/A 가용일 사이에 분류일(1월 첫 거래일)이 낀 짝(그 분류일은 "
                                                      "고친 거래일을 먼저 쓴다 — 선언) · dcorr_targets = 거래일이 고쳐진 원 행(원 행 제출 연도) · "
                                                      "dcorr_no_orig = DATE_OF_ORIG_SUB 가 없어 거래일 정정을 볼 수 없던 4/A 행",
                                              "by_filing_year": dcorr,
                                              "total": {k: sum(v[k] for v in dcorr.values()) for k in next(iter(dcorr.values()))}},
           "totals": dict(sorted(tot.items())), "quarters": qstats}
    doc.update(D)
    IM._wj_stable(DENS, doc, indent=1)
    print("→ 패널 %d 행 · %d 파일 %.1fMB · density.json %.0fKB · 새로 읽은 분기 %d · %.0fs"
          % (len(rows), len(files), sum(v["bytes"] for v in files.values()) / 1e6, os.path.getsize(DENS) / 1024, n_new,
             time.time() - t0))
    return doc


# ════════════════════════════════════════════════════════════════════════
# xcheck — r_r1_flags.py(표지·분류 한 곳) 대 이 패널: 식 · 원 행 · 정리 · 정정 대조 + 월 OS·RS 종목 수(개수만) + 분류 수 조정
# ════════════════════════════════════════════════════════════════════════
HIST_RULE = [
    "단위 (보고자 CIK, 발행사 그룹) · 항목 (거래일, 가용일) · 분류일 D_Y 에 가용일 ≤ D_Y · 거래 연도 Y−3..Y−1 인 항목만 센다.",
    "행 = r_r1_flags.prepare 를 통과한 Form 4 · 4/A 의 P · S 행(코드·A/D·날짜·보고자 거르기 뒤) · Form 5 는 없다.",
    "강제 매도 행(stc — 등록 식 · 선언 p)은 1차 이력에서 뺀다(T6 이력만 넣는다).",
    "cnt = 1 행: 행의 모든 보고자(관계를 거르지 않는다 — 'Other' 만 · 관계 칸 빈 보고자 포함 · 선언 d).",
    "cnt = 0 부분 중복 행(10인 상한으로 쪼갠 공동 제출 · 보고자를 더한 정정본): own(새 보고자)만 · odup 는 앞선 같은 여섯 칸 키 제출이 이미 싣는다.",
    "4/A 정정 행(corr = 2): ocor(정정 보고자)는 넣지 않는다 — 원 행이 원 가용일로 싣는다 · own(새 보고자)만.",
    "정정된 원 행(corr = 1): 그대로(거래일 · 가용일 · 보고자 불변 — 이력은 수량·단가를 보지 않는다).",
    "거래일 정정 행(corr = 3 · 선언 q2): ocor(겹친 보고자)는 넣지 않는다 · own(새 보고자)만(그 4/A 의 거래일 · 가용일).",
    "거래일이 고쳐진 원 행(tdh): 고친 거래일(tdh[0]) · 원 행 가용일 · 원 행 보고자로 넣는다(원래 거래일은 넣지 않는다).",
    "여섯 칸 키가 같은 중복 행: 지워져 없다(첫 공시만).",
]


def _key(r):
    return (r["acc"], str(r["sk"]))


def _cmp_prepared(prep, recs):
    """prepare 결과(정본 행) 대 패널 레코드(load_panel) — 행 집합 · 가용일 · cnt · corr · 정정 뒤 값 · 짝 · 세는 보고자."""
    pm = {_key(r): r for r in recs}
    got = {(r.acc, r.sk): r for r in prep}
    d = collections.Counter()
    ex = []
    for k, r in got.items():
        p = pm.get(k)
        if p is None:
            continue
        for f, a, b in (("avail", r.avail, p["av"]), ("count", bool(r.count), bool(p["cnt"])), ("corr", r.corr or 0, p["corr"] or 0),
                        ("shares_eff", _k6(r.shares), _k6(p["shares_eff"])), ("price_eff", _k6(r.price), _k6(p["price_eff"])),
                        ("shares_c", _k6(r.shc), _k6(p["shares_c"])), ("price_c", _k6(r.pxc), _k6(p["price_c"])),
                        ("tdh", [str(x) for x in r.tdh] if r.tdh else None, [str(x) for x in p["tdh"]] if p.get("tdh") else None),
                        ("ctgt", [str(x) for x in r.ctgt] if r.ctgt else None,
                         [str(x) for x in p["ctgt"]] if p.get("ctgt") else None),
                        ("own", sorted(c for c, _ in r.owners), sorted(c for c, _ in p["own_bits"])),
                        ("stc", bool(r.stc), bool(p["stc"])), ("stc_v1", bool(r.stc_v1), bool(p["stc_v1"]))):
            if f == "ctgt" and (r.corr or 0) not in (2, 3):
                continue
            if a != b:
                d["diff_" + f] += 1
                if len(ex) < 10:
                    ex.append([k[0], k[1], f, str(a)[:60], str(b)[:60]])
    return {"panel_rows": len(recs), "kept_by_prepare": len(got), "panel_only": len(set(pm) - set(got)),
            "prepare_only": len(set(got) - set(pm)), "diff": dict(d), "examples": ex}


def _r1_density(B, M, R):
    """월 OS·RS 종목 수(r_r1_flags 1차 판) — Stage M 세계(등록 FPI 표지) · 사양 칸 세계 · s16 멤버. 개수만."""
    F = B["flags"]["primary"]
    mem = M.members(R)
    bym = {}
    for ym in sorted(B["months_ok"]):
        m = mem.get(ym)
        if not m:
            continue
        rec = {}
        for nm in ("s16", "sm", "sm_spec"):
            gs = m[nm]
            if not gs:
                continue
            if nm == "sm_spec" and gs == m["sm"]:
                continue
            os_ = [F.dummy(g, ym, "OS") for g in gs]
            rs_ = [F.dummy(g, ym, "RS") for g in gs]
            rec[nm] = {"n": len(gs), "OS": sum(1 for x in os_ if x == 1), "RS": sum(1 for x in rs_ if x == 1),
                       "OS_none": sum(1 for x in os_ if x is None), "ALL": sum(1 for g in gs if F.dummy(g, ym, "ALL") == 1)}
        bym[ym] = rec

    def f0(nm):
        ms = [ym for ym in bym if (nm in bym[ym]) or (nm == "sm_spec" and "sm" in bym[ym])]
        get = lambda ym: bym[ym].get(nm) or bym[ym]["sm"]
        osn = [get(ym)["OS"] for ym in ms]
        rsn = [get(ym)["RS"] for ym in ms]
        return {"months": [ms[0], ms[-1], len(ms)] if ms else None, "member_group_months": sum(get(ym)["n"] for ym in ms),
                "OS_median": _med(osn), "OS_min": min(osn) if osn else None,
                "OS_min_month": ms[osn.index(min(osn))] if osn else None,
                "RS_median": _med(rsn), "RS_min": min(rsn) if rsn else None,
                "pass": bool(osn) and _med(osn) >= 20 and min(osn) >= 5 and _med(rsn) >= 10,
                "rule": "OS 중앙값 ≥ 20 · 최소 ≥ 5 · RS 중앙값 ≥ 10 (R1 params F0)"}
    return f0("sm"), f0("sm_spec"), bym


def _cls_by(H, cal, years):
    tab = H.table(years)
    out = {}
    for j, Yr in enumerate(years):
        cnt = collections.Counter(s[j] for s in tab.values())
        out[str(Yr)] = {"D": cal.first_td(Yr), "R": cnt["R"], "O": cnt["O"], "U": cnt["U"], "N": cnt["N"],
                        "late_excluded": H.late(Yr)}
    return out, tab


def _reconcile(B, cal, years):
    """검토 재계산(2014 R 729 · O 1,625) 대 r_r1_flags(모든 보고자) — 이력을 내부자 관계 보고자에게만 붙이면 어떻게 되나.
    쌍 분해: 사라지는 쌍(내부자 이력만으로는 3년 중 빈 해가 생기거나 이력이 없다) · 라벨이 바뀌는 쌍. 표지 행 라벨 차이(개수만)."""
    H = B["hist"][True]
    full_cls, tab = _cls_by(H, cal, years)
    ins_rows = []
    for r in B["rows"]:
        ow = tuple((c, rel) for c, rel in r.owners if R1.is_insider(rel))
        if ow:
            ins_rows.append(r.copy(owners=ow))
    H2 = R1.History(ins_rows, cal, True)
    ins_cls, tab2 = _cls_by(H2, cal, years)
    dec = {}
    for j, Yr in enumerate(years):
        gone, relab = collections.Counter(), collections.Counter()
        for k, s in tab.items():
            a = s[j]
            if a not in "RO":
                continue
            b = tab2.get(k, "-" * len(years))[j]
            if b == "-":
                gone[a] += 1
            elif b != a:
                relab[a + ">" + b] += 1
        dec[str(Yr)] = {"all_reporters": {"R": full_cls[str(Yr)]["R"], "O": full_cls[str(Yr)]["O"]},
                        "insider_only": {"R": ins_cls[str(Yr)]["R"], "O": ins_cls[str(Yr)]["O"]},
                        "pairs_without_insider_history": dict(gone), "pairs_relabelled": dict(relab)}
    # 표지 행(세는 · 내부자 · 강제 매도 아닌 매도) 라벨이 두 정의에서 갈리는 수(가용 연도별)
    lab = collections.defaultdict(collections.Counter)
    for r in B["rows"]:
        if not r.count or r.code != "S" or r.stc:
            continue
        elig = [c for c, rel in r.owners if R1.is_insider(rel)]
        if not elig:
            continue
        a = R1._label([H.cls(c, r.gid, r.ty()) for c in elig])
        b = R1._label([H2.cls(c, r.gid, r.ty()) for c in elig])
        v = lab[r.ym[:4]]
        v["rows"] += 1
        if a != b:
            v["differ"] += 1
            v[a + ">" + b] += 1
    return {"cause": "검토 재계산은 분류 이력을 그 행에서 내부자 관계(Director · Officer · TenPercentOwner 비트)가 있는 보고자에게만 "
                     "붙였다. 사양(«분류 이력에는 그 제출의 모든 보고자에게 붙인다») · r_r1_flags 선언 d 는 관계를 거르지 않는다. "
                     "insider_only 판이 검토 수를 그대로 재현한다 — 차이는 모두 이 거르기에서 온다.",
            "which_is_right": "all_reporters(r_r1_flags · 사양 문구). insider_only 는 다른 정의다 — 버그가 아니다. 표지에 쓰이는 라벨은 "
                              "내부자 관계 보고자의 것뿐이지만 그들의 이력에는 관계가 'Other' 로 적힌 행도 사양대로 들어간다.",
            "by_year": dec, "flag_row_labels_by_avail_year": {y: dict(v) for y, v in sorted(lab.items())}}


def _hist_counts(B):
    """이력에 들어간 · 빠진 (보고자, 행) 항목 수 — 규칙 HIST_RULE 의 개수판(1차 · stc 제외)."""
    c = collections.Counter()
    for r in B["rows"]:
        if r.stc:
            c["excluded_stc_row_owner_entries"] += len(r.owners) + len(r.ocor or ())
            continue
        if r.corr == 2:
            c["corr_row_new_owner_entries_in"] += len(r.owners)
            c["corr_row_ocor_entries_not_attached"] += len(r.ocor or ())
        elif r.corr == 3:
            c["dcorr_row_new_owner_entries_in"] += len(r.owners)
            c["dcorr_row_ocor_entries_not_attached"] += len(r.ocor or ())
        elif r.count:
            c["count1_owner_entries_in"] += len(r.owners)
        else:
            c["count0_partial_new_owner_entries_in"] += len(r.owners)
            c["count0_partial_odup_entries_not_attached"] += len(r.odup or ())
        c["corr1_rows_in"] += 1 if r.corr == 1 else 0
        c["tdh_rows_in_with_corrected_tdate"] += 1 if r.tdh else 0
    return dict(sorted(c.items()))


def cmd_xcheck(quarters_=None):
    t0 = time.time()
    M = Map()
    man = IM.ins_manifest()
    dens = _rj(DENS) or {}
    out = {"note": "build/r_r1_flags.py(분류·표지 한 곳) 대 이 패널 — 개수만(수익 없음). r_r1_flags_sha256 = 이 대조를 돌린 판 · "
                   "panel_pins = 패널을 만든 판(density.json pins). 두 판이 같아야 커밋한다.",
           "generated": _now(), "r_r1_flags_sha256": _sha_file(R1.__file__), "ins_pit_build_sha256": _sha_file(os.path.abspath(__file__)),
           "panel_pins": dens.get("pins"), "panel_files": dens.get("panel_files"),
           "pins_consistent": ((dens.get("pins") or {}).get("r_r1_flags") == _sha_file(R1.__file__)
                               and (dens.get("pins") or {}).get("script") == _sha_file(os.path.abspath(__file__)))}
    out["regex_same"] = {"stc": R1.STC_RX.pattern == STC_RX.pattern, "stc_v1": R1.STC_RX_V1.pattern == STC_RX_V1.pattern,
                         "plan": R1.PLAN_RX.pattern == PLAN_RX.pattern, "neg": R1.NEG_RX.pattern == NEG_RX.pattern,
                         "shared_object": STC_RX is R1.STC_RX, "stc": R1.STC_RX.pattern}
    # 1 원 행: 그쪽 DERA 읽기(ZIP 직접 · 각주 CSV 따옴표를 풀지 않는다) 대 이쪽 원 행 캐시(Form 4 · 4/A) — (acc, sk) 와 칸
    qs = quarters_ or quarters()
    diff = collections.Counter()
    ex = []
    for key in qs:
        theirs, _ = R1.rows_from_dera(zip_path(key, man), M.c2g, keep_text=False)
        mine, _, _ = load_or_parse(key, M, man, (_rj(CMAN) or {}).get("files", {}), lean=True)
        mi = {(r["acc"], str(r["sk"])): r for r in mine if r["doc"] in FORMS4}
        th = {(r.acc, r.sk): r for r in theirs}
        diff["mine_only"] += len(set(mi) - set(th))
        diff["theirs_only"] += len(set(th) - set(mi))
        for k in sorted(set(mi) & set(th)):          # 예시 목록이 해시 순서에 매이지 않게
            a, b = mi[k], th[k]
            for f, va, vb in (("fdate", a["fdate"], b.fdate), ("tdate", a["tdate"], b.tdate), ("code", a["code"], b.code),
                              ("shares", _k6(a["shares"]), _k6(b.shares)), ("price", _k6(a["price"]), _k6(b.price)),
                              ("gid", a["gid"], b.gid), ("stc", bool(a["stc"]), bool(b.stc)),
                              ("stc_v1", bool(a["stc_v1"]), bool(b.stc_v1)),
                              ("p10_rx", bool(a["p10_rx"]), bool(b.p10_rx)), ("aff", a["aff"], b.aff),
                              ("owners", sorted(c for c, _ in a["owners"]), sorted({c for c, _ in b.owners})),
                              ("rels", sorted((c, _bits(x)) for c, x in a["owners"]),
                               sorted({(c, _bits(x)) for c, x in b.owners}))):
                if va != vb:
                    diff["field_" + f] += 1
                    if len(ex) < 20:
                        ex.append([key, k[0], k[1], f, str(va)[:80], str(vb)[:80]])
        diff["compared"] += len(set(mi) & set(th))
        del theirs, mine, mi, th
        print("  %s 원 행 대조 누적 %d" % (key, diff["compared"]), flush=True)
    out["raw_rows"] = {"quarters": [qs[0], qs[-1], len(qs)], "diff": dict(diff), "examples": ex}
    cal1 = R1.Cal()
    # 3 그쪽 prepare(원 행 전체 · 캐시 짝 없이 처음부터) 대 이쪽 clean — 같은 행 · cnt · corr · 짝 · 정정 뒤 값
    #   (메모리 — 분기마다 정본 행으로 바꿔 사전을 버리고, 패널은 그 뒤에 읽는다)
    allrows = []
    for key in quarters():
        rs, _, _ = load_or_parse(key, M, man, (_rj(CMAN) or {}).get("files", {}), lean=True)
        allrows.extend(R1.rows_from_records([r for r in rs if r["doc"] in FORMS4]))
        del rs
    th_prep, th_st = R1.prepare(allrows, cal1)
    del allrows
    recs = load_panel()
    out["prepare_from_raw_vs_panel"] = dict(_cmp_prepared(th_prep, recs), their_stats=th_st)
    del th_prep
    # 2 정리 멱등: 패널(load_panel — 원 보고자 · 처음 값 · 정정 짝 캐시)을 그쪽 prepare 에 다시 넣으면 같은 행 · cnt · corr · 값
    B = R1.build(R1.rows_from_records(recs), cal1, variants=("primary",))
    out["prepare_idempotent"] = dict(_cmp_prepared(B["rows"], recs), prepare_stats=B["prep"])
    # 4 월 OS·RS 종목 수(그쪽 분류 · 1차 판) — Stage M 세계(등록 FPI 표지 fpi_q) · 사양 칸 세계 · s16 멤버
    R = IM.load_refs()
    f0, f0_spec, bym = _r1_density(B, M, R)
    years = list(range(2011, 2027))
    cls_by, _ = _cls_by(B["hist"][True], cal1, years)
    F = B["flags"]["primary"]
    yr = {}
    for y, c in sorted(F.by_year.items()):
        tot = c["O"] + c["R"] + c["U"] + c["N"]
        yr[y] = {"S_rows_labeled": tot, "O": c["O"], "R": c["R"], "U": c["U"], "N": c["N"],
                 "U_share": round(c["U"] / tot, 4) if tot else None, "stc_x": c["stc_x"],
                 "stc_x_rate": round(c["stc_x"] / (tot + c["stc_x"]), 4) if (tot + c["stc_x"]) else None,
                 "stc_x_v1": c["stc_x_v1"], "stc_v1_only_kept": c["stc_v1_only"], "corr_S": c["corr_S"],
                 "joint": c["joint"], "joint_split": c["joint_split"]}
    out["r1_density"] = {
        "rule": "r_r1_flags.build(primary) 을 이 패널에 — OS/RS = 그달 가용된 기회주의/루틴 매도 ≥ 1(공동 제출 라벨 %s). "
                "sm = Stage M 세계(%s..%s · 비금융 · Section 16(등록 FPI 표지 %s) · 지도 F0 통과) · sm_spec = 같은 세계를 사양 칸 fpi 로 · "
                "s16 = Section 16 적용 멤버 그룹." % (R1.JOINT_RULE, STAGE_M[0], STAGE_M[1], M.fpi_field),
        "f0_stage_m": f0, "f0_stage_m_spec_fpi": f0_spec,
        "classification_by_year": cls_by, "labels_by_avail_year": yr, "by_month": bym}
    # 5 분류 수 조정(검토 729/1,625 대 735/1,651) · 6 이력 규칙
    out["reconcile_classification"] = _reconcile(B, cal1, list(range(2014, 2027)))
    out["classification_history_rows"] = {"rule": HIST_RULE, "counts": _hist_counts(B)}
    del B
    # 6b 선언 q2 앞의 규칙 재현(2026-09-25 판 — 거래일 정정 없음) — corr = 3 행 cnt := 1(지운 보고자 없으면) · 보고자 own + ocor ·
    #    corr · ctgt 를 비워 짝을 다시 찾지 않게 · prepare(date_corrections=False)
    r2 = [dict(r, cnt=None, corr=None, ctgt=None) if r["corr"] == 3 else r for r in recs]
    B2 = R1.build(R1.rows_from_records(r2), cal1, variants=("primary",), date_corrections=False)
    f02, _, _ = _r1_density(B2, M, R)
    cl2, _ = _cls_by(B2["hist"][True], cal1, [2014, 2026])
    out["round2_rule_reproduction"] = {
        "rule": "선언 q2(거래일 정정) 앞의 규칙 — 패널 corr = 3 행을 corr · ctgt · cnt 없음(prepare 가 다시 판정 — 지운 보고자가 없으면 새 사건)으로 "
                "돌리고 r_r1_flags.build(date_corrections=False). 2026-09-25 xcheck(r_r1_flags 1a74a109) 값: Stage M OS 중앙값 68 · 최소 25 · "
                "RS 중앙값 57 · 4/A 새 사건 행 528(옛 정의 · 사건 행 510).",
        "rows": len(B2["rows"]), "prep": {k: B2["prep"].get(k, 0) for k in ("kept", "amend_new_rows", "amend_new_rows_v1", "corr_rows",
                                                                         "corr_targets", "dcorr_rows", "count_false")},
        "f0_stage_m": {k: f02[k] for k in ("months", "OS_median", "OS_min", "RS_median", "RS_min")},
        "classification": {y: {k: v[k] for k in ("R", "O", "U")} for y, v in cl2.items()}}
    del B2, r2
    # 7 옛 규칙 재현(감사 칸만으로) — cnt6 · stc_v1 · 제출된 그대로의 값 · 원 보고자 · 정정 없음(prepare corrections=False)
    old = [dict(r, cnt=r["cnt6"], stc=r["stc_v1"], corr=None, ctgt=None) for r in recs]
    Bo = R1.build(R1.rows_from_records(old), cal1, variants=("primary",), corrections=False)
    del old
    f0o, _, _ = _r1_density(Bo, M, R)
    clo, _ = _cls_by(Bo["hist"][True], cal1, [2014, 2026])
    out["old_rule_reproduction"] = {
        "rule": "패널 감사 칸만으로 수정 전 규칙을 다시 만든다 — cnt := cnt6 · stc := stc_v1 · 값은 제출된 그대로(sh · px) · 보고자 own + odup + ocor · "
                "r_r1_flags.build(corrections=False). 수정 전 xcheck(2026-09-25T08:38Z · r_r1_flags dabf312e) 값과 같아야 한다: "
                "행 472,497 · Stage M OS 중앙값 68 · 최소 25 · RS 중앙값 57 · 2014 R 735 · O 1,651 · 2026 R 517 · O 920.",
        "rows": len(Bo["rows"]), "prep": Bo["prep"], "f0_stage_m": {k: f0o[k] for k in ("months", "OS_median", "OS_min", "RS_median")},
        "classification": {y: {k: v[k] for k in ("R", "O", "U")} for y, v in clo.items()}}
    del Bo, recs
    IM._wj_stable(XCHK, out, indent=1)
    print("→ %s · 원 행 차이 %s · 멱등 %s · 원 행 prepare 대 패널 %s · Stage M OS 중앙값 %s 최소 %s · RS 중앙값 %s · 옛 규칙 %s (%.0fs)"
          % (os.path.relpath(XCHK, ROOT), dict(diff), out["prepare_idempotent"]["diff"] or "0",
             out["prepare_from_raw_vs_panel"]["diff"] or "0", f0["OS_median"], f0["OS_min"], f0["RS_median"],
             out["old_rule_reproduction"]["f0_stage_m"], time.time() - t0))
    return out


# ════════════════════════════════════════════════════════════════════════
# flags — cikmonth.json · routine.json(§A 출력 b · c) — r_r1_flags 로 이 패널에서(개수만)
# ════════════════════════════════════════════════════════════════════════
CIKM = os.path.join(OUTD, "cikmonth.json")
ROUT = os.path.join(OUTD, "routine.json")


def cmd_flags():
    t0 = time.time()
    M = Map()
    dens = _rj(DENS) or {}
    pins = {"r_r1_flags": _sha_file(R1.__file__), "ins_pit_build": _sha_file(os.path.abspath(__file__)), "issuer_map": M.sha,
            "panel": {k: v["sha256"] for k, v in (dens.get("panel_files") or {}).items()}, "panel_pins": dens.get("pins")}
    if (dens.get("pins") or {}).get("r_r1_flags") != pins["r_r1_flags"] or (dens.get("pins") or {}).get("script") != pins["ins_pit_build"]:
        raise SystemExit("🚨 패널(density.json pins)이 다른 r_r1_flags · ins_pit_build 판으로 만들어졌다 — build 를 먼저")
    for k, v in pins["panel"].items():
        if _sha_file(os.path.join(ROOT, k)) != v:
            raise SystemExit("🚨 패널 파일 %s 가 density.json 의 해시와 다르다 — build 를 먼저" % k)
    B = R1.build(R1.rows_from_records(load_panel()), R1.Cal())
    cm = R1.cikmonth_doc(B)
    cm = dict({"generated": _now(), "pins": pins, "prep": B["prep"]}, **cm)
    IM._wj_stable(CIKM, cm)
    H = B["hist"][True]
    rd = R1.routine_doc(H, range(H.y0, int(DATA_END[:4]) + 1))
    rd = dict({"generated": _now(), "pins": pins}, **rd)
    IM._wj_stable(ROUT, rd)
    ncell = sum(len(v) for v in cm["groups"].values())
    print("→ %s %.1fMB (그룹 %d · 칸 %d · months_ok %s..%s) · %s %.1fMB (키 %d) (%.0fs)"
          % (os.path.relpath(CIKM, ROOT), os.path.getsize(CIKM) / 1e6, len(cm["groups"]), ncell, cm["months_ok"][0],
             cm["months_ok"][-1], os.path.relpath(ROUT, ROOT), os.path.getsize(ROUT) / 1e6, len(rd["cls"]), time.time() - t0))
    return cm, rd


# ════════════════════════════════════════════════════════════════════════
def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "check":
        IM.cmd_check()
    elif cmd == "fetch":
        cmd_fetch(remote="--remote" in argv)
    elif cmd == "build":
        cmd_build()
    elif cmd == "xcheck":
        qs = [a for a in argv[2:] if re.fullmatch(r"\d{4}q\d", a)]
        cmd_xcheck(qs or None)
    elif cmd == "flags":
        cmd_flags()
    elif cmd == "all":
        IM.cmd_check()
        cmd_fetch(remote="--remote" in argv)
        cmd_build()
        cmd_xcheck()
        cmd_flags()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
