# -*- coding: utf-8 -*-
"""build/r_r2flags.py — 배치 R · R2-LAZYRF «10-Q 위험요인 분기 대비 대규모 개정» 표지(CH_active) + R5-ALARM 경보 사건 세기.

카드 원문 scratchpad/rbatch_research.json «final» — slate R2-LAZYRF(rule (2)~(8) · params) · R5-ALARM(rule (a)(b) · params) ·
data_build_plan §A0(발행사 그룹) · §B(submissions 패널 필드) · §C(10-Q 특징 필드) · §D(R5 사건 목록).

무엇을·왜.
  R2 — 경영진은 위험요인 절(Part II Item 1A)을 거의 그대로 베껴 쓴다. 크게 고쳐 쓴 분기의 새 문장은 대개 나쁜 소식이고 시장은 그것을
    읽지 않는다(CMN «Lazy Prices» 표 A-15: 10-Q 위험요인 직전 분기 대비 · 전년도 분포 5분위 · 다음 달 진입 3개월 보유 · Q1 −0.80%/월).
    롱온리는 «바꾼 회사를 빼는» 단계로만 쓴다. 이 파일은 그 표지 한 벌을 만든다 — 짝 짓기 · 형태 전환 결측 · 전년도 하위 20% 경계 ·
    CH_active(t−2..t) · 결측 더미 · Δlog(1A 단어수) 통제 값 · SimDoc 대조 판.
  R5 — 정기보고 지연(NT 10-K/Q) · 재무제표 신뢰 불가(4.02) · 감사인 사임(4.01) · 상장유지 경고(3.01) 는 직전 12개월,
    파산·채무 가속·구조조정·중대 손상·지배권 변경(1.03 · 2.04 · 2.05 · 2.06 · 5.01) 은 직전 90일 — 걸린 이름-월을 센다.
    표본 안에서는 사건 수와 업종 분포만 센다(카드: 수익을 재지 않으므로 시도 수에 더하지 않는다).

🚨 이 모듈은 어떤 표지와 수익의 관계도 계산하지 않는다 — 가격 · 수익을 읽지 않는다(--dry 의 달력 감사가 stocks.json 의 날짜 칸만 본다).
   γ · 분위 수익 · 적중률은 등록 뒤 한 번 굽기(§E rbatch_mech · rbatch_run)의 몫이다. 여기서는 합성 시험과 구성 점검(개수 · 비율)만 한다.

R2 규칙(카드 그대로 · 미리 고정).
  문서   = 10-Q 원본만(form == '10-Q' · /A 제외). 가용일 = acceptanceDateTime(UTC) 을 ET 로 바꿔 마감(16:00) 이후 접수면 다음 NYSE
           거래일, 휴장일 접수도 다음 거래일. 공개월 = 가용일이 속한 달.
  짝     = 같은 발행사 그룹의 «바로 앞» 10-Q 원본(reportDate 순) — reportDate 가 70~200일 앞선 것만. 1분기 10-Q 의 바로 앞 10-Q 는
           전년 3분기 10-Q 다(4분기는 10-K 라 문서 집합에 없다 · 간격 약 182일). 52/53주 회계연도의 53주 해에 12-12-12-16 달력을 쓰는
           곳(COST 2023-05-07→11-26 · PEP 2022-09-03→2023-03-25 · KR 2023-11-04→2024-05-25 = 203일)은 창 밖 = 구조적 결측이다 —
           창은 카드 고정이라 바꾸지 않고 r2_density 가 연도별 gap_201_210 으로 센다. 바로 앞이 창 밖이면 짝 없음이다
           (더 앞 문서로 건너뛰지 않는다).
  형태   = B(상용구만 · 정규식 적중 & 150단어 미만) · U(상용구 + 갱신 · 적중 & 150 이상) · F(전문 · 첫 200단어에 적중 없음 & 500 이상) ·
           적중 없음 & 500 미만 = 분리 실패. 한쪽 F · 다른 쪽 B/U = «형태 전환» → 결측. B-B · U-U · B-U · U-B · F-F 는 그대로 비교.
  SimRF  = 단어빈도 코사인(CMN Sim_Cosine). 전처리(소문자 · 숫자 → '#' · 두 글자 이상 알파벳 토큰)는 tokens() — HTML 정리(ix:header ·
           숨김 div · 숫자 표)는 §C 빌더 몫이다.
  Q1     = 직전 달력연도에 공개된(가용일 기준) 세계 전체 유효 짝의 SimRF 하위 20% 경계(np.quantile · linear)보다 **낮으면**(<).
  CH_active(g, t) = 공개월 t−2..t 의 10-Q 가운데 Q1 이 하나라도 있으면 1(A-15 «다음 달 진입 · 3개월 보유» — r_{t+1} 에 건다).
  MISS(g, t)      = CH = 0 이고 그 창에 점수를 못 매긴 10-Q(분리 실패 · 짝 없음 · 형태 전환 · 경계 없음 …)가 하나라도 있으면 1.
                    창에 10-Q 가 없으면 CH = MISS = 0(정보 없음 — 결측이 아니다). FPI 는 10-Q 가 없으니 결측으로 세지 않는다.

랩 선택(선언 — 카드에 문구가 없는 구현 세부).
  ① 같은 그룹 같은 reportDate 의 10-Q 원본이 둘 이상이면(선행·후계 CIK 동시 제출 · 원본 재제출) 하나만 남기고 나머지는 센다
     (dup_period · CIK 가 다르면 dup_period_xcik 도 · r2_density 가 목록을 싣는다). 남기는 순서: 그달 issuer_map 주 CIK(tm) →
     직전 정본 문서와 같은 CIK(연속 — 동시 효력 CIK 가 분기마다 번갈아 뽑혀 «다른 발행사끼리의 짝» 이 되는 것을 막는다 ·
     ONEOK 1039684/74154 · TMUS · ESRX) → 먼저 가용 → 접수 시각(ET) → accession. §C 빌더는 «먼저 가용» 만 쓴다 — 두 CIK 가
     갈리는 드문 경우 빌더 대조(⑯)에 불일치로 보인다(등록 전 결정 사항).
  ② 바로 앞 짝이 현재 문서보다 늦게 가용하면(늦은 제출) 결측(prior_late · §C 빌더와 같은 규칙). 🚨 이 판정은 현재 문서 가용일
     «뒤» 의 정보(앞 분기 10-Q 가 나중에 나왔다는 사실)를 쓴다 — 가용 시점의 시점정확 짝은 더 앞 문서(3분기 대 1분기 같은
     건너뛰기)라 카드의 «바로 앞» 비교가 아니므로 점수를 매기지 않는다. 닿는 곳은 결측 더미(MISS)뿐이고 CH=1 을 만들지는 않는다
     (다만 건너뛰기 짝이었다면 났을 CH 를 지울 수는 있다 · 연도별 miss_prior_late 로 센다 · 등록 전 결정 사항).
  ③ 조기폐장일(refresh_events._half_days)의 마감은 13:00 — «마감 뒤 접수는 다음 거래일» 의 뜻을 지킨다(월말 형성일이 추수감사절
     다음날인 해가 있다 · 2019-11-29 · 2024-11-29).
  ④ 발행사 그룹의 CIK 효력 구간(_issuer_map groups.ciks)을 «제출월»(filingDate 의 달 · 없으면 접수 ET 날짜의 달 · 그것도 없으면
     가용월)에 건다 — §C 빌더(cmd_list)와 같은 달. 가용월로 걸면 효력 끝 달 말일 마감 뒤 제출이 다음 달로 밀려 그룹을 잃는다.
  ⑤ SimDoc 대조(TXT2 10-Q 판)는 같은 짝 규칙(바로 앞 · 70~200일 · prior_late)을 쓰고 1A 형태 규칙은 걸지 않는다(문서 전체 척도).
  ⑥ Δlog(1A 단어수) 통제 값 = 창 안 가장 최근 유효 짝의 log(n_rf) − log(n_rf_prev) · 없으면 0.
  ⑦ 경계 분포의 «세계»(짝의 공개월 기준) = 호출자 세계 ∩ §C 빌더의 in_world(그달 비금융 멤버 · 2014-06 부터). 호출자 세계가
     집합이면 그 집합이 덮는 달에서만 판정하고, 덮지 않는 달(신호월만 담은 세계의 2016-08 이전 등)은 in_world 로 · 그것도
     없으면 자료 전체(§C 가 세계 비금융 그룹만 받는다)로 둔다 — 세계가 신호월만 덮으면 첫해 경계가 없고 둘째 해 경계가
     한 해의 일부(1분기 짝 없는 8~12월)로만 서던 결함을 막는다. 경계 연도마다 출처별 짝 수(src)와 호출자 세계가 덮은 달 수
     (world_months)를 bounds 에 싣는다. 호출 가능한 world 는 모든 달을 덮는다고 본다(.months 속성이 있으면 그 달만).
  ⑧ 접수 시각이 없는 기록은 빌더 가용일(avail_date) · 없으면 공시일(filingDate) 다음 거래일로 둔다(보수 · 개수를 센다).
     규칙 달력(2005~2031) 밖 날짜는 당기거나 멈추지 않고 버리고 센다(drop_out_of_cal).
  ⑧b (2026-09-26 · 등록 전 · 검토 지적 — 이 파일이 접수 시각으로 가용일을 다시 재서 §C 빌더의 filingDate 바닥 · 늦은 재접수 ·
     숨은 ET 규칙을 놓쳤고 짝 상태 2건이 빌더와 갈렸다) §C 기록에 빌더 가용일(avail)과 방법(avail_how)이 있으면 **빌더 가용일을
     쓴다**(다시 재지 않는다 · avail_builder). 방법이 acc(접수 시각 규칙)이고 접수 ET 가 조기폐장일 13:00 뒤 · 16:00 전이면
     ③ 만 위에 건다(빌더는 16:00 만 본다 → 다음 거래일 · avail_builder_half). 빌더 가용일이 이 달력의 거래일이 아니면 다음
     거래일로 굴리고 센다(avail_builder_not_td). 빌더 방법이 없는 기록(합성 · 옛 판)은 종전 규칙(접수 시각 → ③)이다.
  ⑭ reportDate 가 없는 10-Q 는 버리지 않고 사슬에 둔다(filingDate 자리 · «막이») — 그 문서와 그 다음 문서의 짝은 no_rd 결측
     (§C 빌더와 같은 규칙). 버리면 다음 분기가 더 앞 문서와 짝이 된다(3분기 대 1분기 183일 = 창 안 «건너뛰기»). 선택 입력
     tenk({그룹: [10-K · 10-KT reportDate]} · §B 에서 tenk_from_sub)를 주면 120일 넘는 짝은 두 reportDate 사이에 10-K 가
     있을 때만 유효하다(없으면 skip_suspect · 10-K 기록이 없는 그룹은 long_gap_unverified 로 센다).
  ⑮ 진단판(excl_ixbrl · excl_covid)의 경계는 본판(제외 없음)의 경계를 그대로 쓴다 — 제외는 그 짝만 결측(excluded)으로 바꾼다.
     제외한 짝이 다음 해 분포에서도 빠지면 «짝 제외의 효과» 에 «경계 이동» 이 섞인다.
  ⑯ 빌더 대조 — §C 의 pair_status(ok · no_prior · gap_out · prior_late · no_rd · cur_fail · prior_fail · shape_switch)와
     prev_acc 를 이 파일의 짝 판정과 대조해 센다(builder_ps:* · prev_acc_*). 불일치율 ≤ 1%(F_BUILDER_DISAGREE)는 랩 구성
     점검이다(카드 F0 아님 · r2_density checks).
  ⑰ F0 분리 실패율 = 경계 세계(⑦) 문서 가운데 받지 못한 것(fetch_* · unparsed)을 뺀 문서의 형태 없음 비율(§C 빌더 coverage 와
     같은 정의 · 등록 커밋에 이 정의로 고정). 받지 못한 문서 수는 unfetched · 옛 정의(전체 문서 분모)는 fail_rate_all_docs 로 따로.

R5 규칙(카드 그대로).
  (a) 형성일 d(월 m 의 마지막 NYSE 거래일) 기준 직전 12개월: NT 10-K · NT 10-Q · 8-K 4.02 · 8-K 4.01 중 사임/재선임 거부(본문 규칙) ·
      8-K 3.01.
  (b) 직전 90일: items 에 {1.03, 2.04, 2.05, 2.06, 5.01} 이 든 8-K 원본(2.02 와 같은 제출에 묶인 것 포함 · 8-K/A 제외).
  4.01 본문 규칙: 'resign' 또는 'declin(ed|es) to stand' → 사임 · 'dismiss' · 'not re-engaged' · 'selection process' → 정례 교체(빼지 않는다).
랩 선택(R5 · 선언).
  ⑨ 두 쪽이 다 걸리면 사임으로 본다('both' — «재선임을 거부했고 위원회가 선정 절차를 시작했다» 는 문장이 흔하다). 어느 쪽도 없으면
     빼지 않는다('none'). 본문이 없으면('no_text') 빼지 않고 센다 — 본문 수집 누락이 F0 에서 보이게.
  ⑩ 본문 규칙은 4.01 절(‘Item 4.01’ 머리 ~ 다음 항목 머리 앞)에만 건다 — 같은 8-K 의 5.02 임원 사임 문장이 섞이지 않게.
     다음 머리 = 4.01 이 아닌 ‘Item d.dd’ 가운데 본문 속 참조(바로 앞 낱말이 this · in · under · see … )가 아닌 첫 것
     («this Item 4.01» · «Item 4.01(b)» 에서 절이 잘리지 않게). 머리를 못 찾으면 본문 전체. 머리 찾음/못 찾음 · 절 길이 ·
     카드 정규식이 놓치는 문형 후보(«will decline to stand» · «would not stand for reappointment» — 카드 고정이라 판정엔 안 쓴다 ·
     등록 동결 전 결정)를 log 의 t401:* 로 센다.
  ⑪ (a) 의 NT · 8-K 도 정정본(/A)은 뺀다 — 같은 사건의 두 번째 공시라 창만 늘린다.
  ⑫ 12개월 창은 월 단위(가용월 m−11..m · 가용일 ≤ d · issuer_map F0 와 같은 셈), 90일 창은 달력일(d − 90 < 가용일 ≤ d).
  ⑬ 가용일은 R2 와 같은 규칙(접수 ET · 마감 뒤 다음 거래일) — 형성일 종가에 쓸 수 있었던 사건만 건다. 그룹은 ④ 와 같이 제출월로.
  ⑱ 중복 제거 = (그룹, accession) — 그룹을 먼저 정하고 센다. 공동 제출 8-K 가 지도 밖 자회사 CIK(PG&E 유틸리티 75488) ·
     효력 구간 밖 선행 CIK(TDCC 29915)로 먼저 와도 그룹 기록의 사건을 잃지 않는다(입력 순서 무관). 두 그룹이 같은 8-K 를
     내면 두 그룹 모두 사건이다.
  ⑲ 재편 서명(진단 · 1차 규칙은 카드 그대로) — 3.01 · 5.01 사건이 (3.03 또는 5.03) 과 (1.01 또는 2.01) 을 함께 싣거나('items'),
     같은 그룹 CIK 효력 구간의 시작/끝 달 ±1개월 안이면('splice') reorg 표지를 단다(지주사 재편 · 분할 · XOM 2026-07-01 ·
     DIS · XRX · DOW). r5_count 는 표지 사건을 뺀 수(flagged_xreorg)를 함께 싣는다 — 어느 쪽을 1차로 둘지는 등록 동결 전 결정.
     3.01 의 자발적 상장 이전(PEP · EXC · AEP · KDP · WMT)은 본문 없이는 가리지 못한다(한계 · 선언). 8-K12B 등 재편 서식은
     카드 서식(8-K)이 아니라 사건으로 세지 않고 log 에만 센다.

어댑터 — 자료(§B data/_sub_pit.json.gz · §C data/_tenq_rf.json 또는 data/_txt_sim.json · §A0 data/_issuer_map.json)는 다른 작업이 지금
  만들고 있다. 필드 이름은 이 파일의 F_TENQ · F_SUB 두 표에서만 고친다(앞 후보가 우선). 컨테이너 모양(행 목록 · {'docs': […]} ·
  열 묶음 {'cols','rows'} · CIK 별 submissions 열 묶음 · accession 키 사전)은 _records 가 알아본다. acceptanceDateTime 의 'Z' 가
  실제 UTC 라는 것(§B 비평 실측: 17:30~21:30Z 접수 720건이 모두 같은 날 filingDate)은 ACC_Z_IS_UTC 한 곳에만 둔다.

사용:
  python build/r_r2flags.py --selftest                                 # 합성 자료 단위 시험(수익 없음)
  python build/r_r2flags.py --dry [--tenq P] [--sub P] [--t401 P] [--im P] [--export P] [--shape-ver card|v2|v3]
      # 실제 자료가 있으면 구성·밀도만(개수 · 비율 · F0 문턱 · 빌더 대조 · §B 가 있으면 tenk 건너뛰기 대조판) — 없으면 없다고
      # 적는다. 경계 세계 = 지도 전 기간(2014-06~) 비금융 · 비 FPI 멤버-월. R5 개수는 금융을 넣은 멤버-월 · Eg 상위 30 근사
      # 부분집합(data/_eg_q5_scores_pitgics.json — 예측치 · 수익 아님)으로 센다. --export 를 줄 때만 그 경로에
      # 정식 표지 판(r_p0_adapt flags_override 모양 · R2 CH/CH_MISS · R5 ALARM · ALARM_XREORG 진단)을 쓴다.
      # --shape-ver: §C 패널(data/_tenq_rf.json)의 어느 형태 판 열을 읽을지(card = 열 이름 그대로 · 기본 · v2 = *_v2 · v3 = *_v3 ·
      # tenq_ver_view). 판마다 형태 · 분리 상태 · 짝 상태만 다르고 경계 · 토큰 · SimRF 값은 같다. 등록 때 판을 고른다.
"""
from __future__ import annotations
import bisect, collections, datetime as dt, gzip, hashlib, io, json, math, os, random, re, sys, tempfile

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q            # noqa: E402  mshift · months_between · FORM0 · HOLD1(랩 월 산수 한 벌)
import refresh_events as EV        # noqa: E402  _holidays · _half_days(NYSE 휴장 규칙은 한 곳에만)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# ════════════════════════════════════════════════════════════════════════
# 모수 — 카드 params 그대로(다른 분위 · 척도 · 창은 시험하지 않는다)
# ════════════════════════════════════════════════════════════════════════
PAIR_LO, PAIR_HI = 70, 200                       # 짝 창(reportDate 차이 · 일)
Q_LO = 0.20                                      # 하위 20% · 경계 = 전년도 분포
HEAD_WORDS, B_MAX, F_MIN = 200, 150, 500         # 형태 판정: 첫 200단어 · B < 150 ≤ U · F ≥ 500
BOILER = re.compile(r"\bno material changes?\b|\bnot (?:been )?materially changed\b"
                    r"|\bthere (?:have|has) been no material changes?\b")
