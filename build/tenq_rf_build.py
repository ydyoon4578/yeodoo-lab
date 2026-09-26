#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§C 10-Q 위험요인(Part II Item 1A) 텍스트 패널 — data/_tenq_rf.json  (R2-LAZYRF 자료 빌드)

무엇을·왜.
  R2 는 «10-Q 위험요인 절을 직전 분기 대비 크게 고쳐 쓴 회사» 를 EG30 에서 빼는 카드다(CMN «Lazy Prices» 표 A-15 사양).
  그 표지의 재료가 이 파일이다 — 세계 비금융 발행사 그룹의 10-Q 원본마다 Part II Item 1A 절을 떼어 내고, 형태(B/U/F)를
  미리 고정한 규칙으로 판정하고, 같은 그룹의 바로 앞 10-Q 와 짝을 지어 단어빈도 코사인(SimRF)과 문서 전체 코사인(SimDoc)을 잰다.
  가용 시각(acceptanceDateTime → ET)도 함께 싣는다. 분위 · CH_active · 회귀는 여기서 하지 않는다(r_r2flags · 등록 뒤 Stage M 몫).
  🚨 자료 빌드다 — 어떤 표지와 수익의 관계도 계산하지 않는다. 가격 · 수익 파일을 읽지 않는다.

대상(미리 고정).
  세계 = PIT S&P 500 ∪ NDX 멤버-월(data/_issuer_map.json · 2014-06..2026-09) 가운데 비금융(issuer_map.sector_at ≠ Financials).
  그룹마다 비금융 멤버였던 첫 달 − 11개월 ~ 마지막 달(2013-07 이전은 자른다)에 제출된 form == '10-Q' 원본(/A · 10-QT 제외).
  − 11개월은 첫 짝(바로 앞 10-Q · reportDate 70~200일 전)과 2013-07.. 시작(사양 «첫 짝 포함») 을 함께 덮는다.
  CIK 는 그룹의 효력 구간(groups.ciks 의 시작·끝 달) 안에서 제출된 것만 그 그룹 문서다.
  목록은 issuer_map.py sub 가 받아 둔 submissions(+ 과거 조각) 캐시에서 만든다 — 추가 요청 없음.

원문(주 문서 primaryDocument) — edgar.fetch_bytes(초당 8회 · gzip · 백오프). 여러 스레드가 받되 edgar._throttle 을 잠금으로 감싸
  전체 요청 간격은 1/8초 이상이다. 원본은 저장소 밖 RBATCH_RAW/tenq/doc/<연>/<accession>.htm.gz 에 두고
  sha256(gzip 전송을 푼 내용 바이트)을 data/_tenq_rf/manifest.json 에 고정한다 — 다시 받을 때 해시가 바뀌면 멈춘다.
  차단 페이지('Undeclared Automated Tool')가 오면 즉시 멈춘다.

