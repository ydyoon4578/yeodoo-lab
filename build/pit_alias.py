# -*- coding: utf-8 -*-
"""build/pit_alias.py — 명단 티커 → 가격 키 **날짜 인식 별칭** 표를 두는 한 곳(배치 R · 2026-09-25).

왜 있나.
  pit_panel._key 는 «명단 티커 → 점 표기 → cik_spliced» 차례로 가격 키를 찾는다. cik_spliced 는
  data/pit_universe.json 의 한 칸인데 **pit_backtest.py 가 실행 때마다 새로 쓰는 산출물**이다
  (cik_aliases: index_history 의 cik·cik_hist 로 같은 CIK 의 다른 티커를 잇는다). 거기에 손으로 칸을
  보태면 다음 PIT 굽기가 지운다. 그리고 그 함수는 구조상 못 잇는 경우가 있다 —
  · cik_conflicts 에 걸린 CIK(PCLN/BKNG · DISCA/DISCK/WBD · IR/TT 는 «같은 달 함께 나온다» 로 막힌다)
  · 명단 티커 키에 **다른 증권** 값이 이미 있어 «그날 값이 선 첫 후보» 가 그것을 먼저 잡는 경우
    (IR: 2017-05-12 부터 Gardner Denver · SPLS·SNDK: 티커 재사용 · FOXA/FOX: 2019-03 부터 Fox Corp)
  · 위키 NDX 표의 오타(NXP ← NXPI · 2022-01..2024-05)
  그래서 사람이 확인한 별칭을 **코드에** 두고(pit_quarantine.py 와 같은 방식 — 명단을 여러 벌로 두지 않는다)
  pit_panel._key · pit_px_db2(사내 DB 채움의 목표 키) 가 이것을 먼저 본다.

규칙.
  · 별칭은 창(frm..to, 날짜 · 양끝 포함) 안에서 **이긴다** — 명단 티커 키에 값이 있어도 별칭 키를 쓴다
    (IR 2017-05..2020-02 가 그 경우다). 창 밖에서는 아무 일도 안 한다.
  · 🚨 2026-09-26 — 창 안인데 별칭 키에 계열이 **아예 없으면** 그 날은 «가격 키 없음»(pit_panel._key → None ·
    pit_px_db2.lab_val → 값 없음)이다. 명단 티커 키로 떨어지지 않는다 — 떨어지면 L1/L2 처럼 **다른 회사** 가격을 읽는다
    (DD@30554 · JCI@53669 · CB@20171 은 옛 회사 계열이 들어오기 전까지 결측이 맞다).
  · 날짜를 모르는 호출(i=None)에는 적용하지 않는다(종전 뜻 그대로).
  · dedup_cik(줄의 선택 칸) — 창 안에서 이중클래스 한 종 줄이기(pit_panel.union_members · month_rows)에 쓰는 CIK 를 이 줄의
    CIK 로 바꾼다. index_history 의 평면 CIK 가 인수자의 것이라 두 회사가 한 종으로 접히던 짝(JCI/TYC · CB/ACE)을 편다.
  · 키 «티커@CIK» 는 재사용 티커의 옛 증권 전용 키다(SPLS@791519 = Staples · SNDK@1000180 = 옛 SanDisk).
    pit_px_refresh 는 이 키를 받지 않는다(closed) — 야후에 물을 이름이 아니다.
  · 명단 고치기(LIST_FIX)는 pit_panel.load_world 의 월말 명단에만 건다(index_history.json 은 안 바꾼다).
  · 모든 줄은 §A0 발행사 지도(data/_issuer_map.json)의 그룹 · CIK 로 확인한다: python build/pit_alias.py --check

🚨 pit_backtest.py(게시 PIT)는 이 표를 **아직 읽지 않는다** — 그 엔진은 _pit_px_cache.json 과 자체 CIK 승계를 쓰고,
  QFWD 원장이 코드 핀으로 얼려 두었다. 붙이려면 그 파일의 CODE_REV 를 올리는 별도 변경이다.
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# t = 명단 티커(pit_panel.load_world 표기 — '.' 는 '-' 로 바뀌어 있다) · key = 가격 키 · to/frm = 날짜(포함)
# cik = 그 창의 발행사 CIK(§A0 지도 그룹의 주 CIK) · kind = 무엇을 고치나
ALIASES = [
    {"t": "DISCA", "key": "WBD", "frm": None, "to": "2022-04-08", "cik": 1437107, "kind": "rename",
     "why": "Discovery Series A → 2022-04-08 WarnerMedia 합병 뒤 Warner Bros. Discovery(WBD) · 같은 법인(CIK 1437107) · "
            "WBD 의 과거 계열이 곧 DISCA 계열이다. cik_conflicts(DISCA/DISCK/WBD)라 pit_backtest 승계가 안 잇는다."},
    {"t": "DISCK", "key": "WBD", "frm": None, "to": "2022-04-08", "cik": 1437107, "kind": "rename_class_approx",
     "why": "Discovery Series C → 합병 때 WBD 1:1. 🚨 근사: C 주를 A 주(WBD 과거 = DISCA) 가격으로 잰다 — C 는 A 보다 "
            "몇 % 싸게 거래됐다(의결권 없음). 같은 회사라 수익은 거의 같지만 수준은 다르다. 이중클래스는 회사당 하나라 "
            "union_members 는 DISCA 를 남기므로 이 줄은 DISCK 만 명단에 있는 달(없다)이나 이중클래스를 안 줄이는 읽는 곳에만 닿는다."},
    {"t": "PCLN", "key": "BKNG", "frm": None, "to": "2018-02-28", "cik": 1075531, "kind": "rename",
     "why": "Priceline Group → 2018-02-27 Booking Holdings(BKNG) 개명 · 같은 법인(CIK 1075531). NDX 명단은 2018-02 월말까지 "
            "PCLN 으로 적는다(개명 시차) — 그래서 창 끝이 02-28 이다. 랩 키 PCLN 은 2025-10-16 부터 다른 증권(재사용)이다."},
    {"t": "TSO", "key": "ANDV", "frm": None, "to": "2017-07-31", "cik": 50104, "kind": "rename",
     "why": "Tesoro → 2017-08-01 Andeavor(ANDV) 개명 · 같은 법인(CIK 50104) · 랩 ANDV 계열(2009~2018-10)이 Tesoro 이력을 담는다."},
    {"t": "FOXA", "key": "TFCFA", "frm": None, "to": "2019-03-12", "cik": 1308161, "kind": "reuse_ticker",
     "why": "21st Century Fox 클래스 A(CIK 1308161) — 2019-03-13 티커를 TFCFA 로 바꾸고 03-20 Disney 가 인수. 티커 FOXA 는 "
            "2019-03 부터 Fox Corp(CIK 1754301 · 랩 sd/FOXA 는 2019-03-12 부터). 21CF 시절 값은 사내 DB 종가를 TFCFA 키에 둔다."},
    {"t": "FOX", "key": "TFCF", "frm": None, "to": "2019-03-12", "cik": 1308161, "kind": "reuse_ticker",
     "why": "21st Century Fox 클래스 B(CIK 1308161) — FOXA 와 같다(TFCF 로 바꾼 뒤 Disney 인수 · FOX 는 Fox Corp 가 이어받음)."},
    {"t": "IR", "key": "TT", "frm": None, "to": "2020-02-29", "cik": 1466258, "kind": "reuse_ticker",
     "why": "옛 Ingersoll-Rand plc(CIK 1466258) → 2020-03-02 Trane Technologies(TT)로 개명 · 같은 증권. 티커 IR 은 2020-03 부터 "
            "Ingersoll Rand Inc.(옛 Gardner Denver · CIK 1699150)이고 랩 sd/IR 은 그 계열(2017-05-12 상장~)이라 "
            "2017-05..2020-02 에 명단 IR 이 다른 회사 가격으로 잡혔다(2019-08-30 IR 27.51 · TT 85.2)."},
    {"t": "SPLS", "key": "SPLS@791519", "frm": None, "to": "2017-09-12", "cik": 791519, "kind": "reuse_datekey",
     "why": "Staples(CIK 791519 · 2017-09-12 Sycamore 비공개화). 랩 키 SPLS 는 2026-08-10 부터 다른 증권(재사용)이라 "
            "Staples 값(사내 DB · NDX 2014-06..2015-12)은 날짜 인식 키에 둔다."},
    {"t": "SNDK", "key": "SNDK@1000180", "frm": None, "to": "2016-05-12", "cik": 1000180, "kind": "reuse_datekey",
     "why": "옛 SanDisk(CIK 1000180 · 2016-05-12 WDC 인수). 오늘 SNDK 는 2025 WDC 분사 Sandisk(CIK 2023554 · sd) — "
            "옛 값(사내 DB · NDX 2014-06..2016-03)은 날짜 인식 키에 둔다."},
    {"t": "UA", "key": "UAA", "frm": None, "to": "2016-12-06", "cik": 1336917, "kind": "class_rename",
     "why": "Under Armour 클래스 A 는 2016-12-07 까지 티커 UA · 그 뒤 UAA(랩 UAA 계열 2009~). 랩 키 UA 는 클래스 C"
            "(2016-03-23~)라 2016-12-06 까지의 명단 UA 는 UAA 로 읽어야 같은 증권이다."},
    {"t": "UA-C", "key": "UA", "frm": None, "to": "2016-12-06", "cik": 1336917, "kind": "class_rename",
     "why": "Under Armour 클래스 C 는 2016-04~12-06 티커 UA.C · 12-07 부터 UA(랩 키 UA = 클래스 C). cik_spliced 의 "
            "UA.C → UAA(클래스 A)보다 맞는 증권이다. (별도로 pit_panel._key 가 cik_spliced 를 '-' 표기로만 찾아 "
            "'UA.C' 칸을 못 찾던 결함도 고쳤다.)"},
    # ── 2026-09-26 — 편출 가격 보관소(공개 데이터셋 스테이징)의 제안 줄 · 재사용 가드가 붙든 키 · 랩 문제 L1/L2 ────────────
    # 격리 이름의 날짜 인식 키(U4) — 랩 키 PARA · COL 은 격리(pit_quarantine: 편입 기간 값이 다른 증권)라 쓰지 않고, 관문을
    # 통과한 공개 데이터셋 계열을 옛 증권 전용 키에 둔다(SPLS@791519 선례). 값은 병합 단계(--merge-stage)로 들어온다.
    {"t": "COL", "key": "COL@1137411", "frm": None, "to": "2018-11-30", "cik": 1137411, "kind": "reuse_datekey",
     "why": "Rockwell Collins(CIK 1137411 · 2018-11-26 United Technologies 인수). 랩 키 COL 은 격리 — 편입 기간 가격이 "
            "0.01~1.80달러(다른 증권)였다. 공개 데이터셋(NYSE-dgawlik · S&P 500 5년) 계열을 날짜 인식 키에 둔다."},
    {"t": "PARA", "key": "PARA@813828", "frm": None, "to": "2025-07-31", "cik": 813828, "kind": "reuse_datekey",
     "why": "Paramount Global(CIK 813828 · 2025-08-07 Skydance 합병 → Paramount Skydance PSKY). 랩 키 PARA 는 격리 — "
            "편입 기간 계열이 57.80~113,900 으로 뛰는 다른 증권이었다. 창 끝 = 마지막 멤버 월말(2025-07-31) · 2025-07 "
            "보유월(8월) 값은 같은 키에서 읽는다(스테이징 절단 2025-08-06 과 짝)."},
    # A0 — 같은 CIK 의 개명(이미 게시 중인 랩 키 값을 그대로 읽는다 · 가격 사본 없음 · 창 끝 = 마지막 멤버 월말)
    {"t": "MHFI", "key": "SPGI", "frm": None, "to": "2016-04-29", "cik": 64040, "kind": "rename",
     "why": "McGraw Hill Financial → 2016-04-28 S&P Global(SPGI) 개명 · 같은 법인(CIK 64040 · §A0 그룹 g64040)."},
    {"t": "NU", "key": "ES", "frm": None, "to": "2015-01-30", "cik": 72741, "kind": "rename",
     "why": "Northeast Utilities → 2015-02 Eversource Energy(ES) 개명 · 같은 법인(CIK 72741 · §A0 그룹 g72741)."},
    {"t": "WLP", "key": "ELV", "frm": None, "to": "2014-11-28", "cik": 1156039, "kind": "rename",
     "why": "WellPoint → 2014-12 Anthem(ANTM) → 2022-06 Elevance Health(ELV) 개명 · 같은 법인(CIK 1156039 · §A0 그룹 g1156039) · "
            "랩 ELV 계열(야후)이 WellPoint 이력을 담는다."},
    {"t": "ZMH", "key": "ZBH", "frm": None, "to": "2015-05-29", "cik": 1136869, "kind": "rename",
     "why": "Zimmer Holdings → 2015-06 Zimmer Biomet(ZBH) 개명 · 같은 법인(CIK 1136869 · §A0 그룹 g1136869)."},
    # 재사용 가드(V8 · pit_px_db2 G7)가 붙든 키 — 랩 키에는 뒤에 다른 증권 값이 있어 옛 증권 값은 날짜 인식 키에 둔다.
    # 창 끝 = 그 티커가 옛 증권을 뜻한 마지막 날(인수 · 파산은 마지막 거래일 · 개명은 개명 뒤에도 같은 증권이라 보유월 끝).
    # 값은 병합 단계로 들어온다(그 전에는 이 키가 없어 _key 가 None — 다른 증권으로 떨어지지 않는다).
    {"t": "DOW", "key": "DOW@29915", "frm": None, "to": "2017-08-31", "cik": 29915, "kind": "reuse_datekey",
     "why": "Dow Chemical(CIK 29915) — 2017-08-31 DuPont 과 합병 → DowDuPont(DWDP · 2017-09-01 거래 시작). 티커 DOW 는 "
            "2019-03-20 분사 Dow Inc(CIK 1751788 · 랩 sd/DOW)가 다시 쓴다."},
    {"t": "APC", "key": "APC@773910", "frm": None, "to": "2019-08-08", "cik": 773910, "kind": "reuse_datekey",
     "why": "Anadarko Petroleum(CIK 773910) — 2019-08-08 Occidental 인수 완료. 랩 키 APC 는 2026-08 부터 다른 증권 값이다."},
    {"t": "NFX", "key": "NFX@912750", "frm": None, "to": "2019-02-13", "cik": 912750, "kind": "reuse_datekey",
     "why": "Newfield Exploration(CIK 912750) — 2019-02-13 Encana 인수 완료. 랩 키 NFX 는 2026-08 부터 다른 증권 값이다."},
    {"t": "INFO", "key": "INFO@1598014", "frm": None, "to": "2022-02-28", "cik": 1598014, "kind": "reuse_datekey",
     "why": "IHS Markit(CIK 1598014) — 2022-02-28 S&P Global 합병 완료. 랩 키 INFO 는 2024-10 부터 다른 증권 값이다."},
    {"t": "STI", "key": "STI@750556", "frm": None, "to": "2019-12-06", "cik": 750556, "kind": "reuse_datekey",
     "why": "SunTrust Banks(CIK 750556) — 2019-12-06 BB&T 와 합병(Truist · TFC 는 12-09 부터). 랩 키 STI 는 2022-05 부터 "
            "다른 증권 값이다."},
    {"t": "Q", "key": "Q@1478242", "frm": None, "to": "2017-11-30", "cik": 1478242, "kind": "reuse_datekey",
     "why": "Quintiles IMS(CIK 1478242) — 2017-11-06 IQVIA(IQV)로 개명 · 같은 증권이 계속 거래되므로 창을 보유월(2017-11) 끝까지 "
            "둔다. 티커 Q 는 2025-11 부터 Qnity Electronics(CIK 2058873 · 랩 sd/Q)다."},
    {"t": "SBNY", "key": "SBNY@1288784", "frm": None, "to": "2023-03-10", "cik": 1288784, "kind": "reuse_datekey",
     "why": "Signature Bank(CIK 1288784 · FDIC 제출 은행) — 2023-03-12 규제당국 폐쇄 · 마지막 거래일 03-10. 랩 키 SBNY 는 "
            "2024-08 부터 다른 증권 값이다."},
    {"t": "ACT", "key": "ACT@1578845", "frm": None, "to": "2015-06-30", "cik": 1578845, "kind": "reuse_datekey",
     "why": "Actavis plc(CIK 1578845) — 2015-06-15 Allergan plc(AGN)로 개명 · 같은 증권이 계속 거래되므로 창을 보유월(2015-06) "
            "끝까지 둔다. 랩 키 ACT 는 2021-09 부터 다른 증권 값이다."},
    # 랩 문제 L1 · L2 — 인수자가 피인수 회사의 티커를 물려받아 벤더 계열이 **인수자 이력** 을 옛 티커 아래 싣는다.
    #   명단의 그 티커는 그 시절 피인수 회사다. 날짜 인식 키로 가르고, 옛 회사 계열이 없으면 그 달들은 결측이다
    #   (다른 회사 가격으로 채우지 않는다). dedup_cik = 이중클래스 한 종 줄이기에 쓰는 CIK(아래 dedup_cik_at) —
    #   index_history 의 평면 CIK 가 인수자의 것이라 두 회사가 한 종으로 접히던 짝(JCI/TYC · CB/ACE)을 편다.
    {"t": "DD", "key": "DD@30554", "frm": None, "to": "2017-08-31", "cik": 30554, "kind": "reuse_datekey",
     "why": "L1 — 2014-06..2017-08 의 명단 DD 는 E.I. du Pont(CIK 30554). 랩 키 DD(야후 DD)의 그 시절 계열은 Dow Chemical 이다 — "
            "NYSE-dgawlik(CC0) DOW 와 일간 수익 상관 0.998 · DD 와 0.713, 2015-07-01 Chemours 분사(NYSE DD −3.9%)가 없고 "
            "배당이 Dow 의 분기 0.37/0.42/0.46. E.I. du Pont 계열은 공개 데이터셋 NYSE-dgawlik DD(CC0 · 2010-01..2016-12)에서 "
            "병합 단계로 이 키에 들어온다(그 전과 2017-01..08 — 허용 소스 없음 — 은 결측)."},
    {"t": "JCI", "key": "JCI@53669", "frm": None, "to": "2016-09-01", "cik": 53669, "kind": "reuse_datekey", "dedup_cik": True,
     "why": "L2 — 2014-06..2016-08 의 명단 JCI 는 옛 Johnson Controls Inc(CIK 53669). 벤더의 JCI 계열은 그 시절 Tyco 의 것이다"
            "(2016-09-06 955:1000 주식 병합 · 분기 배당 0.18/0.205 · 1·4·7·10월 주기). 옛 JCI 계열은 허용 소스에 없어 그 달들은 "
            "결측이다. TYC(Tyco)는 index_history CIK 833444 를 JCI 와 같이 써 한 종으로 접혔다 — dedup_cik 로 편다."},
    {"t": "CB", "key": "CB@20171", "frm": None, "to": "2016-01-14", "cik": 20171, "kind": "reuse_datekey", "dedup_cik": True,
     "why": "L2 — 2014-06..2015-12 의 명단 CB 는 옛 Chubb Corp(CIK 20171). 벤더의 CB 계열은 그 시절 ACE Ltd 의 것이다"
            "(분기 배당 0.63~0.68 · 2015-07-01 인수 발표일 +0.8%). 옛 Chubb 계열은 허용 소스에 없어 그 달들은 결측이다. "
            "ACE 는 index_history CIK 896159 를 CB 와 같이 써 한 종으로 접혔다 — dedup_cik 로 편다."},
    {"t": "ACE", "key": "CB", "frm": None, "to": "2016-01-14", "cik": 896159, "kind": "rename",
     "why": "위 줄의 짝(2026-09-26 검토 지적) — 2014-06..2015-12 의 명단 ACE 는 ACE Ltd(CIK 896159). 2016-01-14 Chubb Corp 인수를 "
            "마치고 Chubb Limited 로 개명 · 2016-01-15 부터 티커 CB · 같은 법인. 랩 키 CB(야후 CB)의 2016-01-14 전 계열이 곧 ACE "
            "자신의 계열이다(NYSE-dgawlik 'CB' 2015-06-30 101.68 = ACE · 배당을 넣으면 랩 CB 수익과 맞는다). 명단 CB 는 그 창에서 "
            "CB@20171(옛 Chubb · 계열 없음)로 가므로 한 키를 두 명단 티커가 읽지 않는다. 본 창(2016-08~) 앞이라 T 와 무관."},
]

# 명단 고치기 — pit_panel.load_world 가 월말 명단을 만든 뒤 건다(이월 전 원 명단의 그달에만).
LIST_FIX = [
    {"ix": "ndx", "frm": "2022-01", "to": "2024-05", "bad": "NXP", "good": "NXPI", "cik": 1413447,
     "why": "위키 NASDAQ-100 표가 2022-01..2024-05 에 NXP Semiconductors 를 'NXP' 로 적었다(그 달들 NDX 명단에 NXPI 가 없고 "
            "앞뒤 달은 NXPI). 랩 가격 키 'NXP' 는 다른 증권(2023-06-30 12.61 · NXPI 193.13)이고 §A0 지도는 NXP 를 NXPI 와 같은 "
            "그룹(g1413447 · 수작업 줄)으로 둔다. 빼지 않고 이름을 바로잡는다 — 빼면 NDX 만 쓰는 패널이 실제 멤버 하나를 잃는다."},
    # 2026-09-26 — 랩 문제 L5: 위키 표기 ANSYS · KLA 는 ANSS · KLAC 의 별표기다(같은 §A0 그룹 · 가격 키를 만들지 않는다).
    #   같은 달 다른 지수 명단에 바른 표기가 있으면 합집합이 한 회사를 두 번 센다.
    {"ix": "spx", "frm": "2019-01", "to": "2019-03", "bad": "ANSYS", "good": "ANSS", "cik": 1013462,
     "why": "위키 S&P 500 표가 2019-01..03 에 ANSYS Inc 를 'ANSYS' 로 적었다(앞뒤 달은 ANSS · §A0 그룹 g1013462)."},
    {"ix": "ndx", "frm": "2019-12", "to": "2021-01", "bad": "ANSYS", "good": "ANSS", "cik": 1013462,
     "why": "위키 NASDAQ-100 표가 2019-12..2021-01 에 'ANSYS' 로 적었다 — 같은 달 S&P 500 명단의 ANSS 와 한 회사(g1013462)."},
    {"ix": "ndx", "frm": "2022-01", "to": "2022-05", "bad": "KLA", "good": "KLAC", "cik": 319201,
     "why": "위키 NASDAQ-100 표가 2022-01..05 에 KLA Corp 를 'KLA' 로 적었다 — 같은 달 S&P 500 명단의 KLAC 와 한 회사(g319201)."},
]


def key_at(t, d):
    """명단 티커 t 의 날짜 d('YYYY-MM-DD') 별칭 키 — 창 밖이면 None."""
    if not d:
        return None
    for a in ALIASES:
        if a["t"] == t and (a["frm"] is None or d >= a["frm"]) and d <= a["to"]:
            return a["key"]
    return None


def dedup_cik_at(t, d):
    """명단 티커 t 의 날짜 d 에서 한 종 줄이기에 쓸 CIK(10자리 문자열) — dedup_cik 줄의 창 안일 때만 · 아니면 None."""
    if not d:
        return None
    for a in ALIASES:
        if a["t"] == t and a.get("dedup_cik") and (a["frm"] is None or d >= a["frm"]) and d <= a["to"]:
            return "%010d" % int(a["cik"])
    return None


def by_key():
    """가격 키 → 그 키로 가는 별칭 줄 목록."""
    out = {}
    for a in ALIASES:
        out.setdefault(a["key"], []).append(a)
    return out


def fix_lists(lists, months=None):
    """{'spx': {월: [티커]}, 'ndx': {...}} 를 제자리에서 고친다(티커는 '-' 표기). 고친 칸 수를 돌려준다.

    이월된 달(원 명단이 빈 달)도 고친다 — 이월은 직전 달 명단의 사본이라 같은 오타를 옮겨 온다."""
    n = 0
    for f in LIST_FIX:
        rows = lists.get(f["ix"]) or {}
        for m in list(rows):
            if not (f["frm"] <= m <= f["to"]):
                continue
            lst = rows[m]
            if f["bad"] not in lst:
                continue
            new = [x for x in lst if x != f["bad"]]
            if f["good"] not in new:
                new.append(f["good"])
            rows[m] = new
            n += 1
    return n


# ── 확인(§A0 지도 · 가격 기록) ──────────────────────────────────────────────────────────────────
def _mprev(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return "%04d-%02d" % (y - (m == 1), 12 if m == 1 else m - 1)


def _tm_rows(tm, t):
    return tm.get(t) or tm.get(t.replace("-", ".")) or []


def check(data=DATA, say=print):
    """모든 별칭 · 명단 고치기를 §A0 발행사 지도 그룹 · CIK 로 확인한다. 실패 목록을 돌려준다(빈 목록 = 통과)."""
    p = os.path.join(data, "_issuer_map.json")
    if not os.path.exists(p):
        return ["§A0 지도 %s 가 없다 — 확인할 수 없다" % p]
    M = json.load(io.open(p, encoding="utf-8"))
    tm, G = M.get("tm") or {}, M.get("groups") or {}
    bad = []
    for a in ALIASES:
        # 지도는 월말 단위다 — 월말(근사: 그달 28일)이 창 안인 달만 본다(FOXA 2019-03 월말은 이미 Fox Corp 다)
        m0 = (a["frm"] or "0000-00-00")[:7]
        m1 = a["to"][:7] if (a["to"][:7] + "-28") <= a["to"] else _mprev(a["to"][:7])
        rows = []
        for r in _tm_rows(tm, a["t"]):
            lo, hi = max(r[0], m0), min(r[1], m1)
            if lo <= hi:
                rows.append(r)
        if not rows:
            bad.append("%s: 창 %s..%s 에 §A0 지도 줄이 없다" % (a["t"], m0, m1))
            continue
        grp = {r[2] for r in rows}
        ciks = set()
        for r in rows:
            ciks |= set(r[4] or [])
        ok_cik = a["cik"] in ciks
        # 목표 키가 명단 티커이기도 하면 그 키의 그룹이 같아야 한다(시기는 따지지 않는다 — 개명 뒤에만 명단에 있다)
        kt = a["key"].split("@")[0] if "@" in a["key"] else a["key"]
        if "@" in a["key"]:
            ok_key = int(a["key"].split("@")[1]) == a["cik"]
            kgrp = {"(키 CIK %s)" % a["key"].split("@")[1]}
        else:
            krows = _tm_rows(tm, kt)
            kgrp = {r[2] for r in krows}
            ok_key = bool(kgrp & grp)
        line = "%-5s → %-13s ~%s  지도 그룹 %s · CIK %s 가 창의 CIK 집합에 %s · 목표 키 그룹 %s %s" % (
            a["t"], a["key"], a["to"], ",".join(sorted(grp)), a["cik"], "있다" if ok_cik else "없다",
            ",".join(sorted(kgrp)) or "-", "일치" if ok_key else "불일치")
        say("  " + ("✅ " if (ok_cik and ok_key and len(grp) == 1) else "❌ ") + line)
        if not (ok_cik and ok_key and len(grp) == 1):
            bad.append(line)
    for f in LIST_FIX:
        rb = [r for r in _tm_rows(tm, f["bad"]) if not (r[1] < f["frm"] or r[0] > f["to"])]
        rg = _tm_rows(tm, f["good"])
        gb, gg = {r[2] for r in rb}, {r[2] for r in rg}
        ok = bool(gb) and gb <= gg and any(f["cik"] in (r[4] or []) for r in rb)
        line = "명단 %s %s..%s: %s → %s  그룹 %s / %s" % (f["ix"].upper(), f["frm"], f["to"], f["bad"], f["good"],
                                                   ",".join(sorted(gb)) or "-", ",".join(sorted(gg)) or "-")
        say("  " + ("✅ " if ok else "❌ ") + line)
        if not ok:
            bad.append(line)
    return bad


def coverage(data=DATA, say=print):
    """별칭 창 안 명단 월말마다 목표 키에 값이 서나 · 별칭 없이 잡히던 키와 값(비교) — 보고용."""
    S = json.load(io.open(os.path.join(data, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    today = {s["t"] for s in S["stocks"]}
    P = json.load(io.open(os.path.join(data, "pit_px.json"), encoding="utf-8"))
    if P.get("dates") != dates:
        say("  ⚠ pit_px.json 격자 ≠ pxd_dates — 값 대조를 건너뛴다")
        return {}
    D = len(dates)

    def ser(k):
        if k in today:
            a = json.load(io.open(os.path.join(data, "sd", k + ".json"), encoding="utf-8")).get("pxd") or []
            return a if len(a) == D else [None] * D
        o = (P.get("px") or {}).get(k)
        a = [None] * D
        if o:
            for j, v in enumerate(o.get("p") or []):
                if 0 <= o["i0"] + j < D:
                    a[o["i0"] + j] = v
        return a

    H = json.load(io.open(os.path.join(data, "index_history.json"), encoding="utf-8"))
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    out = {}
    for a in ALIASES:
        ks = ser(a["key"])
        own = ser(a["t"]) if (a["t"] in today or a["t"] in (P.get("px") or {})) else [None] * D
        n = hit = diff = 0
        ex = None
        for m in sorted(H.get("months") or {}):
            row = H["months"][m] or {}
            mem = {x.replace(".", "-") for ix in ("spx", "ndx") for x in (row.get(ix) or [])}
            if a["t"] not in mem or m not in me:
                continue
            i = me[m]
            if dates[i] > a["to"] or (a["frm"] and dates[i] < a["frm"]):
                continue
            n += 1
            if ks[i] is not None:
                hit += 1
            if own[i] is not None and ks[i] is not None and abs(own[i] / ks[i] - 1) > 0.02:
                diff += 1
                ex = ex or (dates[i], own[i], ks[i])
        out[a["t"]] = {"key": a["key"], "member_months_in_window": n, "key_priced": hit,
                       "own_key_priced_but_different": diff, "example_own_vs_alias": ex}
        say("  %-5s → %-13s 창 안 멤버 월말 %3d · 별칭 키 값 %3d · 명단 티커 키가 다른 값 %3d %s"
            % (a["t"], a["key"], n, hit, diff, ("(예 %s %s 대 %s)" % ex) if ex else ""))
    return out


if __name__ == "__main__":
    if "--check" in sys.argv:
        print("§A0 발행사 지도 대조 — 별칭 %d줄 · 명단 고치기 %d줄" % (len(ALIASES), len(LIST_FIX)))
        b = check()
        print("가격 기록 대조(별칭 창 안 월말):")
        coverage()
        print("✅ 통과" if not b else "❌ %d건 불일치" % len(b))
        raise SystemExit(1 if b else 0)
    print(__doc__)