CLOSE, HALF_CLOSE = (16, 0), (13, 0)             # 마감(ET) · 조기폐장일 마감(랩 선택 ③)
F0_PAIRS_YEAR, F0_FAIL_RATE, F0_CH_MEDIAN = 900, 0.20, 30   # R2 F0(등록 전)
F_BUILDER_DISAGREE = 0.01                                    # 랩 구성 점검(⑯) — 빌더 짝 상태와의 불일치율 문턱(카드 F0 아님)
LONG_GAP = 120                                               # ⑭ tenk 대조를 거는 짝 간격(일) — 1분기 대 전년 3분기(≈182)만 넘는다

R5_NT = ("NT 10-K", "NT 10-Q")
R5_AMEND = ("8-K/A", "NT 10-K/A", "NT 10-Q/A")               # 랩 선택 ⑪
R5_A_ITEMS = ("4.02", "3.01")
R5_B_ITEMS = ("1.03", "2.04", "2.05", "2.06", "5.01")       # Lerman·Livnat Table 3 Panel D
R5_ALL_ITEMS = frozenset(R5_A_ITEMS + R5_B_ITEMS + ("4.01",))
R5_A_MONTHS, R5_B_DAYS = 12, 90                             # 12개월 = 랩 선택(출처 없음 · 카드 선언)
R5_REORG_TYPES = ("3.01", "5.01")                           # ⑲ 재편 서명(진단)을 거는 사건
R5_REORG_A, R5_REORG_B, R5_REORG_SPLICE_M = frozenset({"3.03", "5.03"}), frozenset({"1.01", "2.01"}), 1
R5_OTHER_8K = ("8-K12B", "8-K12G3", "8-K15D5")               # 카드 서식 밖(재편 승계 등록) — 사건으로 세지 않고 log 만
RX_RESIGN = re.compile(r"resign|declin(?:ed|es) to stand")
RX_ROUTINE = re.compile(r"dismiss|not re-engaged|selection process")
RX_401_GAP = re.compile(r"declin\w* to stand|not (?:to )?stand for re|(?:will|would|not) (?:not )?seek re-?(?:election|appointment)")
RESIGN_CLASSES = ("resign", "both")                         # 랩 선택 ⑨
LABELS_401 = ("resign", "routine", "both", "none")

# NYSE 특별 휴장(규칙 밖) — 9·11 · 레이건 · 포드 · 샌디 · 부시 · 카터. refresh_events.ADHOC(임시휴장의 단일 원천)를 합친다 —
# 전방 판에서 ADHOC 에 새 휴장이 적히면 여기에도 닿는다.
_SPECIAL_LIT = frozenset({"2001-09-11", "2001-09-12", "2001-09-13", "2001-09-14", "2004-06-11", "2007-01-02",
                          "2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09"})


def _special_closed(adhoc):
    return _SPECIAL_LIT | frozenset(adhoc or ())


SPECIAL_CLOSED = _special_closed(getattr(EV, "ADHOC", None))

# ════════════════════════════════════════════════════════════════════════
# 어댑터 — 필드 이름은 여기서만 고친다(앞 후보가 우선)
# ════════════════════════════════════════════════════════════════════════
ACC_Z_IS_UTC = True     # §B 실측 — acceptanceDateTime 의 Z 는 실제 UTC. 틀렸다고 밝혀지면 여기 한 줄만 바꾼다(False = 값이 ET).

F_TENQ = {               # §C 10-Q 문서 한 건(data/_tenq_rf.json · 계획서 이름 data/_txt_sim.json)
    "acc":      ("acc", "accession", "accessionNumber", "adsh"),
    "cik":      ("cik", "CIK"),
    "gid":      ("gid", "group", "grp", "g", "그룹"),
    "form":     ("form", "formType", "form_type"),       # §C 계획 필드 목록엔 없다(10-Q 원본만 받는다) → 없으면 10-Q 로 본다
    "rd":       ("rd", "reportDate", "report_date", "period"),
    "fd":       ("fd", "filingDate", "filing_date"),
    "acc_utc":  ("acceptanceDateTime", "accepted_utc", "acc_utc", "accepted"),
    "acc_et":   ("accepted_et", "acc_et", "acceptance_et", "avail_et"),
    "avail":    ("avail_date", "avail"),                   # 빌더가 셈한 가용일 — avail_how 가 있으면 그것을 쓴다(⑧b) · 없으면 접수 시각이 없을 때만
    "avail_how": ("avail_how",),                           # 빌더 가용일 규칙(acc · fd_floor · fd_late · fd_etamb · fd_noacc — ⑧b)
    "shape":    ("shape", "rf_shape", "form_shape", "형태", "form_bu"),
    "status":   ("parse_status", "status"),
    "n_rf":     ("n_words_rf", "nw_rf", "n_rf"),
    "ixbrl":    ("isInlineXBRL", "ixbrl", "ix"),
    "tf_rf":    ("tf_rf", "tf1a"),
    "tf_doc":   ("tf_doc",),
    "text_rf":  ("text_rf", "rf_text"),
    "sim_rf":   ("SimRF", "sim_rf", "simrf"),
    "sim_doc":  ("SimDoc", "sim_doc"),
    "prev_acc": ("prev_acc", "pair_acc", "prev"),
    "dlog":     ("dlog_len_rf", "dlog_len", "dlog"),       # n_rf 가 없을 때만 쓴다(있으면 여기서 다시 잰다)
    "ix_sw":    ("ixbrl_switch",),                         # 짝 수준 표지 — 문서의 isInlineXBRL 이 없을 때만 쓴다
    "in_world": ("in_world", "inw"),                       # §C: pub_m 에 그룹이 비금융 멤버(⑦ 경계 세계 · 2014-06 부터)
    "pair_status": ("pair_status",),                       # §C 빌더의 짝 상태 — 대조만(⑯)
}
# 빌더 짝 상태 → 이 파일의 결측 이유(None = 유효 짝). 뒤 두 줄은 계획서 이름(parse_status 칸에 짝 상태를 적은 판).
BUILDER_PS = {"ok": (None,), "no_prior": ("no_prior",), "gap_out": ("gap",), "gap": ("gap",), "prior_late": ("prior_late",),
              "no_rd": ("no_rd",), "cur_fail": ("fail_cur",), "prior_fail": ("fail_prev",), "shape_switch": ("transition",),
              "no_pair": ("no_prior", "gap", "prior_late"), "form_switch": ("transition",)}
PLAN_PS_IN_STATUS = ("no_pair", "form_switch")
F_SUB = {                # §B submissions 한 줄(8-K · NT · 10-Q …) — data/_sub_pit.json.gz
    "acc":      ("accessionNumber", "acc", "accession", "adsh"),
    "cik":      ("cik", "CIK"),
    "gid":      ("gid", "group"),
    "form":     ("form", "formType"),
    "items":    ("items", "item"),
    "fd":       ("filingDate", "fd"),
    "rd":       ("reportDate", "rd"),
    "acc_utc":  ("acceptanceDateTime", "accepted_utc", "acc_utc"),
    "acc_et":   ("accepted_et", "acc_et"),
    "doc":      ("primaryDocument", "doc"),
}
SHAPES = {"B": "B", "U": "U", "F": "F"}
FAIL_STATUS = {"fail", "failed", "split_fail", "no_1a", "error", "err", "noparse", "parse_fail"}
_META_KEYS = {"note", "notes", "doc", "meta", "generated", "manifest", "pins", "inputs", "schema", "version", "log", "stats",
              "f0", "coverage", "hash", "sha256", "fields", "format"}
_RX_ACC = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_RX_CIKKEY = re.compile(r"^(?:CIK)?0*(\d{1,10})(?:\.json)?$")
_KNOWN = set(k for v in F_TENQ.values() for k in v) | set(k for v in F_SUB.values() for k in v)


def _pick(rec, keys):
    for k in keys:
        v = rec.get(k)
        if v is not None and v != "":
            return v
    return None


def _columnar(d):
    f = d.get("form")
    return isinstance(f, list) and all(len(v) == len(f) for v in d.values() if isinstance(v, list))


def _with_hint(x, hint):
    if hint is None:
        return x
    x = dict(x)
    x.setdefault("_key", hint)
    return x


def _records(obj, hint=None):
    """컨테이너 모양을 알아보고 행 사전 목록으로 편다. 행마다 묶음 키(CIK · accession)를 '_key' 로 달아 둔다."""
    out = []
    if isinstance(obj, list):
        for x in obj:
            if isinstance(x, dict):
                out += _records(x, hint) if (_columnar(x) or "filings" in x) else [_with_hint(x, hint)]
        return out
    if not isinstance(obj, dict):
        return out
    if isinstance(obj.get("cols"), list) and isinstance(obj.get("rows"), list):
        cs = obj["cols"]
        return [_with_hint(dict(zip(cs, r)), hint) for r in obj["rows"] if isinstance(r, (list, tuple))]
    if _columnar(obj):
        ks = [k for k, v in obj.items() if isinstance(v, list)]
        return [_with_hint({k: obj[k][i] for k in ks}, hint) for i in range(len(obj["form"]))]
    if isinstance(obj.get("filings"), dict):                        # submissions 원본 모양(recent + 이어받은 조각)
        h = obj.get("cik", hint)
        out += _records(obj["filings"].get("recent") or {}, h)
        for x in obj["filings"].get("pages") or obj.get("pages") or []:
            out += _records(x, h)
        return out
    for k in ("docs", "rows", "data", "records", "ciks", "by_cik", "events", "filings"):
        if isinstance(obj.get(k), (list, dict)):
            return _records(obj[k], hint)
    for k, v in obj.items():
        if k in _META_KEYS:
            continue
        if isinstance(v, dict) and not _columnar(v) and "filings" not in v and any(kk in _KNOWN for kk in v):
            out.append(_with_hint(v, k))                            # accession(또는 CIK) 키 → 기록 한 건
        elif isinstance(v, (list, dict)):
            out += _records(v, k)
    return out


def _key_cik(k):
    m = _RX_CIKKEY.match(str(k)) if k is not None else None
    return int(m.group(1)) if m else None


def _int(x):
    try:
        return int(str(x).strip().lstrip("CIK") or "x")
    except Exception:
        return None


def _bool(x):
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in ("0", "false", "no", "n", "f"):
        return False
    if s in ("1", "true", "yes", "y", "t"):
        return True
    return None


def adapt_tenq(r):
    """§C 문서 한 건 → 정본 필드. 모르는 모양은 None 으로 두고 쓰는 쪽이 이유별로 센다."""
    c = {k: _pick(r, v) for k, v in F_TENQ.items()}
    if c["acc"] is None and r.get("_key") is not None and _RX_ACC.match(str(r["_key"])):
        c["acc"] = str(r["_key"])
    c["cik"] = _int(c["cik"]) if c["cik"] is not None else _key_cik(r.get("_key"))
    moved = False
    if c["form"] is not None and (str(c["form"]).strip().upper() in SHAPES or str(c["form"]).strip().lower() in FAIL_STATUS):
        if c["shape"] is None:                                  # «형태» 를 form 으로 옮긴 빌더 — 서식이 아니라 형태 값이다
            c["shape"] = c["form"]
        c["form"], moved = None, True
    c["status_raw"] = (str(c["status"]).strip().lower() if c["status"] is not None else None)
    raw_shape = c["shape"]
    c["shape_field"] = moved or any(k in r for k in F_TENQ["shape"])   # 칸이 «있는가»(값이 null 인 실패 문서는 있다고 본다)
    c["shape"] = SHAPES.get(str(raw_shape).strip().upper()) if raw_shape is not None else None
    c["in_world"] = _bool(c["in_world"])
    c["pair_status"] = str(c["pair_status"]).strip().lower() if c["pair_status"] is not None else None
    if c["status"] is not None and str(c["status"]).strip().lower() in FAIL_STATUS:
        c["shape"] = None
    for k in ("sim_rf", "sim_doc", "n_rf", "dlog"):
        if c[k] is not None:
            try:
                c[k] = float(c[k])
            except Exception:
                c[k] = None
    c["ixbrl"] = _bool(c["ixbrl"])
    c["ix_sw"] = _bool(c["ix_sw"])
    return c


def adapt_sub(r):
    c = {k: _pick(r, v) for k, v in F_SUB.items()}
    c["cik"] = _int(c["cik"]) if c["cik"] is not None else _key_cik(r.get("_key"))
    return c


def read_json(path):
    with open(path, "rb") as fh:
        b = fh.read()
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return json.loads(b.decode("utf-8"))


# §C 형태 판 고르기(--shape-ver) — §C 빌더는 카드 판(접미 없음) · v2(_v2) · v3(_v3) 열을 함께 싣는다. 판을 고르면 아래 열을 그 판의
#   열로 바꿔 읽는다(형태 · 상태 열이 없으면 멈춘다 — 조용히 카드 판으로 떨어지지 않게). card = 이전 동작 그대로.
TENQ_VERS = ("card", "v2", "v3")
TENQ_VER_COLS = ("shape", "parse_status", "pair_status", "SimRF", "SimRF_sw", "prev_shape", "boiler")
# 🔒 등록 결정(2026-09-26 · F0 전에 정했다 — PREREG «F0 전에 정한 것»): 형태 판 = v3(§C 파서 라운드 2 검증 통과 판) ·
#   Q1 규칙 = «B-B 짝은 변경 없음»(유효 짝 가운데 앞 · 지금 형태가 모두 B 면 SimRF = 1 로 두고 경계 분포에도 1 로 넣는다 → 경계를 다시
#   잰다 · 그 짝은 Q1 이 될 수 없다) · R2 F0 분리 실패 = split_fail + no_1a(⑰ 의 형태 없음 — 두 실패를 함께 센다).
#   카드 판(card)과 옛 Q1 규칙(base)은 명시적으로 고를 때만(감사 · 대조).
REG_SHAPE_VER = "v3"
REG_Q1_RULE = "bb_nochange"
Q1_RULES = ("base", "bb_nochange")


def tenq_ver_view(recs, ver=None):
    """§C 기록 목록 → 고른 형태 판의 열을 기본 이름으로 옮긴 사본(card · None 이면 그대로)."""
    if ver in (None, "card"):
        return recs
    if ver not in TENQ_VERS:
        raise SystemExit("🚨 --shape-ver 는 %s 가운데 하나" % (TENQ_VERS,))
    sfx, out, miss = "_" + ver, [], 0
    for r in recs:
        r = dict(r)
        for c in TENQ_VER_COLS:
            if c + sfx in r:
                r[c] = r[c + sfx]
            elif c in ("shape", "parse_status"):
                miss += 1
        out.append(r)
    if miss:
        raise SystemExit("🚨 §C 기록 %d건에 %s 판 형태 · 상태 열(shape%s · parse_status%s)이 없다" % (miss, ver, sfx, sfx))
    return out


def load_tenq(path, ver=None):
    """§C 기록 → 정본 필드(ver = 형태 판 · None 이면 등록 판 REG_SHAPE_VER · 'card' 는 명시할 때만)."""
    return [adapt_tenq(r) for r in tenq_ver_view(_records(read_json(path)), REG_SHAPE_VER if ver is None else ver)]


def load_sub(path):
    return [adapt_sub(r) for r in _records(read_json(path))]


def load_t401(path):
    """4.01 본문(§D 가 받는다) — {accession: 본문} 또는 {accession: 미리 판정한 표지}."""
    d = read_json(path)
    if isinstance(d, dict) and isinstance(d.get("docs"), dict):
        d = d["docs"]
    return {str(k): v for k, v in (d or {}).items() if k not in _META_KEYS}


class IssuerMap:
    """data/_issuer_map.json(§A0) 읽개 — issuer_map.py 는 SEC_UA 없이는 import 를 거부하므로 문서화된 모양(tm_format ·
    groups_format)을 여기서 직접 읽는다."""

    def __init__(self, d):
        self.doc = d
        self.tm = d.get("tm") or {}
        self.groups = d.get("groups") or {}
        self.cik2g = collections.defaultdict(list)
        for g, v in self.groups.items():
            for row in v.get("ciks") or []:
                a = (row[1] or "")[:7] or None
                b = (row[2] or "")[:7] or None
                self.cik2g[int(row[0])].append((g, a, b))
        self.idx = {}
        self.prim = collections.defaultdict(set)                    # (그룹, 달) → 주 CIK(tm 네 번째 칸) — 랩 선택 ①
        # 등록 FPI 표지 = _issuer_map.json fpi_registered.tm_index(2026-09-25 권고 fpi_q = 7 · 사양 칸 5 는 옛 판) — 칸을 박아 두지 않는다
        self.fpi_index = int((d.get("fpi_registered") or {}).get("tm_index", 5))
        fx = self.fpi_index
        for t, runs in self.tm.items():
            for run in runs:
                a, b, g = run[0], run[1], run[2]
                fpi = run[fx] if len(run) > fx else (run[5] if len(run) > 5 else None)
                pc = run[3] if len(run) > 3 else None
                for ym in Q.months_between(a, b):
                    self.idx[(t, ym)] = (g, fpi)
                    if g and pc is not None:
                        self.prim[(g, ym)].add(int(pc))
        self._splice = {}

    @classmethod
    def load(cls, path=os.path.join(DATA, "_issuer_map.json")):
        return cls(read_json(path))

    def group_of(self, cik, ym):
        for g, a, b in self.cik2g.get(int(cik), ()):
            if (a is None or a <= ym) and (b is None or ym <= b):
                return g
        return None

    def primary_ciks(self, g, ym):
        return self.prim.get((g, ym), frozenset())

    def splice_months(self, g):
        """그룹 CIK 효력 구간의 시작 · 끝 달(열린 끝 제외) — ⑲ 재편 서명."""
        if g not in self._splice:
            s = set()
            for row in (self.groups.get(g) or {}).get("ciks") or []:
                for x in (row[1], row[2]):
                    if x:
                        s.add(str(x)[:7])
            self._splice[g] = frozenset(s)
        return self._splice[g]

    def resolve(self, t, ym):
        for k in (t, t.replace("-", "."), t.replace(".", "-")):
            if (k, ym) in self.idx:
                return self.idx[(k, ym)]
        return (None, None)


def _im_of(gof):
    """gof 가 IssuerMap.group_of(묶인 메서드)면 그 지도 — 호출자를 고치지 않고 주 CIK · 효력 경계를 쓰게."""
    im = getattr(gof, "__self__", None)
    return im if isinstance(im, IssuerMap) else None


# ════════════════════════════════════════════════════════════════════════
# 달력 · 시각
# ════════════════════════════════════════════════════════════════════════
def rule_days(y0, y1):
    """규칙 NYSE 거래일(주말 · refresh_events._holidays · 특별 휴장 제외)."""
    hol = set()
    for y in range(y0, y1 + 1):
        hol |= set(EV._holidays(y))
    d, end, out = dt.date(y0, 1, 1), dt.date(y1, 12, 31), []
    while d <= end:
        s = d.isoformat()
        if d.weekday() < 5 and s not in hol and s not in SPECIAL_CLOSED:
            out.append(s)
        d += dt.timedelta(days=1)
    return out


