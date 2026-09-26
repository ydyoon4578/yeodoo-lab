#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§G 전방 일간 Form 4 수집 — EDGAR daily-index form.idx → §A0 지도의 현재 CIK → Form 4 · 4/A 원문 → XML 행

무엇을·왜.
  DERA 분기 자료는 분기가 끝나고 몇 주 뒤에야 나온다(2026Q2 판 2026-07-09 게시). R1 전방 팔은 그 사이의 달을 봐야 하므로
  EDGAR 일간 색인에서 세계 발행사의 Form 4 · 4/A 만 골라 원문 XML 을 읽는다. 행은 §A(build/ins_pit_build.py)의 원 행과
  **같은 칸 이름**으로 만든다 — 그래서 DERA 패널과 이어 붙여 같은 정리(clean)를 한 번에 건다.

경로.
  1 색인   https://www.sec.gov/Archives/edgar/daily-index/YYYY/QTRn/form.YYYYMMDD.idx (분기 디렉터리의 index.json 으로 날을 안다).
  2 거르기 서식 4 · 4/A 줄 가운데 CIK 가 그달 §A0 지도의 현재 CIK(issuer_map.current_ciks(그달))인 것 — 한 제출이 발행사·보고자마다
          한 줄씩 나오므로 접수번호로 묶는다. 보고자 CIK 로만 걸린 제출(세계 회사가 남의 10% 보유자)은 XML 을 읽은 뒤 발행사가
          세계 밖이면 버리고 센다.
  3 원문   edgar/data/<CIK>/<접수번호>.txt 1건 = 요청 1건. <XML> 블록의 ownershipDocument 를 읽는다. 머리의 ACCEPTANCE-DATETIME 과
          FILED AS OF DATE 도 싣는다(DERA 에는 접수 시각이 없다 — 가용일 규칙은 §A 와 같게 FILING_DATE 다음 NYSE 거래일로 둔다).
  4 XML 행 nonDerivativeTransaction 가운데 코드 P · S. 행 각주 = DERA *_FN 열과 같은 12자리(securityTitle · transactionDate ·
          deemedExecutionDate · transactionCoding · transactionTimeliness · transactionShares · transactionPricePerShare ·
          transactionAcquiredDisposedCode · sharesOwnedFollowingTransaction · valueOwnedFollowingTransaction ·
          directOrIndirectOwnership · natureOfOwnership)의 footnoteId 를 그 순서로. 그 밖 자리의 footnoteId 는 뒤에 붙이고 센다.
          관계 = isDirector · isOfficer · isTenPercentOwner · isOther → DERA 식 문자열. aff10b5One · remarks · documentType(정정 여부).
  5 표지   강제 매도 · 10b5-1 식은 build/r_r1_flags.py 의 한 벌을 ins_pit_build 를 거쳐 그대로 쓴다(P.is_stc · P.is_stc_v1 ·
          P.plan_hit — 2026-09-25 등록 전 수정 식 · 옛 식 판정은 감사 칸 stc_v1). 정리(clean)도 ins_pit_build 의 것 — 4/A 정정
          (r_r1_flags 선언 q)이 DERA 패널과 이어진다: 7월 4/A 가 6월 원 행을 고치면 그 4/A 행은 사건이 아니고(cnt 0 · corr 2), 고쳐진 6월
          원 행(DERA 패널 파일은 다시 쓰지 않는다)은 forward.json 의 back_corrections 에 적는다. 거래일만 고친 4/A(선언 q2 · corr 3)도 같다
          (back_tdate_corrections). XML 의 dateOfOriginalSubmission 이 DERA 의 DATE_OF_ORIG_SUB 자리다.
  6 원장  🔒 달 파일은 «그달 끝 현재» 로 쓴다(2026-09-26 · 검토 지적 — 뒤 4/A 가 앞 달 파일을 다시 쓰면 전방 원장이 덧붙이기만이 아니다).
          1차 값(sh · px · usd)은 제출된 그대로라 뒤 4/A 가 바꾸지 않는다(선언 q). 뒤 달에 제출된 4/A 가 고친 칸(corr 1 · shc · pxc · usdc ·
          ctgt · tdh)은 앞 달 파일에 넣지 않고 forward.json 의 late_corrections 에만 적는다. 다 찬 달의 파일 sha256 이 지난 실행과 다르면
          forward.json complete_months_changed 에 적는다(지도 · 규칙이 바뀐 경우 등 — 감사).

판 고정 — 받은 파일(색인 · 원문)마다 sha256 을 data/_ins_daily/manifest/YYYY-MM.json 에 적는다(원문은 저장소 밖 RAW/daily).
  다시 받았을 때 해시가 바뀌면 멈춘다. 그달 CIK 집합의 해시와 지도 해시도 같이 적는다.

출력.
  data/_ins_daily/manifest/YYYY-MM.json   색인·원문 sha256 · 날짜별 개수
  data/_ins_daily/ps/ps_YYYY-MM.json.gz   전방 달(DERA 끝 2026-06-30 뒤)의 정리된 P/S 행 — §A 패널과 같은 칸 + adt(접수 시각).
                                          정리는 DERA 패널 전체 + 일간 행을 한 번에 clean 한 결과에서 DERA 끝 뒤 행만 싣는다
                                          (7월의 4/A 가 6월 원본을 지우는 정정 중복이 이어진다).
  data/_ins_daily/forward.json            전방 요약 — 받은 색인 날 수(index_days · 2026-07-01..09-24 = 22 + 21 + 17 = 60일) · 달별 파일 ·
                                          가용월 밀도 · back_corrections(전방 4/A 가 고친 DERA 기간 원 행).
  data/_ins_daily/test_2026q2.json        일치 시험(사양 §G): 2026Q2 를 이 경로로 다시 만들어 DERA 와 대조.
                                          (그룹, 보고자, 거래일, 코드, 수량, 단가) 행 일치율 ≥ 99.5% · 회사-월 OS 불일치 ≤ 1%.
  ⚠ HFIAA(2026-03-18 로 알려진 FPI 이사·임원 Section 16(a) 보고)로 FPI 멤버도 Form 4 를 낸다 — 이 수집은 지도의 현재 CIK 를
    FPI 여부와 무관하게 다 받는다. FPI 이름을 R1 전방 팔에 넣을지는 쓰는 쪽의 결정이다(fpi 표지는 지도에 있다).
  🚨 자료 빌드다 — 어떤 표지와 수익의 관계도 계산하지 않는다.

