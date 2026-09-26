# -*- coding: utf-8 -*-
"""build/r_stages.py — 배치 R(RBATCH) Stage S · «EG30 + 빼기 단계» 구성 한 벌 → qbatch_core 호환 CardResult.

카드 원문: scratchpad/rbatch_research.json «final» — slate R1-OPPSELL · R2-LAZYRF · R5-ALARM 의 [Stage S] · controls · params(F0) ·
  forward_plan(«R1·R2 EG30 단계 팔» · FF2 (b)(g)) · batch_design_changes 6(쌓기 · 단계 모양 = Stage M 더미를 그대로 옮긴 빼기-채우기).

무엇을·왜.
  두 기전(R1 기회주의 내부자 매도 · R2 10-Q 위험요인 대규모 개정)은 «종목 고유 악재로 이름을 빼는» 일을 한다. 롱온리 펀드는 공매도 대신
  EG30 후보에서 뺀다. 교체 방식은 Stage M 더미를 그대로 옮긴 것이라 새 강도 모수가 없다 — 배치 Q 의 «상위 40 · 최대 10 · 강도순» 모양은
  쓰지 않는다(오염된 모양 · 새 모수). 표본 안 Stage S 는 **측정만**이고 판정은 전방(FF1 · FF2)이다.
  같은 빼기-채우기를 카드마다 따로 짜면 반드시 갈린다(이 저장소가 되풀이 밟은 결함) — 그래서 한 엔진(replace_top · stage_s)에 표지만 바꿔 끼운다.

규칙(카드 그대로 — 문턱·창을 여기서 바꾸지 않는다).
  R1-OPPSELL  분기 편입일 r 마다 Eg 상위 30 가운데 «OS 활성»(가용월 r−2..r 에 기회주의 매도 ≥ 1) 이름을 빼고, OS 비활성 Eg 차순위로 채워
              30 종을 만든다. 비중은 V0 규칙(시총가중 · 20% 상한) · 편입 사이에는 바꾸지 않는다. FPI(Section 16 비적용)는 걸러낼 수 없으니
              그대로 두고 편입마다 몇 종인지 싣는다.
  R2-LAZYRF   같은 설계 — «CH 활성»(공개월 r−2..r 의 10-Q 가 전년도 하위 20%) 이름을 뺀다. 3월 편입은 10-Q 공개가 적어 교체가 거의 없다(카드 선언).
  R12-STACK   쌓은 팔 V0 + R1 + R2 — OS 활성 ∪ CH 활성을 빼고 둘 다 비활성인 차순위로 채운다(측정 · forward_plan «쌓은 팔»).
  R5-ALARM    매월 말 EG30 명단에서 경보 이름을 뺀다 — (a) 직전 12개월 NT 10-K/Q · 4.02 · 4.01 사임 · 3.01 · (b) 직전 90일 1.03/2.04/2.05/2.06/5.01
              (사건 판정은 r_r2flags 정본). 표본 안은 **걸린 이름-월 수와 업종 분포만** 센다 — 카드: 수익을 계산하지 않으므로 시도 수에 더하지 않는다.
              팔 목표(매월)는 전방 원장(«V0 + R5» 측정 팔)용으로 짓기만 하고 해시를 싣는다.
  대조        편입마다 규칙의 교체 수 n_r 를 맞춘다(카드 controls).
              R1: C1 루틴 매도(RS 활성) n_r · 모자라면 무작위 채움 / C2 분류 없는 전체 매도 $/시총 상위 n_r / C3 12-1 모멘텀 상위 n_r / C4 FP 베타 상위 n_r.
              R2: C2 SimDoc 하위 n_r / C3 / C4 / C5 Δlog(1A 단어수) 상위 n_r (카드의 C1 = 아래 위약).
  위약        무작위 n_r 교체 1000회 — 뽑기 i 는 default_rng(SEED + i) 한 줄기로 편입 순서대로(랩 위약 규약 · q_ltd.placebo_targets 와 같다).
  F0(Stage S) 편입당 교체 수 중앙값 2~15. 벗어나면 측정 불가 — 그 카드의 수익은 계산하지 않는다.

선언된 선택(카드 문구가 정하지 않은 곳 — 여기 한 번 고정한다. 등록 문서에 그대로 옮긴다).
  ① V0 규칙 = qg_lab.World.weights(EG_BASE) 그대로 — 시총가중 · 20% 상한(eg30plus.cap_weights 와 같은 반복 · 같은 합 순서라 비트까지 같다).
     카드 문구의 «금융은 지수 비중» 은 V0 에 없는 규칙(eg30plus S1 의 규칙)이다. EG_BASE 의 Eg(pitgics)는 금융에 값이 없어 V0 에 금융이
     한 번도 들지 않는다(snap_wt 실측 0/1230 이름-편입) — 적용하지 않는다. 표지가 모두 0 이면 목표 해시가 ctx.V0_targets 와 같다(--construct 단언).
  ② 이름의 편입일 상태(r_r1_flags 선언 j 와 같다): fpi(걸러낼 수 없음) · unres(그룹 미해결) · unk(표지 None) · on · off.
     상위 30 안의 fpi · unres · unk 는 그대로 둔다. 채움은 off 와 fpi 만(비활성이 확인된 이름) — unk · unres · on 은 건너뛰고 센다.
     그룹은 편입월 r 의 지도 그룹 하나로 창(r−2..r) 전체를 본다 — 티커가 다른 회사로 넘어간 경우 앞 회사의 표지가 옮겨 오지 않는다.
  ③ R2 결측(분리 실패 · 짝 없음 · 형태 전환 → CH = 0 + 결측 더미)은 Stage S 에서 off 다(CH 활성이 아니다). 상위 30 안의 결측 수는 따로 센다.
  ④ 쌓은 팔 = 한 번의 합집합 교체(표지 하나라도 on → 뺌 · 채움은 두 표지 모두 off/fpi). 순차(R1 뒤 R2)와는 «R1 채움 이름이 R2 unk» 인
     가장자리에서만 갈린다. 두 카드가 모두 F0 를 넘을 때만 잰다(자기 F0 는 없다 · 교체 수는 보고만).
  ⑤ 대조·위약의 모집단 = 규칙이 뺄 수 있었던 이름(상위 30 가운데 상태가 on · off). FPI · 미해결 · 모름 이름은 규칙이 빼지 못하니 대조도 빼지 않는다
     (q_ltd 검토 수정과 같은 뜻 — 규칙과 위약이 같은 구조를 갖고 고르기만 다르다). 채움 = 뺀 이름 밖 Eg 차순위(규칙의 비활성 거르기 없이).
     그래서 대조는 31위 밖의 OS·CH 활성 이름을 다시 들일 수 있고, 규칙이 짧으면(short > 0) 대조가 규칙보다 이름이 많다 — 등록 문서에 선언된 비대칭으로 적는다.
  ⑥ C1 — r_r1_flags.pick_set(선언 o) 그대로: 편입일의 규칙 활성(on · R1 이면 OS 활성) 이름은 후보에서도 채움에서도 뺀다(exclude) — 겹치면 C1 이
     규칙과 같은 이름을 빼서 «분류가 일하는지» 대조가 흐려진다. RS 활성(∖ OS 활성)이 n_r 보다 많으면 그 가운데 무작위 n_r · 모자라면 모집단의
     나머지 off 이름에서 무작위로 채운다 · 그래도 모자라면 n_r 보다 적게(편입마다 c1_short 로 센다 · 겹침 c1_overlap 은 늘 0 이어야 한다).
     씨앗 C1_SEED = SEED − 1 한 줄기(위약 SEED + 0..999 와 겹치지 않는다).
  ⑦ 순서 대조(C3~C5) — 점수 없는 이름은 뒤 · 동점은 Eg 순서. C2(R1) 는 r_r1_flags.pick_c2(선언 o) 그대로 — 점수 = Σ_{r−2..r} 재량 매도 $
     (분류 없음 · 강제 매도 뺀 cikmonth usd_all) ÷ 편입일 시총(창은 OS 활성과 같다) · 점수 > 0 인 이름만 점수 순(동점 Eg 순서) · 모자라면 나머지
     (매도 없음 · 점수 없음)에서 씨앗 C2_SEED = SEED − 2 한 줄기로 무작위 채움(편입마다 n_nosale) — 매도 없는 이름을 Eg 순서로 고르면 늘 최상위
     Eg 이름을 뺀다. exclude 는 없다(C2 는 «분류 없는 전체 매도» 라 OS 활성과 겹치는 것이 뜻이다 · r_r1_flags 기본값).
     C2(R2) = 창 안 마지막 유효 짝의 SimDoc(낮을수록 먼저) · C5 = 같은 짝의 Δlog(1A 단어수)(클수록 먼저).
  ⑧ 12-1 모멘텀 = qg_lab.World.raw("mom")(252일 수익 − 21일 수익 · 랩 x-mom12 규약) · FP 베타 = eg30plus.World.fp_beta(편입일).
  ⑨ R5 매월: 분기 편입은 R1 과 같은 빼기-채우기. 편입 사이 달은 그달 경보 이름만 판다 — 남은 이름은 흘러간 비중 그대로(거래 없음),
     빈 몫은 그달 Eg 순위의 비경보 차순위(보유 밖)에 시총 비례 · 20% 상한(넘친 몫은 남은 이름에 비례)으로. 경보가 없는 달은 흘러간 비중
     그대로(매매 없음). stock_path reb=1 규약상 달 중간에 가격이 끊긴 이름은 그달 말 현금이 된다(V0 는 다음 편입까지 마지막 가격) — 전방 원장의 한계.
  ⑩ 위약 통계 = Δβ(뽑기 − V0)의 전 월 평균과 하락월 평균(qbatch_run.dbeta — 전방 FF2 (b) 의 표본 안 짝). 둘 다 싣고 판정에 쓰지 않는다.
  ⑪ 형성일 = 세계 격자의 그달 마지막 거래일(Wd.me) — 월 더미는 그달 말까지 가용한 사건이다. --construct 가 형성일 = NYSE 규칙 달력의
     그달 마지막 거래일인지 편입마다 확인한다(격자 구멍이면 하루 선견). R5 경보는 형성일(세계 격자) 기준으로 건다.
  ⑫ R2 경계 분포의 세계는 Stage M 과 같은 것을 넘겨야 한다(load_bundle(r2_world=…)) — 안 주면 §C 자료 전체(r_r2flags 랩 선택 ⑦).
  ⑬ 정의된 달(months_ok — 밖의 달은 None · 조용히 0 으로 읽지 않는다). OS·RS = cikmonth 의 months_ok. CH·CH_MISS = r_p0_adapt 와 같게
     _tenq_rf.json 최상위 months_ok(목록)가 있으면 그것 · 없으면 window_defined(문서 공개월) = [첫 공개월 + 2, 끝 공개월].
     ALARM = _sub_pit 최상위 months_ok 가 있으면 그것 · 없으면 [첫 제출월 + 11(12개월 창 a), 끝 제출월](전 기록의 filingDate 범위).
  ⑭ F0(Stage S) 의 중앙값은 «잴 수 있는 편입» 만으로 — 카드 표지마다 창(r−w+1..r)의 모든 달이 정의되고, 지도 F0(편입월 위반율 ≤ 2% ·
     r_stagem.IssuerMap.month_ok · 지도에 f0 표가 없으면 걸지 않는다)와 §F 커버리지 F0(data/_r_coverage.json 이 있으면 · r_p0_adapt.coverage_months)
     를 넘은 편입. 뺀 편입과 이유를 싣는다. 구성(목표)은 그대로 — 정의되지 않은 달의 이름은 unk 라 남는다(선언 ②).
  ⑮ 덮어쓰기 data/_r_flags.json 은 **옵트인**(load_bundle(allow_override=True) · --allow-override) — r_p0 와 같다(정식 빌더를 가린다 ·
     Stage M · r_run 은 읽지 않는다). 기본은 파일이 있어도 쓰지 않고 src 에 «있지만 쓰지 않음» 을 적는다. 쓸 때 months_ok 는
     r_p0_adapt._override_defined 와 같은 세 모양(최상위 목록 · {카드: 목록} · {카드: {더미: 목록}}) · 없으면 None 을 src 에 경고로 싣는다.
     덮어쓰기가 CH 를 줘도 SimDoc · Δlog(대조 C2 · C5)는 정본 10-Q 에서 짓는다(정본이 없으면 그 대조는 «없음» · 실제 굽기는 멈춘다).
  ⑯ 자료 지문(src 의 sha256) — 글 파일은 CRLF → LF 로 맞춘 바이트(r_run._sha_lf) · .gz 는 푼 바이트(r_run._sha_file(gz=True)) · 규칙은 sha_rule.
  ⑰ Q07 제외 명단(R1·R2 자카드 · 카드 «등록 전») = q_ltd 얼린 적합(strict · 다시 적합하지 않는다)으로 지은 V1 목표에서 P(Eg 상위 45) 가운데
     빠진 15 종 · V1 목표 해시가 등록 핀(c1ff6f6f017e… · qfwd_adapter PIN)과 다르면 멈춘다(q07_lists · --construct 가 실제 표지가 있거나 --q07 일 때).

CardResult 모양(qbatch_run 의 store 가 읽는 키 그대로 — rbatch 러너가 같은 lite 로 싣는다).
  {"code", "cls": "M"(측정만), "fr"(TR · 10bp), "fr_pr"(PR), "fr20"(TR · 20bp), "controls": {"V0", "V0_20", "C1".."C5"}, "arms": {},
   "placebo": {"random": {"draws", "draws_down", "true", "true_down", "p95", "p95_down", "stat", …}}, "perm": None, "g4": {}(표본 안 관문 없음),
   "label_caps": {}, "f0", "targets_hash"(q_ltd.thash 와 같은 식), "log": {편입 기록 · 대조 명단 · 자카드 · 위약 씨앗 · measured}}
  R5 는 "cls": "count" — fr 없음(러너는 부류 D 처럼 싣는다).

🚨 방화벽 — 등록 전에는 실제 표지와 실제 미래 수익의 관계를 계산하지 않는다(data_build_plan 원칙 · 등록 뒤 한 번 굽기).
  · run() 은 실제 표지(kind "real")를 받으면 RBATCH_COMMIT(등록 커밋) 없이는 멈춘다 — 러너(§E rbatch_run)가 frozen_check 뒤 한 번 부른다.
  · --construct 는 구성만(목표 · 개수 · 해시 · 자카드 · 달력) — 수익 통계 없음. 실제 표지가 있으면 F0(교체 수)와 C3 자카드를 잰다
    (카드: 등록 전 · 수익 없음). V0 재현 대조만 V0 자신의 경로를 쓴다(표지 없음 · qbatch_core.Ctx 의 예외 조항).
  · --construct 의 연기 시험은 합성 표지로 run() 을 qbatch_core.blind_smoke 에 넣는다 — 예외 · 모양 · 시간만 보고 값은 버린다.
  · --selftest 는 합성 세계 · 합성 가격 · 합성 표지만.

어댑터 — 아직 빌드 중인 자료(data/_issuer_map.json · data/_ins_pit/cikmonth.json · data/_tenq_rf.json · data/_sub_pit.json.gz)의 경로 ·
  필드 이름은 FIELDS 한 곳에만 둔다. 10-Q · submissions 레코드 필드는 정본 빌더 r_r2flags(F_TENQ · F_SUB)가 읽는다 — 여기서 다시 적지 않는다.
  공급 순서(표지마다): ① (allow_override 일 때만 · 선언 ⑮) 덮어쓰기 data/_r_flags.json({"cards": {카드: {더미: {월: [그룹]}}}, "months_ok": …}
  · r_p0_adapt 와 같은 파일 · 같은 months_ok 모양) ② 정본(cikmonth · r_r2flags.r2_build · r_r2flags.r5_events)
  ③ 없으면 None — 부르는 쪽이 «자료 없음» 으로 싣는다(조용히 0 을 채우지 않는다).
  자료가 있는 곳 = RBATCH_DATA(없으면 이 파일 옆 data/ · r_stagem 과 같은 변수).

재사용(복제하지 않는다): qbatch_core(stock_path · fund_from_path · Ctx · Grid · blind_smoke · mshift · SEED) · eg30plus(EG_BASE · formations ·
  cap_weights · nw_t · down_t · v0_targets · World.fp_beta · World.sector) · qg_lab(World.score · raw("mom") · sleeve) · qbatch_run(dbeta ·
  sleeve_beta · both_side · lite) · r_r2flags(10-Q · submissions 정본 표지 · NYSE 규칙 달력) · 시총은 pit_panel._shares 경로(World.mcap).

  python build/r_stages.py --selftest                     # 합성 세계 · 합성 표지(실제 자료 없음 · 저장소 작업 트리에서 된다)
  cd $TEMP/snap_wt && RBATCH_DATA=<지도가 있는 data 경로> python -X utf8 build/r_stages.py --construct [--out 경로] [--nperm-smoke 3]
      [--allow-override](덮어쓰기 파일을 표지 출처로 · 선언 ⑮) [--q07](실제 표지가 없어도 Q07 제외 명단을 짓고 핀을 맞춘다 · 선언 ⑰)
  종료 코드(--construct): V0 재현 · 합성 위반 · 점 시점 · 연기 시험 · 실제 자료 적재(파일이 있는데 읽다 멈춤) · 실제 표지 구성 위반 ·
      Q07 핀 가운데 하나라도 어긋나면 1(«자료 없음» 은 실패가 아니다).
  (저장소 작업 트리는 가격 격자가 어긋나 pit_panel.load_world 가 멈춘다 — 자료 판 작업 사본 snap_wt 로 이 파일을 복사해서 돌린다)
"""
from __future__ import annotations
import datetime as dt, hashlib, io, json, os, sys, time, warnings

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402  mshift · months_between · SEED · Ctx · stock_path · blind_smoke

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RDATA = os.environ.get("RBATCH_DATA") or DATA   # 배치 R 자료(지도 · 내부자 · 10-Q · submissions)가 있는 곳
_RB = os.path.join(os.path.dirname(os.path.abspath(RDATA)), "build")
if os.path.isdir(_RB) and os.path.abspath(_RB) != HERE and _RB not in sys.path:
    sys.path.append(_RB)   # 형제 정본(r_r1_flags · r_r2flags)을 snap_wt 에서도 찾게 — 랩 핵심 모듈은 이 파일 옆 것이 먼저다(맨 뒤에 붙인다)