class Cal:
    """NYSE 거래일 달력. 규칙 달력이 정본이다 — 관측 격자(stocks.json pxd_dates)는 구멍이 있어서(HEAD 에서 2026-09-22 · 09-24
    누락 · §F) 정본으로 쓰지 않고 --dry 에서 감사만 한다."""

    def __init__(self, days=None, y0=2005, y1=2031):
        self.days = sorted(set(days if days is not None else rule_days(y0, y1)))
        self.lo, self.hi = (("%04d-01-01" % y0, "%04d-12-31" % y1) if days is None else (self.days[0], self.days[-1]))
        self._s = set(self.days)
        self._half = set()
        for y in range(int(self.days[0][:4]), int(self.days[-1][:4]) + 1):
            self._half |= set(EV._half_days(y))
        self._last = {}
        for d in self.days:
            self._last[d[:7]] = d

    def is_td(self, d):
        return d in self._s

    def next_after(self, d):
        i = bisect.bisect_right(self.days, d)
        if i >= len(self.days):
            raise ValueError("달력 밖: %s" % d)
        return self.days[i]

    def close_hm(self, d):
        return HALF_CLOSE if d in self._half else CLOSE

    def roll(self, d, hm=None, strict=False):
        """d 가 거래일이고(마감 전 · hm 을 주면) strict 가 아니면 d, 아니면 다음 거래일. 달력 밖이면 None(⑧ — 당기거나 멈추지 않는다)."""
        if not d or d < self.lo or d > self.hi:
            return None
        if not strict and self.is_td(d) and (hm is None or hm < self.close_hm(d)):
            return d
        i = bisect.bisect_right(self.days, d)
        return self.days[i] if i < len(self.days) else None

    def month_end(self, ym):
        return self._last.get(ym)


def _nth_sun(y, m, n):
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))


def _last_sun(y, m):
    nx = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return nx - dt.timedelta(days=(nx.weekday() - 6) % 7)


def utc_to_et(u):
    """naive UTC → naive ET. 미국 서머타임 규칙을 직접 센다(zoneinfo 유무와 무관하게 같은 답 · selftest 가 zoneinfo 와 대조).
    2007~: 3월 둘째 일요일 07:00 UTC ~ 11월 첫째 일요일 06:00 UTC · 1987~2006: 4월 첫째 일요일 ~ 10월 마지막 일요일."""
    y = u.year
    a, b = (_nth_sun(y, 3, 2), _nth_sun(y, 11, 1)) if y >= 2007 else (_nth_sun(y, 4, 1), _last_sun(y, 10))
    s = dt.datetime(a.year, a.month, a.day, 7)
    e = dt.datetime(b.year, b.month, b.day, 6)
    return u + dt.timedelta(hours=-4 if s <= u < e else -5)


_RX_TS = re.compile(r"^(\d{4})-(\d\d)-(\d\d)(?:[T ](\d\d):(\d\d)(?::(\d\d)(?:\.\d+)?)?)?\s*(Z|[+-]\d\d:?\d\d)?$")


_RX_TS14 = re.compile(r"^(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)$")


def parse_ts(s):
    """'2023-11-02T18:04:17.000Z' 류 → (naive datetime, 오프셋 분 | 'Z' | None | 'ET').
    EDGAR SGML 머리의 ACCEPTANCE-DATETIME('20231102180417')은 미국 동부 시각이다 → 'ET'."""
    m14 = _RX_TS14.match(str(s).strip())
    if m14:
        return dt.datetime(*map(int, m14.groups())), "ET"
    m = _RX_TS.match(str(s).strip())
    if not m:
        return None, None
    y, mo, d, hh, mi, ss, off = m.groups()
    t = dt.datetime(int(y), int(mo), int(d), int(hh or 0), int(mi or 0), int(ss or 0))
    if off is None or off == "Z":
        return t, off
    sg = 1 if off[0] == "+" else -1
    o = off[1:].replace(":", "")
    return t, sg * (int(o[:2]) * 60 + int(o[2:]))


def to_et(r):
    """기록의 접수 시각 → naive ET(없으면 None)."""
    if r.get("acc_et"):
        t, off = parse_ts(r["acc_et"])
        if t is not None:
            if off == "ET":
                return t
            if off == "Z" or isinstance(off, int):
                return utc_to_et(t - dt.timedelta(minutes=off if isinstance(off, int) else 0))
            return t
    if r.get("acc_utc"):
        t, off = parse_ts(r["acc_utc"])
        if t is not None:
            if off == "ET":
                return t
            if isinstance(off, int):
                return utc_to_et(t - dt.timedelta(minutes=off))
            return utc_to_et(t) if ACC_Z_IS_UTC else t
    return None


def _date(s):
    if not s:
        return None
    s = str(s)[:10]
    try:
        dt.date.fromisoformat(s)
        return s
    except Exception:
        return None


def avail_of(r, cal):
    """가용일(NYSE 거래일) · 방법. §C 빌더 가용일 · 방법이 있으면 그것(⑧b — 방법 acc 에만 ③ 조기폐장 13:00 을 위에 건다).
    없으면 접수 ET 가 거래일 마감 전이면 그날, 아니면 다음 거래일(휴장일 접수도 다음 거래일). 접수 시각이 없으면 빌더 가용일 ·
    공시일 다음 거래일(랩 선택 ⑧). 규칙 달력 밖이면 (None, 'out_of_cal')."""
    av_b, how_b = _date(r.get("avail")), r.get("avail_how")
    if av_b and how_b:
        if how_b == "acc":
            et = to_et(r)
            if (et is not None and et.date().isoformat() == av_b and av_b in cal._half
                    and HALF_CLOSE <= (et.hour, et.minute) < CLOSE):
                d = cal.roll(av_b, strict=True)
                return (d, "builder_half") if d else (None, "out_of_cal")
        d = cal.roll(av_b)
        if d is None:
            return None, "out_of_cal"
        return (d, "builder") if d == av_b else (d, "builder_not_td")
    et = to_et(r)
    if et is not None:
        d = cal.roll(et.date().isoformat(), (et.hour, et.minute))
        return (d, "et") if d else (None, "out_of_cal")
    av = _date(r.get("avail"))
    if av:
        d = cal.roll(av)
        return (d, "given") if d else (None, "out_of_cal")
    fd = _date(r.get("fd"))
    if fd:
        d = cal.roll(fd, strict=True)
        return (d, "fd_next") if d else (None, "out_of_cal")
    return None, "none"


def _drop_key(how):
    return "drop_no_time" if how == "none" else "drop_" + how


def _grp_month(r, av):
    """CIK 효력 구간을 거는 달(④ · ⑬) — filingDate 의 달 · 없으면 접수 ET 날짜의 달 · 그것도 없으면 가용월."""
    fd = _date(r.get("fd"))
    if fd:
        return fd[:7]
    et = to_et(r)
    return et.date().isoformat()[:7] if et is not None else av[:7]


# ════════════════════════════════════════════════════════════════════════
# 텍스트 도구 — 형태 판정 · 코사인(§C 빌더와 같은 규칙 · 대조와 합성 시험용)
# ════════════════════════════════════════════════════════════════════════
_RX_DIG = re.compile(r"[0-9]")
_RX_TOK = re.compile(r"[a-z]{2,}")


def tokens(text):
    """소문자 · 숫자 → '#' · 두 글자 이상 알파벳 토큰만(카드 전처리의 토큰 단계)."""
    return _RX_TOK.findall(_RX_DIG.sub("#", (text or "").lower()))


def shape_of(toks):
    """(형태 B/U/F 또는 None = 분리 실패, 단어 수)."""
    n = len(toks)
    if BOILER.search(" ".join(toks[:HEAD_WORDS])):
        return ("B" if n < B_MAX else "U"), n
    return ("F" if n >= F_MIN else None), n


def tf(toks):
    return dict(collections.Counter(toks))


def cosine(a, b):
    """단어빈도 코사인(CMN Sim_Cosine). fsum 이라 사전 순서와 무관하게 같은 값."""
    if not a or not b:
        return None
    if len(a) > len(b):
        a, b = b, a
    dot = math.fsum(float(v) * float(b.get(k, 0)) for k, v in a.items())
    na = math.sqrt(math.fsum(float(v) ** 2 for v in a.values()))
    nb = math.sqrt(math.fsum(float(v) ** 2 for v in b.values()))
    if na == 0 or nb == 0:
        return None
    return dot / (na * nb)


# ════════════════════════════════════════════════════════════════════════
# R2 — 문서 · 짝 · 경계 · CH_active
# ════════════════════════════════════════════════════════════════════════
def norm_docs(recs, cal, gof=None):
    """정본 10-Q 기록 → {키: 문서}. 버린 것은 이유별로 센다(조용히 버리지 않는다).
    그룹을 먼저 정하고 (그룹, accession) 으로 중복을 없앤다 — 입력 순서와 무관(⑱ 과 같은 뜻). 한 accession 이 두 그룹에
    걸리면(공동 제출 · §C 빌더도 둘 다 싣는다) 두 그룹 모두의 문서이고 키는 'accession@그룹', 아니면 키 = accession.
    reportDate 가 없는 문서는 막이로 남긴다(⑭)."""
    log, tmp = collections.Counter(), {}
    for r in recs:
        form = str(r.get("form") or "").strip().upper()
        if not form:
            form = "10-Q"
            log["form_assumed_10-Q"] += 1                       # §C 는 10-Q 원본만 받는다(계획 필드 목록에 서식 칸이 없다)
        if form != "10-Q":
            log["drop_form:%s" % form] += 1
            continue
        acc = r.get("acc")
        if not acc:
            log["drop_no_acc"] += 1
            continue
        acc = str(acc)
        rd = _date(r.get("rd"))
        av, how = avail_of(r, cal)
        if av is None:
            log[_drop_key(how)] += 1
            continue
        g = r.get("gid")
        if not g and gof is not None and r.get("cik") is not None:
            g = gof(int(r["cik"]), _grp_month(r, av))
        if not g:
            log["drop_no_group"] += 1
            continue
        g = str(g)
        log["avail_" + how] += 1
        if not rd:
            log["no_rd_blocker"] += 1                            # ⑭ 버리지 않는다 — 사슬의 막이
        shape, n_rf, tf_rf = r.get("shape"), r.get("n_rf"), r.get("tf_rf")
        if r.get("text_rf") is not None:                        # 본문이 오면 여기서 판정(대조 · 합성 시험)
            tk = tokens(r["text_rf"])
            s2, n2 = shape_of(tk)
            if r.get("shape_field") and shape != s2:
                log["shape_disagree"] += 1
            shape, n_rf, tf_rf = s2, float(n2), tf(tk)
        elif not r.get("shape_field"):
            log["shape_field_absent"] += 1                       # 형태 칸 자체가 없다 = 필드 이름이 틀렸을 수 있다(F0 가 잡는다)
        et = to_et(r)
        d = {"acc": acc, "gid": g, "cik": r.get("cik"), "rd": rd, "fd": _date(r.get("fd")), "avail": av, "pub_m": av[:7],
             "et": et.isoformat(sep=" ") if et is not None else None, "shape": shape, "n_rf": n_rf, "ixbrl": r.get("ixbrl"),
             "tf_rf": tf_rf, "tf_doc": r.get("tf_doc"), "sim_rf": r.get("sim_rf"), "sim_doc": r.get("sim_doc"),
             "prev_acc": r.get("prev_acc"), "dlog_given": r.get("dlog"), "ix_sw": r.get("ix_sw"),
             "status_raw": r.get("status_raw"), "in_world": r.get("in_world"), "pair_status": r.get("pair_status")}
        k = (g, acc)
        if k in tmp:
            log["drop_dup_acc"] += 1                             # 같은 그룹의 두 CIK 가 같은 제출을 싣는다 — 하나만(순서 무관)
            if _same_acc_rank(d) < _same_acc_rank(tmp[k]):
                tmp[k] = d
            continue
        tmp[k] = d
    n_g = collections.Counter(a for (_, a) in tmp)
    docs = {}
    for (g, a), d in sorted(tmp.items()):
        if n_g[a] > 1:
            log["co_filed_acc_groups"] += 1
        d["key"] = a if n_g[a] == 1 else "%s@%s" % (a, g)
        docs[d["key"]] = d
    return docs, log


def _same_acc_rank(d):
    return (d["avail"], d["et"] or "", str(d["cik"]), d["rd"] or "", str(d["shape"]))


def _gap(d, p):
    if p is None or not d["rd"] or not p["rd"]:
        return None
    return (dt.date.fromisoformat(d["rd"]) - dt.date.fromisoformat(p["rd"])).days


def _check(d, p, metric):
    """(결측 이유 | None, 유사도, 유사도 출처). 순서는 §C 빌더와 같다(no_prior → no_rd → gap → prior_late → 실패 → 형태 전환)."""
    if p is None:
        return "no_prior", None, None
    gap = _gap(d, p)
    if gap is None:
        return "no_rd", None, None                              # ⑭ 막이 — 어느 한쪽 reportDate 가 없다
    if not (PAIR_LO <= gap <= PAIR_HI):
        return "gap", None, None
    if p["avail"] > d["avail"]:
        return "prior_late", None, None
    if metric == "rf":
        if d["shape"] is None:
            return "fail_cur", None, None
        if p["shape"] is None:
            return "fail_prev", None, None
        if (d["shape"] == "F") != (p["shape"] == "F"):
            return "transition", None, None
        ta, tb, given = d["tf_rf"], p["tf_rf"], d["sim_rf"]
    else:
        ta, tb, given = d["tf_doc"], p["tf_doc"], d["sim_doc"]
    if ta and tb:
        s, how = cosine(ta, tb), "tf"
    elif given is not None:
        if d["prev_acc"] and str(d["prev_acc"]) != p["acc"]:
            return "pair_mismatch", None, "given"               # 빌더가 다른 문서와 비교한 값 — 쓰지 않는다
        s, how = float(given), ("given" if d["prev_acc"] else "given_unverified")
    else:
        return "no_sim", None, None
    if s is None or not math.isfinite(s):
        return "no_sim", None, how
    return None, s, how


def _dup_rank(x, g, prim, prev_cik):
    """랩 선택 ① — 같은 reportDate 중복에서 남길 문서의 순위(작을수록 먼저)."""
    c = x["cik"]
    is_prim = prim is not None and c is not None and int(c) in prim(g, x["pub_m"])
    return (0 if is_prim else 1, 0 if (prev_cik is not None and c == prev_cik) else 1, x["avail"], x["et"] or "", x["acc"])


def pair_docs(docs, metric="rf", prim=None, tenk=None):
    """그룹마다 reportDate 순으로 세우고 바로 앞 문서와 짝을 짓는다. 반환 (pairs{키: 짝}, dups[(버린 키, 남긴 키)], log).
    prim(g, ym) → 그달 주 CIK 집합(①) · tenk = {그룹: [10-K reportDate]}(⑭ · 없으면 대조하지 않는다)."""
    by_g = collections.defaultdict(list)
    for d in docs.values():
        by_g[d["gid"]].append(d)
    pairs, dups, log = {}, [], collections.Counter()
    for g in sorted(by_g):
        L = sorted(by_g[g], key=lambda d: (d["rd"] or d["fd"] or d["avail"], d["avail"], d["et"] or "", d["acc"]))
        canon = []
        for d in L:
            if canon and d["rd"] and canon[-1]["rd"] == d["rd"]:
                prev_cik = canon[-2]["cik"] if len(canon) >= 2 else None
                a = canon[-1]
                keep, drop = (a, d) if _dup_rank(a, g, prim, prev_cik) <= _dup_rank(d, g, prim, prev_cik) else (d, a)
                canon[-1] = keep
                dups.append((drop["key"], keep["key"]))         # 랩 선택 ①
                log["dup_period"] += 1
                if drop["cik"] != keep["cik"]:
                    log["dup_period_xcik"] += 1
                continue
            canon.append(d)
        ks = sorted(tenk.get(g) or []) if tenk is not None else None
        for j, d in enumerate(canon):
            p = canon[j - 1] if j else None
            why, sim, how = _check(d, p, metric)
            gap = _gap(d, p)
            if why is None and gap is not None and gap > LONG_GAP and tenk is not None:   # ⑭ 건너뛰기 대조
                if g not in tenk:
                    log["long_gap_unverified"] += 1
                elif bisect.bisect_right(ks, d["rd"]) - bisect.bisect_right(ks, p["rd"]) > 0:      # 10-K rd ∈ (p.rd, d.rd]
                    log["long_gap_verified"] += 1
                else:
                    why, sim, how = "skip_suspect", None, how
            if how:
                log["sim_" + how] += 1
            dlog = None
            if why is None and d["n_rf"] and p["n_rf"] and d["n_rf"] > 0 and p["n_rf"] > 0:
                dlog = math.log(d["n_rf"]) - math.log(p["n_rf"])
            elif why is None and d.get("dlog_given") is not None:
                dlog = float(d["dlog_given"])                   # 단어 수가 없으면 빌더 값(짝이 같다고 확인된 경우만 여기 온다)
                log["dlog_given"] += 1
            ixs = _ix_switch(d, p)
            if metric == "rf":                                  # ⑯ 빌더 대조(SimDoc 판은 형태 규칙이 없어 대조하지 않는다)
                pa = d.get("prev_acc")
                if pa is not None:
                    log["prev_acc_" + ("agree" if (p is not None and str(pa) == p["acc"]) else "disagree")] += 1
                bps = d.get("pair_status") or (d.get("status_raw") if d.get("status_raw") in PLAN_PS_IN_STATUS else None)
                if bps is not None:
                    exp = BUILDER_PS.get(bps)
                    if exp is None:
                        log["builder_ps_unknown:%s" % bps] += 1
                    elif why in exp:
                        log["builder_ps:agree"] += 1
                    else:
                        log["builder_ps:%s→%s" % (bps, why or "ok")] += 1
            pairs[d["key"]] = {"acc": d["acc"], "key": d["key"], "gid": g, "rd": d["rd"], "avail": d["avail"],
                               "pub_m": d["pub_m"], "prev": p["acc"] if p else None, "prev_key": p["key"] if p else None,
                               "gap": gap, "why": why, "sim": sim if why is None else None, "dlog": dlog, "shape": d["shape"],
                               "shape_prev": p["shape"] if p else None, "ix_switch": bool(ixs), "in_world": d.get("in_world")}
    return pairs, dups, log


def _ix_switch(d, p):
    """iXBRL 전환 짝 — 두 문서의 isInlineXBRL 이 다르면 True. 문서 값이 없으면 빌더의 짝 표지(ixbrl_switch)."""
    if p is not None and d.get("ixbrl") is not None and p.get("ixbrl") is not None:
        return d["ixbrl"] != p["ixbrl"]
    return bool(d.get("ix_sw"))


def excl_ixbrl(d, p):
    """진단(측정): iXBRL 전환 짝(isInlineXBRL 이 서로 다른 짝)을 뺀 판."""
    return p is not None and _ix_switch(d, p)


def excl_covid(d, p):
    """진단(측정): 2020-03~08 공개분(코로나 위험요인)을 뺀 판."""
    return "2020-03" <= d["pub_m"] <= "2020-08"


def mark_excluded(pairs, docs, exclude):
    """⑮ 진단판 — 유효 짝 가운데 exclude(문서, 앞 문서) 가 참인 것만 결측(excluded)으로. 경계는 건드리지 않는다. 반환 = 바꾼 수."""
    n = 0
    for k, p in pairs.items():
        if p["why"] is None and exclude(docs[k], docs[p["prev_key"]] if p["prev_key"] else None):
            p["why"], p["sim"], p["dlog"] = "excluded", None, None
            n += 1
    return n


