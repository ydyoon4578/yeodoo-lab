#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/r_r1_flags.py — RBATCH R1-OPPSELL 내부자 표지: CMP 루틴/기회주의 분류 · OS/RS 월 더미 · Stage S «OS 활성» · 쌍둥이 T1~T6

무엇을·왜.
  R1 의 Stage M 회귀(§E rbatch_mech.py)와 Stage S 단계(§E rbatch_run.py)가 먹는 표지를 **한 곳에서** 만든다.
  같은 표지를 엔진·러너·전방 원장(data/_qfwd/flags/)이 저마다 만들면 반드시 갈린다(이 저장소가 되풀이 밟은 결함).
  🚨 이 파일은 수익을 한 줄도 읽지 않는다. 실제 표지와 실제 미래 수익의 관계는 등록 뒤 한 번 굽는 측정이다
     (PREREG RBATCH · batch_design_changes 1 · data_build_plan «등록 전에는 어떤 플래그의 수익 관계도 계산하지 않는다»).
     --selftest 는 합성 자료만, --dera-check 는 파싱 개수만 찍는다.

규칙(사양 R1 rule (2)~(6) · params · §A «행 단위 규칙» 그대로 — 문턱·창을 여기서 바꾸지 않는다).
  1 행      Form 4 · 4/A 의 NONDERIV 행 가운데 P(A/D = A) · S(A/D = D). 금액 하한 없음 · 10b5-1 로 빼지 않음(1차).
            가용일 = FILING_DATE 다음 NYSE 거래일(DERA 에는 접수 시각이 없다) · 사건월 = 가용일이 속한 달.
            TRANS_DATE > FILING_DATE 인 행은 버리고 센다.
  2 정정본  자기 공시일에 들어온다. (발행사 그룹, 보고자, 거래일, 코드, 수량, 단가)로 중복을 지우고 **첫 공시만** 남긴다.
            4/A 행의 (그룹, 보고자, 거래일, 코드)가 앞선 **다른** 제출의 행에서 이미 나왔는데 수량·단가만 다르면 새 사건이 아니라
            **정정**이다(선언 q — 2026-09-25 등록 전 수정): 4/A 행은 세지 않는다(count = False · corr = 2). 원 행은 가용일 · 표지 ·
            **수량 · 단가 · 금액(제출된 그대로 — 등록 1차)** 이 그대로이고, 고친 값은 감사 칸(shc · pxc · usdc · corr = 1)에만 싣는다
            (선언된 민감도 T1C 만 그 값을 쓴다 · 선언 q 2026-09-26 개정).
            4/A 행의 (그룹, 보고자, 코드, 수량, 단가)가 그 4/A 가 고치는 제출(DATE_OF_ORIG_SUB = 그 행의 제출일)의 «살아 있는» 행과 같고
            거래일만 다르면 **거래일 정정**이다(선언 q2 — 2026-09-26 등록 전 수정): 4/A 행은 세지 않고(count = False · corr = 3)
            원 행의 가용일 · 사건은 그대로 · 고친 거래일은 **분류 이력에만** 쓴다(원 행 tdh).
  3 강제 매도(sell-to-cover) 행에 연결된 각주(*_FN 열)에만 STC_RX 를 건다. 걸린 행은 재량 매도에서도, 분류 이력에서도 뺀다
            (코드 F 와 같은 비재량 처분). REMARKS 에는 걸지 않는다. 'non-discretionary' 갈래는 같은 문장 80자 안에 원천징수·세금
            (withh · tax) 맥락이 있어야 한다(선언 p — 2026-09-25 등록 전 수정). 식은 이 파일에 한 벌 — ins_pit_build · ins_daily 가 import 한다.
  4 분류    매년 1월 첫 거래일 D_Y 에 (보고자 CIK, 발행사 그룹) 단위. 가용일 ≤ D_Y 인 Form 4/4A P·S 행만(Form 5 · 강제 매도 제외 ·
            어느 행 · 어느 보고자가 들어가는지는 선언 r 에 정확히 적었다).
            거래일 기준 직전 3개 달력연도 Y−3·Y−2·Y−1 각각에 ≥ 1건이어야 분류한다.
            세 해 모두 거래한 같은 달이 있으면 R(루틴), 없으면 O(기회주의), 한 해라도 비면 U(분류 불가).
            자료 첫날 뒤로 3년이 다 차지 않은 해(Y − 3 < HIST_Y0)는 N(자료 부족 — U 와 따로 센다).
  5 더미    OS(g, t) = 달 t 에 가용된 기회주의 매도 ≥ 1 → 1 · RS 같은 방식. 분류 불가 보고자는 OS 에도 RS 에도 넣지 않는다.
  6 공동    공동 제출은 행을 **제출당 한 번만** 센다. 분류 이력에는 그 제출의 **모든 보고자**에게 붙인다.
  7 Stage S OS 활성(r) = 가용월 r−2..r 가운데 OS = 1 이 하나라도 있음. Eg 상위 30 에서 빼고 OS 비활성 차순위로 채운다.

선언된 선택(사양 문구가 정하지 않은 곳 — 여기 한 번 고정한다. 등록 문서에 그대로 옮긴다).
  a 분류 적용 연도 = **행의 거래일 연도 Y** 의 분류(D_Y). CMP 와 같다(그해 거래는 그해 초 분류). D_Y ≤ 가용일 이 늘 성립한다
    (가용일은 FILING_DATE ≥ TRANS_DATE ≥ Y-01-01 뒤의 거래일이다) → 시점정확. 12월 거래가 1월에 가용되면 사건월은 1월,
    분류는 전년 D 의 것이다.
  b 공동 제출의 표지 배정(JOINT_RULE): 그 행의 내부자 관계 보고자 가운데 O 가 하나라도 → O · 아니면 R → R · 아니면 N → N ·
    아니면 U. 보고자 분류가 갈린 행 수를 센다(밀도 보고서).
  c 정정 중복은 보고자마다 본다 — 모든 보고자 키가 앞선 **다른 제출**에서 이미 나온 행은 버린다. 일부만 새로우면 그 행은
    **표지에서 세지 않고**(거래당 한 번) 새 보고자의 분류 이력에만 붙인다. 실측 2016Q3 37건 = 보고자 10인 상한 때문에 한 거래를
    연속 접수번호 둘로 쪼갠 펀드 묶음 공동 제출(…133529 → …133530 등)과 보고자를 더한 정정본이었다 — 남기면 같은 거래가 두 번 센다.
    같은 제출 안의 같은 값 두 행(직접·간접 두 로트)은 지우지 않는다. 원본을 다시 낸 4(정정이 아닌 재제출)도 같은 규칙.
  d 분류 이력의 보고자 = 제출의 모든 보고자(사양 문구 · 관계를 거르지 않는다). 표지 행의 보고자 = 관계에 Officer · Director ·
    TenPercentOwner 가 들어 있는 보고자(부분 문자열 — DERA 는 'TenPercentOwnerOther' 처럼 붙여 쓴다).
  e P 는 A/D = A, S 는 A/D = D 만 쓴다(어긋나면 버리고 센다).
  f 표지가 N(자료 부족) 행을 품은 그룹-월: O 가 있으면 OS = 1(확실), 없으면 OS = None(모름). RS 같다.
    자료 창(DERA 분기 범위) 밖 달과 창 끝에서 덜 찬 달은 None 이다 — 조용히 0 으로 채우지 않는다.
  g 10b5-1 표지(쌍둥이 T1·T2 전용 · 1차에는 쓰지 않는다): 행에 연결된 각주 + 제출 REMARKS 에서 PLAN_RX 적중 수 > 부정문(NEG_RX)
    적중 수면 1. 제출일 2023-04-01 부터는 AFF10B5ONE = 1 과 OR(그 전 체크박스는 소급 열이라 쓰지 않는다). 분류 이력은
    건드리지 않는다 — 표지 행에서만 뺀다(두 가지를 한꺼번에 바꾸지 않기 위해).
  h 행 금액 = TRANS_SHARES × TRANS_PRICEPERSHARE. 단가가 비면 금액 없음(T1 의 $10만 문턱에서 빠진다 · 수를 센다).
  i FPI 표지가 null(모름)인 멤버-월은 Section 16 적용으로 본다(issuer_map F0 와 같다) — 수를 따로 센다. FPI 표지 = 지도의
    등록 표지(_issuer_map.json fpi_registered — 2026-09-25 권고 fpi_q: 직전 정기보고가 10-Q 면 FPI 아님 · TEAM 2022-11..2023-07 ·
    NXPI 2019-10..2020-01 이 사양 칸과 다르다). IssuerMap.members 는 그 칸을 읽는다(사양 칸은 fpi_spec 으로 따로 싣는다).
  j Stage S 채움: 차순위 가운데 OS 비활성이 **확인된** 이름(off)과 FPI(구조적으로 비활성)를 Eg 순서대로. 그룹 미해결 · 표지 None
    이름은 비활성을 확인할 수 없으니 채움에서 건너뛴다(n_skip_fill). 상위 30 안의 FPI 와 그런 이름은 그대로 둔다(걸러낼 수
    없다) — 편입마다 수를 보고한다(n_fpi_top · n_unres_top · n_unk_top).
  k 미리 정리된 캐시(§A 패널 cnt 칸)의 «세지 않음(cnt = 0)» 은 prepare 가 **지키고**, prepare 자신의 판정과 AND 로 묶는다
    (어느 쪽이든 «이미 센 거래» 라 하면 세지 않는다 — 한 거래를 두 번 세는 쪽으로는 절대 기울지 않는다). 패널이 지운 보고자(odup)를
    되붙이지 않은 레코드를 넘겨도 같은 결과가 나온다(selftest cache_roundtrip_ok). 해 일부만 읽으면 앞 해의 첫 공시가 없어도
    cnt = 0 행은 세지 않는다 — 전체 자료의 판정이 맞다.
  l 늦은 공시 · 정정은 사양대로 «자기 공시일» 사건이다 — 최대 지연 문턱을 두지 않는다(두려면 등록 전 새 모수). 대신 밀도 보고서에
    지연 > STALE_REPORT_DAYS(365일 · 보고용일 뿐 규칙이 아니다) 인 표지 행 수 · 그런 행만으로 OS = 1 이 된 칸 수 · 4/A 가 끼어
    (그룹, 보고자, 거래일, 코드) 가 두 사건월에 걸친 수를 싣는다(stale · corrections) — 등록 문서에 옮긴다. 선언 q 뒤로는
    세는 행(count = True)에서 그런 키가 0 이어야 한다(정정 행은 세지 않는다) · broad 는 세지 않는 행까지 본 옛 정의다.
  m T4 는 보고자 라벨에서 U → O 로 **먼저** 바꾼 뒤 JOINT_RULE 을 건다(보고자 [R, U] 인 공동 행 = T4 에서 O · [N, U] = O).
    그래서 T4 의 개수는 1차 O + U 와 다르다 — cikmonth 의 t4_os_n · t4_rs_n 을 읽을 것(1차 O + U 로 다시 만들지 말 것).
  n T2 전후 분할은 **가용월**(SPLIT_T2) 기준이고 체크박스 OR 은 **제출일**(AFF_FROM) 기준이다 — 2023-03-31 제출(2023-04-03 가용)
    행은 'post' 에 들지만 체크박스를 쓰지 않는다(수: by_year S_post_prebox).
  o 대조 C1 은 OS 활성 이름을 후보에서도 채움에서도 뺀다(pick_set exclude) — 겹치면 C1 이 Stage S 와 같은 이름을 빼서 «분류가
    일하는지» 대조가 흐려진다. 대조 C2(전체 매도 $/시총)는 점수 ≤ 0(매도 없음)을 순위에 넣지 않고 모자라면 시드 무작위로 채운다
    (pick_c2 · n_nosale 보고) — 매도 없는 이름을 Eg 순서로 고르면 늘 최상위 Eg 이름을 빼게 된다.
  p 강제 매도 식의 'non-discretionary' 갈래는 원래 맨 낱말이었다. 그러면 «sold pursuant to a written non-discretionary Rule 10b5-1(c)
    sales plan» 같은 10b5-1 계획 각주가 강제 매도로 빠진다(실측 DERA 2011Q1..2026Q2 Form 4/4A: 그 갈래에 걸린 S 행 174 · 그 갈래로만
    걸린 130행이 모두 10b5-1 계획 매도 · 2016 에 67행). 등록 전에 그 갈래를 STC_ND = 'non-discretionary[^.]{0,80}(withh|tax)' 로
    좁혔다(새 갈래는 옛 갈래의 부분집합 — 새 식은 행을 더 빼지 않고 덜 뺄 뿐이다). 옛 식은 STC_RX_V1 로 감사용으로만 남긴다
    (행 칸 stc_v1 · 해마다 stc_v1_only = 옛 식으로는 빠지고 새 식으로는 남는 내부자 매도 행). stc_nd = 새 갈래로만 걸린 행(실측 0).
  q 정정(4/A)은 새 사건이 아니다. 4/A 행의 어느 보고자라도 여섯 칸 키로는 새로운데 (그룹, 보고자, 거래일, 코드) 가 앞선 다른 제출
    (원본 4 · 앞 4/A · 정정 행 포함)의 행에서 이미 나왔으면 그 행은 정정 행이다 — count = False · corr = 2 · 그 보고자(ocor)는 분류
    이력에 붙이지 않는다(원 행이 원 가용일로 이미 싣는다). 여섯 칸 키가 같은 보고자는 전처럼 지운 보고자(odup), 어느 쪽도 아닌
    보고자는 새 보고자(own — 이력에만)다. 짝: 한 4/A 안에서 (그룹, 거래일, 코드) 가 같은 정정 행을 SK 순으로 하나씩, 앞선 제출의
    «살아 있는» 행(정정 행이 아니고 · 이 4/A 가 같은 값으로 다시 적어 확인한 행이 아닌 것) 가운데 보고자가 겹치는 첫 행(제출 순서)에
    짝짓는다. 짝지은 원 행은 corr = 1 · ctgt = [정정 접수번호, SK] · 고친 값 shc · pxc · usdc(아래 🔒 — 원 행 값은 바꾸지 않는다). 가용일 ·
    표지(stc · p10 · aff) · 보고자 · 수량 · 단가는 원 행 그대로다. 짝이 없는 정정 행(4/A 로트가 원 행보다 많다)은 값을 옮기지 않고 사건도 아니다
    (corr = 2 · ctgt 없음 · corr_unpaired 로 센다). 정렬 = (제출일, 원본 먼저, 접수번호, SK 수치) — ins_pit_build.clean 과 같은 순서.
    짝은 패널에 적는다(정정 행의 ctgt = [원 행 접수번호, SK]) — 패널에는 4/A 가 같은 값으로 다시 적은(지워진) 행이 없어서 «확인» 을
    다시 알 수 없으므로, 캐시 레코드가 짝을 가져오면(corr = 2 · ctgt) prepare 는 다시 찾지 않고 그 짝을 쓴다(선언 k 와 같은 이치).
    🔒 2026-09-26 개정(등록 전 · 검토 지적 — 값을 원 가용월로 앞당기면 4/A 가용일에야 알려진 값을 쓰고, «빠뜨린 로트를 더한» 4/A 가
    원 로트 값을 덮는다): **등록 1차 = 제출된 그대로의 값(as-filed) · 원 가용월.** 원 행의 shares · price · usd 는 바꾸지 않는다.
    짝지은 4/A 의 값은 감사 칸 shc · pxc · usdc(corr = 1 · 여러 번 고치면 마지막 값)에만 싣고, 그 값을 쓰는 곳은 선언된 민감도 T1C
    (T1 과 같고 금액만 고친 값 · cikmonth t1c_os_n · t1c_os3) 하나다. 1차 OS · RS 는 값을 보지 않는다(금액 하한 없음).
    짝 짓기(확인 · 여러 로트)는 «지금 값»(고친 값이 있으면 그것)으로 비교한다 — 짝 결과는 개정 전과 같다.
    옛 규칙(여섯 칸 키만 · 4/A 가 자기 공시월의 새 사건)은 §A 패널의 cnt6 · ocor 칸으로 재현한다(cnt6 = 옛 규칙의 cnt ·
    수량 · 단가는 원래 제출 값 그대로 · corr = 2 · 3 행은 보고자 own + ocor).
  q2 거래일 정정(2026-09-26 등록 전 수정 · 검토 실측: 세는 4/A 행 가운데 104 행이 자기가 고치는 제출의 행을 거래일만 바꿔 되풀이했다).
    4/A 행의 보고자가 여섯 칸 키로도 네 칸 키로도 새롭고(선언 q 의 정정이 아니고), 그 4/A 의 DATE_OF_ORIG_SUB 가 제출일인 제출의
    «살아 있는» 행(정정 행 아님 · 이 4/A 가 같은 값으로 다시 적어 확인한 행 아님 · 이 4/A 안에서 이미 거래일 정정으로 짝지은 행 아님 —
    같은 4/A 가 값을 고친 원 행은 된다: 한 4/A 가 한 원 로트의 값과 거래일을 함께 고친 실측 2건) 가운데
    (그룹, 코드, 수량, 단가 — 제출된 그대로 또는 앞 4/A 가 고친 값)가 같고 거래일이 다르며 보고자가 겹치는 첫 행(제출 순서)이 있으면 —
    4/A 행은 count = False ·
    corr = 3 · 겹친 보고자는 ocor(이력에 붙이지 않는다) · 나머지 보고자는 own(이력에만) · ctgt = [원 행 접수번호, SK].
    원 행은 가용일 · 사건 · 라벨(거래 연도 = 원래 거래일)이 그대로이고 tdh = [고친 거래일, 4/A 접수번호, SK] — 분류 이력만 고친
    거래일을 쓴다(원 가용일로 · 4/A 가용일 전의 분류일 D_Y 가 사이에 끼면 그 D_Y 는 고친 거래일을 먼저 쓴다 — dcorr_hist_early 로 센다).
    캐시 레코드가 corr 칸을 가져오면(패널) corr = 3 인 행만 거래일 정정이고 그 짝(ctgt)을 쓴다 — 패널에는 확인된 행이 없어
    다시 찾으면 달라질 수 있다(선언 k · q 와 같은 이치). corr 칸이 없는 레코드(DERA ZIP · 일간 XML)만 다시 찾는다.
    DATE_OF_ORIG_SUB 가 없는 4/A 는 거래일 정정이 될 수 없다(dcorr_no_orig 로 센다). 개정 전 규칙(q2 없음)은
    prepare(date_corrections=False) + corr = 3 행을 cnt = 1(지운 보고자 없으면) · 보고자 own + ocor 로 되돌린 패널로 재현한다(xcheck).
  r 분류 이력(History)에 들어가는 것 — 정확히. 단위 (보고자 CIK, 발행사 그룹) · 항목 (거래일, 가용일).
    prepare 를 통과한 Form 4 · 4/A 의 P · S 행(코드 · A/D · 날짜 · 보고자 거르기 뒤) 가운데
      · 강제 매도 행(stc — 새 식)은 뺀다(T6 만 넣는다). Form 5 는 처음부터 없다.
      · count = True 행: 행의 모든 보고자(관계를 거르지 않는다 — 선언 d · 'Other' 만인 보고자 · 관계 칸이 빈 보고자도 붙는다).
      · count = False 부분 중복 행(보고자 10인 상한으로 쪼갠 공동 제출 · 보고자를 더한 정정본): 새 보고자(own)만. 지운 보고자(odup)는
        같은 여섯 칸 키의 앞선 제출이 더 이른 가용일로 이미 싣는다.
      · 정정 행(corr = 2): 정정 보고자(ocor)는 넣지 않는다 · 새 보고자(own)만.
      · 정정된 원 행(corr = 1): 그대로 들어간다(거래일 · 가용일 · 보고자가 안 바뀐다 — 이력은 수량·단가를 보지 않는다).
      · 거래일 정정 행(corr = 3 · 선언 q2): 겹친 보고자(ocor)는 넣지 않는다 · 새 보고자(own)만(그 4/A 의 거래일 · 가용일).
      · 거래일이 고쳐진 원 행(tdh): 거래일 자리에 고친 거래일(tdh[0]) · 가용일은 원 행 그대로 · 보고자 그대로.
      · 여섯 칸 키가 같은 중복 행: 지워져 없다(첫 공시만).
    분류일 D_Y 에는 가용일 ≤ D_Y 이고 거래 연도가 Y−3..Y−1 인 항목만 센다. 표지 행의 라벨은 내부자 관계(Officer · Director ·
    TenPercentOwner) 보고자에게서만 나오므로 관계가 'Other' 뿐인 보고자의 분류는 세기만 하고 표지에 쓰이지 않는다. routine.json ·
    xcheck 의 연도별 R/O/U 수는 그들을 포함한다 — 검토 재계산(2014 R 729 · O 1,625)은 이력을 내부자 관계 보고자에게만 붙인 판이고
    이 파일(사양대로 모든 보고자 · R 735 · O 1,651)과의 차이는 모두 그 거르기에서 온다(ins_pit_build xcheck → xcheck_r1.json reconcile).

