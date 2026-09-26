#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§A0 날짜 인식 발행사 지도 + §B Section 16 적용(FPI) 표지 — data/_issuer_map.json

무엇을·왜.
  RBATCH(R1 기회주의 내부자 매도 · R2 10-Q 위험요인 개정 · R5 경보) 의 모든 조인은 «그달 그 티커가 어느 SEC 등록 법인
  (CIK)이었나» 에 걸린다. 그런데 랩에 있던 지도는 둘 다 날짜를 모른다 —
    · data/index_history.json 의 cik 는 티커 → **마지막으로 본** CIK 하나(평면 지도)이고,
    · cik_hist 는 CIK → 티커 목록일 뿐 **선행 CIK** 를 담지 않는다.
  비평 실측(2016Q3 DERA 대 2016-08 명단): 평면 지도의 CIK 로는 Form 4 가 0건이고 다른(선행) CIK 로만 제출된 멤버가
  15종이었다(DIS 1001039 · CI 701221 · AVGO 1649338 · DOW 29915 · DD 30554 · FOX/FOXA 1308161 · MYL · WRK · XRX …).
  XOM 은 평면 지도 CIK 2115436(2026-07 지주사)으로는 창 전체가 0건이다 — 실제 제출은 34088 에서 나온다.
  그러면 OS=RS=0 이 거짓으로 찍히고, §B 제출 목록·§C 10-Q 짝·CMP 분류 이력이 조용히 끊긴다.

  그래서 (티커, 월) → 발행사 그룹과 그달의 CIK 집합을 만든다. 그룹은 지주사 재편·재설립처럼 **같은 경제적 발행사**의
  선행 CIK 와 후계 CIK 를 이은 것이다(분할·피인수·다른 회사로 넘어간 티커는 잇지 않는다 — 아래 «잇기 규칙»).

증거(셋, 우선순위 순).
  ① DERA Insider Transactions Data Sets 의 SUBMISSION 표 (ISSUERCIK, ISSUERTRADINGSYMBOL, ISSUERNAME, FILING_DATE)
     — 2011Q1..2026Q2 분기 ZIP. 제출자가 **그때** 적은 티커라 날짜를 안다. Form 3/3A/4/4A/5/5A 만 센다.
  ② EDGAR submissions(data.sec.gov) — 현재 tickers, 이름 이력(formerNames 의 from/to), 제출 기간, 연차보고 서식.
  ③ 위키 과거 리비전 — index_history.json(name · cik · cik_hist · cik_names · cik_conflicts) 과
     pit_gics_sectors.json 의 **월별** CIK 열(SPX 만 · 편집 지연 있음 → 약한 증거).
  후보가 둘 이상이거나 이름이 맞지 않으면 data/_issuer_map_manual.json(수작업 검증 목록)에 올린다 — 해결값은 그 파일이 정한다.

(티커, 월) 결정 규칙(미리 고정).
  1. DERA 티커 몫: 명단 티커 T(정규화 = 영숫자만 대문자)로 제출된 Form 3/4/5 를 창 [m−k, m] (k = 0, 1, 3, 6, 12 차례)에서
     세어 합계 ≥ 3 이 되는 첫 창을 쓴다. 뒤쪽 창이 비면 [m−k, m+k] 로 한 번 더 본다. 몫 ≥ 0.20 인 CIK 가 후보다.
     잡음 거르기: 이름이 명단 이름과 맞거나 닻인 후보가 하나라도 있으면 둘 다 아닌 후보(제출자가 남의 티커를 적은 것 —
     O → Northern Oil · A → Baldwin & Lyons · PCG → 자회사 유틸리티)는 몫에서 뺀다. 전부 잡음이면 이름이 맞는 산 닻으로 간다.
     자기 티커로 증거가 없으면 그달 같은 닻(company_tickers · cik_map · 위키 평면 CIK — cik_conflicts 제외)을 공유하는
     형제 클래스 티커의 증거를 빌린다(FOXA ← FOX · GOOGL ← GOOG · NWSA ← NWS).
  2. DERA 증거가 없으면(FPI · 신규 상장 · 제출자가 다른 표기를 쓴 경우) 닻 후보: 위키 월별 CIK · 위키 평면 CIK ·
     cik_map.json · SEC company_tickers.json · edgar.PREDECESSOR · 수작업 anchor. 그달 앞뒤 18개월 안에 EDGAR 제출이
     있는 것만 산다. DERA 끝(2026-06) 뒤의 달은 DERA 에 없던 **새** 닻 CIK 의 submissions Form 3/4/5 도 후보로 센다
     (submissions 에는 그 CIK 가 보고자인 제출도 섞이므로 옛 CIK 에는 이 경로를 쓰지 않는다).
  3. 후보들이 한 그룹으로 모이면 자동(깨끗한 넘겨받기 — 옛 그룹의 이 티커 마지막 제출이 새 주 CIK 첫 제출 + 45일 안 — 도
     자동). 이름이 맞지 않거나 그룹이 둘 이상이면 수작업 목록의 resolve 가 정한다. 없으면 그 멤버-월은 해결 못 한 채로
     남긴다(조용히 채우지 않는다). 명단 이름 칸이 빈 티커(NDX 전용)는 noref 대기열로 사람이 이름을 본다.
  4. 그달 CIK 집합 = 그룹의 CIK 가운데 효력 구간이 그달과 겹치는 것. 주 CIK = 그 티커로 월말까지 가장 늦게 제출을 시작한 후보.
     효력 구간은 그룹 안 CIK 사이의 경계만 긋는다 — 가장 이른 CIK 는 앞이, 가장 늦은 CIK 는 뒤가 열린다(null).
     그룹 이름 = 멤버-월에서 가장 자주 주 CIK 였던 CIK(g<CIK>).

잇기 규칙(선행 → 후계, 미리 고정).
  같은 티커의 DERA 주 CIK 가 A → B 로 바뀐 지점을 모두 찾아(«전환» — 첫 멤버월 전 2011-01 부터 본다: 분류 이력 3년이
  창 앞으로 닿기 때문에 ETN 2012 · PRGO 2013 같은 창 이전 재편도 잡는다) 다음 셋을 본다.
    B 신규   : B 의 첫 Form 3/4/5(아무 티커) 가 전환 12개월 전보다 뒤이고, 전환 6개월 전까지 다른 티커로 5건 이상 낸 적이 없다.
    A 소멸   : A 의 마지막 Form 3/4/5(아무 티커) 가 전환 6개월 뒤보다 앞이다.
    이름     : A·B 이름(EDGAR 이력 + DERA) 이 맞는다.
  셋 다 참이면 «잇기 후보»(지주사 재편·재설립·인버전·티커를 이어받은 합병 지주사). 하나라도 거짓이면 잇지 않는다
  (티커가 다른 기존 회사로 넘어감 · 분할 신설사가 티커를 가져감 · A 가 다른 티커로 계속 살아 있음).
  잇기 후보와 명단 이웃 전환(티커가 바뀌며 새 CIK 로 넘어간 경우) 은 모두 수작업 목록에서 확인·결정한다 —
  결정(splice / separate)과 근거가 그 파일에 남는다. 자동 판정은 제안일 뿐이다(SNDK · FOX 는 자동이 splice 라 했지만
  재사용 티커 · 분할 신설사라 separate 로 뒤집었다). 결정 기준은 _issuer_map_manual.json 의 rules 에 적었다.

수작업 목록 키 — splice(선행·후계 결정) · resolve((티커, 구간) → 주 CIK) · exclude((티커, 구간)에서 뺄 CIK) ·
  anchor(회사 검색으로 찾은 닻) · alias(티커 별칭) · sibling(형제 클래스 묶음) · name_ok(이름 대조 통과) ·
  verified(대기열 항목 확인 — 위키 편집 지연 · 파싱 사고).

§B Section 16 적용 표지(FPI).
  멤버-월 m 마다 그룹 CIK 들의 **직전 연차보고**(filingDate ≤ m 말, 원본 10-K · 10-K405 · 10-KT · 20-F · 40-F)가
  20-F 나 40-F 면 fpi=1(외국 사적발행인 · Section 16 비적용), 10-K 계열이면 0. 연차보고가 아직 없으면 직전 정기보고
  (10-Q → 0 · 6-K → 1)로, 그것도 없으면 18개월 안 등록서식·수시공시(S-1 · S-4 · 10-12B · 8-K → 0 · F-1 · F-4 → 1)로,
  그것도 없으면 null(모름 — FDIC 제출 은행 FRC · SBNY). 표지 fpi_q 는 20-F 뒤 10-Q 를 냈으면(미국 재설립 ·
  FPI 지위 상실 — TEAM 2022-11 · NXPI 2019-10) 그달부터 0 이다. 🚨 등록 권고(2026-09-25) = fpi_q(FPI_REGISTERED · 문서의
  fpi_registered) — 사양 규칙은 이미 10-Q 를 낸 TEAM 2022-11..2023-07 · NXPI 2019-10..2020-01(13 멤버-월)을 떨어뜨린다.
  F0 와 Stage M 요약은 등록 표지로 세고 사양 칸으로 센 것을 옆에 싣는다(f0.spec_flag · coverage.fpi_registered_vs_spec).
  사양 칸(tm 5 번)은 지우지 않는다 — 읽는 쪽은 fpi_registered.tm_index 칸(7)을 쓴다.

섹터(sector_at — Stage M 비금융 판정). 위키 SPX GICS 표(PIT) → 수작업 표 data/_issuer_map_sector_manual.json(NDX 전용 ·
  편출 이름의 그때 GICS · 공개 지식 · 사내 DB 쓰지 않음) → index_history 섹터 · stocks.json 오늘 섹터(둘 다 비PIT 대체 —
  coverage.sector_sources 에 선언).
  ⚠ 한계 둘. (i) 10-K 를 내는 FPI(SHPG · SHOP)는 fpi=0 인데 Form 4 가 없다 — F0 위반 목록이 그것을 잡는다.
  (ii) 2026-03 부터 FPI 멤버 다수가 Form 3/4 를 낸다. 실측(DERA 2026Q1): 2026-03 Form 3 전체 7,937건(1·2월은 월 약
  1,300건)이고 FPI 멤버 16개사 앞 Form 3/4 115건(Form 3 110) 중 109건이 03-17·18 에 몰렸다 — FPI 이사·임원에게 Section 16(a) 보고를
  지우는 법(Holding Foreign Insiders Accountable Act · 2026-03-18 시행으로 알려짐 · 이 빌드에서 법령 원문은 확인하지
  않았다)과 시기가 맞는다. coverage 의 fpi_form345_2025_01_2026_02_vs_2026_03_on 에 종목별 건수를 싣는다.
  표지 정의는 사양대로 둔다(전방 §G 는 이 변화를 따로 다뤄야 한다).

F0(수익 없이).
  FPI 가 아닌 멤버-월마다 그달 CIK 집합(그룹)으로 직전 12개월(제출월 m−11..m)에 Form 3/4/5 가 1건 이상 있어야 한다.
  DERA 가 닿지 않는 달(2026-07~)은 submissions 의 Form 3/4/5 로 센다. 위반 목록을 싣고, 위반율 > 2% 인 달은 측정 불가.
  🚨 이 파일은 자료 빌드다 — 어떤 표지와 수익의 관계도 계산하지 않는다(P0·Stage M 은 등록 뒤).

SEC 접속 — 모든 요청이 build/edgar.py 를 거친다(초당 8회 · gzip · 백오프). 🚨 SEC_UA 환경변수가 없으면 실행을 거부한다
  (edgar.py 의 기본 UA 를 조용히 쓰지 않는다 — 어떤 연락처를 쓸지는 사용자가 정한다). UA 값은 어느 파일에도 적지 않는다.

원본 보관 — 큰 원본은 저장소 밖(RBATCH_RAW, 기본 %TEMP%/rbatch/raw)에 두고 sha256 으로 고정한다.
  DERA ZIP  → data/_ins_pit/manifest.json (§A ins_pit_build.py 와 공유 · 다시 받을 때 해시가 바뀌면 멈춘다)
  그 밖     → data/_issuer_map_manifest.json (submissions · company_tickers · 회사 검색 · 연차보고 목록)

사용:
    SEC_UA="이름 연락처" python build/issuer_map.py check        # index.json 1건 + submissions 1건 · HTTP 200 · gzip 확인
    SEC_UA=...            python build/issuer_map.py dera         # DERA ZIP 2011Q1..2026Q2 받기 · 고정 · SUBMISSION 집계
    SEC_UA=...            python build/issuer_map.py sub          # 후보 CIK 의 submissions(+과거 조각) · company_tickers
    SEC_UA=...            python build/issuer_map.py search       # 후보가 없는 티커의 EDGAR 회사 검색
    SEC_UA=...            python build/issuer_map.py build        # 지도 · 표지 · F0 · 커버리지 → data/_issuer_map.json
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 🚨 SEC_UA 가 없으면 거부한다 — edgar.py 는 없을 때 기본값으로 조용히 넘어가므로, import 전에 막는다.
if not (os.environ.get("SEC_UA") or "").strip():
    sys.exit("🚨 SEC_UA 환경변수가 없다 — SEC 요청의 User-Agent(이름 + 연락처)를 명시적으로 정해서 넘길 것. "
             "edgar.py 의 기본값은 쓰지 않는다.")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402

if edgar.UA != os.environ["SEC_UA"]:
    sys.exit("🚨 edgar.UA 가 SEC_UA 와 다르다 — edgar.py 가 환경변수를 읽지 않았다")

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RAW = os.environ.get("RBATCH_RAW") or os.path.join(tempfile.gettempdir(), "rbatch", "raw")
OUT = os.path.join(DATA, "_issuer_map.json")
MANUAL = os.path.join(DATA, "_issuer_map_manual.json")
MAN_IM = os.path.join(DATA, "_issuer_map_manifest.json")
MAN_INS = os.path.join(DATA, "_ins_pit", "manifest.json")
QUEUE = os.path.join(RAW, "_manual_queue.json")      # 수작업 대기열(빌드가 쓴다 · 저장소 밖)