def _inw(world):
    """world → (판정 함수 | None, 덮는 달 집합 | None = 모든 달). 집합 {(그룹, 달)} 은 그 달들만 덮는다(⑦)."""
    if world is None:
        return None, None
    if callable(world):
        cv = getattr(world, "months", None)
        return world, (set(cv) if cv is not None else None)
    ws = set(world)
    return (lambda g, ym: (g, ym) in ws), {ym for _, ym in ws}


def _bw(gid, pm, iw, inw, cover):
    """⑦ 경계 세계 판정 → (들어가나, 출처). iw = §C in_world(None = 칸 없음)."""
    if inw is not None and (cover is None or pm in cover):
        cw = bool(inw(gid, pm))
        return (cw, "caller") if iw is None else ((cw and bool(iw)), "caller+in_world")
    if iw is not None:
        return bool(iw), "in_world"
    return True, ("all" if inw is None else "uncovered_all")


def boundaries(pairs, inw=None, q=Q_LO, min_n=1, cover=None):
    """{공개연도 Y: {cut, n, src, world_months}} — Y 의 경계 = Y−1 에 공개된 세계(⑦) 유효 짝 SimRF 의 q 분위(np.quantile · linear).
    짝이 min_n 보다 적으면 None(카드에 최소 수가 없어 기본 1 — 연간 유효 짝 ≥ 900 은 F0 가 따로 본다 · r_stagem 잠정 빌더는 50).
    src = 세계 판정 출처별 짝 수 · world_months = Y−1 가운데 호출자 세계가 덮은 달 수(None = 호출자 세계가 모든 달을 덮음/없음)."""
    by_y, src = collections.defaultdict(list), collections.defaultdict(collections.Counter)
    for p in pairs.values():
        if p["why"] is not None:
            continue
        ok, s = _bw(p["gid"], p["pub_m"], p.get("in_world"), inw, cover)
        y = int(p["pub_m"][:4])
        src[y][s if ok else s + ":out"] += 1
        if ok:
            by_y[y].append(p["sim"])
    B = {}
    for y in sorted({int(p["pub_m"][:4]) for p in pairs.values()}):
        v = sorted(by_y.get(y - 1) or [])
        B[y] = {"cut": (float(np.quantile(np.asarray(v, float), q)) if len(v) >= max(1, min_n) else None), "n": len(v),
                "src": dict(sorted(src.get(y - 1, {}).items())),
                "world_months": (sum(1 for m in cover if m[:4] == str(y - 1)) if cover is not None else None)}
    return B


def classify(pairs, B):
    """짝마다 miss(결측 이유 | None) · q1(True/False | None) · cut 을 단다."""
    for p in pairs.values():
        cut = (B.get(int(p["pub_m"][:4])) or {}).get("cut")
        p["cut"] = cut
        if p["why"] is not None:
            p["miss"], p["q1"] = p["why"], None
        elif cut is None:
            p["miss"], p["q1"] = "no_boundary", None
        else:
            p["miss"], p["q1"] = None, bool(p["sim"] < cut)


GM_EMPTY = {"ch": 0, "miss": 0, "n": 0, "accs": [], "q1_acc": [], "why": [], "sim": None, "dlog": 0.0, "dlog_raw": None}


def ch_active(pairs):
    """{(그룹, 월 t): 행} — 공개월 t−2..t 창. 창에 10-Q 가 없는 (그룹, 월)은 싣지 않는다(gm_get 이 GM_EMPTY 를 준다)."""
    by_g = collections.defaultdict(list)
    for p in pairs.values():
        by_g[p["gid"]].append(p)
    gm = {}
    for g in sorted(by_g):
        by_m = collections.defaultdict(list)
        for p in by_g[g]:
            by_m[p["pub_m"]].append(p)
        for t in sorted({Q.mshift(m, k) for m in by_m for k in (0, 1, 2)}):
            W = sorted(by_m.get(Q.mshift(t, -2), []) + by_m.get(Q.mshift(t, -1), []) + by_m.get(t, []),
                       key=lambda p: (p["avail"], p["acc"]))
            if not W:
                continue
            ch = any(p["q1"] for p in W)
            bad = sorted({p["miss"] for p in W if p["miss"]})
            ok = [p for p in W if p["miss"] is None]
            last = ok[-1] if ok else None
            gm[(g, t)] = {"ch": int(ch), "miss": int((not ch) and bool(bad)), "n": len(W), "accs": [p["acc"] for p in W],
                          "q1_acc": [p["acc"] for p in W if p["q1"]], "why": bad,
                          "sim": last["sim"] if last else None,
                          "dlog": (last["dlog"] if (last and last["dlog"] is not None) else 0.0),
                          "dlog_raw": (last["dlog"] if last else None)}
    return gm


def gm_get(gm, g, t):
    return gm.get((g, t), GM_EMPTY)


def r2_build(recs, cal, gof=None, world=None, metric="rf", exclude=None, q=Q_LO, min_n=1, prim=None, tenk=None,
             q1_rule=REG_Q1_RULE):
    """정본 기록 → R2 표지 한 벌. metric='rf'(1차 SimRF) · 'doc'(SimDoc 대조). exclude = 진단판 술어(excl_ixbrl · excl_covid).
    world = 경계 세계(⑦ · 집합이면 덮는 달만) · prim = 주 CIK(① · gof 가 IssuerMap.group_of 면 그 지도에서) · tenk = ⑭.
    q1_rule = 'bb_nochange'(등록 · metric 'rf' 에만 — B-B 유효 짝 SimRF := 1 · 원래 값은 sim_raw · 경계 분포에도 1) · 'base'(옛 규칙)."""
    if q1_rule not in Q1_RULES:
        raise SystemExit("🚨 q1_rule 은 %s 가운데 하나" % (Q1_RULES,))
    inw, cover = _inw(world)
    im = _im_of(gof)
    if prim is None and im is not None:
        prim = im.primary_ciks
    docs, log_d = norm_docs(recs, cal, gof)
    pairs, dups, log_p = pair_docs(docs, metric, prim, tenk)
    if metric == "rf" and q1_rule == "bb_nochange":             # 🔒 등록 Q1 규칙 — B-B 짝은 변경 없음(경계를 그 분포로 다시 잰다)
        for p in pairs.values():
            if p["why"] is None and p["shape"] == "B" and p["shape_prev"] == "B":
                p["sim_raw"], p["sim"] = p["sim"], 1.0
                log_p["bb_nochange"] += 1
    B = boundaries(pairs, inw, q, min_n, cover)                 # ⑮ 경계는 진단 제외 «전» 본판 짝으로
    if exclude is not None:
        log_p["excluded"] += mark_excluded(pairs, docs, exclude)
    classify(pairs, B)
    gm = ch_active(pairs)
    return {"metric": metric, "docs": docs, "pairs": pairs, "dups": dups, "bounds": B, "gm": gm,
            "log": dict(sorted((log_d + log_p).items())), "inw": inw, "cover": cover, "q1_rule": q1_rule if metric == "rf" else None}


def tenk_from_sub(recs, cal=None, gof=None):
    """§B submissions 기록 → {그룹: [10-K · 10-KT reportDate]}(⑭ 건너뛰기 대조용 · 정정본도 회계연도 끝의 증거로 받는다)."""
    out = collections.defaultdict(set)
    for r in recs:
        form = str(r.get("form") or "").strip().upper()
        if not form.startswith("10-K") or form.startswith("10-KSB"):
            continue
        rd = _date(r.get("rd"))
        if not rd:
            continue
        g = r.get("gid")
        if not g and gof is not None and r.get("cik") is not None:
            fd = _date(r.get("fd"))
            g = gof(int(r["cik"]), fd[:7] if fd else rd[:7])
        if g:
            out[str(g)].add(rd)
    return {g: sorted(v) for g, v in out.items()}


def members_from_im(im, months, sectors=None, drop_fin=True):
    """구성 점검용 멤버-월 [{t, ym, gid, fpi, sector}] — issuer_map tm(SPX ∪ NDX 멤버-월). 금융은 pit_gics_sectors(SPX 만)로 뺀다 ·
    섹터를 모르는 NDX 전용 이름은 남긴다(점검용 근사 · 1차 세계는 §E 러너가 정한다)."""
    ms = set(months)
    sec_of = {}
    if sectors:
        for ym, row in (sectors.get("months") or {}).items():
            for s, ts in (row.get("sec") or {}).items():
                for t in ts:
                    sec_of[(t, ym)] = s
    out = []
    for (t, ym), (g, fpi) in sorted(im.idx.items()):
        if ym not in ms:
            continue
        s = sec_of.get((t, ym)) or sec_of.get((t.replace(".", "-"), ym))
        if drop_fin and s == "Financials":
            continue
        out.append({"t": t, "ym": ym, "gid": g, "fpi": fpi, "sector": s})
    return out


def member_rows(R, members):
    """멤버-월 → R2 행. status: ok · fpi(표본 밖) · fpi_null(표지 모름 · 표지는 계산) · unresolved(그룹 없음)."""
    out = {}
    for m in members:
        g, fpi = m.get("gid"), m.get("fpi")
        if not g:
            out[(m["t"], m["ym"])] = dict(GM_EMPTY, status="unresolved", gid=None)
            continue
        row = gm_get(R["gm"], g, m["ym"])
        st = "fpi" if fpi == 1 else ("fpi_null" if fpi is None else "ok")
        if st == "fpi":
            row = GM_EMPTY
        out[(m["t"], m["ym"])] = dict(row, status=st, gid=g)
    return out


def _unfetched(st):
    return bool(st) and (str(st).startswith("fetch") or st == "unparsed")


def r2_density(R, months=None, inw=None):
    """연도별 밀도(수익 없음 · 등록 전 커밋용) — 문서 · 짝 · 결측 이유 · 형태 분포 · 형태 전환 비율 · 경계 · 월 CH 수 · F0.
    valid_world(F0 연간 유효 짝)와 fail_rate(F0 분리 실패율 · ⑰)는 경계 세계(⑦)와 같은 판정을 쓴다. checks = 랩 구성 점검(⑯ · ①)."""
    docs, pairs = R["docs"], R["pairs"]
    if inw is None:
        inw, cover = R.get("inw"), R.get("cover")
    else:
        inw, cover = _inw(inw)
    Y = collections.defaultdict(collections.Counter)
    for d in docs.values():
        c = Y[d["pub_m"][:4]]
        c["docs"] += 1
        c["shape_" + (d["shape"] or "fail")] += 1
        if _unfetched(d.get("status_raw")):
            c["unfetched"] += 1
        elif _bw(d["gid"], d["pub_m"], d.get("in_world"), inw, cover)[0]:
            c["f0_docs"] += 1
            c["f0_fail"] += d["shape"] is None
    xcik = []
    for a, k in R["dups"]:
        Y[docs[a]["pub_m"][:4]]["dup_period"] += 1
        if docs[a]["cik"] != docs[k]["cik"]:
            Y[docs[a]["pub_m"][:4]]["dup_period_xcik"] += 1
            xcik.append({"gid": docs[k]["gid"], "rd": docs[k]["rd"], "kept": [docs[k]["acc"], docs[k]["cik"]],
                         "dropped": [docs[a]["acc"], docs[a]["cik"]]})
    for p in pairs.values():
        c = Y[p["pub_m"][:4]]
        c["valid" if p["why"] is None else "miss_" + p["why"]] += 1
        c["valid_world"] += p["why"] is None and _bw(p["gid"], p["pub_m"], p.get("in_world"), inw, cover)[0]
        c["no_boundary"] += p["miss"] == "no_boundary"
        c["q1"] += bool(p["q1"])
        c["ix_switch"] += p["ix_switch"]
        c["gap_201_210"] += p["why"] == "gap" and p["gap"] is not None and 201 <= p["gap"] <= 210   # 53주 해 12-12-12-16 달력
    by_year = {}
    for y in sorted(Y):
        c = Y[y]
        nd = c["docs"] - c["dup_period"]
        both_shape = (c["valid"] + c["miss_transition"] + c["miss_pair_mismatch"] + c["miss_no_sim"] + c["miss_excluded"]
                      + c["miss_skip_suspect"])
        b = R["bounds"].get(int(y)) or {}
        by_year[y] = dict(sorted(c.items()), fail_rate=(c["f0_fail"] / c["f0_docs"] if c["f0_docs"] else None),
                          fail_rate_all_docs=(c["shape_fail"] / c["docs"] if c["docs"] else None),
                          transition_rate=(c["miss_transition"] / both_shape if both_shape else None),
                          q1_rate=(c["q1"] / (c["valid"] - c["no_boundary"]) if (c["valid"] - c["no_boundary"]) > 0 else None),
                          canon_docs=nd, cut=b.get("cut"), cut_n=b.get("n"), cut_src=b.get("src"),
                          cut_world_months=b.get("world_months"))
    lg = R["log"]
    n_ps = sum(v for k, v in lg.items() if k.startswith("builder_ps:"))
    n_dis = n_ps - lg.get("builder_ps:agree", 0)
    n_pa = lg.get("prev_acc_agree", 0) + lg.get("prev_acc_disagree", 0)
    rate = (n_dis / n_ps) if n_ps else None
    checks = {"builder_ps_n": n_ps, "builder_ps_disagree": n_dis, "builder_ps_disagree_rate": rate,
              "builder_ps_disagree_le_%.2f" % F_BUILDER_DISAGREE: (rate <= F_BUILDER_DISAGREE) if rate is not None else None,
              "builder_ps_by_reason": {k[len("builder_ps:"):]: v for k, v in sorted(lg.items())
                                       if k.startswith("builder_ps:") and k != "builder_ps:agree"},
              "prev_acc_n": n_pa, "prev_acc_disagree": lg.get("prev_acc_disagree", 0),
              "dup_period_xcik": xcik[:50], "dup_period_xcik_n": len(xcik)}
    mc = collections.Counter()
    for (g, t), row in R["gm"].items():
        if row["ch"] and _bw(g, t, None, inw, cover)[0]:
            mc[t] += 1
    months = list(months) if months is not None else sorted({t for (_, t) in R["gm"]})
    series = [mc.get(t, 0) for t in months]
    med = float(np.median(series)) if series else None
    f0 = {"pairs_year_ge_%d" % F0_PAIRS_YEAR: {y: by_year[y]["valid_world"] >= F0_PAIRS_YEAR for y in by_year},
          "fail_rate_le_%.2f" % F0_FAIL_RATE: {y: (by_year[y]["fail_rate"] is not None and by_year[y]["fail_rate"] <= F0_FAIL_RATE)
                                               for y in by_year},
          "ch_median_ge_%d" % F0_CH_MEDIAN: (med is not None and med >= F0_CH_MEDIAN)}
    return {"metric": R["metric"], "by_year": by_year, "ch_month": {"median": med, "min": min(series) if series else None,
            "max": max(series) if series else None, "n_months": len(series)}, "f0": f0, "checks": checks, "log": R["log"]}


# ════════════════════════════════════════════════════════════════════════
# R5 — 경보 사건
# ════════════════════════════════════════════════════════════════════════
_RX_ITEM = re.compile(r"^\d\.\d\d$")
_RX_H401 = re.compile(r"item\s*4\.01\b", re.I)
_RX_HNEXT = re.compile(r"item\s*(\d\.\d\d)\b", re.I)
_RX_TAILWORD = re.compile(r"([A-Za-z]+)$")
_INLINE_PRE = frozenset({"this", "in", "under", "to", "of", "see", "by", "and", "or", "per", "with", "pursuant", "such", "said",
                         "the", "our", "its", "that", "within", "herein", "above", "below", "required", "described"})


def parse_items(x):
    """submissions 'items'("2.02,9.01" 또는 목록) → ({'2.02', '9.01'}, 못 읽은 토큰)."""
    if x is None:
        return set(), []
    toks = x if isinstance(x, (list, tuple)) else re.split(r"[,;\s]+", str(x))
    ok, bad = set(), []
    for t in toks:
        t = str(t).strip()
        if not t:
            continue
        (ok.add(t) if _RX_ITEM.match(t) else bad.append(t))
    return ok, bad


def section_401(text):
    """(4.01 절 본문, 머리를 찾았나) — 랩 선택 ⑩. 끝 = 4.01 이 아닌 ‘Item d.dd’ 가운데 본문 속 참조가 아닌 첫 머리."""
    s = text or ""
    m = _RX_H401.search(s)
    if not m:
        return s, False
    rest = s[m.end():]
    for n in _RX_HNEXT.finditer(rest):
        if n.group(1) == "4.01":
            continue                                            # «this Item 4.01» · «Item 4.01(b)» — 같은 절
        w = _RX_TAILWORD.search(rest[:n.start()].rstrip())
        if w and w.group(1).lower() in _INLINE_PRE:
            continue                                            # «described in Item 9.01» — 본문 속 참조
        return rest[:n.start()], True
    return rest, True


def classify_401(text, st=None):
    """4.01 본문 → 'resign' · 'routine' · 'both'(→ 사임 · ⑨) · 'none' · 'no_text'. 규칙은 카드에 미리 고정한 정규식 그대로.
    st(Counter)를 주면 머리 찾음 · 절 길이 · 카드 정규식이 놓치는 문형 후보를 센다(⑩ · 판정엔 쓰지 않는다)."""
    if text is None:
        return "no_text"
    sec, found = section_401(text)
    s = re.sub(r"\s+", " ", sec.lower())
    r, o = RX_RESIGN.search(s), RX_ROUTINE.search(s)
    lab = "both" if (r and o) else "resign" if r else "routine" if o else "none"
    if st is not None:
        st["t401:hdr_" + ("found" if found else "missing")] += 1
        n = len(s)
        st["t401:len_" + ("lt200" if n < 200 else "lt1000" if n < 1000 else "lt5000" if n < 5000 else "ge5000")] += 1
        if lab in ("routine", "none") and RX_401_GAP.search(s):
            st["t401:spec_gap_candidate"] += 1                  # 카드 정규식 밖 사임 문형 후보(등록 동결 전 결정)
    return lab


def _label_401(t401, acc, st=None):
    if t401 is None or acc not in t401:
        return "no_text"
    v = t401[acc]
    if isinstance(v, str) and v in LABELS_401:
        return v
    if isinstance(v, dict):
        v = v.get("text") if v.get("text") is not None else v.get("label")
        if isinstance(v, str) and v in LABELS_401:
            return v
    return classify_401(v, st)


def _mi(ym):
    return int(ym[:4]) * 12 + int(ym[5:7])


def _reorg_sig(its, g, av, splice):
    """⑲ 재편 서명 — 'items' · 'splice' · None."""
    if its & R5_REORG_A and its & R5_REORG_B:
        return "items"
    if splice is not None:
        m = _mi(av[:7])
        if any(abs(_mi(x) - m) <= R5_REORG_SPLICE_M for x in splice(g)):
            return "splice"
    return None