쌍둥이(모두 측정 — 시도 수와 DSR N 에 센다. 사양 controls 그대로).
  T1 원 계획 실용판  Officer 보고자만 · 행 금액 ≥ $100,000 · 10b5-1 표지 행 제외 · 3개월 룩백(t−2..t) 위에 엔진이 JT k=0..2 를 얹는다.
                     금액 = 제출된 그대로(선언 q 2026-09-26).
  T1C 선언된 민감도  T1 과 같고 4/A 가 고친 원 행(corr = 1)만 금액을 고친 값(usdc)으로 잰다(원 가용월 · 4/A 가용일 전에는 알려지지
                     않은 값이다 — 민감도일 뿐 1차를 대신하지 않는다 · cikmonth t1c_os_n · t1c_os3).
  T2 10b5-1 제외판   행 단위 각주 + REMARKS · 2023-04 부터 체크박스 OR · 2023-04 전후 분할 보고(split_t2).
  T3 CMP 표본 한정판 표지는 1차와 같고, 표본 가면(mask) = 그달 분류된(O·R) 내부자 P·S 행이 ≥ 1 인 그룹-월.
  T4 넓은판          분류 불가(U) 보고자의 매도를 기회주의로 센다(보고자 라벨 U → O 뒤 JOINT_RULE · 선언 m · 칸 t4_os_n · t4_rs_n).
  T5 합동 회귀판     표지는 1차와 같다 — 월 고정효과 · 회사 군집 표준오차는 엔진(§E)의 일이다(여기선 별칭).
  T6 순수 CMP판      강제 매도를 빼지 않는다(표지와 분류 이력 둘 다).
  ALL(대조)          분류 없는 전체 매도 더미(1차 행 규칙 · 라벨 무시) — «분류가 일하는지» 대조.

어댑터 — 원천 필드 이름은 이 파일의 네 곳에만 있다(자료 빌드가 이름을 정하면 여기만 고친다).
  DERA_COLS    DERA Insider Transactions TSV 열 이름(SUBMISSION · REPORTINGOWNER · NONDERIV_TRANS · FOOTNOTES).
  CACHE_FIELDS P/S 행 레코드(사전) 이름 — ins_pit_build.load_panel 이 내는 이름과 같다(보고자 목록형과 보고자별 펼친형 둘 다 받는다 ·
               cnt 칸을 지킨다 · 선언 k).
  PANEL_FIELDS §A 패널 data/_ins_pit/ps/ps_YYYY.json.gz 의 열 이름(ins_pit_build.PANEL_COLS) → CACHE_FIELDS(load_panel_records).
               정정(선언 q · q2)을 prepare 가 다시 만들 수 있게 with_odup 형은 보고자 own + odup + ocor · 수량·단가는 제출된 그대로(sh · px) · orig 를 낸다.
  IM_TM · IM_GC data/_issuer_map.json 의 tm · groups 행 순서(issuer_map.py 머리말의 tm_format · groups_format).
  ⚠ issuer_map.py 는 SEC_UA 가 없으면 import 에서 끝나므로 여기선 JSON 을 직접 읽는다(load_map 과 같은 뜻).

재사용: NYSE 휴장 규칙 = refresh_events._holidays + ADHOC(규칙은 한 곳에만) · 달 셈 = qbatch_core.mshift/months_between/SEED.

사용:
    python build/r_r1_flags.py --selftest                 # 합성 자료 단위 시험(수익 없음)
    python build/r_r1_flags.py --dera-check ZIP [ZIP …]   # DERA 분기 ZIP 파싱 개수만(어댑터 대조 · 수익 없음)
    python build/r_r1_flags.py --density DERA_DIR [--brief] # 전 분기 ZIP + 발행사 지도 → 밀도 · F0(수익 없음 · 아무 파일도 쓰지 않는다)
    python build/r_r1_flags.py --density-panel [--brief]    # 같은 것을 §A 패널(data/_ins_pit/ps)로
    python build/r_r1_flags.py --panel-check DERA_DIR       # ZIP 경로 대 패널 경로(odup 있음 · 없음) 표지가 칸마다 같은가(수익 없음)
    python build/r_r1_flags.py --calcheck                 # 휴장 규칙 대 stocks.json pxd_dates 격자
