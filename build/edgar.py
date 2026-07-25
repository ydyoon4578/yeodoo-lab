#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC EDGAR 공용 클라이언트.

EDGAR는 이 랩이 붙일 수 있는 무료 소스 중 가장 많은 칸을 여는 하나다
(40슬롯 중 9칸이 EDGAR 계열 소스 하나씩에 막혀 있다). 그래서 호출 규약을
파이프라인마다 따로 쓰지 않고 여기 한 곳에 둔다.

── SEC가 요구하는 것 ───────────────────────────────────────────────────
* User-Agent에 **이름과 연락처**를 넣을 것. 안 넣으면 403이다.
  실측(2026-07-25): 'python-urllib/3.12' → 403. 'yeodoo-lab' → 200.
  'yeodoo-lab globalkbam@gmail.com'(SEC가 문서에 적은 형태) → 200.
  URL이 든 UA는 한 번 403을 받은 적이 있어 쓰지 않는다 — 이름+이메일이 가장 안정적이다.
* 초당 10회 이하. 여기서는 8회로 잡는다(경계에 붙이면 429가 섞인다).

── 실측 비용 ───────────────────────────────────────────────────────────
  company_tickers.json   214KB · 0.11s · 10,429종목
  submissions/CIK…json    28KB · 0.08s (gz)
  → 518종목 전수 ≈ 65초(8 req/s 상한 기준). 무인증.

이 파일은 표준 라이브러리만 쓴다 — 갱신 잡의 의존성이 늘면 크론이 깨질 확률도 는다.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

# SEC 정책상 연락 가능한 주소를 넣어야 한다. 이 저장소의 커밋 작성자 주소와 같고,
# 공개 저장소 이력에 이미 들어 있다. 다른 값을 쓰려면 SEC_UA 환경변수로 덮어쓴다.
UA = os.environ.get("SEC_UA") or "yeodoo-lab globalkbam@gmail.com"

RATE = 8.0                      # req/s 상한(SEC 공지 10회보다 낮게)
_MIN_GAP = 1.0 / RATE
_last = [0.0]

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUB_URL = "https://data.sec.gov/submissions/CIK%010d.json"

# EDGAR 원문 링크. accession은 하이픈을 뺀 형태가 디렉터리 이름이다.
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
FILING_IDX = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s-index.htm"


def _throttle() -> None:
    gap = time.time() - _last[0]
    if gap < _MIN_GAP:
        time.sleep(_MIN_GAP - gap)
    _last[0] = time.time()


def get_json(url: str, retries: int = 4):
    """EDGAR JSON 1건. 실패하면 None을 준다(빌드를 중단하지 않는다 — 판단은 호출자 몫).

    403은 UA 문제일 수도, 일시적 차단일 수도 있어 재시도한다. 429/5xx도 같다.
    404는 재시도하지 않는다 — 그 CIK에 그 파일이 없다는 확정 답이다.
    """
    for attempt in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept-Encoding": "gzip",
                              "Accept": "application/json"})
            raw = urllib.request.urlopen(req, timeout=30).read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1.0 * (attempt + 1))
    return None


def ticker_cik_map() -> dict:
    """{티커: CIK(int)}. SEC 표기는 BRK-B처럼 하이픈을 쓴다.

    우리 유니버스도 yfinance 표기(BRK-B)라 대개 그대로 맞지만, 점 표기(BRK.B)를
    쓰는 소스가 섞여도 붙도록 두 형태를 모두 키로 넣는다."""
    j = get_json(TICKERS_URL)
    if not j:
        return {}
    out = {}
    for v in (j.values() if isinstance(j, dict) else j):
        t = str(v.get("ticker") or "").upper().strip()
        cik = v.get("cik_str")
        if not t or not isinstance(cik, int):
            continue
        out.setdefault(t, cik)
        if "-" in t:
            out.setdefault(t.replace("-", "."), cik)
        if "." in t:
            out.setdefault(t.replace(".", "-"), cik)
    return out


def submissions(cik: int):
    """회사 제출 이력(최근분). filings.recent가 열-지향 배열이라 행으로 뒤집어 쓴다."""
    return get_json(SUB_URL % int(cik))


def rows(sub: dict):
    """filings.recent(열-지향) → 행 리스트. 열 길이가 어긋난 응답은 최소 길이에서 자른다.

    ⚠ recent에는 **최근 1,000건 또는 1년치**만 들어온다. 그보다 오래된 것은
    filings.files[]의 별도 파일에 있고, 이 랩의 화면은 최근분만 쓰므로 따라가지 않는다.
    (따라가면 회사당 호출이 2배가 되고, 8-K 피드·IR 목록 어느 쪽도 그 깊이가 필요없다.)
    """
    rec = ((sub or {}).get("filings") or {}).get("recent") or {}
    keys = [k for k in ("accessionNumber", "filingDate", "reportDate", "form", "items",
                        "primaryDocument", "primaryDocDescription", "size",
                        "acceptanceDateTime") if k in rec]
    if not keys:
        return []
    n = min(len(rec[k]) for k in keys)
    return [{k: rec[k][i] for k in keys} for i in range(n)]