SEC 접속 — 모든 요청이 build/edgar.py 를 거친다(초당 8회 · gzip · 백오프). 🚨 SEC_UA 환경변수가 없으면 실행을 거부한다.

사용:
    SEC_UA="이름 연락처" python build/ins_daily.py check
    SEC_UA=...            python build/ins_daily.py day 2026-09-24          # 하루 받기(색인 + 원문)
    SEC_UA=...            python build/ins_daily.py range 2026-04-01 2026-06-30
    SEC_UA=...            python build/ins_daily.py forward [--until YYYY-MM-DD]   # DERA 끝 다음날부터 빠진 날 · 그다음 panel
    SEC_UA=...            python build/ins_daily.py panel                   # 받은 원문 → 전방 패널
    SEC_UA=...            python build/ins_daily.py test 2026q2             # 일치 시험(받기 포함)
    (어느 명령이든 --rate N 으로 초당 상한을 8 아래로 낮출 수 있다 — 같은 IP 에서 다른 SEC 작업이 돌 때)
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

if not (os.environ.get("SEC_UA") or "").strip():
    sys.exit("🚨 SEC_UA 환경변수가 없다 — SEC 요청의 User-Agent(이름 + 연락처)를 명시적으로 정해서 넘길 것. "
             "edgar.py 의 기본값은 쓰지 않는다.")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402
import issuer_map as IM  # noqa: E402
import ins_pit_build as P  # noqa: E402  Cal · Map · clean · 표지 식 · 패널 칸 · load_panel

if edgar.UA != os.environ["SEC_UA"]:
    sys.exit("🚨 edgar.UA 가 SEC_UA 와 다르다")

ROOT = P.ROOT
DATA = P.DATA
OUTD = os.path.join(DATA, "_ins_daily")
MAND = os.path.join(OUTD, "manifest")
PSD = os.path.join(OUTD, "ps")
RAWD = os.path.join(P.RAW, "daily")
IDX_URL = "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR%d/"
DOC_URL = "https://www.sec.gov/Archives/"
DERA_END = P.DATA_END
FORMS4 = ("4", "4/A")

_now, _sha, _rj, _wj = IM._now, IM._sha, IM._rj, IM._wj

# DERA NONDERIV_TRANS *_FN 열 순서 ↔ XML 자리
FN_SLOTS = (("securityTitle",), ("transactionDate",), ("deemedExecutionDate",), ("transactionCoding",),
            ("transactionTimeliness",), ("transactionAmounts", "transactionShares"),
            ("transactionAmounts", "transactionPricePerShare"), ("transactionAmounts", "transactionAcquiredDisposedCode"),
            ("postTransactionAmounts", "sharesOwnedFollowingTransaction"),
            ("postTransactionAmounts", "valueOwnedFollowingTransaction"),
            ("ownershipNature", "directOrIndirectOwnership"), ("ownershipNature", "natureOfOwnership"))


# ════════════════════════════════════════════════════════════════════════
# 판 고정 — 달마다 manifest
# ════════════════════════════════════════════════════════════════════════
class MonthMan:
    def __init__(self):
        self.docs = {}
        self.dirty = set()

    def _path(self, ym):
        return os.path.join(MAND, ym + ".json")

    def get(self, ym):
        if ym not in self.docs:
            self.docs[ym] = _rj(self._path(ym)) or {
                "note": "§G 일간 Form 4 수집 고정표 — build/ins_daily.py. idx[날짜] = 색인 파일(sha256 · 바이트 · 줄 수 · 걸린 접수번호 수) · "
                        "docs[접수번호] = [원문 .txt sha256, 바이트, 제출일, 걸린 CIK]. 원문은 저장소 밖 RAW/daily/doc. "
                        "ciks = 그달 거르기에 쓴 CIK 집합의 sha256 과 크기(issuer_map.current_ciks) · issuer_map = 지도 sha256.",
                "ym": ym, "idx": {}, "docs": {}, "ciks": None, "issuer_map": None}
        return self.docs[ym]

    def put_doc(self, ym, acc, meta):
        d = self.get(ym)
        old = d["docs"].get(acc)
        if old and old[0] != meta[0]:
            raise SystemExit("🚨 원문 해시가 바뀌었다 — %s\n   manifest %s\n   지금     %s" % (acc, old[0], meta[0]))
        if old != meta:
            d["docs"][acc] = meta
            self.dirty.add(ym)

    def put_idx(self, ym, day, meta):
        d = self.get(ym)
        old = d["idx"].get(day)
        if old and old.get("sha256") != meta.get("sha256"):
            raise SystemExit("🚨 색인 해시가 바뀌었다 — %s (%s → %s)" % (day, old.get("sha256"), meta.get("sha256")))
        if old != meta:
            d["idx"][day] = meta
            self.dirty.add(ym)

    def save(self):
        for ym in sorted(self.dirty):
            d = self.docs[ym]
            d["updated"] = _now()
            d["idx"] = dict(sorted(d["idx"].items()))
            d["docs"] = dict(sorted(d["docs"].items()))
            p = self._path(ym)
            os.makedirs(MAND, exist_ok=True)
            head = {k: v for k, v in d.items() if k not in ("idx", "docs")}
            lines = ["{"]
            for k, v in head.items():
                lines.append(" %s: %s," % (json.dumps(k), json.dumps(v, ensure_ascii=False)))
            for sec in ("idx", "docs"):
                items = list(d[sec].items())
                lines.append(" %s: {" % json.dumps(sec))
                for i, (k, v) in enumerate(items):
                    lines.append("  %s: %s%s" % (json.dumps(k), json.dumps(v, separators=(",", ":")), "," if i < len(items) - 1 else ""))
                lines.append(" }" + ("," if sec == "idx" else ""))
            lines.append("}")
            with io.open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
            os.replace(p + ".tmp", p)
        self.dirty.clear()