def r5_events(recs, cal, gof=None, t401=None, splice=None):
    """정본 submissions 기록 → ({그룹: [사건]}, log, 4.01 판정 개수). 사건 = {type, win('a' 12개월 · 'b' 90일), acc, avail, form,
    reorg}. 그룹을 먼저 정하고 (그룹, accession) 으로 중복을 없앤다(⑱ · 입력 순서 무관). splice(g) → 효력 경계 달(⑲ · gof 가
    IssuerMap.group_of 면 그 지도에서)."""
    im = _im_of(gof)
    if splice is None and im is not None:
        splice = im.splice_months
    log, cand = collections.Counter(), {}
    for r in recs:
        form = str(r.get("form") or "").strip().upper()
        if form in R5_AMEND:
            log["skip_amend:" + form] += 1                       # 랩 선택 ⑪
            continue
        its = set()
        if form in ("8-K",) + R5_OTHER_8K:
            its, bad = parse_items(r.get("items"))
            if bad:
                log["items_unparsed"] += 1
            if not (its & R5_ALL_ITEMS):
                continue
            if form != "8-K":
                log["other_form_alarm_items:" + form] += 1       # 카드 서식 밖 — 사건으로 세지 않는다(⑲)
                continue
        elif form not in R5_NT:
            continue
        acc = str(r.get("acc") or "")
        if not acc:
            log["drop_no_acc"] += 1
            continue
        av, how = avail_of(r, cal)
        if av is None:
            log[_drop_key(how)] += 1
            continue
        g = r.get("gid")
        if not g and gof is not None and r.get("cik") is not None:
            g = gof(int(r["cik"]), _grp_month(r, av))
        if not g:
            log["drop_no_group"] += 1                            # 지도 밖 CIK — 같은 accession 의 그룹 기록은 따로 남는다(⑱)
            continue
        k = (str(g), acc)
        rank = (av, how, form, ",".join(sorted(its)), str(r.get("cik")))
        if k in cand:
            log["drop_dup_acc"] += 1
            if rank >= cand[k][0]:
                continue
        cand[k] = (rank, form, its, av, how)
    ev, c401 = collections.defaultdict(list), collections.Counter()
    for (g, acc), (_, form, its, av, how) in sorted(cand.items()):
        log["avail_" + how] += 1
        kinds = []
        if form in R5_NT:
            kinds.append((form, "a"))
        else:
            kinds += [(it, "a") for it in R5_A_ITEMS if it in its]
            if "4.01" in its:
                lab = _label_401(t401, acc, log)
                c401[lab] += 1
                if lab in RESIGN_CLASSES:
                    kinds.append(("4.01R", "a"))
            kinds += [(it, "b") for it in R5_B_ITEMS if it in its]
        sig = _reorg_sig(its, g, av, splice) if any(k in R5_REORG_TYPES for k, _ in kinds) else None
        for k, w in kinds:
            ro = sig if k in R5_REORG_TYPES else None
            ev[g].append({"type": k, "win": w, "acc": acc, "avail": av, "form": form, "reorg": ro})
            log["event:" + k] += 1
            if ro:
                log["reorg:%s:%s" % (k, ro)] += 1
    for g in ev:
        ev[g].sort(key=lambda e: (e["avail"], e["acc"], e["type"]))
    return dict(ev), dict(sorted(log.items())), dict(sorted(c401.items()))


def r5_alarm(evs, ym, d):
    """월 ym · 형성일 d 에 걸리는 사건 목록(랩 선택 ⑫ · 가용일 ≤ d)."""
    lo_m = Q.mshift(ym, -(R5_A_MONTHS - 1))
    dd = dt.date.fromisoformat(d)
    out = []
    for e in evs:
        if e["avail"] > d:
            break
        if e["win"] == "a":
            ok = lo_m <= e["avail"][:7] <= ym
        else:
            ok = (dd - dt.date.fromisoformat(e["avail"])).days < R5_B_DAYS
        if ok:
            out.append(e)
    return out


def r5_count(ev, members, cal):
    """멤버-월 → (행 {(t, ym): {flag, flag_xreorg, trig}}, 요약). 요약은 개수 · 연도 · 업종 · 사건 종류뿐이다(수익 없음).
    flag = 카드 그대로 · flag_xreorg = 재편 서명(⑲) 사건만으로 걸린 것을 뺀 판(진단)."""
    rows = {}
    S = {"n": 0, "flagged": 0, "flagged_xreorg": 0, "reorg_only": 0, "unresolved": 0, "fpi": 0,
         "by_year": collections.Counter(), "n_by_year": collections.Counter(), "by_year_xreorg": collections.Counter(),
         "by_sector": collections.Counter(), "by_sector_xreorg": collections.Counter(), "by_type": collections.Counter(),
         "by_type_xreorg": collections.Counter(), "by_win": collections.Counter()}
    for m in members:
        t, ym, g = m["t"], m["ym"], m.get("gid")
        S["n"] += 1
        S["n_by_year"][ym[:4]] += 1
        S["fpi"] += m.get("fpi") == 1
        if not g:
            S["unresolved"] += 1
            rows[(t, ym)] = {"flag": 0, "flag_xreorg": 0, "trig": [], "status": "unresolved"}
            continue
        d = cal.month_end(ym)
        trig = r5_alarm(ev.get(g, ()), ym, d) if d else []
        trx = [e for e in trig if not e.get("reorg")]
        f, fx = int(bool(trig)), int(bool(trx))
        rows[(t, ym)] = {"flag": f, "flag_xreorg": fx, "trig": [(e["type"], e["acc"], e["avail"]) for e in trig], "status": "ok",
                         "d": d}
        if f:
            S["flagged"] += 1
            S["by_year"][ym[:4]] += 1
            S["by_sector"][m.get("sector") or "?"] += 1
            for k in sorted({e["type"] for e in trig}):
                S["by_type"][k] += 1
            for w in sorted({e["win"] for e in trig}):
                S["by_win"][w] += 1
            S["reorg_only"] += not fx
        if fx:
            S["flagged_xreorg"] += 1
            S["by_year_xreorg"][ym[:4]] += 1
            S["by_sector_xreorg"][m.get("sector") or "?"] += 1
            for k in sorted({e["type"] for e in trx}):
                S["by_type_xreorg"][k] += 1
    for k in ("by_year", "n_by_year", "by_year_xreorg", "by_sector", "by_sector_xreorg", "by_type", "by_type_xreorg", "by_win"):
        S[k] = dict(sorted(S[k].items()))
    return rows, S


# ════════════════════════════════════════════════════════════════════════
# 공용 — Stage S 교체(Eg 상위 n 에서 표지 이름을 빼고 차순위로 채움)
# ════════════════════════════════════════════════════════════════════════
def fill_top(ranked, excluded, n=30):
    """(고른 n, 상위 n 에서 빠진 이름) — 차순위도 표지면 건너뛴다. 교체 수 n_r = len(빠진 이름)."""
    ex = set(excluded)
    return [x for x in ranked if x not in ex][:n], [x for x in ranked[:n] if x in ex]


def to_override(R, card="R2-LAZYRF"):
    """r_p0_adapt 정식 판 모양 — {"cards": {카드: {"CH": {월: [그룹]}, "CH_MISS": {월: [그룹]}}}}(월 = 신호월 t)."""
    ch, miss = collections.defaultdict(list), collections.defaultdict(list)
    for (g, t), row in sorted(R["gm"].items()):
        if row["ch"]:
            ch[t].append(g)
        if row["miss"]:
            miss[t].append(g)
    return {"cards": {card: {"CH": dict(sorted(ch.items())), "CH_MISS": dict(sorted(miss.items()))}},
            "src": "build/r_r2flags.py", "metric": R["metric"], "hash": r2_hash(R)}


def to_stagem_fp(R):
    """r_stagem 모양 — {(그룹, 월): {CH, CH_miss, dlog}} · dlog 는 창 안 마지막 유효 짝의 값(없으면 None — 쓰는 쪽이 채움+결측열)."""
    return {k: {"CH": float(v["ch"]), "CH_miss": float(v["miss"]), "dlog": v["dlog_raw"]} for k, v in R["gm"].items()}


def r5_flagsets(rows, members):
    """R5 정식 판 모양 — {"cards": {"R5-ALARM": {"ALARM": {월: [그룹]}, "ALARM_XREORG": {…}}}}(걸린 멤버-월의 그룹 · 전방 기록
    팔용). ALARM = 카드 그대로(1차) · ALARM_XREORG = 재편 서명 사건만으로 걸린 것을 뺀 진단판(⑲)."""
    out, outx = collections.defaultdict(set), collections.defaultdict(set)
    for m in members:
        r = rows.get((m["t"], m["ym"]))
        if r and r["flag"] and m.get("gid"):
            out[m["ym"]].add(m["gid"])
        if r and r.get("flag_xreorg") and m.get("gid"):
            outx[m["ym"]].add(m["gid"])
    return {"cards": {"R5-ALARM": {"ALARM": {k: sorted(v) for k, v in sorted(out.items())},
                                   "ALARM_XREORG": {k: sorted(v) for k, v in sorted(outx.items())}}},
            "src": "build/r_r2flags.py"}


def _h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:16]


def r2_hash(R):
    return _h({"pairs": R["pairs"], "gm": {"%s|%s" % k: v for k, v in R["gm"].items()}, "bounds": R["bounds"],
               "dups": R["dups"]})


# ════════════════════════════════════════════════════════════════════════
# selftest — 합성 자료만
# ════════════════════════════════════════════════════════════════════════
def _words(n, seed, vocab=None):
    rng = random.Random(seed)
    V = vocab or ["risk", "market", "supply", "customer", "regulation", "cyber", "tariff", "credit", "liquidity", "patent",
                  "litigation", "competition", "pandemic", "currency", "inflation", "labor", "climate", "debt", "tax", "data"]
    return " ".join(rng.choice(V) for _ in range(n))


def _doc(acc, gid, rd, utc, shape="B", n_rf=100.0, tfv=None, **kw):
    if tfv is None and kw.get("sim_rf") is None and kw.get("text_rf") is None:
        tfv = {"a": 1}                                   # 기본: 같은 단어빈도(유사도 1) — 주어진 SimRF 를 시험하는 문서는 비운다
    r = {"acc": acc, "gid": gid, "cik": kw.pop("cik", None), "form": kw.pop("form", "10-Q"), "rd": rd, "fd": utc[:10],
         "acc_utc": utc, "acc_et": None, "shape": shape, "shape_field": True, "status": None, "n_rf": n_rf, "ixbrl": None,
         "tf_rf": tfv, "tf_doc": None, "text_rf": None, "sim_rf": None, "sim_doc": None, "prev_acc": None}
    r.update(kw)
    return r


def _sub(acc, gid, form, items, utc, cik=None):
    return {"acc": acc, "gid": gid, "cik": cik, "form": form, "items": items, "fd": utc[:10], "rd": None, "acc_utc": utc,
            "acc_et": None, "doc": None}


PRICE_KEYS = ("stocks.json", "pit_px", "assets.json", "pxd", "load_world", "month_rows", "stock_path")