DERA_INDEX = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
Q0, Q1 = (2011, 1), (2026, 2)                         # DERA 범위(§A 와 같다)
DERA_LAST_DAY = "2026-06-30"                          # Q1 의 마지막 날 — 그 뒤는 submissions 로 센다
F345 = ("3", "3/A", "4", "4/A", "5", "5/A")
ANNUAL = {"10-K": 0, "10-K405": 0, "10-KT": 0, "20-F": 1, "40-F": 1}
PERIODIC = {"10-Q": 0, "6-K": 1}
REGFORM = {"S-1": 0, "S-4": 0, "10-12B": 0, "8-K": 0, "F-1": 1, "F-4": 1}   # 첫 정기보고 전의 대체 증거
PAGE_SINCE = "2010-01-01"                             # 이보다 오래된 submissions 조각은 받지 않는다
CHECK_URLS = ("https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/index.json",
              "https://data.sec.gov/submissions/CIK0000320193.json")


# ════════════════════════════════════════════════════════════════════════
# 공용
# ════════════════════════════════════════════════════════════════════════
def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rj(p, default=None):
    if not os.path.exists(p):
        return default
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _wj(p, obj, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"), sort_keys=False)
    tmp = p + ".tmp"
    if p.endswith(".gz"):
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(s + "\n")
    else:
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(s + "\n")
    os.replace(tmp, p)


def _wj_stable(p, obj, indent=None, key="generated"):
    """_wj 와 같다 — 다만 이미 있는 파일과 key(만든 시각) 말고 내용이 같으면 옛 시각을 그대로 둔다
    (같은 입력으로 다시 빌드하면 파일 바이트가 같다 · 두 번 빌드 sha256 대조)."""
    old = _rj(p) if os.path.exists(p) else None
    if isinstance(old, dict) and isinstance(obj, dict) and key in old and key in obj:
        a = {k: v for k, v in old.items() if k != key}
        b = json.loads(json.dumps({k: v for k, v in obj.items() if k != key}, ensure_ascii=False))
        if a == b:
            obj[key] = old[key]
    _wj(p, obj, indent=indent)


def _ym(d: str) -> str:
    return d[:7]


def _madd(ym: str, k: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + (m - 1) + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def _mdiff(a: str, b: str) -> int:
    """a − b (개월)."""
    return (int(a[:4]) * 12 + int(a[5:7])) - (int(b[:4]) * 12 + int(b[5:7]))


def _mend(ym: str) -> str:
    n = _madd(ym, 1)
    return (dt.date(int(n[:4]), int(n[5:7]), 1) - dt.timedelta(days=1)).isoformat()


def norm_sym(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def sym_tokens(raw: str):
    """DERA ISSUERTRADINGSYMBOL → 정규화 토큰들. 통째 + 쉼표·세미콜론·&·공백으로 가른 조각.
    ⚠ '/' 로는 가르지 않는다 — 'BRK/B' 를 'BRK' 와 'B'(다른 회사 티커)로 쪼개면 오염된다."""
    s = (raw or "").upper().strip()
    out = set()
    w = norm_sym(s)
    if w:
        out.add(w)
    for p in re.split(r"[,;&\s]+", s):
        p = re.sub(r"^(NYSE|NASDAQ|NYSEMKT|AMEX|OTC)[:\-]", "", p)
        q = norm_sym(p)
        if q and q not in ("NYSE", "NASDAQ", "NONE", "NA", "N"):
            out.add(q)
    return out


class Manifest:
    """원본 고정표. key → {url, sha256, bytes, fetched, …}. 해시가 바뀌면 멈춘다(allow_update 가 아니면)."""

    def __init__(self, path, note, section):
        self.path, self.section = path, section
        self.doc = _rj(path) or {"note": note, section: {}}
        self.doc.setdefault(section, {})
        self.dirty = False

    def get(self, key):
        return self.doc[self.section].get(key)

    def put(self, key, meta, allow_update=False):
        meta = dict(meta)
        if key.startswith(("sub/", "browse/")) and meta.get("url") and meta.get("status") is None:
            meta.pop("url", None)              # 키에서 유도된다(url_rule)
        if meta.get("path") in (key, key + ".gz"):
            meta.pop("path", None)
        old = self.doc[self.section].get(key)
        if old and old.get("sha256") != meta.get("sha256") and not allow_update:
            raise SystemExit("🚨 고정 해시가 바뀌었다 — %s\n   manifest %s\n   지금     %s\n"
                             "   원본이 다시 게시됐다. 빌드를 멈춘다(무엇이 바뀌었는지 먼저 볼 것)."
                             % (key, old.get("sha256"), meta.get("sha256")))
        if old != meta:
            self.doc[self.section][key] = meta
            self.dirty = True

    def save(self):
        """한 항목 한 줄(diff 가 읽히고 파일이 작다)."""
        if not self.dirty:
            return
        self.doc["updated"] = _now()
        ent = dict(sorted(self.doc[self.section].items()))
        head = {k: v for k, v in self.doc.items() if k != self.section}
        lines = ["{"]
        for k, v in head.items():
            lines.append(" %s: %s," % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False)))
        lines.append(" %s: {" % json.dumps(self.section))
        items = list(ent.items())
        for i, (k, v) in enumerate(items):
            lines.append("  %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                         json.dumps(v, ensure_ascii=False, separators=(",", ":")),
                                         "," if i < len(items) - 1 else ""))
        lines.append(" }")
        lines.append("}")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, self.path)
        self.dirty = False


def _head(url):
    """HEAD 1건(edgar.probe — 같은 UA · 같은 초당 상한). Last-Modified · Content-Length 만 본다."""
    try:
        _st, hd, _b = edgar.probe(url, method="HEAD", timeout=60, raise_http=True)
        return {"last_modified": hd.get("Last-Modified"), "content_length": hd.get("Content-Length")}
    except Exception as e:  # HEAD 는 참고용 — 실패해도 받기는 계속한다
        return {"last_modified": None, "content_length": None, "head_error": str(e)[:80]}


def cached_fetch(man: Manifest, key: str, url: str, rel: str, refresh=False, gz=True):
    """원본 1건 — RAW/rel 에 있으면 해시를 manifest 와 맞춰 읽고, 없으면 edgar.fetch_bytes 로 받아 고정한다.
    sha256 은 **내용 바이트**(gzip 전송을 푼 뒤)에 건다. 404 는 None."""
    p = os.path.join(RAW, rel)
    if os.path.exists(p) and not refresh:
        b = gzip.open(p, "rb").read() if gz else open(p, "rb").read()
        m = man.get(key)
        if m and m.get("sha256") != _sha(b):
            raise SystemExit("🚨 로컬 원본이 manifest 해시와 다르다 — %s (%s)" % (key, p))
        if not m:
            man.put(key, {"url": url, "sha256": _sha(b), "bytes": len(b), "fetched": None, "path": rel})
        return b
    try:
        b = edgar.fetch_bytes(url, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            man.put(key, {"url": url, "sha256": None, "bytes": 0, "fetched": _now(), "path": None, "status": 404},
                    allow_update=True)
            return None
        raise
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if gz:
        with gzip.open(p + ".tmp", "wb", compresslevel=6) as f:
            f.write(b)
    else:
        with open(p + ".tmp", "wb") as f:
            f.write(b)
    os.replace(p + ".tmp", p)
    man.put(key, {"url": url, "sha256": _sha(b), "bytes": len(b), "fetched": _now(), "path": rel},
            allow_update=refresh)
    return b


# ════════════════════════════════════════════════════════════════════════
# check — UA 가 차단 페이지가 아니라 진짜 200 을 받는지
# ════════════════════════════════════════════════════════════════════════
def cmd_check():
    res = []
    for url in CHECK_URLS:
        st, hd, raw = edgar.probe(url, timeout=30)       # 받은 그대로(상태 · 머리 · 전송 바이트) — SEC urlopen 은 edgar.py 에만
        ce, ct = hd.get("Content-Encoding"), hd.get("Content-Type")
        body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        blocked = b"Undeclared Automated Tool" in body
        ok_json = False
        try:
            json.loads(body.decode("utf-8"))
            ok_json = True
        except Exception:
            pass
        res.append({"url": url, "status": st, "content_encoding": ce, "content_type": ct,
                    "wire_bytes": len(raw), "body_bytes": len(body), "blocked_page": blocked, "json": ok_json,
                    "sha256": _sha(body), "at": _now()})
        print("  %s → HTTP %s · %s · %s · 전송 %dB / 본문 %dB · 차단페이지 %s · JSON %s"
              % (url, st, ce, ct, len(raw), len(body), blocked, ok_json))
    good = all(r["status"] == 200 and r["content_encoding"] == "gzip" and not r["blocked_page"] and r["json"] for r in res)
    _wj(os.path.join(RAW, "_access_check.json"), {"ok": good, "checks": res})
    if not good:
        raise SystemExit("🚨 접속 점검 실패 — UA 를 확인할 것(차단 페이지 · 비 gzip · 비 200)")
    print("✓ 접속 점검 통과(HTTP 200 · gzip · JSON)")
    return res


# ════════════════════════════════════════════════════════════════════════
# dera — 분기 ZIP 받기 · 고정 · SUBMISSION 집계
# ════════════════════════════════════════════════════════════════════════
def _quarters():
    y, q = Q0
    while (y, q) <= Q1:
        yield "%dq%d" % (y, q)
        q += 1
        if q == 5:
            y, q = y + 1, 1


def dera_links():
    html = edgar.fetch_bytes(DERA_INDEX, timeout=60).decode("utf-8", "ignore")
    out = {}
    for h in re.findall(r'href="([^"]*form345\.zip)"', html):
        m = re.search(r"(\d{4}q\d)_form345\.zip", h)
        if m and m.group(1) not in out:
            out[m.group(1)] = h if h.startswith("http") else "https://www.sec.gov" + h
    return out


def ins_manifest():
    return Manifest(MAN_INS, "DERA Insider Transactions Data Sets 분기 ZIP 고정표 — sha256 · 크기 · Last-Modified. "
                             "build/issuer_map.py(§A0) 가 만들고 build/ins_pit_build.py(§A) 가 같이 쓴다. "
                             "다시 받을 때 해시가 바뀌면 빌드를 멈춘다(과거 분기는 2022년에 재추출됐고, "
                             "2025-07 에 2023~2025판에 AFF10B5ONE 이 소급 추가됐다). ZIP 본체는 저장소 밖에 둔다.", "zips")


def fetch_dera():
    man = ins_manifest()
    links = None
    for key in _quarters():
        rel = "dera/%s_form345.zip" % key
        p = os.path.join(RAW, rel)
        if os.path.exists(p):
            sha = _sha_file(p)
            m = man.get(key)
            if m and m["sha256"] != sha:
                raise SystemExit("🚨 %s 로컬 ZIP 해시가 manifest 와 다르다" % key)
            if not m:
                links = links or dera_links()
                meta = {"url": links.get(key), "sha256": sha, "bytes": os.path.getsize(p), "fetched": None,
                        "path": rel}
                meta.update(_head(links[key]))
                man.put(key, meta)
            continue
        links = links or dera_links()
        url = links.get(key)
        if not url:
            raise SystemExit("🚨 인덱스 페이지에 %s 링크가 없다" % key)
        hd = _head(url)
        t0 = time.time()
        b = edgar.fetch_bytes(url, timeout=600)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".tmp", "wb") as f:
            f.write(b)
        os.replace(p + ".tmp", p)
        meta = {"url": url, "sha256": _sha(b), "bytes": len(b), "fetched": _now(), "path": rel}
        meta.update(hd)
        with zipfile.ZipFile(p) as z:
            meta["inner"] = {i.filename.split("/")[-1]: [i.file_size, "%04d-%02d-%02d" % i.date_time[:3]]
                             for i in z.infolist()}
        man.put(key, meta)
        man.save()
        print("  %s %.1fMB %.0fs %s" % (key, len(b) / 1e6, time.time() - t0, hd.get("last_modified")), flush=True)
    man.save()
    return man


MON = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
       "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}


def _ddate(s):
    s = (s or "").strip()
    if len(s) == 11 and s[2] == "-" and s[6] == "-":
        mm = MON.get(s[3:6].upper())
        if mm:
            return "%s-%s-%s" % (s[7:11], mm, s[0:2])
    return ""


def dera_agg(key, zsha):
    """분기 ZIP → SUBMISSION 집계(저장소 밖 캐시 · ZIP 해시에 묶는다).
    sym  : [정규화 티커, CIK, 제출월, 건수]
    cik  : [CIK, 제출월, Form3 계, Form4 계, Form5 계]
    span : [CIK, 정규화 티커, 첫 제출일, 마지막 제출일, 건수]
    names: [CIK, ISSUERNAME, 건수]"""
    cp = os.path.join(RAW, "dera_agg", key + ".json.gz")
    c = _rj(cp)
    if c and c.get("zip_sha256") == zsha:
        return c
    p = os.path.join(RAW, "dera", key + "_form345.zip")
    sym, cikc, span, names = collections.Counter(), collections.Counter(), {}, collections.Counter()
    n_rows = n_bad = n_nosym = 0
    with zipfile.ZipFile(p) as z:
        nm = {n.split("/")[-1]: n for n in z.namelist()}
        with z.open(nm["SUBMISSION.tsv"]) as f:
            rd = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t",
                                quoting=csv.QUOTE_NONE)
            for r in rd:
                dtp = (r.get("DOCUMENT_TYPE") or "").strip()
                if dtp not in F345:
                    continue
                n_rows += 1
                fd = _ddate(r.get("FILING_DATE"))
                try:
                    ck = int((r.get("ISSUERCIK") or "").strip())
                except ValueError:
                    n_bad += 1
                    continue
                if not fd:
                    n_bad += 1
                    continue
                ym = fd[:7]
                cls = dtp[0]
                cikc[(ck, ym, cls)] += 1
                names[(ck, (r.get("ISSUERNAME") or "").strip())] += 1
                toks = sym_tokens(r.get("ISSUERTRADINGSYMBOL"))
                if not toks:
                    n_nosym += 1
                for s in toks:
                    sym[(s, ck, ym)] += 1
                    k = (ck, s)
                    v = span.get(k)
                    if v is None:
                        span[k] = [fd, fd, 1]
                    else:
                        if fd < v[0]:
                            v[0] = fd
                        if fd > v[1]:
                            v[1] = fd
                        v[2] += 1
    cik_rows = {}
    for (ck, ym, cls), n in cikc.items():
        row = cik_rows.setdefault((ck, ym), [ck, ym, 0, 0, 0])
        row[{"3": 2, "4": 3, "5": 4}[cls]] += n
    doc = {"key": key, "zip_sha256": zsha, "n_rows": n_rows, "n_bad": n_bad, "n_nosym": n_nosym,
           "sym": [[s, ck, ym, n] for (s, ck, ym), n in sorted(sym.items())],
           "cik": sorted(cik_rows.values()),
           "span": [[ck, s, v[0], v[1], v[2]] for (ck, s), v in sorted(span.items())],
           "names": [[ck, nmv, n] for (ck, nmv), n in sorted(names.items())]}
    _wj(cp, doc)
    return doc