# ════════════════════════════════════════════════════════════════════════
# 고정값(카드 params — 여기 말고 다른 문턱·창은 시험하지 않는다)
# ════════════════════════════════════════════════════════════════════════
N_TOP = 30                              # EG30
CAP = 0.20                              # V0 발행사 상한
COST20 = 0.0020                         # 20bp 행
NPERM = 1000                            # 위약 뽑기 수(카드) — 연기 시험에서만 작게 넘긴다
SEED = Q.SEED                           # 20260925 · 뽑기 i = default_rng(SEED + i)(랩 위약 규약) — 등록 커밋에서 고정
C1_SEED = SEED - 1                      # C1 무작위 한 줄기(선언 ⑥)
C2_SEED = SEED - 2                      # R1 C2 매도 없음 채움 한 줄기(선언 ⑦)
F0_NR = (2, 15)                         # Stage S F0 — 편입당 교체 수 중앙값
IM_VIOL = 0.02                          # 지도 F0 — 그달 위반율 상한(r_stagem.IM_VIOL · 선언 ⑭)
R5_A_MONTHS = 12                        # R5 창 (a) 12개월(r_r2flags.R5_A_MONTHS · ALARM 정의 달 · 선언 ⑬)
Q07_V1_PIN = "c1ff6f6f017e4ecb2936005ce0a160f95daa5ea23d8fe14d2c7a0aa648f658f8"   # qfwd_adapter PIN["Q07_V1"](선언 ⑰)
WINDOW = {"OS": 3, "RS": 3, "CH": 1, "CH_MISS": 1, "ALARM": 1}   # 표지 창(달) — OS·RS 는 가용월 r−2..r · CH·ALARM 은 빌더가 이미 창을 걸었다
FILL_OK = ("off", "fpi")                # 채움에 들 수 있는 상태(선언 ②)
DROPPABLE = ("on", "off")               # 대조·위약의 모집단(선언 ⑤)

CARDS = {
    "R1-OPPSELL": {"flags": ("OS",), "freq": "Q", "placebo": True, "returns": True,
                   "controls": {"C1": ("set", "RS"), "C2": ("pos", "sell_usd_mcap"), "C3": ("hi", "mom"), "C4": ("hi", "beta")}},
    "R2-LAZYRF": {"flags": ("CH",), "freq": "Q", "placebo": True, "returns": True,
                  "controls": {"C2": ("lo", "simdoc"), "C3": ("hi", "mom"), "C4": ("hi", "beta"), "C5": ("hi", "dlog")}},
    "R12-STACK": {"flags": ("OS", "CH"), "freq": "Q", "placebo": False, "returns": True, "controls": {}},
    "R5-ALARM": {"flags": ("ALARM",), "freq": "M", "placebo": False, "returns": False, "controls": {}},
}
QCARDS = ("R1-OPPSELL", "R2-LAZYRF", "R12-STACK")

# ════════════════════════════════════════════════════════════════════════
# FIELDS — 새 자료의 경로·필드 이름. 스키마가 확정되면 **여기만** 고친다(값이 튜플이면 앞 후보부터 찾는다).
# ════════════════════════════════════════════════════════════════════════
FIELDS = {
    # §A0 — tm[티커] = [[첫 달, 끝 달, 그룹, 주 CIK, [CIK 집합], fpi, 출처, fpi_q]] (build/issuer_map.py tm_format · 2026-09-25 판)
    #   지도 F0 = f0.by_month[달] = [확인 수, 위반 수, 위반율](r_stagem.FIELDS["issuer_map"] f0 · f0_rate) · f0.bad_months(r_p0_adapt.month_gate)
    #   🔒 fpi 칸은 박지 않는다 — 지도의 fpi_registered.tm_index(2026-09-25 권고 fpi_q = 7) · 없으면 5(사양 칸 · 옛 판)
    "issuer_map": {"file": "_issuer_map.json", "tm": "tm", "row": {"first": 0, "last": 1, "gid": 2, "fpi": 5},
                   "fpi_registered": "fpi_registered",
                   "f0": ("f0", "by_month"), "f0_rate": 2, "bad_months": ("f0", "bad_months")},
    # 덮어쓰기(옵트인 · r_p0_adapt.FIELDS["flags_override"] 와 같은 파일) — {"cards": {카드: {더미: {월: [그룹]}}},
    #   "months_ok": 목록 | {카드: 목록} | {카드: {더미: 목록}}}(r_p0_adapt._override_defined 와 같은 세 모양)
    "override": {"file": "_r_flags.json", "cards": "cards", "months_ok": "months_ok",
                 "map": {"OS": ("R1-OPPSELL", "OS"), "RS": ("R1-OPPSELL", "RS"), "CH": ("R2-LAZYRF", "CH"),
                         "CH_MISS": ("R2-LAZYRF", "CH_MISS"), "ALARM": ("R5-ALARM", "ALARM")}},
    # §A (b) 그룹 × 가용월 집계(정본 r_r1_flags.cikmonth_doc) — {"months_ok": [...], "groups": {그룹: {달: {…}}}} · 표에 없는 칸 = 0
    "ins": {"file": os.path.join("_ins_pit", "cikmonth.json"), "root": ("groups", "gm", "cikmonth"), "months_ok": "months_ok",
            "os": ("O", "os_n", "n_os"), "rs": ("R", "rs_n", "n_rs"), "na": ("N", "na_n", "n_na"),
            "os_na": ("os_na",), "rs_na": ("rs_na",), "usd": ("usd_all", "all$")},
    # §C 10-Q 문서 — 레코드 필드는 r_r2flags.F_TENQ 가 읽는다 · gm 행(r_r2flags.ch_active) 필드는 아래
    "tenq": {"file": "_tenq_rf.json", "months_ok": "months_ok", "pub_m": "pub_m"},
    "r2_gm": {"ch": "ch", "miss": "miss", "sim": "sim", "dlog": "dlog_raw"},
    # §B submissions(R5) — 레코드 필드는 r_r2flags.F_SUB(정의 달은 adapt_sub 의 fd) · 4.01 본문은 r_r2flags.load_t401
    "sub": {"file": "_sub_pit.json.gz", "t401": "_t401.json", "months_ok": "months_ok", "fd": "fd"},
    # §F 커버리지 F0(r_p0_adapt.FIELDS["coverage"] 와 같은 파일 · 읽기는 r_p0_adapt.coverage_months)
    "coverage": {"file": "_r_coverage.json"},
}


def _pick(rec, names):
    for n in names:
        if isinstance(rec, dict) and n in rec:
            return rec[n]
    return None