"""
from __future__ import annotations

import bisect
import collections
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as QC          # noqa: E402  mshift · months_between · SEED
import refresh_events as REV      # noqa: E402  NYSE 휴장 규칙(_holidays · ADHOC)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
IMAP = os.path.join(DATA, "_issuer_map.json")

csv.field_size_limit(10 ** 9)

# ════════════════════════════════════════════════════════════════════════
# 고정값(사양 R1 params — 여기 말고 다른 문턱·창은 시험하지 않는다)
# ════════════════════════════════════════════════════════════════════════
FORMS4 = ("4", "4/A")
CODES = {"P": "A", "S": "D"}                              # 코드 → 맞는 A/D
INSIDER = ("Officer", "Director", "TenPercentOwner")      # CMP 내부자 정의(부분 문자열)
OFFICER = ("Officer",)                                    # T1
JT_K = (0, 1, 2)                                          # 엔진이 쓰는 JT 시차(여기선 기록만)
STAGE_S_WINDOW = 3                                        # 가용월 r−2..r
STAGE_S_N = 30
T1_MIN_USD = 100000.0
T1_LOOKBACK = 3
AFF_FROM = "2023-04-01"                                   # 체크박스 의무(Form 4 개정 시행일)
SPLIT_T2 = "2023-04"                                      # T2 전후 분할(가용월)
DATA_START, DATA_END = "2011-01-01", "2026-06-30"         # DERA 2011Q1..2026Q2 제출일 범위(§A)
JOINT_RULE = "O>R>N>U"
STALE_REPORT_DAYS = 365                                   # 밀도 보고용(선언 l) — 규칙 문턱이 아니다

# 강제 매도 — 사양 R1 params 의 다섯 갈래(대소문자 무시 · 행에 연결된 각주에만). 🚨 저장소에 한 벌 — build/ins_pit_build.py 와
# build/ins_daily.py 는 이 이름들을 import 한다(같은 표지를 두 곳에서 만들면 갈린다).
# 'non-discretionary' 갈래는 원천징수·세금 맥락을 요구한다(선언 p · 2026-09-25 등록 전 수정 — 옛 맨 낱말 갈래로만 걸린 130행이
# 모두 10b5-1 계획 매도였다).
_STC_CORE = (r"sell[- ]to[- ]cover|(sell|sold|sale)[^.]{0,80}\bto cover\b|(sell|sold|sale)[^.]{0,80}(satisfy|cover)[^.]{0,40}tax"
             r"|mandated by the (issuer|company)")
STC_ND = r"non-discretionary[^.]{0,80}(withh|tax)"
STC_RX = re.compile(_STC_CORE + "|" + STC_ND, re.I)
# 감사 전용 — 수정 전 식(맨 'non-discretionary'). 규칙에는 쓰지 않는다 · 전후 개수(stc_v1 칸)를 재현하는 데만 쓴다.
STC_RX_V1 = re.compile(_STC_CORE + "|non-discretionary", re.I)
# 보고 전용(선언 p) — 'non-discretionary' 갈래를 뺀 식(새 갈래로만 걸린 행 stc_nd 를 가린다).
STC_CORE_RX = re.compile(_STC_CORE, re.I)
# 10b5-1 — 비평 실측과 같은 적중식 + 명시적 부정문(«not … pursuant to a Rule 10b5-1» · «non-10b5-1»)만 빼는 좁은 식
PLAN_RX = re.compile(r"10b5-?\s*1", re.I)
NEG_RX = re.compile(r"\bnot\s+(?:been\s+)?(?:made|effected|executed|sold|entered\s+into|conducted|transacted|done)?\s*"
                    r"(?:pursuant\s+to|under|in\s+accordance\s+with|subject\s+to)\s+(?:a\s+|an\s+|the\s+|any\s+)?(?:sec\s+)?(?:rule\s+)?10b5-?\s*1"
                    r"|\bnon-?\s*10b5-?\s*1", re.I)

# ════════════════════════════════════════════════════════════════════════
# 어댑터 — 원천 필드 이름(여기 네 곳만 고친다 — DERA_COLS · CACHE_FIELDS · PANEL_FIELDS · IM_TM·IM_GC)
# ════════════════════════════════════════════════════════════════════════
DERA_COLS = {
    # SUBMISSION
    "acc": "ACCESSION_NUMBER", "fdate": "FILING_DATE", "doc": "DOCUMENT_TYPE", "issuer": "ISSUERCIK",
    "sym": "ISSUERTRADINGSYMBOL", "remarks": "REMARKS", "aff": "AFF10B5ONE", "orig": "DATE_OF_ORIG_SUB",
    # REPORTINGOWNER
    "own_cik": "RPTOWNERCIK", "own_rel": "RPTOWNER_RELATIONSHIP",
    # NONDERIV_TRANS
    "sk": "NONDERIV_TRANS_SK", "tdate": "TRANS_DATE", "code": "TRANS_CODE", "shares": "TRANS_SHARES",
    "price": "TRANS_PRICEPERSHARE", "ad": "TRANS_ACQUIRED_DISP_CD", "fn_suffix": "_FN",
    # FOOTNOTES
    "fn_id": "FOOTNOTE_ID", "fn_txt": "FOOTNOTE_TXT",
    # 표 이름
    "T_SUB": "SUBMISSION.tsv", "T_OWN": "REPORTINGOWNER.tsv", "T_ND": "NONDERIV_TRANS.tsv", "T_FN": "FOOTNOTES.tsv",
}
CACHE_FIELDS = {
    # 한 행 = NONDERIV 행 하나(보고자 목록형) 또는 (행, 보고자) 하나(펼친형 — owners 가 없고 owner_cik 가 있으면 (acc, sk)로 다시 묶는다)
    "acc": "acc", "sk": "sk", "doc": "doc", "fdate": "fdate", "issuer": "issuer_cik", "gid": "gid",
    "tdate": "tdate", "code": "code", "ad": "ad", "shares": "shares", "price": "price",
    "fn": "fn_text",            # 행에 연결된 각주 본문(이어 붙인 것)
    "fn_ids": "fn_ids",         # 또는 각주 ID 목록(footnotes 사전을 따로 넘길 때)
    "remarks": "remarks", "aff": "aff",
    "owners": "owners",         # [[cik, 관계], …] 또는 [{"cik":…, "rel":…}, …]
    "owner_cik": "owner_cik", "owner_rel": "owner_rel",
    "stc": "stc", "p10_rx": "p10_rx",   # 텍스트가 없는 캐시가 미리 계산한 표지(텍스트가 있으면 여기서 다시 계산한다)
    "stc_v1": "stc_v1",         # (선택 · 감사) 수정 전 강제 매도 식(STC_RX_V1)의 판정 — 텍스트가 있으면 여기서 다시 계산한다
    "stc_nd": "stc_nd",         # (선택) 강제 매도가 'non-discretionary' 갈래로만 걸렸나(선언 p · 없으면 모름)
    "count": "cnt",             # 미리 정리된 캐시의 «표지에 센다» 1 · 0(선언 k — 0 은 prepare 가 지킨다 · 없으면 prepare 가 정한다)
    "corr": "corr",             # (선택) 캐시의 정정 표시(선언 q — 2 정정 행 · 1 정정된 원 행 · 0) · 2 인 행은 ctgt 짝을 prepare 가 쓴다
    "ctgt": "ctgt",             # (선택) 정정 행의 원 행 [접수번호, SK](corr 2 · 3 · null = 짝 없음)
    "orig": "orig",             # (선택) 4/A 의 DATE_OF_ORIG_SUB(고치는 제출의 제출일 · 선언 q2) — 없으면 거래일 정정이 될 수 없다
}
OWNER_KEYS = ("cik", "rel")
# §A 패널(build/ins_pit_build.py PANEL_COLS · 행 = 목록 · 열 이름은 파일의 "cols") → CACHE_FIELDS 키.
# own · odup · ocor = [[보고자 CIK, 관계 비트]] · sh · px = 제출된 그대로(등록 1차 · 선언 q 2026-09-26) · shc · pxc = 정정 값(감사 · T1C) ·
# orig = 4/A 의 DATE_OF_ORIG_SUB · tdh = 거래일이 고쳐진 원 행의 [고친 거래일, 4/A 접수번호, SK](선언 q2 — prepare 가 다시 만든다).
PANEL_DIR = os.path.join(DATA, "_ins_pit", "ps")
PANEL_FIELDS = {"gid": "g", "issuer": "cik", "acc": "acc", "sk": "sk", "doc": "doc", "fdate": "fd", "tdate": "td", "code": "c",
                "shares": "sh", "price": "px", "owners": "own", "odup": "odup", "ocor": "ocor", "orig": "orig",
                "corr": "corr", "ctgt": "ctgt", "stc": "stc", "stc_v1": "stc_v1", "p10_rx": "p10", "aff": "aff", "count": "cnt"}
PANEL_ROLE = (("Director", 1), ("Officer", 2), ("TenPercentOwner", 4), ("Other", 8))   # ins_pit_build.ROLE
IM_TM = ("a", "b", "gid", "primary", "ciks", "fpi", "src", "fpi_q")    # tm[티커] 행
IM_GC = ("cik", "from", "to", "basis", "name")                        # groups[g]["ciks"] 행

MON = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
       "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}


def iso(s) -> str:
    """DERA 'DD-MON-YYYY' · ISO · 'YYYYMMDD' → 'YYYY-MM-DD'(못 읽으면 '')."""
    s = (str(s) if s is not None else "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    if len(s) == 11 and s[2] == "-" and s[6] == "-":
        mm = MON.get(s[3:6].upper())
        return "%s-%s-%s" % (s[7:11], mm, s[0:2]) if mm else ""
    if len(s) == 8 and s.isdigit():
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    return ""


def _num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().replace(",", "")
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
    s = (str(s) if s is not None else "").strip().lower()
    if s in ("1", "true", "y", "yes"):
        return 1
    if s in ("0", "false", "n", "no"):
        return 0
    return None


def _fn_ids(v):
    return [x for x in re.split(r"[,\s]+", (v or "").strip()) if x]


def is_stc(fn_text: str) -> bool:
    return bool(fn_text) and STC_RX.search(fn_text) is not None


def is_stc_v1(fn_text: str) -> bool:
    """수정 전 강제 매도 식(감사 전용 · 선언 p) — 규칙에는 쓰지 않는다."""
    return bool(fn_text) and STC_RX_V1.search(fn_text) is not None


def stc_nd_only(fn_text: str) -> bool:
    """강제 매도가 새 'non-discretionary … withh/tax' 갈래로만 걸렸나(보고 전용 · 선언 p)."""
    return is_stc(fn_text) and STC_CORE_RX.search(fn_text) is None


def plan_hit(text: str) -> bool:
    """10b5-1 적중 — 적중 수가 명시적 부정문 수보다 많을 때만(부정문 하나는 적중 하나를 품는다)."""
    if not text:
        return False
    n = len(PLAN_RX.findall(text))
    return n > 0 and n > len(NEG_RX.findall(text))


def is_insider(rel: str, need=INSIDER) -> bool:
    rel = rel or ""
    return any(k in rel for k in need)


# ════════════════════════════════════════════════════════════════════════
# NYSE 거래일(규칙 = refresh_events · 관측 격자가 있으면 그 구간은 관측)
# ════════════════════════════════════════════════════════════════════════
class Cal:
    def __init__(self, observed=None, y0=2004, y1=2032):
        rule = []
        d, end = dt.date(y0, 1, 1), dt.date(y1, 12, 31)
        hol = {}
        while d <= end:
            if d.year not in hol:
                hol[d.year] = set(REV._holidays(d.year)) | {k for k in REV.ADHOC if k.startswith(str(d.year))}
            s = d.isoformat()
            if d.weekday() < 5 and s not in hol[d.year]:
                rule.append(s)
            d += dt.timedelta(days=1)
        if observed:
            obs = sorted(set(observed))
            lo, hi = obs[0], obs[-1]
            self.days = sorted([x for x in rule if x < lo or x > hi] + obs)
            self.src = ("observed", lo, hi)
        else:
            self.days = rule
            self.src = ("rule", rule[0], rule[-1])
        self._set = set(self.days)
        self._first, self._last = {}, {}

    def is_td(self, s):
        return s in self._set

    def next_td(self, s: str) -> str:
        """s 보다 **뒤의** 첫 거래일(s 가 거래일이어도 다음 날)."""
        i = bisect.bisect_right(self.days, s)
        return self.days[i]

    def first_td(self, y: int) -> str:
        if y not in self._first:
            self._first[y] = self.next_td("%04d-12-31" % (y - 1))
        return self._first[y]

    def last_td(self, ym: str) -> str:
        if ym not in self._last:
            i = bisect.bisect_right(self.days, ym + "-32") - 1
            self._last[ym] = self.days[i] if (i >= 0 and self.days[i].startswith(ym)) else None
        return self._last[ym]


def avail_months(cal: Cal, start=DATA_START, end=DATA_END, lo="2004-01", hi="2032-12"):
    """자료 창 [start, end](제출일)로 **다 찬** 가용월 집합.
    달 M 이 다 찼다 = M 에 가용되는 모든 제출일 f 가 창 안이다 · f 의 범위는 [M 전달 마지막 거래일, M 마지막 거래일 − 1일]."""
    out = set()
    for ym in QC.months_between(lo, hi):
        lt, lp = cal.last_td(ym), cal.last_td(QC.mshift(ym, -1))
        if not lt or not lp:
            continue
        fmax = (dt.date.fromisoformat(lt) - dt.timedelta(days=1)).isoformat()
        if start <= lp and fmax <= end:
            out.add(ym)
    return out


def hist_y0(start=DATA_START) -> int:
    """거래 연도 y 가 온전히 들어온 첫 해 — 제출일 창이 y-01-01 이전(또는 같은 날)에 시작해야 한다."""
    y = int(start[:4])
    return y if start <= "%04d-01-01" % y else y + 1


# ════════════════════════════════════════════════════════════════════════
# 정본 행
# ════════════════════════════════════════════════════════════════════════
class Row:
    __slots__ = ("acc", "sk", "doc", "fdate", "avail", "ym", "issuer", "gid", "tdate", "code", "ad",
                 "shares", "price", "usd", "owners", "fn", "remarks", "aff", "stc", "p10_rx", "p10_box", "p10", "count",
                 "stc_nd", "lag", "stc_v1", "corr", "shc", "pxc", "usdc", "ctgt", "cym", "ocor", "odup", "corr_in", "ctgt_in",
                 "orig", "tdh")

    def __init__(self, **k):
        for f in self.__slots__:
            setattr(self, f, k.get(f))

    def copy(self, **chg):
        r = Row(**{f: getattr(self, f) for f in self.__slots__})
        for k, v in chg.items():
            setattr(r, k, v)
        return r

    def ty(self) -> int:
        return int(self.tdate[:4])


def _usd(sh, px):
    return (sh * px) if (sh is not None and px is not None and px > 0) else None


def _mkrow(acc, sk, doc, fdate, issuer, gid, tdate, code, ad, shares, price, owners, fn, remarks, aff,
           stc=None, p10_rx=None, count=None, stc_nd=None, stc_v1=None, corr=None, ctgt=None, orig=None):
    """정본 행 하나. count = 미리 정리된 캐시의 cnt(None = 모름 · prepare 가 정한다 · 0 이면 prepare 가 지킨다 · 선언 k).
    stc_nd = 강제 매도가 'non-discretionary' 갈래로만 걸렸나(본문이 있으면 여기서 계산 · 없으면 캐시 값 · 그것도 없으면 None).
    stc_v1 = 수정 전 식의 판정(감사 · 선언 p — 본문이 있으면 여기서 · 없으면 캐시 값 · 그것도 없으면 None).
    corr · ctgt = 캐시(패널)의 정정 표시와 짝(선언 q · q2 — corr 2 · 3 인 정정 행의 원 행 [접수번호, SK] · prepare 가 그 짝을 쓴다).
    orig = 4/A 의 DATE_OF_ORIG_SUB(선언 q2 · 없으면 None)."""
    sh, px = _num(shares), _num(price)
    fdate, tdate = iso(fdate), iso(tdate)
    fn = fn or ""
    remarks = remarks or ""
    if fn or stc is None:
        stc_v = is_stc(fn)
        nd = stc_nd_only(fn)
        v1 = is_stc_v1(fn)
    else:
        stc_v = bool(stc)
        nd = False if not stc_v else (None if stc_nd is None else bool(stc_nd))
        v1 = None if stc_v1 is None else bool(stc_v1)
    return Row(acc=str(acc), sk=str(sk if sk is not None else ""), doc=str(doc or "").strip(), fdate=fdate,
               issuer=_cik(issuer), gid=gid, tdate=tdate, code=str(code or "").strip().upper(),
               ad=str(ad or "").strip().upper(), shares=sh, price=px, usd=_usd(sh, px),
               owners=tuple(owners), fn=fn, remarks=remarks, aff=_aff(aff),
               stc=stc_v, stc_nd=nd, stc_v1=v1,
               p10_rx=plan_hit(fn + " " + remarks) if (fn or remarks or p10_rx is None) else bool(p10_rx),
               count=None if count is None else bool(count),
               corr_in=None if corr is None else int(corr), ctgt_in=tuple(ctgt) if ctgt else None,
               orig=(iso(orig) or None) if orig else None)


def _gid_of(cik2gid, issuer):
    if cik2gid is None:
        return "c%d" % issuer if issuer is not None else None
    return cik2gid.get(issuer)


def _tables_from_zip(path, C=DERA_COLS):
    z = zipfile.ZipFile(path)
    names = {n.split("/")[-1]: n for n in z.namelist()}

    def rd(t):
        with z.open(names[t]) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t",
                                      quoting=csv.QUOTE_NONE)
    return {t: (lambda t=t: rd(t)) for t in (C["T_SUB"], C["T_OWN"], C["T_ND"], C["T_FN"])}


def rows_from_dera(src, cik2gid=None, C=DERA_COLS, keep_text=True):
    """DERA 분기 표 → 정본 P/S 행. src = ZIP 경로 또는 {표 이름: 행 목록 | 행을 내는 함수}.
    cik2gid 가 있으면 그 발행사(세계 그룹)만 남긴다. keep_text=False 면 표지(stc · p10_rx)를 계산한 뒤 본문을 버린다(메모리).
    반환 (행, 개수)."""
    T = _tables_from_zip(src, C) if isinstance(src, str) else src

    def it(t):
        v = T[t]
        return v() if callable(v) else iter(v)
    st = collections.Counter()
    sub = {}
    for r in it(C["T_SUB"]):
        doc = (r.get(C["doc"]) or "").strip()
        if doc not in FORMS4:
            continue
        ck = _cik(r.get(C["issuer"]))
        g = _gid_of(cik2gid, ck)
        if g is None:
            st["sub_outside_world"] += 1
            continue
        sub[r[C["acc"]]] = (doc, r.get(C["fdate"]), ck, g, r.get(C["remarks"]), r.get(C["aff"]), r.get(C["orig"]))
    nd, need = [], set()
    for r in it(C["T_ND"]):
        a = r.get(C["acc"])
        if a not in sub:
            continue
        code = (r.get(C["code"]) or "").strip().upper()
        if code not in CODES:
            continue
        ids = []
        for k, v in r.items():
            if k and k.endswith(C["fn_suffix"]) and v:
                ids.extend(_fn_ids(v))
        need.update((a, x) for x in ids)
        nd.append((a, r, ids))
    fn = {}
    for r in it(C["T_FN"]):
        k = (r.get(C["acc"]), (r.get(C["fn_id"]) or "").strip())
        if k in need:
            fn[k] = r.get(C["fn_txt"]) or ""
    own = collections.defaultdict(list)
    accs = {a for a, _, _ in nd}
    for r in it(C["T_OWN"]):
        a = r.get(C["acc"])
        if a in accs:
            c = _cik(r.get(C["own_cik"]))
            if c is not None:
                own[a].append((c, (r.get(C["own_rel"]) or "").strip()))
    out = []
    for a, r, ids in nd:
        doc, fd, ck, g, rem, aff, orig = sub[a]
        seen, txt = set(), []
        for x in ids:
            if x not in seen:
                seen.add(x)
                txt.append(fn.get((a, x), ""))
        row = _mkrow(a, r.get(C["sk"]), doc, fd, ck, g, r.get(C["tdate"]), r.get(C["code"]), r.get(C["ad"]),
                     r.get(C["shares"]), r.get(C["price"]), own.get(a, ()), " ".join(t for t in txt if t), rem, aff, orig=orig)
        if not keep_text:
            row.fn = row.remarks = ""
        out.append(row)
    st["rows_ps"] = len(out)
    return out, dict(st)


def rows_from_records(recs, F=CACHE_FIELDS, cik2gid=None, footnotes=None):
    """§A 행 캐시(이름 미정) → 정본 행. 보고자 목록형 · 펼친형 둘 다. footnotes = {(acc, 각주 ID): 본문}(fn_ids 형일 때)."""
    recs = list(recs)
    g = lambda r, k: r.get(F[k]) if F.get(k) else None
    if recs and g(recs[0], "owners") is None and g(recs[0], "owner_cik") is not None:
        by = collections.OrderedDict()
        for r in recs:
            k = (str(g(r, "acc")), str(g(r, "sk")))
            if k not in by:
                by[k] = (r, [])
            c = _cik(g(r, "owner_cik"))
            if c is not None and all(c != x for x, _ in by[k][1]):
                by[k][1].append((c, g(r, "owner_rel") or ""))
        items = list(by.values())
    else:
        items = []
        for r in recs:
            ow = []
            for o in g(r, "owners") or []:
                if isinstance(o, dict):
                    ow.append((_cik(o.get(OWNER_KEYS[0])), o.get(OWNER_KEYS[1]) or ""))
                else:
                    ow.append((_cik(o[0]), o[1] if len(o) > 1 else ""))
            items.append((r, [x for x in ow if x[0] is not None]))
    out = []
    for r, ow in items:
        ck = _cik(g(r, "issuer"))
        gid = g(r, "gid") or _gid_of(cik2gid, ck)
        if gid is None:
            continue
        fn = g(r, "fn")
        if fn is None and footnotes is not None:
            ids = g(r, "fn_ids") or []
            ids = _fn_ids(ids) if isinstance(ids, str) else list(ids)
            fn = " ".join(footnotes.get((str(g(r, "acc")), x), "") for x in dict.fromkeys(ids))
        out.append(_mkrow(g(r, "acc"), g(r, "sk"), g(r, "doc"), g(r, "fdate"), ck, gid, g(r, "tdate"), g(r, "code"),
                          g(r, "ad"), g(r, "shares"), g(r, "price"), ow, fn, g(r, "remarks"), g(r, "aff"),
                          stc=g(r, "stc"), p10_rx=g(r, "p10_rx"), count=g(r, "count"), stc_nd=g(r, "stc_nd"),
                          stc_v1=g(r, "stc_v1"), corr=g(r, "corr"), ctgt=g(r, "ctgt"), orig=g(r, "orig")))
    return out


def to_records(rows, F=CACHE_FIELDS, keep_text=True):
    """정본 행(prepare 결과) → CACHE_FIELDS 이름의 보고자 목록형 레코드(§A 패널을 흉내 — cnt 칸 포함 · 지운 보고자는 싣지 않는다).
    rows_from_records 로 다시 읽어 build 하면 같은 표지가 나와야 한다(selftest cache_roundtrip_ok)."""
    out = []
    for r in rows:
        rec = {F["acc"]: r.acc, F["sk"]: r.sk, F["doc"]: r.doc, F["fdate"]: r.fdate, F["issuer"]: r.issuer, F["gid"]: r.gid,
               F["tdate"]: r.tdate, F["code"]: r.code, F["ad"]: r.ad, F["shares"]: r.shares, F["price"]: r.price,
               F["owners"]: [[c, rel] for c, rel in r.owners], F["aff"]: r.aff, F["stc"]: r.stc, F["p10_rx"]: r.p10_rx,
               F["stc_nd"]: r.stc_nd, F["stc_v1"]: r.stc_v1,
               F["remarks"]: r.remarks if keep_text else "", F["fn"]: r.fn if keep_text else None, F["orig"]: r.orig}
        if r.count is not None:
            rec[F["count"]] = 1 if r.count else 0
        if r.corr is not None:
            rec[F["corr"]] = r.corr
            if r.corr in (2, 3):
                rec[F["ctgt"]] = list(r.ctgt) if r.ctgt else None
        out.append(rec)
    return out


def load_panel_records(path=PANEL_DIR, years=None, with_odup=True, P=PANEL_FIELDS, F=CACHE_FIELDS):
    """§A 패널(data/_ins_pit/ps/ps_YYYY.json.gz · 열 이름은 파일의 "cols") → CACHE_FIELDS 이름 레코드(rows_from_records 에 넘긴다).
    with_odup = 패널이 cnt = 0 행에서 지운 보고자(odup)와 정정 보고자(ocor)를 되붙인다 — prepare 가 정리 · 정정을 처음부터 다시
    만든다(ins_pit_build.load_panel 과 같은 형). 끄면 보고자는 own 만이고 cnt 칸만으로 «세지 않음» 을 지킨다(선언 k) — 둘 다 같은
    표지를 내야 한다(--panel-check). 수량 · 단가는 두 형 모두 제출된 그대로(sh · px — 등록 1차 · 선언 q 2026-09-26)다.
    관계 비트는 PANEL_ROLE 로 DERA 식 문자열로 되돌린다."""
    import gzip
    rel_of = lambda b: ",".join(k for k, v in PANEL_ROLE if int(b) & v)
    out = []
    for f in sorted(os.listdir(path)):
        if not (f.startswith("ps_") and f.endswith(".json.gz")):
            continue
        if years and f[3:7] not in {str(y) for y in years}:
            continue
        with gzip.open(os.path.join(path, f), "rt", encoding="utf-8") as fh:
            d = json.load(fh)
        j = {k: i for i, k in enumerate(d["cols"])}
        opt = lambda r, k: r[j[P[k]]] if P.get(k) in j else None
        for r in d["rows"]:
            code = r[j[P["code"]]]
            own = list(r[j[P["owners"]]] or [])
            sh, px = r[j[P["shares"]]], r[j[P["price"]]]
            if with_odup:
                own += list(opt(r, "odup") or []) + list(opt(r, "ocor") or [])
            rec = {F["acc"]: r[j[P["acc"]]], F["sk"]: r[j[P["sk"]]], F["doc"]: r[j[P["doc"]]], F["fdate"]: r[j[P["fdate"]]],
                   F["issuer"]: r[j[P["issuer"]]], F["gid"]: r[j[P["gid"]]], F["tdate"]: r[j[P["tdate"]]], F["code"]: code,
                   F["ad"]: CODES.get(code), F["shares"]: sh, F["price"]: px,
                   F["owners"]: [[c, rel_of(b)] for c, b in own], F["stc"]: r[j[P["stc"]]], F["stc_v1"]: opt(r, "stc_v1"),
                   F["p10_rx"]: r[j[P["p10_rx"]]], F["aff"]: r[j[P["aff"]]], F["count"]: r[j[P["count"]]],
                   F["corr"]: opt(r, "corr"), F["ctgt"]: opt(r, "ctgt") if opt(r, "corr") in (2, 3) else None,
                   F["orig"]: opt(r, "orig"), F["remarks"]: "", F["fn"]: None}
            out.append(rec)
    return out


# ════════════════════════════════════════════════════════════════════════
# 발행사 지도(§A0) — data/_issuer_map.json 을 직접 읽는다
# ════════════════════════════════════════════════════════════════════════
class IssuerMap:
    def __init__(self, path=IMAP, doc=None):
        d = doc if doc is not None else json.load(io.open(path, encoding="utf-8"))
        self.doc = d
        self.idx = {}
        ix = {k: j for j, k in enumerate(IM_TM)}
        # 등록 FPI 표지 — 지도의 fpi_registered 가 가리키는 칸(2026-09-25 권고: fpi_q · 직전 정기보고가 10-Q 면 FPI 아님).
        # 지도에 그 칸 지시가 없으면(옛 판 · 합성 문서) 사양 칸 fpi. 두 칸은 fpi_spec · fpi_q 로 따로 싣는다.
        self.fpi_field = ((d.get("fpi_registered") or {}).get("field") or "fpi")
        if self.fpi_field not in ix:
            raise SystemExit("🚨 fpi_registered.field=%s 가 tm 칸(%s)에 없다" % (self.fpi_field, IM_TM))
        for t, runs in d["tm"].items():
            for run in runs:
                a, b = run[ix["a"]], run[ix["b"]]
                fq = run[ix["fpi_q"]] if len(run) > ix["fpi_q"] else run[ix["fpi"]]
                rec = {"gid": run[ix["gid"]], "primary": run[ix["primary"]], "ciks": run[ix["ciks"]],
                       "fpi": run[ix[self.fpi_field]] if len(run) > ix[self.fpi_field] else run[ix["fpi"]],
                       "fpi_spec": run[ix["fpi"]], "fpi_q": fq, "src": run[ix["src"]]}
                for ym in QC.months_between(a, b):
                    self.idx[(t, ym)] = rec
        self.cik2gid, self.conflicts = {}, []
        jc = {k: j for j, k in enumerate(IM_GC)}
        for gid, g in d["groups"].items():
            for row in g["ciks"]:
                c = int(row[jc["cik"]])
                if c in self.cik2gid and self.cik2gid[c] != gid:
                    self.conflicts.append((c, self.cik2gid[c], gid))
                    continue
                self.cik2gid[c] = gid
        f0 = (d.get("f0") or {}).get("by_month") or {}
        self.f0_bad = {m for m, v in f0.items() if v and v[0] and v[1] / v[0] > 0.02}
        self.months = sorted({ym for _, ym in self.idx})

    def at(self, t, ym):
        for k in (t, t.replace("-", "."), t.replace(".", "-")):
            r = self.idx.get((k, ym))
            if r is not None:
                return r
        return None

    def members(self, ym, tickers=None):
        """그달 멤버(티커 목록을 주면 그 안에서) → {"s16": {티커: 그룹}, "fpi": [...], "fpi_null": [...], "unresolved": [...]}.
        s16 = 그룹이 풀렸고 fpi != 1(null 포함 · 선언 i)."""
        ts = tickers if tickers is not None else sorted({t for (t, m) in self.idx if m == ym})
        out = {"s16": {}, "fpi": [], "fpi_null": [], "unresolved": []}
        for t in ts:
            r = self.at(t, ym)
            if r is None or not r["gid"]:
                out["unresolved"].append(t)
            elif r["fpi"] == 1:
                out["fpi"].append(t)
            else:
                out["s16"][t] = r["gid"]
                if r["fpi"] is None:
                    out["fpi_null"].append(t)
        return out


# ════════════════════════════════════════════════════════════════════════
# 정리 — 기간 · 코드 · 날짜 · 정정 중복
# ════════════════════════════════════════════════════════════════════════
def _k6(x):
    return None if x is None else round(float(x), 6)


def sk_num(sk) -> int:
    """정렬용 SK 수치(없거나 수가 아니면 −1) — ins_pit_build.clean 과 같은 순서(문자열 SK '10' < '9' 를 피한다)."""
    try:
        return int(sk)
    except (TypeError, ValueError):
        return -1


def dedupe_order(fdate, doc, acc, sk):
    """정정 중복 판정 순서 — (제출일, 원본 먼저, 접수번호, SK 수치). ins_pit_build.clean 과 한 식."""
    return (fdate, doc != "4", acc, sk_num(sk))


def _eff(X):
    """짝 짓기에 쓰는 «지금 값» — 고친 값(corr = 1 의 shc · pxc)이 있으면 그것 · 아니면 제출된 그대로(선언 q)."""
    return (X.shc, X.pxc) if X.corr == 1 else (X.shares, X.price)


def prepare(rows, cal: Cal, corrections=True, date_corrections=True):
    """정본 행 → (남은 행(제출일 순) · 개수). 표지·분류 모두 이 결과만 쓴다. 입력 행은 바꾸지 않는다(복사본을 돌려준다).
    count=False 인 행 = 앞선 다른 제출이 이미 알린 거래에 보고자만 더한 것(10인 상한으로 쪼갠 공동 제출 · 보고자를 더한 정정본)
    — 표지에서는 세지 않고(거래당 한 번) 새 보고자의 분류 이력에만 붙인다(선언 c).
    4/A 정정(선언 q): 정정 행은 count=False · corr=2(owners = 새 보고자만 · ocor = 정정 보고자 · odup = 지운 보고자) ·
    짝지은 원 행은 수량 · 단가 · 금액을 **바꾸지 않고**(제출된 그대로 — 등록 1차) 고친 값을 shc · pxc · usdc 에 싣는다 · corr=1 ·
    ctgt = (정정 접수번호, SK) · 정정 행의 ctgt = (원 행 접수번호, SK) · cym = 원 행 사건월.
    거래일 정정(선언 q2 · date_corrections): 정정 행은 count=False · corr=3 · ocor = 겹친 보고자 · 원 행 tdh = (고친 거래일, 접수번호, SK).
    입력 행이 캐시의 짝(corr_in = 2 · 3 · ctgt_in)을 가져오면 그 짝을 쓴다 — 패널에는 4/A 가 같은 값으로 다시 적어 «확인» 한 원 행
    (지워진 중복 행)이 남지 않아 짝을 다시 찾으면 달라질 수 있다(선언 k 와 같은 이치). 입력 행에 corr 칸이 있으면(패널) corr_in = 3 인
    행만 거래일 정정이다.
    입력 행의 count 가 False(미리 정리된 캐시의 cnt = 0)면 그대로 지킨다 — 이쪽 판정과 AND(선언 k).
    lag = 가용일 − 거래일(달력일 · 보고용 · 선언 l).
    corrections=False = 옛 규칙(여섯 칸 키만 · 4/A 도 새 사건) — 감사 재현 전용(선언 q · xcheck old_rule_reproduction).
    date_corrections=False = 선언 q2 앞의 규칙(거래일만 다른 4/A 도 새 사건) — 감사 재현 전용(xcheck round2_rule_reproduction)."""
    st = collections.Counter()
    keep = []
    for r0 in rows:
        r = r0.copy(count=(r0.count is not False), corr=0, shc=None, pxc=None, usdc=None, tdh=None, ctgt=None, cym=None,
                    ocor=(), odup=())
        if r0.count is False:
            st["cnt0_in"] += 1
        if r.doc not in FORMS4:
            st["drop_not_form4"] += 1
            continue
        if r.code not in CODES:
            st["drop_code"] += 1
            continue
        if r.ad != CODES[r.code]:
            st["drop_ad_mismatch"] += 1
            continue
        if not r.tdate or not r.fdate:
            st["drop_no_date"] += 1
            continue
        if r.tdate > r.fdate:
            st["drop_tdate_after_fdate"] += 1
            continue
        if not r.owners:
            st["drop_no_owner"] += 1
            continue
        r.avail = cal.next_td(r.fdate)
        r.ym = r.avail[:7]
        r.lag = (dt.date.fromisoformat(r.avail) - dt.date.fromisoformat(r.tdate)).days
        r.p10_box = 1 if (r.fdate >= AFF_FROM and r.aff == 1) else 0
        r.p10 = bool(r.p10_rx or r.p10_box)
        keep.append(r)
    keep.sort(key=lambda r: dedupe_order(r.fdate, r.doc, r.acc, r.sk))
    first = {}                                   # 여섯 칸 키 → 그 키를 처음 낸 접수번호
    seen4 = set()                                # (그룹, 보고자, 거래일, 코드) — 앞선 제출에서 나온 것(남은 행의 모든 보고자)
    live = collections.defaultdict(list)         # (그룹, 거래일, 코드) → 앞선 제출의 «살아 있는» 행 번호(정정 행 제외)
    live_fd = collections.defaultdict(list)      # (그룹, 제출일, 코드) → 같은 뜻(선언 q2 — 4/A 가 고치는 제출의 행)
    pos = {}                                     # (접수번호, SK) → 행 번호(캐시 짝 찾기)
    allown = []                                  # 행 번호 → 그 행의 원 보고자 CIK 집합
    out = []
    i = 0
    while i < len(keep):
        j = i
        while j < len(keep) and keep[j].acc == keep[i].acc:
            j += 1
        block, i = keep[i:j], j
        amend = corrections and block[0].doc == "4/A"
        stat = []
        for r in block:
            new, old, cor = [], [], []
            for c, rel in r.owners:
                k6 = (r.gid, c, r.tdate, r.code, _k6(r.shares), _k6(r.price))
                a0 = first.get(k6)
                if a0 is not None and a0 != r.acc:
                    old.append((c, rel))              # 앞선 다른 제출과 여섯 칸이 같다(같은 제출 안 두 로트는 지우지 않는다)
                elif amend and (r.gid, c, r.tdate, r.code) in seen4:
                    cor.append((c, rel))              # 선언 q — 앞선 제출이 알린 거래를 값만 고쳤다
                else:
                    new.append((c, rel))
            stat.append([r, new, old, cor, []])       # 마지막 칸 = 거래일 정정 보고자(선언 q2)
        if amend:
            # 이 4/A 가 같은 값으로 다시 적은 원 행(확인) — 정정 짝에서 뺀다(«지금 값»으로 비교)
            conf = set()
            for r, new, old, cor, _ in stat:
                if old and not cor:
                    oc = {c for c, _ in old}
                    for x in live.get((r.gid, r.tdate, r.code), ()):
                        es, ep = _eff(out[x])
                        if x not in conf and _k6(es) == _k6(r.shares) and _k6(ep) == _k6(r.price) and oc & allown[x]:
                            conf.add(x)
                            break
            used = set()
            for r, new, old, cor, _ in stat:
                if not cor:
                    continue
                cc = {c for c, _ in cor}
                tgt = None
                if r.corr_in == 2:                        # 캐시(패널)가 정한 짝 — 다시 찾지 않는다
                    st["corr_from_cache"] += 1
                    if r.ctgt_in:
                        ka = (str(r.ctgt_in[0]), str(r.ctgt_in[1]))
                        tgt = next((x for x in live.get((r.gid, r.tdate, r.code), ()) if (out[x].acc, out[x].sk) == ka), None)
                        if tgt is None:
                            st["corr_cache_target_missing"] += 1
                else:
                    for x in live.get((r.gid, r.tdate, r.code), ()):
                        if x not in conf and x not in used and cc & allown[x]:
                            tgt = x
                            break
                r.corr, r.count = 2, False
                if tgt is None:
                    st["corr_unpaired"] += 1
                    continue
                used.add(tgt)
                X = out[tgt]
                X.shc, X.pxc, X.usdc = r.shares, r.price, _usd(r.shares, r.price)   # 🔒 원 행 값은 그대로(제출된 그대로 · 선언 q)
                X.corr, X.ctgt = 1, (r.acc, r.sk)
                r.ctgt, r.cym = (X.acc, X.sk), X.ym
                st["corr_paired"] += 1
                st["corr_paired_cross_month"] += 1 if X.ym != r.ym else 0
            # 선언 q2 — 거래일 정정: 고치는 제출(DATE_OF_ORIG_SUB)의 살아 있는 행과 (그룹, 코드, 수량 · 단가)가 같고 거래일만 다르다.
            #   짝은 거래일 정정끼리만 하나씩(used_d) — 같은 4/A 가 한 원 행의 값(정정 행)과 거래일(이 행)을 함께 고칠 수 있다
            used_d = set()
            for item in (stat if date_corrections else ()):
                r, new, old, cor, dcor = item
                if cor or not new:
                    continue
                if r.corr_in is not None and r.corr_in != 3:
                    continue                              # 캐시(패널)가 거래일 정정이 아니라고 정했다
                tgt, cached = None, r.corr_in == 3
                if cached:
                    st["dcorr_from_cache"] += 1
                    if r.ctgt_in:
                        tgt = pos.get((str(r.ctgt_in[0]), str(r.ctgt_in[1])))
                        if tgt is not None and out[tgt].corr in (2, 3):
                            tgt = None
                    if tgt is None:
                        st["dcorr_cache_target_missing"] += 1
                else:
                    if not r.orig:
                        st["dcorr_no_orig"] += 1
                        continue
                    nc = {c for c, _ in new}
                    for x in live_fd.get((r.gid, r.orig, r.code), ()):
                        X = out[x]
                        if x in conf or x in used_d or X.tdate == r.tdate or not (nc & allown[x]):
                            continue
                        es, ep = _eff(X)                  # 제출된 그대로 또는 고친 값(앞 4/A 가 값을 고친 원 행) — 둘 중 하나와 같으면
                        if ((_k6(X.shares) == _k6(r.shares) and _k6(X.price) == _k6(r.price))
                                or (_k6(es) == _k6(r.shares) and _k6(ep) == _k6(r.price))):
                            tgt = x
                            break
                    if tgt is None:
                        continue                          # 거래일 정정이 아니다 — 새 행(자기 공시일 사건)
                r.corr, r.count = 3, False
                if tgt is None:
                    continue
                used_d.add(tgt)
                X = out[tgt]
                xo = allown[tgt]
                item[4] = [(c, rel) for c, rel in new if c in xo]
                item[1] = [(c, rel) for c, rel in new if c not in xo]
                X.tdh = (r.tdate, r.acc, r.sk)
                r.ctgt, r.cym = (X.acc, X.sk), X.ym
                st["dcorr_paired"] += 1
                st["dcorr_paired_cross_month"] += 1 if X.ym != r.ym else 0
                st["dcorr_hist_year_change"] += 1 if X.tdate[:4] != r.tdate[:4] else 0
                y0, y1 = int(X.avail[:4]), int(r.avail[:4])
                st["dcorr_hist_early"] += 1 if any(X.avail <= cal.first_td(y) < r.avail for y in range(y0 + 1, y1 + 1)) else 0
        for r, new, old, cor, dcor in stat:
            if not new and not cor and not dcor and r.corr != 3:
                st["drop_dup_" + ("amend" if r.doc == "4/A" else "orig")] += 1
                continue
            own0 = {c for c, _ in r.owners}
            if cor:
                st["corr_rows"] += 1
                r.ocor, r.odup, r.owners = tuple(cor), tuple(old), tuple(new)
                st["corr_rows_with_new_owner"] += 1 if new else 0
            elif r.corr == 3:
                st["dcorr_rows"] += 1
                st["dcorr_rows_" + r.code] += 1
                r.ocor, r.odup, r.owners = tuple(dcor), tuple(old), tuple(new)
                st["dcorr_rows_with_new_owner"] += 1 if new else 0
            elif old:
                st["dup_partial_owner"] += 1
                r.owners, r.odup = tuple(new), tuple(old)
                r.count = False
            elif not r.count:
                st["cnt0_kept_from_cache"] += 1       # 캐시가 «이미 센 거래» 라 했고 이쪽은 그 앞 공시를 못 봤다(지운 보고자 없는 레코드 · 해 일부)
            if not r.count:
                st["count_false"] += 1
            if r.doc == "4/A":
                if not cor and r.corr != 3:
                    st["amend_new_rows_v1"] += 1      # 옛 정의(정정 행이 아닌 남은 4/A 행 — 세지 않는 부분 중복 포함 · 보고용)
                if r.count:
                    st["amend_new_rows"] += 1         # 🔒 사건인 4/A 행(count = True) — 2026-09-26 정의 수정(검토 지적)
            for c, _ in new + cor + dcor:
                first.setdefault((r.gid, c, r.tdate, r.code, _k6(r.shares), _k6(r.price)), r.acc)
            for c in own0:
                seen4.add((r.gid, c, r.tdate, r.code))
            allown.append(own0)
            pos[(r.acc, r.sk)] = len(out)
            if r.corr not in (2, 3):
                live[(r.gid, r.tdate, r.code)].append(len(out))
                live_fd[(r.gid, r.fdate, r.code)].append(len(out))
            out.append(r)
    st["corr_targets"] = sum(1 for r in out if r.corr == 1)
    st["dcorr_targets"] = sum(1 for r in out if r.tdh)
    st["amend_no_orig"] = sum(1 for r in out if r.doc == "4/A" and not r.orig)
    st["kept"] = len(out)
    return out, dict(st)


# ════════════════════════════════════════════════════════════════════════
# 분류(routine.json) — (보고자 CIK, 그룹, 연도) → R · O · U · N
# ════════════════════════════════════════════════════════════════════════
class History:
    def __init__(self, rows, cal: Cal, stc_excl=True, start=DATA_START):
        self.cal, self.stc_excl = cal, stc_excl
        self.y0 = hist_y0(start) + 3                       # 첫 분류 가능 해
        h = collections.defaultdict(list)
        for r in rows:
            if stc_excl and r.stc:
                continue
            td = r.tdh[0] if r.tdh else r.tdate           # 선언 q2 — 거래일이 고쳐진 원 행은 고친 거래일(가용일은 원 행 그대로)
            for c, _ in r.owners:                          # 선언 d — 모든 보고자에게 붙인다
                h[(c, r.gid)].append((td, r.avail))
        for v in h.values():
            v.sort()
        self.h = dict(h)
        self._c = {}

    def cls(self, c, gid, Y):
        k = (c, gid, Y)
        v = self._c.get(k)
        if v is None:
            v = self._c[k] = self._classify(c, gid, Y)
        return v

    def _classify(self, c, gid, Y):
        if Y < self.y0:
            return "N"
        D = self.cal.first_td(Y)
        by = {Y - 3: set(), Y - 2: set(), Y - 1: set()}
        lo, hi = "%04d-01-01" % (Y - 3), "%04d-12-31" % (Y - 1)
        rows = self.h.get((c, gid), ())
        i = bisect.bisect_left(rows, (lo,))
        while i < len(rows) and rows[i][0] <= hi:
            td, av = rows[i]
            if av <= D:
                by[int(td[:4])].add(td[5:7])
            i += 1
        if any(not s for s in by.values()):
            return "U"
        return "R" if (by[Y - 3] & by[Y - 2] & by[Y - 1]) else "O"

    def late(self, Y):
        """분류일 D_Y 뒤에 도착해 이력에서 빠진 행(보고자 붙임 단위 · 거래 연도 Y−3..Y−1)."""
        D = self.cal.first_td(Y)
        lo, hi = "%04d-01-01" % (Y - 3), "%04d-12-31" % (Y - 1)
        return sum(1 for v in self.h.values() for td, av in v if lo <= td <= hi and av > D)

    def table(self, years):
        """routine.json 본문 — 키 'CIK|그룹' → 해마다 한 글자(R · O · U · N · '-' = 창 안 이력 없음)."""
        out = {}
        for (c, gid), v in sorted(self.h.items(), key=lambda kv: (str(kv[0][1]), kv[0][0])):
            ys = {int(td[:4]) for td, _ in v}
            s = []
            for Y in years:
                s.append(self.cls(c, gid, Y) if ys & {Y - 3, Y - 2, Y - 1} else "-")
            if any(x != "-" for x in s):
                out["%d|%s" % (c, gid)] = "".join(s)
        return out


# ════════════════════════════════════════════════════════════════════════
# 표지 — 판(variant)마다 그룹 × 가용월 집계와 더미
# ════════════════════════════════════════════════════════════════════════
VARIANTS = {
    "primary": {"stc_excl": True, "no_p10": False, "min_usd": None, "rels": INSIDER, "u_as_o": False, "lookback": 1},
    "T1": {"stc_excl": True, "no_p10": True, "min_usd": T1_MIN_USD, "rels": OFFICER, "u_as_o": False, "lookback": T1_LOOKBACK},
    "T2": {"stc_excl": True, "no_p10": True, "min_usd": None, "rels": INSIDER, "u_as_o": False, "lookback": 1, "split": SPLIT_T2},
    "T3": {"alias": "primary", "mask": "classified_trade"},
    "T4": {"stc_excl": True, "no_p10": False, "min_usd": None, "rels": INSIDER, "u_as_o": True, "lookback": 1},
    "T5": {"alias": "primary", "engine": "pooled_month_fe_firm_cluster"},
    "T6": {"stc_excl": False, "no_p10": False, "min_usd": None, "rels": INSIDER, "u_as_o": False, "lookback": 1},
    # 선언된 민감도(선언 q 2026-09-26) — T1 과 같고 4/A 가 고친 원 행(corr = 1)의 금액만 고친 값(usdc)으로 잰다
    "T1C": {"stc_excl": True, "no_p10": True, "min_usd": T1_MIN_USD, "rels": OFFICER, "u_as_o": False, "lookback": T1_LOOKBACK,
            "vals": "corrected"},
}
TWINS = ("T1", "T2", "T3", "T4", "T5", "T6")
SENS = ("T1C",)                                            # 선언된 민감도(쌍둥이 밖 · 카드 controls 가 아니다)
# 집계 칸: O·R·U·N = 표지 행 수(라벨별 · 거래당 한 번) · bO… = 매수 행 · all = 표지 행 전체 · sO… = 서로 다른 매도자 수(보고자 자기 라벨)
#          stc_x · p10_x · usd_x · rel_x = 이 판에서 빠진 매도 행(강제 매도 · 10b5-1 · $ 문턱 · 관계) · p10 = 10b5-1 표지 매도 행(빼기 전)
#          joint · joint_split = 공동 제출 행 · 그 가운데 보고자 분류가 갈린 행 · 금액은 usd[그룹][달][라벨]
#          stale_O… = 그 라벨 매도 행 가운데 지연(가용일 − 거래일) > STALE_REPORT_DAYS 인 행(보고용 · 선언 l)


def _label(ls):
    for x in ("O", "R", "N"):
        if x in ls:
            return x
    return "U"


class Flags:
    """한 판의 표지. agg[그룹][가용월] = 개수·금액 사전. 더미는 dummy/active 로만 읽는다(창 밖 None)."""

    def __init__(self, name, spec, rows, hist: History, months_ok):
        self.name, self.spec, self.hist, self.months_ok = name, spec, hist, set(months_ok)
        self.agg = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter()))
        self.usd = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter()))
        self.sel = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
        self.by_year = collections.defaultdict(collections.Counter)
        sp = spec
        for r in rows:
            if not r.count:                      # 이미 센 거래(선언 c) — 이력에만 있다
                continue
            A = self.agg[r.gid][r.ym]
            yr = self.by_year[r.ym[:4]]
            elig = [c for c, rel in r.owners if is_insider(rel, INSIDER) and is_insider(rel, sp["rels"])]
            if not elig:
                if r.code == "S":
                    A["rel_x"] += 1
                continue
            if r.code == "S":                         # 선언 p — 옛 식(STC_RX_V1)과의 전후(보고 전용)
                if r.stc_v1 is None:
                    yr["stc_v1_unk"] += 1
                else:
                    yr["stc_x_v1"] += 1 if r.stc_v1 else 0
                    yr["stc_v1_only"] += 1 if (r.stc_v1 and not r.stc) else 0
            if sp["stc_excl"] and r.stc:              # 내부자 매도 가운데 강제 매도 — 제외율의 분모가 내부자 매도가 되게 관계 뒤에 센다
                if r.code == "S":
                    A["stc_x"] += 1
                    yr["stc_x"] += 1
                    if r.stc_nd is None:
                        yr["stc_nd_unk"] += 1
                    elif r.stc_nd:                    # 'non-discretionary' 갈래로만(선언 p) · 그 가운데 10b5-1 적중
                        yr["stc_nd"] += 1
                        yr["stc_nd_p10"] += 1 if r.p10_rx else 0
                continue
            ls = [hist.cls(c, r.gid, r.ty()) for c in elig]
            if sp["u_as_o"]:                          # 선언 m — 보고자 라벨에서 먼저 U → O, 그다음 JOINT_RULE
                l0 = _label(ls)
                ls = ["O" if x == "U" else x for x in ls]
                if r.code == "S" and _label(ls) != l0 and l0 != "U":
                    A["u2o_relabel"] += 1             # 1차 O + U 로는 못 만드는 행(보고자 [R, U] 공동 행 등)
            lab = _label(ls)
            if r.code == "P":
                A["b" + lab] += 1
                continue
            yr["S"] += 1
            yr["S_rx"] += 1 if r.p10_rx else 0
            if r.ym >= SPLIT_T2:
                yr["S_post"] += 1
                yr["S_box"] += r.p10_box
                yr["S_or"] += 1 if r.p10 else 0
                yr["S_mis"] += 1 if bool(r.p10_rx) != bool(r.p10_box) else 0
                yr["S_post_prebox"] += 1 if r.fdate < AFF_FROM else 0      # 선언 n — 'post' 인데 체크박스 전 제출일
            if r.p10:
                A["p10"] += 1
            if sp["no_p10"] and r.p10:
                A["p10_x"] += 1
                continue
            usd = r.usdc if (sp.get("vals") == "corrected" and r.corr == 1) else r.usd   # 선언 q — 1차 = 제출된 그대로
            if r.corr == 1 and sp["min_usd"] is not None:     # 선언 q — 고친 값이면 문턱을 넘나드는 행(보고 전용 · T1 대 T1C)
                if (r.usd is not None and r.usd >= sp["min_usd"]) != (r.usdc is not None and r.usdc >= sp["min_usd"]):
                    yr["corr_t1_cross"] += 1
            if sp["min_usd"] is not None and (usd is None or usd < sp["min_usd"]):
                A["usd_x"] += 1
                continue
            if len(elig) > 1:
                A["joint"] += 1
                yr["joint"] += 1
                if len(set(ls)) > 1:
                    A["joint_split"] += 1
                    yr["joint_split"] += 1
            A[lab] += 1
            A["all"] += 1
            yr[lab] += 1
            yr["corr_S"] += 1 if r.corr == 1 else 0           # 선언 q — 4/A 가 값을 고친 표지 매도 행(1차는 제출된 그대로)
            yr["tdh_S"] += 1 if r.tdh else 0                  # 선언 q2 — 4/A 가 거래일을 고친 표지 매도 행(사건 · 라벨 그대로)
            if r.lag is not None and r.lag > STALE_REPORT_DAYS:      # 선언 l — 보고용
                A["stale_" + lab] += 1
                yr["stale_S"] += 1
                yr["stale_" + lab] += 1
            for c, l in zip(elig, ls):
                self.sel[r.gid][r.ym][l].add(c)
            if usd is not None:
                self.usd[r.gid][r.ym][lab] += usd
                self.usd[r.gid][r.ym]["all"] += usd

    def counts(self, gid, ym):
        g = self.agg.get(gid)
        return g.get(ym, collections.Counter()) if g else collections.Counter()

    def dummy(self, gid, ym, kind="OS"):
        """OS · RS · ALL(분류 없는 전체 매도) · MASK(T3 표본: 분류된 P·S ≥ 1) → 1 · 0 · None(창 밖 · 선언 f)."""
        if ym not in self.months_ok:
            return None
        A = self.counts(gid, ym)
        if kind == "OS":
            if A["O"] > 0 or (self.spec["u_as_o"] and A["U"] > 0):
                return 1
            return None if A["N"] > 0 else 0
        if kind == "RS":
            if A["R"] > 0:
                return 1
            return None if A["N"] > 0 else 0
        if kind == "ALL":
            return 1 if A["all"] > 0 else 0
        if kind == "MASK":
            return 1 if (A["O"] + A["R"] + A["bO"] + A["bR"]) > 0 else 0
        raise ValueError(kind)

    def active(self, gid, r, kind="OS", window=None):
        """가용월 r−window+1..r 에 더미 1 이 하나라도 → 1 · 아니고 None 이 끼면 None · 아니면 0."""
        w = window or self.spec.get("lookback") or 1
        vals = [self.dummy(gid, QC.mshift(r, -j), kind) for j in range(w)]
        if 1 in vals:
            return 1
        return None if None in vals else 0

    def flag(self, gid, ym, kind="OS"):
        """회귀에 넣는 이 판의 표지 — lookback 이 1 보다 크면(T1) 룩백 더미, 아니면 그달 더미."""
        return self.active(gid, ym, kind) if (self.spec.get("lookback") or 1) > 1 else self.dummy(gid, ym, kind)

    def series(self, gids, months, kind="OS"):
        return {g: [self.flag(g, m, kind) for m in months] for g in gids}

    def export(self):
        """cikmonth.json 모양 — 그룹 → 가용월 → 개수(0 은 빼고) + 매도자 수(s…) + 금액($)."""
        out = {}
        for g in sorted(self.agg, key=str):
            for m in sorted(self.agg[g]):
                c = {k: v for k, v in self.agg[g][m].items() if v}
                c.update({"s" + k: len(v) for k, v in self.sel[g][m].items() if v})
                c.update({k + "$": round(v, 2) for k, v in self.usd[g][m].items() if v})
                if c:
                    out.setdefault(str(g), {})[m] = c
        return out


def routine_doc(H: History, years):
    """routine.json(§A 출력 c) — 분류일 · 연도별 개수 · 분류일 뒤 도착 제외 수 · 키별 분류 문자열."""
    years = list(years)
    tab = H.table(years)
    by = {}
    for j, Y in enumerate(years):
        cnt = collections.Counter(s[j] for s in tab.values())
        by[str(Y)] = {"D": H.cal.first_td(Y), "R": cnt["R"], "O": cnt["O"], "U": cnt["U"], "N": cnt["N"], "late_excluded": H.late(Y)}
    return {"note": "R1 CMP 분류 — 키 'CIK|그룹' · 문자 j = years[j] 의 분류(R 루틴 · O 기회주의 · U 분류 불가 · N 자료 부족 · '-' 창 안 이력 없음). "
                    "build/r_r1_flags.py 규칙(가용일 ≤ D_Y · Form 4/4A P·S · 강제 매도 제외 · 공동 제출은 모든 보고자 · 부분 중복 행은 새 보고자만 · "
                    "4/A 정정 행의 정정 보고자는 넣지 않는다 — 머리말 선언 r). 보고자 관계를 거르지 않으므로 'Other' 만인 보고자의 분류도 센다"
                    "(표지 라벨에는 내부자 관계 보고자만 쓰인다).",
            "stc_excluded": H.stc_excl, "first_year": H.y0, "years": years, "by_year": by, "cls": tab}


# cikmonth.json 칸 — 정식 이름(1차 판 · 선언 b 의 행 라벨) 과 소비 쪽(r_stagem.FIELDS["ins"] · r_p0_adapt) 이 찾는 별칭(한 곳).
# 별칭 값은 정식 칸과 **같은 수**다(행 라벨 기준 — 공동 제출 행은 JOINT_RULE 로 한 라벨만). 매도자 수(보고자 자기 라벨)는 sO… 칸.
BASE_KEYS = ("O", "R", "U", "N", "all", "bO", "bR", "bU", "bN")
EXPORT_ALIASES = {"os_n": "O", "rs_n": "R", "un_n": "U", "s_n": "all", "ob_n": "bO", "rb_n": "bR"}
TWIN_KEYS = (("T1", "O", "t1_os_n"), ("T2", "O", "t2_os_n"), ("T2", "R", "t2_rs_n"), ("T4", "O", "t4_os_n"), ("T4", "R", "t4_rs_n"),
             ("T6", "O", "t6_os_n"), ("T6", "R", "t6_rs_n"), ("T1C", "O", "t1c_os_n"))


def cikmonth_doc(B, sparse=True):
    """cikmonth.json(§A 출력 b) — 그룹 × 가용월 한 칸 = 1차 판 개수 + 매도자 수 + 별칭 + 쌍둥이 칸.
    ⚠ 소비 쪽이 알아야 할 것 넷: (1) months_ok 밖 달은 싣지 않는다 — «없음 = 0» 으로 읽으면 창 끝(2026-07)이 거짓 0 이 된다.
      (2) 표에 없는 (그룹, 달)은 그달 표지 행이 없다는 뜻(0)이다 — 단 t1_os3(T1 3개월 룩백 더미)은 룩백이 걸친 달도 칸을 만들어 싣는다.
      (3) os_na / rs_na = 1 이면 그 칸의 더미는 None(자료 부족 N 행 · 선언 f) — 표본에서 뺄 것. T4 는 t4_os_na · t4_rs_na.
      (4) sparse(기본): 칸 안에서 값이 0 인 키는 싣지 않는다(«키 없음 = 0» · r_stagem.FIELDS 의 희소 규약). null(모름 — t1_os3)은 싣는다.
      T4 는 t4_os_n · t4_rs_n 을 읽는다 — 1차 O + U 로 다시 만들면 보고자 [R, U] 공동 행을 놓친다(선언 m)."""
    F = B["flags"]
    P, mo = F["primary"], B["months_ok"]
    keys = set()
    for v in ("primary", "T1", "T2", "T4", "T6", "T1C"):
        for g, bym in F[v].agg.items():
            for m in bym:
                if m in mo:
                    keys.add((g, m))
    T1, T1C = F["T1"], F["T1C"]
    for TT in (T1, T1C):
        for g, bym in TT.agg.items():
            for m, c in bym.items():
                if c["O"] > 0:
                    for j in range(1, T1_LOOKBACK):
                        m2 = QC.mshift(m, j)
                        if m2 in mo:
                            keys.add((g, m2))
    groups = {}
    for g, m in sorted(keys, key=lambda k: (str(k[0]), k[1])):
        c = P.counts(g, m)
        rec = {k: int(c[k]) for k in BASE_KEYS}
        rec.update({"s" + k: len(P.sel[g][m][k]) if (g in P.sel and m in P.sel[g]) else 0 for k in ("O", "R", "U", "N")})
        rec.update({a: rec[k] for a, k in EXPORT_ALIASES.items()})
        for v, k, a in TWIN_KEYS:
            rec[a] = int(F[v].counts(g, m)[k])
        rec["t1_os3"] = T1.active(g, m, "OS", T1_LOOKBACK)
        rec["t1c_os3"] = T1C.active(g, m, "OS", T1_LOOKBACK)          # 선언된 민감도(선언 q) — 고친 금액
        rec["os_na"] = 1 if P.dummy(g, m, "OS") is None else 0
        rec["rs_na"] = 1 if P.dummy(g, m, "RS") is None else 0
        rec["t4_os_na"] = 1 if F["T4"].dummy(g, m, "OS") is None else 0
        rec["t4_rs_na"] = 1 if F["T4"].dummy(g, m, "RS") is None else 0
        rec["stc_x"], rec["p10"], rec["joint"] = int(c["stc_x"]), int(c["p10"]), int(c["joint"])
        u = P.usd[g][m] if (g in P.usd and m in P.usd[g]) else {}
        rec["usd_all"], rec["usd_O"] = round(u.get("all", 0.0), 2), round(u.get("O", 0.0), 2)
        if sparse:
            rec = {k: v for k, v in rec.items() if v is None or v != 0}
        groups.setdefault(str(g), {})[m] = rec
    return {"note": "R1 그룹 × 가용월 집계 — build/r_r1_flags.py(cikmonth_doc 머리말의 ⚠ 넷을 읽을 것). 칸: O·R·U·N 표지 행 수(JOINT_RULE) · "
                    "bO… 매수 행 · all 재량 매도 행 · sO… 매도자 수 · 별칭 aliases · 쌍둥이 t1_os_n(Officer · $10만 · 10b5-1 제외) · "
                    "t1_os3(그 3개월 룩백 더미) · t1c_os_n · t1c_os3(선언된 민감도 T1C — 4/A 가 고친 금액 · 선언 q) · "
                    "t2_*(10b5-1 제외) · t4_*(U → O 뒤 JOINT_RULE · 1차 O+U 와 다르다) · "
                    "t6_*(강제 매도 포함) · T3 = O+R+bO+bR ≥ 1 · T5 = 1차. " + ("희소 — 값이 0 인 키는 싣지 않는다(키 없음 = 0 · null = 모름)."
                                                                     if sparse else ""),
            "sparse": bool(sparse),
            "months_ok": sorted(m for m in mo if m >= min((m for _, m in keys), default="9999")),
            "joint_rule": JOINT_RULE, "aliases": EXPORT_ALIASES, "twin_keys": [list(x) for x in TWIN_KEYS],
            "variants": {v: {k: (list(x) if isinstance(x, tuple) else x) for k, x in VARIANTS[v].items()} for v in VARIANTS},
            "rules": {"stc_rx": STC_RX.pattern, "stc_rx_v1_audit": STC_RX_V1.pattern, "plan_rx": PLAN_RX.pattern, "neg_rx": NEG_RX.pattern,
                      "corrections": "4/A 정정은 새 사건이 아니다(선언 q) — 정정 행 세지 않음 · 원 행 가용일 · 값은 제출된 그대로(1차) · "
                                     "고친 값은 T1C 민감도만 · 거래일만 고친 4/A 도 새 사건이 아니다(선언 q2 · 고친 거래일은 분류 이력에만)",
                      "history": "선언 r"},
            "groups": groups}


def build(rows, cal: Cal, start=DATA_START, end=DATA_END, variants=("primary",) + TWINS + SENS + ("ALL",), months_ok=None,
          corrections=True, date_corrections=True):
    """정본 행 → {"flags": {판: Flags}, "hist": {stc_excl: History}, "prep": 정리 개수, "months_ok": …}."""
    rows, pst = prepare(rows, cal, corrections=corrections, date_corrections=date_corrections)
    mo = set(months_ok) if months_ok is not None else avail_months(cal, start, end)
    H = {True: History(rows, cal, True, start)}
    F = {}
    for v in variants:
        if v == "ALL":
            continue
        sp = VARIANTS[v]
        base = sp.get("alias")
        if base:
            if base not in F:
                F[base] = Flags(base, VARIANTS[base], rows, H[True], mo)
            F[v] = F[base]
            continue
        if not sp["stc_excl"] and False not in H:
            H[False] = History(rows, cal, False, start)
        F[v] = Flags(v, sp, rows, H[sp["stc_excl"]], mo)
    if "primary" not in F:
        F["primary"] = Flags("primary", VARIANTS["primary"], rows, H[True], mo)
    F["ALL"] = F["primary"]            # ALL 은 1차 행 규칙의 dummy(kind="ALL")
    return {"flags": F, "hist": H, "prep": pst, "months_ok": mo, "rows": rows}


# ════════════════════════════════════════════════════════════════════════
# Stage S — Eg 상위 30 에서 OS 활성을 빼고 차순위로 채운다 · 대조 교체
# ════════════════════════════════════════════════════════════════════════
def status_of(key, r, gid_of, fpi_of, flags: Flags, kind="OS", window=STAGE_S_WINDOW):
    """이름의 편입일 상태 — 'fpi'(걸러낼 수 없음) · 'unres'(그룹 미해결) · 'unk'(표지 None) · 'on' · 'off'."""
    if fpi_of is not None and fpi_of(key) == 1:
        return "fpi"
    g = gid_of(key)
    if not g:
        return "unres"
    a = flags.active(g, r, kind, window)
    return "unk" if a is None else ("on" if a == 1 else "off")


def replace_top(ranked, n, drop, fill_ok):
    """상위 n 에서 drop 을 빼고, 차순위 가운데 fill_ok(이름) 가 참인 것으로 Eg 순서대로 채운다."""
    top = list(ranked[:n])
    dset = set(drop)
    keep = [k for k in top if k not in dset]
    fill = []
    for k in ranked[n:]:
        if len(keep) + len(fill) >= n:
            break
        if k not in dset and fill_ok(k):
            fill.append(k)
    return {"picks": keep + fill, "dropped": [k for k in top if k in dset], "filled": fill,
            "n_r": len([k for k in top if k in dset]), "short": n - len(keep) - len(fill)}


def stage_s(ranked, r, gid_of, fpi_of, flags: Flags, n=STAGE_S_N, window=STAGE_S_WINDOW):
    """사양 Stage S — 편입일 r 의 명단. 비중은 V0 규칙(시총가중 · 20% 상한 · 금융 지수 비중)으로 러너가 매긴다."""
    st = {k: status_of(k, r, gid_of, fpi_of, flags, "OS", window) for k in ranked}
    out = replace_top(ranked, n, [k for k in ranked[:n] if st[k] == "on"], lambda k: st[k] in ("off", "fpi"))
    top = ranked[:n]
    out.update({"r": r, "n_fpi_top": sum(st[k] == "fpi" for k in top), "n_unres_top": sum(st[k] == "unres" for k in top),
                "n_unk_top": sum(st[k] == "unk" for k in top), "n_fpi_fill": sum(st[k] == "fpi" for k in out["filled"]),
                "n_skip_fill": sum(1 for k in ranked[n:ranked.index(out["filled"][-1]) + 1] if st[k] in ("unk", "unres"))
                if out["filled"] else 0})
    return out


def pick_set(top, cands, n_r, rng, exclude=()):
    """대조 C1 — 상위 명단 가운데 후보 집합에서 n_r 개(많으면 무작위) · 모자라면 나머지에서 무작위로 채운다.
    exclude(편입일 r 의 OS 활성 이름 · 선언 o)는 후보에서도 채움에서도 뺀다 — C1 이 Stage S 와 같은 이름을 빼지 않게.
    채울 이름도 모자라면 n_r 보다 적게 돌려준다(부르는 쪽이 짧음을 센다)."""
    ex = set(exclude)
    cs = set(cands) - ex
    c = [k for k in top if k in cs]
    rest = [k for k in top if k not in cs and k not in ex]
    if len(c) >= n_r:
        return [c[j] for j in sorted(rng.choice(len(c), n_r, replace=False).tolist())]
    k = min(len(rest), n_r - len(c))
    extra = [rest[j] for j in sorted(rng.choice(len(rest), k, replace=False).tolist())] if k > 0 else []
    return c + extra


def pick_ordered(top, score, n_r):
    """대조 C3 · C4 — 점수(12-1 모멘텀 · FP 베타) 상위 n_r(점수 없는 이름은 뒤 · 동점은 Eg 순서).
    C2(매도 $/시총)는 pick_c2 를 쓴다 — 점수 0(매도 없음)이 순위에 끼면 늘 최상위 Eg 이름을 뺀다(선언 o)."""
    pos = {k: j for j, k in enumerate(top)}
    s = sorted(top, key=lambda k: (score(k) is None, -(score(k) or 0.0), pos[k]))
    return s[:n_r]


def pick_c2(top, score, n_r, rng, exclude=()):
    """대조 C2 — 전체 매도 $/시총 > 0 인 이름만 점수 순(동점 Eg 순서) · 모자라면 나머지(매도 없음)에서 시드 무작위로 채운다.
    반환 {"picks", "n_nosale"(채움 수 · 편입마다 보고)}. exclude 는 pick_set 과 같은 뜻(부르는 쪽이 정한다 · 기본 없음)."""
    ex = set(exclude)
    pos = {k: j for j, k in enumerate(top)}
    sc = {k: score(k) for k in top if k not in ex}
    pos_k = sorted((k for k, v in sc.items() if v is not None and v > 0), key=lambda k: (-sc[k], pos[k]))
    picks = pos_k[:n_r]
    ps = set(pos_k)
    rest = [k for k in top if k in sc and k not in ps]
    need = min(len(rest), n_r - len(picks))
    extra = [rest[j] for j in sorted(rng.choice(len(rest), need, replace=False).tolist())] if need > 0 else []
    return {"picks": picks + extra, "n_nosale": len(extra)}


def c1_overlap(picks, os_active):
    """C1 명단과 OS 활성 이름의 겹침 수(편입마다 보고 · exclude 를 제대로 넘겼으면 0)."""
    return len(set(picks) & set(os_active))


def pick_random(top, n_r, rng):
    """위약 — 무작위 n_r(default_rng(SEED + i) 를 부르는 쪽이 넘긴다)."""
    return [top[j] for j in sorted(rng.choice(len(top), min(n_r, len(top)), replace=False).tolist())]


def jaccard(a, b):
    a, b = set(a), set(b)
    return (len(a & b) / len(a | b)) if (a | b) else None


def split_t2(ym):
    return "post" if ym >= SPLIT_T2 else "pre"


# ════════════════════════════════════════════════════════════════════════
# F0 · 밀도 보고(수익 없이 — 등록 전 커밋)
# ════════════════════════════════════════════════════════════════════════
def _med(x):
    x = sorted(x)
    if not x:
        return None
    n = len(x)
    return x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2


def f0_stage_m(flags: Flags, members, months):
    """사양 F0 — 월 OS 종목 수 중앙값 ≥ 20 · 최소 ≥ 5 · 월 RS 종목 수 중앙값 ≥ 10. members = {달: 그룹 모음}."""
    os_n, rs_n, rows = [], [], {}
    for m in months:
        gs = members.get(m) or ()
        o = [flags.flag(g, m, "OS") for g in gs]
        s = [flags.flag(g, m, "RS") for g in gs]
        n_os, n_rs = sum(1 for v in o if v == 1), sum(1 for v in s if v == 1)
        rows[m] = {"n": len(gs), "os": n_os, "rs": n_rs, "os_none": sum(v is None for v in o)}
        os_n.append(n_os)
        rs_n.append(n_rs)
    res = {"months": len(months), "os_median": _med(os_n), "os_min": min(os_n) if os_n else None,
           "rs_median": _med(rs_n), "by_month": rows}
    res["pass"] = bool(os_n and res["os_median"] >= 20 and res["os_min"] >= 5 and res["rs_median"] >= 10)
    return res


def f0_stage_s(n_r_list):
    """사양 F0 — 편입당 교체 수 중앙값 2~15. 벗어나면 측정 불가."""
    md = _med(list(n_r_list))
    return {"median": md, "pass": md is not None and 2 <= md <= 15}


def density(B, members=None, months=None, years=None):
    """밀도 보고서 본문 — 판별 없이 개수만. B = build() 결과."""
    F = B["flags"]["primary"]
    H = B["hist"][True]
    yrs = {}
    for y, c in sorted(F.by_year.items()):
        S = c["S"]
        d = {"sale_rows": S, "stc_excluded": c["stc_x"], "stc_rate": (c["stc_x"] / (S + c["stc_x"])) if (S + c["stc_x"]) else None,
             "U_share": (c["U"] / S) if S else None, "N_share": (c["N"] / S) if S else None,
             "p10_regex_rate": (c["S_rx"] / S) if S else None, "joint_rows": c["joint"], "joint_label_split": c["joint_split"]}
        d.update({"stc_nd_only": c["stc_nd"], "stc_nd_only_p10": c["stc_nd_p10"], "stc_nd_unknown": c["stc_nd_unk"],
                  "stc_excluded_v1": c["stc_x_v1"], "stc_v1_only_kept": c["stc_v1_only"], "stc_v1_unknown": c["stc_v1_unk"],
                  "corr_S": c["corr_S"], "corr_t1_cross": c["corr_t1_cross"],
                  "stale_S": c["stale_S"], "stale_O": c["stale_O"], "stale_R": c["stale_R"]})
        if c["S_post"]:
            d.update({"p10_box_rate": c["S_box"] / c["S_post"], "p10_or_rate": c["S_or"] / c["S_post"],
                      "p10_regex_box_mismatch": c["S_mis"] / c["S_post"], "S_post_prebox": c["S_post_prebox"]})
        yrs[y] = d
    cy = {}
    for Y in (years or []):
        tab = collections.Counter(H.cls(c, g, Y) for (c, g), v in H.h.items()
                                  if any(Y - 3 <= int(td[:4]) <= Y - 1 for td, _ in v))
        cy[str(Y)] = {"D": H.cal.first_td(Y), "R": tab["R"], "O": tab["O"], "U": tab["U"], "N": tab["N"], "late_excluded": H.late(Y)}
    out = {"prep": B["prep"], "by_year": yrs, "classification": cy, "joint_rule": JOINT_RULE,
           "stale": stale_report(F, B["months_ok"], members, months), "corrections": corrections_report(B["rows"], months)}
    if members is not None and months:
        out["f0_stage_m"] = f0_stage_m(F, members, months)
    return out


def stale_report(F: Flags, months_ok, members=None, months=None):
    """선언 l — 지연 > STALE_REPORT_DAYS 인 표지 매도 행이 만든 OS 칸. 전 창(months_ok)과 F0 멤버 창(members · months) 따로."""
    def one(cells):
        n_os = n_with = n_only = rows = 0
        for g, m in cells:
            A = F.counts(g, m)
            if A["O"] > 0:
                n_os += 1
                s = A["stale_O"]
                rows += s
                n_with += 1 if s > 0 else 0
                n_only += 1 if (s > 0 and s == A["O"]) else 0
        return {"os_cells": n_os, "os_cells_with_stale": n_with, "os_cells_only_stale": n_only, "stale_O_rows": rows}
    allc = [(g, m) for g, bym in F.agg.items() for m in bym if m in months_ok]
    out = {"days": STALE_REPORT_DAYS, "all_months_ok": one(allc)}
    if members is not None and months:
        out["f0_window_members"] = one([(g, m) for m in months for g in (members.get(m) or ())])
    return out


def corrections_report(rows, months=None):
    """선언 l — 표지에 센 매도 행 가운데 (그룹, 보고자, 거래일, 코드) 가 4/A 를 끼고 둘 이상 접수번호에 나오는 키 ·
    그 가운데 사건월이 둘 이상인 키(한 거래가 두 달에 표지를 세운다). months 를 주면 그 창 안 사건월만.
    broad = 넓은 정의(정리 뒤 모든 행 · P 포함 · 세지 않는 행 · 모든 보고자(정정 행의 정정 보고자 ocor 포함) · 모든 달 —
    검토 실측 503 · 238 과 같은 정의 · 정정 행이 남아 있으므로 선언 q 뒤에도 거의 그대로다).
    선언 q 뒤로는 세는 행의 keys_multi_acc_with_4A 가 0 이어야 한다(정정 행은 세지 않는다) · corrections_by_year 는 정정 행 수."""
    mset = set(months) if months else None
    by, br = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        for c, _ in tuple(r.owners) + tuple(r.ocor or ()):
            br[(r.gid, c, r.tdate, r.code)].add((r.acc, r.doc, r.ym))
        if not r.count or r.code != "S" or (mset is not None and r.ym not in mset):
            continue
        for c, rel in r.owners:
            if is_insider(rel):
                by[(r.gid, c, r.tdate, r.code)].add((r.acc, r.doc, r.ym))

    def cnt(d):
        multi = [v for v in d.values() if len({a for a, _, _ in v}) > 1 and any(x == "4/A" for _, x, _ in v)]
        return len(multi), sum(1 for v in multi if len({m for _, _, m in v}) > 1)
    a, b = cnt(by)
    c, d = cnt(br)
    # 선언 q — 정정 행(corr = 2 · 4/A 제출 연도별) · 짝 · 짝 없음 · 원 행과 사건월이 다른 짝(옛 규칙이면 새 달에 사건을 세웠을 것)
    cy = collections.defaultdict(collections.Counter)
    for r in rows:
        if r.corr == 2:
            y = cy[r.fdate[:4]]
            y["corr_rows"] += 1
            y["corr_rows_S"] += 1 if r.code == "S" else 0
            if r.ctgt:
                y["paired"] += 1
                y["paired_cross_month"] += 1 if r.cym != r.ym else 0
            else:
                y["unpaired"] += 1
        elif r.corr == 3:                                              # 선언 q2 — 거래일 정정 행
            y = cy[r.fdate[:4]]
            y["dcorr_rows"] += 1
            y["dcorr_rows_S"] += 1 if r.code == "S" else 0
            y["dcorr_paired"] += 1 if r.ctgt else 0
            y["dcorr_paired_cross_month"] += 1 if (r.ctgt and r.cym != r.ym) else 0
        if r.corr == 1:
            cy[r.fdate[:4]]["targets_by_orig_year"] += 1
        if r.tdh:
            cy[r.fdate[:4]]["dcorr_targets_by_orig_year"] += 1
    tot = collections.Counter()
    for v in cy.values():
        tot.update(v)
    return {"keys_multi_acc_with_4A": a, "keys_cross_month": b, "window": [min(months), max(months)] if months else None,
            "broad": {"keys_multi_acc_with_4A": c, "keys_cross_month": d},
            "corrections_by_year": {y: dict(v) for y, v in sorted(cy.items())}, "corrections_total": dict(tot)}


# ════════════════════════════════════════════════════════════════════════
# 합성 시험(수익 없음)
# ════════════════════════════════════════════════════════════════════════
def _syn():
    """합성 제출 — 발행사 그룹 g1(CIK 101 + 선행 CIK 100) · g2(CIK 200)."""
    R = []
    n = [0]

    def add(fd, td, code, own, doc="4", gid="g1", issuer=101, sh=100.0, px=50.0, fn="", rem="", aff=None, acc=None, sk=None,
            orig=None):
        n[0] += 1
        R.append(_mkrow(acc or "A%05d" % n[0], sk if sk is not None else n[0], doc, fd, issuer, gid, td, code,
                        CODES.get(code, "D"), sh, px, own, fn, rem, aff, orig=orig))
        return R[-1]
    Of = lambda c: (c, "Officer")
    Di = lambda c: (c, "Director")
    # A: 3·3·3월 → 2016 루틴 · 2016-05 매도 → RS
    for y in (2013, 2014, 2015):
        add("%d-03-11" % y, "%d-03-10" % y, "S", [Of(1)])
    add("2016-05-03", "2016-05-02", "S", [Of(1)])
    # B: 3·6·9월 → 기회주의 · 2016-05 매도 → OS(g1)
    for y, m in ((2013, 3), (2014, 6), (2015, 9)):
        add("%d-%02d-11" % (y, m), "%d-%02d-10" % (y, m), "S", [Of(2)])
    add("2016-05-04", "2016-05-03", "S", [Of(2)], gid="g2", issuer=200)      # 다른 그룹 → g2 에서는 이력 없음(U)
    add("2016-06-02", "2016-06-01", "S", [Of(2)])                             # g1 → OS 2016-06
    # C: 2014·2015 만 → U(2016)
    for y in (2014, 2015):
        add("%d-04-11" % y, "%d-04-10" % y, "S", [Di(3)])
    add("2016-07-06", "2016-07-05", "S", [Di(3)])
    # D: 3·3월 + 2015-12-28 거래를 2016-01-15 에 늦게 제출 → D_2016(01-04)엔 2015 가 비어 U · 늦은 제외 1
    add("2013-03-11", "2013-03-10", "S", [Of(4)])
    add("2014-03-11", "2014-03-10", "S", [Of(4)])
    add("2016-01-15", "2015-12-28", "S", [Of(4)])
    add("2016-08-02", "2016-08-01", "S", [Of(4)])
    # D2: 같은 모양인데 12-30 에 제출 → 12월이 이력에 들어와 O(3·3·12)
    add("2013-03-11", "2013-03-10", "S", [Of(5)])
    add("2014-03-11", "2014-03-10", "S", [Of(5)])
    add("2015-12-30", "2015-12-28", "S", [Of(5)])
    add("2016-08-03", "2016-08-02", "S", [Of(5)])
    # E: P 와 S 섞어 1월 → 루틴
    add("2013-01-15", "2013-01-14", "P", [Di(6)])
    add("2014-01-15", "2014-01-14", "S", [Di(6)])
    add("2015-01-15", "2015-01-14", "P", [Di(6)])
    add("2016-01-15", "2016-01-14", "P", [Di(6)])
    add("2016-09-02", "2016-09-01", "S", [Di(6)])
    add("2017-01-17", "2017-01-13", "P", [Di(6)])                             # 2018 에도 루틴(1·1·1월) — T3 가면용
    # F: 2015 거래가 강제 매도뿐 → 1차 U · T6 R
    add("2013-02-11", "2013-02-10", "S", [Of(7)])
    add("2014-02-11", "2014-02-10", "S", [Of(7)])
    add("2015-02-11", "2015-02-10", "S", [Of(7)], fn="Shares sold to cover the tax withholding obligation in respect of vesting.")
    add("2016-10-04", "2016-10-03", "S", [Of(7)])
    # G: 2015 가 Form 5 뿐 → U
    add("2013-05-11", "2013-05-10", "S", [Of(8)])
    add("2014-05-11", "2014-05-10", "S", [Of(8)])
    add("2016-02-12", "2015-05-10", "S", [Of(8)], doc="5")
    add("2016-11-02", "2016-11-01", "S", [Of(8)])
    # T4 공동: A(2016 루틴) + C(2016 분류 불가) 한 행(2016-02) → 1차 R(RS) · T4 는 U → O 뒤 O>R → O(OS) · 1차 O + U 로는 못 만든다
    add("2016-02-04", "2016-02-03", "S", [Of(1), Di(3)])
    # 공동: H(루틴 3월) + I(펀드 · 공동 제출에서만 3·3·7월 → 기회주의) — 한 행 한 번 · O>R → OS
    for y in (2013, 2014):
        add("%d-03-12" % y, "%d-03-11" % y, "S", [Of(9), (10, "TenPercentOwner")])
    add("2015-03-12", "2015-03-11", "S", [Of(9)])
    add("2015-07-12", "2015-07-11", "S", [(10, "TenPercentOwnerOther")])
    j = add("2016-12-02", "2016-12-01", "S", [Of(9), (10, "TenPercentOwner"), (11, "Other")], sh=1000.0, px=100.0)
    # 정정: 원본 2017-03-02 · 같은 값 4/A → 지움 · 단가 다른 4/A → 새 행(자기 공시일 2017-04)
    add("2017-03-02", "2017-03-01", "S", [Of(2)], acc="ORIG1", sk=1)
    add("2017-04-10", "2017-03-01", "S", [Of(2)], doc="4/A", acc="AMD1", sk=1)
    add("2017-04-11", "2017-03-01", "S", [Of(2)], doc="4/A", px=51.0, acc="AMD2", sk=1)
    # 같은 제출 안 같은 값 두 로트 → 둘 다 남는다
    add("2017-05-03", "2017-05-02", "S", [Of(2)], acc="LOT", sk=1)
    add("2017-05-03", "2017-05-02", "S", [Of(2)], acc="LOT", sk=2)
    # 거래일 > 제출일 → 버림
    add("2017-06-01", "2017-06-05", "S", [Of(2)])
    # 거래 연도 분류: 2016-12-29 거래 · 2017-01-05 제출 → 사건월 2017-01 · 분류는 D_2016(B 는 2016 에도 O)
    add("2017-01-05", "2016-12-29", "S", [Of(2)])
    # 강제 매도 행 연결: 한 제출 두 행 · 각주는 첫 행에만 → 첫 행만 빠진다(2017-07 · B)
    add("2017-07-06", "2017-07-05", "S", [Of(2)], fn="Represents shares sold to satisfy tax withholding upon vesting of RSUs.", acc="STC2", sk=1)
    add("2017-07-06", "2017-07-05", "S", [Of(2)], fn="The price reported is a weighted average.", acc="STC2", sk=2)
    # T1: 2017-09 이사 단독 · 임원 $5만 · 임원 $20만 10b5-1 · 2017-10 임원 $20만 재량(B)
    add("2017-09-06", "2017-09-05", "S", [Di(3)], sh=10000.0, px=50.0)
    add("2017-09-07", "2017-09-06", "S", [Of(2)], sh=1000.0, px=50.0)
    add("2017-09-08", "2017-09-07", "S", [Of(2)], sh=4000.0, px=50.0, fn="Sold pursuant to a Rule 10b5-1 trading plan adopted May 1, 2017.")
    add("2017-10-04", "2017-10-03", "S", [Of(2)], sh=4000.0, px=50.0)
    # T2 · 체크박스: 2023-05 AFF=1(빠짐) · 2022-05 AFF=1(쓰지 않음) · 부정문 각주(빠지지 않음). B 는 2019·2020·2021 달이 달라 2022·2023 에 O
    for fd, td in (("2019-02-06", "2019-02-05"), ("2020-08-05", "2020-08-04"), ("2021-11-03", "2021-11-02")):
        add(fd, td, "S", [Of(2)])
    add("2023-05-03", "2023-05-02", "S", [Of(2)], aff="1")
    add("2022-05-03", "2022-05-02", "S", [Of(2)], aff="1")
    add("2022-06-02", "2022-06-01", "S", [Of(2)], fn="These shares were not sold pursuant to a Rule 10b5-1 trading plan.")
    # T3: 2018-02 분류된 P 만(E) · 2018-03 분류 불가 매도만(C, 2018 에는 C 가 2015·2016·2017 이 차지 않음)
    add("2018-02-06", "2018-02-05", "P", [Di(6)])
    add("2018-03-06", "2018-03-05", "S", [(12, "Director")])
    # 보고자 10인 상한으로 쪼갠 공동 제출: 같은 거래를 SPL1(21, 22) · SPL2(22, 23) → 거래는 한 번(2018-05) · 23 의 이력에는 붙는다
    add("2018-05-02", "2018-05-01", "S", [(21, "TenPercentOwner"), (22, "TenPercentOwner")], acc="SPL1", sk=1, sh=5000.0)
    add("2018-05-02", "2018-05-01", "S", [(22, "TenPercentOwner"), (23, "TenPercentOwner")], acc="SPL2", sk=1, sh=5000.0)
    # N: 자료 창 첫 해들(2012 거래) → N
    add("2012-06-05", "2012-06-04", "S", [Of(13)])
    # 선언 p — 맨 'non-discretionary' 10b5-1 계획 각주는 이제 강제 매도가 아니다(옛 식으로만 걸림 → stc_v1_only · 2017-11 B 의 O 매도) ·
    #   원천징수 맥락이 있는 'non-discretionary' 각주는 새 갈래로만 걸린다(stc_nd · 2017-11 강제 매도 1)
    add("2017-11-02", "2017-11-01", "S", [Of(2)], fn="Effected pursuant to a Rule 10b5-1 trading plan; the sale was non-discretionary.")
    add("2017-11-03", "2017-11-02", "S", [Of(2)],
        fn="Represents a non-discretionary transaction effected to satisfy tax withholding obligations upon vesting of RSUs.")
    # 선언 q — 여러 로트 정정: 원본 두 로트(100@60 · 200@61) · 4/A 가 첫 로트를 같은 값으로 다시 적고(확인 → 지움) · 둘째를 250@61 로
    #   고치고(짝 → 원 행 값 바뀜) · 새 로트 50@62 를 더한다(짝 없음 · 사건 아님). SK 10 은 문자열 정렬('10' < '2')이면 짝이 틀어진다.
    for sk, sh, px in ((1, 100.0, 60.0), (2, 200.0, 61.0)):
        add("2019-04-02", "2019-04-01", "S", [Of(41)], gid="g4", issuer=400, sh=sh, px=px, acc="ML1", sk=sk)
    for sk, sh, px in ((1, 100.0, 60.0), (2, 250.0, 61.0), (10, 50.0, 62.0)):
        add("2019-05-06", "2019-04-01", "S", [Of(41)], gid="g4", issuer=400, sh=sh, px=px, doc="4/A", acc="ML2", sk=sk)
    # 늦은 공시(선언 l): g3 보고자 31 이 3·6·9월 → 2020 기회주의 · 2020-02 거래를 2021-06 에 제출 → 2021-06 OS 는 늦은 행만으로
    for fd, td in (("2017-03-13", "2017-03-10"), ("2018-06-11", "2018-06-08"), ("2019-09-11", "2019-09-10")):
        add(fd, td, "S", [Of(31)], gid="g3", issuer=300)
    add("2021-06-15", "2020-02-10", "S", [Of(31)], gid="g3", issuer=300)
    # 선언 q2 — 거래일 정정(g5 · 보고자 51): DC1(2018-07-02 제출 · 06-28 거래 300@40) → 4/A DC2(DATE_OF_ORIG_SUB 2018-07-02 · 06-29 거래 ·
    #   같은 값) = 정정(사건 아님 · 원 행 이력 거래일 06-29) · DC4 는 고치는 제출일이 틀려(09-05) 짝이 없다 → 새 사건 ·
    #   DC6 은 DC5 를 같은 값으로 다시 적고(확인 → 지움) 다른 거래일의 같은 값 로트를 더한다 → 확인된 원 행은 짝이 될 수 없다 → 새 사건
    add("2018-07-02", "2018-06-28", "S", [Of(51)], gid="g5", issuer=500, sh=300.0, px=40.0, acc="DC1", sk=1)
    add("2018-08-06", "2018-06-29", "S", [Of(51)], gid="g5", issuer=500, sh=300.0, px=40.0, doc="4/A", acc="DC2", sk=1, orig="2018-07-02")
    add("2018-09-04", "2018-08-30", "S", [Of(51)], gid="g5", issuer=500, sh=300.0, px=40.0, acc="DC3", sk=1)
    add("2018-10-01", "2018-08-31", "S", [Of(51)], gid="g5", issuer=500, sh=300.0, px=40.0, doc="4/A", acc="DC4", sk=1, orig="2018-09-05")
    add("2018-11-01", "2018-10-30", "S", [Of(51)], gid="g5", issuer=500, sh=500.0, px=20.0, acc="DC5", sk=1)
    add("2018-12-03", "2018-10-30", "S", [Of(51)], gid="g5", issuer=500, sh=500.0, px=20.0, doc="4/A", acc="DC6", sk=1, orig="2018-11-01")
    add("2018-12-03", "2018-10-31", "S", [Of(51)], gid="g5", issuer=500, sh=500.0, px=20.0, doc="4/A", acc="DC6", sk=2, orig="2018-11-01")
    # 선언 q2 — 앞 4/A 가 값을 고친 원 행(DC7 300@40 → DC8 300@45)을 다른 4/A(DC9)가 제출된 값 300@40 으로 거래일만 바꿔 적었다 → 거래일 정정
    add("2020-03-02", "2020-02-27", "S", [Of(53)], gid="g5", issuer=500, sh=300.0, px=40.0, acc="DC7", sk=1)
    add("2020-03-10", "2020-02-27", "S", [Of(53)], gid="g5", issuer=500, sh=300.0, px=45.0, doc="4/A", acc="DC8", sk=1, orig="2020-03-02")
    add("2020-04-06", "2020-02-28", "S", [Of(53)], gid="g5", issuer=500, sh=300.0, px=40.0, doc="4/A", acc="DC9", sk=1, orig="2020-03-02")
    # 선언 q2 — 한 4/A(DV2)가 한 원 로트(DV1 221@81.58 · 05-13)의 값(SK 2: 05-13 을 7500@80.65 로)과 거래일(SK 1: 221@81.58 을 05-10 으로)을
    #   함께 고친다(실측 0001127602-12-011741 모양) → SK 2 값 정정 · SK 1 거래일 정정 · 둘 다 사건 아님
    add("2021-05-17", "2021-05-13", "S", [Of(54)], gid="g5", issuer=500, sh=221.0, px=81.58, acc="DV1", sk=1)
    add("2021-06-01", "2021-05-10", "S", [Of(54)], gid="g5", issuer=500, sh=221.0, px=81.58, doc="4/A", acc="DV2", sk=1, orig="2021-05-17")
    add("2021-06-01", "2021-05-13", "S", [Of(54)], gid="g5", issuer=500, sh=7500.0, px=80.65, doc="4/A", acc="DV2", sk=2, orig="2021-05-17")
    # 선언 q — 1차는 제출된 그대로 · T1C 민감도만 고친 값: TC1 임원 1000@50($5만 · T1 문턱 밑) → 4/A TC2 가 단가 150 으로($15만)
    add("2019-07-02", "2019-07-01", "S", [Of(52)], gid="g5", issuer=500, sh=1000.0, px=50.0, acc="TC1", sk=1)
    add("2019-08-05", "2019-07-01", "S", [Of(52)], gid="g5", issuer=500, sh=1000.0, px=150.0, doc="4/A", acc="TC2", sk=1)
    # 창 밖: 2026-07 가용 → None
    add("2026-06-30", "2026-06-29", "S", [Of(2)])
    return R, j


def selftest() -> dict:
    """합성 자료만 — 랩 수익 없음. 이름이 _ok 로 끝나는 항목이 모두 참이어야 통과."""
    import numpy as np
    t = {}
    cal = Cal()
    # 1) 달력
    t["cal_ok"] = (cal.next_td("2016-12-30") == "2017-01-03" and cal.first_td(2017) == "2017-01-03"
                   and cal.next_td("2012-10-26") == "2012-10-31" and cal.first_td(2022) == "2022-01-03"
                   and cal.is_td("2021-12-31") and cal.last_td("2026-06") == "2026-06-30"
                   and cal.next_td("2016-07-01") == "2016-07-05" and cal.next_td("2025-01-08") == "2025-01-10"
                   and cal.first_td(2016) == "2016-01-04")
    mo = avail_months(cal)
    t["months_ok"] = ("2026-06" in mo and "2026-07" not in mo and "2011-01" not in mo and "2011-02" in mo
                      and hist_y0() == 2011 and hist_y0("2011-04-01") == 2012)
    # 2) 정규식
    plan_nd = "These shares are being sold pursuant to a written non-discretionary Rule 10b5-1(c) sales plan dated November 23, 2011."
    t["stc_rx_ok"] = (is_stc("Shares sold to cover the tax withholding obligation in respect of vesting")
                      and is_stc("sell-to-cover transaction") and is_stc("Represents shares sold to satisfy tax withholding")
                      and not is_stc("a non-discretionary sale") and is_stc_v1("a non-discretionary sale")
                      and not is_stc(plan_nd) and is_stc_v1(plan_nd)
                      and is_stc("Represents a non-discretionary transaction effected to satisfy tax withholding obligations")
                      and is_stc("a non-discretionary sale of shares withheld by the issuer")
                      and not is_stc("pursuant to a Rule 10b5-1 plan; the reporting person had no discretion")
                      and not is_stc("The price reported is a weighted average")
                      and STC_RX.pattern == _STC_CORE + "|" + STC_ND)
    t["plan_rx_ok"] = (plan_hit("Sold pursuant to a Rule 10b5-1 trading plan") and plan_hit("10b5 1 plan")
                       and not plan_hit("These shares were not sold pursuant to a Rule 10b5-1 trading plan.")
                       and not plan_hit("non-10b5-1 sale") and not plan_hit("weighted average price")
                       and plan_hit("Not all shares: sales A were effected pursuant to a Rule 10b5-1 plan; sales B were not made pursuant to a Rule 10b5-1 plan."))
    # 3) 합성 제출 전체
    R, joint = _syn()
    B = build(R, cal)
    F, H = B["flags"]["primary"], B["hist"][True]
    pst = B["prep"]
    t["prep_counts"] = pst
    t["prep_ok"] = (pst.get("drop_tdate_after_fdate") == 1 and pst.get("drop_dup_amend") == 3 and pst.get("drop_not_form4") == 1
                    and pst.get("amend_new_rows", 0) == 2 and pst.get("amend_new_rows_v1", 0) == 2
                    and pst.get("corr_rows") == 6 and pst.get("corr_paired") == 5
                    and pst.get("corr_unpaired") == 1 and pst.get("corr_targets") == 5 and pst.get("corr_paired_cross_month") == 4
                    and pst.get("dcorr_rows") == 3 and pst.get("dcorr_paired") == 3 and pst.get("dcorr_targets") == 3
                    and pst.get("dcorr_paired_cross_month") == 3 and pst.get("dcorr_hist_early", 0) == 0)
    c = H.cls
    t["classify_ok"] = (c(1, "g1", 2016) == "R" and c(2, "g1", 2016) == "O" and c(2, "g2", 2016) == "U"
                        and c(3, "g1", 2016) == "U" and c(4, "g1", 2016) == "U" and c(5, "g1", 2016) == "O"
                        and c(6, "g1", 2016) == "R" and c(7, "g1", 2016) == "U" and c(8, "g1", 2016) == "U"
                        and c(9, "g1", 2016) == "R" and c(10, "g1", 2016) == "O" and c(13, "g1", 2012) == "N"
                        and c(1, "g1", 2013) == "N")
    t["classify_t6_ok"] = B["hist"][False].cls(7, "g1", 2016) == "R"
    t["late_ok"] = H.late(2016) == 1
    d = F.dummy
    t["dummy_ok"] = (d("g1", "2016-05", "RS") == 1 and d("g1", "2016-05", "OS") == 0 and d("g2", "2016-05", "OS") == 0
                     and d("g1", "2016-06", "OS") == 1 and d("g1", "2016-07", "OS") == 0 and d("g1", "2016-07", "RS") == 0
                     and d("g1", "2016-08", "OS") == 1          # D2(O) · D(U) 둘 다 8월 — O 하나로 1
                     and d("g1", "2016-09", "RS") == 1 and d("g1", "2016-10", "OS") == 0 and d("g1", "2016-11", "OS") == 0
                     and d("g1", "2026-07", "OS") is None and d("g9", "2016-05", "OS") == 0)
    t["avail_month_ok"] = d("g1", "2017-01", "OS") == 1 and F.counts("g1", "2017-01")["O"] == 1
    cj = F.counts("g1", "2016-12")
    t["joint_ok"] = (cj["O"] == 1 and cj["R"] == 0 and cj["joint"] == 1 and cj["joint_split"] == 1 and cj["all"] == 1
                     and d("g1", "2016-12", "OS") == 1 and d("g1", "2016-12", "RS") == 0)
    byk = {(r.acc, r.sk): r for r in B["rows"]}
    o1, a2 = byk.get(("ORIG1", "1")), byk.get(("AMD2", "1"))
    m1, m2, m10 = byk.get(("ML1", "1")), byk.get(("ML1", "2")), byk.get(("ML2", "10"))
    t["amend_ok"] = (F.counts("g1", "2017-03")["O"] == 1 and F.counts("g1", "2017-04")["O"] == 0      # 선언 q — 정정은 새 사건이 아니다
                     and o1.corr == 1 and o1.price == 50.0 and o1.shares == 100.0 and o1.pxc == 51.0 and o1.shc == 100.0
                     and o1.usd == 100 * 50.0 and o1.usdc == 100 * 51.0 and o1.ctgt == ("AMD2", "1")
                     and o1.ym == "2017-03" and a2.corr == 2 and a2.count is False and a2.ctgt == ("ORIG1", "1") and a2.cym == "2017-03"
                     and a2.owners == () and a2.ocor == ((2, "Officer"),) and ("AMD1", "1") not in byk
                     and F.usd["g1"]["2017-03"]["O"] == 100 * 50.0)                                       # 🔒 1차 = 제출된 그대로
    t["amend_multilot_ok"] = (m1.corr == 0 and m1.shares == 100.0 and m2.corr == 1 and m2.shares == 200.0 and m2.shc == 250.0
                              and m2.ctgt == ("ML2", "2") and m10.corr == 2 and m10.ctgt is None and m10.count is False
                              and ("ML2", "1") not in byk and F.counts("g4", "2019-04")["all"] == 2
                              and F.counts("g4", "2019-05")["all"] == 0 and F.usd["g4"]["2019-04"]["all"] == 100 * 60.0 + 200 * 61.0
                              and not any(td == "2019-04-01" and av >= "2019-05" for td, av in H.h.get((41, "g4"), [])))
    # 선언 q2 — 거래일 정정
    dc1, dc2, dc4, dc6b = byk.get(("DC1", "1")), byk.get(("DC2", "1")), byk.get(("DC4", "1")), byk.get(("DC6", "2"))
    h51 = H.h.get((51, "g5"), [])
    t["dcorr_ok"] = (dc2 is not None and dc2.corr == 3 and dc2.count is False and dc2.ocor == ((51, "Officer"),) and dc2.owners == ()
                     and dc2.ctgt == ("DC1", "1") and dc2.cym == "2018-07" and dc1.tdh == ("2018-06-29", "DC2", "1")
                     and dc1.corr == 0 and dc1.count is True and dc1.tdate == "2018-06-28" and dc1.ym == "2018-07"
                     and ("2018-06-29", dc1.avail) in h51 and not any(td == "2018-06-28" for td, _ in h51)
                     and sum(1 for td, _ in h51 if td == "2018-06-29") == 1
                     and F.counts("g5", "2018-07")["all"] == 1 and F.counts("g5", "2018-08")["all"] == 0
                     and dc4.count is True and dc4.corr == 0 and F.counts("g5", "2018-10")["all"] == 1
                     and ("DC6", "1") not in byk and dc6b.count is True and dc6b.corr == 0 and F.counts("g5", "2018-12")["all"] == 1
                     and byk[("DC7", "1")].corr == 1 and byk[("DC7", "1")].pxc == 45.0 and byk[("DC7", "1")].price == 40.0
                     and byk[("DC7", "1")].tdh == ("2020-02-28", "DC9", "1") and byk[("DC9", "1")].corr == 3
                     and byk[("DC9", "1")].count is False and byk[("DC8", "1")].corr == 2 and F.counts("g5", "2020-04")["all"] == 0
                     and byk[("DV1", "1")].corr == 1 and byk[("DV1", "1")].shc == 7500.0 and byk[("DV1", "1")].shares == 221.0
                     and byk[("DV1", "1")].tdh == ("2021-05-10", "DV2", "1") and byk[("DV2", "1")].corr == 3
                     and byk[("DV2", "2")].corr == 2 and byk[("DV2", "1")].count is False and F.counts("g5", "2021-06")["all"] == 0)
    tc1, tc2 = byk.get(("TC1", "1")), byk.get(("TC2", "1"))
    T1f, T1Cf = B["flags"]["T1"], B["flags"]["T1C"]
    t["t1c_ok"] = (tc1.corr == 1 and tc1.usd == 50000.0 and tc1.usdc == 150000.0 and tc1.price == 50.0 and tc1.pxc == 150.0
                   and tc2.corr == 2 and T1f.counts("g5", "2019-07")["usd_x"] == 1 and T1Cf.counts("g5", "2019-07")["usd_x"] == 0
                   and T1Cf.counts("g5", "2019-07")["all"] == 1 and T1f.counts("g5", "2019-07")["all"] == 0
                   and F.usd["g5"]["2019-07"]["all"] == 50000.0 and T1Cf.usd["g5"]["2019-07"]["all"] == 150000.0
                   and T1f.by_year["2019"]["corr_t1_cross"] == 1 and T1Cf.by_year["2019"]["corr_t1_cross"] == 1
                   and VARIANTS["T1C"]["vals"] == "corrected" and "T1C" not in TWINS)
    t["lots_ok"] = F.counts("g1", "2017-05")["O"] == 2
    c7 = F.counts("g1", "2017-07")
    t["stc_row_link_ok"] = c7["O"] == 1 and c7["stc_x"] == 1
    c11 = F.counts("g1", "2017-11")
    t["stc_plan_nd_kept_ok"] = c11["O"] == 1 and c11["stc_x"] == 1        # 선언 p — 계획 각주 행은 남고 원천징수 각주 행만 빠진다
    t["T6_ok"] = (B["flags"]["T6"].counts("g1", "2017-07")["O"] == 2 and B["flags"]["T6"].dummy("g1", "2016-10", "RS") == 1)
    t["T4_ok"] = B["flags"]["T4"].dummy("g1", "2016-07", "OS") == 1 and d("g1", "2016-07", "OS") == 0
    T1 = B["flags"]["T1"]
    c9 = T1.counts("g1", "2017-09")
    t["T1_ok"] = (c9["O"] == 0 and c9["rel_x"] == 1 and c9["usd_x"] == 1 and c9["p10_x"] == 1
                  and T1.dummy("g1", "2017-10", "OS") == 1 and T1.flag("g1", "2017-12", "OS") == 1
                  and T1.flag("g1", "2018-01", "OS") == 0 and T1.flag("g1", "2017-09", "OS") == 0
                  and d("g1", "2017-09", "OS") == 1)
    T2 = B["flags"]["T2"]
    t["T2_ok"] = (T2.dummy("g1", "2023-05", "OS") == 0 and d("g1", "2023-05", "OS") == 1 and T2.dummy("g1", "2022-05", "OS") == 1
                  and T2.dummy("g1", "2022-06", "OS") == 1 and T2.dummy("g1", "2017-09", "OS") == 1 and split_t2("2023-04") == "post")
    T3 = B["flags"]["T3"]
    t["T3_ok"] = (T3 is F and T3.dummy("g1", "2018-02", "MASK") == 1 and T3.dummy("g1", "2018-03", "MASK") == 0
                  and T3.dummy("g1", "2018-03", "ALL") == 1 and B["flags"]["T5"] is F)
    t["N_ok"] = F.counts("g1", "2012-06")["N"] == 1 and d("g1", "2012-06", "OS") is None
    t["split_joint_ok"] = (pst.get("dup_partial_owner") == 1 and F.counts("g1", "2018-05")["all"] == 1
                           and any(td == "2018-05-01" for td, _ in H.h.get((23, "g1"), []))
                           and any(td == "2018-05-01" for td, _ in H.h.get((21, "g1"), [])))
    ex = F.export()
    rd = routine_doc(H, range(2014, 2019))
    t["export_ok"] = (ex["g1"]["2016-12"].get("sO") == 1 and ex["g1"]["2016-12"].get("sR") == 1 and ex["g1"]["2016-12"].get("O") == 1
                      and "R" not in ex["g1"]["2016-12"] and ex["g1"]["2017-05"].get("sO") == 1 and ex["g1"]["2017-05"].get("O") == 2
                      and ex["g1"]["2016-12"].get("O$") == 100000.0 and ex["g1"]["2017-09"].get("p10") == 1
                      and rd["by_year"]["2016"]["R"] == 3 and rd["by_year"]["2016"]["O"] == 3 and rd["by_year"]["2016"]["U"] == 4
                      and rd["by_year"]["2016"]["late_excluded"] == 1)
    cm = cikmonth_doc(B)
    cg = cm["groups"]["g1"]
    cv = lambda m, k: cg.get(m, {}).get(k, 0)                  # 희소 칸 — 키 없음 = 0
    cmd = cikmonth_doc(B, sparse=False)
    t["cikmonth_sparse_ok"] = (cm["sparse"] is True and all(
        {k: v for k, v in rec.items() if v is None or v != 0} == cm["groups"][g][m]
        for g, bym in cmd["groups"].items() for m, rec in bym.items())
        and all(v != 0 or v is None for bym in cm["groups"].values() for rec in bym.values() for v in rec.values()))
    t["cikmonth_ok"] = (cv("2016-12", "os_n") == 1 and cv("2016-12", "rs_n") == 0 and cv("2016-12", "sR") == 1
                        and cv("2017-10", "t1_os_n") == 1 and cv("2017-12", "t1_os3") == 1 and cv("2017-12", "os_n") == 0
                        and cv("2017-07", "t6_os_n") == 2 and cv("2017-07", "os_n") == 1 and cv("2023-05", "t2_os_n") == 0
                        and cv("2012-06", "os_na") == 1 and "2026-07" not in cg and "2026-07" not in cm["months_ok"]
                        and cv("2018-02", "rb_n") == 1)
    t["no_mutation_ok"] = all(r.count is None and r.avail is None for r in R) and len([r for r in R if r.acc == "SPL2"][0].owners) == 2
    # 3b) T4 — 보고자 라벨 U → O 를 JOINT_RULE 앞에(선언 m)
    T4f = B["flags"]["T4"]
    c2p, c2t = F.counts("g1", "2016-02"), T4f.counts("g1", "2016-02")
    t["T4_joint_ok"] = (c2p["R"] == 1 and c2p["O"] == 0 and d("g1", "2016-02", "RS") == 1 and d("g1", "2016-02", "OS") == 0
                        and c2t["O"] == 1 and c2t["R"] == 0 and T4f.dummy("g1", "2016-02", "OS") == 1 and T4f.dummy("g1", "2016-02", "RS") == 0
                        and cv("2016-02", "t4_os_n") == 1 and cv("2016-02", "t4_rs_n") == 0 and cv("2016-02", "rs_n") == 1
                        and cv("2016-02", "t4_os_na") == 0 and cv("2016-07", "t4_os_n") == 1 and cv("2016-07", "os_n") == 0
                        and c2t["u2o_relabel"] == 1 and T4f.counts("g1", "2016-07")["u2o_relabel"] == 0
                        and t4_relabel_report(B)["rows_relabelled"] == 1)
    # 3c) 강제 매도 'non-discretionary' 갈래 겹침(선언 p) · 늦은 공시 · 정정이 두 달에 걸침(선언 l) · T2 경계(선언 n)
    dn = density(B)
    y17 = dn["by_year"]["2017"]
    t["stc_nd_ok"] = (not stc_nd_only("Effected pursuant to a Rule 10b5-1 trading plan; the sale was non-discretionary.")
                      and stc_nd_only("Represents a non-discretionary transaction effected to satisfy tax withholding obligations")
                      and not stc_nd_only("Shares sold to cover taxes upon vesting.") and not stc_nd_only("weighted average")
                      and y17["stc_nd_only"] == 1 and y17["stc_nd_only_p10"] == 0 and y17["stc_nd_unknown"] == 0
                      and y17["stc_v1_only_kept"] == 1 and y17["stc_excluded_v1"] == y17["stc_excluded"] + 1
                      and _mkrow("a", 1, "4", "2017-01-03", 1, "g", "2017-01-02", "S", "D", 1, 1, [(1, "Officer")], None, "", None,
                                 stc=True).stc_nd is None
                      and _mkrow("a", 1, "4", "2017-01-03", 1, "g", "2017-01-02", "S", "D", 1, 1, [(1, "Officer")], None, "", None,
                                 stc=False).stc_nd is False)
    sr = dn["stale"]["all_months_ok"]
    t["stale_ok"] = (F.counts("g3", "2021-06")["stale_O"] == 1 and d("g3", "2021-06", "OS") == 1 and sr["os_cells_only_stale"] == 1
                     and sr["os_cells_with_stale"] == 1 and dn["by_year"]["2021"]["stale_S"] == 1
                     and sum(v.get("stale_S", 0) for v in dn["by_year"].values()) == 1)
    cr = dn["corrections"]
    t["corrections_ok"] = (cr["keys_multi_acc_with_4A"] == 0 and cr["keys_cross_month"] == 0          # 선언 q — 세는 행에는 없다
                           and cr["broad"]["keys_multi_acc_with_4A"] == 5 and cr["broad"]["keys_cross_month"] == 4
                           and cr["corrections_total"].get("corr_rows") == 6 and cr["corrections_total"].get("paired") == 5
                           and cr["corrections_total"].get("unpaired") == 1 and cr["corrections_total"].get("paired_cross_month") == 4
                           and cr["corrections_total"].get("targets_by_orig_year") == 5
                           and cr["corrections_total"].get("dcorr_rows") == 3 and cr["corrections_total"].get("dcorr_paired") == 3
                           and cr["corrections_total"].get("dcorr_targets_by_orig_year") == 3)
    t["t2_boundary_ok"] = dn["by_year"]["2023"].get("S_post_prebox") == 0 and split_t2("2023-03") == "pre"
    # 3d) 캐시 왕복(선언 k) — prepare 결과를 패널 모양 레코드(cnt · 지운 보고자 없음)로 냈다 다시 읽어도 표지가 칸마다 같다.
    #     지운 보고자를 되붙인 형(ins_pit_build.load_panel)도 같다. cnt 칸을 버리면 쪼갠 공동 제출을 두 번 센다(위험의 증거).
    # 핵심 서명(보고자 own 만 읽는 판도 같아야 한다) · 온전한 서명(T1C 금액 · 정정 짝 · 거래일 정정 칸까지 — own + odup + ocor 판)
    strip_c = lambda G: {g: {m: {k: v for k, v in rec.items() if not k.startswith("t1c")} for m, rec in bym.items()} for g, bym in G.items()}
    sigf = lambda BB: (json.dumps({v: BB["flags"][v].export() for v in ("primary", "T1", "T2", "T4", "T6")}, sort_keys=True),
                       json.dumps(strip_c(cikmonth_doc(BB)["groups"]), sort_keys=True), json.dumps(BB["hist"][True].table(range(2014, 2027))))
    sigF = lambda BB: sigf(BB) + (json.dumps(BB["flags"]["T1C"].export(), sort_keys=True),
                                  json.dumps(cikmonth_doc(BB)["groups"], sort_keys=True),
                                  json.dumps(sorted([r.acc, str(r.sk), r.corr, r.shc, r.pxc, list(r.tdh) if r.tdh else None, bool(r.count)]
                                                    for r in BB["rows"])))
    s0, S0 = sigf(B), sigF(B)
    recs = to_records(B["rows"], keep_text=False)
    orig_own = {(r.acc, r.sk): r.owners for r in R}
    recs_od = [dict(x, owners=[[c, rel] for c, rel in orig_own[(x["acc"], x["sk"])]]) for x in recs]
    recs_nc = [{k: v for k, v in x.items() if k != CACHE_FIELDS["count"]} for x in recs]
    # 패널 형(ins_pit_build.load_panel · load_panel_records(with_odup=True)) — 원 보고자 · 정정된 원 행은 처음 값 · 정정 짝(ctgt) 캐시
    orig_v = {(r.acc, r.sk): (r.shares, r.price) for r in R}
    recs_pn = [dict(x, owners=[[c, rel] for c, rel in orig_own[(x["acc"], x["sk"])]],
                    shares=orig_v[(x["acc"], x["sk"])][0], price=orig_v[(x["acc"], x["sk"])][1]) for x in recs]
    recs_pn_nolink = [{k: v for k, v in x.items() if k not in (CACHE_FIELDS["corr"], CACHE_FIELDS["ctgt"])} for x in recs_pn]
    Bc, Bo, Bn, Bp, Bq = (build(rows_from_records(x), cal) for x in (recs, recs_od, recs_nc, recs_pn, recs_pn_nolink))
    t["cache_no_cnt_double_count"] = Bn["flags"]["primary"].counts("g1", "2018-05")["all"]
    t["cache_roundtrip_ok"] = (sigf(Bc) == s0 and sigF(Bo) == S0 and sigF(Bp) == S0 and Bc["prep"].get("cnt0_in") == 10
                               and Bc["prep"].get("cnt0_kept_from_cache") == 1 and Bo["prep"].get("dup_partial_owner") == 1
                               and t["cache_no_cnt_double_count"] == 2 and B["prep"].get("count_false") == 10
                               and Bp["prep"].get("corr_from_cache") == 6 and Bp["prep"].get("corr_targets") == 5
                               and Bp["prep"].get("corr_cache_target_missing", 0) == 0
                               and Bp["prep"].get("dcorr_from_cache") == 3 and Bp["prep"].get("dcorr_targets") == 3
                               and Bp["prep"].get("dcorr_cache_target_missing", 0) == 0)
    # 짝을 캐시에 적는 까닭(선언 q) — 패널에는 4/A 가 같은 값으로 다시 적은 로트(ML2 SK 1)가 지워져 없으므로, 짝을 다시 찾으면
    #   정정 로트(ML2 SK 2)가 확인됐던 원 로트(ML1 SK 1)에 잘못 붙어 값이 바뀐다(250@61) — 짝 없는 새 로트(SK 10)는 ML1 SK 2 를 고친다
    t["corr_link_needed_ok"] = (sigF(Bq) != S0 and [r for r in Bq["rows"] if (r.acc, r.sk) == ("ML1", "1")][0].shc == 250.0
                                and [r for r in Bq["rows"] if (r.acc, r.sk) == ("DC1", "1")][0].tdh == ("2018-06-29", "DC2", "1"))
    # 선언 q2 앞의 규칙(date_corrections=False) — DC2 가 새 사건(2018-08) · 원 행 이력은 원래 거래일
    Bd0 = build(R, cal, date_corrections=False)
    b0 = {(r.acc, r.sk): r for r in Bd0["rows"]}
    t["dcorr_off_ok"] = (b0[("DC2", "1")].count is True and b0[("DC2", "1")].corr == 0 and b0[("DC1", "1")].tdh is None
                         and Bd0["flags"]["primary"].counts("g5", "2018-08")["all"] == 1
                         and any(td == "2018-06-28" for td, _ in Bd0["hist"][True].h.get((51, "g5"), [])))
    # 4) 입력 순서에 매이지 않는다
    R2, _ = _syn()
    rng = np.random.default_rng(QC.SEED)
    R2 = [R2[k] for k in rng.permutation(len(R2))]
    B2 = build(R2, cal)
    t["order_invariant_ok"] = (json.dumps(B2["flags"]["primary"].export(), sort_keys=True) == json.dumps(F.export(), sort_keys=True)
                               and H.table(range(2014, 2019)) == B2["hist"][True].table(range(2014, 2019)))
    tab = H.table(range(2014, 2019))
    t["routine_table_ok"] = tab.get("1|g1", "")[2] == "R" and tab.get("2|g1", "")[2] == "O" and tab.get("4|g1", "")[2] == "U"
    # 5) Stage S
    ranked = ["k%02d" % i for i in range(40)]
    gmap = {k: "G" + k for k in ranked}
    SF = Flags("s", VARIANTS["primary"], [], H, mo)
    for k, m in (("k03", "2016-09"), ("k07", "2016-11"), ("k30", "2016-10"), ("k12", "2016-08")):
        SF.agg["G" + k][m]["O"] = 1
    fpi = {"k05": 1, "k31": 1}
    gmap["k33"] = None                                                         # 그룹 미해결 — 채움에서 건너뛴다
    S = stage_s(ranked, "2016-11", gmap.get, fpi.get, SF)
    S2 = stage_s(ranked, "2016-11", gmap.get, fpi.get, Flags("s2", VARIANTS["primary"], [], H, mo))
    SF.agg["Gk32"]["2016-11"]["O"] = 1
    S3 = stage_s(ranked, "2016-11", gmap.get, fpi.get, SF)
    t["stage_s"] = {k: S[k] for k in ("dropped", "filled", "n_r", "n_fpi_top", "n_fpi_fill", "short")}
    t["stage_s_ok"] = (S["dropped"] == ["k03", "k07"] and S["filled"] == ["k31", "k32"] and len(S["picks"]) == 30
                       and S["n_fpi_top"] == 1 and S["n_fpi_fill"] == 1 and "k12" in S["picks"] and "k30" not in S["picks"]
                       and S2["n_r"] == 0 and S2["picks"] == ranked[:30]
                       and S3["filled"] == ["k31", "k34"] and S3["n_skip_fill"] == 1)
    rng = np.random.default_rng(QC.SEED + 1)
    top = ranked[:30]
    c1 = pick_set(top, {"k01", "k02"}, 3, rng)
    c3 = pick_ordered(top, lambda k: {"k04": 3.0, "k09": 2.0}.get(k), 2)
    pr = pick_random(top, 2, np.random.default_rng(QC.SEED + 7))
    t["controls_ok"] = (len(c1) == 3 and {"k01", "k02"} <= set(c1) and c3 == ["k04", "k09"] and len(set(pr)) == 2
                        and pr == pick_random(top, 2, np.random.default_rng(QC.SEED + 7)) and jaccard(["a", "b"], ["b", "c"]) == 1 / 3)
    # 선언 o — C1 은 OS 활성 이름을 후보에서도 채움에서도 뺀다 · C2 는 매도 없는 이름을 점수 순위에 넣지 않는다
    osa = {"k03", "k04"} | set(top[10:])
    c1x = pick_set(top, {"k01", "k02", "k03"}, 4, np.random.default_rng(QC.SEED + 2), exclude=osa)
    c1y = pick_set(top, {"k01", "k02", "k03"}, 9, np.random.default_rng(QC.SEED + 2), exclude=osa)
    sc2 = {"k04": 3.0, "k09": 0.0, "k10": None, "k12": 1.5}
    p2 = pick_c2(top, sc2.get, 4, np.random.default_rng(QC.SEED + 3))
    p2b = pick_c2(top, sc2.get, 4, np.random.default_rng(QC.SEED + 3))
    p2x = pick_c2(top, sc2.get, 2, np.random.default_rng(QC.SEED + 3), exclude={"k04"})
    t["controls_c1_c2_ok"] = (len(c1x) == 4 and {"k01", "k02"} <= set(c1x) and c1_overlap(c1x, osa) == 0
                              and set(c1y) == {"k00", "k01", "k02", "k05", "k06", "k07", "k08", "k09"} and c1_overlap(c1y, osa) == 0
                              and p2["picks"][:2] == ["k04", "k12"] and p2["n_nosale"] == 2 and len(set(p2["picks"])) == 4
                              and p2 == p2b and p2x["picks"][0] == "k12" and p2x["n_nosale"] == 1 and "k04" not in p2x["picks"])
    t["f0_s_ok"] = f0_stage_s([1, 2, 3, 4]).get("pass") is True and f0_stage_s([0, 1, 1]).get("pass") is False
    mem = {m: {"g1", "g2"} for m in ("2016-05", "2016-06")}
    f0 = f0_stage_m(F, mem, ["2016-05", "2016-06"])
    t["f0_m_ok"] = f0["by_month"]["2016-05"]["rs"] == 1 and f0["by_month"]["2016-06"]["os"] == 1 and f0["pass"] is False
    # 6) 어댑터 — DERA 열 이름 · 날짜 서식 · 각주 행 연결 · 보고자 목록
    T = {"SUBMISSION.tsv": [{"ACCESSION_NUMBER": "X1", "FILING_DATE": "31-AUG-2016", "DOCUMENT_TYPE": "4", "ISSUERCIK": "0000000101",
                             "REMARKS": "", "AFF10B5ONE": ""},
                            {"ACCESSION_NUMBER": "X2", "FILING_DATE": "31-AUG-2016", "DOCUMENT_TYPE": "3", "ISSUERCIK": "101"},
                            {"ACCESSION_NUMBER": "X3", "FILING_DATE": "31-AUG-2016", "DOCUMENT_TYPE": "4", "ISSUERCIK": "999"}],
         "REPORTINGOWNER.tsv": [{"ACCESSION_NUMBER": "X1", "RPTOWNERCIK": "0001188987", "RPTOWNER_RELATIONSHIP": "Officer"},
                                {"ACCESSION_NUMBER": "X1", "RPTOWNERCIK": "0001188988", "RPTOWNER_RELATIONSHIP": "TenPercentOwnerOther"}],
         "NONDERIV_TRANS.tsv": [{"ACCESSION_NUMBER": "X1", "NONDERIV_TRANS_SK": "1", "TRANS_DATE": "29-AUG-2016", "TRANS_CODE": "S",
                                 "TRANS_SHARES": "4801.0", "TRANS_PRICEPERSHARE": "54.56", "TRANS_ACQUIRED_DISP_CD": "D",
                                 "TRANS_SHARES_FN": "F1,F2", "TRANS_PRICEPERSHARE_FN": "F2"},
                                {"ACCESSION_NUMBER": "X1", "NONDERIV_TRANS_SK": "2", "TRANS_DATE": "29-AUG-2016", "TRANS_CODE": "M",
                                 "TRANS_SHARES": "4801.0", "TRANS_ACQUIRED_DISP_CD": "A"},
                                {"ACCESSION_NUMBER": "X3", "NONDERIV_TRANS_SK": "3", "TRANS_DATE": "29-AUG-2016", "TRANS_CODE": "S",
                                 "TRANS_ACQUIRED_DISP_CD": "D"}],
         "FOOTNOTES.tsv": [{"ACCESSION_NUMBER": "X1", "FOOTNOTE_ID": "F1", "FOOTNOTE_TXT": "Shares sold to cover taxes upon vesting."},
                           {"ACCESSION_NUMBER": "X1", "FOOTNOTE_ID": "F2", "FOOTNOTE_TXT": "Weighted average price."}]}
    rows, st = rows_from_dera(T, cik2gid={101: "g1", 100: "g1"})
    r0 = rows[0] if rows else None
    t["dera_adapter_ok"] = (len(rows) == 1 and r0.fdate == "2016-08-31" and r0.tdate == "2016-08-29" and r0.gid == "g1"
                            and r0.stc and abs(r0.usd - 4801 * 54.56) < 1e-6 and len(r0.owners) == 2 and st.get("sub_outside_world") == 1
                            and r0.fn.count("Weighted") == 1)
    recs = [{"acc": "Y1", "sk": 1, "doc": "4", "fdate": "2016-08-31", "issuer_cik": 100, "tdate": "2016-08-29", "code": "S", "ad": "D",
             "shares": 10, "price": 5, "fn_text": "", "remarks": "", "aff": None, "owner_cik": 1, "owner_rel": "Officer"},
            {"acc": "Y1", "sk": 1, "doc": "4", "fdate": "2016-08-31", "issuer_cik": 100, "tdate": "2016-08-29", "code": "S", "ad": "D",
             "shares": 10, "price": 5, "fn_text": "", "remarks": "", "aff": None, "owner_cik": 2, "owner_rel": "Director"}]
    rr = rows_from_records(recs, cik2gid={100: "g1"})
    rr2 = rows_from_records([dict(recs[0], owners=[[1, "Officer"], {"cik": 2, "rel": "Director"}])], cik2gid={100: "g1"})
    t["cache_adapter_ok"] = (len(rr) == 1 and rr[0].owners == ((1, "Officer"), (2, "Director")) and rr[0].gid == "g1"
                             and len(rr2) == 1 and rr2[0].owners == rr[0].owners)
    # 7) 발행사 지도(합성 문서)
    doc = {"tm": {"AAA": [["2016-01", "2016-12", "g1", 101, [101], 0, "dera", 0]], "BBB": [["2016-01", "2016-12", "g2", 200, [200], 1, "dera", 1]],
                  "CCC": [["2016-01", "2016-12", None, None, [], None, "none", None]], "BRK.B": [["2016-01", "2016-12", "g3", 300, [300], None, "dera", None]]},
           "groups": {"g1": {"ciks": [[100, None, "2015-12", "splice", "OLD"], [101, "2016-01", None, "dera_sym", "NEW"]]},
                      "g2": {"ciks": [[200, None, None, "dera_sym", "FPI"]]}, "g3": {"ciks": [[300, None, None, "dera_sym", "BRK"]]}},
           "f0": {"by_month": {"2016-01": [100, 3, 0.03], "2016-02": [100, 1, 0.01]}}}
    im = IssuerMap(doc=doc)
    mm = im.members("2016-06")
    t["issuer_map_ok"] = (im.cik2gid == {100: "g1", 101: "g1", 200: "g2", 300: "g3"} and mm["s16"] == {"AAA": "g1", "BRK.B": "g3"}
                          and mm["fpi"] == ["BBB"] and mm["unresolved"] == ["CCC"] and mm["fpi_null"] == ["BRK.B"]
                          and im.at("BRK-B", "2016-06")["gid"] == "g3" and im.f0_bad == {"2016-01"})
    t["density"] = density(B, members={m: {"g1", "g2"} for m in ("2016-05", "2016-06")}, months=["2016-05", "2016-06"],
                           years=[2016])["classification"]
    t["all_ok"] = all(v for k, v in t.items() if k.endswith("_ok"))
    return t


# ════════════════════════════════════════════════════════════════════════
# 실자료 파싱 대조(수익 없음) · 달력 대조
# ════════════════════════════════════════════════════════════════════════
def dera_check(paths, world=True):
    """DERA 분기 ZIP → 어댑터 개수(비평 실측과 대조할 것: S 든 Form 4 중 공동 제출 · 행 단위 10b5-1 부분 적용 · 강제 매도)."""
    im = IssuerMap() if (world and os.path.exists(IMAP)) else None
    out = {}
    cal = Cal()
    for p in paths:
        rows, st = rows_from_dera(p, cik2gid=im.cik2gid if im else None)
        S = [r for r in rows if r.code == "S" and r.ad == "D"]
        byacc = collections.defaultdict(list)
        for r in S:
            byacc[r.acc].append(r)
        mixed = sum(1 for rs in byacc.values() if len({bool(r.p10_rx) for r in rs}) > 1)
        ok, pst = prepare(rows, cal)
        out[os.path.basename(p)] = {
            "world_filter": bool(im), "ps_rows": len(rows), "s_rows": len(S), "s_filings": len(byacc),
            "s_filings_joint": sum(1 for rs in byacc.values() if len(rs[0].owners) > 1),
            "s_filings_mixed_10b51": mixed, "s_rows_stc": sum(r.stc for r in S), "s_rows_p10_rx": sum(bool(r.p10_rx) for r in S),
            "s_rows_stc_nd_only": sum(1 for r in S if r.stc and r.stc_nd),
            "s_rows_stc_nd_only_p10": sum(1 for r in S if r.stc and r.stc_nd and r.p10_rx),
            "s_rows_box": sum(1 for r in S if r.aff == 1), "adapter": st, "prepare": pst}
    return out


def _zip_rows(zdir, im):
    import glob
    zs = sorted(glob.glob(os.path.join(zdir, "*_form345.zip")))
    rows, ast = [], collections.Counter()
    for p in zs:
        rs, st = rows_from_dera(p, cik2gid=im.cik2gid, keep_text=False)
        rows.extend(rs)
        ast.update(st)
    qs = [os.path.basename(p)[:6] for p in zs]
    start = "%s-%02d-01" % (qs[0][:4], 3 * int(qs[0][5]) - 2)
    qe = qs[-1]
    end = (dt.date(int(qe[:4]) + (qe[5] == "4"), (3 * int(qe[5])) % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()
    return rows, dict(ast), qs, start, end


def density_dera(zdir, window=("2016-06", "2026-07"), src="zips"):
    """DERA 분기 ZIP 전부(src="zips") 또는 §A 패널(src="panel") + 발행사 지도 → 밀도 · F0(수익 없음 · 아무것도 쓰지 않는다).
    세계 = 지도의 멤버-월 가운데 그룹이 풀렸고 fpi != 1 · pit_gics_sectors 의 그달 Financials(SPX 표) 제외 · 지도 F0 나쁜 달 제외."""
    import time
    t0 = time.time()
    im = IssuerMap()
    if src == "panel":
        rows = rows_from_records(load_panel_records())
        ast, qs, start, end = {"panel_rows": len(rows)}, ["panel", "panel"], DATA_START, DATA_END
        zs = []
    else:
        rows, ast, qs, start, end = _zip_rows(zdir, im)
        zs = qs
    t1 = time.time()
    cal = Cal()
    B = build(rows, cal, start=start, end=end)
    t2 = time.time()
    G = json.load(io.open(os.path.join(DATA, "pit_gics_sectors.json"), encoding="utf-8"))["months"]
    fin = {m: set((v.get("sec") or {}).get("Financials") or []) for m, v in G.items()}
    months = [m for m in QC.months_between(*window) if m in B["months_ok"] and m not in im.f0_bad]
    members, excl = {}, collections.Counter()
    for m in months:
        mm = im.members(m)
        ks = [k for k in fin if k <= m]
        f = fin.get(m) or (fin[max(ks)] if ks else set())
        members[m] = {g for t, g in mm["s16"].items() if t not in f}
        excl["fpi"] += len(mm["fpi"])
        excl["unresolved"] += len(mm["unresolved"])
        excl["fpi_null_kept"] += len(mm["fpi_null"])
    out = density(B, members, months, years=range(hist_y0(start) + 3, int(end[:4]) + 1))
    out["window"] = list(window)
    out["window_months_uncovered"] = [m for m in QC.months_between(*window) if m not in B["months_ok"]]
    out["window_months_bad_map_f0"] = [m for m in QC.months_between(*window) if m in im.f0_bad]
    out["data"] = {"src": src, "zips": len(zs), "first": qs[0], "last": qs[-1], "filing_window": [start, end], "adapter": dict(ast),
                   "member_month_excl": dict(excl), "sec": [round(t1 - t0, 1), round(t2 - t1, 1), round(time.time() - t2, 1)]}
    tw = {}
    for v in ("T1", "T2", "T4", "T6"):
        f = f0_stage_m(B["flags"][v], members, months)
        tw[v] = {"os_median": f["os_median"], "os_min": f["os_min"], "rs_median": f["rs_median"]}
    out["twins_density"] = tw
    out["t4_vs_primary_OplusU"] = t4_relabel_report(B, members, months)
    return out


def t4_relabel_report(B, members=None, months=None):
    """선언 m — T4(보고자 U → O 뒤 JOINT_RULE) 대 1차 O + U 로 다시 만든 T4 가 갈리는 행 · 칸 수(엔진이 옛 방식으로 읽으면 생기는 차이)."""
    P, T4 = B["flags"]["primary"], B["flags"]["T4"]
    rows_diff = sum(1 for g, bym in T4.agg.items() for m, c in bym.items() if c["O"] != P.counts(g, m)["O"] + P.counts(g, m)["U"])
    def cells(gm):
        d_os = d_rs = 0
        for g, m in gm:
            a = T4.dummy(g, m, "OS")
            c = P.counts(g, m)
            b = None if m not in P.months_ok else (1 if (c["O"] + c["U"]) > 0 else (None if c["N"] > 0 else 0))
            d_os += a != b
            d_rs += T4.dummy(g, m, "RS") != P.dummy(g, m, "RS")
        return {"os_cells_diff": d_os, "rs_cells_diff": d_rs}
    out = {"cells_O_count_diff": rows_diff, "rows_relabelled": sum(c["u2o_relabel"] for bym in T4.agg.values() for c in bym.values()),
           "all_months_ok": cells([(g, m) for g, bym in T4.agg.items() for m in bym if m in T4.months_ok])}
    if members is not None and months:
        out["f0_window_members"] = cells([(g, m) for m in months for g in (members.get(m) or ())])
    return out


def panel_check(zdir):
    """ZIP 경로 대 §A 패널 경로(odup 되붙임 · 안 붙임) — 모든 판의 export · cikmonth_doc 가 같은가(선언 k 의 실자료 대조 · 수익 없음)."""
    import time
    t0 = time.time()
    im = IssuerMap()
    cal = Cal()
    rows, _, _, start, end = _zip_rows(zdir, im)
    Bz = build(rows, cal, start=start, end=end)
    del rows
    sig = lambda B: {**{v: json.dumps(B["flags"][v].export(), sort_keys=True) for v in ("primary", "T1", "T2", "T4", "T6")},
                     "cikmonth": json.dumps(cikmonth_doc(B)["groups"], sort_keys=True),
                     "routine": json.dumps(B["hist"][True].table(range(2014, 2027)), sort_keys=True)}
    sz = sig(Bz)
    kz = {(r.acc, r.sk): bool(r.count) for r in Bz["rows"]}
    # 선언 q — 보고자가 정정 보고자뿐인 정정 행(corr = 2 · 새 보고자 없음)은 own 만 읽는 판(panel_no_odup)에서 보고자가 없어 빠진다
    #   (세지 않는 행이고 이력에도 붙지 않으니 표지는 같다) — 그 판의 행 대조에서만 뺀다.
    kz_corr_noown = {(r.acc, r.sk) for r in Bz["rows"] if r.corr == 2 and not r.owners}
    del Bz
    out = {"zip_filing_window": [start, end]}
    for wo in (True, False):
        Bp = build(rows_from_records(load_panel_records(with_odup=wo)), cal, start=start, end=end)
        sp = sig(Bp)
        kp = {(r.acc, r.sk): bool(r.count) for r in Bp["rows"]}
        oz = set(kz) - set(kp) - (set() if wo else kz_corr_noown)
        out["panel_odup" if wo else "panel_no_odup"] = {
            "same": {k: sz[k] == sp[k] for k in sz}, "prep": Bp["prep"], "rows": len(kp),
            "rows_only_zip": len(oz), "rows_only_panel": len(set(kp) - set(kz)),
            "corr_rows_without_own_skipped": 0 if wo else len(kz_corr_noown & (set(kz) - set(kp))),
            "count_flag_diff": sum(1 for k in kz if k in kp and kz[k] != kp[k])}
        del Bp
    out["sec"] = round(time.time() - t0, 1)
    out["all_same"] = all(all(v["same"].values()) and v["count_flag_diff"] == 0 and not v["rows_only_zip"] and not v["rows_only_panel"]
                          for k, v in out.items() if k.startswith("panel_"))
    return out


def calcheck():
    p = os.path.join(DATA, "stocks.json")
    G = json.load(io.open(p, encoding="utf-8"))["pxd_dates"]
    cal = Cal()
    lo, hi = G[0], G[-1]
    rule = [d for d in cal.days if lo <= d <= hi]
    gs = set(G)
    return {"grid": [lo, hi, len(G)], "rule_only": [d for d in rule if d not in gs][:20],
            "grid_only": [d for d in G if d not in cal._set][:20]}


def main(argv):
    if "--selftest" in argv:
        t = selftest()
        print(json.dumps(t, ensure_ascii=False, indent=1, default=str))
        return 0 if t["all_ok"] else 1
    if "--dera-check" in argv:
        ps = [a for a in argv[argv.index("--dera-check") + 1:] if not a.startswith("--")]
        print(json.dumps(dera_check(ps, world="--all-issuers" not in argv), ensure_ascii=False, indent=1))
        return 0
    if "--density" in argv or "--density-panel" in argv:
        if "--density-panel" in argv:
            res = density_dera(None, src="panel")
        else:
            res = density_dera(argv[argv.index("--density") + 1])
        if "--brief" in argv:
            res["f0_stage_m"].pop("by_month", None)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0
    if "--panel-check" in argv:
        res = panel_check(argv[argv.index("--panel-check") + 1])
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0 if res["all_same"] else 1
    if "--calcheck" in argv:
        print(json.dumps(calcheck(), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