def dera_f4sym(key, zsha):
    """분기 ZIP → Form 4 · 4/A 제출만의 티커 집계(저장소 밖 캐시 · ZIP 해시에 묶는다) — 커버리지의 «지도에 안 이어진 CIK» 용.
    sym  : [정규화 티커, 발행사 CIK, 제출월, 건수]
    names: [CIK, ISSUERNAME, 건수]"""
    cp = os.path.join(RAW, "dera_agg", key + ".f4sym.json.gz")
    c = _rj(cp)
    if c and c.get("zip_sha256") == zsha:
        return c
    p = os.path.join(RAW, "dera", key + "_form345.zip")
    if _sha_file(p) != zsha:
        raise SystemExit("🚨 %s ZIP 해시가 manifest 와 다르다" % p)
    sym, names = collections.Counter(), collections.Counter()
    with zipfile.ZipFile(p) as z:
        nm = {n.split("/")[-1]: n for n in z.namelist()}
        with z.open(nm["SUBMISSION.tsv"]) as f:
            rd = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t",
                                quoting=csv.QUOTE_NONE)
            for r in rd:
                if (r.get("DOCUMENT_TYPE") or "").strip() not in ("4", "4/A"):
                    continue
                fd = _ddate(r.get("FILING_DATE"))
                try:
                    ck = int((r.get("ISSUERCIK") or "").strip())
                except ValueError:
                    continue
                if not fd:
                    continue
                names[(ck, (r.get("ISSUERNAME") or "").strip())] += 1
                for s in sym_tokens(r.get("ISSUERTRADINGSYMBOL")):
                    sym[(s, ck, fd[:7])] += 1
    doc = {"key": key, "zip_sha256": zsha, "sym": [[s, ck, ym, n] for (s, ck, ym), n in sorted(sym.items())],
           "names": [[ck, nmv, n] for (ck, nmv), n in sorted(names.items())]}
    _wj(cp, doc)
    return doc


def unjoined_f4(B, M, used, IV, OKS, manual):
    """멤버-월에 그 멤버 티커로 낸 Form 4 · 4/A 가운데 그달 지도 CIK 집합 밖 CIK 로 낸 것 — 분류와 건수(수익 없음).
    joined = 그달 CIK 집합 · same_group_other_interval = 같은 그룹 CIK 인데 효력 구간 밖 · other_world_group = 다른 세계 그룹 CIK
    (제출자가 남의 티커를 적었다) · outside_world = 어느 그룹에도 없는 CIK(이어지지 않은 제출 — 표에 이유)."""
    syms = {norm_sym(t) for ym in B.months for t in B.MM[ym]}
    F4 = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for key in _quarters():
        a = dera_f4sym(key, B.D.zip_sha[key])
        for s, ck, ym, n in a["sym"]:
            if s in syms:
                F4[s][ym][ck] += n
    c2g = {c: g for g, cs in used.items() for c in cs}
    tot = collections.Counter()
    cells = collections.defaultdict(lambda: [0, None, None, 0])      # (티커, CIK, 분류) → [건수, 첫 달, 끝 달, 멤버-월 수]
    for ym in B.months:
        for t in B.MM[ym]:
            r = M[(t, ym)]
            if r["status"] not in OKS:
                continue
            g = r["gid"]
            cs = set(B.cik_set(g, used, IV, ym, r["primary"]))
            for ck, n in F4[norm_sym(t)].get(ym, {}).items():
                if ck in cs:
                    k = "joined"
                elif c2g.get(ck) == g:
                    k = "same_group_other_interval"
                elif ck in c2g:
                    k = "other_world_group"
                else:
                    k = "outside_world"
                tot[k] += n
                if k != "joined":
                    v = cells[(t, ck, k)]
                    v[0] += n
                    v[1] = ym if v[1] is None or ym < v[1] else v[1]
                    v[2] = ym if v[2] is None or ym > v[2] else v[2]
                    v[3] += 1
    need = {ck for (_, ck, _) in cells}
    nm = collections.defaultdict(collections.Counter)
    for key in _quarters():
        for ck, name, n in dera_f4sym(key, B.D.zip_sha[key])["names"]:
            if ck in need:
                nm[ck][name] += n
    why = {(x.get("t"), int(x["cik"])): x.get("why") for x in manual.get("exclude", []) + manual.get("unjoined", [])}
    rows = []
    for (t, ck, k), v in cells.items():
        dn = (nm[ck].most_common(1) or [[None]])[0][0]
        # 이름이 명단 이름과 맞으면(같은 회사 계열 — 운영 파트너십 · 자회사 · 옛 지주사) 이어지지 않은 제출일 수 있다 · 아니면 티커 잡음
        k2 = k + ("_name_match" if (k == "outside_world" and dn and names_sim(ref_names(B.R, t), {dn})[0] >= NAME_OK) else "")
        rows.append([t, ck, k2, v[0], v[1], v[2], v[3], dn, why.get((t, ck))])
    rows.sort(key=lambda x: (-x[3], x[0], x[1]))
    by, byn = collections.Counter(), collections.Counter()
    for x in rows:
        by[x[2]] += 1
        byn[x[2]] += x[3]
    return {"rule": "DERA SUBMISSION Form 4 · 4/A · ISSUERTRADINGSYMBOL = 멤버 티커(sym_tokens 정규화 — 지도 증거와 같은 규칙) · 제출월 = 멤버-월. "
                    "분류는 그달 지도 CIK 집합 기준: joined · same_group_other_interval · other_world_group(다른 세계 그룹 CIK) · "
                    "outside_world_name_match(어느 그룹에도 없고 DERA 이름이 명단 이름과 맞는 CIK — 같은 회사 계열인데 잇지 않은 제출 · 이유를 "
                    "수작업 표 unjoined 에 적는다) · outside_world(이름도 다른 CIK — 제출자가 남의 티커를 적은 잡음: O → Northern Oil 등). "
                    "행 = [티커, CIK, 분류, Form 4 건수, 첫 달, 끝 달, 멤버-월 수, DERA 이름, 이유(수작업 exclude · unjoined)].",
            "form4_by_class": dict(tot), "form4_by_class_detail": dict(byn), "n_ticker_cik_by_class": dict(by),
            "outside_world_name_match": [x for x in rows if x[2] == "outside_world_name_match"],
            "outside_world_top": [x for x in rows if x[2] == "outside_world"][:40],
            "other_rows_top": [x for x in rows if not x[2].startswith("outside_world")][:40]}


def cmd_dera():
    man = fetch_dera()
    tot = 0
    for key in _quarters():
        m = man.get(key)
        a = dera_agg(key, m["sha256"])
        tot += a["n_rows"]
        print("  %s Form3/4/5 %d · 날짜·CIK 불량 %d · 티커 빈칸 %d" % (key, a["n_rows"], a["n_bad"], a["n_nosym"]),
              flush=True)
    print("✓ DERA %d분기 · Form 3/4/5 %d건" % (len(list(_quarters())), tot))




# ════════════════════════════════════════════════════════════════════════
# 저장소 참조 자료 · 멤버-월
# ════════════════════════════════════════════════════════════════════════
IN_FILES = ("index_history.json", "pit_gics_sectors.json", "cik_map.json", "delisted_names.json",
            "stocks.json", "pit_universe.json", "pit_reuse.json", "_issuer_map_sector_manual.json")
SECTOR_MANUAL = os.path.join(DATA, "_issuer_map_sector_manual.json")   # 수작업 섹터 표(위키 PIT 에 없고 대체 칸도 빈 멤버-월)


def load_refs():
    R = {}
    R["H"] = _rj(os.path.join(DATA, "index_history.json"))
    R["G"] = (_rj(os.path.join(DATA, "pit_gics_sectors.json")) or {}).get("months") or {}
    R["cikmap"] = {t: int(c) for t, c in ((_rj(os.path.join(DATA, "cik_map.json")) or {}).get("co") or {}).items()}
    R["deln"] = {t: v.get("name") for t, v in
                 ((_rj(os.path.join(DATA, "delisted_names.json")) or {}).get("names") or {}).items()}
    S = _rj(os.path.join(DATA, "stocks.json")) or {}
    R["sname"] = {s["t"]: s.get("name") for s in S.get("stocks") or []}
    R["ssec"] = {s["t"]: s.get("sector") for s in S.get("stocks") or []}
    R["secman"] = collections.defaultdict(list)
    for x in (_rj(SECTOR_MANUAL) or {}).get("rows") or []:
        R["secman"][x["t"]].append((x["from"], x["to"], x["sector"]))
    R["inputs"] = {f: _sha_file(os.path.join(DATA, f)) for f in IN_FILES if os.path.exists(os.path.join(DATA, f))}
    return R


def member_months(H):
    """{월: {티커: 'spx'|'ndx'|'spx+ndx'}} — 한쪽 지수가 빈 달은 직전 달을 잇는다(pit_panel.load_world 와 같은 규칙).
    티커는 index_history 표기 그대로(BRK.B · BF.B)."""
    out, carried = {}, []
    last = {"spx": [], "ndx": []}
    for ym in sorted(H["months"]):
        row = H["months"][ym] or {}
        cur = {}
        for ix in ("spx", "ndx"):
            v = row.get(ix) or []
            if not v and last[ix]:
                v = last[ix]
                carried.append([ym, ix, len(v)])
            if v:
                last[ix] = v
            for t in v:
                cur[t] = (cur[t] + "+" + ix) if t in cur else ix
        out[ym] = cur
    return out, carried


def ref_names(R, t):
    H = R["H"]
    out = set()
    if (H.get("name") or {}).get(t):
        out.add(H["name"][t])
    for c, d in (H.get("cik_names") or {}).items():
        if t in d and d[t]:
            out.add(d[t])
    for src in (R["deln"], R["sname"]):
        if src.get(t):
            out.add(src[t])
    return out


def anchors_static(R, t, ctk):
    """티커 → 닻 CIK 들(날짜 없는 것) · 출처 이름."""
    H = R["H"]
    out = []
    v = (H.get("cik") or {}).get(t)
    if v:
        out.append((int(v), "wiki_flat"))
    for c, ts in (H.get("cik_hist") or {}).items():
        if t in ts:
            out.append((int(c), "cik_hist"))
    for c, d in (H.get("cik_names") or {}).items():
        if t in d:
            out.append((int(c), "cik_names"))
    for k in sorted({t, t.replace(".", "-"), t.replace("-", ".")}):
        if k in R["cikmap"]:
            out.append((R["cikmap"][k], "cik_map"))
        for c in ctk.get(k, []):
            out.append((c, "company_tickers"))
    for c in edgar.PREDECESSOR.get(t, []):
        out.append((int(c), "edgar.PREDECESSOR"))
    seen, res = set(), []
    for c, s in out:
        if (c, s) not in seen:
            seen.add((c, s))
            res.append((c, s))
    return res


def wiki_month_cik(R, t, ym):
    v = ((R["G"].get(ym) or {}).get("cik") or {}).get(t)
    return int(v) if v else None


def sector_src_at(R, t, ym):
    """(섹터, 출처) — 그달 위키 GICS(SPX 표 · PIT) → 수작업 섹터 표(_issuer_map_sector_manual.json · 그때 GICS · PIT) →
    index_history 섹터(티커당 한 값 · 비PIT) → stocks.json 오늘 섹터(비PIT). 위키 표에 이름은 있는데 섹터 칸이 빈 달(LYV 2019-12)은
    없는 것으로 보고 다음 출처로 간다. 출처 = wiki_pit · manual · index_history · stocks_today · none."""
    g = R["G"].get(ym)
    if g:
        for sec, ts in (g.get("sec") or {}).items():
            if t in ts and sec:
                return sec, "wiki_pit"
    for a, b, sec in (R.get("secman") or {}).get(t, ()):
        if a <= ym <= b:
            return sec, "manual"
    h = (R["H"].get("sector") or {}).get(t)
    if h:
        return h, "index_history"
    s = R["ssec"].get(t)
    if s:
        return s, "stocks_today"
    return None, "none"


def sector_at(R, t, ym):
    """그달 섹터(sector_src_at 의 섹터) — 위키 PIT → 수작업 표 → 비PIT 대체(index_history · 오늘 섹터)."""
    return sector_src_at(R, t, ym)[0]