def _no_price_reads():
    """dry · selftest 밖의 모든 함수 본문(문서 문자열 제외)에 가격 · 수익 원천 이름이 없는지 — 정적 점검."""
    import ast
    with open(os.path.abspath(__file__), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in ("dry", "selftest", "_no_price_reads"):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                body = body[1:]
            for sub in body:
                for n in ast.walk(sub):
                    v = n.value if isinstance(n, ast.Constant) else (n.id if isinstance(n, ast.Name) else
                                                                       (n.attr if isinstance(n, ast.Attribute) else None))
                    if isinstance(v, str) and any(k in v for k in PRICE_KEYS):
                        bad.append((node.name, v[:40]))
    return not bad


def selftest():
    T = {}
    cal = Cal()
    # 아래 시험들은 짝 · 경계 · 창의 기계(옛 Q1 규칙 base)를 잰다 — 등록 규칙 bb_nochange 는 따로 시험한다(bb_nochange_rule)
    _rb = globals()["r2_build"]
    r2_build = lambda *a, **k: _rb(*a, **dict({"q1_rule": "base"}, **k))  # noqa: E731
    # ── 시각 · 달력 ────────────────────────────────────────────────
    u = dt.datetime
    T["et_dst_edges"] = (utc_to_et(u(2019, 3, 10, 6, 59, 59)) == u(2019, 3, 10, 1, 59, 59)
                         and utc_to_et(u(2019, 3, 10, 7, 0, 0)) == u(2019, 3, 10, 3, 0, 0)
                         and utc_to_et(u(2019, 11, 3, 5, 59, 59)) == u(2019, 11, 3, 1, 59, 59)
                         and utc_to_et(u(2019, 11, 3, 6, 0, 0)) == u(2019, 11, 3, 1, 0, 0)
                         and utc_to_et(u(2006, 4, 2, 7, 0, 0)) == u(2006, 4, 2, 3, 0, 0)
                         and utc_to_et(u(2006, 3, 20, 12, 0, 0)) == u(2006, 3, 20, 7, 0, 0))
    try:
        from zoneinfo import ZoneInfo
        z, rng, ok = ZoneInfo("America/New_York"), random.Random(20260925), True
        for _ in range(3000):
            t = u(2005, 1, 1) + dt.timedelta(seconds=rng.randrange(0, 26 * 365 * 86400))
            ref = t.replace(tzinfo=dt.timezone.utc).astimezone(z).replace(tzinfo=None)
            ok &= utc_to_et(t) == ref
        T["et_vs_zoneinfo_3000"] = bool(ok)
    except Exception:
        T["et_vs_zoneinfo_3000"] = "zoneinfo 없음 — 건너뜀"
    closed = ["2019-11-28", "2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09", "2022-06-20", "2024-03-29", "2021-07-05",
              "2016-12-26", "2023-01-02"]
    open_ = ["2021-12-31", "2026-09-22", "2026-09-24", "2019-11-29", "2022-06-17", "2010-12-31"]
    T["calendar_rule"] = all(not cal.is_td(d) for d in closed) and all(cal.is_td(d) for d in open_)
    T["month_end"] = cal.month_end("2019-11") == "2019-11-29" and cal.month_end("2020-05") == "2020-05-29"
    a1 = avail_of({"acc_utc": "2019-06-14T19:59:59.000Z"}, cal)[0]          # 15:59:59 EDT 금 → 그날
    a2 = avail_of({"acc_utc": "2019-06-14T20:00:00.000Z"}, cal)[0]          # 16:00 EDT 금 → 다음 월
    a3 = avail_of({"acc_utc": "2019-06-15T14:00:00Z"}, cal)[0]              # 토 → 월
    a4 = avail_of({"acc_utc": "2019-11-29T18:30:00Z"}, cal)[0]              # 조기폐장일 13:30 EST → 다음 거래일(③)
    a5 = avail_of({"acc_utc": "2019-11-29T17:59:00Z"}, cal)[0]              # 12:59 EST → 그날
    a6 = avail_of({"acc_utc": "2019-07-03T15:00:00Z"}, cal)[0]              # 7/3 반휴 11:00 EDT → 그날
    a7 = avail_of({"acc_utc": "2019-07-03T18:00:00Z"}, cal)[0]              # 7/3 14:00 EDT → 7/5(7/4 휴장)
    a8 = avail_of({"acc_et": "2019-06-14 15:30:00"}, cal)[0]                # ET 필드 그대로
    a9 = avail_of({"fd": "2019-06-14"}, cal)                                 # 시각 없음 → 다음 거래일(⑧)
    a10 = avail_of({"acc_utc": "2019-06-14T15:59:59-04:00"}, cal)[0]         # 오프셋 표기
    a11 = avail_of({"acc_utc": "20190614155959"}, cal)[0]                   # SGML 14자리 = ET → 그날
    a12 = avail_of({"acc_utc": "20190614160000"}, cal)[0]                   # 16:00 ET → 다음 거래일
    T["avail_rules"] = (a1 == "2019-06-14" and a2 == "2019-06-17" and a3 == "2019-06-17" and a4 == "2019-12-02"
                        and a5 == "2019-11-29" and a6 == "2019-07-03" and a7 == "2019-07-05" and a8 == "2019-06-14"
                        and a9 == ("2019-06-17", "fd_next") and a10 == "2019-06-14" and a11 == "2019-06-14"
                        and a12 == "2019-06-17")
    # ⑧b — 빌더 가용일 · 방법이 있으면 그것(방법 acc 에만 ③ 조기폐장 13:00) · 빌더 방법이 없으면 종전 규칙
    T["avail_builder"] = (avail_of({"avail": "2019-06-14", "avail_how": "fd_floor", "acc_utc": "2019-06-13T19:00:00Z"}, cal)
                          == ("2019-06-14", "builder")
                          and avail_of({"avail": "2019-11-29", "avail_how": "acc", "acc_utc": "2019-11-29T18:30:00Z"}, cal)
                          == ("2019-12-02", "builder_half")
                          and avail_of({"avail": "2019-11-29", "avail_how": "acc", "acc_utc": "2019-11-29T17:59:00Z"}, cal)
                          == ("2019-11-29", "builder")
                          and avail_of({"avail": "2019-06-17", "avail_how": "fd_etamb", "acc_utc": "2019-06-14T16:30:00Z"}, cal)
                          == ("2019-06-17", "builder")
                          and avail_of({"avail": "2019-06-15", "avail_how": "fd_late"}, cal) == ("2019-06-17", "builder_not_td")
                          and avail_of({"avail": "2019-06-13", "acc_utc": "2019-06-14T19:00:00Z"}, cal)[0] == "2019-06-14")
    # 등록 FPI 표지 칸(fpi_registered.tm_index) — 사양 칸 5 를 박아 두지 않는다
    _tmx = {"AAA": [["2017-01", "2017-12", "gA", 1, [1], 1, "dera", 0]]}
    T["fpi_registered_index"] = (IssuerMap({"tm": _tmx, "fpi_registered": {"field": "fpi_q", "tm_index": 7}}).resolve("AAA", "2017-06")
                                 == ("gA", 0) and IssuerMap({"tm": _tmx}).resolve("AAA", "2017-06") == ("gA", 1))
    # ── 텍스트 도구 ───────────────────────────────────────────────
    tb = tokens("Item 1A. Risk Factors. There have been no material changes to the risk factors disclosed in our 2016 "
                "Annual Report on Form 10-K.")
    tu = tokens("There have been no material changes from the risk factors previously disclosed, except as follows. "
                + _words(200, 1))
    tu2 = tokens("There have been no material changes to the risk factors. " + _words(150, 11))      # 160단어 — 150 문턱
    tf_ = tokens(_words(600, 2))
    tx = tokens(_words(300, 3))
    tlate = tokens(_words(250, 4) + " there has been no material change " + _words(300, 5))
    tnot = tokens("Our risk factors have not been materially changed since the annual report. " + _words(10, 6))
    T["shape_rules"] = (shape_of(tb)[0] == "B" and shape_of(tu)[0] == "U" and shape_of(tf_)[0] == "F"
                        and shape_of(tu2) == ("U", 160) and shape_of(tu2[:149]) == ("B", 149)
                        and shape_of(tx)[0] is None and shape_of(tlate)[0] == "F" and shape_of(tnot)[0] == "B"
                        and "#" not in " ".join(tb) and all(len(w) >= 2 for w in tb))
    T["cosine"] = (abs(cosine({"a": 2, "b": 1}, {"b": 1, "a": 2}) - 1) < 1e-15 and cosine({"a": 1}, {"b": 1}) == 0.0
                   and cosine({}, {"a": 1}) is None and abs(cosine({"a": 1, "b": 1}, {"a": 1}) - 1 / math.sqrt(2)) < 1e-15)
    # ── 짝 짓기 ───────────────────────────────────────────────────
    recs = [
        _doc("g1-151", "G1", "2015-03-31", "2015-05-01T14:00:00Z"),
        _doc("g1-152", "G1", "2015-06-30", "2015-07-31T14:00:00Z"),
        _doc("g1-153", "G1", "2015-09-30", "2015-10-30T14:00:00Z"),
        _doc("g1-153a", "G1", "2015-09-30", "2015-12-01T14:00:00Z", form="10-Q/A"),
        _doc("g1-161", "G1", "2016-03-31", "2016-04-29T14:00:00Z"),
        _doc("g2-151", "G2", "2015-03-31", "2015-05-01T14:00:00Z"),
        _doc("g2-152", "G2", "2015-06-30", "2015-07-31T14:00:00Z"),
        _doc("g2-161", "G2", "2016-03-31", "2016-04-29T14:00:00Z"),       # 3분기 10-Q 가 없다 → 바로 앞 = 2분기 · 275일
        _doc("ap-153", "AP", "2015-06-27", "2015-07-22T20:30:00Z"),       # 52/53주 회계연도
        _doc("ap-161", "AP", "2015-12-26", "2016-01-27T21:00:00Z"),
        _doc("ap-163", "AP", "2016-06-25", "2016-07-27T20:30:00Z"),
        _doc("ap-171", "AP", "2016-12-31", "2017-02-01T21:00:00Z"),       # 14주 1분기 · 189일
    ]
    R = r2_build(recs, cal)
    P = R["pairs"]
    T["pair_q1_to_prior_q3"] = (P["g1-161"]["prev"] == "g1-153" and P["g1-161"]["gap"] == 183 and P["g1-161"]["why"] is None
                                and P["g1-152"]["prev"] == "g1-151" and P["g1-151"]["why"] == "no_prior")
    T["pair_amend_ignored"] = "g1-153a" not in P and R["log"].get("drop_form:10-Q/A") == 1
    T["pair_gap_no_skip"] = P["g2-161"]["why"] == "gap" and P["g2-161"]["prev"] == "g2-152" and P["g2-161"]["gap"] == 275
    T["pair_52_53_week"] = (P["ap-161"]["gap"] == 182 and P["ap-161"]["why"] is None and P["ap-171"]["gap"] == 189
                            and P["ap-171"]["why"] is None)
    # 선행·후계 CIK 잇기(효력 구간) · 같은 기간 중복
    gmap = {401: [("GS", None, "2019-02")], 402: [("GS", "2019-03", None)], 501: [("GD", None, None)], 502: [("GD", None, None)]}

    def gof(c, ym):
        for g, a, b in gmap.get(c, ()):
            if (a is None or a <= ym) and (b is None or ym <= b):
                return g
        return None
    recs2 = [_doc("s-183", None, "2018-09-30", "2018-11-01T14:00:00Z", cik=401),
             _doc("s-191", None, "2019-03-31", "2019-05-01T14:00:00Z", cik=402),
             _doc("s-191old", None, "2019-03-31", "2019-05-02T14:00:00Z", cik=401),   # 효력 끝난 선행 CIK → 그룹 밖
             _doc("d-172a", None, "2017-06-30", "2017-08-01T14:00:00Z", cik=501),
             _doc("d-172b", None, "2017-06-30", "2017-08-01T15:00:00Z", cik=502),     # 같은 기간 공동 제출 → 늦은 것 버림
             _doc("d-171", None, "2017-03-31", "2017-05-01T14:00:00Z", cik=501),
             _doc("x-1", None, "2017-03-31", "2017-05-01T14:00:00Z", cik=999)]
    R2 = r2_build(recs2, cal, gof=gof)
    P2 = R2["pairs"]
    T["splice_across_ciks"] = P2["s-191"]["prev"] == "s-183" and P2["s-191"]["why"] is None and "s-191old" not in P2
    T["dup_period_keep_first"] = (R2["dups"] == [("d-172b", "d-172a")] and P2["d-172a"]["prev"] == "d-171"
                                  and R2["log"].get("drop_no_group") == 2)
    # 형태 전환 · 분리 실패 · 늦은 앞 문서 · 빌더 값 대조
    recs3 = [_doc("t-1", "T", "2017-03-31", "2017-05-01T14:00:00Z", shape="F", tfv={"a": 1}),
             _doc("t-2", "T", "2017-06-30", "2017-08-01T14:00:00Z", shape="B", tfv={"a": 1}),
             _doc("t-3", "T", "2017-09-30", "2017-11-01T14:00:00Z", shape="U", tfv={"a": 1}),
             _doc("t-4", "T", "2018-03-31", "2018-05-01T14:00:00Z", shape=None, tfv={"a": 1}),
             _doc("t-5", "T", "2018-06-30", "2018-08-01T14:00:00Z", shape="U", tfv={"a": 1}),
             _doc("f-1", "FF", "2017-03-31", "2017-05-01T14:00:00Z", shape="F", tfv={"a": 1, "b": 1}),
             _doc("f-2", "FF", "2017-06-30", "2017-08-01T14:00:00Z", shape="F", tfv={"a": 1}),
             _doc("l-1", "L", "2017-03-31", "2017-05-01T14:00:00Z"),
             _doc("l-2", "L", "2017-06-30", "2017-12-01T14:00:00Z", tfv={"a": 1}),    # 늦게 낸 2분기
             _doc("l-3", "L", "2017-09-30", "2017-11-01T14:00:00Z", tfv={"a": 1}),
             _doc("v-1", "V", "2017-03-31", "2017-05-01T14:00:00Z"),
             _doc("v-2", "V", "2017-06-30", "2017-08-01T14:00:00Z", sim_rf=0.5, prev_acc="v-1"),
             _doc("v-3", "V", "2017-09-30", "2017-11-01T14:00:00Z", sim_rf=0.4, prev_acc="v-1"),   # 빌더가 다른 짝
             _doc("v-4", "V", "2018-03-31", "2018-05-01T14:00:00Z", sim_rf=0.3)]
    R3 = r2_build(recs3, cal)
    P3 = R3["pairs"]
    T["shape_transition"] = (P3["t-2"]["why"] == "transition" and P3["t-3"]["why"] is None and P3["t-4"]["why"] == "fail_cur"
                             and P3["t-5"]["why"] == "fail_prev" and P3["f-2"]["why"] is None
                             and abs(P3["f-2"]["sim"] - 1 / math.sqrt(2)) < 1e-15)
    T["prior_late"] = P3["l-3"]["why"] == "prior_late" and P3["l-2"]["why"] is None
    T["builder_sim"] = (P3["v-2"]["why"] is None and P3["v-2"]["sim"] == 0.5 and P3["v-3"]["why"] == "pair_mismatch"
                        and P3["v-4"]["why"] is None and R3["log"].get("sim_given_unverified") == 1)
    # ── 경계(전년도 하위 20% · 공개연도 · 세계) ─────────────────────
    recs4 = []
    for k in range(1, 101):
        g = "B%03d" % k
        recs4 += [_doc(g + "-1", g, "2016-03-31", "2016-05-02T14:00:00Z"),
                  _doc(g + "-2", g, "2016-06-30", "2016-08-01T14:00:00Z", sim_rf=k / 100, prev_acc=g + "-1")]
    for g, s in (("C1", 0.20), ("C2", 0.208), ("C3", 0.21)):
        recs4 += [_doc(g + "-1", g, "2017-03-31", "2017-05-01T14:00:00Z"),
                  _doc(g + "-2", g, "2017-06-30", "2017-08-01T14:00:00Z", sim_rf=s, prev_acc=g + "-1")]
    recs4 += [_doc("Y-1", "Y", "2016-09-30", "2016-11-01T14:00:00Z"),
              _doc("Y-2", "Y", "2016-12-31", "2017-01-03T22:00:00Z", sim_rf=0.0, prev_acc="Y-1")]   # 가용 2017-01-04 → 2017 분포
    R4 = r2_build(recs4, cal)
    B4, P4 = R4["bounds"], R4["pairs"]
    T["boundary_prior_year"] = (B4[2017]["cut"] is not None and abs(B4[2017]["cut"] - 0.208) < 1e-12 and B4[2017]["n"] == 100 and P4["C1-2"]["q1"] is True
                                and P4["C2-2"]["q1"] is False and P4["C3-2"]["q1"] is False)
    T["boundary_pub_year_by_avail"] = P4["Y-2"]["pub_m"] == "2017-01" and sum(1 for p in P4.values() if p["why"] is None and p["pub_m"][:4] == "2017") == 4 and P4["Y-2"]["q1"] is True
    T["no_boundary_first_year"] = P4["B050-2"]["miss"] == "no_boundary" and P4["B050-2"]["q1"] is None and B4[2016]["cut"] is None
    # 등록 Q1 규칙(bb_nochange) — B-B 짝은 SimRF 1 로 경계 분포에 들고 Q1 이 될 수 없다 · 경계를 다시 잰다(F-F 는 그대로)
    recs5 = []
    for k in range(1, 101):
        g, sh = "Z%03d" % k, ("B" if k <= 50 else "F")
        recs5 += [_doc(g + "-1", g, "2016-03-31", "2016-05-02T14:00:00Z", shape=sh),
                  _doc(g + "-2", g, "2016-06-30", "2016-08-01T14:00:00Z", shape=sh, sim_rf=k / 100, prev_acc=g + "-1")]
    for g, sh, sv in (("D1", "F", 0.70), ("D4", "B", 0.10)):
        recs5 += [_doc(g + "-1", g, "2017-03-31", "2017-05-01T14:00:00Z", shape=sh),
                  _doc(g + "-2", g, "2017-06-30", "2017-08-01T14:00:00Z", shape=sh, sim_rf=sv, prev_acc=g + "-1")]
    Rb, Rn = _rb(recs5, cal, q1_rule="base"), _rb(recs5, cal)
    T["bb_nochange_rule"] = (abs(Rb["bounds"][2017]["cut"] - 0.208) < 1e-12 and abs(Rn["bounds"][2017]["cut"] - 0.708) < 1e-12
                             and Rb["pairs"]["D1-2"]["q1"] is False and Rn["pairs"]["D1-2"]["q1"] is True
                             and Rb["pairs"]["D4-2"]["q1"] is True and Rn["pairs"]["D4-2"]["q1"] is False
                             and Rn["pairs"]["D4-2"]["sim"] == 1.0 and Rn["pairs"]["D4-2"]["sim_raw"] == 0.10
                             and Rn["log"].get("bb_nochange") == 51 and Rn["q1_rule"] == "bb_nochange" and REG_Q1_RULE == "bb_nochange"
                             and REG_SHAPE_VER == "v3" and _rb(recs5, cal, metric="doc")["q1_rule"] is None)
    R4w = r2_build(recs4, cal, world=lambda g, ym: not (g.startswith("B") and int(g[1:]) <= 50))
    T["boundary_world_only"] = (R4w["bounds"][2017]["cut"] or 0) and abs(R4w["bounds"][2017]["cut"] - 0.608) < 1e-12 and R4w["bounds"][2017]["n"] == 50
    # ── CH_active · MISS · 월 경계 ─────────────────────────────────
    recs5 = []
    for k in range(50):                                                                       # 2016 분포 0.20..0.69 → 2017 경계 0.298
        recs5 += [_doc("zp-%d" % k, "Z%d" % k, "2016-03-31", "2016-05-02T14:00:00Z"),
                  _doc("z-%d" % k, "Z%d" % k, "2016-06-30", "2016-08-01T14:00:00Z", sim_rf=0.2 + k / 100)]
    recs5 += [_doc("c-0", "C", "2016-12-31", "2017-01-05T14:00:00Z"),
              _doc("c-1", "C", "2017-03-31", "2017-05-10T14:00:00Z", sim_rf=0.1),                  # Q1 → 05·06·07
              _doc("c-2", "C", "2017-06-30", "2017-08-09T14:00:00Z", shape=None),                  # 분리 실패 → MISS 08·09·10
              _doc("c-3", "C", "2017-09-30", "2017-11-08T14:00:00Z", sim_rf=0.9),                  # 앞 문서 실패 → MISS 11·12·01
              _doc("e-0", "E", "2016-12-31", "2017-01-05T14:00:00Z"),
              _doc("e-1", "E", "2017-03-31", "2017-05-31T20:30:00Z", sim_rf=0.1),                  # 5/31 16:30 EDT → 6/1
              _doc("o-0", "O", "2016-12-31", "2017-01-05T14:00:00Z"),
              _doc("o-1", "O", "2017-03-31", "2017-05-05T14:00:00Z", sim_rf=0.1),
              _doc("o-2", "O", "2017-06-30", "2017-07-10T14:00:00Z", shape=None)]                  # Q1 과 결측이 한 창 → CH 우선
    R5 = r2_build(recs5, cal)
    G = lambda g, t: gm_get(R5["gm"], g, t)
    T["ch_window_t2_t"] = ([G("C", m)["ch"] for m in ("2017-04", "2017-05", "2017-06", "2017-07", "2017-08")] == [0, 1, 1, 1, 0]
                           and G("C", "2017-04")["n"] == 0)
    T["miss_dummy"] = ([G("C", m)["miss"] for m in ("2017-07", "2017-08", "2017-09", "2017-10", "2017-11", "2017-12",
                                                    "2018-01", "2018-02")] == [0, 1, 1, 1, 1, 1, 1, 0]
                       and abs((R5["bounds"][2017]["cut"] or 0) - 0.298) < 1e-12 and G("C", "2018-02")["n"] == 0
                       and G("C", "2017-08")["why"] == ["fail_cur"] and G("C", "2017-11")["why"] == ["fail_prev"])
    T["month_edge_after_close"] = (R5["pairs"]["e-1"]["pub_m"] == "2017-06" and G("E", "2017-05")["n"] == 0
                                   and [G("E", m)["ch"] for m in ("2017-05", "2017-06", "2017-08", "2017-09")] == [0, 1, 1, 0])
    T["ch_beats_miss"] = (G("O", "2017-07")["ch"] == 1 and G("O", "2017-07")["miss"] == 0 and G("O", "2017-08")["ch"] == 0
                          and G("O", "2017-08")["miss"] == 1)
    # 유효 짝이 없는 창의 dlog 는 0 · 유효 짝의 dlog = log(n/n_prev)
    recs6 = [_doc("w-1", "W", "2017-03-31", "2017-05-01T14:00:00Z", n_rf=500.0),
             _doc("w-2", "W", "2017-06-30", "2017-08-01T14:00:00Z", n_rf=1000.0, sim_rf=0.9)]
    R6 = r2_build(recs5[:100] + recs6, cal)                                                   # Z 분포로 2017 경계가 선다
    T["dlog_len"] = (abs((R6["pairs"]["w-2"]["dlog"] or 0) - math.log(2)) < 1e-12 and gm_get(R6["gm"], "W", "2017-05")["dlog"] == 0.0
                     and abs(gm_get(R6["gm"], "W", "2017-10")["dlog"] - math.log(2)) < 1e-12
                     and gm_get(R6["gm"], "W", "2017-11")["dlog"] == 0.0)
    # ── 본문 경로(형태 · tf 를 여기서) · SimDoc 판 · 진단 제외 ──────
    txtB = "There have been no material changes to our risk factors. " + _words(20, 7)
    txtF1, txtF2 = _words(700, 8), _words(700, 9)
    recs7 = [_doc("x-1", "X", "2017-03-31", "2017-05-01T14:00:00Z", shape=None, shape_field=False, text_rf=txtF1,
                  tf_doc={"q": 1, "r": 1}, ixbrl=False),
             _doc("x-2", "X", "2017-06-30", "2017-08-01T14:00:00Z", shape=None, shape_field=False, text_rf=txtB,
                  tf_doc={"q": 1}, ixbrl=True),
             _doc("x-3", "X", "2017-09-30", "2017-11-01T14:00:00Z", shape=None, shape_field=False, text_rf=txtF2,
                  tf_doc={"q": 1}, ixbrl=True),
             _doc("x-4", "X", "2018-03-31", "2018-05-01T14:00:00Z", shape=None, shape_field=False, text_rf=txtF1,
                  tf_doc={"q": 1}, ixbrl=True)]
    R7 = r2_build(recs7, cal)
    R7d = r2_build(recs7, cal, metric="doc")
    R7x = r2_build(recs7, cal, exclude=excl_ixbrl)
    T["text_path"] = (R7["docs"]["x-2"]["shape"] == "B" and R7["docs"]["x-1"]["shape"] == "F"
                      and R7["pairs"]["x-2"]["why"] == "transition" and R7["pairs"]["x-3"]["why"] == "transition"
                      and R7["pairs"]["x-4"]["why"] is None
                      and abs(R7["pairs"]["x-4"]["sim"] - cosine(tf(tokens(txtF1)), tf(tokens(txtF2)))) < 1e-15)
    T["simdoc_no_shape_rule"] = (R7d["pairs"]["x-2"]["why"] is None and abs(R7d["pairs"]["x-2"]["sim"] - 1 / math.sqrt(2)) < 1e-15
                                 and R7d["pairs"]["x-3"]["sim"] == 1.0)
    recs7b = [dict(r, shape="F", shape_field=True, tf_rf={"a": 1}, text_rf=None) for r in recs7]
    R7b = r2_build(recs7b, cal, exclude=excl_ixbrl)
    T["exclude_ixbrl"] = (R7b["pairs"]["x-2"]["why"] == "excluded" and R7b["pairs"]["x-2"]["ix_switch"] is True
                          and R7b["pairs"]["x-3"]["why"] is None and R7x["pairs"]["x-2"]["why"] == "transition"
                          and gm_get(R7b["gm"], "X", "2017-08")["why"] == ["excluded"])
    R7c = r2_build(recs7b, cal, exclude=excl_covid)
    T["exclude_covid_pred"] = excl_covid({"pub_m": "2020-05"}, None) and not excl_covid({"pub_m": "2020-09"}, None) \
        and all(p["why"] != "excluded" for p in R7c["pairs"].values())
    # ── 순서 무관 · 결정성 ─────────────────────────────────────────
    big = recs + recs3 + recs4 + recs5
    h0 = r2_hash(r2_build(big, cal))
    sh = list(big)
    random.Random(7).shuffle(sh)
    T["order_invariant_hash"] = h0 == r2_hash(r2_build(sh, cal)) == r2_hash(r2_build(big, cal))
    # ── 어댑터 — 다른 필드 이름 · 열 묶음 · gzip · 효력 구간 지도 ──
    raw = {"note": "합성", "cols": ["accessionNumber", "cik", "formType", "reportDate", "acceptanceDateTime", "형태",
                                   "n_words_rf", "SimRF", "prev_acc", "isInlineXBRL"],
           "rows": [["0000000001-17-000001", "CIK0000000401", "10-Q", "2017-03-31", "2017-05-01T14:00:00.000Z", "B", 90, None,
                     None, 0],
                    ["0000000001-17-000002", 401, "10-Q", "2017-06-30", "2017-08-01T14:00:00.000Z", "B", 99, "0.93",
                     "0000000001-17-000001", 1],
                    ["0000000001-17-000003", 401, "10-Q", "2017-09-30", "2017-11-01T14:00:00.000Z", "fail", 10, None, None, 1]]}
    keyed = {"0000000002-17-000001": {"cik": 402, "form": "10-Q", "rd": "2017-03-31", "accepted_et": "2017-05-01 10:00:00",
                                      "shape": "U", "n_words_rf": 400, "parse_status": "ok"},
             "0000000002-17-000002": {"cik": 402, "form": "10-Q", "rd": "2017-06-30", "accepted_et": "2017-08-01 10:00:00",
                                      "shape": "U", "n_words_rf": 400, "parse_status": "split_fail"}}
    fd, p = tempfile.mkstemp(suffix=".json.gz")
    os.close(fd)
    try:
        with gzip.open(p, "wb") as fh:
            fh.write(json.dumps(raw).encode("utf-8"))
        A = load_tenq(p, "card")
    finally:
        os.remove(p)
    Ak = [adapt_tenq(r) for r in _records(keyed)]
    plan = {"rows": [{"acc": "p-1", "g": "gP", "rd": "2017-03-31", "avail_date": "2017-05-06", "form": "B", "SimRF": None,
                      "parse_status": "no_pair"},
                     {"acc": "p-2", "g": "gP", "rd": "2017-06-30", "accepted_et": "2017-08-01 17:10:00", "form": "F", "simrf": 0.4,
                      "parse_status": "form_switch", "prev_acc": "p-1"},
                     {"acc": "p-3", "g": "gP", "rd": "2017-09-30", "accepted_et": "2017-11-01T09:00:00", "shape": "F",
                      "SimRF": 0.7, "prev_acc": "p-2", "dlog_len_rf": 0.25, "ixbrl_switch": 1, "parse_status": "ok"}]}
    Rp = r2_build([adapt_tenq(r) for r in _records(plan)], cal)
    Pp = Rp["pairs"]
    T["adapter_plan_shape"] = (Rp["log"].get("form_assumed_10-Q") == 3 and Rp["docs"]["p-1"]["shape"] == "B"
                               and Rp["docs"]["p-1"]["avail"] == "2017-05-08" and Rp["log"].get("avail_given") == 1
                               and Rp["docs"]["p-2"]["avail"] == "2017-08-02" and Pp["p-2"]["why"] == "transition"
                               and Pp["p-3"]["why"] is None and Pp["p-3"]["sim"] == 0.7 and Pp["p-3"]["dlog"] == 0.25
                               and Pp["p-3"]["ix_switch"] is True and Rp["log"].get("builder_ps:agree") == 2
                               and Rp["log"].get("prev_acc_agree") == 2 and Rp["log"].get("dlog_given") == 1)
    im = IssuerMap({"tm": {"AAA": [["2017-04", "2017-12", "gA", 401, [401], 0, "dera", 0]],
                           "BRK.B": [["2017-04", "2017-12", "gB", 402, [402], 0, "dera", 0]],
                           "FPX": [["2017-04", "2017-12", "gF", 403, [403], 1, "dera", 1]],
                           "UNR": [["2017-04", "2017-12", None, None, [], None, "none", None]]},
                    "groups": {"gA": {"ciks": [[401, None, None, "dera_sym", "A"]]},
                               "gB": {"ciks": [[402, "2017-01", None, "dera_sym", "B"]]},
                               "gF": {"ciks": [[403, None, None, "dera_sym", "F"]]}}})
    RA = r2_build(A + Ak, cal, gof=im.group_of)
    PA = RA["pairs"]
    T["adapter_fields"] = (len(A) == 3 and A[0]["cik"] == 401 and A[0]["shape"] == "B" and A[1]["sim_rf"] == 0.93
                           and A[1]["ixbrl"] is True and A[2]["shape"] is None and PA["0000000001-17-000002"]["why"] is None
                           and PA["0000000001-17-000002"]["sim"] == 0.93 and PA["0000000001-17-000002"]["ix_switch"] is True
                           and PA["0000000001-17-000003"]["why"] == "fail_cur" and len(Ak) == 2 and Ak[1]["shape"] is None
                           and PA["0000000002-17-000002"]["why"] == "fail_cur" and RA["docs"]["0000000002-17-000001"]["gid"] == "gB")
    mem = [{"t": t, "ym": "2017-06", "gid": im.resolve(t, "2017-06")[0], "fpi": im.resolve(t, "2017-06")[1]}
           for t in ("AAA", "BRK-B", "FPX", "UNR", "ZZZ")]
    MR = member_rows(RA, mem)
    T["member_status"] = ([MR[(t, "2017-06")]["status"] for t in ("AAA", "BRK-B", "FPX", "UNR", "ZZZ")]
                          == ["ok", "ok", "fpi", "unresolved", "unresolved"] and MR[("BRK-B", "2017-06")]["gid"] == "gB")
    # ── R5 ────────────────────────────────────────────────────────
    T["r5_items"] = (parse_items("2.02,9.01") == ({"2.02", "9.01"}, []) and parse_items(["1.03", " 2.04"])[0] == {"1.03", "2.04"}
                     and parse_items("5,7") == (set(), ["5", "7"]) and parse_items(None) == (set(), []))
    tx401 = {
        "k1": "Item 4.01 Changes in Registrant's Certifying Accountant. On March 1, 2019, KPMG LLP informed the Company that it "
              "resigned as the independent registered public accounting firm.",
        "k2": "Item 4.01. Deloitte & Touche LLP declined to stand for re-election for the fiscal year 2020 audit.",
        "k3": "Item 4.01. On May 2, 2019, the Audit Committee dismissed Ernst & Young LLP.",
        "k4": "Item 4.01. KPMG declined to stand for re-appointment. The Audit Committee has commenced a selection process.",
        "k5": "Item 4.01. On May 2, the Audit Committee approved the dismissal of EY. Item 5.02 Departure of Directors. "
              "Mr. X resigned as Chief Financial Officer.",
        "k6": "Item 4.01. The Company engaged PricewaterhouseCoopers LLP as its new auditor.",
        "k7": "The Company was notified that its auditor will RESIGN   effective June 1.",
    }
    T["r5_401_rule"] = ([classify_401(tx401[k]) for k in ("k1", "k2", "k3", "k4", "k5", "k6", "k7")]
                        == ["resign", "resign", "routine", "both", "routine", "none", "resign"] and classify_401(None) == "no_text")
    subs = [_sub("n1", "GA", "NT 10-K", "", "2019-03-01T15:00:00Z"),                       # 10:00 EST → 3/1 · 12개월
            _sub("b1", "GA", "8-K", "2.02,2.05,9.01", "2019-01-15T15:00:00Z"),            # 2.05 · 90일
            _sub("ba", "GA", "8-K/A", "1.03", "2019-01-16T15:00:00Z"),                    # 정정본 → 뺀다
            _sub("b2", "GB", "8-K", "5.01", "2019-05-31T21:00:00Z"),                      # 17:00 EDT 금 → 6/3
            _sub("r1", "GC", "8-K", "4.01,9.01", "2018-06-15T14:00:00Z"),                 # 사임
            _sub("r2", "GD", "8-K", "4.01", "2018-06-15T14:00:00Z"),                      # 해임 → 빼지 않는다
            _sub("r3", "GD", "8-K", "4.01", "2018-07-16T14:00:00Z"),                      # 본문 없음
            _sub("r4", "GG", "8-K", "4.01", "2018-09-14T14:00:00Z"),                      # 두 쪽 다 → 사임(⑨)
            _sub("q1", "GE", "8-K", "3.01", "2020-01-10T15:00:00Z"),
            _sub("q2", "GE", "8-K", "4.02,2.06", "2020-02-03T15:00:00Z"),
            _sub("d0", "GF", "8-K", "2.04", "2019-03-01T15:00:00Z"),                      # 5/30(89일) 창 안 · 5/31(91일) 밖
            _sub("x", "GA", "10-Q", "", "2019-05-01T15:00:00Z")]
    ev, lg, c401 = r5_events(subs, cal, t401={"r1": tx401["k1"], "r2": tx401["k3"], "r4": {"text": tx401["k4"]}})
    types = {g: [e["type"] for e in v] for g, v in ev.items()}
    T["r5_events"] = (types == {"GA": ["2.05", "NT 10-K"], "GB": ["5.01"], "GC": ["4.01R"], "GE": ["3.01", "2.06", "4.02"],
                                "GF": ["2.04"], "GG": ["4.01R"]} and c401 == {"both": 1, "no_text": 1, "resign": 1, "routine": 1}
                      and lg.get("skip_amend:8-K/A") == 1 and ev["GB"][0]["avail"] == "2019-06-03")
    fl = lambda g, ym: bool(r5_alarm(ev.get(g, ()), ym, cal.month_end(ym)))
    flt = lambda g, ym, k: bool([e for e in r5_alarm(ev.get(g, ()), ym, cal.month_end(ym)) if e["type"] == k])
    T["r5_window_12m"] = ([flt("GA", m, "NT 10-K") for m in ("2019-02", "2019-03", "2020-02", "2020-03")]
                          == [False, True, True, False]
                          and [fl("GC", m) for m in ("2018-05", "2018-06", "2019-05", "2019-06")] == [False, True, True, False])
    T["r5_window_90d"] = ([bool([e for e in r5_alarm(ev["GA"], m, cal.month_end(m)) if e["type"] == "2.05"])
                           for m in ("2018-12", "2019-01", "2019-02", "2019-03", "2019-04")] == [False, True, True, True, False]
                          and [fl("GB", m) for m in ("2019-05", "2019-06", "2019-08", "2019-09")] == [False, True, True, False])
    T["r5_90d_edge"] = (bool(r5_alarm(ev["GF"], "2019-05", "2019-05-29")) and not r5_alarm(ev["GF"], "2019-05", "2019-05-30")
                        and (dt.date(2019, 5, 30) - dt.date(2019, 3, 1)).days == 90)
    memr5 = [{"t": g[1:], "ym": m, "gid": g, "fpi": 0, "sector": "S" + g[1]} for g in ("GA", "GB", "GC", "GD", "GE")
             for m in Q.months_between("2018-01", "2020-12")] + [{"t": "U", "ym": "2019-01", "gid": None, "fpi": None}]
    rows5, S5 = r5_count(ev, memr5, cal)
    T["r5_count"] = (S5["n"] == 181 and S5["unresolved"] == 1 and S5["flagged"] == 14 + 3 + 12 + 0 + 12
                     and S5["by_sector"] == {"SA": 14, "SB": 3, "SC": 12, "SE": 12} and S5["by_type"]["4.01R"] == 12
                     and S5["by_type"]["2.05"] == 3 and S5["by_win"] == {"a": 36, "b": 9}
                     and rows5[("A", "2019-03")]["flag"] == 1 and rows5[("D", "2018-06")]["flag"] == 0)
    ov = to_override(R5)["cards"]["R2-LAZYRF"]
    fp = to_stagem_fp(R6)
    R4m = r2_build(recs4, cal, min_n=101)
    T["exporters"] = ("C" in ov["CH"].get("2017-05", []) and "C" in ov["CH_MISS"].get("2017-08", []) and "C" not in ov["CH"].get("2017-08", [])
                      and fp[("W", "2017-08")]["dlog"] is not None and fp[("W", "2017-05")]["dlog"] is None
                      and R4m["bounds"][2017]["cut"] is None and R4m["pairs"]["C1-2"]["miss"] == "no_boundary"
                      and r5_flagsets(rows5, memr5)["cards"]["R5-ALARM"]["ALARM"]["2019-06"] == ["GA", "GB"]
                      and r5_flagsets(rows5, memr5)["cards"]["R5-ALARM"]["ALARM"]["2019-05"] == ["GA", "GC"])
    # ── 공용 교체 ────────────────────────────────────────────────
    rk = [chr(65 + i) for i in range(26)]
    pk, rm = fill_top(rk, {"B", "D"}, 3)
    T["fill_top"] = pk == ["A", "C", "E"] and rm == ["B"] and fill_top(rk, set(), 30)[0] == rk
    # ── 적대 검토에서 찾은 결함의 회귀 시험(scratchpad r2_adv · r2_adv2) ─────────────
    # ⑱ R5 — 지도 밖 CIK · 같은 그룹 두 CIK · 두 그룹 공동 제출이 섞여도 입력 순서와 무관하게 같은 사건
    gofx = lambda c, ym: {401: "GX", 402: "GY", 403: "GX"}.get(c)   # noqa: E731
    sA = _sub("0000000009-19-000001", None, "8-K", "1.03,2.04", "2019-01-29T15:00:00Z", cik=999)       # 지도 밖 자회사 CIK
    sC = _sub("0000000009-19-000002", None, "8-K", "2.06", "2019-03-01T15:00:00Z", cik=402)
    pool, base_ev, ok_ord = [sA, dict(sA, cik=401), sC, dict(sC, cik=403), dict(sC, cik=401)], None, True
    for seed in range(12):
        L = list(pool)
        random.Random(seed).shuffle(L)
        e_ = r5_events(L, cal, gof=gofx)[0]
        sig = sorted((g, e["acc"], e["type"]) for g, v in e_.items() for e in v)
        base_ev = sig if base_ev is None else base_ev
        ok_ord = ok_ord and sig == base_ev
    T["r5_dedupe_after_group"] = ok_ord and base_ev == [("GX", "0000000009-19-000001", "1.03"), ("GX", "0000000009-19-000001", "2.04"),
                                                        ("GX", "0000000009-19-000002", "2.06"), ("GY", "0000000009-19-000002", "2.06")]
    # R2 — 한 accession 이 두 그룹(공동 제출)이면 두 그룹 모두의 문서 · 지도 밖 CIK 는 따로 버림 · 순서 무관
    gof2 = lambda c, ym: {401: "GA", 402: "GB"}.get(c)   # noqa: E731
    dd_ = [_doc("acc-1", None, "2017-06-30", "2017-08-01T14:00:00Z", cik=c) for c in (999, 401, 402)]
    Ra, Rb = r2_build(dd_, cal, gof=gof2), r2_build(dd_[::-1], cal, gof=gof2)
    T["r2_co_filed_groups"] = (sorted(Ra["docs"]) == ["acc-1@GA", "acc-1@GB"] and r2_hash(Ra) == r2_hash(Rb)
                               and Ra["docs"]["acc-1@GB"]["gid"] == "GB" and Ra["log"].get("drop_no_group") == 1
                               and Ra["pairs"]["acc-1@GA"]["acc"] == "acc-1")
    # ⑦ 호출자 세계가 신호월(2016-08~)만 덮어도 2016 분포는 한 해 전체(덮지 않는 달은 in_world · 없으면 자료 전체)
    recsW = []
    for k in range(40):
        g = "W%02d" % k
        for j, (rd, fd, s) in enumerate((("2015-09-30", "2015-11-02", None), ("2016-03-31", "2016-05-02", 0.30),
                                         ("2016-06-30", "2016-08-01", 0.90), ("2016-09-30", "2016-11-01", 0.92),
                                         ("2017-03-31", "2017-05-01", 0.31 + k / 1000))):
            recsW.append(_doc("%s-%d" % (g, j), g, rd, fd + "T14:00:00Z", sim_rf=s))
    wset = {("W%02d" % k, m) for k in range(40) for m in Q.months_between("2016-08", "2018-12")}
    RW = r2_build(recsW, cal, world=wset)
    RW2 = r2_build([dict(r, in_world=not r["acc"].startswith("W0")) for r in recsW], cal, world=wset)
    q17 = sum(1 for p in RW["pairs"].values() if p["pub_m"][:4] == "2017" and p["q1"])
    T["boundary_world_midyear"] = (abs((RW["bounds"][2017]["cut"] or 0) - 0.30) < 1e-12 and RW["bounds"][2017]["n"] == 120
                                   and RW["bounds"][2017]["src"] == {"caller": 80, "uncovered_all": 40}
                                   and RW["bounds"][2017]["world_months"] == 5 and q17 == 0
                                   and RW2["bounds"][2017]["n"] == 90
                                   and RW2["bounds"][2017]["src"] == {"caller+in_world": 60, "caller+in_world:out": 20,
                                                                      "in_world": 30, "in_world:out": 10}
                                   and r2_density(RW)["by_year"]["2016"]["valid_world"] == 120)
    # ⑮ 진단판 제외가 다음 해 경계를 옮기지 않는다
    recsF = []
    for k in range(30):
        g = "F%02d" % k
        recsF += [_doc(g + "-0", g, "2019-12-31", "2020-02-03T14:00:00Z"),
                  _doc(g + "-1", g, "2020-03-31", "2020-05-01T14:00:00Z", sim_rf=0.30 + k / 1000),
                  _doc(g + "-2", g, "2020-06-30", "2020-08-03T14:00:00Z", sim_rf=0.31 + k / 1000),
                  _doc(g + "-3", g, "2020-09-30", "2020-11-02T14:00:00Z", sim_rf=0.90 + k / 10000),
                  _doc(g + "-4", g, "2021-03-31", "2021-05-03T14:00:00Z", sim_rf=0.85 + (k % 10) / 1000)]
    RF0, RFc = r2_build(recsF, cal), r2_build(recsF, cal, exclude=excl_covid)
    q21 = lambda R: sorted(p["acc"] for p in R["pairs"].values() if p["pub_m"][:4] == "2021" and p["q1"])   # noqa: E731
    T["exclude_keeps_main_bounds"] = (RFc["bounds"] == RF0["bounds"] and q21(RFc) == q21(RF0) == []
                                      and RFc["log"].get("excluded") == 60 and RFc["pairs"]["F00-1"]["why"] == "excluded"
                                      and RFc["pairs"]["F00-3"]["why"] is None)

    # ⑯ §C 빌더 행 모양(pair_status · in_world · prev_acc) — 대조가 살아 있고 불일치를 센다 · ⑰ F0 실패율 정의
    def brow(n, rd, fd, ps, shape="F", st="ok", prev=None, sim=None):
        return {"acc": "0000000001-16-%06d" % n, "cik": 1, "grp": "g1", "form": "10-Q", "fd": fd, "rd": rd,
                "acceptanceDateTime": fd + "T14:00:00.000Z", "accepted_et": fd + "T10:00:00", "avail": fd, "pub_m": fd[:7],
                "isInlineXBRL": 0, "parse_status": st, "shape": shape, "n_words_rf": 900 if shape else None, "in_world": True,
                "prev_acc": ("0000000001-16-%06d" % prev) if prev else None, "pair_status": ps, "SimRF": sim}
    bdoc = {"note": "합성", "fields": {"acc": "accession", "grp": "그룹"}, "coverage": {"n_docs": 6}, "dropped": [],
            "docs": [brow(1, "2016-03-31", "2016-05-02", "no_prior", shape="B"),
                     brow(2, "2016-06-30", "2016-08-01", "shape_switch", prev=1),
                     brow(3, "2016-09-30", "2016-11-01", "cur_fail", shape=None, st="fetch_404", prev=2),
                     brow(4, "2017-06-30", "2017-08-01", "gap_out", prev=3),
                     brow(5, "2017-09-30", "2017-11-01", "ok", prev=4, sim=0.8),
                     brow(6, "2018-03-31", "2018-05-01", "ok", shape="U", prev=4)]}          # 빌더는 ok · 여기선 형태 전환 · 앞 문서도 다름
    RB = r2_build([adapt_tenq(r) for r in _records(bdoc)], cal)
    DB = r2_density(RB)
    T["builder_crosscheck"] = (len(_records(bdoc)) == 6 and RB["log"].get("builder_ps:agree") == 5
                               and RB["log"].get("builder_ps:ok→transition") == 1 and RB["log"].get("prev_acc_disagree") == 1
                               and RB["log"].get("prev_acc_agree") == 4 and DB["checks"]["builder_ps_n"] == 6
                               and DB["checks"]["builder_ps_disagree_le_0.01"] is False
                               and DB["checks"]["builder_ps_by_reason"] == {"ok→transition": 1}
                               and RB["docs"]["0000000001-16-000001"]["in_world"] is True
                               and RB["log"].get("shape_field_absent") is None
                               and DB["by_year"]["2016"]["fail_rate"] == 0.0 and DB["by_year"]["2016"]["unfetched"] == 1
                               and abs(DB["by_year"]["2016"]["fail_rate_all_docs"] - 1 / 3) < 1e-12)
    vv = tenq_ver_view([{"acc": "v1", "shape": "U", "parse_status": "ok", "pair_status": "shape_switch", "shape_v3": "F",
                         "parse_status_v3": "ok", "pair_status_v3": "ok", "SimRF": None, "SimRF_v3": 0.5}], "v3")
    T["tenq_shape_ver"] = (vv[0]["shape"] == "F" and vv[0]["pair_status"] == "ok" and vv[0]["SimRF"] == 0.5
                           and tenq_ver_view([{"shape": "U"}], "card")[0]["shape"] == "U"
                           and adapt_tenq(vv[0])["shape"] == "F")
    af = adapt_tenq({"acc": "z1", "rd": "2017-03-31", "fd": "2017-05-01", "shape": None, "parse_status": "split_fail"})
    an = adapt_tenq({"acc": "z2", "rd": "2017-03-31", "fd": "2017-05-01", "rf_shape_wrong": "B"})
    T["shape_field_presence"] = af["shape_field"] is True and af["shape"] is None and an["shape_field"] is False
    # ① 동시 효력 두 CIK — 연속(직전 정본 CIK) · 주 CIK(issuer_map tm) 가 «다른 발행사끼리의 짝» 을 막는다
    gofo = lambda c, ym: {501: "GO", 502: "GO"}.get(c)   # noqa: E731
    tfA, tfB = {"alpha": 5, "beta": 3}, {"gamma": 4, "delta": 2}
    recsO = [_doc("a1", None, "2016-03-31", "2016-05-02T14:00:00Z", cik=501, tfv=tfA),
             _doc("b1", None, "2016-03-31", "2016-05-03T14:00:00Z", cik=502, tfv=tfB),
             _doc("a2", None, "2016-06-30", "2016-08-02T14:00:00Z", cik=501, tfv=tfA),
             _doc("b2", None, "2016-06-30", "2016-08-01T14:00:00Z", cik=502, tfv=tfB)]     # 이번 분기엔 502 가 먼저
    RO = r2_build(recsO, cal, gof=gofo)
    imO = IssuerMap({"tm": {"OKE": [["2016-01", "2016-12", "GO", 502, [501, 502], 0, "dera", 0]]},
                     "groups": {"GO": {"ciks": [[501, None, None, "x", "A"], [502, None, None, "x", "B"]]}}})
    ROp = r2_build(recsO, cal, gof=imO.group_of)
    T["dup_continuity_primary"] = (RO["pairs"]["a2"]["prev"] == "a1" and abs(RO["pairs"]["a2"]["sim"] - 1) < 1e-12
                                   and "b2" not in RO["pairs"] and RO["log"].get("dup_period_xcik") == 2
                                   and r2_density(RO)["checks"]["dup_period_xcik_n"] == 2
                                   and ROp["pairs"]["b2"]["prev"] == "b1" and abs(ROp["pairs"]["b2"]["sim"] - 1) < 1e-12)
    # ⑭ rd 없는 10-Q 는 막이(건너뛰기 없음) · tenk 로 빠진 2분기를 알아본다
    RE = r2_build([_doc("s-1", "S", "2017-03-31", "2017-05-01T14:00:00Z"), _doc("s-2", "S", None, "2017-08-01T14:00:00Z"),
                   _doc("s-3", "S", "2017-09-30", "2017-11-01T14:00:00Z")], cal)
    recsK = [_doc("k-1", "K", "2017-03-31", "2017-05-01T14:00:00Z"),
             _doc("k-3", "K", "2017-09-30", "2017-11-01T14:00:00Z"),                   # 2분기 10-Q 가 자료에 없다
             _doc("k-5", "K", "2018-03-31", "2018-05-01T14:00:00Z")]                   # 1분기 대 전년 3분기(사이에 10-K)
    RK0, RK, RKu = r2_build(recsK, cal), r2_build(recsK, cal, tenk={"K": ["2016-12-31", "2017-12-31"]}), r2_build(recsK, cal, tenk={})
    tk_ = tenk_from_sub([{"form": "10-K", "rd": "2017-12-31", "gid": "K"}, {"form": "10-KT", "rd": "2016-12-31", "gid": "K"},
                         {"form": "10-Q", "rd": "2017-09-30", "gid": "K"}, {"form": "10-K", "rd": None, "gid": "K"}])
    T["skip_back_blocked"] = (RE["pairs"]["s-3"]["why"] == "no_rd" and RE["pairs"]["s-3"]["prev"] == "s-2"
                              and RE["pairs"]["s-2"]["why"] == "no_rd" and RE["log"].get("no_rd_blocker") == 1
                              and RK0["pairs"]["k-3"]["why"] is None and RK["pairs"]["k-3"]["why"] == "skip_suspect"
                              and RK["pairs"]["k-5"]["why"] is None and RK["log"].get("long_gap_verified") == 1
                              and RKu["log"].get("long_gap_unverified") == 2 and tk_ == {"K": ["2016-12-31", "2017-12-31"]})
    # 53주 해 12-12-12-16 달력(COST 2023-05-07 → 11-26 = 203일) — 창 밖 결측을 연도별로 센다
    RCs = r2_build([_doc("cs-1", "CS", "2023-05-07", "2023-05-31T14:00:00Z"),
                    _doc("cs-2", "CS", "2023-11-26", "2023-12-20T14:00:00Z")], cal)
    T["gap_203_counted"] = (RCs["pairs"]["cs-2"]["gap"] == 203 and RCs["pairs"]["cs-2"]["why"] == "gap"
                            and r2_density(RCs)["by_year"]["2023"]["gap_201_210"] == 1)
    # ④ ⑬ 그룹은 제출월로 — 효력 끝 달 말일 마감 뒤 제출(가용은 다음 달)도 그 그룹
    gofp = lambda c, ym: {601: ("GP" if ym <= "2026-07" else None), 602: ("GP" if ym >= "2026-08" else None)}.get(c)   # noqa: E731
    evp = r5_events([_sub("p8", None, "8-K", "2.05", "2026-07-31T20:30:00Z", cik=601)], cal, gof=gofp)[0]
    Rpm = r2_build([_doc("pq", None, "2026-06-30", "2026-07-31T20:30:00Z", cik=601)], cal, gof=gofp)
    T["group_by_filing_month"] = ((evp.get("GP") or [{}])[0].get("avail") == "2026-08-03" and "pq" in Rpm["docs"]
                                  and Rpm["docs"]["pq"]["pub_m"] == "2026-08" and Rpm["docs"]["pq"]["gid"] == "GP")
    # ⑧ 달력 밖은 버리고 센다 · ADHOC 단일 원천
    T["calendar_edges"] = (avail_of({"acc_utc": "2003-06-02T14:00:00Z"}, cal) == (None, "out_of_cal")
                           and avail_of({"acc_utc": "2032-01-05T14:00:00Z"}, cal) == (None, "out_of_cal")
                           and avail_of({"fd": "2031-12-31"}, cal) == (None, "out_of_cal")
                           and r2_build([_doc("old", "O", "2003-03-31", "2003-05-01T14:00:00Z")], cal)["log"].get("drop_out_of_cal") == 1
                           and r5_events([_sub("o8", "GO", "8-K", "1.03", "2033-01-03T15:00:00Z")], cal)[1].get("drop_out_of_cal") == 1
                           and set(getattr(EV, "ADHOC", None) or ()) <= SPECIAL_CLOSED
                           and "2031-06-06" in _special_closed({"2031-06-06": "합성 임시휴장"}))
    # ⑩ 4.01 절 — 자기 참조 · 하위 머리 · 본문 속 참조에서 잘리지 않는다 · 카드 정규식 밖 문형은 후보로만 센다
    t_self = ("Item 4.01 Changes in Registrant's Certifying Accountant. (a) The Company provided KPMG with a copy of the "
              "disclosures in this Item 4.01. KPMG informed the Audit Committee that it resigned effective upon completion.")
    t_sub = "Item 4.01. (a) Previous accountant. Item 4.01(b) New accountant. Deloitte declined to stand for re-election."
    t_ref = "Item 4.01. As described in Item 9.01 below, the auditor resigned. Item 9.01 Financial Statements. Exhibit 16.1 resign"
    t_gap = "Item 4.01. On June 1, KPMG notified the Company that it will decline to stand for re-election."
    st4 = collections.Counter()
    labs = [classify_401(x, st4) for x in (t_self, t_sub, t_ref, t_gap, tx401["k5"])]
    T["r5_401_section_refs"] = (labs == ["resign", "resign", "resign", "none", "routine"]
                                and st4.get("t401:spec_gap_candidate") == 1 and st4.get("t401:hdr_found") == 5
                                and section_401(t_ref)[0].strip().endswith("resigned."))
    # ⑲ 재편 서명(진단) — 1차 표지는 카드 그대로 · 서명 사건만으로 걸린 이름-월은 xreorg 판에서 빠진다
    subsR = [_sub("ro1", None, "8-K", "1.01,2.01,3.01,3.03,5.02,5.03", "2019-04-01T15:00:00Z", cik=701),
             _sub("ro2", None, "8-K", "5.01", "2019-06-03T15:00:00Z", cik=701),
             _sub("ro3", None, "8-K", "3.01", "2020-06-01T15:00:00Z", cik=701),
             _sub("ro4", None, "8-K12B", "3.01,5.01", "2019-04-02T15:00:00Z", cik=701)]
    evr, lgr, _ = r5_events(subsR, cal, gof=lambda c, ym: {701: "GR"}.get(c), splice=lambda g: {"2019-05"} if g == "GR" else set())
    memR = [{"t": "R", "ym": m, "gid": "GR", "fpi": 0, "sector": "S"} for m in Q.months_between("2019-01", "2021-06")]
    rowsR, SR = r5_count(evr, memR, cal)
    fsR = r5_flagsets(rowsR, memR)["cards"]["R5-ALARM"]
    imR = IssuerMap({"tm": {}, "groups": {"GR": {"ciks": [[701, None, "2019-05-15", "x", "A"], [702, "2019-05-16", None, "x", "B"]]}}})
    evr2 = r5_events([_sub("ro2b", None, "8-K", "5.01", "2019-06-03T15:00:00Z", cik=702)], cal, gof=imR.group_of)[0]
    T["r5_reorg_sig"] = ({e["acc"]: e["reorg"] for e in evr["GR"]} == {"ro1": "items", "ro2": "splice", "ro3": None}
                         and lgr.get("other_form_alarm_items:8-K12B") == 1 and SR["flagged"] == 24 and SR["flagged_xreorg"] == 12
                         and SR["reorg_only"] == 12 and len(fsR["ALARM"]) == 24 and len(fsR["ALARM_XREORG"]) == 12
                         and "2020-06" in fsR["ALARM_XREORG"] and "2019-04" not in fsR["ALARM_XREORG"]
                         and imR.splice_months("GR") == {"2019-05"} and evr2["GR"][0]["reorg"] == "splice")
    # ── 금지 확인: 이 모듈의 R2/R5 경로는 가격 · 수익 파일을 열지 않는다 ─
    T["no_price_reads"] = _no_price_reads()
    ok = all(v is True or (isinstance(v, str) and "건너뜀" in v) for v in T.values())
    return {"ok": ok, "n": len(T), "failed": [k for k, v in T.items() if v is not True and not (isinstance(v, str))], "tests": T}


# ════════════════════════════════════════════════════════════════════════
# --dry — 실제 자료 구성·밀도(수익 없음 · 파일을 쓰지 않는다)
# ════════════════════════════════════════════════════════════════════════
def _first(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def dry(argv):
    def arg(k):
        return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else None
    out = {"note": "구성·밀도만 — 수익 · 가격을 읽지 않는다(달력 감사는 stocks.json 의 pxd_dates 날짜 칸만)", "inputs": {}}
    export = {"cards": {}, "src": "build/r_r2flags.py", "note": "정식 판(r_p0_adapt flags_override 모양) — 표지만 · 수익 없음"}
    cal = Cal()
    sp = os.path.join(DATA, "stocks.json")
    if os.path.exists(sp):
        grid = json.load(io.open(sp, encoding="utf-8")).get("pxd_dates") or []
        lo, hi = (grid[0], grid[-1]) if grid else (None, None)
        rule = [d for d in cal.days if lo and lo <= d <= hi]
        gs = set(grid)
        out["calendar_audit"] = {"grid": [lo, hi, len(grid)], "rule_not_in_grid": [d for d in rule if d not in gs][:40],
                                 "grid_not_in_rule": [d for d in grid if not cal.is_td(d)][:40]}
    imp = arg("--im") or os.path.join(DATA, "_issuer_map.json")
    im = IssuerMap.load(imp) if os.path.exists(imp) else None
    out["inputs"]["issuer_map"] = imp if im else "없음"
    months = Q.months_between(Q.FORM0, Q.mshift(Q.HOLD1, -1))
    members, members5, ws = [], [], None
    if im:
        secp = os.path.join(DATA, "pit_gics_sectors.json")
        sectors = json.load(io.open(secp, encoding="utf-8")) if os.path.exists(secp) else None
        members = members_from_im(im, months, sectors)
        members5 = members_from_im(im, months, sectors, drop_fin=False)          # R5 는 금융을 뺄 까닭이 없다(EG30 은 ex_fin=False)
        # 경계 세계(⑦) = 지도 전 기간(2014-06~)의 비금융 · 비 FPI 멤버-월 — 신호월만 담으면 첫해 경계가 빈다
        all_m = sorted({ym for (_, ym) in im.idx})
        ws = {(m["gid"], m["ym"]) for m in members_from_im(im, all_m, sectors) if m["gid"] and m["fpi"] != 1}
        out["members"] = {"n": len(members), "unresolved": sum(1 for m in members if not m["gid"]),
                          "fpi": sum(1 for m in members if m["fpi"] == 1), "fpi_null": sum(1 for m in members if m["fpi"] is None),
                          "n_r5_with_fin": len(members5), "boundary_world": [all_m[0] if all_m else None,
                                                                              all_m[-1] if all_m else None, len(ws)]}
    sb = _first([arg("--sub"), os.path.join(DATA, "_sub_pit.json.gz"), os.path.join(DATA, "_sub_pit.json")])
    out["inputs"]["sub"] = sb or "없음 — §B 빌드 대기"
    subrecs = load_sub(sb) if sb else None
    tenk = tenk_from_sub(subrecs, cal, gof=im.group_of if im else None) if subrecs else None
    tq = _first([arg("--tenq"), os.path.join(DATA, "_tenq_rf.json"), os.path.join(DATA, "_tenq_rf.json.gz"),
                 os.path.join(DATA, "_txt_sim.json")])
    out["inputs"]["tenq"] = tq or "없음 — §C 빌드 대기"
    sver = arg("--shape-ver") or REG_SHAPE_VER
    out["inputs"]["tenq_shape_ver"] = sver
    if tq:
        recs = load_tenq(tq, sver)
        for metric in ("rf", "doc"):
            R = r2_build(recs, cal, gof=im.group_of if im else None, world=ws, metric=metric)
            out["r2_" + metric] = r2_density(R, months)
            out["r2_" + metric]["hash"] = r2_hash(R)
            if metric == "rf":
                export["cards"].update(to_override(R)["cards"])
            if metric == "rf" and members:
                MR = member_rows(R, members)
                c = collections.Counter(v["status"] for v in MR.values())
                out["r2_rf"]["member_status"] = dict(c)
            if metric == "rf" and tenk:                           # ⑭ 건너뛰기 대조판(1차 판은 카드 그대로 · 차이만 싣는다)
                Rt = r2_build(recs, cal, gof=im.group_of if im else None, world=ws, metric=metric, tenk=tenk)
                out["r2_rf"]["tenk_check"] = {k: v for k, v in Rt["log"].items() if k.startswith("long_gap")}
                out["r2_rf"]["tenk_check"]["skip_suspect"] = sum(1 for p in Rt["pairs"].values() if p["why"] == "skip_suspect")
    if subrecs is not None:
        t4p = arg("--t401") or _first([os.path.join(DATA, "_ev_401.json"), os.path.join(DATA, "_ev_401.json.gz")])
        t401 = load_t401(t4p) if t4p else None
        out["inputs"]["t401"] = t4p or "없음 — 4.01 은 모두 no_text 로 센다"
        ev, lg, c401 = r5_events(subrecs, cal, gof=im.group_of if im else None, t401=t401)
        rows5, S = r5_count(ev, members5, cal) if members5 else ({}, None)
        out["r5"] = {"log": lg, "c401": c401, "summary": S}
        egp = os.path.join(DATA, "_eg_q5_scores_pitgics.json")      # Eg 예측치(점수만 · 수익 아님) — EG30 근사 부분집합
        if members5 and os.path.exists(egp):
            egm = (json.load(io.open(egp, encoding="utf-8")).get("months") or {})
            by_m = collections.defaultdict(list)
            for m in members5:
                sc = (egm.get(m["ym"]) or {})
                v = sc.get(m["t"], sc.get(m["t"].replace(".", "-")))
                if v is not None and m.get("gid"):
                    by_m[m["ym"]].append((-float(v), m["t"], m))
            sub_m = [x[2] for ym in sorted(by_m) for x in sorted(by_m[ym])[:30]]
            _, S30 = r5_count(ev, sub_m, cal)
            out["r5"]["eg_top30_approx"] = {"note": "월별 Eg 상위 30(3개월 리밸런스 · 편입 필터 무시 — 근사)",
                                            **{k: S30[k] for k in ("n", "flagged", "flagged_xreorg", "reorg_only", "by_sector",
                                                                   "by_type", "by_type_xreorg")}}
        if members5:
            export["cards"].update(r5_flagsets(rows5, members5)["cards"])
    xp = arg("--export")
    if xp and export["cards"]:                                  # 명시한 경로에만 쓴다(기본은 아무것도 쓰지 않는다)
        with open(xp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(export, ensure_ascii=False, separators=(",", ":")) + "\n")
        out["exported"] = {"path": xp, "cards": sorted(export["cards"])}
    return out


def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if "--dry" in a:
        print(json.dumps(dry(a), ensure_ascii=False, indent=1, default=str))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