파서(해시 고정 · PARSER_FUNCS 의 소스 + 상수 → PARSER_HASH · §G 전방은 같은 해시의 파서만 쓴다).
  HTML → 줄: lxml.html. script · style · head · ix:header · display:none 요소는 통째로 버린다(꼬리 글은 살린다).
    블록 요소(p · div · br · tr · li · h1..6 · table …)가 줄을 끊고 표의 칸(td · th)은 한 칸 띄어 같은 줄에 잇는다
    («Item 1A.» 와 «Risk Factors» 가 두 칸에 나뉜 머리를 한 줄로 만든다).
    줄마다 «숫자 표» 표지: 그 줄을 담은 가장 안쪽 표의 자기 글(안쪽 표 제외)에서 숫자 ÷ (숫자 + 알파벳) > 15% 면 참.
    숫자 표 줄은 경계 찾기에는 쓰지만(머리가 표 안에 있을 수 있다) 단어에는 넣지 않는다(사양 전처리).
  토큰: 소문자 · 숫자 → '#' · [a-z#]+ 조각 가운데 두 글자 이상 순수 알파벳만(사양 전처리).
  절 머리(시작): 줄 머리가 [part ii ·] item 1a(1 a · ia · items 표기 포함) 이고 뒤가 «risk factors» 이거나(뒤에 본문이 붙은
    run-in 머리 포함) 글자가 없다(«Item 1A.» 만 있는 줄 — 다음 줄이 «Risk Factors» 면 그 줄까지 머리). «Item 1A of …» 같은
    교차 참조는 머리가 아니다. 번호가 틀린 «Item 1. Risk Factors» 같은 머리도 받는다(item_other).
  절 끝: 시작 뒤 첫 [part ii ·] item 1b/2/3/4/5/6 머리(번호 뒤가 구두점 · 줄 끝 · 서식 제목어 · 'and/through/,'),
    또는 signatures · exhibit index · index to exhibits · exhibits 만 있는 줄. 없으면 문서 끝(end_how = 'eof').
  고르기: 시작 머리마다 다음 끝까지를 절 후보로 하고(끝이 같은 후보는 가장 이른 시작 하나 — 쪽 머리의 «(continued)» 를 합친다),
    단어 ≥ 8 인 후보 가운데 **마지막** 것(목차 항목은 단어가 거의 없고 Part II 본문은 목차 · Part I 뒤에 온다).
    그런 후보가 없으면 단어 > 0 인 마지막 후보. item 1a 머리가 하나도 맞지 않으면 대체 경로: «Part II» 머리 줄 뒤의
    «Risk Factors» 만 있는 줄(sec_how = 'plain').
  경계 b2(2026-09-25 적대 검토 반영 — 대체 경로 셋만 · item 1a 머리를 찾은 문서는 bfae3758 판과 같은 경계 · 무작위 400건 중
    399건 동일, 1건은 plain 문서).
    ① plain 경로의 끝에 번호 없는 대문자(또는 제목 대소문자) 항목 제목 줄을 더한다(LEGAL PROCEEDINGS · UNREGISTERED SALES … ·
       DEFAULTS UPON SENIOR SECURITIES · MINE SAFETY DISCLOSURES · OTHER INFORMATION · EXHIBITS · SIGNATURES · Part I 제목).
       WY 0000106535-17-000045 는 870 → 19단어(참 ≈ 18), MOH 0001179929-22-000080 은 224 → 126단어(참 ≈ 121 · v2 U → B).
    ② xref 경로 — «Form 10-Q Cross Reference Index» 가 있고 item 1a 후보가 모두 8단어 미만(색인 줄)이면 문서 전체의 «Risk Factors»
       제목 줄에서 8단어 이상 절 가운데 마지막(끝 = ①). CAH · INTC 2018~ · ILMN · GE 2018~2020 의 본문 절을 잡는다. 본문 절이 없는
       색인(GE «Not applicable(b)» · GEV «(a)» 각주)은 원래대로 = 라벨 규칙의 X.
    ③ item1a_pfx — 후보가 모두 0단어면 머리 앞 비문자 1~8자(«.00ITEM 1A. RISK FACTORS» · PRGO 2016-11)를 떼고 다시 찾는다.
  형태(사양 params 그대로 = 카드 판 · 필드 shape · parse_status · pair_status · SimRF): 상용구 정규식을 절의 첫 200 토큰
    (공백으로 이은 것)에 건다. B = 적중 & < 150 단어 · U = 적중 & ≥ 150 · F = 적중 없음 & ≥ 500 · 적중 없음 & < 500 =
    분리 실패(split_fail) · 머리 없음 = no_1a. 단어 = 절 토큰 수(머리 글 제외).
  형태 v2(랩 수정안 · 필드 *_v2 · 카드 판을 바꾸지 않고 옆에 싣는다 · 쓸지는 등록 때 정한다). 경계 · 토큰 · 문턱은 같고 상용구
    적중만 넓힌다 — 카드 정규식 ∪ «변경 없음» 변형 ∪ 갱신 선언 ∪ (500단어 미만일 때만) 10-K 위험요인 참조문. 근거: 검증 표본과
    겹치지 않는 탐색 표본 500건에서 카드 판 split_fail 92건 가운데 78건이 사람이 읽기에 B/U(«have not been any material
    changes» · «you should carefully consider the factors discussed in Part I, Item 1A … Annual Report» 등)였다.
    두 판 모두 같은 손 라벨 표본으로 채점한다(vscore).
  형태 v3(랩 수정안 · 필드 *_v3 · 카드 판 · v2 옆에 싣는다 · 라운드 2 표본을 뽑기 전에 고정). v2 에서 넷을 바꾼다 —
    ① 참조문 대상에 S-4 등록신고서 · 위임장/투자설명서 · 정보 설명서 · 앞 10-Q(«this Quarterly Report» 제외)를 더하고 사이 낱말을
       16 → 24 로(PSKY 0002041610-25-000013 · CSX · PM · KVUE · BHGE) · ② FLS · 안전항 문단(제목 줄 + 그 아래 문단, 또는
       «forward-looking» 과 강한 경고어가 한 줄에)은 B/U 150단어 문턱에 세지 않는다(KSS 0000885639-15-000013 · TYL · EVRG) ·
       ③ 갱신 선언(upd)이 «… and supersede/restate the risk factors»(복수) · «marked with an asterisk» 와 함께면 500단어 이상에서 F
       (WDC · BMRN · PNR · CMI · FISV · TMUS · NI · BATRA — 전 목록 재기재) · ④(목록 밖 랩 추가) 수동형 갱신 선언 «… are supplemented
       and updated as follows» · «… is amended and restated as follows» · «… is updated to add the following» 도 upd(EIX · AEP · KO ·
       CTVA · WBD · FCX · NSC — v2 는 F 나 split_fail). AMGN 0000318154-20-000060(3,784단어)은 «Below, we are providing, in
       supplemental form, the material changes to our risk factors» 라 라벨 규칙상 U(갱신 선언 + 일부) — ③ 은 이것을 F 로 바꾸지
       않는다(길이만으로 막는 규칙은 AMGN 2024~26 의 8~11천 단어 보충분 같은 진짜 U 를 함께 F 로 만든다).

짝(사양 R2 rule (3) + r_r2flags 의 랩 선택과 같게).
  같은 그룹의 **바로 앞** 10-Q 원본(reportDate 순). 간격이 70~200일이면 짝, 아니면 gap_out(더 앞 문서로 건너뛰지 않는다).
  1분기 10-Q 의 바로 앞은 전년 3분기 10-Q 다(4분기는 10-K). 같은 그룹 같은 reportDate 가 둘 이상이면 가장 먼저 가용한 것만
  남긴다(나머지는 dropped · dup_period). 바로 앞 문서가 현재 문서보다 늦게 가용하면 prior_late(그 시점에 짝을 지을 수 없다).
  한쪽이 F · 다른 쪽이 B/U 면 shape_switch → SimRF 결측(값은 SimRF_sw 에 진단용으로만). 한쪽이라도 절이 없으면 prior_fail/cur_fail.
  SimRF = 두 절 단어빈도 벡터의 코사인(CMN Sim_Cosine). SimDoc = 같은 짝의 문서 전체 코사인(형태 규칙 없음).
  dlog_len_rf = log(n_rf) − log(n_rf_prev). ixbrl_switch = isInlineXBRL 이 짝 사이에 다르다.

가용(사양 R2 rule (2) · 가용일 규칙 v2 = avail_rule).
  acceptanceDateTime 은 실제 UTC 다(§B 비평 실측). ET 로 바꿔(America/New_York) 16:00 이후 접수이거나 거래일이 아니면
  다음 NYSE 거래일(refresh_events._holidays + ADHOC). pub_m = 가용일의 달. 조기폐장(13:00)은 여기서 반영하지 않는다
  (r_r2flags 랩 선택 ③ 은 accepted_et 로 스스로 다시 계산한다 — 아래 두 바닥 규칙도 r_r2flags 에는 없다 · 선언).
  v2(2026-09-25): 가용일은 filingDate 보다 이를 수 없다 — 접수 규칙 날짜가 filingDate 보다 이르면 filingDate 다음 거래일
  (avail_how = fd_floor). 접수 날짜가 filingDate 뒤 NYSE 거래일 3일을 넘으면(재접수 시각 · BKNG 0001075531-15-000074 · CRM
  0001108524-22-000007 · CRL 0001100682-20-000041) filingDate 다음 거래일로 두고 fd_late 로 표지한다. 바뀐 수는 validation.json
  avail_fix.
  v3(2026-09-26 · 등록 전 · 검토 지적 «숨은 ET 표기»): 2023 전(filingDate < 2023-01-01) 문서 가운데 원본 acceptanceDateTime 의 시각을
  ET 로 읽으면 filingDate 그날 16:00–17:30 인 것은 UTC 로 읽든 ET 로 읽든 filingDate 와 맞아 어느 쪽인지 알 수 없다(ET 로만 읽히는
  기록 99건은 모두 2013–2022 · 17:30 ET 뒤 실제 접수 가운데 약 6%가 ET 표기). UTC 로 읽으면 11:00–13:30 ET 라 그날 가용이 되므로
  하루 이를 수 있다 → filingDate 다음 거래일(avail_how = fd_etamb · 보수). 진짜 UTC 인 문서도 하루 늦어진다(선언).
  🔒 선언 — fd_floor 는 ET 읽기보다 하루 늦다: fd_floor 문서(접수 규칙 날짜 < filingDate · 대개 ET 표기 기록)는 filingDate 다음
  거래일인데, 그 기록을 ET 로 읽은 가용일보다 NYSE 거래일 하루(드물게 이틀) 늦다(검토 실측 93건 중 89건 1일 · 4건 2일 ·
  pub_m 이 늦어진 세계 안 문서 7건) — 보수 쪽이고 그대로 둔다(avail_fix.fd_floor_vs_et_reading 이 문서마다 잰다).

검증(수익 없이 · 등록 전).
  손 라벨 — vsample 이 시드 고정(SEED + 1000 × 라운드)으로 뽑고(라운드 1: 연도 · iXBRL · 파서 형태 순으로 줄 세워 계통 추출 =
    비례 층화 · 라운드 2: STRATA2 의 지목 층 — plain 경로 전부 · 교차참조 색인 · FLS 문구 짧은 U · 참조문 · 긴 upd — 과 무작위
    나머지 · 앞 라운드 표본과 설계에 쓴 문서(design_docs)는 뺀다 · 층별 · 모집단 가중 성적도 싣는다),
  vview 가 파서 결과를 숨긴 채 문서 골격(머리 모양 줄)과 본문을 보여 준다. 라벨(시작 줄 · 끝 줄 · 형태)은
  data/_tenq_rf/handlabels.json 에 사람이 적는다. vscore 가 경계의 토큰 정밀도·재현율 · ±10% 단어수 일치율 · 형태 혼동표를 낸다.
  합격선(사양): ±10% 안 문서 ≥ 90% · 형태 정확도 ≥ 95%.

사용:
    SEC_UA="이름 연락처" python build/tenq_rf_build.py check      # index.json 1건 + submissions 1건 · HTTP 200 · gzip · 전송량 표본
    SEC_UA=... python build/tenq_rf_build.py list                  # 대상 10-Q 목록(캐시된 submissions) → RBATCH_RAW/tenq/_list.json
    SEC_UA=... python build/tenq_rf_build.py fetch [--workers 3] [--limit N] [--sample K]
    SEC_UA=... python build/tenq_rf_build.py parse [--procs 4]     # 문서별 특징 → RBATCH_RAW/tenq/feat · _parsed.json
    SEC_UA=... python build/tenq_rf_build.py repin                 # 동작 불변 re-pin(PARSER_REPIN · 표본 재파싱 대조 뒤 해시 표지만 바꾼다)
    SEC_UA=... python build/tenq_rf_build.py build                 # 짝 · SimRF · SimDoc · 점검 → data/_tenq_rf.json
    SEC_UA=... python build/tenq_rf_build.py vsample [--n 100] [--round 1]
    SEC_UA=... python build/tenq_rf_build.py vview ACC … | ACC:S:E …           # 라벨용 보기(파서 결과 숨김)
    SEC_UA=... python build/tenq_rf_build.py vscore [--round 1] [--as 1_rescore]   # --as: 앞 라운드 라벨을 지금 파서로 다시 채점
    SEC_UA=... python build/tenq_rf_build.py xdoc [--n 200]            # (2) 문서 수준 단어수 순위상관(독립 파서)
    SEC_UA=... python build/tenq_rf_build.py r2comp                    # R2 Q1 표지 구성(개수만 · 등록 설계 입력) → data/_tenq_rf/r2_composition.json
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import inspect
import io
import json
import math
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 🚨 SEC_UA 가 없으면 거부한다(edgar.py 의 기본 UA 를 조용히 쓰지 않는다 — 연락처는 사용자가 정한다). 값은 어디에도 적지 않는다.
if not (os.environ.get("SEC_UA") or "").strip():
    sys.exit("🚨 SEC_UA 환경변수가 없다 — SEC 요청의 User-Agent(이름 + 연락처)를 명시적으로 정해서 넘길 것. "
             "edgar.py 의 기본값은 쓰지 않는다.")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402
import issuer_map as IM  # noqa: E402  load_map · load_refs · sector_at · Manifest · _rj · _wj · _madd (SEC_UA 검사 포함)
import refresh_events as REV  # noqa: E402  NYSE 휴장 규칙(_holidays · ADHOC) — 규칙은 한 곳에만

if edgar.UA != os.environ["SEC_UA"]:
    sys.exit("🚨 edgar.UA 가 SEC_UA 와 다르다 — edgar.py 가 환경변수를 읽지 않았다")

import lxml.etree as ET  # noqa: E402
import lxml.html  # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RAW = IM.RAW
RAW_T = os.path.join(RAW, "tenq")
DOC_DIR = os.path.join(RAW_T, "doc")
FEAT_DIR = os.path.join(RAW_T, "feat")
LIST = os.path.join(RAW_T, "_list.json")
PARSED = os.path.join(RAW_T, "_parsed.json")
OUT = os.path.join(DATA, "_tenq_rf.json")
VDIR = os.path.join(DATA, "_tenq_rf")
MAN = os.path.join(VDIR, "manifest.json")
LABELS = os.path.join(VDIR, "handlabels.json")
VALID = os.path.join(VDIR, "validation.json")

WIN0 = "2013-07"                  # 사양: 2013-07..2026-09(첫 짝 포함)
LEAD = 11                         # 그룹 첫 비금융 멤버월 − 11개월부터(첫 짝)
SEED = 20260925                   # 손 라벨 표본 시드(고정)
FIN = "Financials"
CHECK_URLS = ("https://www.sec.gov/Archives/edgar/data/320193/000032019324000081/index.json",
              "https://data.sec.gov/submissions/CIK0000200406.json")
NY = None                         # zoneinfo(America/New_York) — 쓰는 곳에서 만든다(워커 import 가볍게)


# ════════════════════════════════════════════════════════════════════════
# 파서 — 이 절의 함수 · 상수만 PARSER_HASH 에 든다(바꾸면 해시가 바뀐다 · §G 는 해시로 같은 파서임을 확인)
# ════════════════════════════════════════════════════════════════════════
BLOCK_TAGS = frozenset("p div br tr li ul ol h1 h2 h3 h4 h5 h6 table hr center blockquote pre dl dt dd section "
                       "article header footer body html caption thead tbody tfoot form address title".split())
CELL_TAGS = frozenset(("td", "th"))
SKIP_TAGS = frozenset(("script", "style", "head", "ix:header", "noscript", "xml"))
RX_HIDDEN = re.compile(r"display\s*:\s*none", re.I)
RX_WS = re.compile(r"[\s\u00a0\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]+")
RX_DASH = re.compile(r"[\u2010-\u2015\u2212\ufe58\ufe63\uff0d]")
RX_DIGIT = re.compile(r"[0-9]")
RX_ALPHA = re.compile(r"[A-Za-z]")
RX_TOK = re.compile(r"[a-z#]+")
RX_XMLDECL = re.compile(r"^\s*<\?xml[^>]*\?>", re.I)
LXML_VERSIONS = [list(ET.LXML_VERSION), list(ET.LIBXML_VERSION), list(ET.LIBXSLT_VERSION)]   # 파서 입력으로 해시에 든다(2026-09-26)
NUM_TABLE_SHARE = 0.15            # 사양: 숫자 비중 15% 초과 표 제거
# 절 머리 · 끝 — 줄 머리에만 건다(소문자 · 대시 정규화 뒤)
RX_START = re.compile(r"^(?:part\s*(?:ii|2)\W{0,6})?items?\s*(?:1|i)\s*a(?:(?![a-z0-9])|(?=risk))\W{0,6}(risk\s*factors?)?")
RX_RFLINE = re.compile(r"^risk\s*factors?\W*$")
# 번호가 틀린 머리(«Item 1. Risk Factors.» · Howmet 2020) — 어느 item 번호든 뒤가 risk factors 면 머리로 본다(고르기 규칙은 같다)
RX_START_ANY = re.compile(r"^(?:part\s*(?:ii|2)\W{0,6})?items?\s*(?:[0-9]{1,2}|[ivx]{1,4})\s*\.?\s*(?:[a-z](?![a-z]))?"
                          r"\W{0,6}(risk\s*factors?)")
_TITLES = r"unregistered|defaults?|mine|other|exhibits?|legal|submission|changes|purchases?|issuer|controls?|quantitative"
RX_END = re.compile(r"^(?:part\s*(?:ii|2)\W{0,6})?items?\s*(?:1\s*b|2|3|4|5|6)(?:(?![0-9a-z])|(?=" + _TITLES + r"))"
                    r"(?:\s*(?:[.:\-)(,&]|and\b|through\b|to\b)|\s*$|\s*(?:" + _TITLES + r"|not\b|none\b))")
RX_END2 = re.compile(r"^(?:signatures?|exhibit\s+index|index\s+to\s+exhibits|exhibits?(?:\s+index)?)\W*$")
RX_PART2 = re.compile(r"^part\s*(?:ii|2)(?![a-z0-9])")
RX_ITEM4C = re.compile(r"^items?\s*4\W{0,6}controls?\s+and\s+procedures")
MIN_PICK_WORDS = 8                # 절 후보 고르기: 단어 ≥ 8 인 마지막 후보(목차 항목 배제)
HEAD_WORDS, B_MAX, F_MIN = 200, 150, 500       # 사양 params
RX_BOILER = re.compile(r"\bno material changes?\b|\bnot (?:been )?materially changed\b"
                       r"|\bthere (?:have|has) been no material changes?\b")
# v2(랩 수정안 · 카드 정규식을 바꾸지 않고 옆에 싣는다) — 탐색 표본(검증 표본과 겹치지 않음)에서 카드 정규식이 놓친 상용구 셋:
#   ① «변경 없음» 변형(not been any material changes · have not changed materially · remain unchanged · were consistent with)
#   ② 10-K 위험요인 참조문(«…factors discussed in Part I Item 1A of our Annual Report on Form 10-K» — SEC 평이 문체 표준 문장)
#   ③ 갱신 선언(«the following updates/supplements the risk factor…» · «material additions»)
#   ②는 절이 500단어 미만일 때만 적중으로 친다(긴 전문 재기재의 머리에도 10-K 참조가 흔하다 — 그런 절을 U 로 바꾸지 않는다).
#   «supersede · restate»(전문 재기재 선언)가 첫 200 토큰에 있으면 ②는 적중으로 치지 않는다(AAPL 식 전문 재기재 = F).
#   형태: 적중 & < 150 → B · 적중 & ≥ 150 → U · 적중 없음 & ≥ 500 → F · 그 밖 split_fail(카드와 같은 문턱).
_ADJ = r"(?:material|materially|significant|significantly|substantive|substantial|other|additional|new|further|such|major|" \
       r"meaningful|additions or|additions or material|updates or)"
_CHG = r"(?:changes?|additions?|updates?|modifications?|revisions?|developments?)"
RX_NOCHG2 = re.compile(r"\bno (?:" + _ADJ + r" ){0,3}" + _CHG + r"\b"
                       r"|\bno (?:additional|new|other) risk factors?\b"
                       r"|\bnot (?:been |had |identified |experienced |made )?any (?:" + _ADJ + r" ){0,3}(?:" + _CHG[3:-1]
                       + r"|risk factors?)\b"
                       r"|\bnot (?:(?:materially|significantly|substantially|substantively) )?(?:changed|change)\b"
                       r"|\bremain(?:s|ed)? (?:(?:substantially|materially|largely|essentially) )?(?:unchanged|the same|"
                       r"relevant|applicable|accurate|current)\b"
                       r"|\b(?:are|is|were|was) (?:(?:substantially|materially|largely|essentially) )?(?:unchanged|consistent with)\b")
RX_REF2 = re.compile(r"\b(?:risk factors?|factors|risks)\b(?: \w+){0,12}? (?:discussed|described|disclosed|set forth|contained|"
                     r"included|identified|outlined|listed|presented|detailed|reported|found|documented|noted|referred to|"
                     r"appear|appears)(?: \w+){0,16}? (?:annual report|fiscal form|(?:our|its|the|company|registrant) form)\b"
                     r"|\b(?:see|refer to|reference is made to|incorporated (?:herein )?by reference)(?: \w+){0,16}? "
                     r"(?:annual report|fiscal form|(?:our|its|the|company|registrant) form)\b"
                     r"|\b(?:annual report|(?:our|its|the|company|registrant) form)(?: \w+){0,10}? (?:includes?|contains?|"
                     r"discusses|describes|identif(?:y|ies))(?: \w+){0,6}? (?:risk factors?|risks|factors)\b")
RX_UPD2 = re.compile(r"\bthe following (?:\w+ ){0,4}?(?:updates?|supplements?|amends?|modif(?:y|ies)|adds?|reflects?)\b"
                     r"|\b(?:below|above) (?:updates?|supplements?|amends?|modif(?:y|ies))\b"
                     r"|\b(?:updates?|supplements?|amends?) and (?:updates?|supplements?|amends?)\b"
                     r"|\b(?:updates?|supplements?|amendments?|additions?|changes?) (?:to|of) (?:\w+ ){0,3}?risk factors?\b"
                     r"|\b(?:below|following) (?:are|is) (?:\w+ ){0,3}?(?:updates?|additions?|changes?)\b"
                     r"|\brisk factors? (?:\w+ ){0,3}?(?:has|have|were|was) (?:been )?(?:added|updated|supplemented|amended)\b"
                     r"|\bupdated risk factors?\b")
RX_SUPERSEDE = re.compile(r"\bsupersed|\brestat")
# ── 경계 b2(2026-09-25 적대 검토 반영 · 대체 경로 셋만 바뀐다 — item 1a 머리를 찾은 문서의 경계는 그대로) ──
#   ① plain 경로(머리 없이 «RISK FACTORS» 줄만)의 끝 = 다음 번호 머리 · 서명/첨부 줄 «또는» 다음 대문자 항목 제목 줄
#      (LEGAL PROCEEDINGS · UNREGISTERED SALES … · DEFAULTS UPON SENIOR SECURITIES · MINE SAFETY DISCLOSURES · OTHER INFORMATION ·
#      EXHIBITS · SIGNATURES · 교차참조 색인 10-Q 는 Part I 제목(재무제표 · MD&A · 시장위험 · 통제와 절차)도). 번호 없는 제목을
#      쓰는 WY 2016~19 · MOH 2021~25 · EIX 2016 은 절이 Item 2~5 를 삼켰다.
#   ② xref 경로 — «Form 10-Q Cross Reference Index» 가 있는 문서(CAH · INTC 2018~ · ILMN · GE · GEV)에서 item 1a 후보가 모두
#      8단어 미만(색인 줄 · 쪽 번호)이면 문서 전체의 «Risk Factors» 제목 줄을 후보로 삼아(끝 = ①) 8단어 이상인 마지막 것을 고른다.
#      본문 절이 없으면(GE 의 «Not applicable(b)» 색인 각주) 원래 고르기 그대로다.
#   ③ 머리 앞 쓰레기 글자(«.00ITEM 1A. RISK FACTORS» · PRGO 2016-11) — item 1a 후보가 모두 0단어일 때만 앞의 비문자 1~8자를 떼고
#      «item 1a … risk factors» 머리를 다시 찾는다(sec_how = item1a_pfx).
RX_XREF = re.compile(r"cross\s*-?\s*reference\s+(?:index|table|sheet)|10-q\s+cross|10-q\s+(?:cross\s*)?reference\s+index")
_T_TITLES = (r"legal\s+proceedings|unregistered\s+sales?\b|issuer\s+purchases\s+of\s+equity|purchases\s+of\s+equity\s+securities|"
             r"share\s+repurchases?\b|defaults\s+upon\s+senior\s+securities|mine\s+safety\s+disclosures?|submission\s+of\s+matters|"
             r"other\s+information|exhibits?\b|index\s+to\s+exhibits|signatures?\b|financial\s+statements|"
             r"management'?s\s+discussion\s+and\s+analysis|quantitative\s+and\s+qualitative\s+disclosures?|controls\s+and\s+procedures")
RX_TITLE = re.compile(r"^(?:part\s*(?:i|ii|1|2)\W{0,6})?(?:" + _T_TITLES + r")")
TITLE_MAX_WORDS = 14
_SMALL = frozenset("a an and as at by for from in into of on or the to upon with about under its our".split())
RX_PFX = re.compile(r"^[^a-z]{1,8}(?=(?:part\s*(?:ii|2)\W{0,6})?items?\s*(?:1|i)\s*a)")
# ── 형태 v3(랩 수정안 · 필드 *_v3 · 카드 판 · v2 는 그대로 두고 옆에 싣는다 · 쓸지는 등록 때 정한다) ──
#   v2 에서 셋을 바꾼다(검증 표본 2 를 뽑기 전에 고정 · 탐색 문서는 handlabels.json 라운드 2 의 design_docs 에 적고 표본에서 뺀다).
#   ① 참조문(ref) 대상 넓힘 — 10-K 뿐 아니라 S-4 등록신고서 · (합동) 위임장/투자설명서 · 정보 설명서 · 앞 10-Q(«our Quarterly
#      Report on Form 10-Q for …» · «this Quarterly Report» 는 제외 — 같은 10-Q 안의 교차참조는 X), 사이 낱말 16 → 24개(CSX · PM 의
#      «… discussed under Part II, Item 7 (MD&A) of … most recent annual report» 가 16개를 넘었다). 500단어 미만 · 전문 재기재 선언
#      없음 조건은 v2 와 같다.
#   ② 미래예측(FLS) · 안전항 문단은 B/U 150단어 문턱에 세지 않는다 — «Forward-Looking Statements» 류 제목 줄과 그 아래 문단, 또는
#      «forward-looking» 과 강한 경고어(PSLRA · safe harbor · undue reliance · differ materially · not guarantees · 모르는 추가 위험 …)가
#      한 줄에 함께 있는 문단. 단어 수(n_words_rf) · SimRF · F 문턱(500)은 그대로다.
#   ③ 갱신 선언(upd)이 «전문 재기재» 선언과 함께면 F — «… update/supplement/amend and supersede/restate the risk factors/risks/
#      those …»(단수 «the risk factor» 한 개 교체는 제외) · «marked with an asterisk»(전 목록 재기재 + 바뀐 곳 표시). 500단어 이상일 때만.
#   ④ (랩 추가 · 목록의 셋 밖) 수동형 갱신 선언도 upd — «… are supplemented and updated as follows»(EIX · AEP) · «… is amended and
#      restated as follows / as set forth below»(HSIC · WBD) · «… are supplemented by the following»(CTVA) · «… is updated to add /
#      to include the following»(FCX · NSC) · «as updated and supplemented below»(KO). v2 는 이들을 F(500 이상) · split_fail 로 둔다.
_TGT3 = (r"(?:annual report|fiscal form|(?:our|its|the|company|registrant) form|registration statement|(?:joint )?proxy statement|"
         r"prospectus|information statement|(?<!this )quarterly reports? on form)")
RX_REF3 = re.compile(r"\b(?:risk factors?|factors|risks)\b(?: \w+){0,12}? (?:discussed|described|disclosed|set forth|contained|"
                     r"included|identified|outlined|listed|presented|detailed|reported|found|documented|noted|referred to|"
                     r"appear|appears)(?: \w+){0,24}? " + _TGT3 + r"\b"
                     r"|\b(?:see|refer to|reference is made to|incorporated (?:herein )?by reference)(?: \w+){0,24}? " + _TGT3 + r"\b"
                     r"|\b(?:annual report|(?:our|its|the|company|registrant) form|registration statement|proxy statement|prospectus)"
                     r"(?: \w+){0,10}? (?:includes?|contains?|discusses|describes|identif(?:y|ies))(?: \w+){0,6}? (?:risk factors?|risks|factors)\b")
RX_UPD3X = re.compile(r"\b(?:is|are|were|was|has been|have been) (?:hereby )?(?:supplemented|updated|amended)(?: and (?:restated|"
                      r"supplemented|updated))? (?:as follows|by the following|to (?:add|read|include|reflect)|as set forth below|below)\b"
                      r"|\bsupplemented and updated\b|\bupdated and supplemented\b")
RX_RESTATE3 = re.compile(r"\b(?:updates?|supplements?|amends?) and (?:supersedes?|restates?) (?:the (?:risk factors|risks and uncertainties"
                         r"|risks)|those)\b|\bmarked with an asterisk\b")
RX_FLSCUE = re.compile(r"forward[- ]?looking|safe[- ]harbou?r|private securities litigation reform act")
RX_FLSSTRONG = re.compile(r"private securities litigation reform act|safe[- ]harbou?r|undue reliance|speaks? only as of|undertakes? no "
                          r"(?:obligation|duty)|obligation to (?:publicly )?(?:update|revise)|within the meaning of|section 27a|section 21e|"
                          r"words such as|differ materially|not guarantees?|actual (?:outcome|results)|disclaimer|cautionary|lose all or "
                          r"(?:a )?part|currently unaware|not (?:presently|currently) known|(?:deem|believe|consider)s? (?:to be )?immaterial")
RX_FLSHEAD = re.compile(r"^\W*(?:cautionary (?:note|statements?|language)(?: (?:regarding|concerning|about|relating to|with respect to))?"
                        r"(?: forward[- ]?looking (?:statements?|information))?|forward[- ]?looking (?:statements?|information)|"
                        r"safe[- ]harbou?r(?: statements?)?|(?:special |important )?(?:note|information|statement) (?:regarding|concerning|"
                        r"about|on) forward[- ]?looking (?:statements?|information))\W*$")
FLS_HEAD_TOK, FLS_SUBHEAD_TOK = 10, 12


def fls_tokens(body):
    """절 본문 줄 목록 → FLS · 안전항 문단의 토큰 수(v3 B/U 문턱에서 뺀다). (가) FLS 제목 줄(≤ 10토큰)과 그 바로 아래 문단들 —
    FLS 문구나 강한 경고어가 든 줄이 이어지는 동안(단어 없는 쪽 번호 줄은 건너뛴다 · 문구 없는 첫 줄에서 끝난다) · (나) 제목과
    무관하게 «forward-looking» 과 강한 경고어가 한 줄(문단)에 함께 있는 줄."""
    n, under = 0, False
    for ln in body:
        low = RX_DASH.sub("-", ln.lower())
        nt = len(tokens(ln))
        if nt <= FLS_HEAD_TOK and RX_FLSHEAD.match(low.strip()):
            n += nt
            under = True
            continue
        cue, strong = bool(RX_FLSCUE.search(low)), bool(RX_FLSSTRONG.search(low))
        if under and nt > 0:
            if nt > FLS_SUBHEAD_TOK and (cue or strong):
                n += nt
                continue
            under = False
        if cue and strong:
            n += nt
    return n


def shape_v3(toks, body):
    """v3 형태 → (형태 또는 None, 상태, 적중 종류). 적중 종류: card · nochg · upd · upd_restate(→ F) · ref."""
    head = " ".join(toks[:HEAD_WORDS])
    kind = None
    if RX_BOILER.search(head):
        kind = "card"
    elif RX_NOCHG2.search(head):
        kind = "nochg"
    elif RX_UPD2.search(head) or RX_UPD3X.search(head):
        kind = "upd"
    nw = len(toks)
    if kind is None and nw < F_MIN and RX_REF3.search(head) and not RX_SUPERSEDE.search(head):
        kind = "ref"
    if kind == "upd" and nw >= F_MIN and RX_RESTATE3.search(head):
        return "F", "ok", "upd_restate"
    if kind:
        return ("B" if nw - fls_tokens(body) < B_MAX else "U"), "ok", kind
    if nw >= F_MIN:
        return "F", "ok", None
    return None, "split_fail", None


def shape_v2(toks):
    """v2 형태 → (형태 또는 None, 상태, 적중 종류). 적중 종류: card(카드 정규식) · nochg · ref · upd."""
    head = " ".join(toks[:HEAD_WORDS])
    kind = None
    if RX_BOILER.search(head):
        kind = "card"
    elif RX_NOCHG2.search(head):
        kind = "nochg"
    elif RX_UPD2.search(head):
        kind = "upd"
    nw = len(toks)
    if kind is None and nw < F_MIN and RX_REF2.search(head) and not RX_SUPERSEDE.search(head):
        kind = "ref"                      # 참조문은 짧은 절(< 500)에만 — 긴 전문 재기재 머리의 10-K 참조를 U 로 바꾸지 않는다
    if kind:
        return ("B" if nw < B_MAX else "U"), "ok", kind
    if nw >= F_MIN:
        return "F", "ok", None
    return None, "split_fail", None


def decode_doc(b: bytes) -> str:
    if b[:3] == b"\xef\xbb\xbf":
        b = b[3:]
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        s = b.decode("cp1252", errors="replace")
    return RX_XMLDECL.sub("", s, count=1)


def _hidden(el) -> bool:
    st = el.get("style")
    return bool(st and RX_HIDDEN.search(st))


def _own_text_share(tb) -> bool:
    """표의 자기 글(안쪽 표 · 숨김 요소 제외)에서 숫자 ÷ (숫자 + 알파벳) > 15% 인가."""
    d = a = 0
    w = ET.iterwalk(tb, events=("start", "end"))
    for ev, el in w:
        tag = el.tag if isinstance(el.tag, str) else ""
        tag = tag.lower()
        if ev == "start":
            if el is not tb and (tag == "table" or tag in SKIP_TAGS or _hidden(el)):
                w.skip_subtree()
                continue
            if el.text:
                d += len(RX_DIGIT.findall(el.text))
                a += len(RX_ALPHA.findall(el.text))
        else:
            if el is not tb and el.tail:
                d += len(RX_DIGIT.findall(el.tail))
                a += len(RX_ALPHA.findall(el.tail))
    return (d / (d + a)) > NUM_TABLE_SHARE if (d + a) else False


def doc_lines(b: bytes):
    """원문 바이트 → ([(줄 글, 숫자표 줄 여부)], 정보). 줄 글은 공백 정규화된 원래 대소문자."""
    s = decode_doc(b)
    root = lxml.html.document_fromstring(s)
    num = {}
    for tb in root.iter("table"):
        num[tb] = _own_text_share(tb)
    lines, buf, tstack, skipped = [], [], [], set()
    info = {"n_ixheader": 0, "n_hidden": 0, "ixh_text": ""}

    def flush():
        if buf:
            t = RX_WS.sub(" ", "".join(buf)).strip()
            buf.clear()
            if t:
                lines.append((t, bool(tstack and num.get(tstack[-1]))))

    w = ET.iterwalk(root, events=("start", "end"))
    for ev, el in w:
        tag = el.tag
        if not isinstance(tag, str):
            if ev == "end" and el.tail:
                buf.append(el.tail)
            continue
        tag = tag.lower()
        if ev == "start":
            if tag in SKIP_TAGS or _hidden(el):
                if tag == "ix:header":
                    info["n_ixheader"] += 1
                    info["ixh_text"] += " ".join(el.itertext())[:4000]
                elif tag not in SKIP_TAGS:
                    info["n_hidden"] += 1
                    for x in el.iter("ix:header"):
                        info["n_ixheader"] += 1
                        info["ixh_text"] += " ".join(x.itertext())[:4000]
                skipped.add(id(el))
                w.skip_subtree()
                continue
            if tag in BLOCK_TAGS:
                flush()
            elif tag in CELL_TAGS:
                buf.append(" ")
            if tag == "table":
                tstack.append(el)
            if el.text:
                buf.append(el.text)
        else:
            if id(el) in skipped:
                skipped.discard(id(el))
            else:
                if tag in BLOCK_TAGS:
                    flush()
                elif tag in CELL_TAGS:
                    buf.append(" ")
                if tag == "table" and tstack:
                    tstack.pop()
            if el.tail:
                buf.append(el.tail)
    flush()
    return lines, info


def tokens(text: str):
    """사양 전처리: 소문자 · 숫자 → '#' · 두 글자 이상 알파벳 토큰만."""
    s = RX_DIGIT.sub("#", text.lower())
    return [t for t in RX_TOK.findall(s) if len(t) >= 2 and "#" not in t]


def _hnorm(t: str) -> str:
    return RX_DASH.sub("-", t.lower()).replace("\u2019", "'").strip()


def head_kind(lines, i):
    """줄 i 가 절 머리인가 → (종류, 본문 시작 줄, 머리 줄에 붙은 본문 글) 또는 None.
    종류: 'item1a'(item 1a · risk factors) · 'item1a_bare'(item 1a 만) · 'item_other'(다른 번호 · risk factors) ·
    'plain'(risk factors 만)."""
    h = _hnorm(lines[i][0])
    m = RX_START.match(h)
    if m:
        rest = lines[i][0][len(lines[i][0]) - len(h[m.end():]):] if len(h) == len(lines[i][0]) else h[m.end():]
        if m.group(1):
            return "item1a", i + 1, rest
        if not re.search(r"[a-z]", h[m.end():]):
            j = i + 1
            if j < len(lines) and RX_RFLINE.match(_hnorm(lines[j][0])):
                return "item1a_bare", j + 1, ""
            return "item1a_bare", i + 1, ""
        return None
    m = RX_START_ANY.match(h)
    if m:
        return "item_other", i + 1, lines[i][0][m.end():] if len(h) == len(lines[i][0]) else h[m.end():]
    if RX_RFLINE.match(h):
        return "plain", i + 1, ""
    return None


def is_end(lines, i) -> bool:
    h = _hnorm(lines[i][0])
    if RX_END.match(h):
        return len(h.split()) <= 40 or bool(re.match(r"^(?:part\s*(?:ii|2)\W{0,6})?items?\s*[1-6]\s*b?\W{0,6}"
                                                     r"(?:unregistered|defaults?|mine|other|exhibits?|legal|submission|"
                                                     r"purchases?|issuer)", h))
    return bool(RX_END2.match(h))


def _capitalised(t: str) -> bool:
    """줄이 모두 대문자이거나 제목 대소문자(작은 낱말 빼고 모든 낱말이 대문자로 시작)인가."""
    letters = [ch for ch in t if ch.isalpha()]
    if not letters:
        return False
    if not any(ch.islower() for ch in letters):
        return True
    ws = re.findall(r"[A-Za-z][A-Za-z'’]*", t)
    big = [w for w in ws if w.lower() not in _SMALL]
    return bool(big) and all(w[0].isupper() for w in big)


def is_title(lines, i) -> bool:
    """번호 없는 10-Q 항목 제목 줄(대문자 · 제목 대소문자 · 14단어 이하) — plain · xref 경로의 절 끝(경계 b2 ①)."""
    t = lines[i][0]
    if len(t.split()) > TITLE_MAX_WORDS:
        return False
    return bool(RX_TITLE.match(_hnorm(t))) and _capitalised(t)


def head_pfx(lines, i):
    """경계 b2 ③ — 앞 비문자 1~8자(«.00ITEM 1A. RISK FACTORS»)를 떼면 «item 1a … risk factors» 머리인가 → (본문 시작 줄, 붙은 본문)."""
    h = _hnorm(lines[i][0])
    m0 = RX_PFX.match(h)
    if not m0:
        return None
    h2 = h[m0.end():]
    m = RX_START.match(h2)
    if not (m and m.group(1)):
        return None
    return i + 1, h2[m.end():]


def sec_tokens(lines, i0, rest, e):
    """절 본문 토큰(머리 줄에 붙은 본문 + 본문 줄 i0..e−1 · 숫자 표 줄 제외)과 줄별 토큰 수."""
    toks, per = [], {}
    if rest:
        t = tokens(rest)
        toks += t
        per[i0 - 1] = len(t)
    for k in range(i0, e):
        if lines[k][1]:
            continue
        t = tokens(lines[k][0])
        if t:
            toks += t
            per[k] = len(t)
    return toks, per


def body_span(lines, s):
    """머리 줄 s(사람 라벨 또는 파서) → (본문 첫 줄, 머리 줄에 붙은 본문). 머리가 아닌 줄이면 그 줄부터 본문."""
    hk = head_kind(lines, s)
    if hk:
        return hk[1], hk[2]
    hp = head_pfx(lines, s)
    if hp:
        return hp
    return s, ""


def sec_body(lines, i0, rest, e):
    """절 본문 줄 글 목록(머리 줄에 붙은 본문 + 본문 줄 · 숫자 표 줄 제외) — sec_text 와 v3 FLS 문단 판정에 쓴다."""
    return ([rest] if rest else []) + [lines[k][0] for k in range(i0, e) if not lines[k][1]]


def find_section(lines):
    """→ dict(s, e, i0, rest, how, end_how, n_cand) 또는 None(머리 없음)."""
    import bisect
    n = len(lines)
    ends = [i for i in range(n) if is_end(lines, i)]
    heads = []
    for i in range(n):
        hk = head_kind(lines, i)
        if hk:
            heads.append((i,) + hk)
    tends_ = []                                # 경계 b2 ① — 번호 머리 · 서명/첨부 줄 ∪ 번호 없는 대문자 항목 제목 줄(plain · xref 만)

    def tends():
        if not tends_:
            tends_.append(sorted(set(ends) | {i for i in range(n) if is_title(lines, i)}))
        return tends_[0]

    def next_end(i0, ee):
        k = bisect.bisect_left(ee, i0)
        return (ee[k], "item") if k < len(ee) else (n, "eof")

    def cands(kinds, after=-1, ee=None, hs=None):
        ee = ends if ee is None else ee
        seen, out = set(), []
        for i, kind, i0, rest in (heads if hs is None else hs):
            if kind not in kinds or i <= after:
                continue
            e, how = next_end(i0, ee)
            if e in seen:
                continue                       # 끝이 같은 후보 — 가장 이른 시작 하나(쪽 머리 «continued» 합치기)
            seen.add(e)
            toks, _ = sec_tokens(lines, i0, rest, e)
            out.append({"s": i, "e": e, "i0": i0, "rest": rest, "how": kind, "end_how": how, "nw": len(toks)})
        return out

    c = cands(("item1a", "item1a_bare", "item_other"))
    how = "item1a"
    if (not c or max(x["nw"] for x in c) < MIN_PICK_WORDS) and any(RX_XREF.search(_hnorm(t)) for t, _ in lines
                                                                    if len(t.split()) <= 12):
        # 경계 b2 ② — 교차참조 색인 10-Q: 색인의 item 1a 줄(쪽 번호 · 각주 표지)이 아니라 색인이 가리키는 본문 «Risk Factors» 절.
        cx = [x for x in cands(("plain",), ee=tends()) if x["nw"] >= MIN_PICK_WORDS]
        if cx:
            c, how = cx, "xref"
    if how == "item1a" and (not c or all(x["nw"] == 0 for x in c)):
        # 경계 b2 ③ — 머리 앞 쓰레기 글자
        hp = [(i, "item1a_pfx") + hk for i, hk in ((i, head_pfx(lines, i)) for i in range(n)) if hk]
        cp = [x for x in cands(("item1a_pfx",), hs=hp) if x["nw"] > 0] if hp else []
        if cp:
            c, how = cp, "item1a_pfx"
        else:
            # 대체 경로 — «Risk Factors» 만 있는 줄. Part I 안의 같은 소제목(MD&A · 주석)을 잡지 않도록 본문 Part I 의 마지막
            # «Item 4 Controls and Procedures» 머리 뒤(없으면 마지막 «Part II» 머리 뒤)만 본다. 끝 = 경계 b2 ①.
            i4 = [i for i in range(n) if RX_ITEM4C.match(_hnorm(lines[i][0]))]
            p2 = [i for i in range(n) if RX_PART2.match(_hnorm(lines[i][0])) and len(lines[i][0].split()) <= 10]
            after = i4[-1] if i4 else (p2[-1] if p2 else None)
            c2 = cands(("plain",), after=after, ee=tends()) if after is not None and p2 else []
            if c2:
                c, how = c2, "plain"
    if not c:
        return None
    pick = [x for x in c if x["nw"] >= MIN_PICK_WORDS] or [x for x in c if x["nw"] > 0]
    if not pick:
        return None
    x = dict(pick[-1])
    x["n_cand"] = len(c)
    if how in ("plain", "xref", "item1a_pfx"):
        x["how"] = how
    return x


def shape_of(toks):
    """사양 params 그대로 → (형태 또는 None, 상태, 상용구 적중)."""
    head = " ".join(toks[:HEAD_WORDS])
    hit = bool(RX_BOILER.search(head))
    nw = len(toks)
    if hit:
        return ("B" if nw < B_MAX else "U"), "ok", True
    if nw >= F_MIN:
        return "F", "ok", False
    return None, "split_fail", False


def features(b: bytes):
    """원문 1건 → 특징(§G 전방도 이 함수 하나만 쓴다)."""
    lines, info = doc_lines(b)
    doc_toks = []
    for t, isnum in lines:
        if not isnum:
            doc_toks += tokens(t)
    ixh = RX_WS.sub(" ", info["ixh_text"]).strip()
    joined = " ".join(t for t, _ in lines)
    leak = bool(len(ixh) >= 40 and ixh[:200] in joined)
    out = {"n_lines": len(lines), "n_words_doc": len(doc_toks), "n_ixheader": info["n_ixheader"],
           "n_hidden": info["n_hidden"], "ixh_leak": leak, "tf_doc": collections.Counter(doc_toks)}
    sec = find_section(lines)
    out["has_xref"] = any(RX_XREF.search(_hnorm(t)) for t, _ in lines if len(t.split()) <= 12)
    if sec is None:
        out.update({"parse_status": "no_1a", "shape": None, "n_words_rf": 0, "boiler_hit": None, "tf_rf": {},
                    "sec": None, "sec_text": "", "parse_status_v2": "no_1a", "shape_v2": None, "boiler_v2": None,
                    "parse_status_v3": "no_1a", "shape_v3": None, "boiler_v3": None, "n_fls_v3": 0})
        return out, lines
    toks, per = sec_tokens(lines, sec["i0"], sec["rest"], sec["e"])
    shp, st, hit = shape_of(toks)
    shp2, st2, kind2 = shape_v2(toks)
    body = sec_body(lines, sec["i0"], sec["rest"], sec["e"])
    shp3, st3, kind3 = shape_v3(toks, body)
    out.update({"parse_status": st, "shape": shp, "n_words_rf": len(toks), "boiler_hit": hit,
                "parse_status_v2": st2, "shape_v2": shp2, "boiler_v2": kind2,
                "parse_status_v3": st3, "shape_v3": shp3, "boiler_v3": kind3, "n_fls_v3": fls_tokens(body),
                "tf_rf": collections.Counter(toks),
                "sec": {"s": sec["s"], "e": sec["e"], "how": sec["how"], "end_how": sec["end_how"], "n_cand": sec["n_cand"],
                        "head": lines[sec["s"]][0][:160], "end_line": lines[sec["e"]][0][:160] if sec["e"] < len(lines) else ""},
                "sec_text": "\n".join(body)})
    return out, lines


PARSER_FUNCS = (decode_doc, _hidden, _own_text_share, doc_lines, tokens, _hnorm, head_kind, is_end, _capitalised, is_title,
                head_pfx, sec_tokens, body_span, sec_body, find_section, shape_of, shape_v2, fls_tokens, shape_v3, features)
PARSER_CONSTS = (sorted(BLOCK_TAGS), sorted(CELL_TAGS), sorted(SKIP_TAGS), RX_HIDDEN.pattern, RX_WS.pattern,
                 RX_DASH.pattern, RX_TOK.pattern, NUM_TABLE_SHARE, RX_START.pattern, RX_RFLINE.pattern,
                 RX_START_ANY.pattern, RX_END.pattern,
                 RX_END2.pattern, RX_PART2.pattern, RX_ITEM4C.pattern, MIN_PICK_WORDS, HEAD_WORDS, B_MAX, F_MIN, RX_BOILER.pattern,
                 RX_NOCHG2.pattern, RX_REF2.pattern, RX_UPD2.pattern, RX_SUPERSEDE.pattern,
                 RX_XREF.pattern, RX_TITLE.pattern, TITLE_MAX_WORDS, sorted(_SMALL), RX_PFX.pattern, RX_REF3.pattern, RX_UPD3X.pattern,
                 RX_RESTATE3.pattern, RX_FLSCUE.pattern, RX_FLSSTRONG.pattern, RX_FLSHEAD.pattern, FLS_HEAD_TOK, FLS_SUBHEAD_TOK)
# 2026-09-26 — 해시에 빠져 있던 파서 입력(검토 지적): _own_text_share · tokens · decode_doc 가 직접 쓰는 세 식과 lxml · libxml2 · libxslt 판.
# 동작은 바꾸지 않았다(식 · 함수 그대로) — 해시 입력만 넓혔다(re-pin · PARSER_REPIN).
PARSER_CONSTS_EXTRA = (RX_ALPHA.pattern, RX_DIGIT.pattern, RX_XMLDECL.pattern, LXML_VERSIONS)


def _parser_hash(extra=True) -> str:
    """파서 해시 — PARSER_FUNCS 소스 + PARSER_CONSTS(+ PARSER_CONSTS_EXTRA). extra=False 는 2026-09-25 판 정의(re-pin 대조용)."""
    h = hashlib.sha256()
    for f in PARSER_FUNCS:
        h.update(inspect.getsource(f).encode("utf-8"))
    h.update(json.dumps(PARSER_CONSTS, ensure_ascii=False).encode("utf-8"))
    if extra:
        h.update(json.dumps(PARSER_CONSTS_EXTRA, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


PARSER_HASH = _parser_hash()      # import 때 한 번 — 실행 중 파일이 바뀌어도(getsource 는 파일을 다시 읽는다) 값이 흔들리지 않게
PARSER_HASH_LEGACY = _parser_hash(extra=False)
# 고정 해시(2026-09-26 re-pin — 해시 입력에 RX_ALPHA · RX_DIGIT · RX_XMLDECL · lxml 판을 더했다 · 동작 불변). 앞 고정 = a9de814d6c09
# (2026-09-25 · 경계 b2 + 형태 v3 동결 · 라운드 2 검증 표본을 그 해시로 뽑고 채점했다) · 그 앞 = bfae3758c3a2(경계 b1 + v2 · 라운드 1).
# parse · build 는 지금 파서가 이 값과 다르면 멈춘다 — 파서를 고치면 새 값을 여기 고정하고 새 검증 라운드를 돌린다(§G 전방도
# 이 해시의 파서만 쓴다). lxml 을 올려도 해시가 바뀐다(그러면 다시 검증한다).
PARSER_HASH_PIN = "015210646bad4c9461fda7dc33da5b3ac06010d78e1f2c08b10525e93342bab9"
# re-pin 기록 — 옛 고정의 정의(extra=False)로 지금 코드를 다시 재면 옛 고정과 같아야 한다(함수 · 식이 그대로라는 증명). repin 명령이
# 캐시 _parsed.json 의 해시 표지를 옛 → 새로 바꾸기 전에 그것과 무작위 표본 재파싱 일치를 확인한다.
PARSER_REPIN = {"from": "a9de814d6c098631deca53d7e588170b1f7d9418ba19367860705ee45476c0d2", "date": "2026-09-26",
                "note": "해시 입력에 RX_ALPHA · RX_DIGIT · RX_XMLDECL 패턴과 lxml · libxml2 · libxslt 판을 더했다(검토 지적) — 파서 함수 · "
                        "식은 바꾸지 않았다(동작 불변 · 라운드 2 검증은 그대로 유효). 옛 정의 해시 = from 이어야 한다.",
                "sample": 300, "seed": 20260926}


def _require_pin():
    if PARSER_HASH != PARSER_HASH_PIN:
        raise SystemExit("🚨 파서 해시(%s)가 고정값 PARSER_HASH_PIN(%s)과 다르다 — 파서를 바꿨으면 새 값을 고정하고 검증 라운드를 "
                         "다시 돌릴 것" % (PARSER_HASH[:12], PARSER_HASH_PIN[:12]))
    if PARSER_HASH_LEGACY != PARSER_REPIN["from"]:
        raise SystemExit("🚨 옛 정의의 파서 해시(%s)가 re-pin 기록(%s)과 다르다 — 파서 함수나 식이 바뀌었다" % (
            PARSER_HASH_LEGACY[:12], PARSER_REPIN["from"][:12]))


def parser_hash() -> str:
    return PARSER_HASH


def cosine(a, b):
    if not a or not b:
        return None
    if len(a) > len(b):
        a, b = b, a
    num = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return num / (na * nb) if na and nb else None


# ════════════════════════════════════════════════════════════════════════
# 공용
# ════════════════════════════════════════════════════════════════════════
_now = IM._now
_sha = IM._sha
_rj = IM._rj
_wj = IM._wj
_madd = IM._madd


def _ny():
    global NY
    if NY is None:
        from zoneinfo import ZoneInfo
        NY = ZoneInfo("America/New_York")
    return NY


def acc_et(s):
    """acceptanceDateTime('2014-07-23T16:31:45.000Z' · 실제 UTC) → ET 'YYYY-MM-DDTHH:MM:SS'."""
    if not s:
        return None
    d = dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
    return d.astimezone(_ny()).strftime("%Y-%m-%dT%H:%M:%S")


_HOL = {}


def is_td(d: dt.date) -> bool:
    if d.weekday() >= 5:
        return False
    if d.year not in _HOL:
        _HOL[d.year] = set(REV._holidays(d.year)) | {k for k in REV.ADHOC if k.startswith(str(d.year))}
    return d.isoformat() not in _HOL[d.year]


def avail_day(et: str, fd: str = None):
    """16:00 ET 이후 접수 · 거래일이 아닌 날 접수 → 다음 NYSE 거래일. 접수 시각이 없으면 filingDate 다음 거래일(보수)."""
    if et:
        d = dt.date.fromisoformat(et[:10])
        late = et[11:16] >= "16:00"
    else:
        d = dt.date.fromisoformat(fd)
        late = True
    if late or not is_td(d):
        d += dt.timedelta(days=1)
        while not is_td(d):
            d += dt.timedelta(days=1)
    return d.isoformat()


LATE_ACC_BDAYS = 3                # 접수가 filingDate 뒤 NYSE 거래일 3일 넘게 늦으면 재접수 · 재배포로 보고 filingDate 규칙(표지)


def _tdays_between(a: str, b: str) -> int:
    """a < t ≤ b 인 NYSE 거래일 수."""
    d, e, n = dt.date.fromisoformat(a), dt.date.fromisoformat(b), 0
    while d < e:
        d += dt.timedelta(days=1)
        n += is_td(d)
    return n


ET_AMB_WINDOW = ("16:00", "17:30")   # 원본 시각을 ET 로 읽은 창(filingDate 그날) — 두 읽기가 모두 filingDate 와 맞는다
ET_AMB_BEFORE = "2023-01-01"         # 이 날 전 filingDate 문서만(ET 로만 읽히는 기록은 2013–2022 에만 있었다 · 검토 실측)


def avail_rule(et: str, fd: str, raw: str = None):
    """가용일 규칙 v3(2026-09-25 · 09-26 적대 검토 반영) → (가용일, 방법).
    acc       접수 시각(ET) 규칙(avail_day) — 기본.
    fd_floor  접수 규칙의 날짜가 filingDate 보다 이르다(UTC/ET 표기가 어긋난 기록) → filingDate 다음 거래일(시각을 모르는 공시일
              규칙 · 보수). 가용일은 filingDate 보다 이를 수 없다. (17:30 ET 뒤 접수는 filingDate 가 다음 영업일이지만 접수 규칙의
              날짜도 그날이라 여기 걸리지 않는다.) 🔒 선언: ET 읽기보다 거래일 하루(드물게 이틀) 늦다 — 보수 · 그대로 둔다.
    fd_late   접수 날짜가 filingDate 뒤 NYSE 거래일 LATE_ACC_BDAYS 일을 넘는다(재접수 시각 · BKNG · CRM · CRL) → filingDate 다음
              거래일 · 표지(avail_how).
    fd_etamb  (v3) filingDate < ET_AMB_BEFORE · 원본 시각(raw)을 ET 로 읽으면 filingDate 그날 16:00–17:30 — UTC 로 읽은 가용일
              (그날 11:00–13:30 ET → 그날)이 filingDate 다음 거래일보다 이르면 filingDate 다음 거래일(숨은 ET 표기를 가려낼 수 없다 ·
              보수 · 진짜 UTC 문서도 하루 늦어진다 — 선언).
    fd_noacc  접수 시각이 없다 → filingDate 다음 거래일."""
    fdr = avail_day(None, fd)
    if not et:
        return fdr, "fd_noacc"
    a = avail_day(et, fd)
    if fd and a < fd:
        return fdr, "fd_floor"
    if fd and et[:10] > fd and _tdays_between(fd, et[:10]) > LATE_ACC_BDAYS:
        return fdr, "fd_late"
    if (raw and fd and fd < ET_AMB_BEFORE and raw[:10] == fd and ET_AMB_WINDOW[0] <= raw[11:16] <= ET_AMB_WINDOW[1]
            and a < fdr):
        return fdr, "fd_etamb"
    return a, "acc"


def avail_et_reading(raw: str, fd: str):
    """진단 — 원본 acceptanceDateTime 의 시각을 ET 로 읽었을 때의 가용일(avail_day · 보고 전용 · 규칙에 쓰지 않는다)."""
    if not raw:
        return None
    return avail_day(raw[:10] + "T" + raw[11:19], fd)


def doc_path(fd, acc):
    return os.path.join(DOC_DIR, fd[:4], acc + ".htm.gz")


def feat_path(fd, acc):
    return os.path.join(FEAT_DIR, fd[:4], acc + ".json.gz")


def man_open():
    m = IM.Manifest(MAN, "build/tenq_rf_build.py 가 받은 10-Q 주 문서 고정표. 키 = accession. sha256 은 gzip 전송을 푼 내용 "
                         "바이트에 건다. 원본은 저장소 밖 RBATCH_RAW/tenq/doc/<연>/<accession>.htm.gz(gzip 저장).", "files")
    m.doc["url_rule"] = "https://www.sec.gov/Archives/edgar/data/<cik>/<accession 하이픈 뺌>/<doc>"
    return m


def _arg(argv, k, default=None, cast=str):
    if k in argv:
        i = argv.index(k)
        if i + 1 < len(argv):
            return cast(argv[i + 1])
    return default


# ════════════════════════════════════════════════════════════════════════
# check — UA 가 차단 페이지가 아닌 진짜 200 을 받는지 + 전송량 표본
# ════════════════════════════════════════════════════════════════════════
def _raw_get(url):
    """접속 점검 1건 — edgar.probe(받은 그대로 · 같은 UA · 같은 초당 상한). SEC 에 가는 urlopen 은 edgar.py 에만 둔다."""
    t0 = time.time()
    st, hd, raw = edgar.probe(url, timeout=60)
    ce = hd.get("Content-Encoding")
    body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    return st, ce, raw, body, time.time() - t0


def cmd_check(argv):
    res = []
    for url in CHECK_URLS:
        st, ce, raw, body, sec = _raw_get(url)
        blocked = b"Undeclared Automated Tool" in body
        try:
            json.loads(body.decode("utf-8"))
            ok_json = True
        except Exception:
            ok_json = False
        res.append({"url": url, "status": st, "content_encoding": ce, "wire_bytes": len(raw), "body_bytes": len(body),
                    "blocked_page": blocked, "json": ok_json, "sha256": _sha(body), "at": _now()})
        print("  %s → HTTP %s · %s · 전송 %dB / 본문 %dB · 차단페이지 %s · JSON %s"
              % (url, st, ce, len(raw), len(body), blocked, ok_json))
    good = all(r["status"] == 200 and r["content_encoding"] == "gzip" and not r["blocked_page"] and r["json"] for r in res)
    # 주 문서 전송량 표본(시드 고정 · 목록이 있을 때만) — 전체 전송량 추정에 쓴다
    wire = []
    L = _rj(LIST)
    k = _arg(argv, "--wire", 0, int)
    if L and k:
        rng = random.Random(SEED)
        for r in rng.sample(L["docs"], k):
            st, ce, raw, body, sec = _raw_get(edgar.doc_url(r["cik"], r["acc"], r["doc"]))
            wire.append({"acc": r["acc"], "status": st, "ce": ce, "wire": len(raw), "body": len(body), "sec": round(sec, 3)})
        print("  주 문서 표본 %d건: 전송 %.0f KB · 본문 %.0f KB(평균) · 압축비 %.1f"
              % (len(wire), sum(w["wire"] for w in wire) / len(wire) / 1e3, sum(w["body"] for w in wire) / len(wire) / 1e3,
                 sum(w["body"] for w in wire) / max(1, sum(w["wire"] for w in wire))))
    _wj(os.path.join(RAW_T, "_access_check.json"), {"ok": good, "checks": res, "wire_sample": wire})
    if not good:
        raise SystemExit("🚨 접속 점검 실패 — UA 를 확인할 것(차단 페이지 · 비 gzip · 비 200)")
    print("✓ 접속 점검 통과(HTTP 200 · gzip · JSON)")


# ════════════════════════════════════════════════════════════════════════
# list — 대상 10-Q(세계 비금융 그룹 · 효력 구간 · 창)
# ════════════════════════════════════════════════════════════════════════
def world():
    """{그룹: {달: [티커…]}}(비금융 멤버-월) · {(그룹, 달): fpi} · load_map."""
    R = IM.load_refs()
    M = IM.load_map()
    gm = collections.defaultdict(lambda: collections.defaultdict(list))
    fpi = {}
    for (t, ym), v in M["idx"].items():
        g = v["gid"]
        if not g or IM.sector_at(R, t, ym) == FIN:
            continue
        gm[g][ym].append(t)
        fpi[(g, ym)] = v["fpi"] if fpi.get((g, ym)) is None else fpi[(g, ym)]
    return gm, fpi, M, R


def _sub_rows(cik):
    p = os.path.join(RAW, "sub", "CIK%010d.json.gz" % cik)
    if not os.path.exists(p):
        return None
    j = _rj(p)
    recs = [j["filings"]["recent"]]
    miss = []
    for f in j["filings"].get("files") or []:
        pp = os.path.join(RAW, "sub", f["name"] + ".gz")
        if os.path.exists(pp):
            recs.append(_rj(pp))
        elif (f.get("filingTo") or "9999") >= WIN0:
            miss.append(f["name"])
    out = []
    for d in recs:
        ks = [k for k in ("accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "primaryDocument",
                          "size", "isInlineXBRL", "isXBRL") if k in d]
        n = min(len(d[k]) for k in ks)
        for i in range(n):
            out.append({k: d[k][i] for k in ks})
    return out, miss


def cmd_list(argv):
    gm, fpi, M, R = world()
    groups = M["groups"]
    docs, miss, forms = [], [], collections.Counter()
    seen = set()
    for g in sorted(gm):
        ms = sorted(gm[g])
        lo, hi = max(_madd(ms[0], -LEAD), WIN0), ms[-1]
        for c, f, to, src, nm in groups[g]["ciks"]:
            got = _sub_rows(c)
            if got is None:
                miss.append([g, c, "no_submissions"])
                continue
            rows, pm = got
            for p in pm:
                miss.append([g, c, "page_missing:" + p])
            for r in rows:
                fm = r.get("form") or ""
                ym = (r.get("filingDate") or "")[:7]
                if not (lo <= ym <= hi) or (f and ym < f) or (to and ym > to):
                    continue
                if fm.startswith("10-Q") or fm.startswith("NT 10-Q"):
                    forms[fm] += 1
                if fm != "10-Q":
                    continue
                key = (g, r["accessionNumber"])
                if key in seen:
                    continue
                seen.add(key)
                docs.append({"acc": r["accessionNumber"], "cik": c, "grp": g, "fd": r["filingDate"],
                             "rd": r.get("reportDate") or "", "acceptanceDateTime": r.get("acceptanceDateTime") or "",
                             "doc": r.get("primaryDocument") or "", "size": r.get("size"),
                             "isInlineXBRL": int(r.get("isInlineXBRL") or 0)})
    # 한 accession 이 두 그룹에 걸리면(공동 제출) 그대로 둔다 — 받기는 한 번
    docs.sort(key=lambda r: (r["fd"], r["acc"], r["grp"]))
    by_y = collections.Counter(r["fd"][:4] for r in docs)
    _wj(LIST, {"generated": _now(), "window": [WIN0, "lead %d" % LEAD], "n": len(docs),
               "n_acc": len({r["acc"] for r in docs}), "by_year": dict(sorted(by_y.items())), "forms_seen": dict(forms),
               "missing": miss, "docs": docs})
    print("10-Q 원본 %d건(accession %d) · 그룹 %d · 누락 %d" % (len(docs), len({r['acc'] for r in docs}),
                                                        len({r['grp'] for r in docs}), len(miss)))
    print("  연도별", dict(sorted(by_y.items())))
    print("  같은 창의 10-Q 계열 서식", dict(forms))


# ════════════════════════════════════════════════════════════════════════
# fetch — 주 문서(스레드 여러 개 · 잠금으로 초당 8회 유지)
# ════════════════════════════════════════════════════════════════════════
_TLOCK = threading.Lock()
_ORIG_THROTTLE = edgar._throttle
_GAP = [0.0]                      # --rate 로 더 낮춘 간격(초) · edgar 의 1/8초 위에 얹는다(더 느리게만 할 수 있다)
_LAST = [0.0]


def _locked_throttle():
    with _TLOCK:
        _ORIG_THROTTLE()
        g = time.time() - _LAST[0]
        if g < _GAP[0]:
            time.sleep(_GAP[0] - g)
        _LAST[0] = time.time()


def _fetch_one(r):
    p = doc_path(r["fd"], r["acc"])
    url = edgar.doc_url(r["cik"], r["acc"], r["doc"])
    t0 = time.time()
    try:
        b = edgar.fetch_bytes(url, timeout=120)
    except urllib.error.HTTPError as e:
        return r, None, {"status": e.code, "sec": time.time() - t0}
    if b"Undeclared Automated Tool" in b[:20000]:
        return r, None, {"status": "blocked", "sec": time.time() - t0}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    gz = gzip.compress(b, 6)
    with open(p + ".tmp", "wb") as f:
        f.write(gz)
    os.replace(p + ".tmp", p)
    return r, b, {"status": 200, "sec": time.time() - t0, "gz": len(gz)}


def cmd_fetch(argv):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    L = _rj(LIST)
    if not L:
        raise SystemExit("목록이 없다 — list 먼저")
    workers = _arg(argv, "--workers", 3, int)
    rate = _arg(argv, "--rate", edgar.RATE, float)
    if rate > edgar.RATE:
        raise SystemExit("--rate 는 edgar.RATE(%.0f) 이하만" % edgar.RATE)
    _GAP[0] = 1.0 / rate
    # 🚨 SEC 는 IP 단위로 센다 — 같은 IP 의 다른 SEC 잡(§A · §G 등)과 합쳐 초당 10회에 가까우면 약 10분 막는다. 2026-09-25 에
    #   7.7 건/초로 9,800건쯤 받았을 때 429 가 났다(다른 SEC 잡이 같은 시각에 돌고 있었다 · 원인은 특정하지 못했다).
    #   다른 잡이 돌 때는 --rate 를 낮춘다(나머지는 --rate 4 로 받았다).
    limit = _arg(argv, "--limit", None, int)
    k = _arg(argv, "--sample", None, int)
    man = man_open()
    todo, have, bad = [], 0, 0
    uniq = {}
    for r in L["docs"]:
        uniq.setdefault(r["acc"], r)
    items = list(uniq.values())
    if k:
        items = random.Random(SEED + 1).sample(items, k)
    for r in items:
        m = man.get(r["acc"])
        p = doc_path(r["fd"], r["acc"])
        if m and m.get("status") == 404:
            continue
        if os.path.exists(p) and m and m.get("sha256"):
            have += 1
            continue
        if os.path.exists(p) and not m:          # 받았는데 고정표에 없다(중단) — 해시를 지금 고정
            b = gzip.open(p, "rb").read()
            man.put(r["acc"], {"cik": r["cik"], "doc": r["doc"], "sha256": _sha(b), "bytes": len(b), "fetched": None})
            have += 1
            continue
        todo.append(r)
    if limit:
        todo = todo[:limit]
    print("받을 것 %d · 이미 있음 %d · 스레드 %d · 상한 %.1f 건/초" % (len(todo), have, workers, rate), flush=True)
    edgar._throttle = _locked_throttle
    t0 = time.time()
    done = nbytes = ngz = 0
    stat = collections.Counter()
    log = open(os.path.join(RAW_T, "_fetch.log"), "a", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_fetch_one, r) for r in todo]
            for fu in as_completed(futs):
                r, b, meta = fu.result()
                stat[meta["status"]] += 1
                if meta["status"] == "blocked":
                    man.save()
                    raise SystemExit("🚨 차단 페이지(Undeclared Automated Tool) — %s · 멈춘다" % r["acc"])
                if b is None:
                    man.put(r["acc"], {"cik": r["cik"], "doc": r["doc"], "sha256": None, "bytes": 0, "fetched": _now(),
                                       "status": meta["status"]}, allow_update=True)
                    log.write("%s %s %s\n" % (_now(), r["acc"], meta["status"]))
                else:
                    man.put(r["acc"], {"cik": r["cik"], "doc": r["doc"], "sha256": _sha(b), "bytes": len(b), "fetched": _now()})
                    nbytes += len(b)
                    ngz += meta["gz"]
                done += 1
                if done % 250 == 0 or done == len(todo):
                    man.save()
                    el = time.time() - t0
                    print("  %d/%d · %.1f 건/초 · 본문 %.2f GB · 저장 %.2f GB · %.0f초 · 남은 약 %.0f분 · %s"
                          % (done, len(todo), done / el, nbytes / 1e9, ngz / 1e9, el, (len(todo) - done) / (done / el) / 60,
                             dict(stat)), flush=True)
    finally:
        edgar._throttle = _ORIG_THROTTLE
        man.save()
        log.close()
    el = time.time() - t0
    rec = {"at": _now(), "n": done, "sec": round(el, 1), "body_bytes": nbytes, "gz_bytes": ngz, "status": dict(stat),
           "workers": workers, "rate_cap": rate}
    hist = _rj(os.path.join(RAW_T, "_fetch_runs.json")) or []
    hist.append(rec)
    _wj(os.path.join(RAW_T, "_fetch_runs.json"), hist)
    print("받기 끝 — %d건 · %.0f초 · %s" % (done, el, dict(stat)))


# ════════════════════════════════════════════════════════════════════════
# parse — 문서별 특징(여러 프로세스)
# ════════════════════════════════════════════════════════════════════════
def _parse_one(args):
    r, sha = args
    p = doc_path(r["fd"], r["acc"])
    fp = feat_path(r["fd"], r["acc"])
    t0 = time.time()
    try:
        b = gzip.open(p, "rb").read()
        if sha and _sha(b) != sha:
            return {"acc": r["acc"], "parse_status": "error", "err": "sha_mismatch"}
        f, lines = features(b)
    except Exception as e:  # 파서 사고는 문서 단위로 센다
        return {"acc": r["acc"], "parse_status": "error", "err": "%s: %s" % (type(e).__name__, str(e)[:120])}
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    rec = {k: f[k] for k in ("tf_rf", "tf_doc", "sec_text")}
    with gzip.open(fp + ".tmp", "wt", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(fp + ".tmp", fp)
    out = {k: v for k, v in f.items() if k not in ("tf_rf", "tf_doc", "sec_text")}
    out["acc"] = r["acc"]
    out["sha"] = sha
    out["sec_sha"] = _sha(f["sec_text"].encode("utf-8"))[:16]
    out["sec"] = f["sec"]
    out["t"] = round(time.time() - t0, 3)
    return out


def cmd_parse(argv):
    import multiprocessing as mp
    L = _rj(LIST)
    man = man_open()
    procs = _arg(argv, "--procs", 4, int)
    only = _arg(argv, "--only", None)
    uniq = {}
    for r in L["docs"]:
        uniq.setdefault(r["acc"], r)
    _require_pin()
    ph = parser_hash()
    prev = _rj(PARSED) or {}
    keep = {}
    if prev.get("parser_hash") == ph and "--full" not in argv:   # 같은 파서면 이어서(문서 해시 · 특징 파일이 그대로인 것만)
        for acc, o in (prev.get("docs") or {}).items():
            r = uniq.get(acc)
            m = man.get(acc) or {}
            if r and o.get("parse_status") != "error" and o.get("sha") == m.get("sha256") and os.path.exists(feat_path(r["fd"], acc)):
                keep[acc] = o
    jobs = []
    for acc, r in uniq.items():
        m = man.get(acc)
        if not m or not m.get("sha256") or not os.path.exists(doc_path(r["fd"], acc)) or acc in keep:
            continue
        if only and acc not in only.split(","):
            continue
        jobs.append((r, m["sha256"]))
    print("파싱 %d건(이어받음 %d) · 프로세스 %d · 파서 %s" % (len(jobs), len(keep), procs, ph[:12]), flush=True)
    t0 = time.time()
    res = dict(keep)
    with mp.Pool(procs) as pool:
        for i, o in enumerate(pool.imap_unordered(_parse_one, jobs, chunksize=4)):
            res[o["acc"]] = o
            if (i + 1) % 1000 == 0:
                print("  %d/%d · %.0f초" % (i + 1, len(jobs), time.time() - t0), flush=True)
    st = collections.Counter(o["parse_status"] for o in res.values())
    sh = collections.Counter(o.get("shape") for o in res.values())
    _wj(PARSED, {"generated": _now(), "parser_hash": parser_hash(), "sec": round(time.time() - t0, 1), "status": dict(st),
                 "docs": res})
    print("파싱 끝 %.0f초 · %s · 형태 %s" % (time.time() - t0, dict(st), dict(sh)))


def cmd_repin(argv):
    """2026-09-26 re-pin(동작 불변 · PARSER_REPIN) — 캐시 _parsed.json 이 옛 고정(PARSER_REPIN.from)의 파서로 만든 것이면
    ① 옛 정의(extra=False)로 잰 지금 코드의 해시가 옛 고정과 같은지(함수 · 식 불변 — _require_pin 이 본다) ② 시드 고정 무작위 표본
    (PARSER_REPIN.sample 건)을 지금 파서로 다시 파싱해 캐시의 문서 결과 · 특징 파일(tf_rf · tf_doc · 절 본문 해시)과 칸마다 같은지 본 뒤
    ③ 해시 표지만 새 고정으로 바꾸고 re-pin 기록을 _parsed.json 에 싣는다. 하나라도 다르면 멈춘다(그때는 parse --full).
    다시 돌리면 같은 표본 · 같은 판정이다(이미 새 해시면 아무것도 하지 않는다)."""
    _require_pin()
    P = _rj(PARSED)
    if not P:
        raise SystemExit("_parsed.json 이 없다 — parse 먼저")
    if P.get("parser_hash") == PARSER_HASH:
        print("이미 새 고정(%s) — re-pin 할 것 없음 · 기록 %s" % (PARSER_HASH[:12], (P.get("repin") or {}).get("checked")))
        return
    if P.get("parser_hash") != PARSER_REPIN["from"]:
        raise SystemExit("🚨 _parsed.json 의 해시(%s)가 re-pin 출발(%s)이 아니다 — parse --full" % (
            (P.get("parser_hash") or "")[:12], PARSER_REPIN["from"][:12]))
    L = _rj(LIST)
    uniq = {}
    for r in L["docs"]:
        uniq.setdefault(r["acc"], r)
    docs = sorted(a for a, o in P["docs"].items() if o.get("parse_status") != "error" and a in uniq)
    rng = random.Random(PARSER_REPIN["seed"])
    samp = sorted(rng.sample(docs, min(PARSER_REPIN["sample"], len(docs))))
    diff, t0 = [], time.time()
    for acc in samp:
        r = uniq[acc]
        o = P["docs"][acc]
        f, _ = features(gzip.open(doc_path(r["fd"], acc), "rb").read())
        new = {k: v for k, v in f.items() if k not in ("tf_rf", "tf_doc", "sec_text")}
        new["sec_sha"] = _sha(f["sec_text"].encode("utf-8"))[:16]
        bad = [k for k in sorted(set(new) | (set(o) - {"acc", "sha", "t"})) if json.dumps(new.get(k), sort_keys=True)
               != json.dumps(o.get(k), sort_keys=True)]
        ft = _load_feat(r["fd"], acc) or {}
        for k in ("tf_rf", "tf_doc", "sec_text"):
            if json.dumps(ft.get(k), sort_keys=True) != json.dumps(f[k], sort_keys=True):
                bad.append("feat:" + k)
        if bad:
            diff.append([acc, bad[:6]])
    if diff:
        raise SystemExit("🚨 re-pin 표본 %d건 중 %d건이 캐시와 다르다 — 동작이 바뀌었다 · parse --full 로 다시 파싱할 것: %s"
                         % (len(samp), len(diff), diff[:5]))
    P["repin"] = {"from": PARSER_REPIN["from"], "to": PARSER_HASH, "date": PARSER_REPIN["date"], "note": PARSER_REPIN["note"],
                  "legacy_hash_of_current_code": PARSER_HASH_LEGACY, "lxml": LXML_VERSIONS,
                  "checked": len(samp), "identical": len(samp), "seed": PARSER_REPIN["seed"], "sec": round(time.time() - t0, 1)}
    P["parser_hash"] = PARSER_HASH
    _wj(PARSED, P)
    print("re-pin %s → %s · 표본 %d건 모두 같다(%.0f초)" % (PARSER_REPIN["from"][:12], PARSER_HASH[:12], len(samp), time.time() - t0))


# ════════════════════════════════════════════════════════════════════════
# build — 짝 · SimRF · SimDoc · 점검 → data/_tenq_rf.json
# ════════════════════════════════════════════════════════════════════════
def _load_feat(fd, acc):
    p = feat_path(fd, acc)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def pair_docs(L, P):
    """그룹별 짝 짓기(사양 R2 (3) + 랩 선택) → (문서 행 목록, 버린 행 목록)."""
    by_g = collections.defaultdict(list)
    for r in L["docs"]:
        x = dict(r)
        x["accepted_et"] = acc_et(r["acceptanceDateTime"])
        x["avail"], x["avail_how"] = avail_rule(x["accepted_et"], r["fd"], r["acceptanceDateTime"])
        x["avail_acc_only"] = avail_day(x["accepted_et"], r["fd"])      # 옛 규칙(접수 시각만 · bfae3758 판) — 바뀐 수를 센다
        by_g[r["grp"]].append(x)
    rows, dropped = [], []
    for g, xs in by_g.items():
        xs.sort(key=lambda x: (x["rd"] or x["fd"], x["avail"], x["acc"]))
        keep = []
        for x in xs:
            if not x["rd"]:
                x["_no_rd"] = True
            if keep and x["rd"] and keep[-1]["rd"] == x["rd"]:
                prev = keep[-1]
                first = min(prev, x, key=lambda z: (z["avail"], z["accepted_et"] or "", z["acc"]))
                other = x if first is prev else prev
                keep[-1] = first
                dropped.append({"acc": other["acc"], "grp": g, "rd": other["rd"], "why": "dup_period", "kept": first["acc"]})
                continue
            keep.append(x)
        for i, x in enumerate(keep):
            x["_prev"] = keep[i - 1] if i > 0 else None
            rows.append(x)
    return rows, dropped


# 패널 열(저장 순서) — 원본 해시 · 크기 · 주 문서 이름은 data/_tenq_rf/manifest.json 에 있다(여기 싣지 않는다)
COLS = ("acc", "cik", "grp", "tickers", "form", "fd", "rd", "acceptanceDateTime", "accepted_et", "avail", "avail_how", "pub_m",
        "in_world", "isInlineXBRL", "parse_status", "shape", "parse_status_v2", "shape_v2", "boiler_v2", "parse_status_v3",
        "shape_v3", "boiler_v3", "n_words_rf", "n_fls_v3", "n_words_doc", "sec_how", "sec_end", "sec_sha", "prev_acc", "prev_shape",
        "prev_shape_v2", "prev_shape_v3", "prev_n_words_rf", "gap_days", "ixbrl_switch", "pair_status", "pair_status_v2",
        "pair_status_v3", "SimRF", "SimRF_v2", "SimRF_v3", "SimRF_sw", "SimRF_sw_v2", "SimRF_sw_v3", "SimDoc", "dlog_len_rf")
VERS = (("", "parse_status", "shape"), ("_v2", "parse_status_v2", "shape_v2"), ("_v3", "parse_status_v3", "shape_v3"))


def panel_rows(O):
    """data/_tenq_rf.json → 행 사전 목록(열 묶음을 편다)."""
    d = O["docs"]
    if isinstance(d, dict) and "cols" in d:
        return [dict(zip(d["cols"], r)) for r in d["rows"]]
    return d


def cmd_build(argv):
    L = _rj(LIST)
    P = _rj(PARSED)
    man = man_open()
    if not L or not P:
        raise SystemExit("목록 · 파싱 결과가 없다 — list · fetch · parse 먼저")
    _require_pin()
    ph = parser_hash()
    if P.get("parser_hash") != ph:
        raise SystemExit("🚨 _parsed.json 의 파서 해시(%s)가 지금 파서(%s)와 다르다 — parse 를 다시 돌릴 것"
                         % (P.get("parser_hash", "")[:12], ph[:12]))
    PD = P["docs"]
    gm, fpi, M, R = world()
    rows, dropped = pair_docs(L, P)
    feat_cache = {}

    cur_g = [None]

    def F(x):
        k = x["acc"]
        if k not in feat_cache:
            feat_cache[k] = _load_feat(x["fd"], k)
        return feat_cache[k]

    out, pst = [], collections.Counter()
    for x in sorted(rows, key=lambda z: (z["grp"], z["rd"] or z["fd"])):
        if x["grp"] != cur_g[0]:                  # 짝은 같은 그룹 안에서만 — 그룹이 바뀌면 특징 캐시를 비운다(메모리 · 결과 같음)
            feat_cache.clear()
            cur_g[0] = x["grp"]
        m = man.get(x["acc"]) or {}
        pd = PD.get(x["acc"])
        if not m.get("sha256"):
            st = "fetch_%s" % m.get("status", "missing")
        elif pd is None:
            st = "unparsed"
        else:
            st = pd["parse_status"]
        pm = x["avail"][:7]
        st2 = pd.get("parse_status_v2", st) if pd else st
        st3 = pd.get("parse_status_v3", st) if pd else st
        rec = {"acc": x["acc"], "cik": x["cik"], "grp": x["grp"], "form": "10-Q", "fd": x["fd"], "rd": x["rd"],
               "acceptanceDateTime": x["acceptanceDateTime"], "accepted_et": x["accepted_et"], "avail": x["avail"],
               "avail_how": x["avail_how"], "avail_acc_only": x["avail_acc_only"], "pub_m": pm, "isInlineXBRL": x["isInlineXBRL"], "doc": x["doc"], "sha256": m.get("sha256"),
               "bytes": m.get("bytes"), "parse_status": st, "shape": pd.get("shape") if pd else None,
               "n_words_rf": pd.get("n_words_rf") if pd else None, "n_words_doc": pd.get("n_words_doc") if pd else None,
               "boiler_hit": pd.get("boiler_hit") if pd else None,
               "parse_status_v2": st2, "shape_v2": pd.get("shape_v2") if pd else None,
               "boiler_v2": pd.get("boiler_v2") if pd else None,
               "parse_status_v3": st3, "shape_v3": pd.get("shape_v3") if pd else None,
               "boiler_v3": pd.get("boiler_v3") if pd else None, "n_fls_v3": pd.get("n_fls_v3") if pd else None,
               "sec_how": ((pd or {}).get("sec") or {}).get("how"), "sec_end": ((pd or {}).get("sec") or {}).get("end_how"),
               "sec_sha": pd.get("sec_sha") if pd else None,
               "in_world": pm in gm.get(x["grp"], {}), "tickers": sorted(set(gm.get(x["grp"], {}).get(pm, []))),
               "fpi": fpi.get((x["grp"], pm)),
               "prev_acc": None, "prev_rd": None, "prev_shape": None, "prev_shape_v2": None, "prev_shape_v3": None,
               "prev_n_words_rf": None, "gap_days": None,
               "pair_status": None, "pair_status_v2": None, "pair_status_v3": None, "SimRF": None, "SimRF_sw": None,
               "SimRF_v2": None, "SimRF_sw_v2": None, "SimRF_v3": None, "SimRF_sw_v3": None, "SimDoc": None, "dlog_len_rf": None,
               "ixbrl_switch": None}
        pv = x["_prev"]
        if pv is None:
            ps = ps2 = ps3 = "no_prior"
        else:
            rec["prev_acc"], rec["prev_rd"] = pv["acc"], pv["rd"]
            ppd = PD.get(pv["acc"])
            rec["prev_shape"] = ppd.get("shape") if ppd else None
            rec["prev_shape_v2"] = ppd.get("shape_v2") if ppd else None
            rec["prev_shape_v3"] = ppd.get("shape_v3") if ppd else None
            rec["prev_n_words_rf"] = ppd.get("n_words_rf") if ppd else None
            rec["ixbrl_switch"] = int(pv["isInlineXBRL"] != x["isInlineXBRL"])
            gap = (dt.date.fromisoformat(x["rd"]) - dt.date.fromisoformat(pv["rd"])).days if x["rd"] and pv["rd"] else None
            rec["gap_days"] = gap
            if gap is None:
                ps = ps2 = ps3 = "no_rd"
            elif not (70 <= gap <= 200):
                ps = ps2 = ps3 = "gap_out"
            elif pv["avail"] > x["avail"]:
                ps = ps2 = ps3 = "prior_late"
            else:
                fa, fb = F(x), F(pv)
                s = None
                if fa and fb and pd and ppd:
                    rec["SimDoc"] = cosine(fa["tf_doc"], fb["tf_doc"])
                    if pd["n_words_rf"] and ppd["n_words_rf"]:
                        s = cosine(fa["tf_rf"], fb["tf_rf"])
                        rec["dlog_len_rf"] = math.log(pd["n_words_rf"]) - math.log(ppd["n_words_rf"])
                res = {}
                for sfx, k_st, k_sh in VERS:
                    cst = {"": st, "_v2": st2, "_v3": st3}[sfx]
                    if cst != "ok":
                        res[sfx] = "cur_fail"
                    elif not ppd or ppd.get(k_st, ppd["parse_status"]) != "ok":
                        res[sfx] = "prior_fail"
                    else:
                        a, b = pd[k_sh], ppd[k_sh]
                        if (a == "F") != (b == "F"):
                            res[sfx] = "shape_switch"
                            rec["SimRF_sw" + sfx] = s
                        else:
                            res[sfx] = "ok"
                            rec["SimRF" + sfx] = s
                ps, ps2, ps3 = res[""], res["_v2"], res["_v3"]
        rec["pair_status"], rec["pair_status_v2"], rec["pair_status_v3"] = ps, ps2, ps3
        pst[ps] += 1
        for k in ("SimRF", "SimRF_sw", "SimRF_v2", "SimRF_sw_v2", "SimRF_v3", "SimRF_sw_v3", "SimDoc", "dlog_len_rf"):
            if rec[k] is not None:
                rec[k] = round(rec[k], 6)
        rec["isInlineXBRL"] = int(rec["isInlineXBRL"])
        out.append(rec)
    print("문서 %d · 버림 %d · 짝 상태(카드) %s · v2 %s · v3 %s" % (len(out), len(dropped), dict(pst),
                                                           dict(collections.Counter(r["pair_status_v2"] for r in out)),
                                                           dict(collections.Counter(r["pair_status_v3"] for r in out))))
    cov = coverage(out, gm, R)
    af = avail_fix(out)
    V = _rj(VALID) or {}
    V["avail_fix"] = af
    _wj(VALID, V, indent=1)
    ixc = ix_checks(out)
    doc = {"note": "§C 10-Q 위험요인(Part II Item 1A) 텍스트 패널 — 문서마다 절 형태(B/U/F) · 단어수 · 바로 앞 10-Q 와의 "
                   "SimRF(단어빈도 코사인) · SimDoc · 가용 시각. 규칙은 build/tenq_rf_build.py 머리말. 자료 빌드다 — 표지와 "
                   "수익의 관계는 계산하지 않았다(분위 · CH_active 는 r_r2flags · 등록 뒤).",
           "generated": _now(), "parser_hash": ph,
           "fields": {"acc": "accession", "grp": "발행사 그룹(_issuer_map)", "rd": "reportDate", "accepted_et":
                      "acceptanceDateTime(UTC) → ET", "avail": "가용일(avail_rule — 16:00 ET 뒤 · 휴장일 → 다음 NYSE 거래일 · "
                      "filingDate 보다 이르지 않다 · 접수가 filingDate 뒤 거래일 3일 넘게 늦으면 filingDate 다음 거래일)",
                      "avail_how": "acc(접수 시각 규칙) · fd_floor(접수 규칙 날짜 < filingDate → filingDate 다음 거래일 · ET 읽기보다 "
                      "하루 늦다 — 선언) · fd_late(접수가 filingDate 뒤 거래일 3일 넘게 늦음 → filingDate 다음 거래일 · 표지) · "
                      "fd_etamb(2023 전 · 원본 시각을 ET 로 읽으면 filingDate 16:00–17:30 → filingDate 다음 거래일 · v3) · "
                      "fd_noacc(접수 시각 없음)",
                      "pub_m": "가용일의 달", "shape": "B/U/F(사양 params) · 실패면 null", "parse_status":
                      "ok · split_fail(상용구 없음 & < 500단어) · no_1a(머리 없음) · error · fetch_<코드>",
                      "n_words_rf": "절 토큰 수", "pair_status": "ok · no_prior · gap_out · prior_late · no_rd · cur_fail · "
                      "prior_fail · shape_switch", "SimRF": "짝 ok 일 때만(형태 전환은 null · 값은 SimRF_sw)",
                      "SimDoc": "같은 짝의 문서 전체 코사인(형태 규칙 없음)", "in_world": "pub_m 에 그룹이 비금융 멤버",
                      "tickers": "pub_m 에 그 그룹으로 멤버인 티커(세계 밖이면 빈 목록)",
                      "sec_how": "item1a · item1a_bare · item_other · plain · xref(교차참조 색인 10-Q 의 본문 절) · item1a_pfx(머리 앞 "
                      "쓰레기 글자)", "sec_end": "item(다음 항목 머리 · plain/xref 는 대문자 항목 제목 줄 포함) · eof",
                      "*_v3": "형태 v3(랩 수정안 · 참조문 대상 넓힘 · FLS 문단은 B/U 문턱에서 뺌 · 전문 재기재 선언 upd → F · 수동형 "
                      "갱신 선언 · 경계 · 토큰 · SimRF 값은 같고 유효 여부만 다르다)",
                      "boiler_v3": "v3 적중 종류 card · nochg · upd · upd_restate(→ F) · ref",
                      "n_fls_v3": "절 가운데 FLS · 안전항 문단 토큰 수(v3 B/U 문턱에서 뺀다)",
                      "prev_n_words_rf": "짝 앞 문서의 절 토큰 수",
                      "*_v2": "형태 v2(랩 수정안 · 상용구 적중만 넓힘 · 경계 · 토큰 · SimRF 값은 카드 판과 같고 유효 여부만 다르다)",
                      "boiler_v2": "v2 적중 종류 card · nochg · upd · ref", "dlog_len_rf": "log(n_rf) − log(n_rf_prev)(두 절이 "
                      "있으면 · 판과 무관)", "ixbrl_switch": "짝 사이 isInlineXBRL 이 다르면 1",
                      "sec_sha": "절 본문(숫자 표 줄 제외) sha256 앞 16자", "manifest": "원본 sha256 · 크기 · 주 문서 이름 · 받은 "
                      "시각은 data/_tenq_rf/manifest.json(키 = acc)", "docs": "열 묶음 {cols, rows}"},
           "access_check": (_rj(os.path.join(RAW_T, "_access_check.json")) or {}).get("checks"),
           "inputs": {"issuer_map": IM._sha_file(IM.OUT), "list": _sha(json.dumps(L["docs"], sort_keys=True).encode()),
                      "manifest": IM._sha_file(MAN), "script": IM._sha_file(os.path.abspath(__file__)),
                      "issuer_map_py": IM._sha_file(os.path.abspath(IM.__file__)),
                      "issuer_map_sector_manual": (IM._sha_file(os.path.join(DATA, "_issuer_map_sector_manual.json"))
                                                   if os.path.exists(os.path.join(DATA, "_issuer_map_sector_manual.json")) else None)},
           "fetch_runs": _rj(os.path.join(RAW_T, "_fetch_runs.json")), "list_missing": L.get("missing"),
           "coverage": cov, "avail_fix": {k: v for k, v in af.items() if k != "changed"}, "ix_checks": ixc,
           "validation": V.get("summary"), "xdoc": V.get("xdoc"), "dropped": dropped,
           "docs": {"cols": list(COLS), "rows": [[r[c] for c in COLS] for r in out]}}
    IM._wj_stable(OUT, doc)                        # 내용이 같으면 generated 를 그대로(두 번 빌드 sha256 같음 · 2026-09-26)
    print("→ %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
    print("가용일 규칙 v2:", json.dumps({k: v for k, v in af.items() if k != "changed"}, ensure_ascii=False))
    for v in ("v1_card", "v2", "v3"):
        print(v, json.dumps({k: cov[v][k] for k in ("status", "shape", "pairs_ok_by_year")}, ensure_ascii=False))
        print("   실패율(연)", {y: (c["split_fail_rate"], c["no_1a_rate"], c["invalid_rate"]) for y, c in cov[v]["fail_by_year"].items()})


def avail_fix(out):
    """가용일 규칙 v2(avail_rule) 가 옛 규칙(접수 시각만 · avail_acc_only)과 다른 문서 수 · pub_m 이 바뀐 수 · 목록."""
    ch = [r for r in out if r["avail"] != r["avail_acc_only"]]
    pm = [r for r in ch if r["avail"][:7] != r["avail_acc_only"][:7]]
    lag = collections.Counter()
    for r in out:
        if r["avail_how"] == "fd_floor":
            e = avail_et_reading(r["acceptanceDateTime"], r["fd"])
            lag["none" if e is None else (_tdays_between(e, r["avail"]) if e < r["avail"] else -_tdays_between(r["avail"], e))] += 1
    amb = [r for r in out if r["avail_how"] == "fd_etamb"]
    return {"note": "가용일 규칙 v3 — 가용일은 filingDate 보다 이를 수 없다(접수 규칙 날짜가 더 이르면 filingDate 다음 거래일) · 접수가 "
                    "filingDate 뒤 NYSE 거래일 %d일 넘게 늦으면 filingDate 다음 거래일로 두고 avail_how = fd_late 로 표지한다 · "
                    "(v3 · 2026-09-26) filingDate < %s 이고 원본 시각을 ET 로 읽으면 filingDate %s–%s 인 문서는 filingDate 다음 거래일"
                    "(fd_etamb · 숨은 ET 표기 · 보수). 옛 규칙 = 접수 시각만(bfae3758 판)." % (LATE_ACC_BDAYS, ET_AMB_BEFORE, ET_AMB_WINDOW[0],
                                                                                  ET_AMB_WINDOW[1]),
            "fd_floor_vs_et_reading": {"note": "선언 — fd_floor 가용일이 원본 시각을 ET 로 읽은 가용일보다 늦은 NYSE 거래일 수(문서 수) · "
                                               "보수 쪽이라 그대로 둔다", "lag_tdays": dict(sorted(lag.items(), key=lambda kv: str(kv[0])))},
            "fd_etamb": {"n": len(amb), "in_world": sum(1 for r in amb if r["in_world"]),
                         "by_year": dict(sorted(collections.Counter(r["fd"][:4] for r in amb).items())),
                         "pub_m_changed": sum(1 for r in amb if r["avail"][:7] != r["avail_acc_only"][:7]),
                         "pub_m_changed_in_world": sum(1 for r in amb if r["in_world"] and r["avail"][:7] != r["avail_acc_only"][:7])},
            "n_docs": len(out), "avail_how": dict(sorted(collections.Counter(r["avail_how"] for r in out).items())),
            "avail_how_in_world": dict(sorted(collections.Counter(r["avail_how"] for r in out if r["in_world"]).items())),
            "n_avail_changed": len(ch), "n_avail_changed_in_world": sum(1 for r in ch if r["in_world"]),
            "n_pub_m_changed": len(pm), "n_pub_m_changed_in_world": sum(1 for r in pm if r["in_world"]),
            "by_how": {h: {"avail_changed": sum(1 for r in ch if r["avail_how"] == h),
                           "pub_m_changed": sum(1 for r in pm if r["avail_how"] == h)}
                       for h in ("fd_floor", "fd_late", "fd_etamb", "fd_noacc")},
            "fd_late": [[r["acc"], r["tickers"], r["fd"], r["accepted_et"], r["avail_acc_only"], r["avail"]]
                        for r in out if r["avail_how"] == "fd_late"],
            "pub_m_changed": [[r["acc"], r["tickers"], r["fd"], r["accepted_et"], r["avail_acc_only"], r["avail"], r["avail_how"],
                               r["in_world"]] for r in pm],
            "changed": [[r["acc"], r["fd"], r["accepted_et"], r["avail_acc_only"], r["avail"], r["avail_how"]] for r in ch]}


def _eg_ranks():
    """data/_eg_q5_scores_pitgics.json(형성월별 Eg 예측치 · 수익 아님) → {달: {티커: 순위(1 = 최고)}}."""
    d = _rj(os.path.join(DATA, "_eg_q5_scores_pitgics.json")) or {}
    out = {}
    for ym, sc in (d.get("months") or {}).items():
        xs = sorted(((v, t) for t, v in sc.items() if v is not None), reverse=True)
        out[ym] = {t: i + 1 for i, (v, t) in enumerate(xs)}
    return out


def coverage(out, gm, R):
    """연도 · 섹터별 분리 실패율 · 형태 분포 · 형태 전환 · 유효 짝 · 세계 그룹-분기 커버리지 · 실패와 Eg 순위(수익 없음).
    카드 판(접미 없음) · v2 판(_v2) · v3 판(_v3)을 함께 싣는다. 실패는 둘로 나눈다 — split_fail(절은 찾았는데 형태를 못 정함) 과
    no_1a(문서에 Part II Item 1A 가 없음 · 사람 라벨로 확인한 «진짜 없음»이 대부분). R2 F0 «연도별 분리 실패율 ≤ 20%» 는 두 읽기로
    싣는다 — split_fail 만(split_fail_rate) · split_fail + no_1a(split_fail_plus_no1a_rate). no_1a 는 판과 무관한 커버리지 손실이다."""
    W = [r for r in out if r["in_world"] and not (r["parse_status"].startswith("fetch") or r["parse_status"] == "unparsed")]
    yr = lambda r: r["avail"][:4]  # noqa: E731
    cnt = lambda it: dict(sorted(collections.Counter(it).items(), key=lambda kv: str(kv[0])))  # noqa: E731
    q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))] if v else None  # noqa: E731
    secof = {}
    for r in W:
        t = r["tickers"][0] if r["tickers"] else None
        secof[r["acc"]] = (IM.sector_at(R, t, r["pub_m"]) if t else None) or "?"
    egr = _eg_ranks()
    res = {"n_docs": len(out), "n_world_docs": len(W),
           "sec_how": cnt(r["sec_how"] for r in W if r["sec_how"]), "sec_end": cnt(r["sec_end"] for r in W if r["sec_end"])}
    for sfx in ("", "_v2", "_v3"):
        k_st, k_sh, k_ps, k_sim = "parse_status" + sfx, "shape" + sfx, "pair_status" + sfx, "SimRF" + sfx
        by_y = collections.defaultdict(collections.Counter)
        by_s = collections.defaultdict(collections.Counter)
        for r in W:
            by_y[yr(r)][r[k_st]] += 1
            by_s[secof[r["acc"]]][r[k_st]] += 1

        def rates(c):
            n = sum(c.values())
            return {"n": n, "split_fail": c["split_fail"], "no_1a": c["no_1a"], "error": c["error"],
                    "split_fail_rate": round(c["split_fail"] / max(1, n), 4), "no_1a_rate": round(c["no_1a"] / max(1, n), 4),
                    "split_fail_plus_no1a_rate": round((c["split_fail"] + c["no_1a"]) / max(1, n), 4),
                    "invalid_rate": round((n - c["ok"]) / max(1, n), 4)}
        shape_y = collections.defaultdict(collections.Counter)
        pair_y = collections.defaultdict(collections.Counter)
        for r in W:
            shape_y[yr(r)][r[k_sh] or r[k_st]] += 1
            pair_y[yr(r)][r[k_ps]] += 1
        sw = {y: round(c["shape_switch"] / max(1, c["ok"] + c["shape_switch"]), 4) for y, c in sorted(pair_y.items())}
        # 실패와 Eg 순위(형성월 = pub_m 직전 달의 Eg · 순위 1..N) — 상위 30 · 31~100 · 101+ · Eg 없음
        eg = collections.defaultdict(collections.Counter)
        for r in W:
            m0 = _madd(r["pub_m"], -1)
            rk = min((egr.get(m0, {}).get(t) for t in r["tickers"] if egr.get(m0, {}).get(t)), default=None)
            b = "no_eg" if rk is None else ("top30" if rk <= 30 else ("31-100" if rk <= 100 else "101+"))
            eg[b][r[k_st]] += 1
        nw = sorted(r["n_words_rf"] for r in W if r[k_st] == "ok")
        sims = sorted(r[k_sim] for r in W if r[k_sim] is not None)
        res[{"": "v1_card", "_v2": "v2", "_v3": "v3"}[sfx]] = {
            "status": cnt(r[k_st] for r in W), "shape": cnt(r[k_sh] for r in W if r[k_sh]),
            "boiler_kind": cnt(r["boiler" + sfx] for r in W if r["boiler" + sfx]) if sfx else None,
            "fail_by_year": {y: rates(c) for y, c in sorted(by_y.items())},
            "fail_by_sector": {s_: rates(c) for s_, c in sorted(by_s.items())},
            "fail_by_eg_rank": {b_: rates(c) for b_, c in sorted(eg.items())},
            "shape_by_year": {y: dict(c) for y, c in sorted(shape_y.items())},
            "pair_status_by_year": {y: dict(c) for y, c in sorted(pair_y.items())},
            "pairs_ok_by_year": {y: c["ok"] for y, c in sorted(pair_y.items())},
            "shape_switch_rate_by_year": sw,
            "n_words_rf_quantiles": {p: q(nw, p) for p in (0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)},
            "SimRF_quantiles": {p: (round(q(sims, p), 4) if sims else None) for p in (0.01, 0.1, 0.2, 0.5, 0.8, 0.9, 0.99)},
            "f0": {"pairs_ge_900_by_year": {y: c["ok"] >= 900 for y, c in sorted(pair_y.items())},
                   "split_fail_le_20pct_by_year": {y: rates(c)["split_fail_rate"] <= 0.20 for y, c in sorted(by_y.items())},
                   "split_fail_plus_no1a_le_20pct_by_year": {y: rates(c)["split_fail_plus_no1a_rate"] <= 0.20
                                                             for y, c in sorted(by_y.items())},
                   "invalid_le_20pct_by_year": {y: rates(c)["invalid_rate"] <= 0.20 for y, c in sorted(by_y.items())}},
        }
    # R2 F0 문구(두 읽기) 한눈 표 · no_1a 커버리지 손실(판과 무관 — 경계가 같다)
    res["f0_wording"] = {
        "note": "R2 F0 «연도별 분리 실패율 ≤ 20%» — 읽기 A = split_fail ÷ 세계 문서 · 읽기 B = (split_fail + no_1a) ÷ 세계 문서. "
                "등록 커밋에서 하나로 고정한다. no_1a(문서에 Part II Item 1A 가 없음)는 형태 판과 무관한 커버리지 손실이다.",
        "by_version": {v: {y: {"split_fail_rate": c["split_fail_rate"], "split_fail_plus_no1a_rate": c["split_fail_plus_no1a_rate"],
                               "pass_A": c["split_fail_rate"] <= 0.20, "pass_B": c["split_fail_plus_no1a_rate"] <= 0.20}
                           for y, c in res[v]["fail_by_year"].items()} for v in ("v1_card", "v2", "v3")},
        "no_1a_coverage_loss_by_year": {y: {"n": c["n"], "no_1a": c["no_1a"], "share": c["no_1a_rate"]}
                                        for y, c in res["v2"]["fail_by_year"].items()}}
    # 세계 비금융 그룹-분기 가운데 10-Q 가 있는 몫(1·2·3분기 10-Q 만 있고 4분기는 10-K 라 약 3/4 가 상한)
    gq = set()
    for g, ms in gm.items():
        for ym in ms:
            gq.add((g, ym[:4], (int(ym[5:7]) - 1) // 3))
    have = {(r["grp"], r["pub_m"][:4], (int(r["pub_m"][5:7]) - 1) // 3) for r in W}
    gq_y = collections.defaultdict(lambda: [0, 0])
    for g, y, qq in gq:
        gq_y[y][0] += 1
        gq_y[y][1] += (g, y, qq) in have
    res["group_quarters_with_10q"] = {y: [v[0], v[1], round(v[1] / max(1, v[0]), 4)] for y, v in sorted(gq_y.items())}
    return res


def ix_checks(out):
    """(4) iXBRL 전환 짝(2019~2021)의 SimRF · SimDoc 분포 대 같은 해 전환 아닌 짝 · (5) ix:header 제거(JNJ 포함 전체)."""
    P = _rj(PARSED)["docs"]

    def qs(v):
        v = sorted(v)
        return {"n": len(v), "p10": round(v[int(0.1 * len(v))], 4) if v else None,
                "p20": round(v[int(0.2 * len(v))], 4) if v else None,
                "p50": round(v[len(v) // 2], 4) if v else None, "p90": round(v[int(0.9 * len(v))], 4) if v else None,
                "mean": round(sum(v) / len(v), 4) if v else None}
    sw = [r for r in out if r["ixbrl_switch"] == 1]
    ys = sorted({r["avail"][:4] for r in sw})
    res = {"n_switch_pairs": len(sw), "switch_years": dict(collections.Counter(r["avail"][:4] for r in sw))}
    for key in ("SimRF", "SimRF_v2", "SimRF_v3", "SimDoc"):
        a = [r[key] for r in sw if r[key] is not None]
        b = [r[key] for r in out if r["ixbrl_switch"] == 0 and r["avail"][:4] in ys and r[key] is not None]
        res[key] = {"switch_pairs": qs(a), "same_years_non_switch": qs(b)}
    ixd = [r for r in out if r["isInlineXBRL"] == 1 and r["acc"] in P]
    res["ixheader"] = {"ix_docs": len(ixd), "with_ixheader_removed": sum(1 for r in ixd if P[r["acc"]]["n_ixheader"] > 0),
                       "leak": sum(1 for r in ixd if P[r["acc"]].get("ixh_leak")),
                       "JNJ": [[r["acc"], r["fd"], P[r["acc"]]["n_ixheader"], P[r["acc"]].get("ixh_leak"),
                                P[r["acc"]]["parse_status"], P[r["acc"]].get("shape"), P[r["acc"]].get("shape_v3")]
                               for r in ixd if r["cik"] == 200406]}
    return res


# ════════════════════════════════════════════════════════════════════════
# 검증 — 손 라벨 표본 · 보기 · 채점
# ════════════════════════════════════════════════════════════════════════
RX_SKEL = re.compile(r"\bitems?\s*\d|\bpart\s+(?:i|ii|1|2)\b|risk\s+factors?|unregistered\s+sales|legal\s+proceedings|"
                     r"defaults\s+upon|mine\s+safety|other\s+information|^exhibits?\b|signatures?|issuer\s+purchases|"
                     r"purchases\s+of\s+equity|controls\s+and\s+procedures|cross[- ]reference|table\s+of\s+contents", re.I)


def cmd_vsample(argv):
    """시드 고정 비례 층화(연도 · iXBRL · 파서 형태 순 정렬 뒤 계통 추출) — 표본만 적고 파서 결과는 적지 않는다.
    라운드 2 이상은 cmd_vsample_strata(적대 검토가 지목한 층을 일부러 넣고 나머지를 무작위로)."""
    n = _arg(argv, "--n", 100, int)
    rnd = _arg(argv, "--round", 1, int)
    if rnd >= 2:
        return cmd_vsample_strata(argv, n, rnd)
    P = _rj(PARSED)["docs"]
    L = _rj(LIST)
    O = _rj(OUT)
    if not O:
        raise SystemExit("data/_tenq_rf.json 이 없다 — build 먼저(표본은 세계 문서(in_world)에서만 뽑는다)")
    inw = {r["acc"] for r in panel_rows(O) if r["in_world"]}
    uniq = {}
    for r in L["docs"]:
        if r["acc"] in P and P[r["acc"]]["parse_status"] != "error" and r["acc"] in inw:
            uniq.setdefault(r["acc"], r)
    prev = set()
    V = _rj(LABELS) or {}
    for rr, v in (V.get("rounds") or {}).items():
        prev |= set(v.get("sample") or [])
    rng = random.Random(SEED + 1000 * rnd)
    xs = [r for r in uniq.values() if r["acc"] not in prev]
    keyed = sorted(xs, key=lambda r: (r["fd"][:4], r["isInlineXBRL"], P[r["acc"]].get("shape") or "Z", rng.random()))
    step = len(keyed) / n
    off = rng.random() * step
    pick = [keyed[int(off + i * step)]["acc"] for i in range(n)]
    V.setdefault("rounds", {}).setdefault(str(rnd), {})
    V["rounds"][str(rnd)]["sample"] = pick
    V["rounds"][str(rnd)].setdefault("labels", {})
    V["rounds"][str(rnd)]["drawn"] = {"seed": SEED + 1000 * rnd, "n": n, "from": len(keyed), "at": _now(),
                                      "parser_hash": parser_hash(),
                                      "rule": "세계 문서(in_world) 가운데 연도 · iXBRL · 카드 판 파서 형태(실패는 Z) · 난수 순으로 "
                                              "정렬 → 계통 추출(비례 층화)"}
    V.setdefault("label_rules", LABEL_RULES)
    _wj(LABELS, V, indent=1)
    print("표본 %d건(라운드 %d) → %s" % (len(pick), rnd, LABELS))


# 라운드 2 층(순서 = 겹칠 때 먼저 든 층) · 목표 수(plain 은 «넣을 수 있는 만큼 전부»)
STRATA2 = (("plain", None, "plain 경로(sec_how plain · item1a_pfx) 세계 문서 전부 — 경계 b2 ① ③ 검증"),
           ("xref", 12, "교차참조 색인 10-Q(has_xref · 그룹마다 돌아가며) + LMT 2건(검토가 GE · LMT · CAH 를 지목) — 경계 b2 ②"),
           ("fls_u", 12, "v2 U · 500단어 미만 · 절에 forward-looking/safe harbor 문구 — v3 ②"),
           ("ref", 10, "v2 또는 v3 적중 종류 ref(참조문만) — v3 ①"),
           ("upd_long", 8, "v2 적중 종류 upd · 1,500단어 이상(긴 목록 · v3 ③ upd_restate 포함)"),
           ("random", None, "나머지 — 연도 · iXBRL · v3 형태(실패 Z) · 난수 순 정렬 뒤 계통 추출"))


def cmd_vsample_strata(argv, n, rnd):
    """라운드 ≥ 2 표본 — v3 동결(파서 해시 기록) 뒤 새 시드로 뽑는다. 앞 라운드 표본과 설계에 쓴 문서(design_docs · 뽑기 전에
    handlabels.json 라운드 기록에 적는다)는 뺀다. 층마다 난수 순서로 고르고 나머지는 계통 추출. 파서 결과는 적지 않는다(층 이름만)."""
    P = _rj(PARSED)["docs"]
    O = _rj(OUT)
    if not O or O.get("parser_hash") != parser_hash():
        raise SystemExit("data/_tenq_rf.json 이 지금 파서로 빌드되지 않았다 — parse · build 먼저")
    rows = {r["acc"]: r for r in panel_rows(O) if r["in_world"] and P.get(r["acc"], {}).get("parse_status") != "error"}
    V = _rj(LABELS) or {}
    R_ = V.setdefault("rounds", {}).setdefault(str(rnd), {})
    if R_.get("sample"):
        raise SystemExit("라운드 %d 표본이 이미 있다 — 다시 뽑지 않는다" % rnd)
    prev = set()
    for rr, v in (V.get("rounds") or {}).items():
        prev |= set(v.get("sample") or [])
    design = set(R_.get("design_docs") or {})
    seed = SEED + 1000 * rnd
    rng = random.Random(seed)
    pool = sorted(a for a in rows if a not in prev and a not in design)
    rng.shuffle(pool)
    taken, strata = set(), {}

    def take(name, cands, k):
        got = [a for a in cands if a not in taken][:k] if k is not None else [a for a in cands if a not in taken]
        for a in got:
            taken.add(a)
            strata[a] = name
        return got

    def feat_text(a):
        f = _load_feat(rows[a]["fd"], a) or {}
        return (f.get("sec_text") or "").lower()
    # plain
    take("plain", [a for a in pool if rows[a]["sec_how"] in ("plain", "item1a_pfx")], None)
    # xref — 그룹마다 돌아가며(난수 순서) + LMT 2건
    xg = collections.defaultdict(list)
    for a in pool:
        if P[a].get("has_xref"):
            xg[rows[a]["grp"]].append(a)
    lmt = [a for a in pool if "LMT" in rows[a]["tickers"]]
    k_x = STRATA2[1][1] - 2
    order, gs = [], sorted(xg)
    while len(order) < k_x and any(xg[g] for g in gs):
        for g in gs:
            if xg[g] and len(order) < k_x:
                order.append(xg[g].pop(0))
    take("xref", order, k_x)
    take("xref", lmt, 2)
    # FLS 문구가 있는 짧은 U(v2)
    fl = [a for a in pool if a not in taken and rows[a]["shape_v2"] == "U" and (rows[a]["n_words_rf"] or 0) < F_MIN
          and RX_FLSCUE.search(feat_text(a))]
    take("fls_u", fl, STRATA2[2][1])
    take("ref", [a for a in pool if "ref" in (rows[a]["boiler_v2"], rows[a]["boiler_v3"])], STRATA2[3][1])
    take("upd_long", [a for a in pool if rows[a]["boiler_v2"] == "upd" and (rows[a]["n_words_rf"] or 0) >= 1500], STRATA2[4][1])
    k_r = n - len(taken)
    rest = [a for a in pool if a not in taken]
    keyed = sorted(rest, key=lambda a: (rows[a]["fd"][:4], rows[a]["isInlineXBRL"], rows[a]["shape_v3"] or "Z", rng.random()))
    step = len(keyed) / max(1, k_r)
    off = rng.random() * step
    take("random", [keyed[int(off + i * step)] for i in range(k_r)], k_r)
    pick = sorted(taken, key=lambda a: (strata[a], rows[a]["fd"], a))
    # 층별 모집단 크기(가중 추정용 · 같은 층 정의 · 앞 라운드 · 설계 문서 포함 전체 세계 문서 기준)
    allw = sorted(rows)
    pop = collections.Counter()
    seen = set()
    for a in allw:
        if rows[a]["sec_how"] in ("plain", "item1a_pfx"):
            nm = "plain"
        elif P[a].get("has_xref") or "LMT" in rows[a]["tickers"]:
            nm = "xref"
        elif rows[a]["shape_v2"] == "U" and (rows[a]["n_words_rf"] or 0) < F_MIN and RX_FLSCUE.search(feat_text(a)):
            nm = "fls_u"
        elif "ref" in (rows[a]["boiler_v2"], rows[a]["boiler_v3"]):
            nm = "ref"
        elif rows[a]["boiler_v2"] == "upd" and (rows[a]["n_words_rf"] or 0) >= 1500:
            nm = "upd_long"
        else:
            nm = "random"
        pop[nm] += 1
        seen.add(a)
    R_["sample"] = pick
    R_["strata"] = {a: strata[a] for a in pick}
    R_.setdefault("labels", {})
    R_["drawn"] = {"seed": seed, "n": len(pick), "pool": len(pool), "at": _now(), "parser_hash": parser_hash(),
                   "strata_rule": [list(x) for x in STRATA2],
                   "n_by_stratum": dict(collections.Counter(strata.values())), "population_in_world_by_stratum": dict(pop),
                   "rule": "v3 동결 뒤 새 시드 · 세계 문서(in_world) 가운데 앞 라운드 표본 · design_docs 를 빼고 층 순서대로 "
                           "(난수 순) 고른 뒤 나머지는 연도 · iXBRL · v3 형태 · 난수 순 계통 추출"}
    V.setdefault("label_rules", LABEL_RULES)
    _wj(LABELS, V, indent=1)
    print("표본 %d건(라운드 %d · 시드 %d) → %s · 층 %s" % (len(pick), rnd, seed, LABELS, R_["drawn"]["n_by_stratum"]))


LABEL_RULES = {
    "s": "Part II Item 1A 절 머리 줄(vview 줄 번호 · 목차 · 교차참조 색인이 아닌 본문 머리). 머리 없이 본문만 있으면 본문 첫 줄. "
         "절이 없으면 null.",
    "e": "절 바로 다음 항목 머리 줄(끝 · 제외 · Item 2~6 · Signatures · Exhibit Index). 문서 끝까지면 줄 수.",
    "shape": "의미로 판정한다(파서 정규식이 아니라 · 표본을 보기 전에 고정). "
             "B = 자기 위험요인 서술이 없다 — 변경 없음 문장(어떤 표현이든)이나 10-K/직전 10-Q 위험요인 참조문(± 미래예측 "
             "경고)뿐. U = 변경 없음/참조/갱신 선언(«except as set forth below» · «the following supplements/updates» 포함) + "
             "새로 넣거나 고친 위험요인 서술 일부(전체 목록의 재기재가 아님). F = 스스로 완결된 위험요인 목록을 싣는다(재기재 · "
             "«the risks described below» 식) — 변경 없음 문장이 있어도 전체를 다시 싣으면 F. X = 문서에 Part II Item 1A 가 없다 · "
             "'None/Not applicable' · 같은 10-Q 의 다른 곳(MD&A 등)이나 색인 각주로 넘기는 교차참조만 있다.",
    "note": "애매한 경우 note 에 이유를 적는다(채점은 라벨 그대로).",
}


def _lines_of(acc, L):
    r = next(x for x in L["docs"] if x["acc"] == acc)
    b = gzip.open(doc_path(r["fd"], acc), "rb").read()
    lines, _ = doc_lines(b)
    return r, lines


def cmd_vview(argv):
    """라벨용 보기 — 파서 결과는 보여 주지 않는다.
    ACC …            → 골격(머리 모양 줄 · «(continued)» 쪽 머리와 «table of contents» 줄은 뺀다)
    ACC:S:E …        → 줄 S..E 본문(앞 12줄 전문 · 그 뒤 짧은 줄(≤ 14단어 · 소제목 후보) 최대 60개 · 끝 5줄 · 토큰 수)."""
    L = _rj(LIST)
    for arg in argv[2:]:
        m = re.match(r"^(\d{10}-\d{2}-\d{6})(?::(\d+):(\d+))?$", arg)
        if not m:
            continue
        acc = m.group(1)
        r, lines = _lines_of(acc, L)
        print("=" * 100)
        print("%s  %s  %s  fd %s rd %s ix %s  줄 %d" % (acc, r["grp"], r["doc"], r["fd"], r["rd"], r["isInlineXBRL"],
                                                     len(lines)))
        if m.group(2) is not None:
            s_, e = int(m.group(2)), int(m.group(3))
            toks = []
            for k in range(s_, min(e, len(lines))):
                toks += [] if lines[k][1] else tokens(lines[k][0])
            print("  범위 %d..%d · 토큰(줄 전체 · 숫자 표 제외) %d" % (s_, e, len(toks)))
            shown = 0
            for k in range(max(0, s_ - 2), min(len(lines), e + 3)):
                t = lines[k][0]
                if k < s_ + 12 or k > e - 5:
                    print("  %5d%s %s" % (k, "#" if lines[k][1] else " ", t[:500]))
                elif len(t.split()) <= 14 and shown < 60:
                    shown += 1
                    print("  %5d%s %s" % (k, "#" if lines[k][1] else " ", t[:160]))
            continue
        for k, (t, isnum) in enumerate(lines):
            if len(t.split()) <= 25 and RX_SKEL.search(t) and not re.search(r"\(continued\)|table of contents", t, re.I):
                print("  %5d%s %s" % (k, "#" if isnum else " ", t[:150]))


def _shape_scores(per, key):
    conf = collections.Counter((x["true_shape"], x[key]) for x in per)
    n = len(per)
    pr = {}
    for c in ("B", "U", "F", "X"):
        tpc = conf[(c, c)]
        pp = sum(v for (a, b), v in conf.items() if b == c)
        tt = sum(v for (a, b), v in conf.items() if a == c)
        pr[c] = {"n_true": tt, "n_par": pp, "precision": round(tpc / pp, 4) if pp else None,
                 "recall": round(tpc / tt, 4) if tt else None}
    acc = sum(v for (a, b), v in conf.items() if a == b) / max(1, n)
    # 짝 비교 관점: B·U 는 서로 비교되므로(형태 전환이 아님) {B,U} · F · X 세 칸으로 묶은 정확도도 싣는다
    g = lambda z: "BU" if z in ("B", "U") else z  # noqa: E731
    acc3 = sum(v for (a, b), v in conf.items() if g(a) == g(b)) / max(1, n)
    return {"accuracy": round(acc, 4), "accuracy_BU_merged": round(acc3, 4), "by_class": pr,
            "confusion": {"%s->%s" % k: v for k, v in sorted(conf.items())}}


def cmd_vscore(argv):
    """손 라벨 채점 — 경계(토큰 정밀도·재현율 · 시작/끝 줄 일치 · ±10% 단어수) · 형태(카드 v1 · v2 · 사람 경계에 규칙만 건 값)."""
    rnd = str(_arg(argv, "--round", 1, int))
    as_key = _arg(argv, "--as", rnd)                # 앞 라운드를 지금 파서로 다시 채점할 때 다른 키로 싣는다(예: 1_rescore)
    V = _rj(LABELS)
    R_ = V["rounds"][rnd]
    strata = R_.get("strata") or {}
    L = _rj(LIST)
    per = []
    tp = fp = fn = 0
    for acc in R_["sample"]:
        lab = R_["labels"].get(acc)
        if lab is None:
            continue
        r, lines = _lines_of(acc, L)
        f, _ = features(gzip.open(doc_path(r["fd"], acc), "rb").read())
        if lab.get("s") is None:
            tper, ttoks, tbody = {}, [], []
        else:
            i0, rest = body_span(lines, lab["s"])
            ttoks, tper = sec_tokens(lines, i0, rest, lab["e"])
            tbody = sec_body(lines, i0, rest, lab["e"])
        ps = f["sec"]
        if ps is None:
            pper = {}
        else:
            i0, rest = body_span(lines, ps["s"])
            _, pper = sec_tokens(lines, i0, rest, ps["e"])
        ov = sum(min(v, tper.get(k, 0)) for k, v in pper.items())
        nt, npar = sum(tper.values()), sum(pper.values())
        tp += ov
        fp += npar - ov
        fn += nt - ov
        within = (nt == 0 and npar == 0) or (nt > 0 and abs(npar - nt) <= 0.10 * nt)
        r1 = shape_of(ttoks)[0] if ttoks else None
        r2 = shape_v2(ttoks)[0] if ttoks else None
        r3 = shape_v3(ttoks, tbody)[0] if ttoks else None
        per.append({"acc": acc, "fd": r["fd"], "ix": r["isInlineXBRL"], "true_s": lab.get("s"), "true_e": lab.get("e"),
                    "par_s": ps and ps["s"], "par_e": ps and ps["e"], "n_true": nt, "n_par": npar, "overlap": ov,
                    "within10": within,
                    "start_ok": (ps["s"] if ps else None) == lab.get("s"),
                    "end_ok": (ps["e"] if ps else None) == (lab.get("e") if lab.get("s") is not None else None),
                    "true_shape": lab["shape"], "v1": f["shape"] or "X", "v2": f["shape_v2"] or "X", "v3": f["shape_v3"] or "X",
                    # 엄격 판(2026-09-26 · 검토 지적): 파서 실패 가운데 split_fail 은 «X(절 없음)» 가 아니다 — SF 로 두어 X 라벨과 맞지 않게 센다
                    "v1_strict": f["shape"] or ("SF" if f["parse_status"] == "split_fail" else "X"),
                    "v2_strict": f["shape_v2"] or ("SF" if f["parse_status_v2"] == "split_fail" else "X"),
                    "v3_strict": f["shape_v3"] or ("SF" if f["parse_status_v3"] == "split_fail" else "X"),
                    "v1_on_truth": r1 or "X", "v2_on_truth": r2 or "X", "v3_on_truth": r3 or "X",
                    "par_status": f["parse_status"], "par_status_v2": f["parse_status_v2"], "par_status_v3": f["parse_status_v3"],
                    "sec_how": ps and ps["how"], "stratum": strata.get(acc), "note": lab.get("note", "")})
    n = len(per)
    has_true = [x for x in per if x["n_true"]]
    doc_prec = [x["overlap"] / x["n_par"] for x in per if x["n_par"]]
    doc_rec = [x["overlap"] / x["n_true"] for x in has_true]
    w10 = sum(x["within10"] for x in per) / max(1, n)
    summ = {"round": int(rnd), "n_labeled": n, "n_sample": len(R_["sample"]),
            "boundary": {"token_precision_micro": round(tp / max(1, tp + fp), 4),
                         "token_recall_micro": round(tp / max(1, tp + fn), 4),
                         "token_precision_macro": round(sum(doc_prec) / max(1, len(doc_prec)), 4),
                         "token_recall_macro": round(sum(doc_rec) / max(1, len(doc_rec)), 4),
                         "start_line_exact": round(sum(x["start_ok"] for x in per) / max(1, n), 4),
                         "end_line_exact": round(sum(x["end_ok"] for x in per) / max(1, n), 4),
                         "within10_share": round(w10, 4),
                         "section_found_precision": round(sum(1 for x in per if x["n_par"] and x["n_true"]) /
                                                          max(1, sum(1 for x in per if x["n_par"])), 4),
                         "section_found_recall": round(sum(1 for x in per if x["n_par"] and x["n_true"]) /
                                                       max(1, len(has_true)), 4)},
            "shape_v1_card": _shape_scores(per, "v1"), "shape_v2": _shape_scores(per, "v2"), "shape_v3": _shape_scores(per, "v3"),
            "shape_strict_note": "엄격 형태 정확도(*_strict) — split_fail 을 X 와 다른 칸(SF)으로 센다: X 로 라벨된 문서의 split_fail 은 "
                                 "틀림. 위 정확도(*)는 모든 파서 실패(split_fail · no_1a)를 X 로 합친 관례(둘 다 무효 짝이 된다).",
            "shape_v1_card_strict": _shape_scores(per, "v1_strict"), "shape_v2_strict": _shape_scores(per, "v2_strict"),
            "shape_v3_strict": _shape_scores(per, "v3_strict"),
            "shape_v1_rule_on_true_boundary": _shape_scores(per, "v1_on_truth"),
            "shape_v2_rule_on_true_boundary": _shape_scores(per, "v2_on_truth"),
            "shape_v3_rule_on_true_boundary": _shape_scores(per, "v3_on_truth"),
            "pass": {"within10_ge_0.90": w10 >= 0.90,
                     "v1_shape_acc_ge_0.95": _shape_scores(per, "v1")["accuracy"] >= 0.95,
                     "v2_shape_acc_ge_0.95": _shape_scores(per, "v2")["accuracy"] >= 0.95,
                     "v3_shape_acc_ge_0.95": _shape_scores(per, "v3")["accuracy"] >= 0.95,
                     "v1_shape_acc_strict_ge_0.95": _shape_scores(per, "v1_strict")["accuracy"] >= 0.95,
                     "v2_shape_acc_strict_ge_0.95": _shape_scores(per, "v2_strict")["accuracy"] >= 0.95,
                     "v3_shape_acc_strict_ge_0.95": _shape_scores(per, "v3_strict")["accuracy"] >= 0.95},
            "parser_hash": parser_hash(), "labels_round": int(rnd), "at": _now()}
    if strata:
        # 층별 성적 · 세계 모집단 가중 추정(층 표본이 일부러 어려운 문서로 채워져 있어 표본 정확도는 모집단 정확도가 아니다)
        pop = (R_.get("drawn") or {}).get("population_in_world_by_stratum") or {}
        bys = collections.defaultdict(list)
        for x in per:
            bys[x["stratum"]].append(x)
        summ["by_stratum"] = {k: {"n": len(xs), "population": pop.get(k),
                                  "within10": sum(x["within10"] for x in xs),
                                  "v1_ok": sum(x["v1"] == x["true_shape"] for x in xs),
                                  "v2_ok": sum(x["v2"] == x["true_shape"] for x in xs),
                                  "v3_ok": sum(x["v3"] == x["true_shape"] for x in xs),
                                  "v3_ok_strict": sum(x["v3_strict"] == x["true_shape"] for x in xs)} for k, xs in sorted(bys.items())}
        tot = sum(pop.get(k, 0) for k in bys)
        if tot:
            summ["population_weighted"] = {
                "note": "층 k 의 표본 비율에 세계 모집단 몫(population_in_world_by_stratum)을 곱해 더한 값 — 표본 설계의 층 가중 추정",
                "within10": round(sum(pop.get(k, 0) / tot * sum(x["within10"] for x in xs) / len(xs) for k, xs in bys.items()), 4),
                **{v + "_acc": round(sum(pop.get(k, 0) / tot * sum(x[v] == x["true_shape"] for x in xs) / len(xs)
                                         for k, xs in bys.items()), 4)
                   for v in ("v1", "v2", "v3", "v1_strict", "v2_strict", "v3_strict")}}
    byy = collections.defaultdict(list)
    for x in per:
        byy[x["fd"][:4]].append(x)
    summ["by_year"] = {y: {"n": len(xs), "within10": sum(x["within10"] for x in xs),
                           "v1_ok": sum(x["v1"] == x["true_shape"] for x in xs),
                           "v2_ok": sum(x["v2"] == x["true_shape"] for x in xs),
                           "v3_ok": sum(x["v3"] == x["true_shape"] for x in xs)} for y, xs in sorted(byy.items())}
    VV = _rj(VALID) or {}
    VV["note"] = ("§C 파서 손 라벨 검증(수익 없음). 라벨 = data/_tenq_rf/handlabels.json(사람이 vview 로 문서를 읽고 적은 절 머리 줄 · "
                  "끝 줄 · 의미 형태). 채점 = build/tenq_rf_build.py vscore. 합격선(사양 §C): ±10% 단어수 ≥ 90% · 형태 정확도 ≥ 95%.")
    old = (VV.get("rounds") or {}).get(as_key) or {}
    if old.get("per_doc") == json.loads(json.dumps(per, ensure_ascii=False)) and             {k: v for k, v in (old.get("summary") or {}).items() if k != "at"} ==             json.loads(json.dumps({k: v for k, v in summ.items() if k != "at"}, ensure_ascii=False)):
        summ["at"] = old["summary"].get("at", summ["at"])   # 같은 채점이면 시각을 그대로(두 번 빌드 sha256 같음 · 2026-09-26)
    VV.setdefault("rounds", {})[as_key] = {"summary": summ, "per_doc": per}
    VV["summary"] = {k: v["summary"] for k, v in VV["rounds"].items()}
    # 등록 판 합격(2026-09-26 · 러너 r_run RF parser_c 가 읽는다) — 등록 형태 판 v3 · 가장 늦은 정식 라운드(숫자 키) · ±10% ≥ 0.90 ·
    #   형태 정확도(엄격 — split_fail ≠ X) ≥ 0.95. 관례 정확도(실패를 X 로 합침)는 옆에 싣는다.
    rk = sorted((k for k in VV["rounds"] if str(k).isdigit()), key=int)
    if rk:
        ss = VV["rounds"][rk[-1]]["summary"]
        acc_s = (ss.get("shape_v3_strict") or {}).get("accuracy")
        acc_m = (ss.get("shape_v3") or {}).get("accuracy")
        w10 = ss["boundary"]["within10_share"]
        VV["registered"] = {"shape_ver": "v3", "round": rk[-1], "within10": w10, "shape_acc_strict": acc_s, "shape_acc_merged": acc_m,
                            "population_weighted": ss.get("population_weighted"), "rule": "within10 ≥ 0.90 ∧ 엄격 형태 정확도 ≥ 0.95",
                            "parser_hash": ss.get("parser_hash")}
        VV["registered_pass"] = bool(acc_s is not None and w10 >= 0.90 and acc_s >= 0.95)
    _wj(VALID, VV, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    for x in per:
        if not x["within10"] or x["true_shape"] != x["v1"] or x["true_shape"] != x["v2"] or x["true_shape"] != x["v3"]:
            print("  ✗", x["acc"], x["fd"], x["stratum"], "true", x["true_s"], x["true_e"], x["n_true"], x["true_shape"], "| par",
                  x["par_s"], x["par_e"], x["n_par"], "v1", x["v1"], "v2", x["v2"], "v3", x["v3"], "|", x["note"][:90])


def _bs4_words(b: bytes) -> int:
    """독립 경로 단어수 — BeautifulSoup(html.parser) · script/style/head/ix:header/display:none 제거 · get_text · 같은 토큰 규칙.
    숫자 표 제거는 하지 않는다(문서 전체 척도 비교용 · 그래서 수준이 아니라 순위를 본다)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(decode_doc(b), "html.parser")
    for t in soup.find_all(["script", "style", "head", "ix:header"]):
        t.decompose()
    for t in soup.find_all(style=RX_HIDDEN):
        t.decompose()
    return len(tokens(soup.get_text(" ")))


LM_DIR = os.path.join(RAW, "lm")
LM_URL = "https://drive.usercontent.google.com/download?id=1nNoON97aL_6e9jZYZ38lUs-EO4kuMiCj&export=download&confirm=t"
LM_TOTAL = 196768524               # Loughran-McDonald_10X_Summaries_1993-2025.csv(sraf.nd.edu → Google Drive) 전체 바이트


def _lm_rows():
    """RBATCH_RAW/lm 의 조각(header.csv + lm10x_bytes_<시작>-<끝>.part · HTTP Range 로 받은 것)에서 {ACC_NUM: 행} 과 조각 정보.
    Google Drive 가 전체 받기에 'Quota exceeded' 를 돌려 파일 끝(2021-08..2025-12) 20MiB 만 받았다(파일은 FILING_DATE 순)."""
    import csv
    hp = os.path.join(LM_DIR, "header.csv")
    if not os.path.exists(hp):
        return {}, []
    head = io.open(hp, encoding="latin-1").read().strip().split(",")
    out, parts = {}, []
    for fn in sorted(os.listdir(LM_DIR)):
        m = re.match(r"^lm10x_bytes_(\d+)-(\d+)\.part$", fn)
        if not m:
            continue
        b = open(os.path.join(LM_DIR, fn), "rb").read()
        parts.append({"file": fn, "range": [int(m.group(1)), int(m.group(2))], "of": LM_TOTAL, "sha256": _sha(b)})
        if int(m.group(1)) > 0:
            b = b[b.index(b"\n") + 1:]                  # 앞 조각에 걸친 첫 줄은 버린다
        b = b[:b.rfind(b"\n")]                          # 끝에서 잘린 줄도 버린다
        for row in csv.reader(io.StringIO(b.decode("latin-1"))):
            if len(row) == len(head):
                d = dict(zip(head, row))
                out[d["ACC_NUM"]] = d
    if out:
        ds = sorted(v["FILING_DATE"] for v in out.values())
        parts.append({"rows": len(out), "filing_dates": [ds[0], ds[-1]]})
    return out, parts


def _spearman(a, b):
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def cmd_xdoc(argv):
    """(2) 문서 수준 점검 — LM 10X Summaries(sraf.nd.edu · Google Drive) 를 받을 수 있으면 그 N_Words 와, 못 받으면 독립 파서
    (bs4 html.parser) 단어수와 순위상관을 잰다(시드 고정 200건 · 수익 없음). 결과는 validation.json 의 xdoc 에 싣는다."""
    n = _arg(argv, "--n", 200, int)
    P = _rj(PARSED)["docs"]
    L = _rj(LIST)
    uniq = {}
    for r in L["docs"]:
        if r["acc"] in P and P[r["acc"]]["parse_status"] != "error":
            uniq.setdefault(r["acc"], r)
    rng = random.Random(SEED + 7)
    xs = rng.sample(sorted(uniq), n)
    a, b = [], []
    for acc in xs:
        r = uniq[acc]
        raw = gzip.open(doc_path(r["fd"], acc), "rb").read()
        a.append(P[acc]["n_words_doc"])
        b.append(_bs4_words(raw))

    rho = _spearman(a, b)
    ratio = sorted(x / y for x, y in zip(a, b) if y)
    res = {"bs4": {"n": n, "seed": SEED + 7, "reference": "bs4 html.parser 독립 경로(같은 토큰 규칙 · 숫자 표 제거 없음)",
                   "spearman_rho": round(rho, 4), "pass_ge_0.95": rho >= 0.95,
                   "ratio_mine_over_ref": {"p10": round(ratio[int(0.1 * len(ratio))], 3),
                                           "p50": round(ratio[len(ratio) // 2], 3), "p90": round(ratio[int(0.9 * len(ratio))], 3)},
                   "note": "내 단어수는 숫자 표 줄을 뺀 값이라 기준보다 작다(비율 < 1) — 비교는 순위로 한다."}}
    # (2) 사양 본판 — LM 10X Summaries N_Words(마스터 사전 단어 수 · 제출 전체 텍스트)와 순위상관 · 받은 조각에 있는 문서만
    lm, parts = _lm_rows()
    cand = sorted(acc for acc in uniq if acc in lm)
    if cand:
        pick = random.Random(SEED + 8).sample(cand, min(n, len(cand)))
        a2 = [P[x]["n_words_doc"] for x in pick]
        b2 = [int(lm[x]["N_Words"]) for x in pick]
        rho2 = _spearman(a2, b2)
        nex = [int(lm[x]["N_Exhibits"]) for x in pick]
        net = [int(lm[x]["NetFileSize"]) for x in pick]
        light = [i for i, k in enumerate(nex) if k <= 9]
        rat = sorted(y / max(1, x) for x, y in zip(a2, b2))
        res["lm"] = {"n": len(pick), "seed": SEED + 8, "matched_pool": len(cand), "parts": parts, "url": LM_URL,
                     "spearman_rho": round(rho2, 4), "pass_ge_0.95": rho2 >= 0.95,
                     "diagnosis": {
                         "lm_nwords_vs_lm_netfilesize_rho": round(_spearman(b2, net), 4),
                         "mine_vs_lm_netfilesize_rho": round(_spearman(a2, net), 4),
                         "ratio_lm_over_mine": {"p10": round(rat[int(0.1 * len(rat))], 3), "p50": round(rat[len(rat) // 2], 3),
                                                "p90": round(rat[int(0.9 * len(rat))], 3)},
                         "exhibit_light_n_exhibits_le_9": {"n": len(light),
                                                           "rho": round(_spearman([a2[i] for i in light],
                                                                                  [b2[i] for i in light]), 4) if light else None},
                         "note": "LM N_Words 는 제출 전체(본문 + 첨부 EX-10 등) 단어 수다 — LM NetFileSize 와 순위상관이 거의 1. 이 파일의 "
                                 "n_words_doc 은 주 문서만 센다. 첨부가 큰 제출(N_Exhibits 11~41)이 LM/내 비율 3~10배 꼬리를 만든다."},
                     "years": dict(collections.Counter(lm[x]["FILING_DATE"][:4] for x in pick)),
                     "note": "LM 파일은 FILING_DATE 순이고 Google Drive 할당량 때문에 끝 20MiB(2021-08..2025-12)만 받았다 — 표본은 "
                             "그 기간 10-Q 로 한정된다. N_Words 는 LM 마스터 사전 단어만 센 제출 전체 값이라 수준이 아닌 순위로 본다."}
    else:
        res["lm"] = {"n": 0, "note": "LM 조각이 없다(RBATCH_RAW/lm)"}
    res["at"] = _now()
    VV = _rj(VALID) or {}
    VV["xdoc"] = res
    _wj(VALID, VV, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


# ════════════════════════════════════════════════════════════════════════
# r2comp — R2 «큰 개정» Q1 표지의 구성(개수만 · 수익 없음 · 등록 설계 입력)
# ════════════════════════════════════════════════════════════════════════
R2C = os.path.join(VDIR, "r2_composition.json")
STAGE_M = ("2016-08", "2026-07")                 # Stage M 형성월 창(qbatch_core FORM0 .. HOLD1 − 1)
LEN_BUCKETS = ((0, 50, "<=50"), (51, 149, "51-149"), (150, 499, "150-499"), (500, 1999, "500-1999"), (2000, 10 ** 9, ">=2000"))


def _bucket(n):
    for lo, hi, nm in LEN_BUCKETS:
        if n is not None and lo <= n <= hi:
            return nm
    return "none"


def _stage_m_groups():
    """Stage M 세계 {달: 그룹 집합} — 비금융(issuer_map.sector_at) · FPI 아님 · 지도 F0 위반 멤버-월 아님 · 2016-08..2026-07."""
    R = IM.load_refs()
    M = IM.load_map()
    viol = {(v[0], v[1]) for v in ((M["doc"].get("f0") or {}).get("violations") or [])}
    sm = collections.defaultdict(set)
    for (t, ym), v in M["idx"].items():
        if not (STAGE_M[0] <= ym <= STAGE_M[1]) or not v["gid"] or v["fpi"] == 1 or (t, ym) in viol:
            continue
        if IM.sector_at(R, t, ym) == FIN:
            continue
        sm[ym].add(v["gid"])
    return sm, M


def _eg_top30(M):
    """재조정월(Eg 파일 첫 달 + 3·6·9·12월) → 상위 30 이름의 그룹 목록(적대 검토 stageS 근사와 같은 규칙 · 점수만 · 수익 아님)."""
    E = (_rj(os.path.join(DATA, "_eg_q5_scores_pitgics.json")) or {}).get("months") or {}
    months = sorted(E)
    reb = [m for j, m in enumerate(months) if j == 0 or int(m[5:7]) % 3 == 0]
    out = {}
    for r in reb:
        top = sorted(((v, t) for t, v in E[r].items() if v is not None), key=lambda z: (-z[0], z[1]))[:30]
        gs = []
        for v, t in top:
            x = M["idx"].get((t, r)) or M["idx"].get((t.replace("-", "."), r))
            if x and x["gid"]:
                gs.append(x["gid"])
        out[r] = gs
    return out


def _q1_rule(rows, sfx, rule):
    """짝 → (Q1 짝 목록(세계 밖 공개 짝 포함 — CH_active 는 그룹의 모든 10-Q 로 센다), 연도별 경계, 세계 유효 짝 수). 경계는 세계
    (in_world) 유효 짝으로만 선다(r_r2flags ⑦ 과 같은 뜻). rule: base · bb_nochange(B-B 짝 SimRF = 1 로 · 분포와 판정 모두) ·
    bb_nochange_cut_base(경계는 base · B-B 는 Q1 아님) · both150(두 절 모두 150단어 이상인 짝만 · 경계도 그 짝으로) ·
    both150_cut_base(경계는 base · 판정만 두 절 ≥ 150)."""
    import numpy as np
    k_sim, k_sh, k_psh = "SimRF" + sfx, "shape" + sfx, "prev_shape" + sfx
    pairs = [r for r in rows if r["pair_status" + sfx] == "ok" and r[k_sim] is not None]

    def bb(r):
        return r[k_psh] == "B" and r[k_sh] == "B"

    def el150(r):
        return (r["n_words_rf"] or 0) >= B_MAX and (r["prev_n_words_rf"] or 0) >= B_MAX

    def sim(r, for_cut):
        if rule == "bb_nochange" and bb(r):
            return 1.0
        return r[k_sim]
    elig = (lambda r: True) if rule in ("base", "bb_nochange", "bb_nochange_cut_base") else el150
    cut_pool = (lambda r: el150(r)) if rule == "both150" else (lambda r: True)
    by_y = collections.defaultdict(list)
    for r in pairs:
        if r["in_world"] and cut_pool(r):
            by_y[r["pub_m"][:4]].append(sim(r, True))
    cut = {}
    for y in sorted({r["pub_m"][:4] for r in pairs}):
        v = by_y.get(str(int(y) - 1))
        if v:
            cut[y] = float(np.quantile(np.asarray(v, float), Q1_Q))
    q1 = []
    for r in pairs:
        c = cut.get(r["pub_m"][:4])
        if c is None or not elig(r):
            continue
        if rule in ("bb_nochange", "bb_nochange_cut_base") and bb(r):
            continue
        if sim(r, False) < c:
            q1.append(r)
    return q1, cut, sum(1 for r in pairs if r["in_world"])


Q1_Q = 0.20


def cmd_r2comp(argv):
    """R2 Q1(«큰 개정» · 전년도 세계 유효 짝 SimRF 하위 20% 경계 미만) 표지의 구성 — 앞→지금 형태 짝 · 절 길이 칸 · 50단어 이하 절 몫
    · 대안 규칙(B-B 짝 = 변경 없음 · 두 절 모두 150단어 이상일 때만 Q1) · Stage M 세계의 월 CH_active 중앙값/최소 · Eg 상위 30 교체 수
    (재조정월 · Eg 점수 순위 · r_r2flags 대신 이 패널의 pub_m 과 짝 상태를 그대로 쓴 근사 — 적대 검토 r2f0/stageS 와 같은 셈).
    🚨 개수만 — 어떤 표지와 수익의 관계도 계산하지 않는다(가격 · 수익 파일을 읽지 않는다)."""
    import statistics as st_
    O = _rj(OUT)
    if not O or O.get("parser_hash") != parser_hash():
        raise SystemExit("data/_tenq_rf.json 이 지금 파서로 빌드되지 않았다 — build 먼저")
    rows = panel_rows(O)
    W = [r for r in rows if r["in_world"]]
    sm, M = _stage_m_groups()
    months = sorted(sm)
    top = _eg_top30(M)
    res = {"note": "R2 Q1 표지 구성 — 개수만(등록 설계 입력 · 수익 없음). Q1 = 짝 상태 ok 인 세계 짝 가운데 공개연도 Y 의 SimRF 가 Y−1 "
                   "세계 유효 짝 SimRF 의 20% 분위(np.quantile linear)보다 낮은 것. CH_active(g, t) = 공개월 t−2..t 에 Q1 이 하나라도. "
                   "Stage M 세계 = 2016-08..2026-07 비금융 · FPI 아님 · 지도 F0 위반 아님 멤버-월의 그룹. Eg 상위 30 = "
                   "_eg_q5_scores_pitgics.json 재조정월(첫 달 + 3·6·9·12월) 점수 상위 30 이름의 그룹 가운데 CH_active 인 수(교체 수 근사).",
           "generated": _now(), "parser_hash": parser_hash(),
           "panel": {"generated": O.get("generated"), "n_docs": len(rows), "sha256": IM._sha_file(OUT),
                     "path": os.path.relpath(OUT, ROOT).replace(os.sep, "/")},
           "stage_m": {"months": [months[0], months[-1], len(months)], "groups_per_month_median": st_.median(len(sm[m]) for m in months)},
           "eg_rebalances": {"n": len(top), "first": min(top), "last": max(top),
                             "in_stage_m": sum(1 for r in top if STAGE_M[0] <= r <= STAGE_M[1])},
           "len_buckets": [b[2] for b in LEN_BUCKETS], "versions": {}}
    rules = ("base", "bb_nochange", "bb_nochange_cut_base", "both150", "both150_cut_base")
    for ver, sfx in (("card", ""), ("v2", "_v2"), ("v3", "_v3")):
        V_ = {}
        for rule in rules:
            if ver == "card" and rule != "base":
                continue
            q1_all, cut, npairs = _q1_rule(rows, sfx, rule)
            q1 = [r for r in q1_all if r["in_world"]]            # 구성 표는 세계 짝만(적대 검토 r2f0 과 같은 셈)
            k_sh, k_psh = "shape" + sfx, "prev_shape" + sfx
            comp_y = collections.defaultdict(collections.Counter)
            len_y = collections.defaultdict(collections.Counter)
            minlen = collections.Counter()
            for r in q1:
                y = r["pub_m"][:4]
                comp_y[y]["%s-%s" % (r[k_psh], r[k_sh])] += 1
                len_y[y][_bucket(r["n_words_rf"])] += 1
                minlen[_bucket(min(r["n_words_rf"] or 0, r["prev_n_words_rf"] or 0))] += 1
            comp = collections.Counter()
            for c in comp_y.values():
                comp.update(c)
            lens = collections.Counter()
            for c in len_y.values():
                lens.update(c)
            q1g = collections.defaultdict(set)
            for r in q1_all:
                q1g[r["pub_m"]].add(r["grp"])
            ch = []
            for m in months:
                a = q1g.get(m, set()) | q1g.get(_madd(m, -1), set()) | q1g.get(_madd(m, -2), set())
                ch.append(len(a & sm[m]))
            byy = collections.defaultdict(list)
            for m, v in zip(months, ch):
                byy[m[:4]].append(v)
            rep_ = []
            for r_, gs in sorted(top.items()):
                a = q1g.get(r_, set()) | q1g.get(_madd(r_, -1), set()) | q1g.get(_madd(r_, -2), set())
                rep_.append(sum(1 for g in gs if g in a))
            rep_m = [v for (r_, gs), v in zip(sorted(top.items()), rep_) if STAGE_M[0] <= r_ <= STAGE_M[1]]
            n_q1 = len(q1)
            V_[rule] = {"n_valid_pairs_in_world": npairs, "n_q1": n_q1, "n_q1_incl_outside_world": len(q1_all),
                        "cut_by_year": {y: round(c, 6) for y, c in sorted(cut.items())},
                        "q1_by_year": {y: sum(c.values()) for y, c in sorted(comp_y.items())},
                        "composition_total": dict(sorted(comp.items(), key=lambda kv: -kv[1])),
                        "composition_share": {k: round(v / max(1, n_q1), 4) for k, v in sorted(comp.items(), key=lambda kv: -kv[1])},
                        "composition_by_year": {y: dict(sorted(c.items(), key=lambda kv: -kv[1])) for y, c in sorted(comp_y.items())},
                        "cur_len_bucket_total": {b[2]: lens.get(b[2], 0) for b in LEN_BUCKETS},
                        "cur_len_bucket_by_year": {y: {b[2]: c.get(b[2], 0) for b in LEN_BUCKETS} for y, c in sorted(len_y.items())},
                        "min_len_bucket_total": {b[2]: minlen.get(b[2], 0) for b in LEN_BUCKETS},
                        "q1_cur_le50": lens.get("<=50", 0), "q1_cur_le50_share": round(lens.get("<=50", 0) / max(1, n_q1), 4),
                        "q1_either_le50": minlen.get("<=50", 0),
                        "ch_active_stage_m": {"median": st_.median(ch), "min": min(ch), "min_month": months[ch.index(min(ch))],
                                              "max": max(ch), "n_months": len(ch),
                                              "by_year_median_min": {y: [st_.median(v), min(v)] for y, v in sorted(byy.items())}},
                        "eg_top30_replacements": {"median_all_rebalances": st_.median(rep_), "min": min(rep_), "max": max(rep_),
                                                  "n": len(rep_), "median_stage_m_rebalances": st_.median(rep_m) if rep_m else None,
                                                  "min_stage_m": min(rep_m) if rep_m else None, "n_stage_m": len(rep_m),
                                                  "zero_rebalances": sum(1 for v in rep_ if v == 0),
                                                  "by_rebalance": dict(zip(sorted(top), rep_))}}
        res["versions"][ver] = V_
    IM._wj_stable(R2C, res, indent=1)              # 내용이 같으면 generated 를 그대로(2026-09-26)
    for ver, V_ in res["versions"].items():
        for rule, x in V_.items():
            print("%-4s %-22s Q1 %5d · BB %4s · ≤50 %4d · CH 중앙 %s 최소 %s · Eg30 교체 중앙 %s(Stage M %s) 최소 %s" % (
                ver, rule, x["n_q1"], x["composition_total"].get("B-B", 0), x["q1_cur_le50"], x["ch_active_stage_m"]["median"],
                x["ch_active_stage_m"]["min"], x["eg_top30_replacements"]["median_all_rebalances"],
                x["eg_top30_replacements"]["median_stage_m_rebalances"], x["eg_top30_replacements"]["min"]))


# ════════════════════════════════════════════════════════════════════════
def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    fn = {"check": cmd_check, "list": cmd_list, "fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build,
          "vsample": cmd_vsample, "vview": cmd_vview, "vscore": cmd_vscore, "xdoc": cmd_xdoc, "r2comp": cmd_r2comp,
          "repin": cmd_repin}.get(cmd)
    if fn is None:
        print(__doc__)
        return 2
    os.makedirs(RAW_T, exist_ok=True)
    fn(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