# ════════════════════════════════════════════════════════════════════════
# DERA 집계 읽기
# ════════════════════════════════════════════════════════════════════════
class Dera:
    """symcnt[정규화 티커][CIK][월] · cikcnt[CIK][월] = [F3, F4, F5] · span[CIK] = [첫, 끝] · symspan[(CIK, 티커)]
    · names[CIK] = Counter. syms · ciks 를 주면 그것만 싣는다(메모리)."""

    def __init__(self, syms=None, ciks=None):
        man = ins_manifest()
        self.symcnt = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        self.cikcnt = collections.defaultdict(dict)
        self.span, self.symspan = {}, {}
        self.names = collections.defaultdict(collections.Counter)
        self.qnames = collections.defaultdict(dict)       # CIK → {분기: 가장 흔한 이름}
        self.zip_sha = {}
        self.n_rows = 0
        self.qrows = {}
        for key in _quarters():
            m = man.get(key)
            if not m:
                raise SystemExit("🚨 DERA %s 가 manifest 에 없다 — issuer_map.py dera 먼저" % key)
            a = dera_agg(key, m["sha256"])
            self.zip_sha[key] = m["sha256"]
            self.n_rows += a["n_rows"]
            self.qrows[key] = a["n_rows"]
            for s, ck, ym, n in a["sym"]:
                if syms is None or s in syms:
                    self.symcnt[s][ck][ym] += n
            for ck, ym, n3, n4, n5 in a["cik"]:
                if ciks is None or ck in ciks:
                    self.cikcnt[ck][ym] = [n3, n4, n5]
            for ck, s, f, l, n in a["span"]:
                if ciks is None or ck in ciks:
                    v = self.span.get(ck)
                    self.span[ck] = [min(v[0], f), max(v[1], l)] if v else [f, l]
                    k = (ck, s)
                    v = self.symspan.get(k)
                    self.symspan[k] = [min(v[0], f), max(v[1], l), v[2] + n] if v else [f, l, n]
            best = {}
            for ck, nm, n in a["names"]:
                if ciks is None or ck in ciks:
                    self.names[ck][nm] += n
                    if n > best.get(ck, ("", 0))[1]:
                        best[ck] = (nm, n)
            for ck, (nm, n) in best.items():
                self.qnames[ck][key] = nm

    def f345(self, ck, m0, m1):
        """CIK 의 Form 3/4/5 건수(제출월 m0..m1)."""
        d = self.cikcnt.get(ck) or {}
        return sum(sum(v) for ym, v in d.items() if m0 <= ym <= m1)

    def other_sym_before(self, ck, exclude, before):
        """ck 가 exclude 에 없는 티커로 before(날짜) 전에 낸 건수 — 전환 전부터 다른 티커로 살아 있던 회사인지."""
        n = 0
        for (c, s), v in self.symspan.items():
            if c == ck and s not in exclude and v[0] < before:
                n += v[2]
        return n


# ════════════════════════════════════════════════════════════════════════
# sub — company_tickers · submissions(+과거 조각) · 금융 전용은 연차보고 목록
# ════════════════════════════════════════════════════════════════════════
def im_manifest():
    m = Manifest(MAN_IM, "build/issuer_map.py 가 받은 SEC 원본 고정표(DERA ZIP 제외 — data/_ins_pit/manifest.json). "
                         "sha256 은 gzip 전송을 푼 내용 바이트에 건다. 원본은 저장소 밖(RBATCH_RAW/<키>.gz)에 둔다. "
                         "submissions 는 살아 있는 파일이라 받은 날의 판을 고정한 것이다.", "files")
    m.doc["url_rule"] = {"sub/<이름>": "https://data.sec.gov/submissions/<이름>",
                         "browse/<CIK10>_<서식>.atom": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<CIK10>"
                                                      "&type=<서식>&dateb=&owner=include&count=100&output=atom"}
    return m


def company_tickers(man, refresh=False):
    b = cached_fetch(man, "sec/company_tickers.json", edgar.TICKERS_URL, "sec/company_tickers.json.gz", refresh)
    j = json.loads(b.decode("utf-8"))
    out = collections.defaultdict(list)
    for v in (j.values() if isinstance(j, dict) else j):
        t = str(v.get("ticker") or "").upper().strip()
        c = v.get("cik_str")
        if t and isinstance(c, int) and c not in out[t]:
            out[t].append(c)
    return dict(out)


FIN = {"Financials"}
FPI_REGISTERED = "fpi_q"      # 등록 FPI 표지(2026-09-25 권고 — 직전 정기보고가 10-Q 면 FPI 아님 · 사양 칸 fpi 는 옆에 남긴다)


def pure_fin_ciks(R, cand_by_t, MM):
    """모든 멤버-월에서 금융인 티커에만 걸린 CIK — submissions 과거 조각을 받지 않는다(§B 사양: 424B2 조각 회피).
    V·MA 처럼 창 안에서 업종이 바뀐 이름은 여기 들지 않는다. 대신 browse-edgar 의 10-K · 20-F 목록으로 연차보고를 본다."""
    tfin = {}
    for ym, mem in MM.items():
        for t in mem:
            f = sector_at(R, t, ym) in FIN
            tfin[t] = tfin.get(t, True) and f
    c2t = collections.defaultdict(set)
    for t, cs in cand_by_t.items():
        for c in cs:
            c2t[c].add(t)
    return {c for c, ts in c2t.items() if ts and all(tfin.get(t, False) for t in ts)}


def fetch_sub(man, cik, paginate=True, refresh=False):
    rel = "sub/CIK%010d.json.gz" % cik
    b = cached_fetch(man, "sub/CIK%010d.json" % cik, edgar.SUB_URL % cik, rel, refresh)
    if b is None:
        return None
    j = json.loads(b.decode("utf-8"))
    pages = []
    if paginate:
        for f in (j.get("filings") or {}).get("files") or []:
            nm = f.get("name")
            if not nm or (f.get("filingTo") or "9999") < PAGE_SINCE:
                continue
            pb = cached_fetch(man, "sub/" + nm, "https://data.sec.gov/submissions/" + nm, "sub/" + nm + ".gz", refresh)
            if pb is not None:
                pages.append(json.loads(pb.decode("utf-8")))
    return j, pages