# ════════════════════════════════════════════════════════════════════════
# CIK 집합 — 그달 §A0 지도의 현재 CIK
# ════════════════════════════════════════════════════════════════════════
_CK = {}
_LAST = []


def ciks_for(ym):
    """그달의 거르기 CIK 집합 — issuer_map.current_ciks(그달). 지도 끝 달 뒤는 끝 달의 것."""
    if not _LAST:
        _LAST.append(_rj(P.IMAP)["months"][1])
    k = min(ym, _LAST[0])
    if k not in _CK:
        _CK[k] = set(IM.current_ciks(P.IMAP, k))
    return _CK[k]


# ════════════════════════════════════════════════════════════════════════
# 색인 · 원문 받기
# ════════════════════════════════════════════════════════════════════════
def _qtr(day):
    d = dt.date.fromisoformat(day)
    return d.year, (d.month - 1) // 3 + 1


_LIST = {}
LONG_WAIT = (600, 900, 1200)          # edgar.fetch_bytes 의 백오프(합계 약 12.7분)를 다 쓴 뒤에도 429 · 403 이면 더 쉰다


def _fetch(url, timeout=120):
    """edgar.fetch_bytes 1건 — 같은 IP 의 다른 SEC 작업 때문에 차단이 길어지면(실측 2026-09-25 17:37~ 15분 넘게 429)
    10 · 15 · 20분을 더 쉬고 다시 부른다. 요청은 늘 edgar.fetch_bytes 를 거친다(초당 상한 · gzip · 백오프)."""
    for i in range(len(LONG_WAIT) + 1):
        try:
            return edgar.fetch_bytes(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 403) or i == len(LONG_WAIT):
                raise
            print("  ⚠ SEC %s 가 이어진다 — %d초 더 쉬고 다시 (%s)" % (e.code, LONG_WAIT[i], url[:90]), flush=True)
            time.sleep(LONG_WAIT[i])


def idx_days(y, q):
    """분기 디렉터리의 form.YYYYMMDD.idx 날짜 목록(index.json 1건)."""
    if (y, q) not in _LIST:
        b = _fetch(IDX_URL % (y, q) + "index.json", timeout=60)
        j = json.loads(b.decode("utf-8"))
        out = set()
        for it in j.get("directory", {}).get("item", []):
            m = re.fullmatch(r"form\.(\d{8})\.idx", it.get("name", ""))
            if m:
                s = m.group(1)
                out.add("%s-%s-%s" % (s[:4], s[4:6], s[6:]))
        _LIST[(y, q)] = sorted(out)
    return _LIST[(y, q)]


def _gz_write(path, b):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as f:
            f.write(b)
    os.replace(path + ".tmp", path)


def _gz_read(path):
    with gzip.open(path, "rb") as f:
        return f.read()


def fetch_idx(day, MM: MonthMan):
    """그날 색인 → [(서식, CIK, 파일 경로)] (서식 4 · 4/A 만)."""
    y, q = _qtr(day)
    ym = day[:7]
    p = os.path.join(RAWD, "idx", day[:4], "form.%s.idx.gz" % day.replace("-", ""))
    if os.path.exists(p):
        b = _gz_read(p)
    else:
        b = _fetch(IDX_URL % (y, q) + "form.%s.idx" % day.replace("-", ""), timeout=120)
        _gz_write(p, b)
    out = []
    n_lines = 0
    for line in b.decode("latin-1").splitlines():
        if not (line.startswith("4 ") or line.startswith("4/A ")):
            continue
        parts = line.split()
        if len(parts) < 5 or not parts[-1].startswith("edgar/"):
            continue
        n_lines += 1
        out.append((parts[0], int(parts[-3]), parts[-1], parts[-2]))
    meta = {"sha256": _sha(b), "bytes": len(b), "n_form4_lines": n_lines}
    return out, meta


def fetch_doc(path, acc, ym, MM: MonthMan):
    p = os.path.join(RAWD, "doc", ym, acc + ".txt.gz")
    if os.path.exists(p):
        b = _gz_read(p)
        m = MM.get(ym)["docs"].get(acc)
        if m and m[0] != _sha(b):
            raise SystemExit("🚨 로컬 원문이 manifest 해시와 다르다 — %s" % p)
        return b, False
    b = _fetch(DOC_URL + path, timeout=120)
    _gz_write(p, b)
    return b, True


def capture_day(day, MM: MonthMan, verbose=True):
    """하루 — 색인을 받아 걸린 제출의 원문을 받는다. 반환 개수."""
    ym = day[:7]
    S = ciks_for(ym)
    lines, meta = fetch_idx(day, MM)
    hit = collections.OrderedDict()
    for form, cik, path, date in lines:
        if cik in S:
            acc = os.path.basename(path)[:-4]
            if acc not in hit:
                hit[acc] = (form, cik, path, date)
    t0 = time.time()
    n_new = 0
    for acc, (form, cik, path, date) in hit.items():
        b, new = fetch_doc(path, acc, ym, MM)
        n_new += new
        MM.put_doc(ym, acc, [_sha(b), len(b), day, cik])
    meta.update({"n_hit_acc": len(hit)})
    MM.put_idx(ym, day, meta)
    d = MM.get(ym)
    csha = _sha(json.dumps(sorted(S)).encode())
    if d.get("ciks") != [csha, len(S)] or d.get("issuer_map") != IM._sha_file(P.IMAP):
        d["ciks"], d["issuer_map"] = [csha, len(S)], IM._sha_file(P.IMAP)
        MM.dirty.add(ym)
    MM.save()
    if verbose:
        print("  %s 색인 Form 4 줄 %d · 걸린 제출 %d · 새로 받음 %d (%.0fs)" % (day, meta["n_form4_lines"], len(hit), n_new,
                                                                     time.time() - t0), flush=True)
    return {"day": day, "lines": meta["n_form4_lines"], "hit": len(hit), "new": n_new}