def _read(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        b = fh.read()
    if b[:2] == b"\x1f\x8b":
        import gzip
        b = gzip.decompress(b)
    return json.loads(b.decode("utf-8"))


SHA_RULE = "글 파일: CRLF→LF 로 맞춘 바이트의 sha256(r_run._sha_lf) · .gz: 푼 바이트의 sha256(r_run._sha_file(gz=True))"


def _sha_file(path):
    """자료 지문(선언 ⑯) — .gz(이름 또는 gzip 머리)는 푼 바이트 그대로 · 글 파일만 CRLF → LF. gzip 흐름 안의 0x0D0A 를 건드리지 않는다."""
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        b = fh.read()
    if path.endswith(".gz") or b[:2] == b"\x1f\x8b":
        import gzip
        return hashlib.sha256(gzip.decompress(b)).hexdigest()
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _p0a():
    """형제 r_p0_adapt(덮어쓰기 months_ok · window_defined · coverage_months 정본) — 없으면 None(아래 같은 뜻의 사본을 쓴다 · 시험이 대조)."""
    try:
        import r_p0_adapt as P0A
        return P0A
    except Exception:
        return None


def _override_defined_local(ov, card, dummy):
    """r_p0_adapt._override_defined 와 같은 뜻(세 모양 — 최상위 목록 · {카드: 목록} · {카드: {더미: 목록}} · 아니면 None)."""
    mo = (ov or {}).get(FIELDS["override"]["months_ok"])
    if isinstance(mo, list):
        return mo
    if isinstance(mo, dict):
        c = mo.get(card)
        if isinstance(c, list):
            return c
        if isinstance(c, dict) and isinstance(c.get(dummy), list):
            return c[dummy]
    return None


def override_defined(ov, card, dummy):
    P0A = _p0a()
    f = getattr(P0A, "_override_defined", None) if P0A is not None else None
    return f(ov, card, dummy) if f is not None else _override_defined_local(ov, card, dummy)


def _is_ym(m):
    return isinstance(m, str) and len(m) == 7 and m[4] == "-" and m[:4].isdigit() and m[5:].isdigit()


def window_defined(pub_months, lead=2):
    """공개월 목록 → t−lead..t 창이 모두 자료 안에 드는 달 t 목록([첫 + lead, 끝]) — r_p0_adapt.window_defined 와 같은 뜻."""
    pm = sorted(m for m in pub_months if _is_ym(m))
    if not pm:
        return []
    out, m = [], Q.mshift(pm[0], lead)
    while m <= pm[-1]:
        out.append(m)
        m = Q.mshift(m, 1)
    return out


def coverage_months(path):
    """§F 커버리지 F0 를 넘은 신호월 목록 — 파일이 없으면 None(r_p0_adapt.coverage_months 에 경로를 넘긴다 · 없으면 목록 모양만 읽는다)."""
    if not path or not os.path.exists(path):
        return None
    P0A = _p0a()
    if P0A is not None and hasattr(P0A, "coverage_months"):
        return P0A.coverage_months(path)
    d = _read(path)
    if isinstance(d, dict) and isinstance(d.get("months_ok"), list):
        return sorted(d["months_ok"])
    raise SystemExit("🚨 커버리지 파일 %s 모양을 모른다(r_p0_adapt 없음) — r_stages.coverage_months 를 고쳐라" % path)


def thash(T):
    """목표 경로 해시 — q_ltd.thash 와 같은 식(sort_keys JSON 의 sha256)."""
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def jaccard(a, b):
    a, b = set(a), set(b)
    return (len(a & b) / len(a | b)) if (a | b) else None


# ════════════════════════════════════════════════════════════════════════
# 어댑터 — 발행사 지도 · 표지 판
# ════════════════════════════════════════════════════════════════════════
class IssuerMap:
    """§A0 날짜 인식 발행사 지도 — (티커, 달) → (그룹, fpi). 명단 티커는 '-', 지도는 '.' 표기일 수 있어 둘 다 찾는다.
    fpi: 1 = FPI(Section 16 비적용 · 걸러낼 수 없음) · 0 · None(모름 → Section 16 적용으로 본다 · r_r1_flags 선언 i)."""

    def __init__(self, doc, src=None):
        F = FIELDS["issuer_map"]
        R = F["row"]
        self.runs = {}
        fx = int((doc.get(F["fpi_registered"]) or {}).get("tm_index", R["fpi"]))
        self.fpi_index = fx
        for t, runs in (doc.get(F["tm"]) or {}).items():
            self.runs[t] = [(r[R["first"]], r[R["last"]], r[R["gid"]],
                             (r[fx] if len(r) > fx else (r[R["fpi"]] if len(r) > R["fpi"] else None))) for r in runs]
        # 지도 F0(선언 ⑭) — f0 표가 없으면 None(걸지 않는다) · 있으면 {달: 위반율}
        f0 = doc
        for k in F["f0"]:
            f0 = f0.get(k) if isinstance(f0, dict) else None
        self.viol = ({m: v[F["f0_rate"]] for m, v in f0.items() if isinstance(v, (list, tuple)) and len(v) > F["f0_rate"]}
                     if isinstance(f0, dict) else None)
        bm = doc
        for k in F["bad_months"]:
            bm = bm.get(k) if isinstance(bm, dict) else None
        self.bad = set(bm) if isinstance(bm, list) else set()
        self.src = src
        self._c = {}

    def has_f0(self):
        return self.viol is not None

    def month_ok(self, m):
        """지도 F0 — 그달 위반율 ≤ 2% 이고 bad_months 밖이면 True · 표에 없는 달은 None(쓰지 않는다 · r_stagem.IssuerMap.month_ok 와 같은 뜻)."""
        if self.viol is None:
            return None
        v = self.viol.get(m)
        if v is None:
            return None
        return bool(v is not None and v <= IM_VIOL and m not in self.bad)

    @classmethod
    def load(cls, path=None):
        path = path or os.path.join(RDATA, FIELDS["issuer_map"]["file"])
        doc = _read(path)
        if doc is None:
            raise SystemExit("🚨 발행사 지도 %s 가 없다 — RBATCH_DATA 로 지도가 있는 data 경로를 넘겨라" % path)
        return cls(doc, {"path": path, "sha256": _sha_file(path)})

    def who(self, t, m):
        ck = (t, m)
        if ck in self._c:
            return self._c[ck]
        out = (None, None)
        for c in (t, t.replace("-", "."), t.replace(".", "-")):
            for a, b, g, fpi in self.runs.get(c) or ():
                if a <= m <= b:
                    out = (g or None, fpi)
                    break
            if out != (None, None):
                break
        self._c[ck] = out
        return out

    def gids(self):
        return sorted({g for rs in self.runs.values() for _, _, g, _ in rs if g})


class FlagSource:
    """한 표지의 그룹 × 달 표. dummy(g, m) → 1 · 0 · None(모름). 표에 없는 칸은 0(그달 사건 없음) · months_ok 밖의 달은 None.
    active(g, r) = r−window+1..r 창에 1 이 하나라도 → 1 · 아니고 None 이 끼면 None · 아니면 0(r_r1_flags.Flags.active 와 같은 뜻).
    kind: "real"(실제 자료 — run() 은 등록 커밋 없이는 수익을 계산하지 않는다) · "synthetic" · "zero"."""

    def __init__(self, name, kind, on, unk=None, months_ok=None, window=None, src=None, info=None):
        self.name, self.kind = name, kind
        self.on = {m: set(v) for m, v in (on or {}).items() if v}
        self.unk = {m: set(v) for m, v in (unk or {}).items() if v}
        self.months_ok = set(months_ok) if months_ok is not None else None
        self.window = window or WINDOW.get(name, 1)
        self.src = src
        self.info = info or {}

    def dummy(self, g, m):
        if self.months_ok is not None and m not in self.months_ok:
            return None
        if g in self.on.get(m, ()):
            return 1
        if g in self.unk.get(m, ()):
            return None
        return 0

    def active(self, g, r, window=None):
        w = window or self.window
        vals = [self.dummy(g, Q.mshift(r, -j)) for j in range(w)]
        if 1 in vals:
            return 1
        return None if None in vals else 0

    def digest(self):
        h = {"on": {m: sorted(v) for m, v in sorted(self.on.items())}, "unk": {m: sorted(v) for m, v in sorted(self.unk.items())},
             "months_ok": sorted(self.months_ok) if self.months_ok is not None else None, "window": self.window}
        return hashlib.sha256(json.dumps(h, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    def describe(self):
        return {"name": self.name, "kind": self.kind, "src": self.src, "window": self.window, "digest": self.digest(),
                "n_on": sum(len(v) for v in self.on.values()), "n_unk": sum(len(v) for v in self.unk.values()),
                "months": [min(self.on), max(self.on)] if self.on else None}

    def perturbed_after(self, cut, rng, rate=0.2, gids=()):
        """시험용 — cut 뒤 달의 칸을 모두 지우고 무작위로 다시 채운 사본(점 시점 교란 · cut 이하 달은 그대로)."""
        on = {m: set(v) for m, v in self.on.items() if m <= cut}
        unk = {m: set(v) for m, v in self.unk.items() if m <= cut}
        later = sorted({m for m in list(self.on) + list(self.unk) if m > cut} | {Q.mshift(cut, j) for j in range(1, 7)})
        gl = list(gids)
        for m in later:
            u = rng.random(len(gl))
            on[m] = {g for g, x in zip(gl, u) if x < rate}
            unk[m] = {g for g, x in zip(gl, u) if rate <= x < rate + 0.05}
        return FlagSource(self.name, self.kind, on, unk, self.months_ok, self.window, self.src, self.info)


def fs_from_cikmonth(doc, kind="real", src=None):
    """cikmonth.json(r_r1_flags.cikmonth_doc) → (OS, RS, usd{(그룹, 달): $}). 뜻은 r_r1_flags.Flags.dummy 와 같다 —
    O > 0 → 1 · 아니고 os_na(또는 N > 0) → None · 아니면 0 · months_ok 밖의 달 None · 표에 없는 칸 0."""
    F = FIELDS["ins"]
    root = next((doc[k] for k in F["root"] if isinstance(doc.get(k), dict)), None)
    if root is None:
        raise SystemExit("🚨 cikmonth 최상위 키 %s 가 없다 — 있는 키 %s · r_stages.FIELDS['ins'] 를 고쳐라" % (list(F["root"]), sorted(doc)[:20]))
    mo = doc.get(F["months_ok"])
    on = {"OS": {}, "RS": {}}
    unk = {"OS": {}, "RS": {}}
    usd, seen = {}, 0
    for g, bym in root.items():
        if not isinstance(bym, dict):
            continue
        for m, rec in bym.items():
            if not isinstance(rec, dict):
                continue
            o, rr = _pick(rec, F["os"]), _pick(rec, F["rs"])
            seen += (o is not None) or (rr is not None)
            na = float(_pick(rec, F["na"]) or 0)
            for key, v, flag in (("OS", o, _pick(rec, F["os_na"])), ("RS", rr, _pick(rec, F["rs_na"]))):
                if float(v or 0) > 0:
                    on[key].setdefault(m, set()).add(str(g))
                elif (bool(flag) if flag is not None else na > 0):
                    unk[key].setdefault(m, set()).add(str(g))
            u = _pick(rec, F["usd"])
            if u:
                usd[(str(g), m)] = float(u)
    if root and not seen:
        raise SystemExit("🚨 cikmonth 에 기회주의(%s)·루틴(%s) 칸이 한 번도 없다 — FIELDS['ins'] 를 고쳐라" % (F["os"], F["rs"]))
    return (FlagSource("OS", kind, on["OS"], unk["OS"], mo, src=src), FlagSource("RS", kind, on["RS"], unk["RS"], mo, src=src), usd)


def fs_from_r2(gm, gm_doc=None, kind="real", src=None, months_ok=None):
    """r_r2flags.ch_active 행 {(그룹, t): 행} → (CH, CH_MISS, simdoc{(g, t): SimDoc}, dlog{(g, t): Δlog}) — CH 는 이미 t−2..t 창이다."""
    F = FIELDS["r2_gm"]
    ch, miss, dlog = {}, {}, {}
    for (g, t), row in gm.items():
        if row.get(F["ch"]):
            ch.setdefault(t, set()).add(str(g))
        if row.get(F["miss"]):
            miss.setdefault(t, set()).add(str(g))
        if row.get(F["dlog"]) is not None:
            dlog[(str(g), t)] = float(row[F["dlog"]])
    simdoc = {(str(g), t): float(row[F["sim"]]) for (g, t), row in (gm_doc or {}).items() if row.get(F["sim"]) is not None}
    return (FlagSource("CH", kind, ch, None, months_ok, src=src), FlagSource("CH_MISS", kind, miss, None, months_ok, src=src),
            simdoc if gm_doc is not None else None, dlog)


def fs_from_override(doc, name, kind="real"):
    """덮어쓰기 {"cards": {카드: {더미: {월: [그룹]}}}, "months_ok": …} → FlagSource 또는 None.
    months_ok 는 r_p0_adapt._override_defined 와 같은 세 모양(선언 ⑮) — 없으면 None(모든 달을 정의된 달로 본다 · 부르는 쪽이 경고를 싣는다)."""
    F = FIELDS["override"]
    card, dummy = F["map"][name]
    c = ((doc or {}).get(F["cards"]) or {}).get(card) or {}
    if dummy not in c or not isinstance(c[dummy], dict):
        return None
    mo = override_defined(doc, card, dummy)
    return FlagSource(name, kind, {m: set(map(str, v)) for m, v in c[dummy].items()}, None, mo,
                      src="override:%s" % F["file"], info={"months_ok_given": mo is not None})


def sub_months_ok(raw, recs):
    """ALARM 정의 달(선언 ⑬) — 최상위 months_ok(목록)가 있으면 그것 · 없으면 [첫 제출월 + 11, 끝 제출월](filingDate 범위) · 날짜가 없으면 None."""
    mo = raw.get(FIELDS["sub"]["months_ok"]) if isinstance(raw, dict) else None
    if isinstance(mo, list):
        return sorted(mo), "file months_ok"
    fm = sorted({str(r.get(FIELDS["sub"]["fd"]))[:7] for r in recs if r.get(FIELDS["sub"]["fd"])})
    fm = [m for m in fm if _is_ym(m)]
    if not fm:
        return None, "filingDate 없음 — 정의 달을 모른다(모든 달을 정의된 달로 본다)"
    return window_defined(fm, lead=R5_A_MONTHS - 1), "[첫 제출월 + %d, 끝 제출월] %s..%s" % (R5_A_MONTHS - 1, fm[0], fm[-1])


def load_bundle(view, rdata=None, im=None, r2_world=None, allow_override=False):
    """실제 표지 판 한 벌 → {"im", "OS", "RS", "usd", "CH", "CH_MISS", "simdoc", "dlog", "ALARM", "coverage", "src"}. 없는 것은 None(이유는 src).
    allow_override=False(기본)면 덮어쓰기 파일이 있어도 쓰지 않는다(선언 ⑮ · r_p0 --allow-override 와 같은 뜻)."""
    rdata = rdata or RDATA
    imp = os.path.join(rdata, FIELDS["issuer_map"]["file"])
    im = im or IssuerMap.load(imp)
    B = {"im": im, "src": {"issuer_map": im.src, "sha_rule": SHA_RULE}}
    for k in ("OS", "RS", "usd", "CH", "CH_MISS", "simdoc", "dlog", "ALARM"):
        B[k] = None
    ovp = os.path.join(rdata, FIELDS["override"]["file"])
    ov = _read(ovp) if os.path.exists(ovp) else None
    if ov is not None and not allow_override:
        B["src"]["override"] = {"path": ovp, "sha256": _sha_file(ovp), "used": False,
                                "why": "덮어쓰기는 옵트인(allow_override · --allow-override) — 정식 빌더를 가린다(Stage M · r_run 은 읽지 않는다)"}
        print("⚠ r_stages: 덮어쓰기 %s 가 있지만 쓰지 않는다(allow_override 없음)" % ovp, file=sys.stderr)
    elif ov is not None:
        B["src"]["override"] = {"path": ovp, "sha256": _sha_file(ovp), "used": True}
        for name in ("OS", "RS", "CH", "CH_MISS", "ALARM"):
            fs = fs_from_override(ov, name)
            if fs is not None:
                B[name] = fs
                B["src"][name] = {"from": "override", "path": ovp, "sha256": _sha_file(ovp), "months_ok_given": fs.info["months_ok_given"]}
                if not fs.info["months_ok_given"]:
                    B["src"][name]["warn"] = "덮어쓰기에 months_ok 가 없다 — 모든 달을 정의된 달로 읽는다(자료 밖 달이 0 으로 읽힌다)"
    # R1 — cikmonth(정본 r_r1_flags) · C2 의 매도 $ 는 여기에만 있다
    p = os.path.join(rdata, FIELDS["ins"]["file"])
    doc = _read(p)
    if doc is None:
        for name in ("OS", "RS"):
            B["src"].setdefault(name, {"from": "absent", "path": p})
    else:
        os_, rs_, usd = fs_from_cikmonth(doc, src="cikmonth:%s" % p)
        B["usd"] = usd
        for name, fs in (("OS", os_), ("RS", rs_)):
            if B[name] is None:
                B[name] = fs
                B["src"][name] = {"from": "canonical:cikmonth(r_r1_flags)", "path": p, "sha256": _sha_file(p)}
    # R2 — 10-Q 특징(정본 r_r2flags.r2_build — 1차 SimRF · 대조 SimDoc). 덮어쓰기가 CH 를 줘도 SimDoc · Δlog 는 정본에서(선언 ⑮)
    p = os.path.join(rdata, FIELDS["tenq"]["file"])
    if not os.path.exists(p):
        for name in ("CH", "CH_MISS"):
            B["src"].setdefault(name, {"from": "absent", "path": p})
        if B["CH"] is not None:
            B["src"]["CH"]["controls_warn"] = "정본 10-Q 가 없어 SimDoc · Δlog 대조(C2 · C5)를 지을 수 없다 — 실제 굽기는 멈춘다"
    else:
        import r_r2flags as R2
        im2 = R2.IssuerMap.load(imp)
        raw = _read(p)
        recs, cal = R2.load_tenq(p), R2.Cal()
        R = R2.r2_build(recs, cal, gof=im2.group_of, world=r2_world)
        Rd = R2.r2_build(recs, cal, gof=im2.group_of, world=r2_world, metric="doc")
        mo = raw.get(FIELDS["tenq"]["months_ok"]) if isinstance(raw, dict) else None
        if isinstance(mo, list):
            mo, mo_how = sorted(mo), "file months_ok"
        else:
            pm = {d.get(FIELDS["tenq"]["pub_m"]) for d in R["docs"].values()}
            mo = window_defined(pm)
            mo_how = "window_defined(공개월) %s..%s" % (mo[0], mo[-1]) if mo else "공개월 없음"
        ch, miss, simdoc, dlog = fs_from_r2(R["gm"], Rd["gm"], src="canonical:r_r2flags.r2_build(%s)" % p, months_ok=mo)
        B.update({"simdoc": simdoc, "dlog": dlog})
        info = {"path": p, "sha256": _sha_file(p), "r2_hash": R2.r2_hash(R), "months_ok": mo_how,
                "world": "given" if r2_world is not None else "§C 자료 전체(r_r2flags ⑦)"}
        for name, fs in (("CH", ch), ("CH_MISS", miss)):
            if B[name] is None:
                B[name] = fs
                B["src"][name] = dict(info, **{"from": "canonical:r_r2flags.r2_build"})
            else:
                B["src"][name]["controls_from"] = dict(info, **{"from": "canonical:r_r2flags.r2_build(SimDoc · Δlog 만)"})
    # R5 — submissions(정본 r_r2flags.r5_events · 형성일 = 세계 격자의 그달 마지막 거래일)
    if B["ALARM"] is None:
        p = os.path.join(rdata, FIELDS["sub"]["file"])
        if not os.path.exists(p):
            B["src"]["ALARM"] = {"from": "absent", "path": p}
        else:
            import r_r2flags as R2
            im2 = R2.IssuerMap.load(imp)
            tp = os.path.join(rdata, FIELDS["sub"]["t401"])
            t401 = R2.load_t401(tp) if os.path.exists(tp) else None
            raw = _read(p)
            recs = R2.load_sub(p)
            mo, mo_how = sub_months_ok(raw, recs)
            ev, log, c401 = R2.r5_events(recs, R2.Cal(), gof=im2.group_of, t401=t401)
            on, info = {}, {}
            for m in view.months:
                d = view.dates[view.me[m]]
                for g, evs in ev.items():
                    hit = R2.r5_alarm(evs, m, d)
                    if hit:
                        on.setdefault(m, set()).add(str(g))
                        info[(str(g), m)] = sorted({e["type"] for e in hit})
            B["ALARM"] = FlagSource("ALARM", "real", on, None, mo, src="canonical:r_r2flags.r5_events(%s)" % p, info=info)
            B["src"]["ALARM"] = {"from": "canonical:r_r2flags.r5_events", "path": p, "sha256": _sha_file(p), "t401": bool(t401),
                                 "log": log, "c401": c401, "months_ok": mo_how}
    # §F 커버리지 F0(선언 ⑭) — 있으면 F0 중앙값에서 그 밖의 편입을 뺀다
    cp = os.path.join(rdata, FIELDS["coverage"]["file"])
    B["coverage"] = coverage_months(cp)
    B["src"]["coverage"] = {"path": cp, "exists": B["coverage"] is not None, "sha256": _sha_file(cp)}
    return B


def zero_bundle(im):
    """모든 표지가 0 인 판(V0 재현 대조)."""
    B = {"im": im, "src": {"all": "zero"}}
    for f in ("OS", "RS", "CH", "CH_MISS", "ALARM"):
        B[f] = FlagSource(f, "zero", {}, src="zero")
    B.update({"usd": {}, "simdoc": {}, "dlog": {}, "coverage": None})
    return B


def synth_bundle(im, months, seed=11, rate=None, unk=0.01):
    """합성 표지 판 — 그룹 × 달 독립 베르누이(수익과 무관 · 구성 점검용). 실제 자료가 아니다(kind "synthetic")."""
    rate = rate or {"OS": 0.06, "RS": 0.05, "CH": 0.15, "CH_MISS": 0.03, "ALARM": 0.01}
    rng = np.random.default_rng(seed)
    gids = im.gids()
    B = {"im": im, "src": {"all": "synthetic seed %d" % seed}}
    for f in ("OS", "RS", "CH", "CH_MISS", "ALARM"):
        p = rate[f]
        on, un = {}, {}
        for m in months:
            u = rng.random(len(gids))
            on[m] = {g for g, x in zip(gids, u) if x < p}
            un[m] = {g for g, x in zip(gids, u) if p <= x < p + (unk if f in ("OS", "RS") else 0.0)}
        B[f] = FlagSource(f, "synthetic", on, un, src="synthetic seed %d" % seed)
    # 매도 $ — 활성 이름-월의 40% 만(나머지는 가격 없는 행 흉내 · C2 의 «매도 없음 채움» 이 합성에서도 실제로 걸리게)
    usd = {}
    for m in months:
        for g in sorted(B["OS"].on.get(m, set()) | B["RS"].on.get(m, set())):
            u, v = rng.random(), float(rng.lognormal(12.0, 1.5))
            if u < 0.4:
                usd[(g, m)] = v
    B["usd"] = usd
    B["simdoc"] = {(g, m): float(rng.uniform(0.6, 1.0)) for m in months for g in gids if rng.random() < 0.3}
    B["dlog"] = {(g, m): float(rng.normal(0.0, 0.1)) for m in months for g in gids if rng.random() < 0.3}
    B["coverage"] = None
    return B


def _guard(bundle):
    """실제 표지로 수익을 계산하려면 등록 커밋이 있어야 한다(방화벽)."""
    kinds = {v.kind for v in bundle.values() if isinstance(v, FlagSource)}
    if "real" in kinds:
        c = os.environ.get("RBATCH_COMMIT")
        if not c:
            raise SystemExit("🚨 실제 표지로 Stage S 수익을 계산하려면 RBATCH_COMMIT(등록 커밋)이 있어야 한다 — 등록 전에는 --construct(구성만)"
                             " · 합성 표지만 된다.")
        return c
    return None


# ════════════════════════════════════════════════════════════════════════
# 세계 보기 — 구성이 쓰는 것만(eg30plus.World · 합성 세계 둘 다)
# ════════════════════════════════════════════════════════════════════════
def _cand():
    import eg30plus as E
    return dict(E.EG_BASE, index="union")


class View:
    def __init__(self, Wd, im):
        self.Wd, self.im = Wd, im
        self.months, self.me, self.dates = Wd.months, Wd.me, Wd.dates
        self._rk = {}

    def forms(self):
        import eg30plus as E
        return E.formations(self.Wd)

    def ranked(self, m):
        """편입월 m 의 Eg 순위 [(명단 티커, 가격 키)] — qg_lab.World.score(EG_BASE · union) 그대로(V0 가 앞 30 을 쓴다)."""
        if m not in self._rk:
            self._rk[m] = [x for x, _ in self.Wd.score(_cand(), m)]
        return self._rk[m]

    def mcap(self, t, k, i):
        return self.Wd.mcap(t, k, i)

    def mom(self, m):
        return self.Wd.raw("mom", m, "union", False)

    def beta(self, k, i):
        return self.Wd.fp_beta(k, i)

    def sector(self, t, k, m):
        return self.Wd.sector(t, k, m)

    def px(self, k):
        return self.Wd.PX[k]

    def who(self, t, m):
        return self.im.who(t, m) if self.im is not None else (None, None)


# ════════════════════════════════════════════════════════════════════════
# 구성 — 상태 · 빼기-채우기 · V0 비중
# ════════════════════════════════════════════════════════════════════════
def status_one(view, fs, x, r):
    """이름 x = (티커, 키)의 편입월 r 상태 — 'fpi' · 'unres' · 'unk' · 'on' · 'off'(선언 ②)."""
    g, fpi = view.who(x[0], r)
    if fpi == 1:
        return "fpi"
    if not g:
        return "unres"
    a = fs.active(g, r)
    return "unk" if a is None else ("on" if a == 1 else "off")


def combine(sts):
    """여러 표지의 상태 → 하나(선언 ④): on 이 하나라도 → on · 아니고 unres/unk 가 끼면 그것 · 모두 fpi/off 면 fpi(하나라도) 또는 off."""
    for s in ("on", "unres", "unk", "fpi"):
        if s in sts:
            return s
    return "off"


def replace_top(ranked, n, drop, fill_ok):
    """상위 n 에서 drop 을 빼고, 차순위 가운데 fill_ok(이름) 가 참인 것으로 Eg 순서대로 채운다(r_r1_flags.replace_top 과 같은 뜻 · 시험이 대조)."""
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


def _all(_x):
    return True


def weights(view, i, picks):
    """V0 규칙(선언 ①) — qg_lab.World.weights 와 같은 순서 · 같은 반복(eg30plus.cap_weights) → {"w": {키: 비중}, "names": {키: 티커}}."""
    import eg30plus as E
    mc = {x: view.mcap(x[0], x[1], i) for x in picks}
    mc = {x: v for x, v in mc.items() if v}
    w = E.cap_weights(mc, CAP)
    return {"w": {x[1]: v for x, v in w.items()}, "names": {x[1]: x[0] for x in w}}


def stage_s(view, bundle, flags, forms):
    """분기 편입마다 빼기-채우기 → {"forms", "T", "rec", "state"}. state[r] = 순위 · 상태 · 모집단 · 뺀 이름(대조 · 위약 · 시험이 쓴다)."""
    T, rec, state = {}, [], {}
    miss = bundle.get("CH_MISS") if "CH" in flags else None
    for r in forms:
        i = view.me[r]
        ranked = view.ranked(r)
        per = {x: [status_one(view, bundle[f], x, r) for f in flags] for x in ranked}
        st = {x: combine(v) for x, v in per.items()}
        top = ranked[:N_TOP]
        res = replace_top(ranked, N_TOP, [x for x in top if st[x] == "on"], lambda x: st[x] in FILL_OK)
        T[r] = weights(view, i, res["picks"])
        last = ranked.index(res["filled"][-1]) if res["filled"] else N_TOP - 1
        skipped = [x for x in ranked[N_TOP:last + 1] if st[x] not in FILL_OK]
        row = {"r": r, "n_r": res["n_r"], "dropped": [x[0] for x in res["dropped"]], "filled": [x[0] for x in res["filled"]],
               "short": res["short"], "n_droppable": sum(st[x] in DROPPABLE for x in top),
               "n_fpi_top": sum(st[x] == "fpi" for x in top), "n_unres_top": sum(st[x] == "unres" for x in top),
               "n_unk_top": sum(st[x] == "unk" for x in top), "n_fpi_fill": sum(st[x] == "fpi" for x in res["filled"]),
               "n_skip_fill": sum(st[x] in ("unk", "unres") for x in skipped), "n_skip_on": sum(st[x] == "on" for x in skipped),
               "n": len(T[r]["w"])}
        if len(flags) > 1:
            row["n_on_by_flag"] = {f: sum(per[x][j] == "on" for x in top) for j, f in enumerate(flags)}
        if miss is not None:
            row["n_miss_top"] = sum(1 for x in top if view.who(x[0], r)[0] and miss.active(view.who(x[0], r)[0], r) == 1)
        rec.append(row)
        state[r] = {"ranked": ranked, "st": st, "top": top, "droppable": [x for x in top if st[x] in DROPPABLE],
                    "drop": list(res["dropped"]), "fill": list(res["filled"]), "n_r": res["n_r"]}
    return {"forms": list(forms), "flags": list(flags), "T": T, "rec": rec, "state": state}


def v0_rebuild(view, forms):
    """V0 목표를 같은 함수(weights · Eg 앞 30)로 — ctx.V0_targets 와 해시가 같아야 한다."""
    return {r: weights(view, view.me[r], view.ranked(r)[:N_TOP]) for r in forms}


# ── 대조 · 위약 ───────────────────────────────────────────────────────────
def pick_set(pool, cands, n_r, rng, exclude=()):
    """C1 — r_r1_flags.pick_set 와 같은 식(선언 ⑥ · 시험이 대조): 모집단 가운데 후보(∖ exclude)에서 n_r(많으면 무작위) · 모자라면 나머지
    (∖ exclude)에서 무작위로 채운다 · 그래도 모자라면 n_r 보다 적게. exclude(편입일의 규칙 활성 이름)는 후보에서도 채움에서도 뺀다."""
    ex = set(exclude)                  # n_r = 0 도 형제와 같이 rng.choice(…, 0) 를 부른다(한 줄기의 소비가 형제와 같게)
    cs = set(cands) - ex
    c = [x for x in pool if x in cs]
    rest = [x for x in pool if x not in cs and x not in ex]
    if len(c) >= n_r:
        return [c[j] for j in sorted(rng.choice(len(c), n_r, replace=False).tolist())]
    k = min(len(rest), n_r - len(c))
    extra = [rest[j] for j in sorted(rng.choice(len(rest), k, replace=False).tolist())] if k > 0 else []
    return c + extra


def pick_c2(pool, score, n_r, rng, exclude=()):
    """R1 C2 — r_r1_flags.pick_c2 와 같은 식(선언 ⑦ · 시험이 대조): 점수 > 0 인 이름만 점수 순(동점 Eg 순서) · 모자라면 나머지(점수 ≤ 0 · 없음)
    에서 씨앗 무작위로 채운다 → {"picks", "n_nosale"(채움 수)}."""
    ex = set(exclude)
    pos = {x: j for j, x in enumerate(pool)}
    sc = {x: score(x) for x in pool if x not in ex}
    pos_k = sorted((x for x, v in sc.items() if v is not None and v == v and v > 0), key=lambda x: (-sc[x], pos[x]))
    picks = pos_k[:n_r]
    ps = set(pos_k)
    rest = [x for x in pool if x in sc and x not in ps]
    need = min(len(rest), n_r - len(picks))
    extra = [rest[j] for j in sorted(rng.choice(len(rest), need, replace=False).tolist())] if need > 0 else []
    return {"picks": picks + extra, "n_nosale": len(extra)}


def pick_ordered(pool, score, n_r, hi=True):
    """C2~C5 — 점수 상위(hi) 또는 하위 n_r · 점수 없는 이름은 뒤 · 동점은 Eg 순서(pool 은 Eg 순)."""
    if n_r <= 0:
        return []
    sc = {}
    for x in pool:
        v = score(x)
        sc[x] = None if (v is None or v != v) else float(v)
    pos = {x: j for j, x in enumerate(pool)}
    key = lambda x: (sc[x] is None, (-sc[x] if hi else sc[x]) if sc[x] is not None else 0.0, pos[x])
    return sorted(pool, key=key)[:n_r]


def pick_random(pool, n_r, rng):
    """위약 — 모집단에서 비복원 균등 n_r(뽑은 이름은 Eg 순으로 돌려준다)."""
    if n_r <= 0:
        return []
    return [pool[j] for j in sorted(rng.choice(len(pool), min(n_r, len(pool)), replace=False).tolist())]


def score_fn(view, bundle, name):
    """순서 대조 점수 함수(x, r) → 값 또는 None · 자료가 없으면 None(대조를 «없음» 으로 싣는다)."""
    if name == "mom":
        return lambda x, r: view.mom(r).get(x)
    if name == "beta":
        return lambda x, r: view.beta(x[1], view.me[r])
    if name == "sell_usd_mcap":
        usd = bundle.get("usd")
        if usd is None:
            return None

        def f(x, r):
            g, _ = view.who(x[0], r)
            mc = view.mcap(x[0], x[1], view.me[r])
            if not g or not mc:
                return None
            return sum(usd.get((g, Q.mshift(r, -j)), 0.0) for j in range(WINDOW["OS"])) / mc
        return f
    if name in ("simdoc", "dlog"):
        aux = bundle.get(name)
        if aux is None:
            return None

        def g_(x, r):
            g, _ = view.who(x[0], r)
            return aux.get((g, r)) if g else None
        return g_
    raise ValueError(name)


def control(view, bundle, base, kind, arg):
    """교체 수를 맞춘 대조 한 판 → {"T", "drop"{r: [x]}, "hash"} 또는 {"T": None, "unavailable": 이유}."""
    rng = None
    if kind == "set":
        fs = bundle.get(arg)
        if fs is None:
            return {"T": None, "unavailable": "%s 표지 없음" % arg, "kind": kind, "arg": arg}
        rng = np.random.default_rng(C1_SEED)
    else:
        sf = score_fn(view, bundle, arg)
        if sf is None:
            return {"T": None, "unavailable": "%s 자료 없음" % arg, "kind": kind, "arg": arg}
        if kind == "pos":
            rng = np.random.default_rng(C2_SEED)
    T, drop, extra = {}, {}, {}
    for r in base["forms"]:
        S = base["state"][r]
        pool, n_r = S["droppable"], S["n_r"]
        if kind == "set":
            on_rule = [x for x in pool if S["st"][x] == "on"]           # 규칙 활성 — 후보·채움 모두에서 뺀다(선언 ⑥)
            cands = [x for x in pool if status_one(view, fs, x, r) == "on"]
            d = pick_set(pool, cands, n_r, rng, exclude=on_rule)
            ors = set(on_rule)
            extra[r] = {"cand_n": sum(1 for x in cands if x not in ors), "c1_overlap": sum(1 for x in d if x in ors),
                        "c1_short": n_r - len(d)}
        elif kind == "pos":
            got = pick_c2(pool, lambda x: sf(x, r), n_r, rng)
            d = got["picks"]
            extra[r] = {"n_nosale": got["n_nosale"]}
        else:
            d = pick_ordered(pool, lambda x: sf(x, r), n_r, hi=(kind == "hi"))
        res = replace_top(S["ranked"], N_TOP, d, _all)
        T[r] = weights(view, view.me[r], res["picks"])
        drop[r] = d
    out = {"T": T, "drop": drop, "hash": thash(T), "kind": kind, "arg": arg}
    if kind == "set":
        out["cand_n"] = {r: v["cand_n"] for r, v in extra.items()}
        out["c1_overlap"] = {r: v["c1_overlap"] for r, v in extra.items()}
        out["c1_short"] = {r: v["c1_short"] for r, v in extra.items()}
    if kind == "pos":
        out["n_nosale"] = {r: v["n_nosale"] for r, v in extra.items()}
    return out


def placebo_targets(view, base, i_draw):
    """위약 뽑기 i — default_rng(SEED + i) 한 줄기로 편입 순서대로 · 편입마다 모집단에서 n_r 를 빼고 Eg 차순위로 채운다."""
    rng = np.random.default_rng(SEED + i_draw)
    T = {}
    for r in base["forms"]:
        S = base["state"][r]
        d = pick_random(S["droppable"], S["n_r"], rng)
        res = replace_top(S["ranked"], N_TOP, d, _all)
        T[r] = weights(view, view.me[r], res["picks"])
    return T


def placebo_drops(view, base, i_draw):
    """시험용 — 뽑기 i 의 편입별 뺀 이름(placebo_targets 와 같은 줄기)."""
    rng = np.random.default_rng(SEED + i_draw)
    return {r: pick_random(base["state"][r]["droppable"], base["state"][r]["n_r"], rng) for r in base["forms"]}


def measurable(r, flags, bundle, im=None):
    """편입 r 을 잴 수 있는가(선언 ⑭) → 못 재는 이유 목록(빈 목록이 잴 수 있음).
    표지마다 창 r−w+1..r 의 달이 모두 months_ok 안 · 지도 F0(표가 있을 때) True · §F 커버리지(파일이 있을 때) 안."""
    why = []
    for f in flags:
        fs = bundle.get(f)
        if fs is None:
            why.append("%s 없음" % f)
            continue
        if fs.months_ok is not None and any(Q.mshift(r, -j) not in fs.months_ok for j in range(fs.window)):
            why.append("%s 창 밖" % f)
    if im is not None and im.has_f0() and im.month_ok(r) is not True:
        why.append("지도 F0(%s)" % ("표에 없음" if im.month_ok(r) is None else "위반율 > %g" % IM_VIOL))
    cov = bundle.get("coverage")
    if cov is not None and r not in set(cov):
        why.append("커버리지 F0")
    return why


def f0_stage_s(base, bundle=None, im=None):
    """Stage S F0 — 잴 수 있는 편입(선언 ⑭)의 교체 수 중앙값이 2~15. 뺀 편입과 이유를 싣는다(구성은 그대로)."""
    excl = {}
    for row in base["rec"]:
        w = measurable(row["r"], base["flags"], bundle, im) if bundle is not None else []
        if w:
            excl[row["r"]] = w
    rows = [row for row in base["rec"] if row["r"] not in excl]
    n_r = [row["n_r"] for row in rows]
    med = float(np.median(n_r)) if n_r else None
    moy = {}
    for row in rows:
        moy.setdefault(row["r"][5:7], []).append(row["n_r"])
    return {"ok": bool(med is not None and F0_NR[0] <= med <= F0_NR[1]), "rule": "잴 수 있는 편입의 교체 수 중앙값 %d~%d" % F0_NR,
            "median_n_r": med, "min_n_r": min(n_r) if n_r else None, "max_n_r": max(n_r) if n_r else None,
            "n_forms": len(n_r), "n_forms_all": len(base["rec"]), "excluded": excl,
            "n_r": {row["r"]: row["n_r"] for row in base["rec"]},
            "median_n_r_all": float(np.median([row["n_r"] for row in base["rec"]])) if base["rec"] else None,
            "median_n_r_by_month": {k: float(np.median(v)) for k, v in sorted(moy.items())},   # R2 — 3월 편입은 교체가 적다(카드 선언)
            "fpi_top": [min(row["n_fpi_top"] for row in base["rec"]), max(row["n_fpi_top"] for row in base["rec"])] if base["rec"] else None}


def jac_by_form(a, b, forms):
    """편입마다 두 교체 명단의 자카드(둘 다 빈 편입은 뺀다) · 평균."""
    by = {r: jaccard([x[1] for x in a.get(r, ())], [x[1] for x in b.get(r, ())]) for r in forms}
    vals = [v for v in by.values() if v is not None]
    return {"by_form": by, "mean": float(np.mean(vals)) if vals else None, "n": len(vals)}


# ── R5 — 매월 빼기(선언 ⑨) · 사건 수 ─────────────────────────────────────
def _last_px(p, i, lo=0):
    for j in range(i, lo - 1, -1):
        v = p[j]
        if v == v and v > 0:
            return float(v)
    return None


def drift(view, w, i0, i1):
    """i0 비중이 i1 까지 흘러간 비중(마지막 유효 가격 · 합 1) — qg_lab.sleeve 의 단위 보유와 같은 뜻."""
    v = {}
    for k, x in w.items():
        p = view.px(k)
        a, b = _last_px(p, i0), _last_px(p, i1, i0)
        v[k] = x * (b / a) if (a and b) else x
    s = sum(v.values())
    return {k: x / s for k, x in v.items()} if s > 0 else dict(w)


def _fill_weights(mc, total, cap):
    """채움 비중 — total 을 시총 비례로, 한 이름 cap 을 넘지 않게(넘치면 나머지에 비례). eg30plus.water_fill 과 같은 뜻을
    **목록 순서**로(집합 순서에 매이지 않아 해시가 PYTHONHASHSEED 에 흔들리지 않는다) → (비중, 못 채운 몫)."""
    names = list(mc)
    w = {x: 0.0 for x in names}
    free = list(names)
    rem = total
    for _ in range(len(names) + 1):
        if not free or rem <= 1e-15:
            break
        s = sum(mc[x] for x in free)
        prop = {x: rem * mc[x] / s for x in free}
        over = [x for x in free if w[x] + prop[x] > cap + 1e-12]
        if not over:
            for x in free:
                w[x] += prop[x]
            rem = 0.0
            break
        for x in over:
            rem -= cap - w[x]
            w[x] = cap
        free = [x for x in free if x not in over]
    return w, rem


def build_r5(view, bundle, forms, v0T):
    """R5 매월 팔 목표(전방 원장용 · 표본 안 수익 없음) + 사건 수(V0 명단의 걸린 이름-월 · 업종 · 사건 종류)."""
    fs = bundle["ALARM"]
    fq = set(forms)
    T, rec, prev = {}, [], None
    for m in view.months:
        i = view.me[m]
        if m in fq or prev is None:
            ranked = view.ranked(m)
            st = {x: status_one(view, fs, x, m) for x in ranked}
            res = replace_top(ranked, N_TOP, [x for x in ranked[:N_TOP] if st[x] == "on"], lambda x: st[x] in FILL_OK)
            T[m] = weights(view, i, res["picks"])
            rec.append({"m": m, "kind": "form", "n_r": res["n_r"], "dropped": [x[0] for x in res["dropped"]],
                        "filled": [x[0] for x in res["filled"]], "short": res["short"]})
        else:
            w = drift(view, T[prev]["w"], view.me[prev], i)
            names = dict(T[prev]["names"])
            drop = [k for k in w if status_one(view, fs, (names[k], k), m) == "on"]
            if drop:
                held = set(w)
                fill = []
                for x in view.ranked(m):
                    if len(fill) >= len(drop):
                        break
                    if x[1] not in held and status_one(view, fs, x, m) in FILL_OK:
                        fill.append(x)
                freed = sum(w[k] for k in drop)
                keep = {k: v for k, v in w.items() if k not in drop}
                mc = {x: view.mcap(x[0], x[1], i) for x in fill}
                mc = {x: v for x, v in mc.items() if v}
                wf, rem = _fill_weights(mc, freed, CAP) if mc else ({}, freed)
                if rem > 1e-15 and keep:
                    s = sum(keep.values())
                    keep = {k: v + rem * v / s for k, v in keep.items()}
                wn = dict(keep)
                wn.update({x[1]: v for x, v in wf.items()})
                nn = {k: names[k] for k in keep}
                nn.update({x[1]: x[0] for x in wf})
                T[m] = {"w": wn, "names": nn}
                rec.append({"m": m, "kind": "swap", "n_r": len(drop), "dropped": [names[k] for k in drop],
                            "filled": [x[0] for x in wf], "short": len(drop) - len(wf)})
            else:
                T[m] = {"w": w, "names": names}
        prev = m
    # 사건 수 — 그달 말 V0 명단(직전 편입의 30)에서 걸린 이름-월(카드 «표본 안: 걸리는 이름-월 수와 업종 분포만»)
    fl = sorted(forms)
    C = {"name_months": 0, "flagged": 0, "fpi": 0, "unres": 0, "unk": 0, "by_year": {}, "by_sector": {}, "by_type": {}, "by_month": {}}
    for m in view.months:
        f = max(x for x in fl if x <= m)
        for k, t in sorted(v0T[f]["names"].items()):
            s = status_one(view, fs, (t, k), m)
            C["name_months"] += 1
            if s == "on":
                C["flagged"] += 1
                C["by_year"][m[:4]] = C["by_year"].get(m[:4], 0) + 1
                sec = view.sector(t, k, m) or "?"
                C["by_sector"][sec] = C["by_sector"].get(sec, 0) + 1
                C["by_month"].setdefault(m, []).append(t)
                for ty in fs.info.get((view.who(t, m)[0], m), ()):
                    C["by_type"][ty] = C["by_type"].get(ty, 0) + 1
            elif s in ("fpi", "unres", "unk"):
                C[s] += 1
    for k in ("by_year", "by_sector", "by_type", "by_month"):
        C[k] = dict(sorted(C[k].items()))
    arm = {"forms_n_r": [r["n_r"] for r in rec if r["kind"] == "form"], "swaps": sum(1 for r in rec if r["kind"] == "swap"),
           "swap_names": sum(r["n_r"] for r in rec if r["kind"] == "swap"), "short": sum(r["short"] for r in rec)}
    return {"T": T, "rec": rec, "counts": C, "arm": arm, "hash": thash(T)}


# ── 한 벌 구성(수익 없음) ─────────────────────────────────────────────────
def _specs(cards):
    """cards → {코드: 명세}(순서 유지). None = 모듈 CARDS · 코드 목록 = CARDS 에서 고른 것(종전 build 인자) · dict = 그 명세
    (배치 S 재사용 — 명세 모양은 CARDS 와 같다: flags · freq('Q' 편입 · 'M' 매월 사건 수) · placebo · returns · controls ·
    (선택) parts = F0 를 둘 다 넘어야 재는 부분 카드 목록)."""
    if cards is None:
        return dict(CARDS)
    if isinstance(cards, dict):
        return dict(cards)
    return {c: CARDS[c] for c in cards}


def _qcodes(specs):
    """편입 단위로 수익을 재는 카드(종전 QCARDS 의 순서 · 기본이면 QCARDS 그대로)."""
    return tuple(c for c, sp in specs.items() if sp.get("freq") == "Q")


def build(view, bundle, external=None, cards=None):
    """모든 팔의 목표 · 편입 기록 · 대조 · F0 · 자카드 — 수익을 읽지 않는다. external = {이름: {편입월: [티커]}}(Q07 제외 명단 등 · 자카드만).
    cards = None(모듈 CARDS) · 코드 목록 · {코드: 명세}(_specs)."""
    forms = view.forms()
    v0 = v0_rebuild(view, forms)
    out = {"forms": forms, "V0": v0, "v0_hash": thash(v0), "cards": {},
           "src": {k: (v.describe() if isinstance(v, FlagSource) else v) for k, v in bundle.items() if k != "im"}}
    specs = _specs(cards)
    for code, spec in specs.items():
        if any(bundle.get(f) is None for f in spec["flags"]):
            out["cards"][code] = None
            continue
        if spec["freq"] == "M":
            out["cards"][code] = build_r5(view, bundle, forms, v0)
            continue
        base = stage_s(view, bundle, spec["flags"], forms)
        base["controls"] = {c: control(view, bundle, base, kind, arg) for c, (kind, arg) in spec["controls"].items()}
        base["f0"] = f0_stage_s(base, bundle, bundle.get("im"))
        base["hash"] = thash(base["T"])
        base["jaccard"] = {}
        if base["controls"].get("C3", {}).get("T") is not None:
            base["jaccard"]["C3"] = jac_by_form({r: base["state"][r]["drop"] for r in forms}, base["controls"]["C3"]["drop"], forms)
        out["cards"][code] = base
    c1, c2 = out["cards"].get("R1-OPPSELL"), out["cards"].get("R2-LAZYRF")
    if c1 and c2:
        out["cards"]["R2-LAZYRF"]["jaccard"]["R1"] = jac_by_form({r: c2["state"][r]["drop"] for r in forms},
                                                                 {r: c1["state"][r]["drop"] for r in forms}, forms)
    for nm, lists in (external or {}).items():
        for code in ("R1-OPPSELL", "R2-LAZYRF"):
            C = out["cards"].get(code)
            if C:
                by = {r: jaccard([x[0] for x in C["state"][r]["drop"]], lists.get(r, ())) for r in forms}
                vals = [v for v in by.values() if v is not None]
                C["jaccard"][nm] = {"by_form": by, "mean": float(np.mean(vals)) if vals else None, "n": len(vals)}
    return out


def card_log(C, code):
    """싣는 편입 기록(이름은 티커 · 순위·상태 사전은 싣지 않는다)."""
    ctl = {}
    for c, K in C["controls"].items():
        if K.get("T") is None:
            ctl[c] = {"unavailable": K.get("unavailable"), "kind": K.get("kind"), "arg": K.get("arg")}
        else:
            ctl[c] = {"hash": K["hash"], "kind": K["kind"], "arg": K["arg"], "drop": {r: [x[0] for x in v] for r, v in K["drop"].items()}}
            for k in ("cand_n", "c1_overlap", "c1_short", "n_nosale"):
                if k in K:
                    ctl[c][k] = K[k]
    return {"card": code, "flags": C["flags"], "window": {f: WINDOW[f] for f in C["flags"]}, "formations": C["rec"], "controls": ctl,
            "jaccard": C.get("jaccard"), "f0": C["f0"]}


def q07_lists(ctx, pin=Q07_V1_PIN):
    """Q07 제외 명단(선언 ⑰ · 자카드 전용) → {"lists": {편입월: [티커 15]}, "V1_hash", "pin_ok", "manifest", "units", "sec"}.
    q_ltd 얼린 적합(strict — 다시 적합하지 않는다 · 지문이 FITS_MANIFEST 와 달라도 q_ltd 가 멈춘다)으로 V1 목표를 짓고, P(Eg 상위 45) 가운데
    V1 에 없는 이름을 돌려준다. V1 목표 해시가 핀과 다르면 멈춘다. R 표지를 읽지 않는다(Q07 자신의 구성만)."""
    import q_ltd as LT
    t0 = time.time()
    _rows, fits, stt = LT.fit_all(ctx, verbose=False, strict=True)
    T7, _rec = LT.build_targets(ctx, LT.signals(ctx, fits))
    h = LT.thash(T7["V1"])
    if pin and h != pin:
        raise SystemExit("🚨 Q07 V1 목표 해시 %s… 가 핀 %s… 와 다르다 — 얼린 적합·Eg 판을 확인하라" % (h[:16], pin[:16]))
    P = LT.pools(ctx)
    lists = {m: [t for t, k in P[m] if k not in T7["V1"][m]["w"]] for m in sorted(T7["V1"])}
    return {"lists": lists, "V1_hash": h, "pin_ok": (h == pin) if pin else None, "manifest": stt.get("manifest"), "units": stt.get("units"),
            "n_by_form": sorted({len(v) for v in lists.values()}), "sec": round(time.time() - t0, 1)}


# ════════════════════════════════════════════════════════════════════════
# 한 번 굽기 — CardResult(🚨 실제 표지는 등록 커밋 뒤에만)
# ════════════════════════════════════════════════════════════════════════
def _both_side(ex, hold):
    import qbatch_run as QR
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            b = QR.both_side(ex, hold)
        except Exception:
            return None
    return b if all(v == v for v in (b["crash_m"], b["surge_m"])) else None


def measure(fr, V0, controls, G, dm, pl):
    """측정(표본 안 판정 없음) — 전방 FF2 (b)(g) 의 표본 안 짝 · β̂(전방에서 고정해 쓸 값)."""
    import eg30plus as E
    import qbatch_run as QR
    ex = fr["ex"]
    d = QR.dbeta(fr, V0, G)
    raw = ex - V0["ex"]
    out = {"beta_hat": {"rule": QR.sleeve_beta(fr), "V0": QR.sleeve_beta(V0)},
           "X": {"mean": float(ex.mean()), "nw_t": E.nw_t(ex)},
           "dbeta_all": {"mean": float(d.mean()), "nw_t": E.nw_t(d)},
           "dbeta_down": {"mean": float(d[dm].mean()) if dm.any() else None, "down_t": E.down_t(d, dm), "n_down": int(dm.sum())},
           "raw_vs_V0": {"mean": float(raw.mean()), "down_mean": float(raw[dm].mean()) if dm.any() else None},
           "both_side": _both_side(ex, fr["hold"]), "turn": fr.get("turn"), "turn_V0": V0.get("turn"), "vs": {}}
    for c, frc in controls.items():
        if c in ("V0", "V0_20"):
            continue
        x = ex - frc["ex"]
        out["vs"][c] = {"mean": float(x.mean()), "nw_t": E.nw_t(x), "down_mean": float(x[dm].mean()) if dm.any() else None}
    P = pl.get("random")
    if P:
        out["placebo_pct"] = {"all": float(np.mean(np.array(P["draws"]) <= P["true"])),
                              "down": (float(np.mean(np.array(P["draws_down"]) <= P["true_down"])) if P["true_down"] is not None else None)}
    return out


def _placebo(ctx, view, C, V0, G, dm, nperm, fr):
    import qbatch_run as QR
    t0 = time.time()
    d0 = QR.dbeta(fr, V0, G)
    draws, draws_dn, h0 = [], [], None
    for i in range(nperm):
        Ti = placebo_targets(view, C, i)
        if i == 0:
            h0 = thash(Ti)
        fri = ctx.stock_fr(Ti, reb=3)
        d = QR.dbeta(fri, V0, G)
        draws.append(float(d.mean()))
        draws_dn.append(float(d[dm].mean()) if dm.any() else None)
        del fri
    dd = [x for x in draws_dn if x is not None]
    return {"draws": draws, "draws_down": draws_dn, "true": float(d0.mean()), "true_down": float(d0[dm].mean()) if dm.any() else None,
            "p95": float(np.percentile(draws, 95)) if draws else None, "p95_down": float(np.percentile(dd, 95)) if dd else None,
            "stat": "측정만(판정 아님) · Δβ(뽑기 − V0) 전 월 평균(draws) · 하락월 평균(draws_down) · 뽑기 = 편입마다 규칙이 뺄 수 있었던 "
                    "이름(상위 30 의 on·off)에서 균등 무작위 n_r 를 빼고 Eg 차순위로 채움 · 씨앗 default_rng(SEED + i)",
            "n": nperm, "SEED": SEED, "hash0": (h0 or "")[:16], "sec": round(time.time() - t0, 1)}


def _empty(code, why, f0=None, log=None, cls="M"):
    return {"code": code, "cls": cls, "stage": "S", "fr": None, "fr_pr": None, "fr20": None, "controls": {}, "arms": {}, "placebo": {},
            "perm": None, "g4": {}, "label_caps": {}, "f0": f0 or {"ok": False, "why": why}, "targets_hash": None,
            "log": dict(log or {}, skipped_returns=why)}


def run(ctx, bundle=None, nperm=NPERM, external=None, allow_override=False, cards=None):
    """Stage S 한 번 굽기 → {카드: CardResult}. 🚨 실제 표지면 RBATCH_COMMIT 없이는 멈춘다. 결과 값을 찍지 않는다.
    external = {이름: {편입월: [티커]}}(자카드만 · 예: {"Q07": q07_lists(ctx)["lists"]}) · allow_override 는 load_bundle 로(선언 ⑮).
    cards(2026-09-26 · 배치 S 재사용) = None(모듈 CARDS · 종전과 비트까지 같은 결과 — selftest run_cards_default_identical) ·
    코드 목록 · {코드: 명세}(_specs · 편입 카드 = freq 'Q' · 매월 사건 카드 = freq 'M' · 쌓은 카드는 명세 parts 로 부분 카드를 적는다 —
    적지 않으면 코드가 R12-STACK 일 때만 종전대로 R1 · R2)."""
    t0 = time.time()
    specs = _specs(cards)
    qcodes = _qcodes(specs)
    if bundle is None:
        bundle = load_bundle(View(ctx.Wd, None), allow_override=allow_override)
    commit = _guard(bundle)
    view = View(ctx.Wd, bundle["im"])
    B = build(view, bundle, external, cards=specs)
    if B["v0_hash"] != thash(ctx.V0_targets):
        raise SystemExit("🚨 V0 구성 재현 실패 — weights(Eg 앞 30) 해시가 ctx.V0_targets 와 다르다")
    if commit is not None:   # 실제 굽기 — 등록된 대조가 하나라도 없으면 수익을 계산하기 전에 멈춘다(조용히 대조를 잃지 않는다)
        for code in qcodes:
            C = B["cards"].get(code)
            if C is None or not C["f0"]["ok"]:
                continue
            miss = {c: K.get("unavailable") for c, K in C["controls"].items() if K.get("T") is None}
            if miss:
                raise SystemExit("🚨 %s 등록된 대조가 없다 %s — 자료를 채우고 다시(수익을 계산하지 않았다)" % (code, miss))
    V0, V0_20 = ctx.V0(), ctx.V0(cost=COST20)
    G = ctx.G
    hold = V0["hold"]
    dset = set(G.down_months(hold))
    dm = np.array([h in dset for h in hold])
    out, f0ok = {}, {}
    for code in qcodes:
        spec = specs[code]
        C = B["cards"].get(code)
        if C is None:
            out[code] = _empty(code, "표지 자료 없음(%s)" % "·".join(f for f in spec["flags"] if bundle.get(f) is None))
            f0ok[code] = False
            continue
        lg = card_log(C, code)
        f0 = dict(C["f0"])
        pts = spec.get("parts") or (("R1-OPPSELL", "R2-LAZYRF") if code == "R12-STACK" else None)
        if pts:
            parts = all(f0ok.get(c) for c in pts)
            f0 = dict(f0, ok=parts, own_rule="없음(보고만)", why="두 카드가 모두 F0 를 넘을 때만 잰다(선언 ④)")
        f0ok[code] = f0["ok"]
        if not f0["ok"]:
            out[code] = _empty(code, "F0 미달 — 측정 불가(수익을 계산하지 않았다)", f0=f0, log=lg)
            out[code]["targets_hash"] = C["hash"]
            continue
        t1 = time.time()
        T = C["T"]
        fr = ctx.stock_fr(T, reb=3)
        fr_pr, fr20 = ctx.stock_fr(T, reb=3, basis="PR"), ctx.stock_fr(T, reb=3, cost=COST20)
        if fr["hold"] != hold:
            raise SystemExit("🚨 %s 보유월이 V0 와 다르다" % code)
        controls = {"V0": V0, "V0_20": V0_20}
        for c, K in C["controls"].items():
            if K.get("T") is not None:
                controls[c] = ctx.stock_fr(K["T"], reb=3)
        pl = {}
        if spec["placebo"]:
            pl["random"] = _placebo(ctx, view, C, V0, G, dm, nperm, fr)
        lg["measured"] = measure(fr, V0, controls, G, dm, pl)
        lg["placebo"] = {k: {kk: v[kk] for kk in ("n", "SEED", "hash0", "sec")} for k, v in pl.items()}
        lg["sec"] = round(time.time() - t1, 1)
        lg["commit"] = commit
        lg["src"] = {f: B["src"].get(f) for f in spec["flags"]}
        out[code] = {"code": code, "cls": "M", "stage": "S", "fr": fr, "fr_pr": fr_pr, "fr20": fr20, "controls": controls, "arms": {},
                     "placebo": pl, "perm": None, "g4": {}, "label_caps": {}, "f0": f0, "targets_hash": C["hash"], "log": lg}
    for mcode in (c for c, sp in specs.items() if sp.get("freq") == "M"):   # 매월 사건 카드(기본 = R5-ALARM 하나 · 종전 그대로)
        R5 = B["cards"].get(mcode)
        mflags = "·".join(specs[mcode]["flags"])
        if R5 is None:
            out[mcode] = _empty(mcode, "표지 자료 없음(%s)" % mflags, cls="count")
        else:
            out[mcode] = {"code": mcode, "cls": "count", "stage": "S", "fr": None, "fr_pr": None, "fr20": None, "controls": {},
                          "arms": {}, "placebo": {}, "perm": None, "g4": {}, "label_caps": {},
                          "f0": {"ok": True, "why": "카드에 F0 없음 · 표본 안은 사건 수만(수익 없음 · 시도 수에 더하지 않는다)"},
                          "targets_hash": R5["hash"],
                          "log": {"counts": R5["counts"], "arm": R5["arm"], "formations": R5["rec"],
                                  "src": B["src"].get(specs[mcode]["flags"][0]),
                                  "note": "V0 + R5 매월 팔 목표(전방 원장용) — 표본 안 수익은 계산하지 않는다(카드)."}}
    out["_meta"] = {"sec": round(time.time() - t0, 1), "v0_hash": B["v0_hash"], "forms": len(B["forms"]), "nperm": nperm, "SEED": SEED,
                    "C1_SEED": C1_SEED, "commit": commit}
    return out


# ════════════════════════════════════════════════════════════════════════
# 구성 점검 — 규칙 뜻 · 대조 · 위약 · 점 시점(수익 없음 · selftest 와 --construct 가 같이 쓴다)
# ════════════════════════════════════════════════════════════════════════
def check_card(view, bundle, C, n_draws=2):
    """카드 한 판의 구성 뜻을 독립 계산과 맞춘다 → 위반 목록(빈 목록이 통과)."""
    bad = []
    flags = C["flags"]
    for r in C["forms"]:
        S = C["state"][r]
        ranked, st, top = S["ranked"], S["st"], S["top"]
        # 상태를 다시 센다(combine 없이 — 표지마다 직접)
        for x in ranked[:N_TOP + 40]:
            sts = [status_one(view, bundle[f], x, r) for f in flags]
            exp = "on" if "on" in sts else ("unres" if "unres" in sts else ("unk" if "unk" in sts else ("fpi" if "fpi" in sts else "off")))
            if st[x] != exp:
                bad.append(("status", r, x[0]))
        exp_drop = [x for x in top if st[x] == "on"]
        if S["drop"] != exp_drop:
            bad.append(("drop", r))
        exp_fill = [x for x in ranked[N_TOP:] if st[x] in FILL_OK][:len(exp_drop)]
        if S["fill"] != exp_fill:
            bad.append(("fill", r))
        picks = [x for x in top if st[x] != "on"] + exp_fill
        tg = C["T"][r]
        if set(tg["w"]) != {x[1] for x in picks}:
            bad.append(("picks", r))
        if any(st[x] == "on" for x in picks):
            bad.append(("on_in_picks", r))
        if any(x not in picks for x in top if st[x] in ("fpi", "unres", "unk")):
            bad.append(("kept_unfilterable", r))
        s = sum(tg["w"].values())
        if abs(s - 1) > 1e-9 or min(tg["w"].values()) < 0 or max(tg["w"].values()) > CAP + 1e-9:
            bad.append(("weights", r, s))
        if len(tg["w"]) != N_TOP - S_short(C, r):
            bad.append(("count", r, len(tg["w"])))
        pool = S["droppable"]
        on_rule = [x for x in pool if st[x] == "on"]
        for c, K in C.get("controls", {}).items():
            if K.get("T") is None:
                continue
            d = K["drop"][r]
            n_exp = min(S["n_r"], len(pool) - len(on_rule)) if K["kind"] == "set" else S["n_r"]
            if len(d) != n_exp or len(set(d)) != len(d) or any(x not in pool for x in d):
                bad.append(("ctrl_count", c, r))
            if K["kind"] == "pos":
                sf = score_fn(view, bundle, K["arg"])
                sc = {x: sf(x, r) for x in pool}
                posn = sorted([x for x in pool if sc[x] is not None and sc[x] == sc[x] and sc[x] > 0], key=lambda x: (-sc[x], pool.index(x)))
                k = min(len(posn), S["n_r"])
                if d[:k] != posn[:k] or any(x in set(posn) for x in d[k:]):
                    bad.append(("c2_order", c, r))
                if K["n_nosale"][r] != len(d) - k:
                    bad.append(("c2_nosale", c, r))
            if K["kind"] in ("hi", "lo"):
                sf = score_fn(view, bundle, K["arg"])
                vals = [(sf(x, r), j, x) for j, x in enumerate(pool)]
                have = sorted([v for v in vals if v[0] is not None and v[0] == v[0]], key=lambda v: ((-v[0]) if K["kind"] == "hi" else v[0], v[1]))
                none = [v for v in vals if v[0] is None or v[0] != v[0]]
                exp = [v[2] for v in have + none][:S["n_r"]]
                if d != exp:
                    bad.append(("ctrl_order", c, r))
            if K["kind"] == "set":
                if any(x in on_rule for x in d):
                    bad.append(("c1_overlap_rule", r))
                on = [x for x in pool if status_one(view, bundle[K["arg"]], x, r) == "on" and x not in on_rule]
                if len(on) >= S["n_r"] and any(x not in on for x in d):
                    bad.append(("c1_not_rs", r))
                if len(on) < S["n_r"] and any(x not in d for x in on):
                    bad.append(("c1_missing_rs", r))
                if K["c1_overlap"][r] != 0 or K["c1_short"][r] != S["n_r"] - len(d) or K["cand_n"][r] != len(on):
                    bad.append(("c1_log", r))
            if set(K["T"][r]["w"]) != {x[1] for x in replace_top(ranked, N_TOP, d, _all)["picks"]}:
                bad.append(("ctrl_picks", c, r))
    for i in range(n_draws):
        a, b = placebo_drops(view, C, i), placebo_drops(view, C, i)
        if a != b:
            bad.append(("placebo_repro", i))
        for r in C["forms"]:
            S = C["state"][r]
            if len(a[r]) != S["n_r"] or any(x not in S["droppable"] for x in a[r]):
                bad.append(("placebo_count", i, r))
        Ta = placebo_targets(view, C, i)
        for r in C["forms"]:
            if set(Ta[r]["w"]) != {x[1] for x in replace_top(C["state"][r]["ranked"], N_TOP, a[r], _all)["picks"]}:
                bad.append(("placebo_picks", i, r))
    return bad


def S_short(C, r):
    return next(row["short"] for row in C["rec"] if row["r"] == r)


def pit_check(view, bundle, flags, forms, cuts, seed=5):
    """점 시점 — cut 뒤 달의 표지를 모두 바꿔도 cut 이하 편입의 목표가 그대로여야 한다 → 어긋난 (cut, 편입) 목록."""
    rng = np.random.default_rng(seed)
    base = stage_s(view, bundle, flags, forms)
    gids = bundle["im"].gids()
    bad = []
    for cut in cuts:
        b2 = dict(bundle)
        for f in flags:
            b2[f] = bundle[f].perturbed_after(cut, rng, 0.3, gids)
        alt = stage_s(view, b2, flags, forms)
        for r in forms:
            if r <= cut and thash(alt["T"][r]) != thash(base["T"][r]):
                bad.append((cut, r))
        changed = sum(1 for r in forms if r > cut and thash(alt["T"][r]) != thash(base["T"][r]))
        if not changed and any(r > cut for r in forms):
            bad.append((cut, "교란이 뒤 편입을 하나도 바꾸지 않았다(시험이 약하다)"))
    return bad


# ════════════════════════════════════════════════════════════════════════
# 합성 세계(시험 전용 — 실제 자료 없음)
# ════════════════════════════════════════════════════════════════════════
class SynthWorld:
    """eg30plus.World 가 구성·경로에 내주는 것만 흉내 낸다(score · mcap · raw('mom') · fp_beta · sector · PX · me · months · RF ·
    IX_TR/IX_PR · sleeve(qg_lab.World.sleeve 그대로 빌림) · weights(목표 끼워 넣기)). 가격·Eg 는 난수다."""

    def __init__(self, seed=7, n=90, d0="2015-06-01", d1="2019-12-31", f0="2016-08", f1="2019-07"):
        import qg_lab as QL
        self._QL = QL
        rng = np.random.default_rng(seed)
        d, end, dates = dt.date.fromisoformat(d0), dt.date.fromisoformat(d1), []
        while d <= end:
            if d.weekday() < 5:
                dates.append(d.isoformat())
            d += dt.timedelta(days=1)
        self.dates, self.D = dates, len(dates)
        self.di = {s: i for i, s in enumerate(dates)}
        self.me = {}
        for i, s in enumerate(dates):
            self.me[s[:7]] = i
        self.months = Q.months_between(f0, f1)
        T = len(dates)
        mr = rng.normal(0.0003, 0.01, T)
        mr[0] = 0.0
        self.IX_PR = 100.0 * np.exp(np.cumsum(mr))
        self.IX_TR = self.IX_PR * np.exp(np.arange(T) * 0.00006)
        self.tick = ["S%02d" % j for j in range(n)]
        self.tick[17] = "SX-B"                                    # 명단 '-' · 지도 '.' 표기 시험
        self.beta_ = {}
        self.PX, self.shares, self.sec = {}, {}, {}
        secs = ("Information Technology", "Health Care", "Industrials", "Consumer Discretionary", "Energy", "Materials")
        for j, t in enumerate(self.tick):
            b = float(rng.uniform(0.6, 1.5))
            r = b * mr + rng.normal(0.0, 0.015, T)
            p = 20.0 * np.exp(np.cumsum(r))
            if j == 7:                                            # 늦은 상장(그 전은 가격 없음 → 명단 밖)
                p[: self.di["2017-03-01"]] = np.nan
            self.PX[t] = p
            self.shares[t] = float(rng.uniform(1e8, 5e9)) * (60.0 if j in (0, 1) else 1.0)   # 초대형 둘 — 20% 상한이 실제로 걸리게
            self.beta_[t] = None if j == 21 else b                # 베타 없는 이름(순서 대조의 «없음은 뒤» 시험)
            self.sec[t] = secs[j % len(secs)]
        z = rng.normal(0.0, 1.0, n)
        self.eg = {}
        for m in sorted(self.me):
            z = 0.8 * z + 0.6 * rng.normal(0.0, 1.0, n)
            self.eg[m] = {t: float(v) for t, v in zip(self.tick, z)}
        self.RF = {m: 0.001 for m in self.me}
        self._raw = {}

    def score(self, cand, m):
        i = self.me[m]
        vals = {(t, t): v for t, v in self.eg[m].items() if self.mcap(t, t, i)}
        pr = self._QL.pct_rank(vals)
        return sorted(pr.items(), key=lambda kv: (-kv[1], kv[0][0]))

    def mcap(self, t, k, i):
        p = self.PX[k][i]
        return float(p * self.shares[k]) if (p == p and p > 0) else None

    def raw(self, sig, m, index="spx", ex_fin=True, egv="frozen"):
        if sig != "mom":
            raise ValueError(sig)
        if m not in self._raw:
            i = self.me[m]
            out = {}
            for t in self.tick:
                p = self.PX[t]
                if i >= 252 and p[i] == p[i] and p[i - 21] == p[i - 21] and p[i - 252] == p[i - 252]:
                    out[(t, t)] = float(p[i - 21] / p[i - 252] - 1.0)
            self._raw[m] = out
        return self._raw[m]

    def fp_beta(self, k, i):
        return self.beta_[k]

    def sector(self, t, k, m):
        return self.sec[t]

    def weights(self, cand, m):
        tg = cand["targets"][m]
        return dict(tg["w"]), dict(tg["names"])

    def sleeve(self, cand):
        return self._QL.World.sleeve(self, cand)


class SynthCtx(Q.Ctx):
    """합성 세계 위의 qbatch_core.Ctx — V0_targets 는 eg30plus.v0_targets(랩 함수 그대로)가 합성 세계에서 만든다."""

    def __init__(self, Wd):
        super().__init__()
        self._Wd = Wd
        self._G = Q.Grid.from_world(Wd)

    def dmask(self, hold):
        dset = set(self._G.down_months(hold))
        return np.array([h in dset for h in hold])


def synth_issuer_map(Wd):
    """합성 지도(tm_format 모양) — FPI 둘 · 모름 하나 · 달 중간 그룹 바뀜 하나 · 미해결 하나 · '.' 표기 하나."""
    tm = {}
    for j, t in enumerate(Wd.tick):
        key = t.replace("-", ".")
        fpi = 1 if j in (3, 11) else (None if j == 5 else 0)
        if j == 9:
            tm[key] = [["2014-06", "2017-06", "g9a", 9009, [9009], 0, "synth", 0], ["2017-07", "2026-09", "g9b", 9010, [9010], 0, "synth", 0]]
        elif j == 13:
            tm[key] = [["2014-06", "2026-09", None, None, [], None, "unresolved", None]]
        else:
            tm[key] = [["2014-06", "2026-09", "g%d" % j, 1000 + j, [1000 + j], fpi, "synth", 0]]
    return IssuerMap({"tm": tm}, {"path": "synthetic"})


# ════════════════════════════════════════════════════════════════════════
# selftest — 합성만
# ════════════════════════════════════════════════════════════════════════
def selftest() -> dict:
    t0 = time.time()
    import eg30plus as E
    import qbatch_run as QR
    t = {}
    # 1 replace_top — 형제 정본(r_r1_flags.replace_top · r_r2flags.fill_top)과 같은 뜻인가
    rng = np.random.default_rng(1)
    par, par2 = True, True
    try:
        import r_r1_flags as R1F
    except Exception:
        R1F = None
    try:
        import r_r2flags as R2F
    except Exception:
        R2F = None
    for _ in range(300):
        L = list(range(int(rng.integers(30, 70))))
        rng.shuffle(L)
        drop = [x for x in L[:30] if rng.random() < 0.2]
        okset = {x for x in L if rng.random() < 0.8}
        a = replace_top(L, 30, drop, lambda x: x in okset)
        if R1F is not None:
            par &= a == R1F.replace_top(L, 30, drop, lambda x: x in okset)
        if R2F is not None:
            ex = set(drop) | (set(L[30:]) - okset)
            b = replace_top(L, 30, drop, lambda x: x not in ex)
            fb, db = R2F.fill_top(L, ex, 30)
            par2 &= (b["picks"] == fb and b["dropped"] == db)
    t["replace_top_parity_r1flags"] = bool(par) if R1F is not None else "r_r1_flags 없음"
    t["replace_top_parity_r2flags_fill_top"] = bool(par2) if R2F is not None else "r_r2flags 없음"
    # 합성 세계 · 문맥
    Wd = SynthWorld()
    ctx = SynthCtx(Wd)
    im = synth_issuer_map(Wd)
    view = View(Wd, im)
    forms = view.forms()
    t["forms"] = len(forms)
    months = Q.months_between(Q.mshift(Wd.months[0], -3), Wd.months[-1])
    # 2 표지 0 → V0 와 비트까지 같다(랩 eg30plus.v0_targets 가 합성 세계에서 만든 것과)
    Z = zero_bundle(im)
    BZ = build(view, Z)
    h0 = thash(ctx.V0_targets)
    t["v0_rebuild_hash_eq"] = BZ["v0_hash"] == h0
    t["cap_binds_somewhere"] = any(abs(max(tg["w"].values()) - CAP) < 1e-12 for tg in ctx.V0_targets.values())   # 상한 시험이 헛돌지 않게
    for code in QCARDS:
        t["zero_%s_hash_eq_V0" % code] = BZ["cards"][code]["hash"] == h0 and BZ["cards"][code]["T"] == ctx.V0_targets
    r5z = BZ["cards"]["R5-ALARM"]
    t["zero_R5_forms_eq_V0"] = all(r5z["T"][r] == ctx.V0_targets[r] for r in forms)
    t["zero_R5_no_swaps"] = r5z["arm"]["swaps"] == 0
    # 3 합성 표지 — 규칙 · 대조 · 위약 뜻을 독립 계산과
    S = synth_bundle(im, months, seed=11)
    B = build(view, S)
    for code in QCARDS:
        bad = check_card(view, S, B["cards"][code])
        t["check_%s" % code] = bad == []
        if bad:
            t["check_%s_viol" % code] = bad[:8]
    c1 = B["cards"]["R1-OPPSELL"]
    t["R1_n_r_median"] = c1["f0"]["median_n_r"]
    t["R2_n_r_median"] = B["cards"]["R2-LAZYRF"]["f0"]["median_n_r"]
    t["R1_some_drops"] = sum(row["n_r"] for row in c1["rec"]) > 0
    t["R1_fpi_count_eq_map"] = all(row["n_fpi_top"] == sum(1 for x in c1["state"][row["r"]]["top"] if im.who(x[0], row["r"])[1] == 1)
                                   for row in c1["rec"])
    t["R1_fpi_top_total"] = sum(row["n_fpi_top"] for row in c1["rec"])
    # 4 창 — OS 는 r−2..r · r−3 은 안 센다 · 티커의 그룹이 바뀌면 앞 그룹 표지가 옮겨 오지 않는다
    fs = FlagSource("OS", "synthetic", {"2017-04": {"g1"}}, window=3)
    t["window_r_minus_2"] = fs.active("g1", "2017-06") == 1 and fs.active("g1", "2017-07") == 0 and fs.active("g1", "2017-04") == 1
    fs2 = FlagSource("OS", "synthetic", {"2017-06": {"g9a"}}, window=3)
    t["group_switch_no_carry"] = (status_one(view, fs2, ("S09", "S09"), "2017-06") == "on"
                                  and status_one(view, fs2, ("S09", "S09"), "2017-08") == "off")
    fs3 = FlagSource("OS", "synthetic", {}, unk={"2017-05": {"g1"}}, window=3)
    t["unknown_in_window"] = fs3.active("g1", "2017-06") is None and fs3.active("g1", "2017-08") == 0
    fs4 = FlagSource("OS", "synthetic", {"2017-05": {"g1"}}, months_ok=["2017-05", "2017-06"], window=3)
    t["months_ok_edge"] = fs4.active("g1", "2017-06") == 1 and fs4.active("g1", "2017-09") is None
    t["dot_dash_lookup"] = view.who("SX-B", "2018-01")[0] == "g17"
    t["fpi_status"] = status_one(view, S["OS"], ("S03", "S03"), "2018-03") == "fpi" and status_one(view, S["OS"], ("S13", "S13"), "2018-03") == "unres"
    # 5 점 시점 — cut 뒤 표지를 바꿔도 cut 이하 편입은 그대로
    t["pit_R1"] = pit_check(view, S, ("OS",), forms, [forms[3], forms[7]]) == []
    t["pit_STACK"] = pit_check(view, S, ("OS", "CH"), forms, [forms[5]]) == []
    # 6 쌓은 팔 = 합집합
    st = B["cards"]["R12-STACK"]
    ok = True
    for r in forms:
        top = st["state"][r]["top"]
        u = [x for x in top if status_one(view, S["OS"], x, r) == "on" or status_one(view, S["CH"], x, r) == "on"]
        ok &= st["state"][r]["drop"] == u
        ok &= all(status_one(view, S["OS"], x, r) in FILL_OK and status_one(view, S["CH"], x, r) in FILL_OK for x in st["state"][r]["fill"])
    t["stack_union"] = bool(ok)
    # 7 위약 — 씨앗 규약 default_rng(SEED + i) 를 밖에서 다시 재현 · 뽑기마다 다르다
    r_ = np.random.default_rng(SEED + 3)
    exp = {r: pick_random(c1["state"][r]["droppable"], c1["state"][r]["n_r"], r_) for r in forms}
    t["placebo_seed_convention"] = placebo_drops(view, c1, 3) == exp
    t["placebo_draws_differ"] = thash(placebo_targets(view, c1, 0)) != thash(placebo_targets(view, c1, 1))
    t["placebo_n_r_zero_V0"] = all(thash(placebo_targets(view, BZ["cards"]["R1-OPPSELL"], i)) == h0 for i in (0, 1))
    # 8 대조 — C1 은 RS 먼저 · 순서 대조의 «없음은 뒤»(합성 베타 없는 이름 S21)
    t["C1_seed_stream"] = control(view, S, c1, "set", "RS")["hash"] == c1["controls"]["C1"]["hash"]
    pool = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]
    sc = {"A": 1.0, "B": None, "C": 3.0, "D": 3.0}
    t["pick_ordered_ties_none"] = (pick_ordered(pool, lambda x: sc[x[0]], 3) == [("C", "C"), ("D", "D"), ("A", "A")]
                                   and pick_ordered(pool, lambda x: sc[x[0]], 4, hi=False)[-1] == ("B", "B"))
    rr = np.random.default_rng(0)
    t["pick_set_short"] = set(pick_set(pool, [("B", "B")], 3, rr)) >= {("B", "B")} and len(pick_set(pool, [("B", "B")], 3, rr)) == 3
    # 9 R5 매월 — 경보가 달 중간에 걸리면 그 이름만 팔고 채운다 · 나머지는 흘러간 비중 그대로
    f_ = forms[2]
    mid = Q.mshift(f_, 1)
    v0f = ctx.V0_targets[f_]
    res_ = [k for k in v0f["w"] if im.who(v0f["names"][k], mid)[0] and im.who(v0f["names"][k], mid)[1] != 1]
    k_big = max(res_, key=lambda k: v0f["w"][k])
    g_big = im.who(v0f["names"][k_big], mid)[0]
    A5 = dict(Z)
    A5["ALARM"] = FlagSource("ALARM", "synthetic", {mid: {g_big}})
    R5 = build_r5(view, A5, forms, BZ["V0"])
    wd = drift(view, v0f["w"], view.me[f_], view.me[mid])
    tg = R5["T"][mid]
    kept = [k for k in wd if k != k_big]
    t["r5_swap_only_alarmed"] = (k_big not in tg["w"] and all(k in tg["w"] for k in kept) and len(tg["w"]) == len(wd)
                                 and abs(sum(tg["w"].values()) - 1) < 1e-12 and mid not in forms)
    ratio = [tg["w"][k] / wd[k] for k in kept]
    t["r5_kept_drift"] = max(ratio) - min(ratio) < 1e-12 and min(ratio) >= 1 - 1e-12     # 흘러간 비중 그대로(채움이 상한에 걸리면 같은 배율로만 는다)
    t["r5_counts"] = R5["counts"]["flagged"] == 1 and R5["arm"]["swaps"] == 1 and R5["counts"]["by_month"] == {mid: [v0f["names"][k_big]]}
    t["r5_next_month_drift_only"] = Q.mshift(mid, 1) not in forms and set(R5["T"][Q.mshift(mid, 1)]["w"]) == set(tg["w"])
    t["r5_fill_weights_cap"] = (lambda w, rem: abs(sum(w.values()) + rem - 0.5) < 1e-12 and max(w.values()) <= 0.2 + 1e-12)(
        *_fill_weights({"a": 10.0, "b": 1.0, "c": 1.0}, 0.5, 0.2))
    # 10 R5 표지 0 매월 경로 = V0 경로(합성 가격 · 흘러간 비중이 매매를 만들지 않는다)
    frv = ctx.V0()
    fr5 = ctx.stock_fr(r5z["T"], reb=1)
    t["r5_zero_path_eq_V0"] = float(np.max(np.abs(fr5["ex"] - frv["ex"]))) < 1e-9
    # 11 어댑터 — cikmonth · 덮어쓰기 · r2 gm
    doc = {"months_ok": ["2017-01", "2017-02", "2017-03"],
           "groups": {"g1": {"2017-01": {"O": 2, "R": 0, "usd_all": 5e6}, "2017-02": {"O": 0, "R": 1, "N": 0}},
                      "g2": {"2017-02": {"O": 0, "R": 0, "N": 1, "os_na": 1, "rs_na": 1}}}}
    o, r, usd = fs_from_cikmonth(doc, kind="synthetic")
    t["adapter_cikmonth"] = (o.dummy("g1", "2017-01") == 1 and o.dummy("g1", "2017-02") == 0 and r.dummy("g1", "2017-02") == 1
                             and o.dummy("g2", "2017-02") is None and o.dummy("g3", "2017-03") == 0 and o.dummy("g1", "2017-04") is None
                             and usd[("g1", "2017-01")] == 5e6)
    # 덮어쓰기 months_ok — r_p0_adapt._override_defined 와 같은 세 모양(검토 수정 · 최상위 목록이 달 밖을 None 으로)
    cards_ = {"R1-OPPSELL": {"OS": {"2017-01": ["g1"]}}, "R5-ALARM": {"ALARM": {"2017-02": ["g4"]}}}
    ovT = {"cards": cards_, "months_ok": ["2017-01", "2017-02"]}
    ovC = {"cards": cards_, "months_ok": {"R1-OPPSELL": ["2017-01", "2017-02"]}}
    ovD = {"cards": cards_, "months_ok": {"R1-OPPSELL": {"OS": ["2017-01", "2017-02"]}}}
    ovN = {"cards": cards_}
    okk = True
    for ov_ in (ovT, ovC, ovD):
        a1 = fs_from_override(ov_, "OS", kind="synthetic")
        okk &= (a1.dummy("g1", "2017-01") == 1 and a1.dummy("g1", "2017-02") == 0 and a1.dummy("g1", "2017-05") is None
                and a1.info["months_ok_given"] is True)
    a1n, a5 = fs_from_override(ovN, "OS", kind="synthetic"), fs_from_override(ovT, "ALARM", kind="synthetic")
    t["adapter_override"] = (okk and a1n.months_ok is None and a1n.info["months_ok_given"] is False and a5.dummy("g4", "2017-02") == 1
                             and a5.dummy("g4", "2017-05") is None and fs_from_override(ovT, "CH") is None)
    P0A = _p0a()
    if P0A is not None and hasattr(P0A, "_override_defined"):
        shapes = (ovT, ovC, ovD, ovN, {"cards": cards_, "months_ok": {"R1-OPPSELL": {"RS": ["2017-01"]}}}, {"months_ok": "x"})
        t["override_defined_parity_r_p0_adapt"] = all(
            _override_defined_local(o_, c_, d_) == P0A._override_defined(o_, c_, d_)
            for o_ in shapes for c_, d_ in (("R1-OPPSELL", "OS"), ("R1-OPPSELL", "RS"), ("R5-ALARM", "ALARM")))
        t["window_defined_parity_r_p0_adapt"] = all(
            window_defined(pm) == P0A.window_defined(pm)
            for pm in ({"2016-03", "2016-01", "2017-11", None, "junk"}, set(), {"2020-05"}, set(Q.months_between("2014-02", "2016-12"))))
    else:
        t["override_defined_parity_r_p0_adapt"] = "r_p0_adapt 없음"
    gm = {("g1", "2017-05"): {"ch": 1, "miss": 0, "sim": 0.5, "dlog_raw": 0.2}, ("g2", "2017-05"): {"ch": 0, "miss": 1, "sim": None, "dlog_raw": None}}
    ch, mi, sd, dl = fs_from_r2(gm, {("g1", "2017-05"): {"sim": 0.91}}, kind="synthetic")
    t["adapter_r2gm"] = (ch.dummy("g1", "2017-05") == 1 and ch.dummy("g2", "2017-05") == 0 and mi.dummy("g2", "2017-05") == 1
                         and sd[("g1", "2017-05")] == 0.91 and dl[("g1", "2017-05")] == 0.2 and ("g2", "2017-05") not in dl)
    # 12 끝에서 끝까지 — 합성 세계 run() → CardResult 모양 · qbatch_run.lite 가 읽는다
    out = run(ctx, S, nperm=4)
    shape_ok = True
    for code in QCARDS:
        R = out[code]
        shape_ok &= all(k in R for k in ("fr", "fr_pr", "fr20", "controls", "arms", "placebo", "g4", "f0", "log", "targets_hash"))
        if R["fr"] is not None:
            shape_ok &= R["fr"]["hold"] == frv["hold"] and R["targets_hash"] == B["cards"][code]["hash"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                QR.lite(R["fr"], ctx.G)
                for v in R["controls"].values():
                    QR.lite(v, ctx.G)
    t["run_shape"] = bool(shape_ok)
    t["run_R1_measured"] = out["R1-OPPSELL"]["fr"] is not None and "measured" in out["R1-OPPSELL"]["log"]
    t["run_placebo_n"] = len(out["R1-OPPSELL"]["placebo"].get("random", {}).get("draws", [])) == 4 if out["R1-OPPSELL"]["fr"] is not None else "F0"
    t["run_R2_controls"] = sorted(out["R2-LAZYRF"]["controls"]) == ["C2", "C3", "C4", "C5", "V0", "V0_20"] if out["R2-LAZYRF"]["fr"] is not None else "F0"
    t["run_R5_count_only"] = out["R5-ALARM"]["fr"] is None and out["R5-ALARM"]["cls"] == "count"
    # 12b cards= 인자(2026-09-26 · 배치 S 재사용) — 기본(None) · 명시 CARDS · 코드 목록이 비트까지 같다 · 부분 집합은 그 카드만 같다
    def _canon_run(o):
        o = {k: v for k, v in o.items() if k != "_meta"}
        return hashlib.sha256(json.dumps(o, sort_keys=True, default=_js, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _strip_sec(o):
        o = json.loads(json.dumps(o, default=_js, ensure_ascii=False))
        for v in o.values():
            if isinstance(v, dict) and isinstance(v.get("log"), dict):
                v["log"].pop("sec", None)
                for pv in (v.get("log") or {}).get("placebo", {}).values():
                    if isinstance(pv, dict):
                        pv.pop("sec", None)
            for pv in ((v or {}).get("placebo") or {}).values() if isinstance(v, dict) else ():
                if isinstance(pv, dict):
                    pv.pop("sec", None)
        return o
    o_def, o_exp, o_lst = (run(ctx, S, nperm=4), run(ctx, S, nperm=4, cards=dict(CARDS)), run(ctx, S, nperm=4, cards=list(CARDS)))
    h_def = _canon_run(_strip_sec(o_def))
    sub = run(ctx, S, nperm=4, cards={"R2-LAZYRF": CARDS["R2-LAZYRF"], "R5-ALARM": CARDS["R5-ALARM"]})
    t["run_cards_default_identical"] = (h_def == _canon_run(_strip_sec(out)) == _canon_run(_strip_sec(o_exp)) == _canon_run(_strip_sec(o_lst))
                                        and set(sub) - {"_meta"} == {"R2-LAZYRF", "R5-ALARM"}
                                        and sub["R2-LAZYRF"]["targets_hash"] == o_def["R2-LAZYRF"]["targets_hash"]
                                        and (sub["R2-LAZYRF"]["fr"] is None) == (o_def["R2-LAZYRF"]["fr"] is None)
                                        and (sub["R2-LAZYRF"]["fr"] is None
                                             or bool(np.array_equal(sub["R2-LAZYRF"]["fr"]["ex"], o_def["R2-LAZYRF"]["fr"]["ex"])))
                                        and _canon_run(_strip_sec({"R5-ALARM": sub["R5-ALARM"]}))
                                        == _canon_run(_strip_sec({"R5-ALARM": o_def["R5-ALARM"]})))
    oz = run(ctx, Z, nperm=2)
    t["run_zero_F0_blocks"] = (oz["R1-OPPSELL"]["fr"] is None and oz["R1-OPPSELL"]["f0"]["ok"] is False
                               and oz["R12-STACK"]["fr"] is None and oz["R1-OPPSELL"]["targets_hash"] == h0)
    # 표지 0 판의 경로가 V0 와 비트까지 같다(F0 를 비켜 목표만 태워 본다)
    fz = ctx.stock_fr(BZ["cards"]["R1-OPPSELL"]["T"], reb=3)
    t["zero_path_bit_eq_V0"] = bool(np.array_equal(fz["ex"], frv["ex"]))
    # 13 방화벽 — 실제 표지는 등록 커밋 없이 멈춘다
    old = os.environ.pop("RBATCH_COMMIT", None)
    R_ = dict(S)
    R_["OS"] = FlagSource("OS", "real", S["OS"].on, S["OS"].unk)
    try:
        run(ctx, R_, nperm=1)
        t["guard_real_blocks"] = False
    except SystemExit:
        t["guard_real_blocks"] = True
    finally:
        if old is not None:
            os.environ["RBATCH_COMMIT"] = old
    # 15 검토 수정 — C1 exclude · C2 pick_c2 가 형제 정본(r_r1_flags)과 같은 식인가(같은 씨앗 한 줄기로 여러 번 불러 소비까지)
    if R1F is not None and hasattr(R1F, "pick_c2"):
        rng = np.random.default_rng(5)
        p1, p2 = True, True
        for _ in range(200):
            n = int(rng.integers(5, 30))
            top = ["k%02d" % j for j in range(n)]
            cands = {k for k in top if rng.random() < 0.3}
            ex = {k for k in top if rng.random() < 0.25}
            sc_ = {k: (float(rng.normal()) if rng.random() < 0.7 else (0.0 if rng.random() < 0.5 else None)) for k in top}
            s0 = int(rng.integers(0, 10 ** 6))
            ra, rb, rc, rd = (np.random.default_rng(s0) for _ in range(4))
            for n_r in (int(rng.integers(0, 12)), 0, int(rng.integers(0, 12))):
                p1 &= pick_set(top, cands, n_r, ra, exclude=ex) == R1F.pick_set(top, cands, n_r, rb, exclude=ex)
                p2 &= pick_c2(top, sc_.get, n_r, rc) == R1F.pick_c2(top, sc_.get, n_r, rd)
        t["pick_set_parity_r1flags"] = bool(p1)
        t["pick_c2_parity_r1flags"] = bool(p2)
    else:
        t["pick_set_parity_r1flags"] = "r_r1_flags 없음"
    K1 = c1["controls"]["C1"]
    t["c1_no_overlap_with_rule"] = (all(v == 0 for v in K1["c1_overlap"].values())
                                    and all(x not in c1["state"][r]["drop"] for r in forms for x in K1["drop"][r]))
    K2 = c1["controls"]["C2"]
    t["c2_nosale_logged"] = set(K2["n_nosale"]) == set(forms) and all(v >= 0 for v in K2["n_nosale"].values())
    # C2 — 점수 0 · 없음은 순위에 들지 않는다(매도 없는 이름을 Eg 순서로 고르지 않는다)
    sz = {"A": 0.0, "B": 0.0, "C": 2.0, "D": None}
    rz = pick_c2([("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], lambda x: sz[x[0]], 3, np.random.default_rng(0))
    t["c2_zero_not_ranked"] = rz["picks"][0] == ("C", "C") and rz["n_nosale"] == 2 and len(set(rz["picks"])) == 3
    # 덮어쓰기 옵트인 · CH 덮어쓰기에도 정본 대조 자료 · 지문(.gz 는 푼 바이트 · 글은 CRLF→LF) — 임시 폴더의 합성 파일만
    import tempfile, gzip, shutil
    tmp = tempfile.mkdtemp(prefix="r_stages_st_")
    try:
        def _w(rel, obj):
            pth = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            with io.open(pth, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(obj, fh)
            return pth
        _w(FIELDS["issuer_map"]["file"], {"tm": {"S01": [["2014-06", "2026-09", "g1", 1001, [1001], 0, "synth", 0]]}})
        _w(FIELDS["override"]["file"], {"cards": {"R1-OPPSELL": {"OS": {"2017-01": ["g1"]}}, "R2-LAZYRF": {"CH": {"2017-05": ["g1"]}}},
                                        "months_ok": ["2017-01", "2017-05"]})
        _w(FIELDS["ins"]["file"], {"months_ok": ["2017-01", "2017-02"], "groups": {"g1": {"2017-02": {"O": 1, "R": 0, "usd_all": 1e6}}}})
        vw = View(Wd, im)
        b0 = load_bundle(vw, rdata=tmp)
        b1 = load_bundle(vw, rdata=tmp, allow_override=True)
        t["override_opt_in"] = (b0["src"]["override"]["used"] is False and b0["OS"].src.startswith("cikmonth")
                                and b0["OS"].dummy("g1", "2017-02") == 1 and b0["OS"].dummy("g1", "2017-01") == 0
                                and b1["src"]["override"]["used"] is True and b1["OS"].src.startswith("override")
                                and b1["OS"].dummy("g1", "2017-01") == 1 and b1["OS"].dummy("g1", "2017-03") is None
                                and b1["usd"] == {("g1", "2017-02"): 1e6} and b0["CH"] is None and b1["CH"] is not None
                                and "controls_warn" in b1["src"]["CH"] and b1["simdoc"] is None and b0["coverage"] is None)
        gzp = os.path.join(tmp, "x.json.gz")
        rawb = b'{"a":\r\n1}' + bytes(range(256)) * 4
        with open(gzp, "wb") as fh:
            fh.write(gzip.compress(rawb))
        txp = os.path.join(tmp, "y.json")
        with open(txp, "wb") as fh:
            fh.write(b'{"a":\r\n1}\r\n')
        t["sha_gz_raw_text_lf"] = (_sha_file(gzp) == hashlib.sha256(rawb).hexdigest()
                                   and _sha_file(txp) == hashlib.sha256(b'{"a":\n1}\n').hexdigest())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # ALARM 정의 달 — [첫 제출월 + 11, 끝 제출월] · 최상위 months_ok 가 있으면 그것
    mo_, _h = sub_months_ok({}, [{"fd": "2015-03-02"}, {"fd": "2017-06-30"}, {"fd": None}])
    mo2, _h2 = sub_months_ok({"months_ok": ["2016-01"]}, [])
    t["sub_months_ok"] = mo_[0] == "2016-02" and mo_[-1] == "2017-06" and mo2 == ["2016-01"] and sub_months_ok({}, [])[0] is None
    # F0 — 잴 수 있는 편입만(창이 정의 달 밖 · 지도 F0 · 커버리지 F0 인 편입은 중앙값에서 빠진다 · 구성은 그대로)
    start = forms[6]
    S2 = dict(S)
    S2["OS"] = FlagSource("OS", "synthetic", S["OS"].on, S["OS"].unk, [m for m in months if m >= start])
    b2 = stage_s(view, S2, ("OS",), forms)
    f2 = f0_stage_s(b2, S2, im)
    exp_ex = {r for r in forms if Q.mshift(r, -2) < start}
    rest = [row["n_r"] for row in b2["rec"] if row["r"] not in exp_ex]
    t["f0_excludes_undefined_window"] = (set(f2["excluded"]) == exp_ex and f2["median_n_r"] == float(np.median(rest))
                                         and all(row["n_r"] == 0 for row in b2["rec"] if row["r"] < start) and len(exp_ex) >= 6)
    bad_m = forms[9]
    imf = synth_issuer_map(Wd)
    imf.viol = {m: (0.05 if m == bad_m else 0.0) for m in months}
    S3 = dict(S)
    S3["coverage"] = [m for m in months if m != forms[11]]
    f3 = f0_stage_s(stage_s(view, S3, ("OS",), forms), S3, imf)
    t["f0_map_and_coverage"] = (set(f3["excluded"]) == {bad_m, forms[11]} and "지도" in f3["excluded"][bad_m][0]
                                and f3["excluded"][forms[11]] == ["커버리지 F0"] and f3["n_forms"] == len(forms) - 2)
    t["f0_no_table_no_gate"] = f0_stage_s(c1, S, im)["excluded"] == {} and im.has_f0() is False
    # 실제 굽기 — 등록된 대조가 없으면 수익 전에 멈춘다(합성 세계 · 등록 커밋 흉내)
    old_c = os.environ.get("RBATCH_COMMIT")
    os.environ["RBATCH_COMMIT"] = "selftest"
    R_ = dict(S)
    R_["OS"] = FlagSource("OS", "real", S["OS"].on, S["OS"].unk)
    R_["usd"] = None
    try:
        run(ctx, R_, nperm=1)
        t["guard_real_missing_control"] = False
    except SystemExit as e:
        t["guard_real_missing_control"] = "등록된 대조" in str(e)
    finally:
        if old_c is None:
            os.environ.pop("RBATCH_COMMIT", None)
        else:
            os.environ["RBATCH_COMMIT"] = old_c
    # 14 눈가린 연기 시험(합성)
    sm = Q.blind_smoke(run, ctx, S, nperm=2)
    t["blind_smoke"] = bool(sm["ok"]) and sm["shape"] is not None and "R1-OPPSELL" in sm["shape"]
    keys = [k for k, v in t.items() if isinstance(v, bool)]
    return {"ok": all(t[k] for k in keys), "tests": t, "failed": [k for k in keys if not t[k]], "sec": round(time.time() - t0, 1)}


# ════════════════════════════════════════════════════════════════════════
# --construct — 실제 세계(snap_wt) 위 구성 점검(수익 통계 없음)
# ════════════════════════════════════════════════════════════════════════
def construct(nperm_smoke=3, smoke=True, allow_override=False, q07=False):
    t0 = time.time()
    rep = {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "rdata": RDATA}
    ctx = Q.Ctx()
    im = IssuerMap.load()
    rep["issuer_map"] = im.src
    view = View(ctx.Wd, im)
    forms = view.forms()
    rep["forms"] = [forms[0], forms[-1], len(forms)]
    # 1 V0 재현 — 표지 0 이면 모든 분기 팔의 목표 해시가 ctx.V0_targets 와 같다
    Z = zero_bundle(im)
    BZ = build(view, Z)
    h0 = thash(ctx.V0_targets)
    rep["v0"] = {"V0_thash": h0, "rebuild_eq": BZ["v0_hash"] == h0,
                 **{code: BZ["cards"][code]["hash"] == h0 for code in QCARDS},
                 "R5_forms_eq": all(BZ["cards"]["R5-ALARM"]["T"][r] == ctx.V0_targets[r] for r in forms),
                 "R5_swaps": BZ["cards"]["R5-ALARM"]["arm"]["swaps"]}
    # V0 자신의 경로(표지 없음): R5 표지 0 매월 경로가 V0 경로와 얼마나 같은가(흘러간 비중이 매매를 만들지 않는지 · 값은 차이만)
    fv = ctx.V0()
    f5 = ctx.stock_fr(BZ["cards"]["R5-ALARM"]["T"], reb=1)
    rep["v0"]["R5_zero_monthly_path_gap_max_pp"] = float(np.max(np.abs(f5["ex"] - fv["ex"])))
    rep["v0"]["V0_fin_names"] = sum(1 for r in forms for k, t in ctx.V0_targets[r]["names"].items() if ctx.Wd.sector(t, k, r) == "Financials")
    # 2 형성일 = NYSE 규칙 달력의 그달 마지막 거래일(월 더미의 점 시점)
    try:
        import r_r2flags as R2
        cal = R2.Cal()
        mism = [(m, view.dates[view.me[m]], cal.month_end(m)) for m in view.months if view.dates[view.me[m]] != cal.month_end(m)]
        rep["calendar"] = {"months": len(view.months), "mismatch": mism[:10], "n_mismatch": len(mism),
                           "forms_mismatch": [x for x in mism if x[0] in set(forms)]}
    except Exception as e:
        rep["calendar"] = {"err": repr(e)[:200]}
    # 3 지도 — 순위 이름의 해결 · FPI(편입마다 상위 30)
    unres, fpi_top = 0, []
    for r in forms:
        top = view.ranked(r)[:N_TOP]
        unres += sum(1 for x in view.ranked(r) if not view.who(x[0], r)[0])
        fpi_top.append(sum(1 for x in top if view.who(x[0], r)[1] == 1))
    rep["issuer"] = {"ranked_unresolved_name_forms": unres, "fpi_top_min_med_max": [min(fpi_top), float(np.median(fpi_top)), max(fpi_top)],
                     "map_f0_table": im.has_f0(), "map_f0_bad_forms": [r for r in forms if im.has_f0() and im.month_ok(r) is not True]}
    # 4 합성 표지 — 규칙 · 대조 · 위약 뜻 · 점 시점(실제 세계 · 실제 지도 · 수익 없음)
    months = Q.months_between(Q.mshift(view.months[0], -3), view.months[-1])
    S = synth_bundle(im, months, seed=11)
    t1 = time.time()
    B = build(view, S)
    rep["synthetic"] = {"build_sec": round(time.time() - t1, 1)}
    for code in QCARDS:
        C = B["cards"][code]
        bad = check_card(view, S, C, n_draws=2)
        rep["synthetic"][code] = {"violations": bad[:10], "n_viol": len(bad), "f0": {k: C["f0"][k] for k in ("median_n_r", "min_n_r", "max_n_r", "ok")},
                                  "short": sum(row["short"] for row in C["rec"]), "skip_fill": sum(row["n_skip_fill"] for row in C["rec"]),
                                  "controls": {c: (K.get("hash") or "")[:12] or K.get("unavailable") for c, K in C["controls"].items()},
                                  "jaccard_C3_mean": (C["jaccard"].get("C3") or {}).get("mean"),
                                  "c1_overlap": sum(((C["controls"].get("C1") or {}).get("c1_overlap") or {}).values()),
                                  "c1_short": sum(((C["controls"].get("C1") or {}).get("c1_short") or {}).values()),
                                  "c2_nosale": sum(((C["controls"].get("C2") or {}).get("n_nosale") or {}).values()),
                                  "f0_excluded": len(C["f0"]["excluded"])}
    rep["synthetic"]["R5"] = {"swaps": B["cards"]["R5-ALARM"]["arm"]["swaps"], "flagged": B["cards"]["R5-ALARM"]["counts"]["flagged"]}
    rep["synthetic"]["pit"] = {"R1": pit_check(view, S, ("OS",), forms, [forms[10], forms[25]]),
                               "R2": pit_check(view, S, ("CH",), forms, [forms[15]]),
                               "STACK": pit_check(view, S, ("OS", "CH"), forms, [forms[30]])}
    t2 = time.time()
    for i in range(5):
        placebo_targets(view, B["cards"]["R1-OPPSELL"], i)
    rep["synthetic"]["placebo_targets_sec_per_draw"] = round((time.time() - t2) / 5, 3)
    # 5 눈가린 연기 시험 — 합성 표지로 run()(값은 버린다 · 예외 · 모양 · 시간만)
    if smoke:
        sm = Q.blind_smoke(run, ctx, S, nperm=nperm_smoke)
        rep["smoke"] = {"ok": sm["ok"], "sec": sm["sec"], "err": sm["err"],
                        "cards": sorted(k for k in (sm["shape"] or {}) if not k.startswith("_")),
                        "nperm": nperm_smoke}
    # 6 실제 표지(있으면) — 구성만: 교체 수 · F0 · C3 · R1 · Q07 자카드 · FPI · 자료 출처(🚨 수익 없음)
    #   «자료 없음» 은 실패가 아니다 · 파일이 있는데 읽다 멈춤 · 실제 표지 구성 위반 · Q07 핀 어긋남은 실패(real_ok = False · 종료 코드 1)
    rep["real_ok"], rep["real_fail"] = True, []
    RB = None
    try:
        RB = load_bundle(view, im=im, allow_override=allow_override)
    except SystemExit as e:
        rep["real"] = "적재 멈춤: %s" % e
        rep["real_fail"].append("load")
    except Exception as e:                                           # 빌더 예외(스키마 어긋남 등)도 조용히 넘기지 않는다
        rep["real"] = "적재 예외: %r" % (e,)
        rep["real_fail"].append("load")
    if RB is not None:
        rep["real_src"] = {k: v for k, v in RB["src"].items()}
        have = [f for f in ("OS", "CH", "ALARM") if RB.get(f) is not None]
        ext = None
        if q07 or any(RB.get(f) is not None for f in ("OS", "CH")):
            try:
                Q7 = q07_lists(ctx)
                ext = {"Q07": Q7["lists"]}
                rep["q07"] = {k: Q7[k] for k in ("V1_hash", "pin_ok", "manifest", "units", "n_by_form", "sec")}
                rep["q07"]["forms"] = len(Q7["lists"])
                rep["q07"]["forms_eq_stage_s"] = sorted(Q7["lists"]) == sorted(forms)
                if not rep["q07"]["forms_eq_stage_s"]:
                    rep["real_fail"].append("q07_forms")
            except SystemExit as e:
                rep["q07"] = "멈춤: %s" % e
                rep["real_fail"].append("q07")
            except Exception as e:
                rep["q07"] = "예외: %r" % (e,)
                rep["real_fail"].append("q07")
        if have:
            BR = build(view, RB, external=ext)
            rep["real"] = {}
            for code in CARDS:
                C = BR["cards"].get(code)
                if C is None:
                    rep["real"][code] = "자료 없음"
                elif code == "R5-ALARM":
                    rep["real"][code] = {"flagged_name_months": C["counts"]["flagged"], "by_year": C["counts"]["by_year"],
                                         "by_sector": C["counts"]["by_sector"], "unk_name_months": C["counts"]["unk"],
                                         "arm": C["arm"], "hash": C["hash"][:16]}
                else:
                    nv = check_card(view, RB, C, n_draws=1)
                    K1, K2 = C["controls"].get("C1") or {}, C["controls"].get("C2") or {}
                    rep["real"][code] = {"f0": C["f0"], "hash": C["hash"][:16], "jaccard": {k: v.get("mean") for k, v in C["jaccard"].items()},
                                         "violations": len(nv), "violations_head": nv[:10],
                                         "controls": {c: (K.get("hash") or "")[:12] or K.get("unavailable") for c, K in C["controls"].items()},
                                         "c1_overlap": sum((K1.get("c1_overlap") or {}).values()), "c1_short": sum((K1.get("c1_short") or {}).values()),
                                         "c2_nosale": sum((K2.get("n_nosale") or {}).values())}
                    if nv:
                        rep["real_fail"].append("violations:%s" % code)
        else:
            rep["real"] = "실제 표지 자료 없음(OS · CH · ALARM 모두) — 자료 빌드가 끝나면 다시 돌린다"
    rep["real_ok"] = not rep["real_fail"]
    rep["sec"] = round(time.time() - t0, 1)
    return rep


def _js(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    return o.item() if hasattr(o, "item") else str(o)


def main() -> int:
    a = sys.argv[1:]
    if "--selftest" in a:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1, default=_js))
        return 0 if r["ok"] else 1
    if "--construct" in a:
        n = int(a[a.index("--nperm-smoke") + 1]) if "--nperm-smoke" in a else 3
        rep = construct(nperm_smoke=n, smoke="--no-smoke" not in a, allow_override="--allow-override" in a, q07="--q07" in a)
        s = json.dumps(rep, ensure_ascii=False, indent=1, default=_js)
        if "--out" in a:
            p = a[a.index("--out") + 1]
            io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
        print(s)
        ok = rep["v0"]["rebuild_eq"] and all(rep["v0"][c] for c in QCARDS) and rep["v0"]["R5_forms_eq"] and \
            all(rep["synthetic"][c]["n_viol"] == 0 for c in QCARDS) and not any(rep["synthetic"]["pit"].values()) and \
            (rep.get("smoke") or {"ok": True})["ok"] and rep.get("real_ok", False)
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