def fetch_browse(man, cik, form, refresh=False):
    """금융 전용 CIK 의 연차보고 목록(browse-edgar atom · type 앞글자 일치 · 최근 100건)."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=%010d&type=%s&dateb=&owner=include"
           "&count=100&output=atom" % (cik, urllib.parse.quote(form)))
    return cached_fetch(man, "browse/%010d_%s.atom" % (cik, form), url, "browse/%010d_%s.atom.gz" % (cik, form),
                        refresh)


def _rows(d):
    if "form" not in d:
        return []
    ks = ("form", "filingDate", "reportDate")
    n = min(len(d[k]) for k in ks if k in d)
    return [tuple((d[k][i] if k in d else "") or "" for k in ks) for i in range(n)]


KEEP_FORMS = set(ANNUAL) | set(PERIODIC) | set(F345) | {"10-K/A", "20-F/A", "40-F/A", "8-K", "S-1", "F-1", "10-12B",
                                                          "S-4", "F-4", "424B4", "DEF 14A", "15-12B", "15-12G"}
_SUBC = {}


def load_sub(cik):
    """캐시된 submissions → 요약(이름·이력·티커·서식별 제출일). 없으면 None."""
    if cik in _SUBC:
        return _SUBC[cik]
    p = os.path.join(RAW, "sub", "CIK%010d.json.gz" % cik)
    if not os.path.exists(p):
        _SUBC[cik] = None
        return None
    j = _rj(p)
    rows = _rows((j.get("filings") or {}).get("recent") or {})
    files = (j.get("filings") or {}).get("files") or []
    need = [f for f in files if (f.get("filingTo") or "9999") >= PAGE_SINCE]
    got = 0
    for f in need:
        pp = os.path.join(RAW, "sub", (f.get("name") or "") + ".gz")
        if f.get("name") and os.path.exists(pp):
            rows += _rows(_rj(pp))
            got += 1
    fd_all = sorted(r[1] for r in rows if r[1])
    keep = {(r[0], r[1], r[2]) for r in rows if r[0] in KEEP_FORMS}
    br = False
    for form in ("10-K", "20-F", "40-F"):
        bp = os.path.join(RAW, "browse", "%010d_%s.atom.gz" % (cik, form))
        if os.path.exists(bp):
            br = True
            x = gzip.open(bp, "rb").read().decode("latin-1")
            for m in re.finditer(r"<entry>(.*?)</entry>", x, re.S):
                e = m.group(1)
                fm = re.search(r"<filing-type>([^<]+)</filing-type>", e)
                fdm = re.search(r"<filing-date>([^<]+)</filing-date>", e)
                if fm and fdm:
                    keep.add((fm.group(1).strip(), fdm.group(1).strip(), ""))
    rec = {"cik": cik, "name": j.get("name"), "tickers": j.get("tickers") or [], "exchanges": j.get("exchanges") or [],
           "former": [(f.get("name"), (f.get("from") or "")[:10], (f.get("to") or "")[:10])
                      for f in j.get("formerNames") or []],
           "sic": j.get("sic"), "sicd": j.get("sicDescription"), "etype": j.get("entityType"),
           "inc": j.get("stateOfIncorporation"), "cat": j.get("category"),
           "first": fd_all[0] if fd_all else None, "last": fd_all[-1] if fd_all else None,
           "n": len(rows), "pages_need": len(need), "pages_got": got, "browse": br, "forms": sorted(keep)}
    _SUBC[cik] = rec
    return rec


def load_manual():
    m = _rj(MANUAL) or {}
    for k in ("resolve", "splice", "anchor", "name_ok", "alias", "sibling", "exclude", "verified"):
        m.setdefault(k, [])
    return m


def candidate_ciks(R, D, MM, ctk, manual):
    """티커별 후보 CIK — DERA 티커 일치(멤버 기간 −36개월 ~ +6개월 · 2건 이상) ∪ 닻 ∪ 위키 월별 ∪ 수작업."""
    tmon = collections.defaultdict(list)
    for ym in sorted(MM):
        for t in MM[ym]:
            tmon[t].append(ym)
    cand = {}
    alias = collections.defaultdict(list)
    for a in manual.get("alias", []):
        alias[a["t"]] += [norm_sym(x) for x in a.get("syms", [])]
    for t, ms in tmon.items():
        lo, hi = _madd(ms[0], -36), _madd(ms[-1], 6)
        cs = set()
        for s in [norm_sym(t)] + alias.get(t, []):
            for ck, cnt in (D.symcnt.get(s) or {}).items():
                if sum(n for ym, n in cnt.items() if lo <= ym <= hi) >= 2:
                    cs.add(ck)
        for c, _ in anchors_static(R, t, ctk):
            cs.add(c)
        for ym in ms:
            w = wiki_month_cik(R, t, ym)
            if w:
                cs.add(w)
        for key in ("anchor", "resolve"):
            for a in manual.get(key, []):
                if a.get("t") == t and a.get("cik"):
                    cs.add(int(a["cik"]))
        cand[t] = cs
    return cand, dict(tmon)


def cmd_sub(refresh=False):
    R = load_refs()
    MM, _ = member_months(R["H"])
    manual = load_manual()
    man = im_manifest()
    ctk = company_tickers(man, refresh)
    man.save()
    syms = {norm_sym(t) for ym in MM for t in MM[ym]}
    syms |= {norm_sym(x) for a in manual.get("alias", []) for x in a.get("syms", [])}
    D = Dera(syms=syms, ciks=set())
    cand, tmon = candidate_ciks(R, D, MM, ctk, manual)
    extra = set()
    for s in manual["splice"]:
        extra |= {int(s["pred"]), int(s["succ"])}
    allc = sorted({c for cs in cand.values() for c in cs} | extra)
    fin = pure_fin_ciks(R, cand, MM)
    print("후보 CIK %d개(티커 %d) · 금융 전용 %d개(과거 조각 생략 · 연차보고 목록으로 대신)" % (len(allc), len(cand), len(fin)))
    t0, n0 = time.time(), 0
    for i, c in enumerate(allc, 1):
        had = os.path.exists(os.path.join(RAW, "sub", "CIK%010d.json.gz" % c))
        r = fetch_sub(man, c, paginate=c not in fin, refresh=refresh)
        if r and c in fin:
            fetch_browse(man, c, "10-K", refresh)
            fetch_browse(man, c, "20-F", refresh)
        if not had:
            n0 += 1
        if i % 50 == 0:
            man.save()
            print("  … %d/%d · 새로 %d · %.0fs" % (i, len(allc), n0, time.time() - t0), flush=True)
    man.save()
    print("✓ submissions %d CIK (새로 %d) · %.0fs" % (len(allc), n0, time.time() - t0))


def cmd_search(queries):
    """EDGAR 회사 검색(efts search-index · EDGAR 화면의 회사 자동완성과 같은 색인). 결과는 저장소 밖에 두고 해시로 고정."""
    man = im_manifest()
    out = {}
    for q in queries:
        url = "https://efts.sec.gov/LATEST/search-index?keysTyped=" + urllib.parse.quote(q)
        key = "search/" + re.sub(r"[^A-Za-z0-9]+", "_", q)[:60]
        b = cached_fetch(man, key, url, key + ".json.gz")
        hits = []
        if b:
            j = json.loads(b.decode("utf-8"))
            for h in ((j.get("hits") or {}).get("hits") or []):
                src = h.get("_source") or {}
                hits.append({"cik": int(h.get("_id")), "entity": src.get("entity"), "tickers": src.get("tickers")})
        out[q] = hits
        print("  %-40s %s" % (q, "; ".join("%s %s %s" % (x["cik"], x["entity"], x.get("tickers") or "")
                                           for x in hits[:6])))
    man.save()
    return out


# ════════════════════════════════════════════════════════════════════════
# 이름 맞추기
# ════════════════════════════════════════════════════════════════════════
STOP = {"inc", "incorporated", "corp", "corporation", "co", "company", "companies", "cos", "the", "ltd", "limited",
        "plc", "holdings", "holding", "hldgs", "hldg", "group", "grp", "nv", "sa", "ag", "se", "llc", "lp", "class",
        "series", "cl", "common", "stock", "new", "de", "del", "of", "and", "com", "the", "tr", "sh", "ben", "int",
        "adr", "ads", "ord", "shares", "share", "par", "ser", "cv", "bv", "spa", "ab", "asa", "oyj", "kgaa"}
ALIAS = {"intl": "international", "svcs": "services", "tech": "technologies", "technology": "technologies",
         "mfg": "manufacturing", "natl": "national", "sys": "systems", "labs": "laboratories", "lab": "laboratories",
         "pharma": "pharmaceuticals", "pharmaceutical": "pharmaceuticals", "hlds": "holdings", "bancorporation": "bancorp"}


def ntoks(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    w = [ALIAS.get(x, x) for x in s.split()]
    w = [x for x in w if x not in STOP]
    long_ = [x for x in w if len(x) > 1]
    return long_ or w


def name_sim(a, b):
    A, B = ntoks(a), ntoks(b)
    if not A or not B:
        return 0.0
    sa, sb = set(A), set(B)
    inter = len(sa & sb) / min(len(sa), len(sb))
    ca, cb = "".join(A), "".join(B)
    n = min(6, len(ca), len(cb))
    pref = 1.0 if n >= 4 and ca[:n] == cb[:n] else 0.0
    return max(inter, pref)


def names_sim(xs, ys):
    best, pair = 0.0, None
    for x in xs:
        for y in ys:
            s = name_sim(x, y)
            if s > best:
                best, pair = s, (x, y)
    return best, pair


NAME_OK = 0.5


# ════════════════════════════════════════════════════════════════════════
# build
# ════════════════════════════════════════════════════════════════════════
class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def _in_rng(ym, a):
    return (a.get("from") or "0000-00") <= ym <= (a.get("to") or "9999-99")


class Builder:
    def __init__(self):
        self.R = load_refs()
        self.MM, self.carried = member_months(self.R["H"])
        self.months = sorted(self.MM)
        self.manual = load_manual()
        self.man = im_manifest()
        self.ctk = company_tickers(self.man)
        syms = {norm_sym(t) for ym in self.MM for t in self.MM[ym]}
        syms |= {norm_sym(x) for a in self.manual.get("alias", []) for x in a.get("syms", [])}
        D0 = Dera(syms=syms, ciks=set())
        self.cand, self.tmon = candidate_ciks(self.R, D0, self.MM, self.ctk, self.manual)
        allc = {c for cs in self.cand.values() for c in cs}
        for s in self.manual["splice"]:
            allc |= {int(s["pred"]), int(s["succ"])}
        self.allc = allc
        self.D = Dera(syms=syms, ciks=allc)
        self.S = {c: load_sub(c) for c in sorted(allc)}
        self.missing_sub = sorted(c for c, v in self.S.items() if v is None)
        # submissions 의 Form 3/4/5 월별(DERA 가 닿지 않는 달 · 2026-07~)
        self.sub345 = {}
        for c, v in self.S.items():
            cnt = collections.Counter()
            for f, fd, rd in (v or {}).get("forms", []):
                if f in F345 and fd > DERA_LAST_DAY:
                    cnt[fd[:7]] += 1
            self.sub345[c] = cnt
        self.dera_end = DERA_LAST_DAY[:7]
        self.queue = []
        self._rel = {}
        self._nm = {}

    # ── 이름 ──────────────────────────────────────────────────────────
    def cik_names(self, c):
        out = set()
        s = self.S.get(c)
        if s:
            if s.get("name"):
                out.add(s["name"])
            for nm, a, b in s.get("former") or []:
                if nm:
                    out.add(nm)
        for nm, n in self.D.names.get(c, collections.Counter()).most_common(4):
            if nm:
                out.add(nm)
        return out

    def cik_label(self, c):
        s = self.S.get(c) or {}
        if s.get("name"):
            return s["name"]
        nm = self.D.names.get(c)
        return nm.most_common(1)[0][0] if nm else "?"

    # ── 살아 있음(그달 앞뒤 18개월 안에 무언가 냈나) ──────────────────
    def alive(self, c, ym, k=18):
        lo, hi = _madd(ym, -k) + "-01", _mend(_madd(ym, k))
        sp = self.D.span.get(c)
        if sp and sp[0] <= hi and sp[1] >= lo:
            return True
        s = self.S.get(c)
        if s:
            for f, fd, rd in s.get("forms", []):
                if lo <= fd <= hi:
                    return True
        return False

    # ── DERA 티커 몫 ──────────────────────────────────────────────────
    def dera_window(self, syms, ym):
        cnts = [self.D.symcnt.get(s) or {} for s in syms]
        if not any(cnts):
            return None

        def tally(lo, hi):
            tot = collections.Counter()
            for cnt in cnts:
                for ck, c in cnt.items():
                    n = sum(v for m, v in c.items() if lo <= m <= hi)
                    if n:
                        tot[ck] += n
            return tot

        for k in (0, 1, 3, 6, 12):
            tot = tally(_madd(ym, -k), ym)
            if sum(tot.values()) >= 3:
                return "b%d" % k, tot
        for k in (1, 3, 6, 12):
            tot = tally(_madd(ym, -k), _madd(ym, k))
            if sum(tot.values()) >= 3:
                return "s%d" % k, tot
        tot = tally(_madd(ym, -12), _madd(ym, 12))
        if tot:
            return "weak", tot
        return None

    def anchors_at(self, t, ym):
        out = []
        w = wiki_month_cik(self.R, t, ym)
        if w:
            out.append((w, "wiki_month"))
        out += anchors_static(self.R, t, self.ctk)
        for a in self.manual["anchor"]:
            if a.get("t") == t and _in_rng(ym, a):
                out.append((int(a["cik"]), "manual_anchor"))
        seen, res = set(), []
        for c, src in out:
            if c not in seen:
                seen.add(c)
                res.append((c, src))
        return res

    def name_match(self, t, c):
        k = (t, c)
        if k not in self._nm:
            refs = ref_names(self.R, t)
            self._nm[k] = bool(refs) and names_sim(refs, self.cik_names(c))[0] >= NAME_OK
        return self._nm[k]

    def anchor_set(self, t, ym):
        return {c for c, src in self.anchors_at(t, ym)}

    def excluded(self, t, ym):
        """수작업 제외 — 이 티커로 제출됐지만 이 발행사가 아닌 CIK(운영 파트너십 · 이름이 비슷한 다른 회사)."""
        return {int(a["cik"]) for a in self.manual.get("exclude", []) if a.get("t") == t and _in_rng(ym, a)}

    def manual_alias(self, t):
        """수작업 티커 별칭 — 제출자가 다른 클래스 표기로 내는 경우(BRK.B → BRKA 등)."""
        out = []
        for a in self.manual.get("alias", []):
            if a.get("t") == t:
                out += a.get("syms", [])
        return out

    def reliable_anchor_ciks(self, t):
        """형제 클래스(GOOG·GOOGL · FOX·FOXA · NWS·NWSA …)를 묶을 때만 쓰는 닻 — SEC company_tickers · cik_map ·
        위키 평면 CIK(단 index_history.cik_conflicts 에 오른 CIK 는 뺀다: 위키 파싱 사고로 무관한 두 회사가 한 CIK 를 가졌다)."""
        if t in self._rel:
            return self._rel[t]
        bad = {int(x["cik"]) for x in (self.R["H"].get("cik_conflicts") or [])}
        out = set()
        for c, src in anchors_static(self.R, t, self.ctk):
            if src in ("company_tickers", "cik_map", "wiki_flat") and c not in bad:
                out.add(c)
        for a in self.manual.get("sibling", []):
            if t in a.get("tickers", []):
                out.add(("sib", a["id"]))
        self._rel[t] = out
        return out

    def siblings(self, t, ym):
        """그달 같은 닻을 공유하는 다른 멤버 티커(이중 클래스). 자기 티커로 DERA 증거가 없을 때만 빌린다."""
        mine = self.reliable_anchor_ciks(t)
        if not mine:
            return []
        return sorted(u for u in self.MM[ym] if u != t and self.reliable_anchor_ciks(u) & mine)

    def manual_resolve(self, t, ym):
        for a in self.manual["resolve"]:
            if a.get("t") == t and _in_rng(ym, a):
                return a
        return None

    # ── 1단계: 원 후보(그룹 전) ───────────────────────────────────────
    def raw_eval(self):
        """(티커, 월) → {src, win, cands{cik: n}, primary}. 그룹을 모르는 상태의 증거."""
        E = {}
        s_first = {}
        for t, ms in self.tmon.items():
            s = norm_sym(t)
            for ym in ms:
                mr = self.manual_resolve(t, ym)
                if mr:
                    E[(t, ym)] = {"src": "manual", "win": None, "cands": {int(mr["cik"]): 1} if mr.get("cik") else {},
                                  "primary": int(mr["cik"]) if mr.get("cik") else None, "why": mr.get("why"),
                                  "syms": [s]}
                    continue
                syms = [s] + [norm_sym(a) for a in self.manual_alias(t)]
                dw = self.dera_window(syms, ym)
                cands, win, src = {}, None, None
                if dw:
                    src = "dera"
                else:
                    sib = self.siblings(t, ym)
                    if sib:
                        syms = [norm_sym(u) for u in sib]
                        dw = self.dera_window(syms, ym)
                        src = "dera_sib" if dw else None
                if dw:
                    win, tot = dw
                    ex = self.excluded(t, ym)
                    if ex:
                        tot = collections.Counter({c: v for c, v in tot.items() if c not in ex})
                        if not tot:
                            dw = None
                if dw:
                    # 잡음 거르기: 제출자가 남의 티커를 적은 건(O → Northern Oil · A → Baldwin & Lyons · PCG → 자회사 유틸리티)
                    #   이름이 명단 이름과 맞거나 닻인 후보가 하나라도 있으면, 둘 다 아닌 후보는 몫 계산에서 뺀다.
                    good = {c for c in tot if self.name_match(t, c) or c in self.anchor_set(t, ym)}
                    if good:
                        tot = collections.Counter({c: v for c, v in tot.items() if c in good})
                        n = sum(tot.values())
                        cands = {c: v for c, v in tot.items() if v / n >= 0.20} or dict(tot.most_common(1))
                    else:
                        # 창 안 DERA 후보가 전부 잡음이면(그달 그 회사 제출이 없고 남의 제출만 있다) 이름이 맞는 산 닻으로 간다.
                        al = [c for c, a in self.anchors_at(t, ym) if self.alive(c, ym) and self.name_match(t, c)]
                        if al:
                            cands, src, win = {c: 1 for c in al}, "anchor:dera_noise", None
                        else:
                            n = sum(tot.values())
                            cands = {c: v for c, v in tot.items() if v / n >= 0.20} or dict(tot.most_common(1))
                # DERA 끝 뒤의 달: 닻 CIK 가 submissions 에 Form 3/4/5 를 냈으면 후보에 더한다(XOM 2026-07 지주사 같은 경우)
                # ⚠ submissions 의 Form 3/4/5 는 그 CIK 가 **보고자**인 제출도 섞인다(Google LLC 가 남의 회사 10% 주주로 낸 것).
                #   그래서 DERA 에 이 티커 제출 이력이 없는 새 CIK(지주사 신설)만 이 경로로 받는다.
                if ym > self.dera_end:
                    for c, _src in self.anchors_at(t, ym):
                        if any((c, x) in self.D.symspan for x in syms) or self.D.span.get(c):
                            continue
                        n2 = sum(v for m, v in self.sub345.get(c, {}).items() if m <= ym)
                        if n2:
                            cands[c] = cands.get(c, 0) + n2
                            src = src or "sub345"
                if not cands:
                    ex = self.excluded(t, ym)
                    al = [(c, a) for c, a in self.anchors_at(t, ym) if self.alive(c, ym) and c not in ex]
                    if al:
                        # 닻이 여럿이면 앞 순위(위키 월별 → 평면 → …) 하나가 아니라 **모두** 후보로 둔다 — 그룹 판정이 가른다
                        cands = {c: 1 for c, a in al}
                        src = "anchor:" + al[0][1]
                prim = None
                if cands:
                    def start(c):
                        vs = [self.D.symspan[(c, x)][0] for x in syms if (c, x) in self.D.symspan]
                        vs = [v for v in vs if v <= _mend(ym)]
                        if vs:
                            return min(vs)
                        if ym > self.dera_end and self.sub345.get(c):
                            return min(m for m in self.sub345[c]) + "-01"
                        return "0000-00-00"
                    prim = max(cands, key=lambda c: (start(c), cands[c]))
                E[(t, ym)] = {"src": src, "win": win, "cands": cands, "primary": prim, "syms": syms}
        return E

    # ── 2단계: 전환(잇기 후보) ───────────────────────────────────────
    def pre_seq(self, t):
        """첫 멤버월 전(2011-01 ~) 의 DERA 주 CIK — 창 이전 재편(ETN 2012 · PRGO 2013 …)의 선행 CIK 를 찾는다.
        분류 이력(직전 3년)이 창 앞 연도까지 닿기 때문이다. 잡음 거르기는 멤버월과 같다."""
        ms = self.tmon[t]
        out = []
        ym = "%04d-%02d" % (Q0[0], 1)
        s = norm_sym(t)
        while ym < ms[0]:
            dw = self.dera_window([s], ym)
            if dw and dw[0].startswith("b"):
                win, tot = dw
                ex = self.excluded(t, ym)
                tot = collections.Counter({c: v for c, v in tot.items() if c not in ex})
                good = {c for c in tot if self.name_match(t, c) or c in self.anchor_set(t, ym)}
                if good:
                    tot = collections.Counter({c: v for c, v in tot.items() if c in good})
                    p = max(tot, key=lambda c: (min([self.D.symspan[(c, s)][0]] if (c, s) in self.D.symspan else ["0"]), tot[c]))
                    out.append((ym, {"primary": p, "src": "dera"}))
            ym = _madd(ym, 1)
        return out

    def transitions(self, E):
        out = {}
        for t, ms in self.tmon.items():
            s = norm_sym(t)
            prev = None
            seq = self.pre_seq(t) + [(ym, E[(t, ym)]) for ym in ms]
            for ym, e in seq:
                p = e["primary"]
                if p is None:
                    continue
                if prev and prev[1] != p and e["src"] in ("dera", "sub345") and prev[2] in ("dera", "sub345"):
                    a, b = prev[1], p
                    key = (a, b)
                    if key not in out:
                        v = self.D.symspan.get((b, s))
                        d_b = v[0] if v else (min(self.sub345[b]) + "-01" if self.sub345.get(b) else ym + "-01")
                        sp_b = self.D.span.get(b)
                        other = self.D.other_sym_before(b, {s}, (dt.date.fromisoformat(d_b) - dt.timedelta(days=183)).isoformat())
                        b_new = ((not sp_b) or sp_b[0] > (dt.date.fromisoformat(d_b) - dt.timedelta(days=365)).isoformat()) and other < 5
                        sp_a = self.D.span.get(a)
                        a_last = sp_a[1] if sp_a else None
                        sub_a_after = sum(v2 for m, v2 in self.sub345.get(a, {}).items())
                        a_ends = (a_last is None or a_last < (dt.date.fromisoformat(d_b) + dt.timedelta(days=183)).isoformat()) \
                            and not (d_b > DERA_LAST_DAY and sub_a_after >= 5 and
                                     max(self.sub345[a]) > _madd(d_b[:7], 3))
                        sim, pair = names_sim(self.cik_names(a), self.cik_names(b))
                        out[key] = {"t": t, "pred": a, "succ": b, "month": ym, "succ_first": d_b, "pred_last": a_last,
                                    "b_new": bool(b_new), "a_ends": bool(a_ends), "succ_other_sym_before": other,
                                    "name_sim": round(sim, 2), "names": [self.cik_label(a), self.cik_label(b)],
                                    "auto": "splice" if (b_new and a_ends and sim >= NAME_OK) else "separate"}
                prev = (ym, p, e["src"])
        return list(out.values())

    def handoffs(self, E):
        """명단 이웃 전환 — X 가 m 에 빠지고 Y 가 m 또는 m+1 에 들어오며, Y 의 CIK 가 새것 · X 의 CIK 가 끝남 · 이름이 맞음."""
        last = self.months[-1]
        leave, join = collections.defaultdict(list), collections.defaultdict(list)
        for t, ms in self.tmon.items():
            if ms[-1] != last:
                leave[ms[-1]].append(t)
            if ms[0] != self.months[0]:
                join[ms[0]].append(t)
        out = []
        for m, xs in leave.items():
            for y in join.get(m, []) + join.get(_madd(m, 1), []):
                for x in xs:
                    a, b = E[(x, m)]["primary"], E[(y, self.tmon[y][0])]["primary"]
                    if not a or not b or a == b:
                        continue
                    sp_a, sp_b = self.D.span.get(a), self.D.span.get(b)
                    d0 = self.tmon[y][0] + "-01"
                    b_new = (not sp_b) or sp_b[0] > (dt.date.fromisoformat(d0) - dt.timedelta(days=365)).isoformat()
                    a_ends = (not sp_a) or sp_a[1] < (dt.date.fromisoformat(d0) + dt.timedelta(days=183)).isoformat()
                    sim, pair = names_sim(self.cik_names(a) | ref_names(self.R, x), self.cik_names(b) | ref_names(self.R, y))
                    if b_new and a_ends and sim >= NAME_OK:
                        out.append({"from_t": x, "to_t": y, "month": m, "pred": a, "succ": b, "name_sim": round(sim, 2),
                                    "names": [self.cik_label(a), self.cik_label(b)], "auto": "separate(검토)"})
        return out

    # ── 3단계: 그룹 ──────────────────────────────────────────────────
    def groups(self, E, trans):
        uf = UF()
        for (t, ym), e in E.items():
            for c in e["cands"]:
                uf.find(c)
        dec = {}
        for s in self.manual["splice"]:
            dec[(int(s["pred"]), int(s["succ"]))] = s
            if s.get("decision") == "splice":
                uf.union(int(s["pred"]), int(s["succ"]))
        pending = [x for x in trans if (x["pred"], x["succ"]) not in dec]
        return uf, dec, pending

    # ── 4단계: (티커, 월) 판정 ───────────────────────────────────────
    def resolve(self, E, uf):
        out = {}
        for (t, ym), e in E.items():
            cands = e["cands"]
            if not cands:
                out[(t, ym)] = {"status": "none", "src": e["src"]}
                continue
            gs = {}
            for c, n in cands.items():
                gs.setdefault(uf.find(c), []).append(c)
            status = "ok"
            if len(gs) > 1:
                # 깨끗한 넘겨받기: 주 CIK 의 그룹이 월말에 효력 중이고, 다른 그룹 CIK 의 이 티커 마지막 제출이
                #   주 CIK 의 이 티커 첫 제출보다 45일 넘게 늦지 않다 → 주 CIK 쪽으로.
                syms = e.get("syms") or [norm_sym(t)]
                pvs = [self.D.symspan[(e["primary"], x)][0] for x in syms if (e["primary"], x) in self.D.symspan]
                pf = min(pvs) if pvs else None
                ok = pf is not None
                for g, cs in gs.items():
                    if g == uf.find(e["primary"]):
                        continue
                    for c in cs:
                        vv = [self.D.symspan[(c, x)] for x in syms if (c, x) in self.D.symspan]
                        v = [min(x[0] for x in vv), max(x[1] for x in vv)] if vv else None
                        if not v or not pf or v[1] > (dt.date.fromisoformat(pf) + dt.timedelta(days=45)).isoformat():
                            ok = False
                status = "ok_handover" if ok else "conflict"
            g = uf.find(e["primary"])
            out[(t, ym)] = {"status": status, "src": e["src"], "win": e["win"], "gid": g, "primary": e["primary"],
                            "cands": cands, "groups": {k: v for k, v in gs.items()}}
        return out

    def name_check(self, M, uf):
        """그룹 이름 대 명단 이름. 맞지 않으면 name 상태 — 수작업 name_ok 가 있으면 통과."""
        okset = {(a["t"], int(a["cik"])) for a in self.manual["name_ok"]}
        gnames = {}
        for (t, ym), r in M.items():
            if r["status"] not in ("ok", "ok_handover"):
                continue
            g = r["gid"]
            if g not in gnames:
                nm = set()
                for c in self.allc:
                    if uf.find(c) == g:
                        nm |= self.cik_names(c)
                gnames[g] = nm
            refs = ref_names(self.R, t)
            if not refs:
                r["name"] = "no_ref"
                continue
            if (t, r["primary"]) in okset or any((t, c) in okset for c in r["cands"]):
                r["name"] = "manual_ok"
                continue
            sim, pair = names_sim(refs, gnames[g])
            r["name_sim"] = round(sim, 2)
            if sim >= NAME_OK:
                r["name"] = "ok"
            else:
                r["name"] = "mismatch"
                r["status"] = "name"
        return gnames

    # ── 5단계: 그룹 CIK 효력 구간 ───────────────────────────────────
    def intervals(self, M, uf, dec):
        OKS = ("ok", "ok_handover")
        gsyms, gmon, used = collections.defaultdict(set), collections.defaultdict(list), collections.defaultdict(set)
        for (t, ym), r in M.items():
            if r["status"] in OKS or (r["status"] == "manual" and r.get("gid") is not None):
                g = r["gid"]
                gsyms[g].add(norm_sym(t))
                gmon[g].append(ym)
                used[g].add(r["primary"])
                for c, n in r["cands"].items():
                    if uf.find(c) == g:
                        used[g].add(c)
        for (a, b), s in dec.items():
            if s.get("decision") == "splice":
                g = uf.find(a)
                if g in used:
                    used[g] |= {a, b}
        IV = {}
        for g, cs in used.items():
            for c in cs:
                spans = [self.D.symspan[(c, s)] for s in gsyms[g] if (c, s) in self.D.symspan]
                if spans:
                    f, l, src = min(x[0] for x in spans), max(x[1] for x in spans), "dera_sym"
                elif self.D.span.get(c):
                    f, l, src = self.D.span[c][0], self.D.span[c][1], "dera_any"
                else:
                    ds = sorted(fd for fm, fd, rd in (self.S.get(c) or {}).get("forms", [])
                                if fm in ANNUAL or fm in PERIODIC or fm == "8-K")
                    f, l, src = (ds[0], ds[-1], "sub") if ds else (None, None, "none")
                # submissions 의 Form 3/4/5 로 뒤를 늘리는 것은 (i) DERA 마지막 분기에도 이 그룹 티커로 내던 CIK 이거나
                #   (ii) DERA 에 아예 없는 새 CIK 일 때만 — 옛 CIK 가 **보고자**로 낸 제출(Google LLC 가 남의 10% 주주)이 섞이지 않게.
                if self.sub345.get(c) and ((spans and l and l >= "2026-04-01") or not self.D.span.get(c)):
                    l2 = _mend(max(self.sub345[c]))
                    l = max(l, l2) if l else l2
                    f = f or (min(self.sub345[c]) + "-01")
                IV[c] = {"from": f, "to": l, "src": src}
            # 열린 끝: 구간은 **그룹 안 CIK 사이의 경계**를 긋는 데만 쓴다(CIK 는 재사용되지 않는다).
            #   가장 이른 CIK 는 앞이, 가장 늦은 CIK 는 뒤가 열린다 — 한 CIK 그룹은 [null, null].
            #   (DERA 첫 제출일로 앞을 닫으면 2026-03 HFIAA 뒤에야 Form 3 을 낸 FPI 의 과거 20-F 가 구간 밖으로 떨어진다.)
            known = [c for c in cs if IV[c]["from"] or IV[c]["to"]]
            if known:
                c0 = min(known, key=lambda c: (IV[c]["from"] or "0000", c))
                IV[c0]["from"] = None
                c1 = max(known, key=lambda c: (IV[c]["to"] or "9999", IV[c]["from"] or "0000"))
                IV[c1]["to"] = None
        return used, IV, gsyms, gmon

    def cik_set(self, g, used, IV, ym, primary):
        lo, hi = ym + "-01", _mend(ym)
        out = set()
        for c in used.get(g, ()):
            iv = IV.get(c) or {}
            if (iv.get("from") or "0000") <= hi and (iv.get("to") or "9999") >= lo:
                out.add(c)
        if primary:
            out.add(primary)
        return sorted(out)

    # ── 6단계: FPI 표지 ──────────────────────────────────────────────
    def annual_lists(self, used, IV):
        AL, PL = {}, {}
        for g, cs in used.items():
            a, p = [], []
            for c in cs:
                iv = IV.get(c) or {}
                lo = _madd((iv.get("from") or "0000-01")[:7], -15) if iv.get("from") else "0000-00"
                hi = _madd((iv.get("to") or "9999-12")[:7], 15) if iv.get("to") else "9999-99"
                for fm, fd, rd in (self.S.get(c) or {}).get("forms", []):
                    if lo <= fd[:7] <= hi:
                        if fm in ANNUAL:
                            a.append((fd, fm, c))
                        elif fm in PERIODIC or fm in REGFORM:
                            p.append((fd, fm, c))
            AL[g], PL[g] = sorted(set(a)), sorted(set(p))
        return AL, PL

    @staticmethod
    def _last_before(lst, end):
        best = None
        for x in lst:
            if x[0] <= end:
                best = x
            else:
                break
        return best

    def fpi_at(self, g, AL, PL, ym):
        """사양 표지: 직전 연차보고(10-K 계 → 0 · 20-F/40-F → 1). 연차보고가 없으면 18개월 안 정기보고(10-Q → 0 · 6-K → 1)."""
        end = _mend(ym)
        a = self._last_before(AL.get(g, []), end)
        if a:
            return ANNUAL[a[1]], {"form": a[1], "fd": a[0], "cik": a[2], "via": "annual"}
        pl = PL.get(g, [])
        p = self._last_before([x for x in pl if x[1] in PERIODIC], end)
        if p and p[0] >= _madd(ym, -18):
            return PERIODIC[p[1]], {"form": p[1], "fd": p[0], "cik": p[2], "via": "periodic"}
        # 신규 상장·분할 직후(첫 연차·분기보고 전): 등록서식(S-1 · S-4 · 10-12B → 0 · F-1 · F-4 → 1)과 8-K(→ 0)
        r = self._last_before([x for x in pl if x[1] in REGFORM], end)
        if r and r[0] >= _madd(ym, -18):
            return REGFORM[r[1]], {"form": r[1], "fd": r[0], "cik": r[2], "via": "registration"}
        return None, None

    def fpi_q_at(self, g, AL, PL, ym, fpi):
        """보조 표지 fpi_q: 20-F/40-F 뒤에 10-Q 를 냈으면(미국 재설립 · FPI 지위 상실 — TEAM 2022-10, NXPI 2019)
        그달부터 0. 그 밖은 사양 표지와 같다. 사양 표지를 바꾸지 않고 옆에 싣는다."""
        if fpi != 1:
            return fpi
        end = _mend(ym)
        a = self._last_before(AL.get(g, []), end)
        if not a:
            return fpi
        for fd, fm, c in PL.get(g, []):
            if fm == "10-Q" and a[0] < fd <= end:
                return 0
        return fpi

    # ── 7단계: F0 ────────────────────────────────────────────────────
    def g345(self, used, IV):
        """그룹 월별 Form 3/4/5 — DERA(발행사 CIK 기준) + DERA 끝 뒤 달은 submissions(뒤가 열린 CIK 만 · 보고자 제출이 섞일 수 있다)."""
        out = {}
        for g, cs in used.items():
            cnt = collections.Counter()
            for c in cs:
                for ym, v in (self.D.cikcnt.get(c) or {}).items():
                    cnt[ym] += sum(v)
                iv = IV.get(c) or {}
                if iv.get("to") is None or iv["to"] > DERA_LAST_DAY:
                    for ym, v in self.sub345.get(c, {}).items():
                        if ym > self.dera_end:
                            cnt[ym] += v
            out[g] = cnt
        return out


def _runs(items):
    """[(월, 값)] (월 오름차순) → [[첫, 끝, 값]] — 값이 같고 달이 이어질 때 묶는다."""
    out = []
    for ym, v in items:
        if out and out[-1][2] == v and _madd(out[-1][1], 1) == ym:
            out[-1][1] = ym
        else:
            out.append([ym, ym, v])
    return out


CRIT_2016 = ["DIS", "AVGO", "CI", "DD", "DOW", "APA", "FOX", "FOXA", "FTI", "IR", "MYL", "WRK", "XRX", "MDT", "XOM"]


def cmd_build():
    t0 = time.time()
    B = Builder()
    print("멤버-월 %d개월 · 티커 %d · 후보 CIK %d · submissions 없음 %d · DERA Form 3/4/5 %d건 (%.0fs)"
          % (len(B.months), len(B.tmon), len(B.allc), len(B.missing_sub), B.D.n_rows, time.time() - t0), flush=True)
    E = B.raw_eval()
    trans = B.transitions(E)
    hand = B.handoffs(E)
    uf, dec, pending = B.groups(E, trans)
    M = B.resolve(E, uf)
    # 수작업 해결(resolve)은 그룹 판정 전에 들어갔다 — gid 만 채운다
    for (t, ym), r in M.items():
        if E[(t, ym)]["src"] == "manual":
            if E[(t, ym)]["primary"]:
                r["status"] = "manual"
                r["gid"] = uf.find(E[(t, ym)]["primary"])
            else:
                r["status"] = "manual_none"      # 수작업으로 «CIK 없음/측정 불가» 확정
            r["why"] = E[(t, ym)].get("why")
    gnames = B.name_check(M, uf)
    used, IV, gsyms, gmon = B.intervals(M, uf, dec)
    AL, PL = B.annual_lists(used, IV)
    G345 = B.g345(used, IV)

    OKS = ("ok", "ok_handover", "manual")
    # 그룹 이름: union-find 뿌리(가장 작은 CIK)가 아니라 멤버-월에서 가장 자주 주 CIK 였던 것(동률이면 늦은 CIK)
    prim_n = collections.defaultdict(collections.Counter)
    for (t, ym), r in M.items():
        if r["status"] in OKS:
            prim_n[r["gid"]][r["primary"]] += 1
    GN = {g: max(cnt, key=lambda c: (cnt[c], c)) for g, cnt in prim_n.items()}
    tm = collections.defaultdict(list)
    viol, bym = [], {}
    viol_sp, bym_sp = [], {}                     # 사양 칸(fpi) 으로 센 F0 — 비교용(등록 표지는 fpi_q · FPI_REGISTERED)
    fpi_rows, fpi_null = [], []
    fpi_reg_rows = []
    fpi_g, fpi_y = {}, {}
    fpi_q_diff = []
    per_m = collections.defaultdict(lambda: collections.Counter())
    for ym in B.months:
        for t in sorted(B.MM[ym]):
            r = M[(t, ym)]
            st = r["status"]
            per_m[ym][st] += 1
            if st in OKS:
                g = r["gid"]
                cs = B.cik_set(g, used, IV, ym, r["primary"])
                fpi, ev = B.fpi_at(g, AL, PL, ym)
                fpq = B.fpi_q_at(g, AL, PL, ym, fpi)
                if fpq != fpi:
                    fpi_q_diff.append((t, ym))
                val = (g, r["primary"], tuple(cs), fpi, (r["src"] or "").split(":")[0], fpq)
                tm[t].append((ym, val))
                if fpi == 1:
                    fpi_rows.append((t, ym))
                    fpi_g[t] = g
                    n12 = sum(v for m, v in G345[g].items() if _madd(ym, -11) <= m <= ym)
                    fy = fpi_y.setdefault(ym[:4], [0, 0])
                    fy[0] += 1
                    fy[1] += 1 if n12 > 0 else 0
                elif fpi is None:
                    fpi_null.append((t, ym))
                freg = fpq if FPI_REGISTERED == "fpi_q" else fpi          # 등록 표지(2026-09-25 권고 fpi_q)
                if freg == 1:
                    fpi_reg_rows.append((t, ym))
                n12 = sum(v for m, v in G345[g].items() if _madd(ym, -11) <= m <= ym)
                for flag, vl, bb in ((freg, viol, bym), (fpi, viol_sp, bym_sp)):
                    if flag != 1:
                        b = bb.setdefault(ym, [0, 0])
                        b[0] += 1
                        if n12 == 0:
                            b[1] += 1
                            vl.append([t, ym, "g%d" % GN[g], r["primary"], flag])
            else:
                tm[t].append((ym, (None, None, (), None, st, None)))

    # ── 대기열(수작업 검토) ────────────────────────────────────────
    Q = []
    for t, ms in B.tmon.items():
        bad = [(ym, M[(t, ym)]["status"]) for ym in ms if M[(t, ym)]["status"] in ("conflict", "none", "name")]
        for a, b, st in _runs(bad):
            r = M[(t, a)]
            item = {"kind": st, "t": t, "from": a, "to": b, "ref_names": sorted(ref_names(B.R, t))}
            if st == "conflict":
                tot = collections.Counter()
                for ym in ms:
                    if a <= ym <= b:
                        tot.update(M[(t, ym)]["cands"])
                item["cands"] = [{"cik": c, "name": B.cik_label(c), "n": n, "group": uf.find(c),
                                  "dera_span": B.D.span.get(c), "sub_tickers": (B.S.get(c) or {}).get("tickers")}
                                 for c, n in tot.most_common(6)]
            elif st == "none":
                item["anchors"] = [{"cik": c, "src": s, "name": B.cik_label(c), "alive": B.alive(c, a),
                                    "sub_first": (B.S.get(c) or {}).get("first"), "sub_last": (B.S.get(c) or {}).get("last")}
                                   for c, s in B.anchors_at(t, a)]
            else:
                item["primary"] = r["primary"]
                item["primary_names"] = sorted(B.cik_names(r["primary"]))[:8]
                item["name_sim"] = r.get("name_sim")
                item["src"] = r["src"]
            Q.append(item)
    for x in pending:
        Q.append(dict(x, kind="transition"))
    for x in hand:
        if (x["pred"], x["succ"]) not in dec:
            Q.append(dict(x, kind="handoff"))
    # 위키 월별 CIK 가 다른 살아 있는 그룹을 가리키는 달
    wd = []
    for t, ms in B.tmon.items():
        rows = []
        for ym in ms:
            r = M[(t, ym)]
            w = wiki_month_cik(B.R, t, ym)
            if not w or r["status"] not in OKS:
                continue
            if uf.find(w) != r["gid"] and B.D.f345(w, _madd(ym, -3), _madd(ym, 3)) > 0:
                rows.append((ym, (w, r["primary"])))
        for a, b, (w, p) in _runs(rows):
            wd.append({"t": t, "from": a, "to": b, "wiki_cik": w, "wiki_name": B.cik_label(w), "map_primary": p,
                       "map_name": B.cik_label(p)})
    ver = B.manual.get("verified", [])

    def _verified(x):
        for v in ver:
            if v.get("kind") == x["kind"] and v.get("t") == x.get("t") and \
                    (v.get("from") or "0000") <= (x.get("from") or x.get("month") or "") <= (v.get("to") or "9999"):
                return v.get("why") or True
        return None

    for x in wd:
        x["verified"] = _verified(dict(x, kind="wiki_disagree"))
        if not x["verified"]:
            Q.append(dict(x, kind="wiki_disagree"))
    # 명단 이름이 없는 티커(NDX 전용 · 위키 이름 칸 없음) — 자동으로는 이름을 못 맞춘다. 그룹 이름을 사람이 본다.
    okset = {(a["t"], int(a["cik"])) for a in B.manual["name_ok"]}
    noref = []
    for t, ms in sorted(B.tmon.items()):
        if ref_names(B.R, t):
            continue
        rows = [(ym, (M[(t, ym)]["primary"], M[(t, ym)]["status"] == "manual")) for ym in ms if M[(t, ym)]["status"] in OKS]
        for a, b, (p, man_) in _runs(rows):
            item = {"t": t, "from": a, "to": b, "primary": p, "names": sorted(B.cik_names(p))[:6],
                    "sub_tickers": (B.S.get(p) or {}).get("tickers"),
                    "verified": "name_ok" if (t, p) in okset else ("manual_resolve" if man_ else None)}
            noref.append(item)
            if not item["verified"]:
                Q.append(dict(item, kind="noref"))
    _wj(QUEUE, {"generated": _now(), "n": len(Q), "items": Q}, indent=1)
    kinds = collections.Counter(x["kind"] for x in Q)
    print("수작업 대기열 %d건 %s → %s" % (len(Q), dict(kinds), QUEUE))

    # ── 산출 ───────────────────────────────────────────────────────
    groups = {}
    for g, cs in sorted(used.items(), key=lambda x: GN.get(x[0], x[0])):
        if g not in GN:
            continue
        tick = collections.defaultdict(list)
        for (t, ym), r in M.items():
            if r["status"] in OKS and r["gid"] == g:
                tick[t].append(ym)
        runs_a = []
        for fd, fm, c in AL.get(g, []):
            if runs_a and runs_a[-1][2] == fm:
                runs_a[-1][1] = fd
            else:
                runs_a.append([fd, fd, fm])
        groups["g%d" % GN[g]] = {
            "ciks": [[c, IV[c]["from"], IV[c]["to"], IV[c]["src"], B.cik_label(c)]
                     for c in sorted(cs, key=lambda c: (IV[c]["from"] or "0000", c))],
            "tickers": {t: [min(v), max(v)] for t, v in sorted(tick.items())},
            "annual": runs_a,
        }
    tm_out = {}
    for t, items in sorted(tm.items()):
        tm_out[t] = [[a, b, ("g%d" % GN[v[0]]) if v[0] is not None else None, v[1], list(v[2]), v[3], v[4], v[5]]
                     for a, b, v in _runs(items)]

    total = sum(len(B.MM[m]) for m in B.months)
    stat = collections.Counter()
    for m in B.months:
        stat.update(per_m[m])
    res_n = stat["ok"] + stat["ok_handover"] + stat["manual"]
    by_year = {}
    for m in B.months:
        y = m[:4]
        v = by_year.setdefault(y, [0, 0])
        v[0] += len(B.MM[m])
        v[1] += per_m[m]["ok"] + per_m[m]["ok_handover"] + per_m[m]["manual"]
    bad_months = sorted(m for m, (n, k) in bym.items() if n and k / n > 0.02)
    src_c = collections.Counter()
    for t, items in tm.items():
        for ym, v in items:
            if v[0] is not None:
                src_c[v[4]] += 1
    # 비평 대조(2016-08 · XOM)
    crit = {}
    for t in CRIT_2016:
        for ym in ("2016-08", "2025-08", "2026-08"):
            if (t, ym) in M:
                r = M[(t, ym)]
                if r["status"] in OKS:
                    cs = B.cik_set(r["gid"], used, IV, ym, r["primary"])
                    q0, q1 = _madd(ym, -1), _madd(ym, 1)

                    def n345(c):
                        return B.D.f345(c, q0, q1) + sum(v for m, v in B.sub345.get(c, {}).items()
                                                          if q0 <= m <= q1 and m > B.dera_end)
                    fw = (B.R["H"].get("cik") or {}).get(t)
                    crit.setdefault(t, {})[ym] = {"ciks": cs, "flat_wiki": int(fw) if fw else None,
                                                  "f345_3m": sum(n345(c) for c in cs),
                                                  "f345_3m_flat_wiki": n345(int(fw)) if fw else None}
                else:
                    crit.setdefault(t, {})[ym] = {"status": r["status"]}
    # 분류 이력 창(2011~2013): 2014-06~2016-12 멤버 그룹 가운데 해마다 Form 3/4/5 가 있는 비율
    hist = {}
    gs16 = {r["gid"] for (t, ym), r in M.items() if r["status"] in OKS and ym <= "2016-12"}
    for y in ("2011", "2012", "2013", "2014", "2015"):
        n = sum(1 for g in gs16 if sum(v for m, v in G345[g].items() if m[:4] == y) > 0)
        hist[y] = [n, len(gs16)]
    fpi_t = sorted({t for t, ym in fpi_rows})
    # 평면 지도(index_history.cik · 티커 → 마지막 CIK)였다면: 멤버-월마다 CIK 없음 / 직전 12개월 Form 3/4/5 0건 — 비교용
    flat = {}
    Hc = B.R["H"].get("cik") or {}
    fpi_set = set(fpi_rows)
    for ym in B.months:
        y = ym[:4]
        v = flat.setdefault(y, [0, 0, 0, 0])
        for t in B.MM[ym]:
            if (t, ym) in fpi_set:
                continue
            v[0] += 1
            fc = Hc.get(t)
            if not fc:
                v[1] += 1
                continue
            c = int(fc)
            n = B.D.f345(c, _madd(ym, -11), ym) + sum(x for m, x in B.sub345.get(c, {}).items()
                                                     if m > B.dera_end and _madd(ym, -11) <= m <= ym)
            if n == 0:
                v[2] += 1
        v[3] += sum(1 for x in viol if x[1] == ym)
    # Stage M 창(2016-08..2026-07) 요약 — 비금융(그달 GICS) · FPI 아님 · F0 통과. 등록 표지(fpi_q)와 사양 칸(fpi) 둘 다.
    vset = {(x[0], x[1]) for x in viol}
    vset_sp = {(x[0], x[1]) for x in viol_sp}
    tmv = {(t, m): v for t, items in tm.items() for m, v in items}
    sm, sm_sp = ({"member_months": 0, "nonfin": 0, "nonfin_nonfpi": 0, "nonfin_nonfpi_f0pass": 0, "nonfin_fpi": 0,
                  "nonfin_fpi_null": 0} for _ in range(2))
    fpi_by_m = {}
    sec_src = {"stage_m": collections.Counter(), "all": collections.Counter()}
    sec_fb = collections.defaultdict(lambda: collections.defaultdict(list))   # 출처 → 티커 → 달(비PIT 대체 · 수작업)
    for ym in B.months:
        nf = 0
        for t in B.MM[ym]:
            v = tmv.get((t, ym))
            fp = v[3] if v else None
            fq = v[5] if v else None
            if fp == 1:
                nf += 1
            sec, ss = sector_src_at(B.R, t, ym)
            sec_src["all"][ss] += 1
            win = "2016-08" <= ym <= "2026-07"
            if win:
                sec_src["stage_m"][ss] += 1
            if ss != "wiki_pit":
                sec_fb[ss][t].append((ym, sec, win))
            if not win:
                continue
            for d, flag, vs in ((sm, fq if FPI_REGISTERED == "fpi_q" else fp, vset), (sm_sp, fp, vset_sp)):
                d["member_months"] += 1
                if sec in FIN:
                    continue
                d["nonfin"] += 1
                if flag == 1:
                    d["nonfin_fpi"] += 1
                    continue
                if flag is None:
                    d["nonfin_fpi_null"] += 1
                d["nonfin_nonfpi"] += 1
                if (t, ym) not in vs:
                    d["nonfin_nonfpi_f0pass"] += 1
        fpi_by_m[ym] = nf
    # 비PIT 섹터 대체 선언 — 출처별 티커 · 달 수(창 안 · 밖) · 2018-09 GICS 개편과 어긋날 수 있는 달
    sec_decl = {}
    for ss, byt in sorted(sec_fb.items()):
        rows_ = []
        for t, v in sorted(byt.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            secs = sorted({x[1] or "" for x in v})
            cs_pre = sum(1 for ym, sc, w in v if sc == "Communication Services" and ym < "2018-09")
            tel_post = sum(1 for ym, sc, w in v if sc in ("Telecommunication Services", "Telecommunications Services")
                           and ym >= "2018-09")
            rows_.append([t, sum(1 for x in v if x[2]), sum(1 for x in v if not x[2]), v[0][0], v[-1][0], secs, cs_pre, tel_post])
        sec_decl[ss] = {"member_months_stage_m": sum(r_[1] for r_ in rows_), "member_months_other": sum(r_[2] for r_ in rows_),
                        "tickers": len(rows_), "rows": rows_,
                        "financials_member_months": sum(1 for t, v in byt.items() for ym, sc, w in v if sc in FIN)}
    # FPI 멤버의 Form 3/4/5 — 2026-03-18 HFIAA(외국 사적발행인 이사·임원 Section 16(a) 보고) 전후
    hfiaa = {}
    for t in fpi_t:
        g = fpi_g[t]
        pre = sum(v for m, v in G345[g].items() if "2025-01" <= m <= "2026-02")
        post = sum(v for m, v in G345[g].items() if m >= "2026-03")
        if pre or post:
            hfiaa[t] = [pre, post]
    cov = {
        "member_months": total, "resolved": res_n, "resolved_share": round(res_n / total, 5),
        "status": dict(stat), "src": dict(src_c),
        "by_year": {y: [n, k, round(k / n, 4)] for y, (n, k) in sorted(by_year.items())},
        "unresolved": [[t, a, b, st] for t, items in sorted(tm.items()) for a, b, (g, p, cs, f, st, fq) in _runs(items)
                       if g is None],
        "fpi_q_differs": [[t, a, b] for t, a, b in _runs2(fpi_q_diff)],
        "fpi_member_months": len(fpi_rows), "fpi_tickers": fpi_t, "fpi_null_member_months": len(fpi_null),
        "fpi_null": [[t, a, b] for t, a, b in _runs2(fpi_null)],
        "fpi_form345_2025_01_2026_02_vs_2026_03_on": dict(sorted(hfiaa.items())),
        "fpi_member_months_with_f345_12m_by_year": {y: [n, k] for y, (n, k) in sorted(fpi_y.items())},
        "hist_f345_groups_2014_16": hist,
        "flat_map_by_year": {y: {"nonfpi_member_months": a, "no_flat_cik": b, "flat_cik_zero_f345_12m": c,
                                 "new_map_zero_f345_12m": d} for y, (a, b, c, d) in sorted(flat.items())},
        "stage_m_window_2016_08_2026_07": sm, "stage_m_window_2016_08_2026_07_spec_fpi": sm_sp,
        "fpi_registered_vs_spec": {
            "registered": FPI_REGISTERED, "spec_member_months_fpi1": len(fpi_rows), "registered_member_months_fpi1": len(fpi_reg_rows),
            "differ": [[t, a, b] for t, a, b in _runs2(sorted(set(fpi_rows) - set(fpi_reg_rows)))],
            "differ_member_months": len(set(fpi_rows) - set(fpi_reg_rows)),
            "stage_m_nonfin_nonfpi": [sm_sp["nonfin_nonfpi"], sm["nonfin_nonfpi"]],
            "stage_m_nonfin_nonfpi_f0pass": [sm_sp["nonfin_nonfpi_f0pass"], sm["nonfin_nonfpi_f0pass"]],
            "note": "[사양 칸 fpi · 등록 fpi_q] — 사양 규칙(직전 연차보고 20-F/40-F)은 이미 10-Q 를 낸 TEAM · NXPI 를 FPI 로 둔다. 등록 권고: "
                    "fpi_q(직전 정기보고가 10-Q 면 FPI 아님). 두 칸을 모두 싣는다(tm 5 = 사양 · 7 = fpi_q). 읽는 쪽은 "
                    "fpi_registered.tm_index 칸을 쓴다(r_r1_flags · ins_pit_build 는 그렇게 읽는다)."},
        "sector_sources": {"rule": "sector_at = 위키 PIT(SPX 표 · 섹터 칸이 빈 달 제외) → 수작업 표(_issuer_map_sector_manual.json · 그때 GICS) → "
                                   "index_history 섹터(티커당 한 값 · 비PIT) → stocks.json 오늘 섹터(비PIT). 비PIT 두 출처를 여기 선언한다 — "
                                   "금융(Financials)은 하나도 없어 Stage M 세계(비금융)는 바뀌지 않고, Stage M 섹터 더미만 근사다. "
                                   "행 = [티커, 창 안 멤버-월, 창 밖, 첫 달, 끝 달, 섹터들, 2018-09 전인데 Communication Services 인 달, "
                                   "2018-09 뒤인데 Telecommunication Services 인 달].",
                           "counts_stage_m_2016_08_2026_07": dict(sec_src["stage_m"]), "counts_all_months": dict(sec_src["all"]),
                           "by_source": sec_decl},
        "fpi_members_by_month": fpi_by_m,
        "note_2011_2014": "PIT 명단(index_history)은 2014-06 부터다(위키 표에 CIK 열이 생긴 첫 달). 2011-01..2014-05 는 명단이 없어 "
                          "멤버-월 커버리지를 잴 수 없다 — 그 구간은 그룹 CIK 구간(앞이 열린 끝)과 DERA 존재율(hist_f345_groups_2014_16)로만 본다.",
        "n_groups": len(groups), "multi_cik_groups": sorted(g for g, v in groups.items() if len(v["ciks"]) > 1),
        "wiki_disagree": wd, "noref": noref, "crit_2016": crit,
        "manual": {k: len(v) for k, v in B.manual.items() if isinstance(v, list)},
        "unjoined_form4_member_months": unjoined_f4(B, M, used, IV, OKS, B.manual),
        "queue": dict(kinds), "missing_submissions": B.missing_sub,
    }
    bad_sp = sorted(m for m, (n, k) in bym_sp.items() if n and k / n > 0.02)
    f0 = {"rule": "FPI 가 아닌(등록 표지 %s) 멤버-월마다 그룹 CIK 로 제출월 m−11..m 에 Form 3/4/5 ≥ 1. 위반율 > 2%% 인 달은 측정 불가. "
                  "DERA 2011Q1..2026Q2 · 그 뒤 달은 submissions 의 Form 3/4/5. spec_flag = 사양 칸 fpi 로 센 같은 검사(비교)." % FPI_REGISTERED,
          "fpi_flag": FPI_REGISTERED,
          "n_checked": sum(v[0] for v in bym.values()), "n_viol": len(viol),
          "by_month": {m: [n, k, round(k / n, 4) if n else None] for m, (n, k) in sorted(bym.items())},
          "bad_months": bad_months, "violations": viol,
          "spec_flag": {"n_checked": sum(v[0] for v in bym_sp.values()), "n_viol": len(viol_sp), "bad_months": bad_sp,
                        "violations": viol_sp,
                        "only_registered_viol": sorted([x[0], x[1]] for x in viol if (x[0], x[1]) not in vset_sp),
                        "only_spec_viol": sorted([x[0], x[1]] for x in viol_sp if (x[0], x[1]) not in vset)}}
    acc = _rj(os.path.join(RAW, "_access_check.json")) or {}
    doc = {
        "note": "§A0 날짜 인식 발행사 지도 + §B Section 16(FPI) 표지. (티커, 월) → 발행사 그룹 · 그달 CIK 집합 · 주 CIK · fpi. "
                "만든 규칙은 build/issuer_map.py 머리말. 자료 빌드다 — 표지와 수익의 관계는 계산하지 않았다.",
        "generated": _now(),
        "tm_format": "tm[티커] = [[첫 달, 끝 달, 그룹, 주 CIK, [그달 CIK 집합], fpi(사양: 직전 연차보고 20-F/40-F → 1 · 10-K → 0 · "
                     "모름 null), 출처, fpi_q(20-F 뒤 10-Q 를 냈으면 0 — 등록 권고 표지 · fpi_registered)]] — "
                     "출처 dera(DERA 티커 몫) · anchor(위키·SEC 닻) · sub345(DERA 끝 뒤 submissions) · manual. "
                     "그룹이 null 이면 해결 못 한 멤버-월(상태가 출처 칸에 있다).",
        "groups_format": "groups[그룹] = {ciks: [[CIK, 효력 시작, 효력 끝, 근거, 이름]] (null = 열린 끝), "
                         "tickers: {티커: [첫 달, 끝 달]}, annual: [[첫 제출일, 끝 제출일, 연차보고 서식]]}",
        "fpi_registered": {"field": FPI_REGISTERED, "tm_index": 7 if FPI_REGISTERED == "fpi_q" else 5,
                           "why": "사양 표지(직전 연차보고 20-F/40-F)는 FPI 지위를 잃고 10-Q 를 낸 TEAM 2022-11..2023-07 · NXPI 2019-10..2020-01 "
                                  "(13 멤버-월)을 Section 16 비적용으로 떨어뜨린다(TEAM 내부자는 2022-10 부터 Form 3/4 를 냈다). "
                                  "등록 권고 = fpi_q(직전 정기보고가 10-Q 면 FPI 아님). 사양 칸은 지우지 않고 tm 5 번에 남긴다.",
                           "decided": "2026-09-25 등록 전 권고(데이터 빌드) — 등록 커밋이 확정한다"},
        "months": [B.months[0], B.months[-1], len(B.months)], "carried": B.carried,
        "dera": {"quarters": "%dq%d..%dq%d" % (Q0[0], Q0[1], Q1[0], Q1[1]), "form345_rows": B.D.n_rows},
        "access_check": [{k: v for k, v in c.items() if k in ("url", "status", "content_encoding", "blocked_page",
                                                             "json", "wire_bytes", "body_bytes", "at")}
                         for c in acc.get("checks", [])],
        "inputs": B.R["inputs"],
        "pins": {"ins_manifest": _sha_file(MAN_INS) if os.path.exists(MAN_INS) else None,
                 "im_manifest": _sha_file(MAN_IM) if os.path.exists(MAN_IM) else None,
                 "manual": _sha_file(MANUAL) if os.path.exists(MANUAL) else None,
                 "sector_manual": _sha_file(SECTOR_MANUAL) if os.path.exists(SECTOR_MANUAL) else None,
                 "script": _sha_file(os.path.abspath(__file__))},
        "splices": [dict(v) for v in B.manual["splice"]],
        "coverage": cov, "f0": f0,
        "groups": groups, "tm": tm_out,
    }
    _wj_stable(OUT, doc)
    print("→ %s %.0fKB · 멤버-월 %d · 해결 %d (%.2f%%) · 상태 %s · FPI 멤버-월 %d(%d종) · null %d · F0 위반 %d · 측정 불가 달 %d · %.0fs"
          % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024, total, res_n, 100 * res_n / total, dict(stat),
             len(fpi_rows), len(fpi_t), len(fpi_null), len(viol), len(bad_months), time.time() - t0))
    return doc


def _runs2(pairs):
    """[(티커, 월)] → [(티커, 첫, 끝)] 연속 구간."""
    by = collections.defaultdict(list)
    for t, ym in pairs:
        by[t].append(ym)
    out = []
    for t, ms in sorted(by.items()):
        for a, b, _ in _runs([(m, 1) for m in sorted(ms)]):
            out.append((t, a, b))
    return out


# ════════════════════════════════════════════════════════════════════════
# 쓰는 쪽 도우미(§A · §B · §C · §G)
# ════════════════════════════════════════════════════════════════════════
def load_map(path=OUT):
    """data/_issuer_map.json → {'idx': {(티커, 월): {...}}, 'groups': …, 'doc': …}."""
    d = _rj(path)
    idx = {}
    for t, runs in d["tm"].items():
        for a, b, g, p, cs, fpi, src, fpq in runs:
            ym = a
            while ym <= b:
                idx[(t, ym)] = {"gid": g, "primary": p, "ciks": cs, "fpi": fpi, "src": src, "fpi_q": fpq,
                                "fpi_reg": fpq if (d.get("fpi_registered") or {}).get("field") == "fpi_q" else fpi}
                ym = _madd(ym, 1)
    return {"idx": idx, "groups": d["groups"], "doc": d}


def current_ciks(path=OUT, ym=None):
    """전방 수집(§G)용 — 최근 멤버-월의 그룹 CIK 가운데 효력이 열린 것 전부."""
    d = _rj(path)
    ym = ym or d["months"][1]
    gs = set()
    for t, runs in d["tm"].items():
        for a, b, g, p, cs, fpi, src, fpq in runs:
            if g and a <= ym <= b:
                gs.add(g)
    out = set()
    for g in gs:
        for c, f, to, src, nm in d["groups"][g]["ciks"]:
            if to is None or to >= _madd(ym, -12):
                out.add(c)
    return sorted(out)


# ════════════════════════════════════════════════════════════════════════
def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "check":
        cmd_check()
    elif cmd == "dera":
        cmd_dera()
    elif cmd == "sub":
        cmd_sub(refresh="--refresh" in argv)
    elif cmd == "search":
        cmd_search([a for a in argv[2:] if not a.startswith("--")])
    elif cmd == "build":
        cmd_build()
    elif cmd == "all":
        cmd_check()
        cmd_dera()
        cmd_sub()
        cmd_build()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