def days_between(a, b):
    out = []
    d, e = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    qs = set()
    while d <= e:
        qs.add(((d.year), (d.month - 1) // 3 + 1))
        d += dt.timedelta(days=1)
    for y, q in sorted(qs):
        out.extend(x for x in idx_days(y, q) if a <= x <= b)
    return sorted(out)


def capture_range(a, b):
    MM = MonthMan()
    res = []
    for day in days_between(a, b):
        res.append(capture_day(day, MM))
    return res


# ════════════════════════════════════════════════════════════════════════
# XML → 원 행(§A 원 행과 같은 칸)
# ════════════════════════════════════════════════════════════════════════
_XML = re.compile(rb"<XML>\s*(.*?)\s*</XML>", re.S | re.I)


def _t(e, path):
    x = e.find(path)
    return (x.text or "").strip() if x is not None and x.text is not None else ""


def _v(e, path):
    x = e.find(path)
    if x is None:
        return ""
    v = x.find("value")
    if v is not None:
        return (v.text or "").strip()
    return (x.text or "").strip()


def num2(s):
    """XML 수치 → DERA 정밀도(소수 둘째 자리 · 반올림 half-up). DERA 는 TRANS_SHARES · TRANS_PRICEPERSHARE 를 소수 둘째 자리로
    싣는다(실측 2026Q2: 단가 352.833 → 352.83 · 366.855 → 366.86). 같은 자리로 맞춰야 정정 중복 키·금액이 DERA 와 이어진다."""
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None


def _flag(s):
    return (s or "").strip().lower() in ("1", "true")


def _hdr(b, key):
    m = re.search(rb"<" + key + rb">(\S+)", b[:4000]) if key.startswith(b"ACC") else re.search(key + rb":\s*(\S+)", b[:4000])
    return m.group(1).decode("ascii", "replace") if m else ""


def parse_doc(b, acc, c2g):
    """원문 .txt → (원 행 목록, 개수)."""
    st = collections.Counter()
    blk = None
    for m in _XML.finditer(b):
        if b"<ownershipDocument" in m.group(1)[:2000]:
            blk = m.group(1)
            break
    if blk is None:
        st["no_xml"] += 1
        return [], st
    blk = blk.lstrip()
    try:
        root = ET.fromstring(blk)
    except ET.ParseError:
        try:
            fixed = re.sub(rb"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", b"&amp;", blk)
            root = ET.fromstring(fixed)
            st["xml_fixed_amp"] += 1
        except ET.ParseError:
            st["xml_parse_error"] += 1
            return [], st
    doc = _t(root, "documentType")
    fdate = _hdr(b, b"FILED AS OF DATE")
    fdate = "%s-%s-%s" % (fdate[:4], fdate[4:6], fdate[6:8]) if len(fdate) >= 8 else ""
    adt = _hdr(b, b"ACCEPTANCE-DATETIME")
    ck = P._cik(_t(root, "issuer/issuerCik"))
    g = c2g.get(ck)
    if g is None:
        st["issuer_outside_world"] += 1
        return [], st
    if doc not in FORMS4:
        st["doc_" + doc] += 1
        return [], st
    remarks = _t(root, "remarks")
    aff_raw = _t(root, "aff10b5One")
    owners, info = [], []
    for o in root.findall("reportingOwner"):
        c = P._cik(_t(o, "reportingOwnerId/rptOwnerCik"))
        if c is None:
            st["owner_no_cik"] += 1
            continue
        rl = o.find("reportingOwnerRelationship")
        rel = []
        if rl is not None:
            for tag, nm in (("isDirector", "Director"), ("isOfficer", "Officer"), ("isTenPercentOwner", "TenPercentOwner"),
                            ("isOther", "Other")):
                if _flag(_t(rl, tag)):
                    rel.append(nm)
        rel = ",".join(rel)
        for x in owners:
            if x[0] == c:
                x[1] = P.rel_of(P._bits(x[1]) | P._bits(rel))
                st["owner_dup_row"] += 1
                break
        else:
            owners.append([c, rel])
            info.append([c, _t(o, "reportingOwnerId/rptOwnerName"), _t(o, "reportingOwnerRelationship/officerTitle")])
    fns = {}
    for f in root.findall("footnotes/footnote"):
        fns[(f.get("id") or "").strip()] = " ".join("".join(f.itertext()).split())   # DERA 본문처럼 줄바꿈 없는 한 줄
    out = []
    seq = 0
    for tr in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        seq += 1
        code = _t(tr, "transactionCoding/transactionCode").upper()
        if code not in P.CODES:
            continue
        ids, slot_nodes = [], set()
        for path in FN_SLOTS:
            e = tr.find("/".join(path))
            if e is None:
                continue
            for f in e.findall("footnoteId"):
                slot_nodes.add(id(f))
                x = (f.get("id") or "").strip()
                if x and x not in ids:
                    ids.append(x)
        extra = 0
        for f in tr.iter("footnoteId"):
            if id(f) in slot_nodes:
                continue
            x = (f.get("id") or "").strip()
            if x and x not in ids:
                ids.append(x)
                extra += 1
        if extra:
            st["fn_extra_slot"] += 1
        miss = [x for x in ids if x not in fns]
        if miss:
            st["fn_id_missing"] += len(miss)
        txt = " ".join(fns[x] for x in ids if fns.get(x))
        rec = {"acc": acc, "sk": seq, "doc": doc, "fdate": fdate, "issuer_cik": ck, "gid": g,
               "sym": _t(root, "issuer/issuerTradingSymbol"), "tdate": _v(tr, "transactionDate")[:10],
               "deemed": _v(tr, "deemedExecutionDate")[:10], "code": code,
               "ad": _v(tr, "transactionAmounts/transactionAcquiredDisposedCode").upper(),
               "tft": _t(tr, "transactionCoding/transactionFormType"), "swap": _t(tr, "transactionCoding/equitySwapInvolved"),
               "shares": num2(_v(tr, "transactionAmounts/transactionShares")),
               "price": num2(_v(tr, "transactionAmounts/transactionPricePerShare")),
               "shares_raw": _v(tr, "transactionAmounts/transactionShares"),
               "price_raw": _v(tr, "transactionAmounts/transactionPricePerShare"),
               "post": num2(_v(tr, "postTransactionAmounts/sharesOwnedFollowingTransaction")),
               "di": _v(tr, "ownershipNature/directOrIndirectOwnership"), "title": _v(tr, "securityTitle"),
               "fn_ids": ids, "fn_text": txt, "remarks": remarks, "aff": P._aff(aff_raw), "aff_raw": aff_raw or None,
               "ns16": _t(root, "notSubjectToSection16"), "period": _t(root, "periodOfReport"),
               "orig": _t(root, "dateOfOriginalSubmission"), "owners": [list(x) for x in owners], "owner_info": info,
               "stc": 1 if P.is_stc(txt) else 0, "stc_v1": 1 if P.is_stc_v1(txt) else 0,
               "p10_rx": 1 if P.plan_hit(txt + " " + remarks) else 0,
               "p10f": 1 if P.plan_hit(txt) else 0, "p10r": 1 if P.plan_hit(remarks) else 0,
               "adt": adt, "src": "xml", "fn_extra": extra}
        out.append(rec)
    st["rows"] += len(out)
    return out, st


def daily_rows(a, b, restrict=True):
    """받은 원문(제출일 a..b) → 원 행. restrict=True 면 발행사 CIK 가 그달 거르기 집합에 든 것만(시험의 DERA 쪽과 같은 모집단)."""
    M = P.Map()
    MM = MonthMan()
    out, st = [], collections.Counter()
    ym = a[:7]
    while ym <= b[:7]:
        d = MM.get(ym)
        S = ciks_for(ym)
        for acc, (sha, n, day, cik) in d["docs"].items():
            if not (a <= day <= b):
                continue
            p = os.path.join(RAWD, "doc", ym, acc + ".txt.gz")
            if not os.path.exists(p):
                raise SystemExit("🚨 원문이 없다 — %s (받기를 먼저)" % p)
            bb = _gz_read(p)
            if _sha(bb) != sha:
                raise SystemExit("🚨 원문 해시가 manifest 와 다르다 — %s" % p)
            rows, s1 = parse_doc(bb, acc, M.c2g)
            st.update(s1)
            st["docs"] += 1
            for r in rows:
                if r["fdate"] != day:
                    st["fdate_ne_index_day"] += 1
                if restrict and r["issuer_cik"] not in S:
                    st["issuer_not_in_month_set"] += 1
                    continue
                out.append(r)
        ym = IM._madd(ym, 1)
    return out, dict(st)


# ════════════════════════════════════════════════════════════════════════
# 전방 패널
# ════════════════════════════════════════════════════════════════════════
def cmd_panel():
    """DERA 패널 전체 + DERA 끝 뒤 일간 원 행 → clean 한 번 → DERA 끝 뒤 행만 달별 파일로."""
    t0 = time.time()
    months = sorted(f[:-5] for f in os.listdir(MAND) if f.endswith(".json")) if os.path.isdir(MAND) else []
    fw = [m for m in months if m > DERA_END[:7]]
    if not fw:
        print("전방 달이 없다")
        return None
    a = IM._madd(DERA_END[:7], 1) + "-01"
    MM = MonthMan()
    b = max(max(MM.get(m)["idx"]) for m in fw if MM.get(m)["idx"])     # 받은 마지막 색인 날
    xr, st = daily_rows(a, b, restrict=False)
    base = P.load_panel()
    M = P.Map()
    cal = P.Cal()
    rows, cst = P.clean(base + xr, cal, M)
    adt = {r["acc"]: r.get("adt") for r in xr}
    C = P.C
    fd_of = {r[C["acc"]]: r[C["fd"]] for r in rows}
    by = collections.defaultdict(list)
    late = []                                    # 전방 행의 정정 가운데 뒤 달 4/A 에서 온 것(달 파일은 그달 끝 현재 — 여기에만 적는다)
    for r in rows:
        if r[C["fd"]] > DERA_END:
            ym = r[C["fd"]][:7]
            rr = list(r)
            if rr[C["corr"]] == 1 and rr[C["ctgt"]] and (fd_of.get(rr[C["ctgt"]][0]) or "")[:7] > ym:
                late.append([rr[C["acc"]], rr[C["sk"]], "values", rr[C["shc"]], rr[C["pxc"]], rr[C["ctgt"]]])
                rr[C["corr"]], rr[C["ctgt"]], rr[C["shc"]], rr[C["pxc"]], rr[C["usdc"]] = 0, None, None, None, None
            if rr[C["tdh"]] and (fd_of.get(rr[C["tdh"]][1]) or "")[:7] > ym:
                late.append([rr[C["acc"]], rr[C["sk"]], "tdate", rr[C["tdh"]]])
                rr[C["tdh"]] = None
            by[ym].append(rr + [adt.get(r[C["acc"]])])
    pins = {"issuer_map": M.sha, "dera_panel": {f: IM._sha_file(os.path.join(P.PANEL, f)) for f in sorted(os.listdir(P.PANEL))},
            "manifests": {m: IM._sha_file(os.path.join(MAND, m + ".json")) for m in fw},
            "script": IM._sha_file(os.path.abspath(__file__)), "ins_pit_build": IM._sha_file(P.__file__),
            "r_r1_flags": IM._sha_file(P.R1.__file__)}
    # 전방 4/A 가 고친 DERA 기간 원 행(DERA 패널 파일은 다시 쓰지 않는다 — 여기 적는다 · 선언 q)
    fwd_acc = {r["acc"] for r in xr}
    back = [[r[C["acc"]], r[C["sk"]], r[C["g"]], r[C["td"]], r[C["c"]], r[C["sh"]], r[C["px"]], r[C["shc"]], r[C["pxc"]], r[C["ctgt"]]]
            for r in rows if r[C["fd"]] <= DERA_END and r[C["corr"]] == 1 and r[C["ctgt"]] and r[C["ctgt"]][0] in fwd_acc]
    back_td = [[r[C["acc"]], r[C["sk"]], r[C["g"]], r[C["td"]], r[C["c"]], r[C["tdh"]]]
               for r in rows if r[C["fd"]] <= DERA_END and r[C["tdh"]] and r[C["tdh"]][1] in fwd_acc]
    days = {m: len(MM.get(m)["idx"]) for m in fw}
    prev = _rj(os.path.join(OUTD, "forward.json")) or {}
    files = {}
    for ym, rs in sorted(by.items()):
        p = os.path.join(PSD, "ps_%s.json.gz" % ym)
        P.write_gz_json(p, {"note": P.PANEL_NOTE + " · 전방 일간 XML 경로(build/ins_daily.py) · adt = 접수 시각(SGML 머리 ACCEPTANCE-DATETIME).",
                            "cols": P.PANEL_COLS + ["adt"], "month": ym, "through": b, "pins": pins, "n": len(rs), "rows": rs})
        files[ym] = {"rows": len(rs), "bytes": os.path.getsize(p), "sha256": IM._sha_file(p),
                     "corr_rows_4a": sum(1 for r in rs if r[C["corr"]] == 2),           # 사건에서 뺀 4/A 정정 행(선언 q)
                     "dcorr_rows_4a": sum(1 for r in rs if r[C["corr"]] == 3),          # 사건에서 뺀 4/A 거래일 정정 행(선언 q2)
                     "stc_v1_only_S": sum(1 for r in rs if r[C["c"]] == "S" and r[C["stc_v1"]] and not r[C["stc"]]),
                     "complete": ym < b[:7]}
    dens = {}
    mem = M.members(IM.load_refs())
    for ym in sorted(by):
        S = collections.defaultdict(set)
        for r in rows:
            if r[C["av"]][:7] != ym or not r[C["cnt"]] or not any(bb & P.INSIDER_BITS for _, bb in r[C["own"]]):
                continue
            S[r[C["c"]]].add(r[C["g"]])
            if r[C["c"]] == "S" and not r[C["stc"]]:
                S["S_nostc"].add(r[C["g"]])
        m = mem.get(ym) or {"s16": set(), "all": set()}
        dens[ym] = {"world_S": len(S["S"]), "s16_S": len(S["S"] & m["s16"]), "s16_S_nostc": len(S["S_nostc"] & m["s16"]),
                    "s16_P": len(S["P"] & m["s16"]), "complete": ym < b[:7]}
    pb = prev.get("through") or ""
    changed = sorted(ym for ym, v in files.items() if ym < pb[:7] and (prev.get("files") or {}).get(ym, {}).get("sha256")
                     not in (None, v["sha256"]))
    rep = {"generated": _now(), "through": b, "index_days": {"by_month": days, "total": sum(days.values()),
                                                           "note": "받은 EDGAR daily-index form.idx 날 수(= NYSE 거래일)"},
           "files": files, "parse": st, "density_by_avail_month": dens,
           "back_corrections": {"note": "전방 4/A 가 수량·단가를 고친 DERA 기간(≤ %s) 원 행 — [acc, sk, 그룹, 거래일, 코드, 제출된 수량, 제출된 단가, "
                                        "정정 수량, 정정 단가, [정정 4/A acc, sk]]. 원 행 가용일 · 사건 · 1차 값은 그대로(선언 q)." % DERA_END,
                                "n": len(back), "rows": back},
           "back_tdate_corrections": {"note": "전방 4/A 가 거래일을 고친 DERA 기간 원 행 — [acc, sk, 그룹, 거래일, 코드, [고친 거래일, 4/A acc, sk]] · "
                                              "사건 · 라벨 그대로 · 분류 이력만 고친 거래일(선언 q2).", "n": len(back_td), "rows": back_td},
           "late_corrections": {"note": "전방 달 파일의 행을 뒤 달에 제출된 4/A 가 고친 것 — 달 파일에는 넣지 않았다(그달 끝 현재 · 덧붙이기만) · "
                                        "[acc, sk, 'values', 정정 수량, 정정 단가, [4/A acc, sk]] · [acc, sk, 'tdate', [고친 거래일, 4/A acc, sk]].",
                                "n": len(late), "rows": late},
           "complete_months_changed": {"note": "지난 실행(through %s)에 이미 다 찼던 달 가운데 파일 sha256 이 바뀐 달(감사 · 비어야 정상)" % (pb or "-"),
                                       "months": changed},
           "pins": pins}
    IM._wj_stable(os.path.join(OUTD, "forward.json"), rep, indent=1)
    print("→ 전방 패널 %s · 끝 %s · %s (%.0fs)" % ({k: v["rows"] for k, v in files.items()}, b, dens, time.time() - t0))
    return rep


# ════════════════════════════════════════════════════════════════════════
# 일치 시험 — 2026Q2 를 일간 XML 경로로 다시 만들어 DERA 와 대조
# ════════════════════════════════════════════════════════════════════════
def _okey(r, c):
    return (r["gid"], c, r["tdate"], r["code"], P._k6(r["shares"]), P._k6(r["price"]))


def cmd_test(q="2026q2", fetch=True, window=None, out=None):
    t0 = time.time()
    y, n = int(q[:4]), int(q[5])
    a = "%04d-%02d-01" % (y, 3 * (n - 1) + 1)
    b = (dt.date(y + (n == 4), (3 * n) % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()
    if window:                                   # 개발용 부분 창(결과 파일은 out 으로)
        a, b = window
    if fetch:
        capture_range(a, b)
    M = P.Map()
    man = IM.ins_manifest()
    # DERA 쪽 — 원 행 캐시(Form 4 · 4/A) · 발행사 CIK 가 제출월 거르기 집합에 든 것
    dr, _, _ = P.load_or_parse(q, M, man, (_rj(P.CMAN) or {}).get("files", {}))
    D = [r for r in dr if r["doc"] in FORMS4 and a <= r["fdate"] <= b and r["issuer_cik"] in ciks_for(r["fdate"][:7])]
    X, xst = daily_rows(a, b, restrict=True)
    res = {"note": "§G 일치 시험 — %s 를 일간 XML 경로(build/ins_daily.py)로 다시 만들어 DERA 원 행과 대조. 개수만(수익 없음)." % q,
           "generated": _now(), "window": [a, b], "xml_parse": xst,
           "pins": {"issuer_map": M.sha, "dera_zip": man.get(q)["sha256"], "script": IM._sha_file(os.path.abspath(__file__)),
                    "ins_pit_build": IM._sha_file(P.__file__),
                    "manifests": {m: IM._sha_file(os.path.join(MAND, m + ".json")) for m in sorted({a[:7], IM._madd(a[:7], 1), b[:7]})
                                  if m <= b[:7] and os.path.exists(os.path.join(MAND, m + ".json"))}}}
    # 1 제출 단위
    da = {r["acc"] for r in D}
    xa = {r["acc"] for r in X}
    res["accessions"] = {"dera": len(da), "xml": len(xa), "both": len(da & xa), "dera_only": sorted(da - xa)[:50],
                         "n_dera_only": len(da - xa), "xml_only": sorted(xa - da)[:50], "n_xml_only": len(xa - da)}
    # 2 행 단위(보고자마다 한 키) — 사양의 (그룹, 보고자, 거래일, 코드, 수량, 단가)
    cd = collections.Counter(_okey(r, c) for r in D for c, _ in r["owners"])
    cx = collections.Counter(_okey(r, c) for r in X for c, _ in r["owners"])
    both = sum(min(v, cx.get(k, 0)) for k, v in cd.items())
    nd, nx = sum(cd.values()), sum(cx.values())
    ex_d = [list(k) for k in cd if cd[k] > cx.get(k, 0)][:15]
    ex_x = [list(k) for k in cx if cx[k] > cd.get(k, 0)][:15]
    res["rows_owner_key"] = {"dera": nd, "xml": nx, "matched": both, "dera_matched_rate": round(both / nd, 5) if nd else None,
                             "xml_matched_rate": round(both / nx, 5) if nx else None, "dera_unmatched_examples": ex_d,
                             "xml_unmatched_examples": ex_x}
    # 3 같은 접수번호 안 행 칸 대조(순서 무관 — (acc, 거래일, 코드, 수량, 단가, 직접·간접, 거래 뒤 보유) 로 짝.
    #   직접·간접 두 로트는 앞 다섯 칸이 같아서 뒤 두 칸이 없으면 서로 엇갈려 짝지어진다)
    def rk(r):
        return (r["acc"], r["tdate"], r["code"], P._k6(r["shares"]), P._k6(r["price"]), r.get("di"), P._k6(r.get("post")))
    gd, gx = collections.defaultdict(list), collections.defaultdict(list)
    for r in D:
        gd[rk(r)].append(r)
    for r in X:
        gx[rk(r)].append(r)
    fd = collections.Counter()
    fex = []
    for k in sorted(set(gd) & set(gx), key=repr):          # 예시 목록이 해시 순서에 매이지 않게(두 번 빌드 같은 바이트)
        for r1, r2 in zip(gd[k], gx[k]):
            fd["pairs"] += 1
            for f in ("stc", "p10_rx", "p10f", "p10r", "aff", "ad", "doc", "fdate", "gid"):
                if (r1[f] or 0) != (r2[f] or 0):
                    fd[f] += 1
                    if len(fex) < 12:
                        fex.append([k[0], f, str(r1[f])[:60], str(r2[f])[:60]])
            if sorted((c, P._bits(x)) for c, x in r1["owners"]) != sorted((c, P._bits(x)) for c, x in r2["owners"]):
                fd["owners_rel"] += 1
                if len(fex) < 12:
                    fex.append([k[0], "owners", str(r1["owners"])[:80], str(r2["owners"])[:80]])
            t1, t2 = " ".join((r1["fn_text"] or "").split()), " ".join((r2["fn_text"] or "").split())
            if t1 != t2:
                fd["fn_text_differs"] += 1
                if r1["fn_ids"] != r2["fn_ids"]:
                    fd["fn_ids_differ"] += 1
                    # 순서만 다름(DERA 는 같은 자리 안 각주 순서가 XML 과 다를 수 있다) 대 집합이 다름(DERA 가 옆 행 —
                    #   주로 같은 제출의 간접 보유 행 — 의 natureOfOwnership 각주를 붙인 경우를 실측으로 확인)
                    fd["fn_ids_order_only" if sorted(r1["fn_ids"]) == sorted(r2["fn_ids"]) else "fn_ids_set_differs"] += 1
                    if sorted(r1["fn_ids"]) != sorted(r2["fn_ids"]):
                        fd["fn_ids_dera_extra"] += 1 if set(r1["fn_ids"]) > set(r2["fn_ids"]) else 0
                        fd["fn_ids_xml_extra"] += 1 if set(r2["fn_ids"]) > set(r1["fn_ids"]) else 0
                elif t2.startswith(t1) or t1.startswith(t2):
                    fd["fn_text_prefix"] += 1           # 한쪽이 잘렸다(길이를 따로 센다)
                    fd["fn_text_prefix_dera_shorter"] += 1 if len(t1) < len(t2) else 0
                if len(fex) < 24:
                    fex.append([k[0], "fn_text", r1["fn_ids"], r2["fn_ids"], len(t1), len(t2)])
    res["field_parity"] = {"diff": dict(fd), "examples": fex}
    # 4 정리 뒤 행 + 회사-월 OS(분류는 r_r1_flags · 이력은 DERA)
    base = [r for r in P.load_panel() if r["fdate"] < a]
    dq = [r for r in P.load_panel([y]) if a <= r["fdate"] <= b and r["issuer_cik"] in ciks_for(r["fdate"][:7])]
    cal = P.Cal()
    rows_x, _ = P.clean(base + X, cal, M)
    Cc = P.C
    kx = collections.Counter(tuple([r[Cc["g"]], r[Cc["td"]], r[Cc["c"]], P._k6(r[Cc["sh"]]), P._k6(r[Cc["px"]])]
                                   + sorted(c for c, _ in r[Cc["own"]])) for r in rows_x if a <= r[Cc["fd"]] <= b)
    # load_panel 레코드의 owners 에는 odup · ocor 가 되붙고 shares · price 는 처음 값이다 — 정리 뒤 비교는 own(own_bits)과 정정 뒤 값(_eff)
    kd = collections.Counter(tuple([r["gid"], r["tdate"], r["code"], P._k6(r["shares_eff"]), P._k6(r["price_eff"])]
                                   + sorted(c for c, _ in r["own_bits"])) for r in dq)
    mb = sum(min(v, kx.get(k, 0)) for k, v in kd.items())
    res["rows_after_clean"] = {"dera": sum(kd.values()), "xml": sum(kx.values()), "matched": mb,
                               "dera_matched_rate": round(mb / sum(kd.values()), 5) if kd else None,
                               "xml_matched_rate": round(mb / sum(kx.values()), 5) if kx else None}
    try:
        import r_r1_flags as R1
    except Exception as e:
        R1 = None
        res["os"] = {"skipped": "r_r1_flags.py 없음 (%s)" % e}
    if R1 is not None:
        c1 = R1.Cal()
        recs_d = base + dq
        recs_x = base + [dict(r, fn_text=None, remarks="") for r in X]
        Bd = R1.build(R1.rows_from_records(recs_d), c1, variants=("primary",))
        Bx = R1.build(R1.rows_from_records(recs_x), c1, variants=("primary",))
        Fd, Fx = Bd["flags"]["primary"], Bx["flags"]["primary"]
        mem = M.members(IM.load_refs())
        cells = mism = ones = 0
        ex = []
        by_m = {}
        for ym in sorted(m for m in Bd["months_ok"] if a[:7] <= m <= b[:7]):
            gs = mem.get(ym, {}).get("s16", set())
            c0 = m0 = 0
            for g in sorted(gs):
                u, v = Fd.dummy(g, ym, "OS"), Fx.dummy(g, ym, "OS")
                cells += 1
                c0 += 1
                ones += 1 if (u == 1 or v == 1) else 0
                if u != v:
                    mism += 1
                    m0 += 1
                    if len(ex) < 20:
                        ex.append([g, ym, u, v])
            rs_m = sum(1 for g in gs if Fd.dummy(g, ym, "RS") != Fx.dummy(g, ym, "RS"))
            by_m[ym] = {"cells": c0, "os_mismatch": m0, "rs_mismatch": rs_m,
                        "os_dera": sum(1 for g in gs if Fd.dummy(g, ym, "OS") == 1),
                        "os_xml": sum(1 for g in gs if Fx.dummy(g, ym, "OS") == 1)}
        res["os"] = {"r_r1_flags_sha256": IM._sha_file(R1.__file__), "cells": cells, "mismatch": mism,
                     "mismatch_rate": round(mism / cells, 5) if cells else None, "cells_either_1": ones,
                     "mismatch_rate_among_either_1": round(mism / ones, 5) if ones else None, "by_month": by_m, "examples": ex,
                     "rule": "Section 16 멤버 그룹 × 가용월(%s..%s · 다 찬 달) · 분류 이력 = DERA(시험 분기 앞) · 시험 분기 행만 바꿔 넣는다"
                             % (a[:7], b[:7])}
    rr = res["rows_owner_key"]
    rate = min(rr["dera_matched_rate"] or 0, rr["xml_matched_rate"] or 0)
    osr = (res.get("os") or {}).get("mismatch_rate")
    res["row_match"], res["os_mismatch"] = rate, osr                         # 러너(r_run RF g_check)가 읽는 최상위 칸
    res["pass"] = {"row_match_min": rate, "row_rule": ">= 0.995", "row_ok": rate >= 0.995,
                   "os_mismatch": osr, "os_rule": "<= 0.01", "os_ok": (osr is not None and osr <= 0.01),
                   "all": rate >= 0.995 and osr is not None and osr <= 0.01}
    p = out or os.path.join(OUTD, "test_%s.json" % q)
    IM._wj_stable(p, res, indent=1)
    print("→ %s · 제출 DERA %d / XML %d / 둘 다 %d · 행 일치 %.4f / %.4f · 정리 뒤 %.4f / %.4f · OS 불일치 %s · 통과 %s (%.0fs)"
          % (os.path.relpath(p, ROOT), len(da), len(xa), len(da & xa), rr["dera_matched_rate"] or 0, rr["xml_matched_rate"] or 0,
             res["rows_after_clean"]["dera_matched_rate"] or 0, res["rows_after_clean"]["xml_matched_rate"] or 0, osr,
             res["pass"]["all"], time.time() - t0))
    return res


def cmd_forward(until=None):
    a = IM._madd(DERA_END[:7], 1) + "-01"
    b = until or (dt.date.today() - dt.timedelta(days=1)).isoformat()
    capture_range(a, b)
    return cmd_panel()


# ════════════════════════════════════════════════════════════════════════
def set_rate(argv):
    """--rate N — 초당 요청 상한을 edgar 의 8 보다 낮춘다(같은 IP 에서 다른 SEC 작업이 돌 때 합계가 10 을 넘지 않게).
    실측 2026-09-25: tenq_rf_build fetch(작업자 3)와 겹치자 429 가 났다. 8 보다 높게는 못 올린다."""
    if "--rate" in argv:
        r = float(argv[argv.index("--rate") + 1])
        r = max(0.2, min(r, edgar.RATE))
        edgar._MIN_GAP = 1.0 / r
        print("초당 요청 상한 %.1f" % r)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    set_rate(argv)
    if cmd == "check":
        IM.cmd_check()
    elif cmd == "day":
        MM = MonthMan()
        capture_day(argv[2], MM)
    elif cmd == "range":
        capture_range(argv[2], argv[3])
    elif cmd == "forward":
        u = None
        if "--until" in argv:
            u = argv[argv.index("--until") + 1]
        cmd_forward(u)
    elif cmd == "panel":
        cmd_panel()
    elif cmd == "test":
        cmd_test(argv[2] if len(argv) > 2 else "2026q2", fetch="--no-fetch" not in argv)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