def doc_url(cik: int, accession: str, primary_doc: str) -> str:
    """제출 원문(주 문서) 링크. primaryDocument가 비면 제출 인덱스 페이지로 보낸다."""
    acc = str(accession or "").replace("-", "")
    if not acc:
        return ""
    if primary_doc:
        return ARCHIVE % (int(cik), acc, primary_doc)
    return FILING_IDX % (int(cik), acc, str(accession))


# ── 8-K Item 코드 ──────────────────────────────────────────────────────
# 8-K는 '무슨 일이 있었는지'를 Item 번호로 스스로 분류해 제출한다. 이 랩이 해설을
# 붙이지 않고도 피드를 분류할 수 있는 이유가 이것이다 — 분류의 출처가 회사 자신이다.
# 출처: SEC Form 8-K 서식(General Instructions) 항목 표.
ITEM8K = {
    "1.01": "중요 계약 체결", "1.02": "중요 계약 종료", "1.03": "파산·법정관리",
    "1.04": "광산 안전", "1.05": "중대 사이버 침해",
    "2.01": "자산 취득·처분 완료", "2.02": "실적 발표", "2.03": "채무 발생",
    "2.04": "기한이익 상실·가속", "2.05": "구조조정 비용 확정", "2.06": "자산 손상",
    "3.01": "상장폐지·규정 미달", "3.02": "미등록 지분 매각", "3.03": "주주 권리 변경",
    "4.01": "회계법인 교체", "4.02": "과거 재무제표 신뢰 불가(재작성)",
    "5.01": "지배권 변동", "5.02": "임원·이사 변동", "5.03": "정관 변경·회계연도 변경",
    "5.04": "연금 거래정지 기간", "5.05": "윤리강령 변경·면제",
    "5.06": "셸컴퍼니 지위 종료", "5.07": "주주총회 표결 결과", "5.08": "주주제안 기한",
    "6.01": "ABS 정보", "6.02": "수탁자·서비서 변경", "6.03": "신용보강 변경",
    "6.04": "증권 실패", "6.05": "자산풀 변경",
    "7.01": "Reg FD 공개", "8.01": "기타 사항", "9.01": "재무제표·첨부",
}

# 랩 화면에서 '중요'로 따로 묶는 코드 — 회사의 존립·회계 신뢰성·지배구조에 걸리는 것들.
# 주가 영향을 예측하는 분류가 아니다. 무엇이 중요한지에 대한 랩의 편집 판단이며,
# 원문 Item 코드는 그대로 함께 보여준다.
ITEM8K_MAJOR = ("1.03", "1.05", "2.06", "3.01", "4.01", "4.02", "5.01", "5.02")


# ── 티커가 새 등록 법인으로 넘어간 회사의 전신 CIK ──────────────────────
# 회사가 지주회사로 전환하면 SEC상 **새 CIK**가 만들어지고, company_tickers.json은 그
# 새 법인만 가리킨다. 옛 법인의 제출물과 XBRL 사실은 그대로 남아 있지만 티커로는 더 이상
# 닿지 않는다 — SEC가 둘을 잇는 포인터를 주지 않는다.
#
# 실측(2026-07-25): XOM → CIK 2115436 'ExxonMobil Holdings Corp'. 최초 제출 2026-07-01,
#   전체 26건, us-gaap 사실 0개. 전신 CIK 34088 'EXXON MOBIL CORP'에 제출 1,001건과
#   재무 전부가 있다. 둘 다 자기 메타데이터에 티커 XOM을 적지만 company_tickers.json에는
#   중복 항목이 0개라(10,429개 전수 확인) 자동으로는 못 찾는다.
#
# 손으로 적는 대신, 두 파이프라인 모두 이력이 빈약한 종목을 잡아 경고를 띄운다.
PREDECESSOR = {
    "XOM": [34088],
}


def parse_items(s: str):
    """'2.02,9.01' → ['2.02','9.01']. 코드 외 문자열이 섞여도 버리지 않고 그대로 남긴다."""
    out = []
    for p in str(s or "").split(","):
        p = p.strip()
        if p:
            out.append(p)
    return out


if __name__ == "__main__":
    # 자체 점검: 접속·UA·매핑이 살아 있는지 한 번에 본다.
    m = ticker_cik_map()
    print("ticker→CIK 매핑: %d개" % len(m))
    if not m:
        sys.exit("❌ company_tickers.json 실패 — UA 또는 네트워크 확인")
    sub = submissions(m["AAPL"])
    rr = rows(sub)
    print("AAPL: %s · SIC %s %s · 최근 제출 %d건"
          % (sub.get("name"), sub.get("sic"), sub.get("sicDescription"), len(rr)))
    print("최근 5건:", [(r["form"], r["filingDate"]) for r in rr[:5]])
