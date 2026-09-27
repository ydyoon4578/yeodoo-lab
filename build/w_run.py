# -*- coding: utf-8 -*-
"""build/w_run.py — 배치 W 한 번 굽기 러너(등록 A · 등록 B): 얼린 판 점검 → 시작 표식 셋 → 준비 자식(θ = 1 책 · 신호) → G-EGD(w_cmp · 별도 과정) →
굽기 자식(위생 → Tier-1 → 가족 Holm → Tier-2 → 채택 표시 → 보고) → EG30 비교 줄(w_cmp · 별도 과정) → 게시 칸 · 실행 기록 → FINISHED.
등록 전 F0(개수 · 몫 · 날짜 · 라벨만 — 수익 없음) · 자료 명세(data/_wb_manifest.json)도 이 파일이 만든다.

사전등록: build/PREREG-<날짜>-WBATCH.md(본문) + build/PREREG-<날짜>-WBATCH-CARDS.md(카드 원문) — 결과 문서 = 본문 이름 + «-RESULT».
  등록 B 는 build/PREREG-<날짜>-WBATCH-B.md 하나(그 문서를 처음 더한 커밋 = WBATCH_B_COMMIT · 제 시작 표식 · 제 Holm).
  글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다.
설계 원본(구속): wbatch_research.json final(slate · evaluation · oos_protocol · multiplicity · data_plan · build_plan · registration · decisions ·
  needs_user) + 갱신 둘 2026-09-27(명세와 어긋나면 이것이 이긴다 — (가) 사용자 말 · (나) 그 귀결로 오케스트레이터가 정한 것):
  (가) 전방 원장 없음 — data/_wfwd · WFWD · FF1/FF2 · e-과정 전방 보고 · 날짜 박힌 미래 판정을 만들지 않는다 · W13 뺌.
  (나) 🔎 오케스트레이터 결정(계산 전 고정 · 사용자가 구성원 · α · 채택 식을 고르지 않았다): 표본 안 확증 가족 — 등록 A {W01 · W04 · W10m} · 등록 B {W02 · W11} · 카드마다 Tier-1 주 통계 NW(3) t 를 미리 적은 방향으로
       한쪽 Holm α 0.05 · 채택 표시 = Holm 기각 ∧ Tier-2 무해(20bp 연 X ≥ 0 ∧ 하락월 X ≥ 0 ∧ 회전 ≤ 10 ∧ T+1 행) ∧ G-EGD 통과 ·
       W03 · W06 · W12 측정만 · 스텝 S3e/S2/S1 은 W01 위 Δ 로만 · 채택 카드를 펀드에 붙이는 것은 결과 문서 뒤 사용자 결정(날짜 없음).
  사용자 규칙: 평가 창 ≤ 최근 20년(보유월 ≥ 2006-09 · w_core) · 공개 사이트 10년 · G-NoEG · 주식 중심(파생 없음) · 카드마다 근본 이유.
판정 식은 여기서 새로 쓰지 않는다 — w_core · w_stagem · w_hygiene · w_panel · w_ipca · w_ciq · w_pap · w_steps · w_cards · w_geo · w_frag 와
  얼린 V 모듈(v_core · v_cards · v_tests · v_pit …)의 함수를 명세 차례대로 부를 뿐이다. 이 파일이 새로 정한 산수는 머리말 R1 ~ R16 선언이다.

  python -X utf8 build/w_run.py --selftest          판 점검 갈래 · 시작 표식 · 등록 상수 · 게시 칸 누수 · 직렬화 · 폐포 ⊆ 얼린 파일 · 경로 항등 · open() 인코딩(합성만)
  python -X utf8 build/w_run.py --guard             사이트 경계(w_guard · v_guard) + G-NoEG 정적(참/거짓 · 이름만)
  python -X utf8 build/w_run.py --manifest          자료 명세 → data/_wb_manifest.json(SHA · 개수 · 판 — 값 없음)
  python -X utf8 build/w_run.py --f0                등록 전 F0(자식 과정 · 개수 · 몫 · 날짜 · 라벨 · 커버리지 · 위생 셈 · 스위치 활성 · 앵커) → data/_wb_f0.json
  python -X utf8 build/w_run.py --f0-table          data/_wb_f0.json → 등록 문서 §3 표(Markdown)
  python -X utf8 build/w_run.py --pins              얼린 파일 표(git blob · LF sha256)
  python -X utf8 build/w_run.py --precommit         등록 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/w_run.py --smoke [--reg B]   러너 경로 전체 눈가린 연기(산출 · 표식은 저장소 밖 임시 폴더 · 열지 않고 지운다)
  python -X utf8 build/w_run.py --result-doc <게시 칸 파일>   결과 문서 본문(얼린 렌더러 · 게시 칸 파일 하나만)
  WBATCH_COMMIT=<등록 A 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python -X utf8 build/w_run.py      한 번 굽기(A)
  WBATCH_COMMIT=<A> WBATCH_B_COMMIT=<등록 B 커밋> … python -X utf8 build/w_run.py --reg B                                           한 번 굽기(B)

한 번 굽기 규약(v_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다) · 등록 커밋 = 등록 문서 · 카드 문서 · 이 러너 · F0 문서 · 자료 명세를 **처음 더한** 커밋 · origin/main 조상 ·
    그 커밋의 등록 문서 둘에 빈칸(열린 꺾쇠 + TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(새 w_* 파일 · F0 · 명세 + 얼린 V 핀 모듈)이 그 커밋과 바이트 단위로 같다(CRLF 무시) · V 핀(ada1e16ae blob)도 같다.
  · 굽기가 읽는 랩 자료(W_LAB_FILES)가 그 커밋의 판과 같고 추적 안 된 파일이 없다 · 명세 SHA = 지금 SHA(랩 파일 · 폴더 · V 캐시 · W 캐시).
  · 산출물이 없다(저장소 밖 산출 · 실행 기록 · origin/main 의 결과 문서 어느 것이든 있으면 다시 돌지 않는다 — 다시 굽기는 새 등록).
  · 시작 표식 셋: 로컬 둘(<캐시>/out/_wbatch.started · git 공용 폴더 wbatch_started)을 **무엇보다 먼저** 쓰고 origin 태그 refs/tags/wbatch-started 를
    계산 **전에** 민다 · FINISHED 줄이 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만
    WBATCH_RERUN=사유 로 처음부터(이어하기 없음). 등록 B 는 _wbatch_b.* · wbatch_b_started · wbatch-b-started.
  · PYTHONHASHSEED=0 · BLAS/OMP 스레드 1 · numpy 2.5.3 · scipy 1.18.1 · pandas 3.0.6 · 등록 상수(REGISTERED)가 실행 때도 그대로.
  · 🔒 G-NoEG: (1) 판 점검이 w_guard.noeg_static 을 다시 돈다 (2) 계산은 자식 과정에서 · 끝에 sys.modules 금지 모듈 없음 (3) 자식 open 감사에 EG ·
    B/M 정렬 원천 없음 (4) 명세에 EG 파일 없음 — EG 계보를 여는 과정은 w_cmp 하나(부모가 따로 띄운다).
  · 산출은 저장소 밖: <캐시>/out/_wbatch.json(전부) · _wbatch.public.json(결과 문서가 옮길 칸만) · _wbatch.run.json · _wbatch.child.json ·
    _wbatch.prep.json · _wbatch.books.json.gz(G-EGD 넘김 · 비중 · 신호만) · _wbatch.gegd.json · _wbatch.cmp.json.

🔎 이 파일이 정한 산수(선언 — 등록 문서 §8 에 옮긴다 · 계산 전 · 성과를 본 사람 없음)
  R1 차례: 명세 registration.commit_order «등록 → 시작 태그 → F0(G-EGD · P0 기록) → 한 번 굽기» — 등록 전 F0(data/_wb_f0.json)는 수익이 전혀 없는 셈만이고,
     G-EGD 는 굽기 첫 단계(준비 자식 → w_cmp)에서 잰다(W01 θ = 1 책이 IPCA 적합 = 실수익 학습에 기대므로 등록 전에 만들지 않는다).
  R2 W01 KPS7 대체(명세 f0_fallback): 준비 자식이 KPS8 · KPS7 두 판의 θ = 1 C 책(신호만)을 넘기고 → KPS8 G-EGD 통과면 KPS8 · 아니면 KPS7 ·
     W01 의 G-EGD 칸 = 고른 판의 통과 여부(둘 다 실패면 KPS7 · «EG30-근접» · 채택 없음). 고른 판만 굽는다(다른 판의 수익 통계는 계산하지 않는다).
  R3 🔁 W01 가족 통계 = **명세 primary_statistic 그대로** — 기본(S 팔) IPCA 예측 z(r̂) 의 FM γ(등록 전 되돌림 · 비평 2 M5: 초안이 C 팔로 바꾼 것을
     이탈 목록에 적지 않았고, 갱신 나(오케스트레이터 결정)는 «카드의 미리 적은 Tier-1 FM γ» 를 가족 통계로 적었다 · 명세 E[t] 0.93 · 검정력은 이 판의 값) ·
     C 팔 γ · Δγ(C − S) 는 보고(부 가족 BY · 명세 conditional_C.measure) · 채택 대상 책은 명세 adoption_marks 그대로 C 책(Tier-2 무해 · G-EGD 는 C 책) ·
     W04 가족 통계 = z(β^CIQ) FM γ(Stage M-W + FP β̂ + b_dn + LTD 통제 · 명세 primary) · W10m = z(tail)·z(IQR) 교차항(w_stagem S4) ·
     세 카드 모두 판정 p = w_stagem S11 제약 야생 부트스트랩(B 9,999 · 씨앗 SEED + w_core.FAMILY_SEED_OFF · w_core K1).
  R4 W10m 은 책이 없다(명세) → Tier-2 T+1 행 없음 → 채택 표시는 늘 거짓(Holm 기각은 확증으로만 적는다) · G-EGD 의 책 쪽 두 척도는 그 신호의 표준
     θ = 1 슬리브(상위 30%)로 잰다(G-EGD 전용 · 보고).
  R5 Tier-2 경로(명세 common_frame): 목표 = w_cards.sleeve_target(θ 혼합 · 투영 · β 띠) · 선정 버퍼(새 q · 기존 1.5q) · 체결 = w_cards.execute(½ · 틈 0.1 · 삭제 전량 ·
     회전 예산 B2) · 첫 결정은 목표에서(미과금) · 커버리지 못 넘은 결정 달은 재편성 없이 흘러간다(선정 버퍼도 그대로) · 보유월 수익 = v_pit.hold_ret(y_stop) ·
     T+1 = frozen v_cards.SLayer.hold_split(옛 책 첫날 × 새 책 나머지 날) · X = frozen v_core.fund_x · 보고 묶음 = frozen v_tests.s_tests(주 행 T+1) ·
     조건부 베타 조정 α = frozen v_tests.beta_adj_alpha(SPY 총수익 · 랩 rf) · 무해 = w_core.tier2_harmless(20bp T+1).
  R6 스텝(명세 step_order_W01 · 각 Δ 따로): C → +S3e(θ_t = θ0·min(1, W_{t−1}) · IC_s = C 점수의 실현 순위 IC) → +S2(8월 갱신 ω · H · σ_CS = 결정 앞 달들의 단면 y SD 평균 ·
     무거래 규칙 · σ 가 서기 전(첫 8월 앞)은 규칙 끔 = 모든 이름 거래 · 체결 뒤 회전 예산 B2) → +S1(+S3e 목표를 4 트랜치로 체결 — S2 무거래 규칙은 트랜치 체결에
     얹지 않는다: w_steps.tranche_path 가 frozen v_core.execute_book 을 부른다 · 트랜치 목표 = 그달 월말 결정의 목표 책 · 일간 결측 수익 = 0).
     Δ_S3e = X(+S3e) − X(C) · Δ_S2 = X(+S3e+S2) − X(+S3e) · Δ_S1 = X(+S3e+S1) − X(+S3e). S1 X = fund_x(트랜치 월수익(비용 포함), SPY, 비율, 거래 0).
  R7 위약 · 대조(보고만): W01 · W04 칸 안 위약 1,000(섹터 × 시총 3분위) · W03 S 열 섞기 1,000 · W04 C 팔 12개월 블록 섞기 1,000 과 S3e θ 경로 섞기 200 은
     «마찰 없는 능동수익» 통계 mean_t[(θ_t − θ0)·a_t](a_t = θ = 1 책 수익 − w_B 수익) 로 잰다(책 경로 1,000 벌을 다시 체결하지 않는다) · W12 무작위 비발표일 200.
  R8 P0 기록(바뀌지 않은 랩 식 · 가족과 무관): 효과 = IC_lit × 단면 y SD 의 달 평균(γ 단위로 옮김) · σ_plan = max(σ_analytic, 위약 γ SD 90분위).
  R9 V-플러스(보고 · 주의 칸): 주 FM 에 V02 z(−FP β̂) · V03 z(IRRX s) · V04 OB · OS 더미 · V05 z(CAR · 자격 밖 결측 더미)를 더한다 — V01(12-2) · V06(VAL)은 이미 Stage M-W 통제 ·
     🚨 V07(QLT)은 ROA 수준 · 장부 레버리지 입력이라 G-NoEG 로 뺀다. γ 가 절반 넘게 줄거나 부호가 바뀌면 «V 재포장» 주의.
  R10 위생(명세 hygiene_before_bake · 굽기 안): 눈가림 = 가족 셋의 주 통계를 y 씨앗 잡음 패널에서 끝까지(값은 버린다) · 라벨 섞기 누수 200 ·
     심은 신호 20(W01 · W04 는 주 효과 · W10m 은 교차항 IC 0.02 를 심는다 — y = d·IC·u⊥·s̃_t + √(1 − IC²)·e · s̃ = 상태 z 의 표준화 · 상태는 가족 교차항과
     같은 w_cards.w10m_state) · 선견 이동: PIT 독 넣기(결정 달 ≤ 200 · 특성 KPS8 · VAL · tail · FP β̂ · 세계 명단) + 패널 독 넣기(IPCA S · C 점수 24 결정) +
     W04 β^CIQ(24) + C 팔 상태(전부 · 🔁 결정일 d 당일 · 뒤 관측 값을 독으로 바꾼다 — 1영업일 늦춤 규칙을 실제로 시험) · 커버리지 F0 재현(등록 F0 문서와 같은 달 목록).
     🔁 등록 전 보정(비평 1 C1 · H3 · L1 · L3 — w_hygiene H2 · H3 · H6): 라벨 섞기 적중 = 회마다 두쪽 야생 부트스트랩 p(B 999) < 0.05 · 심기는 통제로 잔차화한
     방향(u⊥) · **카드 범위**: 라벨 섞기 · 심은 신호가 못 넘은 카드는 그 카드의 가족 p 가 없음(분모에 남는다 · 기각 · 표시 없음) · 파이프라인 검사(눈가림 ·
     선견 · 커버리지)가 못 넘으면 굽기는 «멈춤» 산출 한 줄(통계 없음 · 다시 굽지 않는다).
  R11 부 가족 BY q 0.10(보고): Tier-1 주 통계 전부 · Δγ(C − S) · Tier-2 C − S · 스텝 Δ 의 한쪽 p · 누적 N = 랩 945 + 이 굽기가 센 팔.
  R12 PBO/CSCV(보고): W01 설정 묶음(주 S · K1 · K2 · K4 · 비제약 · λ̂ S-E) · W04(주 · CAPM 잔차판) · W03(PAP · PEP+PAP · 대각) · 가족 주 계열 γ.
  R13 기대 효과(보고): 가족 주 t 의 경험적 베이즈 수축 t × τ̂²/(1 + τ̂²) · τ̂² = max(0, mean t² − 1) · 주제 대응은 등록 문서 표.
  R14 W06: 일간 평가 수익은 격자 가격(편출 이름 포함) · 사건 창 = 발동 결정일 종가부터 두 책을 흘러가게(w_cards B5) · 쌍둥이 RA = 6개월 수익 ÷ 3년 주간 σ
     (5거래일 겹치지 않는 묶음 로그수익 · 관측 ≥ 104 주).
  R15 W12: 스텝 효과를 그달 슬리브 수익에 더한다(Σ 날 효과 · 곱이 아닌 합 근사) · 대조 = 같은 수의 무작위 비발표일 200 벌의 효과 합 분포.
  R16 공개 칸(결과 문서): 최근 10년 창(보유 2016-09 ~ 2026-08) 수치만 — W03 내부 L 쌍둥이(20년 · French)는 창 · 개수 · 같은 부호(참/거짓)만 싣는다.
  R17 🔁 PN8 내부 가격 오버레이(등록 전 · 비평 1 H2): 우주는 w_panel.real_universe() — 편출 이름의 결정일 가격 구멍을 배치 R 이 쓴 검증된 내부 오버레이로
     빈 칸만 채운 세계(파일 sha256 은 자료 명세 w_cache.px_overlay 에 핀 · 경로 · 원천 이름 · 값은 공개하지 않는다) · 남은 구멍은 F0 price_hole 이 해마다 센다.
  R18 🔁 W10m 척도 없는 쌍둥이(보고 · 비평 1 M5): γ_t / SD_t(tail) 를 같은 상태에 회귀한 판을 싣고, 가족 교차항과 부호가 같은지를 주의 칸
     (mechanical_scaling_same_sign)으로 적는다 — W10m 은 책이 없어 표시가 늘 거짓이라 주의 칸은 해석만 바꾼다.
  R19 🔁 W12 스텝 팔 회전(보고 · 비평 2 M6): 발표일마다 d−1 종가에 w_B 로 가고 d 종가에 되돌리는 거래를 편도 연 회전에 더한다(Σ_d Σ|a_d| / 해) · 기준 V02 회전 +
     스텝 몫 · turn_le10 칸(측정만 카드 · 표시와 무관).
  R22 🔁 W02 C 가닥 강등(등록 B · 명세 open_before_register 규칙 = V D26): Hirshleifer–Lim–Teoh 2009(동시 발표 → 반응 지연 방향)를 등록 전에 열지 못했다
     (SSRN 403 · 로컬 사본 없음 · 웹 검색 한도 소진) → C 팔(발표 밀도 θ 사상)은 쌍둥이(보고 · Δ(C − S))로 내린다 · W02 의 채택 책 = S 책(θ0 0.5) ·
     가족 통계(z(G) FM γ)는 C 가닥과 무관 · 주의 칸 c_arm_demoted_twin. W11 은 Greenwood–Thesmar 2011 을 못 열었지만 F = ΣA² 정의는 2605.26740 초록
     [직접]이 그대로 적는다 — 가닥을 내리지 않고 G–T 특수형 문장은 [지식 · 미확인]으로 적는다(등록 B 문서 §3).
  R21 🔁 A 굽기는 B 등록 커밋 뒤에만(비평 2 H1): 판 점검이 origin/main 에 등록 B 문서(빈칸 없음)가 있어야 A 를 굽는다 — B(하락월 방어 카드 W11 ·
     검정력이 더 큰 가족)를 A 결과가 공개된 뒤에 등록하는 오염을 막는다. 이 등록은 A · B 를 한 커밋에 넣는다(WBATCH_B_COMMIT = WBATCH_COMMIT 가능).
  R20 🔁 W01 구조 검정 쌍둥이(보고 · 비평 1 L4): DM 을 S 팔(주의 칸 dm_t_gt0 · 가족 통계와 같은 판) · C 팔 · PIT 전용 학습 쌍둥이(학습 2014-06 ~ · 선형 기준선과
     같은 학습 길이)로 따로 싣는다 — 주 IPCA 는 2010-01 부터 학습해 선형 기준선(2014-06 ~)과 학습 길이가 다르다(공개).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해 찍지 않는다. --f0 는 개수 · 몫 · 날짜 · 라벨 · 위생 셈 · 스위치 활성(시장 상태)만 ·
   --smoke 는 눈가린 채(y · 평가 수익 = 씨앗 잡음 · 산출을 열지 않고 지운다). 수익을 만지는 함수는 자료 종류 kind 를 받아 w_core.assert_kind_allowed 를 지난다.
"""
from __future__ import annotations

import contextlib
import glob
import gzip
import hashlib
import io
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402  표준 라이브러리만(사이트 경계 · G-NoEG)


# ══════════════════════════════════════════════════════════════════════════
#  등록 문서 · 얼린 파일 · 등록 상수
# ══════════════════════════════════════════════════════════════════════════
def _find_docs():
    """등록 A 문서 둘(본문 · 카드) · 등록 B 문서 — 각각 하나뿐이어야 한다(RESULT 는 제외)."""
    main = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-WBATCH.md")))
    cards = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-WBATCH-CARDS.md")))
    regb = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-WBATCH-B.md")))
    pick = lambda c, dflt: ("build/" + c[0]) if len(c) == 1 else dflt
    return (pick(main, "build/PREREG-0000-00-00-WBATCH.md"), pick(cards, "build/PREREG-0000-00-00-WBATCH-CARDS.md"),
            pick(regb, "build/PREREG-0000-00-00-WBATCH-B.md"), (len(main), len(cards), len(regb)))


PREREG, CARDS_DOC, PREREG_B, _N_DOCS = _find_docs()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
RESULT_B = PREREG_B[:-len(".md")] + "-RESULT.md"
RUNNER = "build/w_run.py"
F0_FILE = "data/_wb_f0.json"                                 # 등록 전 F0(공개 안전 · 등록 커밋이 더한다 · w_guard.WB_ALLOWED)
MANIFEST_FILE = "data/_wb_manifest.json"                     # 자료 명세(공개 안전 · 등록 커밋이 더한다)
FIRST_ADDED = {"A": (PREREG, CARDS_DOC, RUNNER, F0_FILE, MANIFEST_FILE), "B": (PREREG_B,)}
W_MODULES = ("build/w_core.py", "build/w_guard.py", "build/w_stagem.py", "build/w_hygiene.py", "build/w_audit.py", "build/w_cmp.py",
             "build/w_panel.py", "build/w_ipca.py", "build/w_ciq.py", "build/w_pap.py", "build/w_steps.py", "build/w_cards.py",
             "build/w_geo.py", "build/w_frag.py", RUNNER)
NEW_FROZEN = W_MODULES + (F0_FILE, MANIFEST_FILE)
REUSED_FROZEN = tuple("build/%s.py" % m for m in sorted(WC.FROZEN_PINS))     # 얼린 V 핀(ada1e16ae blob — w_core.frozen_check 가 따로 대조)
CMP_FROZEN = ("build/eg30plus.py", "build/qg_lab.py", "build/rally_pattern.py", "build/stoploss.py")   # w_cmp 폐포(G-EGD · 비교 줄 · 별도 과정)
FROZEN = tuple(dict.fromkeys(NEW_FROZEN + REUSED_FROZEN + CMP_FROZEN))
V_LAB_FILES = ("data/stocks.json", "data/pit_px.json", "data/_px_raw.json", "data/splits.json", "data/index_history.json",
               "data/index_ledger.json", "data/pit_universe.json", "data/pit_reuse.json", "data/pit_gics_sectors.json",
               "data/earn_dates.json", "data/_ins_pit/cikmonth.json", "data/_ins_pit/routine.json", "data/_ins_pit/manifest.json",
               "data/_tenq_rf.json", "data/_issuer_map.json", "data/_fxv/index.json", "data/_fxv/manifest.json",
               "data/assets.json", "data/rf_monthly.json", "data/shares_yf.json")   # = frozen v_data.LAB_FILES(selftest 가 대조)
V_LAB_DIRS = ("data/sd", "data/fx", "data/fx_pit", "data/_fxv")                  # = frozen v_data.LAB_DIRS
W_EXTRA_FILES = ("data/bench_px.json", "data/mech_episodes.json", "data/_vb_manifest.json", "data/_vb_f0.json", "data/_vb_lit_open.json")
W_LAB_FILES = V_LAB_FILES + W_EXTRA_FILES
W_LAB_ALL = W_LAB_FILES + V_LAB_DIRS + (F0_FILE, MANIFEST_FILE)
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
LAB_N_BASE = 945                                             # 랩 누적 시도(VBATCH-RESULT 머리 · 명세 D27)

# 굽기 상수(명세 값 · 선언)
N_PLACEBO = 1000                                             # 칸 안 위약(연속 신호판 · 명세 tier1.placebo)
N_W03_PLACEBO = 1000                                         # W03 S 열 섞기
N_W04_SHUFFLE = 1000                                         # W04 C 팔 12개월 블록 섞기
N_S3E_SHUFFLE = 200                                          # S3e θ 경로 섞기
N_FOMC_PLACEBO = 200                                         # W12 무작위 비발표일
PIT_LA_N = 200                                               # PIT 독 넣기 결정 달(모자라면 전부)
PIT_LA_FROM = "2010-06"
IPCA_LA_N = 24                                               # 패널 독 넣기(IPCA 점수) 결정 달
W04_LA_N = 24                                                # W04 β^CIQ 독 넣기
W06_RA_WEEKS = 156                                           # R14
W06_RA_MIN = 104
SMOKE_CAPS = {"nperm": 3, "leak": 3, "plant": 2, "pit_la": 4, "ipca_la": 2, "w04_la": 2, "shuffle": 3, "fomc": 3}
SEED_OFF = {"placebo": 1, "leak": 11, "plant": 21, "pit_la": 31, "ipca_la": 41, "w03": 51, "w04_shuffle": 61, "s3e_shuffle": 71, "fomc": 81,
            "blind_eval": 91, "blind_panel": 101, "w02_shuffle": 111, "w11_random": 121}

# 등록 상수 — 얼린 코드의 값과 같아야 굽는다(실행 중 덮어쓰기 · 연기 덮어쓰기 방지)
REGISTERED = {
    "WC.FAMILY": {"A": ("W01", "W04", "W10m"), "B": ("W02", "W11")}, "WC.FAMILY_ALPHA": 0.05,
    "WC.CARD_DIRECTION": {"W01": 1, "W04": 1, "W10m": 1, "W02": 1, "W11": -1, "W03": 1, "W12": 1}, "WC.SEED": 20260927,
    "WC.HOLD_FLOOR": "2006-09", "WC.DECISION_FLOOR": "2006-08", "WC.S_WIN": ("2016-09", "2026-08"), "WC.TURN_MAX": 10.0, "WC.MAX_YEARS": 20,
    "WC.MEASURE_ONLY": ("W03", "W06", "W12"), "WC.V_COMMIT": "ada1e16ae9772a95246198407acb2f1e51a1906f", "WC.FORWARD_LEDGER": None,
    "S.LAG": 3, "S.MIN_DOF": 10, "S.TOL": 1e-08, "S.P0_Q": 0.4, "S.P0_ALPHA1": 0.0125, "S.P0_TCRIT": 2.27, "S.P0_GATE": 0.15, "S.PLACEBO_Q": 0.9,
    "H.LEAK_N": 200, "H.LEAK_CRIT": 1.96, "H.LEAK_FAIL_HITS": 19, "H.PLANT_IC": 0.02, "H.PLANT_REPS": 20, "H.PLANT_NEED": 16, "H.PLANT_T": 1.645,
    "H.LOOKAHEAD_N": 200, "H.COV_THR": 0.95, "H.BLIND_SCALE": 8.0, "H.LEAK_P": 0.05, "H.LEAK_B": 999,
    "H.PIPELINE_GATES": ("blind_smoke", "lookahead_shift", "coverage_f0"), "H.CARD_GATES": ("label_shuffle_leak", "planted_recovery"),
    "WC.WILD_B": 9999, "WC.FAMILY_SEED_OFF": {"W01": 501, "W04": 502, "W10m": 503, "W02": 504, "W11": 505},
    "WP.PX_OVERLAY_ENV": "WBATCH_PX_OVERLAY", "WP.PX_OVERLAY_FORMAT": "pit_px_stage/1",
    "WP.ME_FLOOR": 300.0, "WP.ME_CEIL": 8000000.0, "WP.LEDGER_BAND": (0.2, 5.0), "WP.COV_THR": 0.95, "WP.CAP_CARRY": 12, "WP.KPS_MIN_FEATURES": 6,
    "WP.KPS_COVER_MIN": 0.9, "WP.V06_USE_SP": False, "WP.TIER1": ("2016-08", "2026-07"), "WP.PANEL_FROM": "2010-01",
    "IP.K_MAIN": 3, "IP.K_TWINS": (1, 2, 4), "IP.KPS8": ("beta_kps", "r1", "log_me", "mom", "hi52", "ltr", "mom12_7", "log_asset"),
    "IP.KPS7": ("beta_kps", "r1", "log_me", "mom", "hi52", "ltr", "mom12_7"), "IP.CROSS": (("beta_kps", "z_baa"), ("r1", "z_vix")),
    "IP.TRAIN_FROM": "2010-01", "IP.LAM_FROM": "2014-06", "IP.FIRST_DECISION": "2016-08", "IP.LAST_DECISION": "2026-07", "IP.IC_LIT": 0.012,
    "IP.ALS_TOL": 1e-06, "IP.ALS_MAXIT": 500, "IP.BETA_SHRINK": (0.6, 0.4), "IP.BETA_WIN": 252, "IP.BETA_MIN": 200, "IP.CV_BLOCKS": 5,
    "IP.CV_PURGE": 1, "IP.CV_EMBARGO": 2, "IP.Z_STATE_MIN": 60,
    "CQ.TAU": 0.2, "CQ.WIN": 60, "CQ.MIN_OBS": 48, "CQ.FIRST_DECISION": "2014-01", "CQ.Q_TOP": 0.3, "CQ.THETA0": 0.5, "CQ.THETA_SLOPE": 0.25,
    "CQ.Z_CLIP": 2.0, "CQ.Z_MIN_N": 12, "CQ.IC_LIT": 0.016, "CQ.BLOCK": 12, "CQ.REPACK_SHRINK": 0.5, "CQ.DN_WIN": 252, "CQ.LTD_U": 0.05,
    "CQ.LTD_MIN": 200, "CQ.TS_NW": 6, "CQ.CT_MIN": 36, "CQ.QFA_TOL": 1e-06, "CQ.QFA_MAXIT": 200,
    "PP.WIN": 60, "PP.K_PAP": 3, "PP.GROSS": 0.2, "PP.SBAND": 0.15, "PP.NW_LAG": 6, "PP.SR_LIT": 0.7, "PP.N_PLACEBO": 1000, "PP.CLEAN_FROM": "2020-07",
    "ST.S3E_LAMBDA": 0.25, "ST.S3E_C": 0.2, "ST.S3E_STEP": 0.1, "ST.S2_LAGS": (0, 1, 2), "ST.S2_UPDATE_MONTH": "08", "ST.S2_COST": 0.001,
    "ST.S2_H_CLIP": (1.0, 12.0), "ST.S2_DECAY_LAGS": 6, "ST.S1_OFFSETS": (0, 5, 10, 15), "ST.FILL": 0.5, "ST.BAND_FRAC": 0.1,
    "CD.Q_DEFAULT": 0.3, "CD.BUFFER": 1.5, "CD.COST": 0.001, "CD.COST_ROBUST": 0.002, "CD.W06_THETA": "S0", "CD.W06_WIN_D": 63, "CD.W06_Q": 0.95,
    "CD.W06_H": (21, 42), "CD.W06_MIN_HIST": 60, "CD.TAIL_WIN": 63, "CD.TAIL_MIN": 50, "CD.TAIL_Q": 0.1, "CD.TAIL_STATE_MIN": 12,
    "CD.FOMC_FROM": "2009-01", "CD.FOMC_TO": "2026-08", "CD.FOMC_T1": ("2014-06", "2026-08"), "CD.FOMC_NW": 5, "CD.FOMC_PLACEBO": 200,
    "CD.FOMC_MIN_NAMES": 50,
    "R.N_PLACEBO": 1000, "R.N_W03_PLACEBO": 1000, "R.N_W04_SHUFFLE": 1000, "R.N_S3E_SHUFFLE": 200, "R.N_FOMC_PLACEBO": 200, "R.PIT_LA_N": 200,
    "R.IPCA_LA_N": 24, "R.W04_LA_N": 24, "R.LAB_N_BASE": 945, "R.VERSIONS": {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"},
}
REGISTERED_B = {"GEO.MIN_PEERS": 3, "GEO.N_SHUFFLE": 1000, "GEO.COV_GATE": 0.5, "FRAG.S_ACTIVE": 0.5, "FRAG.N_RANDOM": 200, "FRAG.IO_MAX": 1.5}


def _mods(reg="A"):
    import w_stagem as S
    import w_hygiene as H
    import w_panel as WP
    import w_ipca as IP
    import w_ciq as CQ
    import w_pap as PP
    import w_steps as ST
    import w_cards as CD
    M = {"WC": WC, "S": S, "H": H, "WP": WP, "IP": IP, "CQ": CQ, "PP": PP, "ST": ST, "CD": CD, "R": sys.modules[__name__]}
    if reg == "B":
        import w_geo as GEO
        import w_frag as FRAG
        M.update({"GEO": GEO, "FRAG": FRAG})
    return M


# ══════════════════════════════════════════════════════════════════════════
#  경로 · 표식(모두 저장소 밖)
# ══════════════════════════════════════════════════════════════════════════
MARK = {"A": {"git": "wbatch_started", "tag": "wbatch-started", "stem": "_wbatch"},
        "B": {"git": "wbatch_b_started", "tag": "wbatch-b-started", "stem": "_wbatch_b"}}
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}           # 연기만 임시 폴더로 돌린다(진짜 캐시 · .git · origin 에 아무것도 남기지 않는다)


def _git(*a, root=None):
    return subprocess.run(["git", "-C", root or ROOT] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")


def _git_mark_path(reg="A"):
    if _OVR["gitmark"]:
        return os.path.join(_OVR["gitmark"], MARK[reg]["git"])
    r = _git("rev-parse", "--git-common-dir")
    g = r.stdout.strip()
    if r.returncode != 0 or not g:
        raise SystemExit("🚨 git 공용 폴더를 찾지 못했다.")
    if not os.path.isabs(g):
        g = os.path.join(ROOT, g)
    return os.path.join(os.path.abspath(g), MARK[reg]["git"])


def out_dir():
    d = _OVR["out"] or WC.cache_dir("out")
    os.makedirs(d, exist_ok=True)
    return d


def paths(d=None, reg="A"):
    d = d or out_dir()
    st = MARK[reg]["stem"]
    j = lambda n: os.path.join(d, st + n)
    return {"dir": d, "out": j(".json"), "mark": j(".started"), "runlog": j(".run.json"), "public": j(".public.json"), "child": j(".child.json"),
            "prep": j(".prep.json"), "books": j(".books.json.gz"), "gegd": j(".gegd.json"), "cmp": j(".cmp.json"), "gitmark": _git_mark_path(reg)}


def _inside_repo(p):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(ROOT))
    return a == r or a.startswith(r + os.sep)


def _existing_outputs(P, reg="A"):
    st = MARK[reg]["stem"]
    have = [P["out"], P["runlog"], P["public"], P["child"], P["prep"], P["books"], P["gegd"], P["cmp"]]
    if os.path.isdir(P["dir"]):
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith(st + ".") and not f.endswith(".started")]
    return sorted({p for p in have if os.path.exists(p)})


def _sha_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _bytes(p):
    return pathlib.Path(p).read_bytes()


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _read_text(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def _write_text(p, txt):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def _read_json(p):
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def peak_mb():
    """최대 작업 메모리(MB · Windows · 값이 아니다)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakWorkingSetSize / 2 ** 20)
    except Exception:                                        # noqa: BLE001
        return None


# ══════════════════════════════════════════════════════════════════════════
#  경계 · 판 · 등록 상수
# ══════════════════════════════════════════════════════════════════════════
def site_guard():
    """사이트 경계 — w_guard.site_guard(배치 W · 표준 라이브러리만) + frozen v_guard.site_guard(배치 V · 같은 저장소)."""
    g = WG.site_guard(ROOT)
    gv = WC.frozen("v_guard").site_guard(ROOT)
    return {"ok": bool(g["ok"] and gv["ok"]), "bad": list(g["bad"]) + ["[V] " + b for b in gv["bad"]], "n_files": g.get("n_files"),
            "n_scanned": g.get("n_scanned")}


def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def _norm(x):
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            x = x.tolist()
    except Exception:                                        # noqa: BLE001
        pass
    if isinstance(x, (list, tuple)):
        return tuple(_norm(v) for v in x)
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def registered_constants_ok(reg="A"):
    M = _mods(reg)
    table = dict(REGISTERED)
    if reg == "B":
        table.update(REGISTERED_B)
    bad = []
    for k, want in table.items():
        mod, attr = k.split(".", 1)
        have = getattr(M[mod], attr, "<없음>")
        if _norm(have) != _norm(want):
            bad.append("%s = %r (등록 %r)" % (k, have, want))
    same = lambda a, b: os.path.normcase(os.path.abspath(a or "")) == os.path.normcase(os.path.abspath(b or ""))
    for mod, nm in (("WC", "holm_family"), ("WC", "adoption_table"), ("WC", "tier2_harmless"), ("S", "fm"), ("S", "summarize"), ("H", "run_all"),
                    ("H", "run_all_scoped"), ("S", "wild_p"), ("S", "family_fm"), ("WP", "real_universe"), ("WP", "apply_px_overlay")):
        fn = getattr(M[mod], nm, None)
        if getattr(fn, "__qualname__", "") != nm or not same(getattr(getattr(fn, "__code__", None), "co_filename", ""), M[mod].__file__):
            bad.append("%s.%s 이 덮어쓰였다" % (mod, nm))
    for k in ("WBATCH_SMOKE", "WBATCH_SMOKE_CAPS", "WBATCH_F0_FILE"):
        if os.environ.get(k):
            bad.append("연기 전용 환경 변수 %s 가 켜져 있다" % k)
    return bad


def placeholder_counts(text):
    return text.count(PLACEHOLDER), text.count(DRAFT_MARK)


def name_check(reg="A"):
    bad = []
    nm, nc, nb = _N_DOCS
    if reg == "A":
        if nm != 1 or nc != 1:
            bad.append("build/PREREG-*-WBATCH.md %d 개 · -WBATCH-CARDS.md %d 개" % (nm, nc))
        elif not (re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-WBATCH\.md", PREREG) and CARDS_DOC == PREREG[:-3] + "-CARDS.md"):
            bad.append("이름 꼴: %s · %s" % (PREREG, CARDS_DOC))
    else:
        if nb != 1:
            bad.append("build/PREREG-*-WBATCH-B.md %d 개" % nb)
        elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-WBATCH-B\.md", PREREG_B):
            bad.append("이름 꼴: %s" % PREREG_B)
    return bad


def code_shas(paths_=None):
    """F0 · 굽기가 쓰는 코드의 LF sha(앞 16자) — F0 문서가 «얼린 코드로 만들어졌는가» 를 판 점검이 본다."""
    out = {}
    for p in (paths_ or [x for x in W_MODULES] + list(REUSED_FROZEN) + list(CMP_FROZEN)):
        fp = os.path.join(ROOT, *p.split("/"))
        out[p] = _sha_lf(_bytes(fp))[:16] if os.path.exists(fp) else None
    return out


# ══════════════════════════════════════════════════════════════════════════
#  자료 명세(값 없음) — data/_wb_manifest.json
# ══════════════════════════════════════════════════════════════════════════
def _dir_digest(rel):
    base = os.path.join(ROOT, *rel.split("/"))
    names = []
    for dp, _, fns in os.walk(base):
        for fn in fns:
            names.append(os.path.relpath(os.path.join(dp, fn), base).replace(os.sep, "/"))
    names.sort()
    lines = "".join("%s\t%s\n" % (n, _sha_lf(_bytes(os.path.join(base, *n.split("/"))))) for n in names)
    return hashlib.sha256(lines.encode("utf-8")).hexdigest(), len(names)


def _index_digest(idx):
    lines = "".join("%s\t%s\n" % (k, v.get("sha256")) for k, v in sorted(idx.items()))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _vcache():
    return WC.VB_CACHE


def _fomc_dir():
    return os.path.join(WC.CACHE, "raw", "fomc")


def _french_file(fid):
    VD = WC.frozen("v_data")
    return os.path.join(_vcache(), "raw", "french", VD.FRENCH_FILES[fid])


def data_manifest(full_cache=True):
    """자료 명세 — 랩 파일(LF sha) · 폴더 digest · V 캐시(V-D1 · companyfacts 핀 · ^GSPC · 넓힌 원장 · French 49 산업) · W 캐시(FOMC 쪽 ·
    등록 B 명세 sha) · 판 · 환경 규칙 — 값 계열 없음."""
    doc = {"kind": "wbatch_manifest", "note": "배치 W 자료 판 동결 — build/w_run.py --manifest 가 쓴다. 값은 없다: SHA-256 · 개수 · 판만. "
                                              "원자료(yfinance · companyfacts · French · SEC 자료집 · HUD 교차표 · 연준 쪽)는 저장소 밖 캐시에만 있다.",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cache_root": "$WBATCH_CACHE 또는 %TEMP%/wbatch_cache(저장소 밖)",
           "v_cache_root": "$VBATCH_CACHE 또는 %TEMP%/vbatch_cache(읽기 전용)", "lab_files": {}, "lab_dirs": {}}
    for rel in W_LAB_FILES:
        p = os.path.join(ROOT, *rel.split("/"))
        doc["lab_files"][rel] = {"sha256_lf": _sha_lf(_bytes(p)), "bytes": os.path.getsize(p)} if os.path.exists(p) else {"missing": True}
    for rel in V_LAB_DIRS:
        dg, n = _dir_digest(rel)
        doc["lab_dirs"][rel] = {"digest": dg, "files": n, "rule": "sha256(«상대 이름 \\t LF sha256 \\n» 을 이름 차례로)"}
    vc = _vcache()
    vi = os.path.join(vc, "raw", "vd1", "_index.json")
    ci = os.path.join(vc, "raw", "companyfacts", "_pin_index.json")
    doc["v_cache"] = {
        "vd1": {"digest": _index_digest(_read_json(vi)["files"]) if os.path.exists(vi) else None, "rule": "V 규칙 — sha256(«키 \\t sha256 \\n»)"},
        "companyfacts_pin": {"digest": _index_digest(_read_json(ci)["files"]) if os.path.exists(ci) else None},
        "gspc": {"sha256": _sha_file(os.path.join(vc, "raw", "yf", "_GSPC.csv")) if os.path.exists(os.path.join(vc, "raw", "yf", "_GSPC.csv")) else None},
        "wide_ledger": {"sha256": _sha_file(os.path.join(vc, "derived", "wide_ledger.json.gz"))
                        if os.path.exists(os.path.join(vc, "derived", "wide_ledger.json.gz")) else None},
        "french_ind49": {"sha256": _sha_file(_french_file("ind49")) if os.path.exists(_french_file("ind49")) else None, "use": "W03 내부 L 쌍둥이만"}}
    fd = _fomc_dir()
    fl = sorted(os.listdir(fd)) if os.path.isdir(fd) else []
    lines = "".join("%s\t%s\n" % (n, _sha_file(os.path.join(fd, n))) for n in fl)
    doc["w_cache"] = {"fomc": {"digest": hashlib.sha256(lines.encode("utf-8")).hexdigest(), "files": len(fl), "source": "federalreserve.gov FOMC 일정 쪽"}}
    for nm in ("w02_manifest", "w11_manifest"):
        p = os.path.join(WC.CACHE, "f0", nm + ".json")
        doc["w_cache"][nm] = {"sha256": _sha_file(p) if os.path.exists(p) else None, "use": "등록 B 자료 판(FSDS · HUD · FTD · 13F 원자료 sha 목록)"}
    import w_panel as WP
    try:
        op = WP.px_overlay_path()
        doc["w_cache"]["px_overlay"] = {"sha256": _sha_file(op), "bytes": os.path.getsize(op),
                                        "use": "PN8 내부 가격 오버레이(저장소 밖 비공개 파일 — sha256 만 · 경로 · 원천 이름 · 값 없음)"}
    except SystemExit:
        doc["w_cache"]["px_overlay"] = {"sha256": None, "use": "PN8 — 파일 없음(등록 판을 지을 수 없다)"}
    doc["versions"] = VERSIONS
    doc["env_rule"] = dict(WC.REQUIRED_ENV)
    doc["frozen_v"] = {"commit": WC.V_COMMIT, "n_modules": len(WC.FROZEN_PINS), "data": sorted(WC.FROZEN_DATA_PINS)}
    doc["eg_files"] = "없다(w_guard EG 표식 파일은 이 명세 · 굽기 입력에 없다)"
    return doc


def manifest_problems(doc=None, full=True):
    """지금 자료 = 명세(판 점검 7) — 문제 목록(이름만)."""
    doc = doc if doc is not None else (_read_json(os.path.join(ROOT, *MANIFEST_FILE.split("/"))) if os.path.exists(os.path.join(ROOT, *MANIFEST_FILE.split("/"))) else None)
    if not doc or doc.get("kind") != "wbatch_manifest":
        return ["자료 명세 없음(--manifest)"]
    now = data_manifest()
    bad = []
    for sec in ("lab_files", "lab_dirs"):
        for k, v in (doc.get(sec) or {}).items():
            n = (now.get(sec) or {}).get(k)
            if n != v:
                bad.append("%s %s 가 명세와 다르다" % (sec, k))
    for sec in ("v_cache", "w_cache"):
        for k, v in (doc.get(sec) or {}).items():
            n = (now.get(sec) or {}).get(k) or {}
            for kk in ("digest", "sha256", "files"):
                if kk in v and n.get(kk) != v.get(kk):
                    bad.append("%s %s.%s 가 명세와 다르다" % (sec, k, kk))
    if full:
        vc = _vcache()
        vi = os.path.join(vc, "raw", "vd1", "_index.json")
        if os.path.exists(vi):
            VX = WC.frozen("v_px_split")
            idx = _read_json(vi)["files"]
            nb = [k for k, v in idx.items() if not os.path.exists(VX.vd1_path(k)) or _sha_file(VX.vd1_path(k)) != v["sha256"]]
            if nb:
                bad.append("V-D1 파일 %d 개 sha 가 목록과 다르다" % len(nb))
    return bad


# ══════════════════════════════════════════════════════════════════════════
#  F0 문서 거르개 · 시작 표식(순수 규칙 · selftest 가 모든 갈래를 본다)
# ══════════════════════════════════════════════════════════════════════════
F0_KEYS = ("coverage", "tier1_months", "kps_coverage", "me_sane", "anchors", "switch_activity", "fomc", "w04_qfa", "noeg_child", "code_sha", "px_overlay",
           "price_hole")


def f0_check(doc, code_now=None, manifest="load"):
    bad = []
    if not isinstance(doc, dict) or doc.get("kind") != "wbatch_f0":
        return ["F0 문서 꼴이 아니다"]
    miss = [k for k in F0_KEYS if k not in doc]
    if miss:
        bad.append("F0 칸 없음: %s" % ", ".join(miss))
    if (doc.get("anchors") or {}).get("gate_ok") is not True:
        bad.append("시총 앵커 관문이 참이 아니다")
    nc = doc.get("noeg_child") or {}
    if nc.get("runtime") is not True or nc.get("open_audit") is not True or nc.get("static") is not True:
        bad.append("F0 자식 과정의 G-NoEG(정적 · 실행 · open 감사)가 참이 아니다")
    if not (doc.get("tier1_months") or {}).get("months"):
        bad.append("Tier-1 결정 달 목록이 비었다")
    ov = doc.get("px_overlay") or {}
    if not ov.get("sha256") or not ov.get("values_filled"):
        bad.append("PN8 내부 가격 오버레이가 F0 세계에 얹히지 않았다")
    else:
        man = load_manifest_doc() if manifest == "load" else manifest
        if man is not None and ((man.get("w_cache") or {}).get("px_overlay") or {}).get("sha256") != ov.get("sha256"):
            bad.append("F0 의 오버레이 sha256 이 자료 명세와 다르다")
    if code_now is not None:
        diff = sorted(p for p, s in (doc.get("code_sha") or {}).items() if code_now.get(p) != s)
        if diff or not doc.get("code_sha"):
            bad.append("F0 를 만든 코드가 지금 코드와 다르다(%s …) — 얼린 코드로 --f0 를 다시" % ", ".join(diff[:3]))
    return bad


def load_manifest_doc():
    p = os.path.join(ROOT, *MANIFEST_FILE.split("/"))
    return _read_json(p) if os.path.exists(p) else None


def load_f0(path=None):
    p = path or os.path.join(ROOT, *F0_FILE.split("/"))
    return _read_json(p) if os.path.exists(p) else None


def _remote_start_tag(reg="A"):
    tag = MARK[reg]["tag"]
    r = _git("ls-remote", "--tags", "origin", "refs/tags/" + tag)
    if r.returncode != 0:
        raise SystemExit("🚨 origin 시작 태그를 확인하지 못했다(git ls-remote 실패 · %s) — 모르면 굽지 않는다." % r.stderr.strip()[:120])
    lines = [x.split() for x in r.stdout.splitlines() if x.strip()]
    return lines[0][0] if lines else None


def start_guard(full, rerun, marks, remote_tag):
    """marks = [(경로, 글)] · remote_tag = origin 시작 태그의 커밋 | None — v_run.start_guard 와 같은 갈래."""
    if any(FINISHED in txt for _, txt in marks):
        raise SystemExit("🚨 굽기가 이미 끝났다(시작 표식에 %s 줄) — 산출을 지웠어도 · WBATCH_RERUN 이어도 다시 돌지 않는다(다시 굽기는 새 등록)." % FINISHED)
    if remote_tag is not None and remote_tag != full:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다 — 다시 굽기는 새 등록." % remote_tag[:8])
    if marks and not rerun:
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 WBATCH_RERUN=사유 로 처음부터(이어하기는 없다)."
                         % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 WBATCH_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다 — 다른 사본 · 복원한 캐시로는 다시 돌지 않는다.")
    if rerun and not all(txt.startswith(full) for _, txt in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if remote_tag is not None and not rerun:
        raise SystemExit("🚨 origin 에 시작 태그가 있다 — 한 번 굽기가 이미 시작됐다(이 컴퓨터의 산출 전 중단이면 WBATCH_RERUN).")
    return True


def _first_added_ok(full, rels):
    for p in rels:
        added = _git("log", "--format=%H", "--diff-filter=A", full, "--", p).stdout.split()
        if not added or added[-1] != full:
            return "%s 는 %s 를 처음 더한 커밋이 아니다" % (full[:8], p)
    return None


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def frozen_check(env=None, reg="A"):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("WBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 WBATCH_COMMIT(등록 A 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --manifest · --f0 · --pins · --precommit · --smoke 만 된다.")
    nb = name_check("A") + (name_check("B") if reg == "B" else [])
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_WBATCH_NO_FETCH"):
        fr = _git("fetch", "--quiet", "origin")
        if fr.returncode != 0:
            raise SystemExit("🚨 git fetch origin 실패 — origin/main 을 새로 보지 못하면 굽지 않는다(%s)." % fr.stderr.strip()[:160])
    r = _git("rev-parse", "--verify", "-q", c + "^{commit}")
    fullA = r.stdout.strip()
    if r.returncode != 0 or not fullA:
        raise SystemExit("🚨 커밋 %s 을 찾지 못했다." % c)
    why = _first_added_ok(fullA, FIRST_ADDED["A"])
    if why:
        raise SystemExit("🚨 %s." % why)
    full = fullA
    if reg == "B":
        cb = env.get("WBATCH_B_COMMIT")
        rb = _git("rev-parse", "--verify", "-q", (cb or "x") + "^{commit}")
        full = rb.stdout.strip()
        if not cb or rb.returncode != 0 or not full:
            raise SystemExit("🚨 WBATCH_B_COMMIT(등록 B 커밋)을 넘겨라.")
        why = _first_added_ok(full, FIRST_ADDED["B"])
        if why:
            raise SystemExit("🚨 %s." % why)
        if _git("merge-base", "--is-ancestor", fullA, full).returncode != 0:
            raise SystemExit("🚨 등록 B 커밋이 등록 A 커밋의 자손이 아니다.")
    for cm in {fullA, full}:
        if _git("merge-base", "--is-ancestor", cm, "origin/main").returncode != 0:
            raise SystemExit("🚨 등록 커밋이 origin/main 에 없다 — 먼저 푸시(git fetch 도).")
    docs = [(fullA, PREREG), (fullA, CARDS_DOC)] + ([(full, PREREG_B)] if reg == "B" else [])
    for cm, doc in docs:
        txt = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (cm, doc)], capture_output=True).stdout.decode("utf-8", "replace")
        n_ph, n_dm = placeholder_counts(txt)
        if n_ph or n_dm or not txt:
            raise SystemExit("🚨 등록 커밋의 %s 에 빈칸 %s⟩ %d · 초안 괄호(U+3014) %d 가 남았다(또는 문서 없음)." % (doc, PLACEHOLDER, n_ph, n_dm))
    if reg == "A":                                                   # R21 🔁 A 굽기는 B 등록 커밋 뒤에만(비평 2 H1 — B 를 A 결과 공개 뒤 등록하지 않게)
        nbB = name_check("B")
        if nbB:
            raise SystemExit("🚨 등록 B 문서가 없다 — A 굽기는 B 등록 커밋 뒤에만(%s)." % "; ".join(nbB))
        addB = _git("log", "--format=%H", "--diff-filter=A", "origin/main", "--", PREREG_B).stdout.split()
        if not addB:
            raise SystemExit("🚨 origin/main 에 등록 B 문서가 없다 — A 굽기는 B 등록 커밋 뒤에만.")
        txtB = subprocess.run(["git", "-C", ROOT, "show", "origin/main:%s" % PREREG_B], capture_output=True).stdout.decode("utf-8", "replace")
        if not txtB or any(placeholder_counts(txtB)):
            raise SystemExit("🚨 origin/main 의 등록 B 문서에 빈칸 · 초안 괄호가 남았다.")
    P = paths(reg=reg)
    if _inside_repo(P["dir"]):
        raise SystemExit("🚨 산출 폴더가 저장소 안이다: %s" % P["dir"])
    outs = _existing_outputs(P, reg)
    if outs:
        raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다(다시 굽기는 새 등록)." % ", ".join(os.path.basename(o) for o in outs))
    res_doc = RESULT if reg == "A" else RESULT_B
    if _git("cat-file", "-e", "origin/main:" + res_doc).returncode == 0:
        raise SystemExit("🚨 origin/main 에 결과 문서가 이미 있다 — 다시 굽기는 새 등록.")
    rerun = env.get("WBATCH_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag(reg) if (real or not env.get("_WBATCH_NO_FETCH")) else env.get("_WBATCH_REMOTE_TAG")
    start_guard(full, rerun, marks, remote)
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True)
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(_bytes(fp)) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 등록 커밋과 다르다." % p)
    fz = WC.frozen_check()
    if not fz["ok"]:
        raise SystemExit("🚨 얼린 V 핀 어긋남: %s" % "; ".join(fz["bad"][:5]))
    if _git("diff", "--quiet", full, "--", *W_LAB_ALL).returncode != 0:
        raise SystemExit("🚨 굽기가 읽는 랩 자료가 등록 커밋의 판과 다르다 — 등록 커밋을 꺼낸 작업 트리에서 굽는다.")
    extra = _git("ls-files", "--others", "--exclude-standard", "--", *W_LAB_ALL).stdout.split()
    if extra:
        raise SystemExit("🚨 랩 자료 폴더에 추적 안 된 파일이 있다(%s …)." % ", ".join(extra[:3]))
    mb = manifest_problems(full=True)
    if mb:
        raise SystemExit("🚨 자료가 명세와 다르다: %s" % "; ".join(mb[:5]))
    fb = f0_check(load_f0(), code_shas())
    if fb:
        raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:4]))
    v = _versions()
    vb = ["%s %s(등록 %s)" % (k, v.get(k), want) for k, want in VERSIONS.items() if v.get(k) != want]
    if vb:
        raise SystemExit("🚨 라이브러리 판이 다르다: %s" % ", ".join(vb))
    eb = WC.env_problems(env)
    if eb:
        raise SystemExit("🚨 환경 핀: %s" % "; ".join(eb))
    cb = registered_constants_ok(reg)
    if cb:
        raise SystemExit("🚨 등록 상수가 다르다: %s" % "; ".join(cb[:6]))
    g = site_guard()
    if not g["ok"]:
        raise SystemExit("🚨 사이트 경계 실패: %s" % "; ".join(g["bad"][:5]))
    ne = WG.noeg_static()
    if not ne["ok"] or "w_run" not in ne["targets"]:
        raise SystemExit("🚨 G-NoEG 정적 전이 점검 실패: 적중 %s · 경계 %s · 핀 밖 %s" % (ne["hits"][:3], ne["separate_violations"][:3], ne["unpinned"][:3]))
    return full


# ══════════════════════════════════════════════════════════════════════════
#  직렬화 · 모듈 셈 · 연 자료
# ══════════════════════════════════════════════════════════════════════════
def _clean(o, depth=0):
    """산출 → 올바른 JSON(NaN · inf → None · 계열 {"__series__"} · 표 {"__frame__"} · 기간 · 날짜 → 글자 · 사전 열쇠 → 글자)."""
    import numpy as np
    import pandas as pd
    if depth > 60:
        return str(o)
    if o is None or isinstance(o, (str, bool)):
        return o
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, pd.Series):
        return {"__series__": {str(k): _clean(v, depth + 1) for k, v in o.items()}}
    if isinstance(o, pd.DataFrame):
        return {"__frame__": {str(c): {str(k): _clean(v, depth + 1) for k, v in o[c].items()} for c in o.columns}}
    if isinstance(o, np.ndarray):
        return _clean(o.tolist(), depth + 1)
    if isinstance(o, dict):
        return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): _clean(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_clean(v, depth + 1) for v in o]
    if isinstance(o, (pd.Period, pd.Timestamp)):
        return str(o)
    return str(o)


def local_modules():
    out = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        f = os.path.abspath(f)
        if os.path.dirname(f) == os.path.abspath(HERE) and f.endswith(".py"):
            out.add("build/" + os.path.basename(f))
    return sorted(out)


def unfrozen_modules(mods=None):
    return [m for m in (mods if mods is not None else local_modules()) if m not in FROZEN]


def data_files_opened():
    base = os.path.normcase(os.path.join(ROOT, "data")) + os.sep
    out = set()
    for p in WG.opened_paths():
        a = os.path.normcase(os.path.abspath(p))
        if a.startswith(base):
            out.add("data/" + os.path.relpath(a, os.path.join(ROOT, "data")).replace(os.sep, "/"))
    return sorted(out)


def unregistered_data(files):
    reg = [x.lower() for x in W_LAB_ALL]
    return [f for f in files if not any(f.lower() == r or f.lower().startswith(r.rstrip("/") + "/") for r in reg)]


def cache_files_opened():
    """열린 캐시 파일(저장소 밖 V · W 캐시) — 뿌리 · 첫 폴더 단위 셈(이름만 · 명세 점검 범위 보고)."""
    import w_panel as WP
    roots = {"v": os.path.normcase(os.path.abspath(WC.VB_CACHE)) + os.sep, "w": os.path.normcase(os.path.abspath(WC.CACHE)) + os.sep,
             "ov": os.path.normcase(os.path.dirname(os.path.abspath(os.environ.get(WP.PX_OVERLAY_ENV) or os.path.join(WC.CACHE, "_no_overlay_", "x")))) + os.sep}
    cnt = {}
    for p in WG.opened_paths():
        a = os.path.normcase(os.path.abspath(p))
        for tag, r in roots.items():
            if a.startswith(r):
                rel = os.path.relpath(a, r).replace(os.sep, "/").split("/")
                key = "ov:px_overlay" if tag == "ov" else "%s:%s" % (tag, "/".join(rel[:2]) if len(rel) > 2 else rel[0])   # PN8 파일 이름은 싣지 않는다
                cnt[key] = cnt.get(key, 0) + 1
    return dict(sorted(cnt.items()))


def noeg_block():
    nr = WG.noeg_report()
    oa = nr.get("open_audit") or {}
    return {"static": {"ok": nr["static"]["ok"], "n_reached": nr["static"]["n_reached"], "hits": nr["static"]["hits"], "unpinned": nr["static"]["unpinned"]},
            "runtime": {"ok": nr["runtime"]["ok"], "loaded_forbidden": nr["runtime"]["loaded_forbidden"]},
            "open_audit": {"ok": oa.get("ok"), "n_opened": oa.get("n_opened"), "n_black": oa.get("n_black")}, "ok": nr["ok"]}


# ══════════════════════════════════════════════════════════════════════════
#  공통 굽기 바탕 — 우주 · 패널 · 슬리브 단면 · 평가 수익(실자료 | 눈가림)
# ══════════════════════════════════════════════════════════════════════════
def _log(msg):
    print(msg, flush=True)


class EvalReturns:
    """평가 수익(🚨 수익) — real: 얼린 v_pit · v_cards.SLayer 경로 그대로 · blind: 같은 모양의 씨앗 잡음(결측 자리 유지 · 달마다 같은 씨앗).
    신호의 입력(과거 가격 · 일간 행렬 DR)은 두 판 모두 실자료다(눈가림은 평가 쪽만 · w_cards 연기와 같다)."""

    def __init__(self, SU, DR, kcol, kind, seed):
        import numpy as np
        self.SU, self.DR, self.kcol, self.kind, self.seed = SU, DR, kcol, kind, int(seed)
        self.SL = WC.frozen("v_cards").SLayer(types.SimpleNamespace(pit=SU))
        self._h, self._N = {}, None
        if kind == "blind":
            rng = np.random.default_rng(self.seed + SEED_OFF["blind_eval"])
            N = rng.normal(0.0, 0.012, DR.shape)
            N[~np.isfinite(DR)] = np.nan
            self._N = N

    def matrix(self):
        return self.DR if self.kind != "blind" else self._N

    def hold(self, m):
        import numpy as np
        if m in self._h:
            return self._h[m]
        r = self.SU.hold_ret(m)
        if self.kind == "blind":
            rng = np.random.default_rng(self.seed + 7919 + WC.mno(m))
            r = {t: (None if r[t] is None else float(rng.normal(0.0, 0.08))) for t in sorted(r)}
        self._h[m] = r
        return r

    def hold_split(self, m):
        if self.kind == "blind":
            return {t: ((None, None) if v is None else (0.0, v)) for t, v in self.hold(m).items()}
        return self.SL.hold_split(m)

    def spy_hold(self, m):
        import numpy as np
        if self.kind == "blind":
            return float(np.random.default_rng(self.seed + 104729 + WC.mno(m)).normal(0.008, 0.04))
        return self.SL.spy_hold(m)

    def spy_monthly(self):
        """보유 달 SPY 총수익 계열(판정 기준 · DM 회귀자) — 격자 월말 대 월말(2009-02 ~)."""
        import pandas as pd
        ms = sorted(self.SU.me_idx)
        out = {}
        for a, b in zip(ms[:-1], ms[1:]):
            out[b] = self.spy_hold(a)
        ks = sorted(out)
        return pd.Series([out[k] for k in ks], index=pd.PeriodIndex(ks, freq="M"), dtype=float)

    def liq_rate(self):
        return self.SL.liq_rate()


def rf_monthly():
    return WC.frozen("v_data").lab_rf_monthly()


def _dm_regs(E):
    VT = WC.frozen("v_tests")
    return VT.dm_regressors(E.spy_monthly(), rf_monthly())


def build_ctx(kind, seed=WC.SEED, log=_log, with_y=True, sleeve_from=None):
    """우주(위생) · 일간 행렬 · 합집합 시장 · 패널 · 슬리브 단면 · 커버리지 · Tier-1 달 — kind real(등록 뒤) | blind(연기) | f0(수익 없음)."""
    import numpy as np
    import w_hygiene as H
    import w_ipca as IP
    import w_panel as WP
    t0 = time.time()
    import w_panel as _WPN
    U0 = _WPN.real_universe()   # PN8 내부 가격 오버레이를 얹은 세계
    SU = WP.sane(U0)
    log("  우주 %.0fs · 격자 %d 일 · 가격 키 %d" % (time.time() - t0, SU.D, len(SU.PX)))
    DR, kcol = WP.daily_matrix(SU)
    months = WP.panel_months(SU)
    mkt_d = IP.union_daily_market(SU, [WC.mshift(months[0], -1)] + months, DR=DR, kcol=kcol)
    log("  일간 행렬 %s · 합집합 시장 · %.0fs" % (DR.shape, time.time() - t0))
    P, X = WP.build_panel(SU, months, DR, kcol, mkt_d, sleeve_from=(sleeve_from or WP.TIER1[0]), log=log, with_y=with_y)
    log("  패널 달 %d · 슬리브 단면 %d · %.0fs" % (len(P["months"]), len(X), time.time() - t0))
    cov = WP.coverage_rows(SU, months)
    t1 = WP.tier1_months(cov)
    dec = [m for m in months if WP.TIER1[0] <= m <= WP.TIER1[1]]
    kc = WP.kps_coverage(P, dec)
    ctx = {"kind": kind, "seed": seed, "U": SU, "DR": DR, "kcol": kcol, "months": months, "mkt_d": mkt_d, "P_real": P, "X": X, "cov": cov, "t1": t1,
           "dec": dec, "dec_ok": [m for m in dec if m in set(t1["months"])], "kps": kc, "sec": {"ctx": round(time.time() - t0, 1)}}
    ctx["drift"] = set(dec) - set(ctx["dec_ok"])
    ctx["w01_ok"] = [m for m in ctx["dec_ok"] if m not in set(kc["fail"])]
    if kind == "blind":
        ctx["P"] = H.blind_panel(P, seed + SEED_OFF["blind_panel"])
    elif kind == "real":
        WC.assert_kind_allowed("real", "w_run.build_ctx")
        ctx["P"] = P
    else:
        ctx["P"] = P
    ctx["pkind"] = ctx["P"]["kind"]
    if kind in ("real", "blind"):
        ctx["E"] = EvalReturns(SU, DR, kcol, kind, seed)
    VD = WC.frozen("v_data")
    A = VD.read_json(VD.lab_path("data/assets.json"))
    ctx["macro"] = {"BAA10Y": A["macro"]["BAA10Y"], "VIXCLS": A["macro"]["VIXCLS"]}
    ctx["cross"] = IP.cross_states(A["macro"]["BAA10Y"], A["macro"]["VIXCLS"], months)
    return ctx


# ══════════════════════════════════════════════════════════════════════════
#  책 · 경로(R5)
# ══════════════════════════════════════════════════════════════════════════
def books_path(X, months, score_of, theta_of, q=None, drift=(), buffer=True):
    """선정 경로 → 목표 책 {결정 달: {티커: 비중}} — 흘러가는 달(drift)은 책을 만들지 않고 선정 버퍼도 그대로 둔다(R5)."""
    import numpy as np
    import w_cards as CD
    q = CD.Q_DEFAULT if q is None else q
    out, prev = {}, None
    for m in months:
        Xm = X.get(m)
        if Xm is None or m in drift:
            continue
        sc = score_of(m)
        th = theta_of(m)
        if sc is None or th is None:
            continue
        s = np.array([sc.get(t, np.nan) for t in Xm.t], float)
        mask = CD.select_top(Xm, s, q, prev=prev, buffer=buffer)
        w, _ = CD.sleeve_target(Xm, mask, float(th))
        if w is None:
            continue
        out[m] = Xm.book(w)
        prev = {Xm.t[i] for i in np.flatnonzero(mask)}
    return out


def w_path(E, X, targets, months, fill=0.5, band_frac=0.1, rate="flat", executor=None, drift=()):
    """목표 책 경로 → 보유 달 DataFrame(S · S_t1 · traded · rate · B · B_EW · beta · n · n_miss · skipped) — frozen v_cards.SLayer.path 와 같은 모양 · 체결만
    w_cards.execute(회전 예산 B2) 또는 executor(스텝) · 흘러가는 달은 재편성하지 않는다(R5). 🚨 수익 입력."""
    import numpy as np
    import pandas as pd
    import w_cards as CD
    C = WC.frozen("v_core")
    rates = E.liq_rate() if rate == "liq" else None
    Ed, rows = None, {}
    for m in months:
        T = targets.get(m)
        Xm = X.get(m)
        if Ed is None:
            if T is None:
                continue
            E_, tr, sk, old = dict(T), 0.0, 0, None
        else:
            if T is None or m in drift:
                E_, tr, sk = dict(Ed), 0.0, 0
            elif executor is not None:
                E_, tr, sk = executor(m, Ed, T)
            else:
                E_, tr, sk = CD.execute(Ed, T, fill=fill, band_frac=band_frac)
            old = {t: v for t, v in Ed.items() if (Xm is None or t in Xm.pos)}
        WG.no_derivative_positions(E_)
        r = E.hold(m)
        Ed_new, R, nmiss = C.drift_book(E_, r)
        sp = E.hold_split(m)
        R1 = C.book_ret(old if old else E_, {t: v[0] for t, v in sp.items()})
        Rr = C.book_ret(E_, {t: v[1] for t, v in sp.items()})
        beta = float(sum(E_[t] * (Xm.beta[Xm.pos[t]] if (Xm is not None and t in Xm.pos and np.isfinite(Xm.beta[Xm.pos[t]])) else 1.0) for t in E_))
        h = WC.mshift(m, 1)
        ew = [v for t, v in r.items() if v is not None and (Xm is None or t in Xm.pos) and np.isfinite(v)]
        rows[h] = {"S": R, "S_t1": ((1 + R1) * (1 + Rr) - 1.0) if (R1 is not None and Rr is not None) else R, "traded": tr,
                   "rate": (rates.get(m, C.S_COST) if rates else C.S_COST), "B": E.spy_hold(m), "B_EW": (float(np.mean(ew)) if ew else None),
                   "beta": beta, "n": len(E_), "n_miss": nmiss, "skipped": sk}
        Ed = Ed_new
    df = pd.DataFrame.from_dict(rows, orient="index")
    if len(df):
        df.index = pd.PeriodIndex(df.index, freq="M")
    return df


def tier2_arm(E, Pdf, regs, name=""):
    """Tier-2 한 팔 — frozen v_tests.s_tests(주 행 T+1 · 10bp · 20bp · D0 · EW · 묶음) · 무해(w_core) · 조건부 베타 조정 α · 편도 회전. 🚨 수익 통계."""
    VT = WC.frozen("v_tests")
    if Pdf is None or not len(Pdf):
        return {"name": name, "n": 0, "harmless": {"harmless": False, "why": "경로 없음"}, "t1_row": False}
    Pw = Pdf.loc[VT.in_win(Pdf.index, *VT.S_WIN)]
    turn = WC.turnover_annual([float(x) for x in Pw["traded"].tolist()], len(Pw)) if len(Pw) else None
    st = VT.s_tests(Pdf, turn, rf=rf_monthly(), ev=VT.events_S())
    X10 = VT.s_x(Pw)
    X20 = VT.s_x(Pw, mult=2.0)
    Xd0 = VT.s_x(Pw, row="d0")
    hm = WC.tier2_harmless({str(k): float(v) for k, v in X20.items() if v == v}, turn, t1_row=("S_t1" in Pw and len(Pw) > 0))
    ba = VT.beta_adj_alpha(X10, regs)
    return {"name": name, "n": int(len(Pw)), "s_tests": st, "turn": turn, "harmless": hm, "beta_adj": ba, "X10": X10, "X20": X20, "Xd0": Xd0,
            "skipped": int(Pw["skipped"].sum()) if "skipped" in Pw else None, "t1_row": True}


def delta_arm(a, b, regs, key="X10"):
    """두 팔의 X 차(보유 달 겹침) — h1 · 조건부 베타 조정 α(보고). 🚨 수익 통계."""
    import pandas as pd
    VT = WC.frozen("v_tests")
    if not a or not b or key not in a or key not in b:
        return None
    d = (pd.Series(a[key], dtype=float) - pd.Series(b[key], dtype=float)).dropna()
    return {"h1": VT.h1(d), "beta_adj": VT.beta_adj_alpha(d, regs), "n": int(len(d)), "series": d}


def frictionless_active(E, X, books1, months):
    """마찰 없는 능동수익 a_t = R(θ = 1 목표 책) − R(w_B)(보유 달 · R7) — {결정 달: a}. 🚨 수익."""
    C = WC.frozen("v_core")
    out = {}
    for m in months:
        b = books1.get(m)
        Xm = X.get(m)
        if b is None or Xm is None:
            continue
        r = E.hold(m)
        rb, rw = C.book_ret(b, r), C.book_ret(Xm.book(Xm.wB), r)
        if rb is not None and rw is not None:
            out[m] = rb - rw
    return out


def theta_stat(theta, theta0, act):
    """R7 — mean_t[(θ_t − θ0)·a_t](θ 경로의 마찰 없는 몫)."""
    v = [(float(theta[m]) - float(theta0)) * a for m, a in act.items() if theta.get(m) is not None]
    return float(sum(v) / len(v)) if v else None


def pct_rank(obs, perm, direction=+1):
    import numpy as np
    p = np.asarray([x for x in perm if x is not None and x == x], float)
    if obs is None or not len(p):
        return None
    return float(np.mean(direction * p < direction * float(obs)))


# ══════════════════════════════════════════════════════════════════════════
#  Tier-1 도우미
# ══════════════════════════════════════════════════════════════════════════
def fm_card(P, months, key_of, name, direction, kind=None, extra_of=None, sample_of=None, wls=False):
    """FM(Stage M-W 통제 · 주 신호 name) → (fm 산출, summarize). key_of(m) → 패널 행 차례 신호 배열 | None."""
    import w_stagem as S
    kind = kind or P["kind"]

    def des(m):
        D = P["m"].get(m)
        z = key_of(m) if D is not None else None
        if D is None or z is None:
            return None
        return [S.stage_m_w_design(D, [(name, z)], extra=(extra_of(m) if extra_of else ()), sample=(sample_of(m) if sample_of else None), wls=wls)]
    res = S.fm(months, des, [name], kind)
    return res, S.summarize(res["months"], res["g"][name], direction)


def fm_family(P, months, key_of, name, direction, B, seed, kind=None, extra_of=None):
    """가족 FM 통계(R3 · w_core K1) — fm_card 의 γ 월 계열 → w_stagem.family_fm(NW(3) t + 제약 야생 부트스트랩 p)."""
    import w_stagem as S
    res, _sm = fm_card(P, months, key_of, name, direction, kind=kind, extra_of=extra_of)
    return S.family_fm(res["months"], res["g"][name], direction, int(B), int(seed))


def fm_design_of(name, key, extra_of=None):
    """심기 잔차화(w_hygiene H3 🔁) — 패널 달 D 의 신호 열쇠 key 로 그 카드의 Stage M-W 설계(통제 기저)를 짓는 함수."""
    import w_stagem as S
    return lambda m, D: S.stage_m_w_design(D, [(name, D[key])], extra=(extra_of(m) if extra_of else ()))


def placebo_blocks(P, months, key_of, name, extra_of=None):
    import numpy as np
    import w_stagem as S
    out = []
    for m in months:
        D = P["m"].get(m)
        z = key_of(m) if D is not None else None
        if D is None or z is None:
            continue
        d = S.stage_m_w_design(D, [(name, z)], extra=(extra_of(m) if extra_of else ()))
        if len(d["idx"]) < 20:
            continue
        cell = S.cells(np.asarray(D["sec"], object)[d["idx"]], np.asarray(D["me"], float)[d["idx"]])
        out.append((m,) + S.placebo_block(d, cell, name))
    return out


def tier1_reports(P, months, key_of, name, direction, ic_lit, n_perm, seed, extra_of=None, down=None):
    """Tier-1 보고 묶음(명세 reported_with) — σ_analytic · 칸 안 위약 · σ_plan · P0 기록 · 순위 IC · 10분위(EW · VW) · 두 반 · 2020-07 뒤 ·
    시총 상위 10 제외 · NDX 전용 · 하락월 · 상승월 IC. 🚨 수익 통계."""
    import numpy as np
    import w_stagem as S
    kind = P["kind"]
    res, sm = fm_card(P, months, key_of, name, direction, extra_of=extra_of)
    out = {"main": sm}
    try:
        out["sigma_analytic"] = S.sigma_analytic(res["parts"], name)
    except SystemExit as e:
        out["sigma_analytic"] = None
        out["sigma_err"] = str(e)[:120]
    bl = placebo_blocks(P, months, key_of, name, extra_of)
    pl = S.placebo(bl, kind, int(n_perm), int(seed), direction) if bl else {"t": np.array([]), "sd_gamma": np.array([])}
    out["placebo"] = {"n": int(n_perm), "rank": S.placebo_rank(sm["nw_t"], pl["t"], direction),
                      "t_q": [float(np.nanquantile(pl["t"], q)) for q in (0.05, 0.5, 0.95)] if len(pl["t"]) else None,
                      "role": "보고만(명세 D11 · 표시 밖)"}
    if out["sigma_analytic"] is not None and len(pl["sd_gamma"]):
        sp = S.sigma_plan(out["sigma_analytic"], pl["sd_gamma"])
        sd_y = [float(np.nanstd(P["m"][m]["y"], ddof=1)) for m in res["months"] if m in P["m"]]
        eff = float(ic_lit) * float(np.mean(sd_y)) if sd_y else None
        out["sigma_plan"] = sp
        out["p0"] = S.p0_record(eff, sp["sigma_plan"], sm["T"]) if (eff and sm["T"]) else None
        out["p0_eff_gamma"] = eff
    ymap = lambda m: S.sector_demean(P["m"][m]["y"], P["m"][m]["sec"])
    zmap = lambda m: key_of(m) if key_of(m) is not None else np.array([])
    ms_k = [m for m in months if m in P["m"] and key_of(m) is not None]
    ics = S.ic_series(ms_k, zmap, ymap, kind)
    out["ic"] = S.summarize(ics["months"], ics["ic"], direction)
    dn = set(down or WC.down_months())
    icd = [v for m, v in zip(ics["months"], ics["ic"]) if WC.mshift(m, 1) in dn]
    icu = [v for m, v in zip(ics["months"], ics["ic"]) if WC.mshift(m, 1) not in dn]
    out["ic_down"] = {"n": len(icd), "mean": float(np.mean(icd)) if icd else None}
    out["ic_up"] = {"n": len(icu), "mean": float(np.mean(icu)) if icu else None}
    de = S.decile_series(ms_k, zmap, lambda m: P["m"][m]["y"], kind)
    dv = S.decile_series(ms_k, zmap, lambda m: P["m"][m]["y"], kind, w_of=lambda m: P["m"][m]["me"])
    out["decile_ew"] = S.summarize(de["months"], de["ls"], direction)
    out["decile_vw"] = S.summarize(dv["months"], dv["ls"], direction)
    mo = res["months"]
    g = res["g"][name]
    half = len(mo) // 2
    out["half1"] = S.summarize(mo[:half], g[:half], direction)
    out["half2"] = S.summarize(mo[half:], g[half:], direction)
    post = [(m, v) for m, v in zip(mo, g) if m >= "2020-07"]
    out["post_2020_07"] = S.summarize([m for m, _ in post], [v for _, v in post], direction)

    def ex_top10(m):
        me = np.asarray(P["m"][m]["me"], float)
        cut = np.sort(me[np.isfinite(me)])[-10] if np.isfinite(me).sum() > 10 else np.inf
        return ~(me >= cut)
    _, out["ex_top10"] = fm_card(P, months, key_of, name, direction, extra_of=extra_of, sample_of=ex_top10)
    _, out["ndx_only"] = fm_card(P, months, key_of, name, direction, extra_of=extra_of, sample_of=lambda m: np.asarray(P["m"][m]["ndx_only"], bool))
    out["gamma"] = {"months": mo, "g": g}
    return out, res


# ══════════════════════════════════════════════════════════════════════════
#  위생(R10)
# ══════════════════════════════════════════════════════════════════════════
def plant_interaction(panel, key, state, ic, direction, rng, resid_of=None):
    """R10 — 교차항 심기: y = d·IC·u·s̃_t + √(1 − IC²)·e(u = 신호 순위 정규 점수 · s̃ = 상태 z 의 표준화 · 상태 없는 달은 e 만). kind synth.
    resid_of(m, D, u) → 통제로 잔차화한 단위 분산 u⊥(w_hygiene H3 🔁)."""
    import numpy as np
    import w_hygiene as H
    vs = np.array([v for v in state.values() if v is not None and v == v], float)
    mu, sd = (float(vs.mean()), float(vs.std(ddof=1))) if len(vs) > 1 else (0.0, 1.0)
    out = {k: v for k, v in panel.items() if k != "m"}
    out["m"] = {}
    for m in panel["months"]:
        D = panel["m"].get(m)
        if D is None:
            continue
        u = np.nan_to_num(H.normal_scores(D[key]))
        if resid_of is not None:
            u = np.nan_to_num(resid_of(m, D, u))
        s = state.get(m)
        st = ((float(s) - mu) / sd) if (s is not None and s == s and sd > 0) else 0.0
        e = rng.normal(0.0, 1.0, len(u))
        E = dict(D)
        E["y"] = direction * ic * u * st + math.sqrt(1 - ic * ic) * e
        out["m"][m] = E
    out["kind"] = "synth"
    return out


def with_signal(P, key, arr_of):
    """패널 사본 — 달마다 신호 배열을 열쇠 key 로 붙인다(심은 신호 · 라벨 섞기 통계용)."""
    out = {k: v for k, v in P.items() if k != "m"}
    out["m"] = {}
    for m in P["months"]:
        D = P["m"].get(m)
        a = arr_of(m) if D is not None else None
        if D is None or a is None:
            continue
        E = dict(D)
        E[key] = a
        out["m"][m] = E
    out["months"] = [m for m in P["months"] if m in out["m"]]
    return out


def month_features(SU, m):
    """PIT 선견 점검 비교용(R10) — 결정 달 m 의 세계 명단 · KPS8 · VAL · tail · FP β̂(일간 행렬 없이 · 합집합 시장은 m−13 ~ m−1 비중)."""
    import numpy as np
    import w_cards as CD
    import w_ipca as IP
    import w_panel as WP
    VF = WC.frozen("v_fund")
    world = WP.stage_world(SU, m)
    if not world:
        return {"n": np.array([0.0])}
    ms = [WC.mshift(m, -k) for k in range(14, 0, -1)]
    ms = [x for x in ms if x in SU.me_idx and WC.mshift(x, 1) in SU.me_idx]
    mkt = IP.union_daily_market(SU, ms)

    def asset_of(r, dd):
        if not r.get("gid"):
            return None
        at = VF.latest(SU.L.series(r["gid"], "asset", "i"), dd)
        return at[0] if at else None
    K8 = IP.kps8_month(SU, m, world, mkt, asset_of=asset_of)
    i = SU.me_idx[m]
    Rw = np.column_stack([SU.daily_ret(r["k"])[max(0, i - CD.TAIL_WIN + 1):i + 1] for r in world])
    out = {c: np.asarray(K8[c], float) for c in IP.KPS8}
    out["tail"] = CD.tail_shape(Rw)
    out["val"] = WP.val_scores(SU, m, world)
    out["beta_fp"] = np.array([np.nan if SU.beta_fp(r["k"], m)["beta"] is None else SU.beta_fp(r["k"], m)["beta"] for r in world], float)
    out["names"] = np.array([float(int(hashlib.sha256(r["t"].encode("utf-8")).hexdigest()[:12], 16)) for r in world], float)
    out["me"] = np.array([r["me"] for r in world], float)
    return out


def pit_lookahead(SU, n, seed, months):
    """R10 — PIT 독 넣기: 결정 달 n 개(씨앗 · 모자라면 전부)에서 독 넣은 우주(d 뒤 가격 · 원장 · 섹터 · 명단 난수)의 특성 = 원 우주의 특성(허용 0)."""
    import numpy as np
    import w_hygiene as H
    rng = np.random.default_rng(seed)
    return H.lookahead_shift(lambda data, t: month_features(data, t), SU, lambda data, t: data.poison_after(t, rng), months, seed, n=n, tol=0.0)


def ipca_lookahead(P, cross, chars, n, seed, noise_seed):
    """R10 — 패널 독 넣기: 결정 t 마다 s ≥ t 달의 y 와 s > t 달의 특성 · 상태를 잡음으로 바꾼 패널로 워크포워드(첫 결정 ~ t)를 다시 돌려
    t 의 S · C 점수가 원 점수와 비트까지 같다."""
    import numpy as np
    import w_hygiene as H
    import w_ipca as IP
    full = {"S": IP.walkforward(P, chars=chars), "C": IP.walkforward(P, chars=chars, cross=cross)}
    decs = sorted(set(full["S"]["dec"]) & set(full["C"]["dec"]))

    def poison(data, t):
        rng = np.random.default_rng(noise_seed + WC.mno(t))
        Q = {k: v for k, v in data.items() if k != "m"}
        Q["m"] = {}
        for m, D in data["m"].items():
            E = dict(D)
            if m >= t:
                y = np.asarray(D["y"], float)
                E["y"] = np.where(np.isfinite(y), rng.normal(0.0, 0.1, len(y)), np.nan)
            if m > t:
                for c in chars:
                    E[c] = rng.normal(0.0, 1.0, len(D[c]))
            Q["m"][m] = E
        return Q

    def sig(data, t):
        if data is P:
            s, c = full["S"]["dec"].get(t), full["C"]["dec"].get(t)
        else:
            cr = {m: (v if m <= t else {"z_baa": 9.0, "z_vix": -9.0}) for m, v in cross.items()}
            s = IP.walkforward(data, chars=chars, last=t)["dec"].get(t)
            c = IP.walkforward(data, chars=chars, cross=cr, last=t)["dec"].get(t)
        return {"S": (s or {}).get("score", np.array([np.nan])), "C": (c or {}).get("score", np.array([np.nan]))}
    return H.lookahead_shift(sig, P, poison, decs, seed, n=n, tol=0.0)


def state_lookahead(macro, months, d_of):
    """R10 — C 팔 상태(FRED BAA10Y · VIXCLS): 🔁 결정일 d **당일부터** 뒤 관측의 **값**을 독으로 바꾼 계열(날짜는 그대로 · 값 + 1,000)의 z_t = 전체 계열의 z_t
    (모든 결정 달) — «월말 값 1영업일 늦춤»(그달 두 번째로 늦은 관측) 규칙이 결정일 d 이후 값을 쓰면 여기서 걸린다(비평 1 L3: 달력 월말로 자르면 아무것도
    시험하지 않았다 · 날짜를 지우면 «그달 두 번째로 늦은» 자리가 바뀌어 규칙 자체를 바꾸므로 값만 바꾼다)."""
    import w_ipca as IP
    bad = []
    full = IP.cross_states(macro["BAA10Y"], macro["VIXCLS"], months)
    for m in months:
        d = d_of(m)
        poison = lambda s: {k: (v if (k < d or v is None) else float(v) + 1000.0) for k, v in s.items()}
        z = IP.cross_states(poison(macro["BAA10Y"]), poison(macro["VIXCLS"]), [m])[m]
        if z != full[m]:
            bad.append(m)
    return {"ok": not bad, "n": len(months), "n_bad": len(bad), "bad": bad[:5], "rule": "결정일 d 당일 · 뒤 FRED 관측 값을 독으로 바꿔도 z_t 가 같다"}


def w04_lookahead(SU, months, n, seed):
    """R10 — W04 β^CIQ · ΔCIQLT 마지막 값: 독 넣은 우주(d 뒤)에서 요인 · 창 · QFA 를 다시 → 같다."""
    import numpy as np
    import w_ciq as CQ
    import w_hygiene as H
    rf = {str(k): float(v) for k, v in rf_monthly().items()}
    rng = np.random.default_rng(seed)

    def sig(U, m):
        fac = CQ.market_factors(U, WC.months_between(WC.mshift(m, -(CQ.WIN + 1)), m), rf)
        w = CQ.run_windows(U, [m], fac)[m]
        keys = sorted(w["beta"])
        return {"beta": np.array([w["beta"][k] for k in keys], float), "keys": np.array([float(int(hashlib.sha256(k.encode()).hexdigest()[:12], 16)) for k in keys]),
                "d": np.array([np.nan if w["d_last"] is None else float(w["d_last"])])}
    return H.lookahead_shift(sig, SU, lambda U, m: U.poison_after(m, rng), months, seed, n=n, tol=0.0)


# ══════════════════════════════════════════════════════════════════════════
#  카드 신호(준비 · 굽기 공통 — 같은 코드 · 같은 입력이면 같은 값)
# ══════════════════════════════════════════════════════════════════════════
def w01_signals(ctx, chars):
    import w_ipca as IP
    P = ctx["P"]
    WS = IP.walkforward(P, chars=chars)
    WCa = IP.walkforward(P, chars=chars, cross=ctx["cross"])
    return WS, WCa


def score_dict(P, W, m):
    D = P["m"].get(m)
    d = W["dec"].get(m)
    if D is None or d is None:
        return None
    return {t: float(v) for t, v in zip(D["t"], d["score"])}


def w04_signals(ctx):
    """W04 — 요인(MKT · SMB) · 창 · QFA · β^CIQ · 상태 z · θ_C 경로 · 하방 통제(b_dn · LTD). 신호의 입력은 과거 수익(실자료)."""
    import numpy as np
    import w_ciq as CQ
    import w_ipca as IP
    SU, P, DR, kcol = ctx["U"], ctx["P"], ctx["DR"], ctx["kcol"]
    VD = WC.frozen("v_data")
    rf = {str(k): float(v) for k, v in rf_monthly().items()}
    fac = CQ.market_factors(SU, WC.months_between("2009-02", WC.mshift(IP.LAST_DECISION, 1)), rf)
    wmonths = sorted(set([CQ.FIRST_DECISION] + [m for m in ctx["months"] if m >= CQ.FIRST_DECISION]))
    wins = CQ.run_windows(SU, wmonths, fac)
    dz = CQ.state_z({m: w["d_last"] for m, w in wins.items()}, sorted(wins))
    th_c = {m: CQ.theta_c(dz.get(m)) for m in ctx["dec"]}
    beta = {m: np.array([wins.get(m, {}).get("beta", {}).get(k, np.nan) for k in P["m"][m]["k"]]) for m in ctx["dec"] if m in P["m"]}
    bench = VD.read_json(VD.lab_path("data/bench_px.json"))
    spx = np.array([np.nan if v is None else float(v) for v in bench["series"]["spx"]["px"]], float)
    bpos = {d: i for i, d in enumerate(bench["dates"])}
    with np.errstate(invalid="ignore", divide="ignore"):
        lspx = np.r_[np.nan, np.log(spx[1:] / spx[:-1])]
    ctl = {}
    for m in ctx["dec"]:
        D = P["m"].get(m)
        if D is None:
            continue
        i1 = SU.me_idx[m]
        cols = [kcol[k] for k in D["k"]]
        Rd = DR[i1 - CQ.DN_WIN + 1:i1 + 1][:, cols]
        with np.errstate(invalid="ignore"):
            Rl = np.log1p(Rd)
        mw = np.array([lspx[bpos[x]] if x in bpos else np.nan for x in SU.dates[i1 - CQ.DN_WIN + 1:i1 + 1]])
        ctl[m] = {"b_dn": CQ.downside_beta(Rl, mw), "ltd": CQ.ltd_np(Rd, CQ.market_ex_i(Rd, D["me"]))}
    return {"fac": fac, "wins": wins, "dz": dz, "theta_c": th_c, "beta": beta, "ctl": ctl}


def w10m_signal(P, m):
    import w_cards as CD
    D = P["m"].get(m)
    return None if D is None else CD.xs_z(D["tail"])


def v_crosses(ctx, months):
    """W06 · W12 V 단면(w_panel.v_cross) + 6개월 모멘텀 · 위험조정 쌍둥이 점수(R14)."""
    import numpy as np
    import w_cards as CD
    import w_panel as WP
    SU = ctx["U"]
    out = {}
    for m in months:
        Xv = WP.v_cross(SU, m)
        Xv.mom6 = np.array([np.nan if v is None else v for v in (CD.mom6_of(SU, k, m) for k in Xv.k)], float)
        out[m] = Xv
    return out


def mom6_ra(ctx, Xv, m):
    """R14 — 6개월 수익 ÷ 3년 주간 σ(5거래일 겹치지 않는 묶음 로그수익 · 관측 ≥ 104 주)."""
    import numpy as np
    DR, kcol = ctx["DR"], ctx["kcol"]
    i = ctx["U"].me_idx[m]
    lo = i - 5 * W06_RA_WEEKS + 1
    out = np.full(Xv.n, np.nan)
    if lo < 1:
        return out
    for j, k in enumerate(Xv.k):
        r = DR[lo:i + 1, kcol[k]]
        with np.errstate(invalid="ignore"):
            lr = np.log1p(r)
        wk = lr[: (len(lr) // 5) * 5].reshape(-1, 5)
        ok = np.isfinite(wk).all(1)
        if ok.sum() >= W06_RA_MIN and np.isfinite(Xv.mom6[j]):
            s = float(wk[ok].sum(1).std(ddof=1))
            if s > 0:
                out[j] = float(Xv.mom6[j]) / s
    return out


def w06_arms(ctx, crosses, ms_all, theta=0.75):
    import copy as _copy
    import numpy as np
    import w_cards as CD
    trig = CD.vol_trigger(CD.sp_daily())
    sched = CD.w06_schedule(trig, ms_all)
    arms = CD.v01_arms(crosses, ms_all, sched, theta=theta)
    VK = WC.frozen("v_cards")
    spec = VK.spec_of("V01")
    nobuf = dict(spec, buffer=False)
    ra, prev = {}, None
    for m in ms_all:
        X = crosses.get(m)
        if X is None:
            prev = None
            continue
        if sched.get(m):
            X6 = _copy.copy(X)
            X6.mom = mom6_ra(ctx, X, m)
            mask = VK.select(X6, nobuf, prev=None)
        else:
            mask = VK.select(X, spec, prev=prev)
        w, _ = VK.target_book(X, spec, mask, theta)
        if w is None:
            continue
        ra[m] = X.book(w)
        prev = {X.t[i] for i in np.flatnonzero(mask)}
    arms["W06_RA"] = ra
    return trig, sched, arms


def v02_books(crosses, months, theta=None):
    import numpy as np
    VK = WC.frozen("v_cards")
    spec = VK.spec_of("V02")
    out, prev = {}, None
    for m in months:
        Xv = crosses.get(m)
        if Xv is None:
            continue
        mask = VK.select(Xv, spec, prev=prev)
        w, _ = VK.target_book(Xv, spec, mask, spec["theta0"] if theta is None else theta)
        if w is None:
            continue
        out[m] = (Xv.book(w), Xv.book(Xv.wB))
        prev = {Xv.t[i] for i in np.flatnonzero(mask)}
    return out


def w03_parts(ctx, E=None, blind_seed=None):
    """W03 섹터 수익(🚨 수익 · 신호의 원천도 수익) · 신호 · 결정 달 목표 책(PAP)."""
    import w_ipca as IP
    import w_pap as PP
    SU = ctx["U"]
    hold_s, secs, R = PP.sector_returns(SU, WC.months_between("2009-01", IP.LAST_DECISION), blind_seed=blind_seed)
    Sg = PP.signals_from_returns(R)
    books = {}
    for m in ctx["dec"]:
        Xm = ctx["X"].get(m)
        if Xm is None or m not in hold_s or m in ctx["drift"]:
            continue
        jj = hold_s.index(m)
        Pi, idx = PP.pi_hat(R, Sg, jj)
        if Pi is None:
            continue
        a = PP.sector_active(PP.positions(Pi, Sg[jj, idx]))
        w, _ = PP.pap_book(a, [secs[i] for i in idx], Xm.wB, Xm.sec, Xm.ndx, Xm.beta)
        books[m] = Xm.book(w)
    return {"hold": hold_s, "secs": secs, "R": R, "books": books}


# ══════════════════════════════════════════════════════════════════════════
#  준비 자식 — G-EGD 넘김(θ = 1 책 · 신호 · 비중만)
# ══════════════════════════════════════════════════════════════════════════
GEGD_CARDS_A = ("W01", "W01_KPS7", "W04", "W10m", "W03", "W06", "W12")


def run_prep(ctx, books_path_out, log=_log):
    """G-EGD 넘김 파일(gz JSON · 저장소 밖) — {cards, months{달: {wB, keys, books{카드}, signals{카드}}}}. 수익 통계 없음(신호 · 비중만)."""
    import numpy as np
    import w_ipca as IP
    P, X, dec = ctx["P"], ctx["X"], ctx["dec"]
    t0 = time.time()
    sc = {}
    for tag, chars in (("W01", IP.KPS8), ("W01_KPS7", IP.KPS7)):
        _WS, WCa = w01_signals(ctx, chars)
        sc[tag] = {m: score_dict(P, WCa, m) for m in dec}
    log("  준비 W01(KPS8 · KPS7) · %.0fs" % (time.time() - t0))
    s4 = w04_signals(ctx)
    sc["W04"] = {m: {t: float(b) for t, b in zip(P["m"][m]["t"], s4["beta"][m]) if np.isfinite(b)} for m in dec if m in s4["beta"]}
    sc["W10m"] = {m: {t: float(v) for t, v in zip(P["m"][m]["t"], w10m_signal(P, m)) if np.isfinite(v)} for m in dec if m in P["m"]}
    log("  준비 W04 · W10m · %.0fs" % (time.time() - t0))
    one = lambda m: 1.0
    books = {c: books_path(X, dec, (lambda m, c=c: sc[c].get(m)), one, drift=ctx["drift"]) for c in ("W01", "W01_KPS7", "W04", "W10m")}
    w3 = w03_parts(ctx, blind_seed=(ctx["seed"] + SEED_OFF["w03"] if ctx["kind"] == "blind" else None))
    books["W03"] = w3["books"]
    ms_all = [m for m in ctx["months"] if m <= IP.LAST_DECISION]
    cr = v_crosses(ctx, ms_all)
    _trig, sched, arms = w06_arms(ctx, cr, ms_all, theta=1.0)
    books["W06"] = {m: b for m, b in arms["W06"].items() if m in set(dec)}
    v2 = v02_books(cr, [m for m in ms_all if m >= WC.frozen("v_cards").S_ARM_FROM], theta=1.0)
    books["W12"] = {m: v2[m][0] for m in dec if m in v2}
    log("  준비 W03 · W06 · W12 · %.0fs" % (time.time() - t0))
    sig = dict(sc)
    sig["W03"] = {}
    for m in dec:
        b = books["W03"].get(m)
        Xm = X.get(m)
        if b and Xm is not None:
            sig["W03"][m] = {t: float(b.get(t, 0.0) - Xm.wB[j]) for j, t in enumerate(Xm.t)}
    sig["W06"] = {m: {t: float(v) for t, v in zip(cr[m].t, (cr[m].mom6 if sched.get(m) else cr[m].mom)) if np.isfinite(v)} for m in dec if m in cr}
    sig["W12"] = {m: {t: -float(v) for t, v in zip(cr[m].t, cr[m].beta) if np.isfinite(v)} for m in dec if m in cr}
    doc = {"cards": list(GEGD_CARDS_A), "months": {}, "note": "w_run.run_prep — θ = 1 목표 책 · 신호 · w_B · 가격 키(수익 통계 없음)"}
    for m in dec:
        Xm = X.get(m)
        if Xm is None:
            continue
        d = {"wB": Xm.book(Xm.wB), "keys": {t: k for t, k in zip(Xm.t, Xm.k)}, "books": {}, "signals": {}}
        for c in GEGD_CARDS_A:
            if m in books.get(c, {}):
                d["books"][c] = books[c][m]
                d["signals"][c] = (sig.get(c) or {}).get(m) or {}
        doc["months"][m] = d
    if _inside_repo(books_path_out):
        raise SystemExit("🚨 G-EGD 넘김 파일이 저장소 안이다")
    os.makedirs(os.path.dirname(books_path_out), exist_ok=True)
    with gzip.open(books_path_out, "wt", encoding="utf-8") as f:
        json.dump(_clean(doc), f, ensure_ascii=False)
    return {"n_months": len(doc["months"]), "books": {c: len(books.get(c, {})) for c in GEGD_CARDS_A}, "sec": round(time.time() - t0, 1)}


def gegd_decisions(gegd):
    """R2 — G-EGD 결과 → W01 판(KPS8 | KPS7) · 카드별 통과(fail closed · 칸 없으면 거짓)."""
    cards = (gegd or {}).get("cards") or {}
    p = lambda c: bool((cards.get(c) or {}).get("pass") is True)
    variant = "KPS8" if p("W01") else "KPS7"
    gp = {"W01": p("W01") if variant == "KPS8" else p("W01_KPS7"), "W04": p("W04"), "W10m": p("W10m"), "W03": p("W03"), "W06": p("W06"), "W12": p("W12")}
    labels = {c: (cards.get(c) or {}).get("label", "칸 없음(fail closed)") if c in cards else "칸 없음(fail closed)" for c in GEGD_CARDS_A}
    return {"w01_chars": variant, "gegd_pass": gp, "gegd_label": labels,
            "gegd_summary": {c: {k: (cards.get(c) or {}).get(k) for k in ("n_months", "corr_EG30", "corr_QG30", "ovx_EG30", "ovx_QG30", "spear_abs", "pass")}
                             for c in GEGD_CARDS_A}}


# ══════════════════════════════════════════════════════════════════════════
#  굽기 본체(등록 A · 🚨 수익 통계 — 등록 커밋 뒤 굽기와 눈가린 연기에서만)
# ══════════════════════════════════════════════════════════════════════════
def _caps(smoke):
    return dict(SMOKE_CAPS) if smoke else {"nperm": N_PLACEBO, "leak": None, "plant": None, "pit_la": PIT_LA_N, "ipca_la": IPCA_LA_N,
                                           "w04_la": W04_LA_N, "shuffle": N_W04_SHUFFLE, "fomc": N_FOMC_PLACEBO}


def run_batch_A(ctx, dec_g, smoke=False, clock=None, log=_log):
    """명세 차례대로 한 번(등록 A) — 선견 → 신호 → 위생(fail-closed) → 가족 Tier-1 → Holm → Tier-2 · 무해 → 채택 표시 → 스텝 → 측정만 카드 → 보고 셈."""
    import numpy as np
    import pandas as pd
    import w_cards as CD
    import w_ciq as CQ
    import w_hygiene as H
    import w_ipca as IP
    import w_pap as PP
    import w_stagem as S
    import w_steps as ST
    clock = clock if clock is not None else {}
    cap = _caps(smoke)
    seed = ctx["seed"]
    P, X, E, SU = ctx["P"], ctx["X"], ctx["E"], ctx["U"]
    kind = ctx["pkind"]
    dec, dec_ok, drift = ctx["dec"], ctx["dec_ok"], ctx["drift"]
    chars = IP.KPS8 if dec_g["w01_chars"] == "KPS8" else IP.KPS7
    out = {"reg": "A", "decisions": {"w01_chars": dec_g["w01_chars"], "gegd_pass": dec_g["gegd_pass"], "gegd_label": dec_g["gegd_label"],
                                     "tier1_months": dec_ok, "drift_months": sorted(drift), "w01_months": ctx["w01_ok"],
                                     "kps_fail": ctx["kps"]["fail"]}, "gegd": dec_g.get("gegd_summary"), "stopped": None, "smoke": bool(smoke)}
    tick = lambda k, t0: clock.__setitem__(k, round(time.time() - t0, 1))
    regs = _dm_regs(E)
    # ── 1. 선견(R10) ─────────────────────────────────────────────────────
    t0 = time.time()
    la_ms = [m for m in ctx["months"] if m >= PIT_LA_FROM]
    la = {"pit": pit_lookahead(SU, cap["pit_la"], seed + SEED_OFF["pit_la"], la_ms)}
    tick("lookahead_pit", t0)
    la["ipca"] = ipca_lookahead(P, ctx["cross"], chars, cap["ipca_la"], seed + SEED_OFF["ipca_la"], seed + SEED_OFF["ipca_la"] + 1)
    la["state"] = state_lookahead(ctx["macro"], ctx["months"], SU.d_of)
    la["w04"] = w04_lookahead(SU, [m for m in dec], cap["w04_la"], seed + SEED_OFF["pit_la"] + 2)
    la["ok"] = all(v.get("ok") for v in la.values() if isinstance(v, dict))
    out["lookahead"] = la
    tick("lookahead", t0)
    log("  선견 %s · %.0fs" % (la["ok"], time.time() - t0))
    if not la["ok"] and not smoke:
        out["stopped"] = "선견 점검 실패(%s)" % ", ".join(k for k, v in la.items() if isinstance(v, dict) and not v.get("ok"))
        return out
    # ── 2. 가족 신호 ─────────────────────────────────────────────────────
    t0 = time.time()
    WS, WCa = w01_signals(ctx, chars)
    s4 = w04_signals(ctx)
    tick("signals", t0)
    ms1, ms4 = ctx["w01_ok"], dec_ok
    kC = lambda m: WCa["dec"][m]["score"] if m in WCa["dec"] else None
    kS = lambda m: WS["dec"][m]["score"] if m in WS["dec"] else None
    k4 = lambda m: CD.xs_z(s4["beta"][m]) if m in s4["beta"] else None
    ex4 = lambda m: [("beta_fp", P["m"][m]["beta_fp"]), ("b_dn", s4["ctl"][m]["b_dn"]), ("ltd_np", s4["ctl"][m]["ltd"])]
    ex4b = lambda m: [("beta_fp", P["m"][m]["beta_fp"])]
    k10 = lambda m: w10m_signal(P, m)
    # ── 3. 위생(R10 · fail-closed) ──────────────────────────────────────
    t0 = time.time()
    ex4p = lambda Pp: (lambda m: [("beta_fp", Pp["m"][m]["beta_fp"]), ("b_dn", s4["ctl"][m]["b_dn"]), ("ltd_np", s4["ctl"][m]["ltd"])])
    gseed = seed + SEED_OFF["leak"] + 500                                   # 위생 회마다 부트스트랩 씨앗(회 사이 같다 · 섞기 씨앗이 회를 가른다)
    stat01 = lambda Pp: fm_family(Pp, ms1, lambda m: Pp["m"][m]["sig_w01"] if m in Pp["m"] else None, "ipca_z", +1, H.LEAK_B, gseed + 1, kind=Pp["kind"])
    stat04 = lambda Pp: fm_family(Pp, ms4, lambda m: Pp["m"][m]["sig_w04"] if m in Pp["m"] else None, "ciq_z", +1, H.LEAK_B, gseed + 2, kind=Pp["kind"],
                                  extra_of=ex4p(Pp))
    stat10 = lambda Pp: CD.w10m_line(Pp, months=[m for m in ms4 if m in Pp["m"]], B=H.LEAK_B, seed=gseed + 3)["interaction"]
    P01 = with_signal(P, "sig_w01", kS)                                   # R3 🔁 — 가족 통계 = S 팔 점수
    P04 = with_signal(P, "sig_w04", k4)
    P10 = with_signal(P, "sig_w10", k10)
    hy = {}
    bl = H.blind_panel(P, seed + SEED_OFF["blind_panel"] + 5)
    try:
        tb = [stat01(with_signal(bl, "sig_w01", kS)), stat04(with_signal(bl, "sig_w04", k4)), stat10(bl)]
        hy["blind_smoke"] = {"ok": all(x.get("t") is not None and x.get("p_wild_two") is not None for x in tb), "n": 3,
                             "rule": "가족 셋 주 통계 · 부트스트랩 p 를 y 씨앗 잡음 패널에서 끝까지(값은 버린다)"}
    except Exception as e:                                                  # noqa: BLE001
        hy["blind_smoke"] = {"ok": False, "err": type(e).__name__}
    del bl
    nleak = cap["leak"] or H.LEAK_N
    hy["label_shuffle_leak"] = {c: H.label_shuffle_leak(f, Pp, seed + SEED_OFF["leak"] + j * 1000, n=nleak)
                                for j, (c, f, Pp) in enumerate((("W01", stat01, P01), ("W04", stat04, P04), ("W10m", stat10, P10)))}
    hy["label_shuffle_leak"]["ok"] = all(v["ok"] for v in hy["label_shuffle_leak"].values() if isinstance(v, dict))
    npl = cap["plant"] or H.PLANT_REPS
    need = min(H.PLANT_NEED, npl) if smoke else H.PLANT_NEED
    res01p = H.residualizer(fm_design_of("ipca_z", "sig_w01"))
    res04p = H.residualizer(lambda m, D: fm_design_of("ciq_z", "sig_w04", extra_of=ex4p(P04))(m, D))
    res10p = H.residualizer(fm_design_of("tail_z", "sig_w10"))
    pr = {"W01": H.planted_recovery(stat01, P01, "sig_w01", +1, seed + SEED_OFF["plant"], reps=npl, need=need, resid_of=res01p),
          "W04": H.planted_recovery(stat04, P04, "sig_w04", +1, seed + SEED_OFF["plant"] + 100, reps=npl, need=need, resid_of=res04p)}
    st10, _sd10 = CD.w10m_state(P)                                        # 🔁 가족 교차항과 같은 상태(패널 모든 달의 확장창 · 비평 1 L1)
    good10 = 0
    for i in range(npl):
        tt = stat10(plant_interaction(P10, "sig_w10", st10, H.PLANT_IC, +1, np.random.default_rng(seed + SEED_OFF["plant"] + 200 + i), resid_of=res10p)).get("t")
        good10 += int(tt is not None and tt == tt and tt >= H.PLANT_T)
    pr["W10m"] = {"ok": good10 >= need, "good": good10, "reps": npl, "need": need, "residualized": True,
                  "rule": "교차항 IC %.3f 를 통제로 잔차화한 방향에 심는다(R10 · 가족 교차항과 같은 상태)" % H.PLANT_IC}
    pr["ok"] = all(v["ok"] for v in pr.values() if isinstance(v, dict))
    hy["planted_recovery"] = pr
    hy["lookahead_shift"] = {"ok": la["ok"]}
    f0 = ctx.get("f0_doc") or {}
    same_t1 = (f0.get("tier1_months") or {}).get("months") == ctx["t1"]["months"] if f0 else None
    hy["coverage_f0"] = {"ok": bool(same_t1) if f0 else bool(smoke), "same_as_registered_f0": same_t1, "T": ctx["t1"]["T"]}
    hy["run_all"] = H.run_all_scoped({k: hy[k] for k in H.PIPELINE_GATES + H.CARD_GATES}, WC.FAMILY["A"])
    out["hygiene"] = hy
    tick("hygiene", t0)
    log("  위생 %s · 카드 %s · %.0fs" % (hy["run_all"]["ok"], hy["run_all"]["card_ok"], time.time() - t0))
    del P01, P04, P10
    if not hy["run_all"]["ok"] and not smoke:
        out["stopped"] = "위생 실패(%s)" % ", ".join(hy["run_all"]["failed"] + hy["run_all"]["missing"])
        return out
    card_ok = hy["run_all"]["card_ok"]
    # ── 4. 가족 Tier-1 · Holm ────────────────────────────────────────────
    t0 = time.time()
    t1 = {}
    t1["W01"], res01 = tier1_reports(P, ms1, kS, "ipca_z", +1, IP.IC_LIT, cap["nperm"], seed + SEED_OFF["placebo"])   # R3 🔁 S 팔(명세 primary)
    res01c, t1["W01_C"] = fm_card(P, ms1, kC, "ipca_z", +1)                                                        # C 팔(보고)
    gS = dict(zip(res01["months"], res01["g"]["ipca_z"]))
    gC = dict(zip(res01c["months"], res01c["g"]["ipca_z"]))
    dms = sorted(m for m in gC if m in gS and gC[m] is not None and gS[m] is not None)
    t1["W01_dgamma_C_S"] = S.summarize(dms, [gC[m] - gS[m] for m in dms], +1)
    t1["W04"], res04 = tier1_reports(P, ms4, k4, "ciq_z", +1, CQ.IC_LIT, cap["nperm"], seed + SEED_OFF["placebo"] + 1, extra_of=ex4)
    _, t1["W04_base"] = fm_card(P, ms4, k4, "ciq_z", +1, extra_of=ex4b)
    t1["W04"]["dnbeta_repack"] = CQ.repack_flag(t1["W04_base"]["mean"], t1["W04"]["main"]["mean"])
    w10 = CD.w10m_line(P, months=ms4, B=WC.WILD_B, seed=seed + WC.FAMILY_SEED_OFF["W10m"])
    t1["W10m"] = {"interaction": w10["interaction"], "interaction_scaled": w10["interaction_scaled"], "scaled_same_sign": w10["scaled_same_sign"],
                  "main": w10["main"], "n_state": w10["n_state"]}
    f01 = S.family_fm(res01["months"], res01["g"]["ipca_z"], +1, WC.WILD_B, seed + WC.FAMILY_SEED_OFF["W01"])
    f04 = S.family_fm(res04["months"], res04["g"]["ciq_z"], +1, WC.WILD_B, seed + WC.FAMILY_SEED_OFF["W04"])
    wi = w10["interaction"]
    fk = ("t", "T", "df", "p_wild_one", "p_wild_two", "B", "seed", "direction")
    fam = {"W01": {k: f01.get(k) for k in fk}, "W04": {k: f04.get(k) for k in fk}, "W10m": {k: wi.get(k) for k in fk}}
    for c in fam:
        fam[c]["hygiene_fail"] = not card_ok.get(c, False)
    holm = WC.holm_family(fam, "A", alpha=WC.FAMILY_ALPHA)
    h5m = set(((ctx["t1"].get("sensitivity") or {}).get("count_and_cap_095") or {}).get("months") or [])      # R17 🔁 남은 가격 구멍 민감도(보고)
    t1["H5_sensitivity"] = {"T_months": len(h5m), "rule": "개수 ∧ 시총 몫 ≥ 0.95 달만(엔진 H5 판 · 남은 편출 가격 구멍이 가장 작은 달) — 가족 통계 셋을 같은 식으로(보고 · 가족 밖)",
                            "W01": fm_card(P, [m for m in ms1 if m in h5m], kS, "ipca_z", +1)[1],
                            "W04": fm_card(P, [m for m in ms4 if m in h5m], k4, "ciq_z", +1, extra_of=ex4)[1],
                            "W10m": CD.w10m_line(P, months=[m for m in ms4 if m in h5m])["interaction"]}
    out["tier1"], out["family"] = t1, {"stats": fam, "holm": holm, "note": WC.FAMILY_NOTE, "power": WC.HONEST_POWER}
    tick("tier1_family", t0)
    log("  가족 Tier-1 · Holm · %.0fs" % (time.time() - t0))
    # ── 5. Tier-2(가족 카드 책) · 무해 · 채택 표시 ─────────────────────────
    t0 = time.time()
    th01 = CD.CARDS["W01"]["sleeve"]["theta0"]
    scC = lambda m: score_dict(P, WCa, m)
    scS = lambda m: score_dict(P, WS, m)
    bk = {"W01_S": books_path(X, dec, scS, lambda m: th01, drift=drift), "W01_C": books_path(X, dec, scC, lambda m: th01, drift=drift)}
    sc4 = lambda m: ({t: float(b) for t, b in zip(P["m"][m]["t"], s4["beta"][m]) if np.isfinite(b)} if m in s4["beta"] else None)
    bk["W04_S"] = books_path(X, dec, sc4, lambda m: CQ.THETA0, drift=drift)
    bk["W04_C"] = books_path(X, dec, sc4, lambda m: s4["theta_c"].get(m), drift=drift)
    bk["W04_BETA"] = books_path(X, dec, lambda m: ({t: float(b) for t, b in zip(P["m"][m]["t"], P["m"][m]["beta_fp"]) if np.isfinite(b)} if m in P["m"] else None),
                                lambda m: s4["theta_c"].get(m), drift=drift)
    rfm = {str(k): float(v) for k, v in rf_monthly().items()}
    nag = CQ.nagel_state({m: E.spy_hold(WC.mshift(m, -1)) for m in ctx["months"]}, ctx["months"])
    th_n = {m: CQ.theta_c(nag.get(m)) for m in dec}
    bk["W04_NAGEL"] = books_path(X, dec, sc4, lambda m: th_n.get(m), drift=drift)
    t2 = {k: tier2_arm(E, w_path(E, X, b, dec, drift=drift), regs, k) for k, b in bk.items()}
    tick("tier2_family", t0)
    one = lambda m: 1.0
    b1C = books_path(X, dec, scC, one, drift=drift)
    b14 = books_path(X, dec, sc4, one, drift=drift)
    act01, act04 = frictionless_active(E, X, b1C, dec), frictionless_active(E, X, b14, dec)
    lb01 = IP.linear_baselines(P, chars=chars)
    struct = IP.structural_test(P, {m: WS["dec"][m] for m in ms1 if m in WS["dec"]}, lb01)
    struct["C_arm"] = {k: v for k, v in IP.structural_test(P, {m: WCa["dec"][m] for m in ms1 if m in WCa["dec"]}, lb01).items()
                       if k in ("T", "dm_vs_fm", "dm_vs_ridge", "oos_r2", "dm_t_gt0")}                                   # R20 🔁 보고
    struct["train_note"] = "주 IPCA 학습 2010-01 ~ · 선형 기준선 학습 2014-06 ~(λ̂ 와 같은 PIT 달) — 학습 길이가 다르다 · 같은 길이 판 = PIT_ONLY 쌍둥이(R20)"
    vplus = vplus_block(ctx, [("W01", ms1, kS, "ipca_z", None), ("W04", ms4, k4, "ciq_z", ex4)])                       # R3 🔁 가족 통계 판
    harm = {"W01": t2["W01_C"]["harmless"], "W04": t2["W04_C"]["harmless"], "W10m": {"harmless": False, "why": "책 없음 — T+1 행 없음(R4)"}}
    caut = {"W01": {"dm_t_gt0": struct.get("dm_t_gt0"), "dm_t_gt0_C": struct["C_arm"].get("dm_t_gt0"), "v_repack": vplus["W01"]["v_repack"],
                    "hygiene_card_ok": card_ok.get("W01")},
            "W04": {"dnbeta_repack": t1["W04"]["dnbeta_repack"], "v_repack": vplus["W04"]["v_repack"], "hygiene_card_ok": card_ok.get("W04")},
            "W10m": {"mechanical_scaling_same_sign": w10["scaled_same_sign"], "hygiene_card_ok": card_ok.get("W10m")}}
    adopt = WC.adoption_table(holm, harm, {c: dec_g["gegd_pass"].get(c) for c in ("W01", "W04", "W10m")}, caut)
    out["tier2"], out["adoption"] = t2, adopt
    out["tier2_delta"] = {"W01_C_minus_S": delta_arm(t2["W01_C"], t2["W01_S"], regs), "W04_C_minus_S": delta_arm(t2["W04_C"], t2["W04_S"], regs),
                          "W04_C_minus_BETA": delta_arm(t2["W04_C"], t2["W04_BETA"], regs), "W04_C_minus_NAGEL": delta_arm(t2["W04_C"], t2["W04_NAGEL"], regs)}
    out["structural_W01"], out["vplus"] = struct, vplus
    log("  Tier-2 · 채택 표시 · %.0fs" % (time.time() - t0))
    # ── 6. W01 쌍둥이 · 대조 · 스텝 ──────────────────────────────────────
    t0 = time.time()
    tw = {}
    gam_cfg = {"S": dict(zip(res01["months"], res01["g"]["ipca_z"]))}
    for nm, spec in IP.TWIN_SPECS.items():
        Wt = IP.walkforward(P, chars=chars, **spec)
        rr, smt = fm_card(P, [m for m in ms1 if m in Wt["dec"]], lambda m, Wt=Wt: Wt["dec"][m]["score"] if m in Wt["dec"] else None, "ipca_z", +1)
        tw[nm] = smt
        gam_cfg[nm] = dict(zip(rr["months"], rr["g"]["ipca_z"]))
        if nm == "PIT_ONLY":                                                                                           # R20 🔁 같은 학습 길이 DM(보고)
            out["structural_W01"]["PIT_ONLY"] = {k: v for k, v in IP.structural_test(P, {m: Wt["dec"][m] for m in ms1 if m in Wt["dec"]}, lb01).items()
                                                 if k in ("T", "dm_vs_fm", "dm_vs_ridge", "oos_r2", "dm_t_gt0")}
    _, tw["LIT_COMPOSITE"] = fm_card(P, ms1, lambda m: IP.lit_composite(P["m"][m], chars) if m in P["m"] else None, "lit_z", +1)
    out["twins_W01"] = tw
    out["steps"] = steps_block(ctx, P, X, E, WCa, scC, th01, ms1, regs, t2["W01_C"], cap, seed)
    zz = {m: s4["dz"].get(m) for m in dec}
    sh = []
    for i in range(cap["shuffle"]):
        zs = CQ.block_shuffle(zz, dec, CQ.BLOCK, seed + SEED_OFF["w04_shuffle"] + i)
        sh.append(theta_stat({m: CQ.theta_c(v) for m, v in zs.items()}, CQ.THETA0, act04))
    obs4 = theta_stat(s4["theta_c"], CQ.THETA0, act04)
    out["w04_c_arm"] = {"stat_obs": obs4, "shuffle_rank": pct_rank(obs4, sh, +1), "n_shuffle": cap["shuffle"],
                        "theta_ge_075": sum(1 for m in dec if (s4["theta_c"].get(m) or 0) >= 0.75), "rule": "R7 마찰 없는 능동수익 · 12개월 블록 섞기"}
    yn = {m: E.spy_hold(m) - rfm.get(WC.mshift(m, 1), 0.0) for m in dec}
    out["w04_ts"] = CQ.ts_measure(kind if kind != "f0" else "blind", dec, {m: -(s4["wins"].get(m, {}).get("d_last") or np.nan) for m in dec}, yn)
    out["w04_twin_capm"] = w04_capm_twin(ctx, s4, ms4)
    tick("w01_twins_steps_w04", t0)
    log("  W01 쌍둥이 · 스텝 · W04 대조 · %.0fs" % (time.time() - t0))
    # ── 7. 측정만 카드 W03 · W06 · W12 ───────────────────────────────────
    t0 = time.time()
    out["W03"] = w03_block(ctx, E, regs, cap, seed)
    tick("W03", t0)
    t1_ = time.time()
    out["W06"], out["W12"] = w06_w12_block(ctx, E, regs, cap, seed)
    tick("W06_W12", t1_)
    log("  측정만 W03 · W06 · W12 · %.0fs" % (time.time() - t0))
    # ── 8. 보고 셈 — BY · PBO · 기대 효과 · DSR · 팔 수 ────────────────────
    t0 = time.time()
    out["secondary_BY"] = by_block(out)
    out["pbo"] = pbo_block(gam_cfg, dict(zip(res04["months"], res04["g"]["ciq_z"])), out, res01, w10)
    out["expected_effect"] = eb_block(fam)
    out["n_arms"] = count_arms(out)
    out["cumulative_N"] = {"lab": LAB_N_BASE, "w_arms_A": out["n_arms"]["total"], "total": LAB_N_BASE + out["n_arms"]["total"]}
    try:
        out["dsr_W01"] = S.dsr(np.array([v for v in res01["g"]["ipca_z"] if v is not None], float), LAB_N_BASE + out["n_arms"]["total"])
    except Exception as e:                                                  # noqa: BLE001
        out["dsr_W01"] = {"err": type(e).__name__}
    tick("reports", t0)
    return out


def vplus_block(ctx, specs):
    """R9 — V-플러스 FM(보고 · 주의 칸): 주 FM 에 V02 · V03 · V04 · V05 신호를 더한다(V07 뺌 · V01 · V06 은 이미 통제)."""
    import numpy as np
    import w_cards as CD
    VE, VI = WC.frozen("v_ear"), WC.frozen("v_ins")
    SU, P = ctx["U"], ctx["P"]
    Ea, In = VE.Earnings(SU), VI.Insider()
    WG.assert_units([WG.unit("v02_lowbeta", source="data/pit_px.json", concept="V02 low beta (FP)", use="control"),
                     WG.unit("v03_irrx", source="data/earn_dates.json + data/pit_px.json", concept="V03 IRRX liquidity-provision reversal", use="control"),
                     WG.unit("v04_ob", source="data/_ins_pit/cikmonth.json", concept="V04 opportunistic insider net buy flag", use="control"),
                     WG.unit("v04_os", source="data/_ins_pit/cikmonth.json", concept="V04 opportunistic insider net sell flag", use="control"),
                     WG.unit("v05_car", source="data/earn_dates.json + data/pit_px.json", concept="V05 earnings announcement CAR", use="control")],
                    "w_run V-플러스")
    memo = {}

    def vx(m):
        if m in memo:
            return memo[m]
        D = P["m"][m]
        ir, ea, fl = Ea.irrx_inputs(m), Ea.ear_inputs(m), In.flags(SU, m)
        s3 = np.array([np.nan if (ir.get(t) or {}).get("s") is None else float(ir[t]["s"]) for t in D["t"]], float)
        car = np.array([float(ea[t]["car"]) if (ea.get(t) or {}).get("eligible") else np.nan for t in D["t"]], float)
        ob = np.array([1.0 if fl.get(t) == "OB" else 0.0 for t in D["t"]])
        os_ = np.array([1.0 if fl.get(t) == "OS" else 0.0 for t in D["t"]])
        memo[m] = [("v02_lowbeta", CD.xs_z(-np.asarray(D["beta_fp"], float))), ("v03_irrx", CD.xs_z(s3)), ("v04_ob", ob), ("v04_os", os_),
                   ("v05_car", CD.xs_z(car))]
        return memo[m]
    out = {}
    for card, months, key_of, name, extra_of in specs:
        ms = [m for m in months if m in P["m"]]
        _, base = fm_card(P, ms, key_of, name, +1, extra_of=extra_of)
        _, plus = fm_card(P, ms, key_of, name, +1, extra_of=lambda m: list(extra_of(m) if extra_of else []) + vx(m))
        rp = None
        if base["mean"] is not None and plus["mean"] is not None and base["mean"] != 0:
            rp = bool(abs(plus["mean"]) < 0.5 * abs(base["mean"]) or np.sign(plus["mean"]) != np.sign(base["mean"]))
        out[card] = {"base": base, "plus": plus, "v_repack": rp, "rule": "R9 — γ 가 절반 넘게 줄거나 부호가 바뀌면 «V 재포장»(주의 칸)"}
    return out


def w04_capm_twin(ctx, s4, months):
    """W04 쌍둥이 — CAPM 잔차판(MKT 만) FM(보고)."""
    import numpy as np
    import w_cards as CD
    import w_ciq as CQ
    SU, P = ctx["U"], ctx["P"]
    beta = {}
    for m in months:
        mem = SU.members(m)
        keys = sorted({r["k"] for r in mem})
        wm = CQ.window_matrix(SU, keys, m, s4["fac"])
        if wm is None:
            continue
        R_ex, mx, smb, _ = wm
        w = CQ.ciq_window(R_ex, mx, smb, capm_only=True)
        bm = {k: float(b) for k, b in zip(keys, w["beta"]) if np.isfinite(b)}
        beta[m] = np.array([bm.get(k, np.nan) for k in P["m"][m]["k"]]) if m in P["m"] else None
    ex4 = lambda m: [("beta_fp", P["m"][m]["beta_fp"]), ("b_dn", s4["ctl"][m]["b_dn"]), ("ltd_np", s4["ctl"][m]["ltd"])]
    res, sm = fm_card(P, [m for m in months if beta.get(m) is not None], lambda m: CD.xs_z(beta[m]) if beta.get(m) is not None else None, "ciq_z", +1,
                      extra_of=ex4)
    return {"fm": sm, "gamma": dict(zip(res["months"], res["g"]["ciq_z"]))}


def steps_block(ctx, P, X, E, WCa, scC, th0, ms1, regs, t2C, cap, seed):
    """R6 — W01 C 위 스텝(각 Δ 따로): +S3e → +S2 → +S1(트랜치)."""
    import numpy as np
    import pandas as pd
    import w_cards as CD
    import w_ipca as IP
    import w_stagem as S
    import w_steps as ST
    C = WC.frozen("v_core")
    dec, drift, kind = ctx["dec"], ctx["drift"], P["kind"]
    ms = [m for m in ms1 if m in P["m"] and m in WCa["dec"]]
    ics = S.ic_series(ms, lambda m: WCa["dec"][m]["score"], lambda m: S.sector_demean(P["m"][m]["y"], P["m"][m]["sec"]), kind)
    icm = dict(zip(ics["months"], ics["ic"]))
    s3 = ST.s3e_theta(icm, dec, th0)
    b3 = books_path(X, dec, scC, lambda m: s3["theta"].get(m), drift=drift)
    t3 = tier2_arm(E, w_path(E, X, b3, dec, drift=drift), regs, "W01_C_S3e")
    # +S2(S3e 위)
    lt = ST.lag_ic_table(kind, ms, lambda m: scC(m) or {}, lambda m: {t: float(v) for t, v in zip(P["m"][m]["t"], P["m"][m]["y"]) if v == v} if m in P["m"] else None)
    sig_cs = {}
    for m in dec:
        if m[5:7] == ST.S2_UPDATE_MONTH:
            v = [float(np.nanstd(P["m"][s]["y"], ddof=1)) for s in ms if WC.mshift(s, 1) <= m and s in P["m"]]
            sig_cs[m] = float(np.mean(v)) if v else None
    sch = ST.s2_schedule(dec, {m: ST.lag_ic_asof(lt, m) for m in dec if m[5:7] == ST.S2_UPDATE_MONTH}, IP.IC_LIT, sig_cs)
    n_tr = {}

    def ex_s2(m, Ed, T):
        sc = sch.get(m) or {}
        if not sc.get("sigma_cs"):
            b, tr, skp = CD.execute(Ed, T)
            n_tr[m] = None
            return b, tr, skp
        zs = ST.s2_aim([scC(m) or {}, scC(WC.mshift(m, -1)) or {}, scC(WC.mshift(m, -2)) or {}], sc["omega"])
        trd = ST.s2_tradable({k: zs.get(k, 0.0) for k in set(T) | set(Ed)}, sc["ic0"], sc["sigma_cs"], sc["H"])
        b, _tr, info = ST.s2_execute(Ed, T, trd)
        b2, tr2, skp = CD.turnover_skip(Ed, b)
        n_tr[m] = info.get("n_trad")
        return b2, tr2, skp
    t32 = tier2_arm(E, w_path(E, X, b3, dec, drift=drift, executor=ex_s2), regs, "W01_C_S3e_S2")
    # +S1(S3e 위 · 트랜치)
    SU = ctx["U"]
    Mx = E.matrix()
    kcol = ctx["kcol"]
    me_idx = [SU.me_idx[m] for m in dec] + [SU.me_idx[WC.mshift(dec[-1], 1)]]
    maps = {m: dict(zip(X[m].t, X[m].k)) for m in dec if m in X}
    me_sorted = [(SU.me_idx[m], m) for m in dec]

    def kmap_of(d):
        j = max([mm for i, mm in me_sorted if i <= d], default=None)
        out_ = {}
        if j is None:
            return out_
        jj = dec.index(j)
        for mm in reversed(dec[max(0, jj - 3):jj + 1]):
            for t, k in (maps.get(mm) or {}).items():
                out_.setdefault(t, k)
        return out_
    km_cache = {}

    def day_ret(d):
        if d >= SU.D:
            return None
        if d not in km_cache:
            km_cache.clear()
            km_cache[d] = kmap_of(d)
        km = km_cache[d]
        row = Mx[d]
        return {t: (float(row[kcol[k]]) if np.isfinite(row[kcol[k]]) else 0.0) for t, k in km.items()}

    def tgt(k, j, d):
        return b3.get(dec[j]) if j < len(dec) else None
    s1 = {}
    for tag, rate in (("10", CD.COST), ("20", CD.COST_ROBUST)):
        tp = ST.tranche_path(kind if kind != "f0" else "blind", SU.D, me_idx, tgt, day_ret, rate=rate)
        s1[tag] = tp
    hold = lambda tp: pd.Series({pd.Period(dec[j - 1], "M") + 1: v for j, v in tp["month_ret"].items() if j - 1 < len(dec)}, dtype=float).sort_index()
    B = E.spy_monthly()
    X10 = C.fund_x(hold(s1["10"]), B.reindex(hold(s1["10"]).index), CD.COST)
    X20 = C.fund_x(hold(s1["20"]), B.reindex(hold(s1["20"]).index), CD.COST_ROBUST)
    VT = WC.frozen("v_tests")
    X10 = X10.loc[VT.in_win(X10.index, *VT.S_WIN)]
    X20 = X20.loc[VT.in_win(X20.index, *VT.S_WIN)]
    t31 = {"name": "W01_C_S3e_S1", "n": int(len(X10)), "X10": X10, "X20": X20, "h1_10": VT.h1(X10), "h1_20": VT.h1(X20), "beta_adj": VT.beta_adj_alpha(X10, regs),
           "turn_tranche": WC.turnover_annual(list(s1["10"]["traded"].values()), len(X10)) if len(X10) else None}
    luck = {}
    for k in ST.S1_OFFSETS:
        tp = ST.tranche_path(kind if kind != "f0" else "blind", SU.D, me_idx, tgt, day_ret, offsets=(k,), rate=CD.COST)
        xk = C.fund_x(hold(tp), B.reindex(hold(tp).index), CD.COST)
        luck[k] = [float(v) for v in xk.loc[VT.in_win(xk.index, *VT.S_WIN)].dropna().tolist()]
    t31["luck"] = ST.luck_report(luck)
    b1 = books_path(X, dec, scC, lambda m: 1.0, drift=drift)
    act = frictionless_active(E, X, b1, dec)
    shs = ST.s3e_shuffle(icm, dec, th0, cap["shuffle"] if cap["shuffle"] < N_S3E_SHUFFLE else N_S3E_SHUFFLE, seed + SEED_OFF["s3e_shuffle"])
    obs = theta_stat(s3["theta"], th0, act)
    return {"S3e": {"arm": t3, "delta": delta_arm(t3, t2C, regs), "theta_path_n": len(s3["theta"]), "e_max": s3["e_max"],
                    "theta_mean": float(np.mean(list(s3["theta"].values()))) if s3["theta"] else None,
                    "shuffle_rank": pct_rank(obs, [theta_stat(th, th0, act) for th in shs], +1), "n_shuffle": len(shs),
                    "e_value_note": "W 는 언제나-유효 e-값으로도 보고(표본 안 · 전방 판정 없음 · 사용자 갱신 가)"},
            "S2": {"arm": t32, "delta": delta_arm(t32, t3, regs), "n_updates": sum(1 for m in dec if (sch.get(m) or {}).get("updated_at") == m),
                   "rule_off_months": sum(1 for m in dec if not (sch.get(m) or {}).get("sigma_cs"))},
            "S1": {"arm": t31, "delta": delta_arm(t31, t3, regs)}}


def w03_block(ctx, E, regs, cap, seed):
    """W03 PAP(측정만) — 주 통계 · 대각 · PEP+PAP · S 열 섞기 위약 · 내부 L 쌍둥이(20년 · 공개 안 함) · 책 경로 X. 🚨 수익."""
    import numpy as np
    import w_pap as PP
    kind = ctx["pkind"]
    blind = ctx["kind"] == "blind"
    w3 = w03_parts(ctx, blind_seed=(ctx["seed"] + SEED_OFF["w03"] if blind else None))
    hold_s, R = w3["hold"], w3["R"]
    res = {"pap": PP.primary(kind, hold_s, R), "diag": PP.primary(kind, hold_s, R, arm="diag"), "pep_pap": PP.primary(kind, hold_s, R, arm="pep_pap")}
    npl = min(cap["nperm"], N_W03_PLACEBO)
    pl = PP.placebo(kind, hold_s, R, int(npl), seed + SEED_OFF["w03"])
    res["placebo"] = {"n": int(npl), "rank": pct_rank(res["pap"]["summary"]["nw_t"], pl["t"], +1)}
    VD = WC.frozen("v_data")
    fr = VD.french("ind49", "vw_m")
    if blind:
        rng = np.random.default_rng(seed + SEED_OFF["w03"] + 1)
        fr = fr.where(fr.isna(), rng.normal(0.008, 0.05, fr.shape))
    lt = PP.l_twin(kind, fr)
    res["l_twin_internal"] = lt
    sm, pap = lt["summary"], res["pap"]["summary"]
    res["l_twin_public"] = {"first_hold": lt["first_hold"], "T": sm.get("T"), "n_assets": lt["n_assets"], "layer": lt["layer"],
                            "same_sign_as_S": (None if (sm.get("mean") is None or pap.get("mean") is None) else bool((sm["mean"] > 0) == (pap["mean"] > 0))),
                            "clean_T": (lt["clean_summary"] or {}).get("T")}
    res["tier2"] = tier2_arm(E, w_path(E, ctx["X"], w3["books"], ctx["dec"], drift=ctx["drift"]), regs, "W03_PAP")
    res["twin_24_industry_groups"] = "삭제(F0 허용 결정 — 24 산업그룹 PIT 파싱 빌드가 서지 않았다)"
    return res


def w06_w12_block(ctx, E, regs, cap, seed):
    """W06 MOM-CR · W12 FOMC-SML(측정만). 🚨 수익."""
    import bisect
    import numpy as np
    import w_cards as CD
    import w_ipca as IP
    SU, DR, kcol = ctx["U"], ctx["DR"], ctx["kcol"]
    kind = ctx["pkind"]
    dec = ctx["dec"]
    ms_all = [m for m in ctx["months"] if m <= IP.LAST_DECISION]
    cr = v_crosses(ctx, ms_all)
    trig, sched, arms = w06_arms(ctx, cr, ms_all)
    trig_ms = [m for m in dec if (trig.get(m) or {}).get("trig")]
    Mx = E.matrix()
    tk = {}
    for m in ms_all:
        for t, k in zip(cr[m].t, cr[m].k):
            tk.setdefault(t, {})[m] = k

    names6 =sorted({t for a in ("W06", "V01_S0", "CTRL12", "W06_RA") for m in trig_ms for t in arms[a].get(m, {})})
    tk6 = {t: tk[t] for t in names6 if t in tk}

    def dret6(i):
        if i >= SU.D:
            return None
        row = Mx[i]
        out = {}
        for t, ks in tk6.items():
            best = max((m for m in ks if SU.me_idx[m] <= i), default=None)
            if best is not None and np.isfinite(row[kcol[ks[best]]]):
                out[t] = float(row[kcol[ks[best]]])
        return out
    di = {m: SU.me_idx[m] for m in trig_ms}
    w06 = {"n_trig_S": len(trig_ms), "trig_months": trig_ms,
           "events_W06_vs_V01": CD.event_windows(kind, arms["W06"], arms["V01_S0"], di, dret6),
           "events_CTRL12_vs_V01": CD.event_windows(kind, arms["CTRL12"], arms["V01_S0"], di, dret6),
           "events_RA_vs_V01": CD.event_windows(kind, arms["W06_RA"], arms["V01_S0"], di, dret6)}
    t2 = {a: tier2_arm(E, w_path(E, ctx["X"], {m: b for m, b in arms[a].items() if m in set(dec)}, dec, drift=ctx["drift"]), regs, a)
          for a in ("V01_S0", "W06", "CTRL12", "W06_RA")}
    w06["tier2"] = t2
    w06["delta_W06_V01"] = delta_arm(t2["W06"], t2["V01_S0"], regs)
    w06["delta_CTRL12_V01"] = delta_arm(t2["CTRL12"], t2["V01_S0"], regs)
    on = sorted({WC.mshift(m, 1) for m in dec if sched.get(m)})
    dd = (w06["delta_W06_V01"] or {}).get("series")
    if dd is not None:
        import pandas as pd
        v = dd.reindex(pd.PeriodIndex(on, freq="M")).dropna()
        w06["delta_in_trigger_windows"] = {"n": int(len(v)), "mean": float(v.mean()) if len(v) else None}
    w06["label"] = "사건 측정만" if (len(trig_ms) * 2 < 12 or len(trig_ms) < 4) else None
    # ── W12 ─────────────────────────────────────────────────────────────
    cal = CD.fomc_calendar(fetch=False)
    fdays = set(cal["dates"])
    B = CD.rolling_beta(DR, ctx["mkt_d"])
    Y = Mx
    me_sorted = sorted(SU.me_idx, key=lambda z: SU.me_idx[z])
    me_pos = [SU.me_idx[z] for z in me_sorted]
    days = [i for i, d in enumerate(SU.dates) if CD.FOMC_T1[0] <= d[:7] <= CD.FOMC_T1[1]]
    memo = {}

    def last_me(i):
        j = bisect.bisect_left(me_pos, i) - 1
        return me_sorted[j] if j >= 0 else None

    def sec_of_day(i):
        m = last_me(i)
        if m is None:
            return None, None
        if m not in memo:
            mask = np.zeros(DR.shape[1], bool)
            sec = np.full(DR.shape[1], None, object)
            for r in SU.members(m):
                j = kcol.get(r["k"])
                s_, _ = SU.sector(r["t"], m, r["ndx_only"])
                if j is not None and s_ is not None:
                    mask[j] = True
                    sec[j] = s_
            memo[m] = (mask, sec)
        return memo[m]
    g = CD.daily_sml(kind, days, Y, B, sec_of_day)
    w12 = {"sml": CD.fomc_slope_test(kind, g, lambda i: SU.dates[i] in fdays), "n_fomc_T1": sum(1 for i in days if SU.dates[i] in fdays),
           "calendar_n": cal["n"], "calendar_by_year": cal["by_year"]}
    v2 = v02_books(cr, [m for m in ms_all if m >= WC.frozen("v_cards").S_ARM_FROM])
    fd_idx = [i for i in days if SU.dates[i] in fdays]

    def active_of(i):
        m = last_me(i)
        if m not in v2:
            return None
        b, wb = v2[m]
        return {k: b.get(k, 0.0) - wb.get(k, 0.0) for k in set(b) | set(wb)}
    kmap = {m: (list(cr[m].t), np.array([kcol[k] for k in cr[m].k], int)) for m in cr}

    def dret(i):
        """그날 평가 수익 {티커: r}(그날 앞 마지막 월말 명단 · 결측은 뺀다 → 효과 식에서 0)."""
        if i >= SU.D:
            return None
        m = last_me(i)
        if m is None or m not in kmap:
            return {}
        names, cols = kmap[m]
        row = Mx[i, cols]
        return {t: float(v) for t, v in zip(names, row) if np.isfinite(v)}
    eff = CD.fomc_step_effect(kind, fd_idx, active_of, dret)
    avec = {}
    for m, (b, wb) in v2.items():
        if m in kmap:
            names, cols = kmap[m]
            a = np.array([b.get(t, 0.0) - wb.get(t, 0.0) for t in names], float)
            avec[m] = (cols, a, float(np.abs(a).sum()))

    def eff_vec(i):
        """R15 — 같은 식의 벡터판(−a′r − 2c·Σ|a|) · 대조 200 벌을 빠르게 · 실제 발표일에서 w_cards.fomc_step_effect 와 같아야 한다."""
        m = last_me(i)
        if m not in avec:
            return None
        cols, a, g = avec[m]
        return float(-(a @ np.nan_to_num(Mx[i, cols])) - 2.0 * CD.COST * g)
    same = all(abs(eff_vec(i) - v) <= 1e-12 for i, v in eff.items())
    nfp = min(cap["fomc"], N_FOMC_PLACEBO)
    pl = CD.fomc_placebo_days([i for i in days if SU.dates[i] not in fdays], len(fd_idx), int(nfp), seed + SEED_OFF["fomc"])
    tot = sum(eff.values())
    pls = [sum(v for v in (eff_vec(i) for i in ds) if v is not None) for ds in pl]
    w12["step"] = {"n_days": len(eff), "sum": tot, "placebo_n": int(nfp), "placebo_rank": pct_rank(tot, pls, +1), "vec_same_as_card_fn": bool(same)}
    base = tier2_arm(E, w_path(E, ctx["X"], {m: v2[m][0] for m in dec if m in v2}, dec, drift=ctx["drift"]), regs, "V02_S0")
    w12["tier2_V02"] = base
    if base.get("n"):
        import pandas as pd
        add = {}
        for i, e in eff.items():
            h = pd.Period(SU.dates[i][:7], "M")
            add[h] = add.get(h, 0.0) + e
        Xs = base["X10"] + 0.1 * pd.Series(add, dtype=float).reindex(base["X10"].index).fillna(0.0)
        VT = WC.frozen("v_tests")
        w12["tier2_step_X10"] = {"h1": VT.h1(Xs), "delta": VT.h1(Xs - base["X10"]), "rule": "R15 — 날 효과 합을 그달 슬리브 수익에 더한다(펀드 몫 0.1)"}
        wins = {str(h) for h in base["X10"].index}
        step_trade = 0.0
        for i in eff:
            h = str(pd.Period(SU.dates[i][:7], "M"))
            m_ = last_me(i)
            if h in wins and m_ in avec:
                step_trade += 2.0 * avec[m_][2]                             # d−1 종가에 Σ|a| 로 w_B · d 종가에 Σ|a| 되돌림
        yrs = base["n"] / 12.0
        add_turn = (0.5 * step_trade / yrs) if yrs else None               # 편도(½ Σ 거래 / 해 · v_core.turnover_annual 과 같은 식)
        tot = (base["turn"] + add_turn) if (base.get("turn") is not None and add_turn is not None) else None
        w12["tier2_step_X10"]["turn"] = {"base_V02": base.get("turn"), "step_add": add_turn, "total": tot,
                                         "turn_le10": (None if tot is None else bool(tot <= WC.TURN_MAX)),
                                         "rule": "R19 — 스텝 팔 편도 연 회전 = V02 회전 + Σ_d Σ|a_d| / 해(측정만 · 표시와 무관)"}
    return w06, w12


def by_block(out):
    """R11 — 부 가족 BY q 0.10(보고): 한쪽 p 모음."""
    import w_stagem as S
    t1 = out.get("tier1") or {}
    pv = {}

    def add(nm, sm, d=+1):
        if sm and sm.get("nw_t") is not None and sm.get("T"):
            pv[nm] = WC.one_sided_p(sm["nw_t"], sm["T"], d)
    add("W01", (t1.get("W01") or {}).get("main"))
    add("W01_C", t1.get("W01_C"))
    add("W01_dgamma", t1.get("W01_dgamma_C_S"))
    add("W04", (t1.get("W04") or {}).get("main"))
    it = (t1.get("W10m") or {}).get("interaction") or {}
    if it.get("t") is not None:
        pv["W10m"] = it.get("p_one")                                            # t(n − 2)(S4)
    its = (t1.get("W10m") or {}).get("interaction_scaled") or {}
    if its.get("t") is not None:
        pv["W10m_scaled"] = its.get("p_one")
    add("W03", ((out.get("W03") or {}).get("pap") or {}).get("summary"))
    sml = ((out.get("W12") or {}).get("sml") or {})
    if sml.get("t") is not None:
        pv["W12"] = WC.one_sided_p(sml["t"], sml["T"], +1)
    for nm, d in (out.get("tier2_delta") or {}).items():
        if d and (d.get("h1") or {}).get("p") is not None:
            pv["T2_" + nm] = d["h1"]["p"]
    for nm in ("S3e", "S2", "S1"):
        d = ((out.get("steps") or {}).get(nm) or {}).get("delta")
        if d and (d.get("h1") or {}).get("p") is not None:
            pv["step_" + nm] = d["h1"]["p"]
    pv = {k: v for k, v in pv.items() if v is not None}
    r = S.by_info(pv, 0.10) if pv else {"admitted": []}
    return {"pvals_n": len(pv), "q": 0.10, "k": r.get("k"), "admitted": r.get("admitted"), "pvals": pv}


def pbo_block(gam_cfg, g04, out, res01, w10):
    """R12 — PBO/CSCV(보고)."""
    import numpy as np
    import w_stagem as S

    def mat(cols):
        ms = sorted(set.intersection(*[set(k for k, v in c.items() if v is not None) for c in cols.values()])) if cols else []
        if len(ms) < 32:
            return None, len(ms)
        return np.array([[cols[c][m] for c in cols] for m in ms], float), len(ms)
    res = {}
    M, n = mat({k: v for k, v in gam_cfg.items() if k in ("S", "K1", "K2", "K4", "UNRESTRICTED", "LAM_SE")})
    res["W01_config"] = S.pbo_cscv(M) if M is not None else {"n_months": n, "pbo": None}
    tw = (out.get("w04_twin_capm") or {}).get("gamma") or {}
    M, n = mat({"main": g04, "capm": tw})
    res["W04_config"] = S.pbo_cscv(M) if M is not None else {"n_months": n, "pbo": None}
    return res


def eb_block(fam):
    """R13 — 가족 주 t 의 경험적 베이즈 수축(보고)."""
    ts = [v["t"] for v in fam.values() if v.get("t") is not None]
    if not ts:
        return None
    tau2 = max(0.0, sum(t * t for t in ts) / len(ts) - 1.0)
    k = tau2 / (1.0 + tau2)
    return {"tau2": tau2, "shrink": k, "t_shrunk": {c: (v["t"] * k if v.get("t") is not None else None) for c, v in fam.items()},
            "themes": {"W01": "JKP 여러 주제(모멘텀 · 크기 · 단기반전 · 저위험)의 조건부 결합", "W04": "JKP 저위험 · 꼬리", "W10m": "JKP 왜도 · 꼬리"},
            "rule": "R13 — t × τ̂²/(1 + τ̂²) · τ̂² = max(0, mean t² − 1)"}


def count_arms(out):
    """누적 N 에 더할 팔(이 굽기가 수익 통계를 계산한 서로 다른 신호 · 책 설정)."""
    t1 = out.get("tier1") or {}
    n_t1 = sum(1 for k in ("W01", "W01_C", "W04", "W04_base", "W10m") if k in t1) + int(bool((t1.get("W10m") or {}).get("interaction_scaled"))) + \
        len(out.get("twins_W01") or {}) + \
        int(bool(out.get("w04_twin_capm"))) + int(bool(out.get("w04_ts"))) + int(bool(out.get("structural_W01"))) * 2 + len(out.get("vplus") or {}) + \
        (3 if out.get("W03") else 0) + int(bool((out.get("W03") or {}).get("l_twin_internal"))) + int(bool((out.get("W12") or {}).get("sml")))
    n_t2 = len(out.get("tier2") or {}) + 3 + int(bool((out.get("W03") or {}).get("tier2"))) + len(((out.get("W06") or {}).get("tier2")) or {}) + \
        int(bool((out.get("W12") or {}).get("tier2_V02"))) + int(bool((out.get("W12") or {}).get("tier2_step_X10"))) + \
        len(((out.get("W06") or {}).get("events_W06_vs_V01")) or {}) * 0
    return {"tier1": n_t1, "tier2": n_t2, "total": n_t1 + n_t2, "rule": "Tier-1 수익 통계(주 · 쌍둥이 · 대조 · V-플러스 · 구조) + Tier-2 책 팔(스텝 셋 포함)"}


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸(R16 · 결과 문서는 이 사전의 칸만 옮긴다)
# ══════════════════════════════════════════════════════════════════════════
PUB_SM = ("T", "mean", "sd", "nw_t", "p_one", "p_wild_one", "p_wild_two", "B", "first", "last", "contiguous", "gaps")
PUB_H1 = ("n", "mean", "ann", "te", "ir", "t", "t12", "p", "first", "last")


def _pk(d, keys):
    return None if not isinstance(d, dict) else {k: d.get(k) for k in keys if k in d}


def _b(v):
    if v is None:
        return None
    return bool(v)


def _pub_t2(a):
    if not a or not a.get("n"):
        return {"n": 0}
    st = a.get("s_tests") or {}
    bd = st.get("bundle") or {}
    yr = (bd.get("years") or {})
    return {"n": a["n"], "h1_10": _pk(st.get("h1_10"), PUB_H1), "h1_20": _pk(st.get("h1_20"), PUB_H1), "h1_d0": _pk(st.get("h1_d0"), PUB_H1),
            "h1_ew": _pk(st.get("h1_ew"), PUB_H1), "turn": a.get("turn"), "harmless": a.get("harmless"), "beta_adj": _pk(a.get("beta_adj"), ("n", "a", "t", "p")),
            "down": bd.get("down"), "up": bd.get("up"), "crash_m": bd.get("crash_m"), "surge_m": bd.get("surge_m"), "crash_legs": bd.get("crash_legs"),
            "rebounds": bd.get("rebounds"), "years": {"won": yr.get("won"), "lost": yr.get("lost"), "rate": yr.get("rate"), "n_full": yr.get("n_full")},
            "blocks4": bd.get("blocks4"), "roll36_neg": bd.get("roll36_neg"), "skipped": a.get("skipped")}


def _pub_delta(d):
    return None if not d else {"n": d.get("n"), "h1": _pk(d.get("h1"), PUB_H1), "beta_adj": _pk(d.get("beta_adj"), ("n", "a", "t", "p"))}


def _pub_t1(r):
    if not r:
        return None
    o = {k: _pk(r.get(k), PUB_SM) for k in ("main", "ic", "decile_ew", "decile_vw", "half1", "half2", "post_2020_07", "ex_top10", "ndx_only") if k in r}
    o.update({"sigma_analytic": r.get("sigma_analytic"), "placebo": r.get("placebo"), "ic_down": r.get("ic_down"), "ic_up": r.get("ic_up"),
              "p0": _pk(r.get("p0"), ("p0", "pi", "t_alt", "gate_report")), "sigma_plan": _pk(r.get("sigma_plan"), ("sigma_plan", "binding"))})
    if "dnbeta_repack" in r:
        o["dnbeta_repack"] = r["dnbeta_repack"]
    return o


def _pub_t1_any(v):
    """Tier-1 칸 — 교차항 카드(W10m · W11)는 교차항 · 주 요약만 · 보고 묶음 카드(W01 · W04 · W02)는 _pub_t1 · 요약 하나는 _pk."""
    if not isinstance(v, dict):
        return v
    if "interaction" in v:
        ik = ("T", "df", "gamma0", "gamma1", "se", "t", "p_one", "p_wild_one", "p_wild_two", "B", "direction", "first", "last")
        o = {"interaction": _pk(v.get("interaction"), ik), "main": _pk(v.get("main"), PUB_SM), "n_state": v.get("n_state")}
        if "interaction_scaled" in v:
            o["interaction_scaled"] = _pk(v.get("interaction_scaled"), ik)
            o["scaled_same_sign"] = v.get("scaled_same_sign")
        for k in ("xtwin", "nagel", "reversal_placebo_synth"):
            if k in v:
                o[k] = _pk(v[k], ("T", "gamma1", "t", "p_one"))
        return o
    if "main" in v:
        o = _pub_t1(v)
        for k in ("indmom", "smooth3"):
            if k in v:
                o[k] = _pk(v[k], PUB_SM)
        if "cbsa_shuffle" in v:
            o["cbsa_shuffle"] = v["cbsa_shuffle"]
        return o
    return _pk(v, PUB_SM)


def _pub_h5(v):
    if not isinstance(v, dict):
        return v
    ik = ("T", "df", "gamma1", "t", "p_one", "direction")
    return {k: (x if k in ("T_months", "rule") else (_pk(x, ik) if "gamma1" in (x or {}) else _pk(x, PUB_SM))) for k, x in v.items()}


def _pub_hy(hy):
    out = {}
    for k, v in (hy or {}).items():
        if k in ("label_shuffle_leak", "planted_recovery") and isinstance(v, dict):
            out[k] = {c: (_pk(x, ("ok", "hits", "none", "n", "good", "reps", "need", "mode", "residualized")) if isinstance(x, dict) else x) for c, x in v.items()}
        elif isinstance(v, dict):
            out[k] = _pk(v, ("ok", "n", "same_as_registered_f0", "T", "missing", "failed", "err", "card_ok", "card_failed", "reg_B_gates"))
        else:
            out[k] = v
    return out


def public_view(out, out_sha256=None, out_bytes=None, cmp=None, reg="A"):
    """R16 — 결과 문서가 옮길 수 있는 칸만(최근 10년 창 수치 · 내부 L 쌍둥이는 창 · 개수 · 부호 참/거짓만 · 계열 없음)."""
    t1 = out.get("tier1") or {}
    fam = out.get("family") or {}
    pv = {"wbatch_public_view": True, "reg": reg, "note": "결과 문서가 옮길 수 있는 칸만(등록 §5 · R16) — 이 밖의 수치 · 계열은 저장소 밖 산출에만",
          "prereg": out.get("prereg"), "prereg_commit": out.get("prereg_commit"), "stopped": out.get("stopped"), "smoke": out.get("smoke"),
          "decisions": out.get("decisions"), "gegd": out.get("gegd"), "lookahead": {k: (_pk(v, ("ok", "n", "n_bad")) if isinstance(v, dict) else v)
                                                                                     for k, v in (out.get("lookahead") or {}).items()},
          "hygiene": _pub_hy(out.get("hygiene")),
          "family": {"stats": fam.get("stats"), "holm": _pk(fam.get("holm"), ("reject", "p", "p_t", "threshold", "order", "m", "alpha", "family", "direction",
                                                                              "hygiene_fail", "p_rule")),
                     "note": fam.get("note"), "power": fam.get("power")},
          "adoption": out.get("adoption"), "tier1": {k: (_pub_h5(v) if k == "H5_sensitivity" else _pub_t1_any(v)) for k, v in t1.items()},
          "tier2": {k: _pub_t2(v) for k, v in (out.get("tier2") or {}).items()},
          "tier2_delta": {k: _pub_delta(v) for k, v in (out.get("tier2_delta") or {}).items()},
          "structural_W01": _pk(out.get("structural_W01"), ("T", "dm_vs_fm", "dm_vs_ridge", "oos_r2", "dm_t_gt0", "C_arm", "PIT_ONLY", "train_note")),
          "vplus": {c: {"base": _pk(v.get("base"), PUB_SM), "plus": _pk(v.get("plus"), PUB_SM), "v_repack": v.get("v_repack")} for c, v in (out.get("vplus") or {}).items()},
          "twins_W01": {k: _pk(v, PUB_SM) for k, v in (out.get("twins_W01") or {}).items()},
          "steps": {k: {"arm": (_pub_t2(v.get("arm")) if k != "S1" else {kk: v["arm"].get(kk) for kk in ("n", "h1_10", "h1_20", "beta_adj", "turn_tranche", "luck")}),
                        "delta": _pub_delta(v.get("delta")), **{kk: v.get(kk) for kk in ("theta_mean", "e_max", "shuffle_rank", "n_shuffle", "n_updates", "rule_off_months")
                                                                  if kk in v}}
                    for k, v in (out.get("steps") or {}).items()},
          "w04_c_arm": out.get("w04_c_arm"), "w04_ts": _pk(out.get("w04_ts"), ("T", "b", "t", "r2_os")),
          "w04_twin_capm": _pk((out.get("w04_twin_capm") or {}).get("fm"), PUB_SM),
          "w11_random": out.get("w11_random"), "w11_activity": out.get("w11_activity"),
          "W03": None, "W06": None, "W12": None, "secondary_BY": {"admitted": (out.get("secondary_BY") or {}).get("admitted"),
                                                                  "pvals_n": (out.get("secondary_BY") or {}).get("pvals_n")},
          "pbo": {k: _pk(v, ("pbo", "n_splits", "S", "N", "T", "n_months")) for k, v in (out.get("pbo") or {}).items()},
          "expected_effect": out.get("expected_effect"), "n_arms": out.get("n_arms"), "cumulative_N": out.get("cumulative_N"),
          "eg30_compare": (cmp or {}).get("summary") if cmp else None, "out_sha256": out_sha256, "out_bytes": out_bytes}
    w3 = out.get("W03")
    if w3:
        pv["W03"] = {"pap": _pk(w3["pap"]["summary"], PUB_SM), "diag": _pk(w3["diag"]["summary"], PUB_SM), "pep_pap": _pk(w3["pep_pap"]["summary"], PUB_SM),
                     "n_assets": w3["pap"].get("n_assets"), "placebo": w3.get("placebo"), "l_twin": w3.get("l_twin_public"), "tier2": _pub_t2(w3.get("tier2")),
                     "twin_24": w3.get("twin_24_industry_groups")}
    w6 = out.get("W06")
    if w6:
        pv["W06"] = {"n_trig_S": w6["n_trig_S"], "trig_months": w6["trig_months"], "label": w6.get("label"),
                     "events_W06_vs_V01": w6["events_W06_vs_V01"], "events_CTRL12_vs_V01": w6["events_CTRL12_vs_V01"],
                     "events_RA_vs_V01": w6["events_RA_vs_V01"], "tier2": {k: _pub_t2(v) for k, v in w6["tier2"].items()},
                     "delta_W06_V01": _pub_delta(w6.get("delta_W06_V01")), "delta_CTRL12_V01": _pub_delta(w6.get("delta_CTRL12_V01")),
                     "delta_in_trigger_windows": w6.get("delta_in_trigger_windows")}
    w12 = out.get("W12")
    if w12:
        pv["W12"] = {"sml": w12.get("sml"), "n_fomc_T1": w12.get("n_fomc_T1"), "step": w12.get("step"), "tier2_V02": _pub_t2(w12.get("tier2_V02")),
                     "tier2_step_X10": {k: (v if k == "turn" else (_pk(v, PUB_H1) if isinstance(v, dict) else v))
                                        for k, v in (w12.get("tier2_step_X10") or {}).items()}}
    return _clean(pv)


def public_leaks(pv):
    """게시 칸 누수 점검 — 계열(__series__) · 긴 숫자 목록(> 12) · 내부 L 쌍둥이 요약 수치가 없어야 한다."""
    bad = []

    def walk(o, path):
        if isinstance(o, dict):
            if "__series__" in o or "__frame__" in o:
                bad.append(path + " 계열")
            for k, v in o.items():
                if k in ("l_twin_internal", "X10", "X20", "Xd0", "series", "gamma"):
                    bad.append(path + "/" + k)
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            if sum(1 for x in o if isinstance(x, (int, float)) and not isinstance(x, bool)) > 12:
                bad.append(path + " 숫자 목록")
            for x in o:
                walk(x, path + "[]")
    walk(pv, "")
    lt = ((pv.get("W03") or {}).get("l_twin") or {})
    for k in ("mean", "nw_t", "sd", "summary"):
        if k in lt:
            bad.append("W03 내부 L 쌍둥이 수치 %s" % k)
    return bad


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서 렌더러(게시 칸 파일 하나만 읽는다)
# ══════════════════════════════════════════════════════════════════════════
def _f(v, nd=3, pct=False):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(x):
        return "—"
    return ("%." + str(nd) + "f%%") % (x * 100) if pct else ("%." + str(nd) + "f") % x


def result_doc(pv):
    L = []
    reg = pv.get("reg", "A")
    L.append("# 결과 — 배치 W 등록 %s (%s · 등록 커밋 `%s`)" % (reg, pv.get("prereg"), (pv.get("prereg_commit") or "")[:12]))
    L.append("")
    L.append("이 문서는 얼린 렌더러(`python -X utf8 build/w_run.py --result-doc`)가 게시 칸 파일 하나에서 만들었다 — 등록 §5 · R16 의 칸만 싣는다.")
    if pv.get("smoke"):
        L.append("🚨 연기 산출(눈가림) — 결과가 아니다.")
    if pv.get("stopped"):
        L.append("")
        L.append("🛑 **굽기 멈춤**: %s — 통계는 계산하지 않았다(다시 굽지 않는다 · 다음은 새 등록)." % pv["stopped"])
    L.append("")
    L.append("## 1. 가족 · Holm · 채택 표시")
    fam = pv.get("family") or {}
    hm = fam.get("holm") or {}
    L.append("")
    L.append("| 카드 | 방향 | T | NW(3) t | 한쪽 p(야생 부트스트랩 · 판정) | 한쪽 p(t 분포 · 보고) | Holm 문턱 | 기각 | Tier-2 무해 | G-EGD | **채택 표시** | 주의 칸 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    ad = pv.get("adoption") or {}
    for c in (hm.get("family") or []):
        st = (fam.get("stats") or {}).get(c) or {}
        a = ad.get(c) or {}
        cd = a.get("conds") or {}
        L.append("| %s | %+d | %s | %s | %s | %s | %s | %s | %s | %s | **%s** | %s |" % (
            c, (hm.get("direction") or {}).get(c, 1), _f(st.get("T")), _f(st.get("t"), 2), _f((hm.get("p") or {}).get(c), 4), _f((hm.get("p_t") or {}).get(c), 4),
            _f((hm.get("threshold") or {}).get(c), 4), _f((hm.get("reject") or {}).get(c)), _f(cd.get("tier2_harmless")), _f(cd.get("gegd_pass")),
            _f(a.get("adopt")), ", ".join("%s=%s" % (k, _f(v)) for k, v in (a.get("cautions") or {}).items()) or "—"))
    L.append("")
    L.append("가족 α %s · m %s · 판정 p %s · 카드 위생 실패(p 없음) %s · %s" % (_f(hm.get("alpha"), 2), hm.get("m"), hm.get("p_rule") or "",
                                                                   ", ".join(hm.get("hygiene_fail") or []) or "없음", fam.get("note") or ""))
    L.append("검정력: %s" % (fam.get("power") or ""))
    for c, a in ad.items():
        if c not in (hm.get("family") or []):
            L.append("- %s: %s" % (c, a.get("path")))
    L.append("")
    L.append("## 2. Tier-1(종목 단면 · 결정 2016-08 ~ 2026-07)")
    L.append("")
    L.append("| 줄 | T | 평균 γ | NW t | 한쪽 p |")
    L.append("|---|---|---|---|---|")
    t1 = pv.get("tier1") or {}
    for k, r in t1.items():
        r = r or {}
        if k == "H5_sensitivity":                                            # R17 — 가족 통계를 H5 달로(보고)
            for c, x in r.items():
                if isinstance(x, dict):
                    L.append("| %s H5 민감도(달 %s) | %s | %s | %s | %s |" % (c, r.get("T_months"), _f(x.get("T")), _f(x.get("gamma1", x.get("mean")), 5),
                                                                 _f(x.get("t", x.get("nw_t")), 2), _f(x.get("p_one"), 4)))
            continue
        if "interaction" in r:
            it = r.get("interaction") or {}
            L.append("| %s 교차항 | %s | %s | %s | %s |" % (k, _f(it.get("T")), _f(it.get("gamma1"), 5), _f(it.get("t"), 2), _f(it.get("p_one"), 4)))
            if r.get("interaction_scaled"):
                it = r["interaction_scaled"]
                L.append("| %s 교차항 척도 없는 쌍둥이(γ_t ÷ SD_t · R18) | %s | %s | %s | %s |" % (k, _f(it.get("T")), _f(it.get("gamma1"), 5), _f(it.get("t"), 2),
                                                                                    _f(it.get("p_one"), 4)))
            for sub in ("xtwin", "nagel"):
                if r.get(sub):
                    it = r[sub]
                    L.append("| %s %s | %s | %s | %s | %s |" % (k, sub, _f(it.get("T")), _f(it.get("gamma1"), 5), _f(it.get("t"), 2), _f(it.get("p_one"), 4)))
        elif "main" in r:
            for sub in ("main", "ic", "decile_ew", "decile_vw", "half1", "half2", "post_2020_07", "ex_top10", "ndx_only", "indmom", "smooth3"):
                s = r.get(sub) or {}
                if s:
                    L.append("| %s %s | %s | %s | %s | %s |" % (k, sub, _f(s.get("T")), _f(s.get("mean"), 5), _f(s.get("nw_t"), 2), _f(s.get("p_one"), 4)))
        else:
            L.append("| %s | %s | %s | %s | %s |" % (k, _f(r.get("T")), _f(r.get("mean"), 5), _f(r.get("nw_t"), 2), _f(r.get("p_one"), 4)))
    L.append("")
    for k in [x for x in ("W01", "W04", "W02") if x in t1]:
        r = t1.get(k) or {}
        L.append("- %s: σ_analytic %s · 위약 순위 %s · P0 %s · 하락월 IC %s · 상승월 IC %s%s" % (
            k, _f(r.get("sigma_analytic"), 5), _f((r.get("placebo") or {}).get("rank"), 3), _f((r.get("p0") or {}).get("p0"), 3),
            _f((r.get("ic_down") or {}).get("mean"), 4), _f((r.get("ic_up") or {}).get("mean"), 4),
            (" · DNBETA 재포장 %s" % _f(r.get("dnbeta_repack"))) if "dnbeta_repack" in r else ""))
    sw = pv.get("structural_W01") or {}
    L.append("- W01 구조 검정(S 팔 · 주의 칸): DM(대 FM) t %s · DM(대 능형) t %s · DM t > 0 둘 다 %s" % (
        _f((sw.get("dm_vs_fm") or {}).get("t"), 2), _f((sw.get("dm_vs_ridge") or {}).get("t"), 2), _f(sw.get("dm_t_gt0"))))
    for nm, lab in (("C_arm", "C 팔"), ("PIT_ONLY", "PIT 전용 학습 쌍둥이 · 같은 학습 길이")):
        v = sw.get(nm) or {}
        if v:
            L.append("  - %s(R20 · 보고): DM(대 FM) t %s · DM(대 능형) t %s" % (lab, _f((v.get("dm_vs_fm") or {}).get("t"), 2), _f((v.get("dm_vs_ridge") or {}).get("t"), 2)))
    for c, v in (pv.get("vplus") or {}).items():
        L.append("- V-플러스 %s: γ %s → %s · V 재포장 %s" % (c, _f((v.get("base") or {}).get("mean"), 5), _f((v.get("plus") or {}).get("mean"), 5), _f(v.get("v_repack"))))
    L.append("")
    L.append("## 3. Tier-2(펀드 틀 · 보유 2016-09 ~ 2026-08 · 주 행 T+1)")
    L.append("")
    L.append("| 팔 | n | 연 X 10bp | t | 연 X 20bp | 하락월 X | 회전 | β 조정 α t | 해마다 승률 | 무해 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")

    def row(nm, a):
        if not a or not a.get("n"):
            L.append("| %s | 0 | — | — | — | — | — | — | — | — |" % nm)
            return
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            nm, a["n"], _f((a.get("h1_10") or {}).get("ann"), 2, True), _f((a.get("h1_10") or {}).get("t"), 2), _f((a.get("h1_20") or {}).get("ann"), 2, True),
            _f((a.get("down") or {}).get("mean"), 3, True), _f(a.get("turn"), 2), _f((a.get("beta_adj") or {}).get("t"), 2),
            _f((a.get("years") or {}).get("rate"), 2), _f((a.get("harmless") or {}).get("harmless"))))
    for k, a in (pv.get("tier2") or {}).items():
        row(k, a)
    for k, st in (pv.get("steps") or {}).items():
        if k != "S1":
            row("W01 C +" + k, st.get("arm"))
    for blk in ("W03", "W06", "W12"):
        b = pv.get(blk) or {}
        if blk == "W03" and b:
            row("W03 PAP", b.get("tier2"))
        if blk == "W06" and b:
            for k, a in (b.get("tier2") or {}).items():
                row("W06 " + k, a)
        if blk == "W12" and b:
            row("W12 V02 정적", b.get("tier2_V02"))
    L.append("")
    L.append("Δ(보유 달 겹침 · 연 · t · β 조정 α t):")
    for k, d in (pv.get("tier2_delta") or {}).items():
        if d:
            L.append("- %s: %s · t %s · α t %s" % (k, _f((d.get("h1") or {}).get("ann"), 2, True), _f((d.get("h1") or {}).get("t"), 2), _f((d.get("beta_adj") or {}).get("t"), 2)))
    for k, st in (pv.get("steps") or {}).items():
        d = st.get("delta") or {}
        L.append("- 스텝 %s: %s · t %s%s" % (k, _f((d.get("h1") or {}).get("ann"), 2, True), _f((d.get("h1") or {}).get("t"), 2),
                                            (" · θ 평균 %s · 섞기 순위 %s" % (_f(st.get("theta_mean"), 3), _f(st.get("shuffle_rank"), 3))) if k == "S3e" else ""))
    L.append("")
    L.append("## 4. 측정만 카드")
    w3 = pv.get("W03") or {}
    if w3:
        p = w3.get("pap") or {}
        lt = w3.get("l_twin") or {}
        L.append("- W03 PAP 롱숏: T %s · NW(6) t %s · 위약 순위 %s · 대각(섹터 모멘텀) t %s · PEP+PAP t %s · 내부 L 쌍둥이(20년 · 창 %s ~ · T %s) S 층과 같은 부호 %s" % (
            _f(p.get("T")), _f(p.get("nw_t"), 2), _f((w3.get("placebo") or {}).get("rank"), 3), _f((w3.get("diag") or {}).get("nw_t"), 2),
            _f((w3.get("pep_pap") or {}).get("nw_t"), 2), lt.get("first_hold"), _f(lt.get("T")), _f(lt.get("same_sign_as_S"))))
    w6 = pv.get("W06") or {}
    if w6:
        L.append("- W06: S 창 발동 %s 번(%s) · 라벨 %s · 발동 창 달 Δ X 평균 %s" % (
            w6.get("n_trig_S"), ", ".join(w6.get("trig_months") or []), w6.get("label") or "—", _f((w6.get("delta_in_trigger_windows") or {}).get("mean"), 3, True)))
        for m, ev in (w6.get("events_W06_vs_V01") or {}).items():
            L.append("  - %s 발동 · 21일 %s · 42일 %s(대 V01 정기판)" % (m, _f((ev or {}).get("21"), 2, True), _f((ev or {}).get("42"), 2, True)))
    w12 = pv.get("W12") or {}
    if w12:
        sml = w12.get("sml") or {}
        stp = w12.get("step") or {}
        L.append("- W12: 발표일 − 비발표일 베타 기울기 b %s · NW(5) t %s · 발표일 %s · 스텝 효과 합 %s · 무작위 비발표일 순위 %s" % (
            _f(sml.get("b"), 5), _f(sml.get("t"), 2), _f(sml.get("n_fomc")), _f(stp.get("sum"), 4), _f(stp.get("placebo_rank"), 3)))
        tn = ((w12.get("tier2_step_X10") or {}).get("turn") or {})
        if tn:
            L.append("  - 스텝 팔 편도 연 회전(R19): V02 %s + 스텝 %s = %s · ≤ 10 %s" % (_f(tn.get("base_V02"), 2), _f(tn.get("step_add"), 2), _f(tn.get("total"), 2),
                                                                     _f(tn.get("turn_le10"))))
    L.append("")
    L.append("## 5. 위생 · 선견 · G-EGD · 보고 셈")
    hy = pv.get("hygiene") or {}
    L.append("- 위생 묶음(파이프라인): %s · 카드 위생 %s · 선견: %s" % (
        _f((hy.get("run_all") or {}).get("ok")), ", ".join("%s %s" % (c, _f(v)) for c, v in ((hy.get("run_all") or {}).get("card_ok") or {}).items()) or "—",
        ", ".join("%s %s" % (k, _f((v or {}).get("ok") if isinstance(v, dict) else v)) for k, v in (pv.get("lookahead") or {}).items())))
    for c, g in (pv.get("gegd") or {}).items():
        L.append("- G-EGD %s: 통과 %s · 능동 상관 EG30 %s · QG30 %s · 겹침 초과 %s · |Spearman| %s" % (
            c, _f((g or {}).get("pass")), _f((g or {}).get("corr_EG30"), 3), _f((g or {}).get("corr_QG30"), 3), _f((g or {}).get("ovx_EG30"), 3), _f((g or {}).get("spear_abs"), 3)))
    L.append("- W01 판: %s(R2)" % ((pv.get("decisions") or {}).get("w01_chars")))
    L.append("- 부 가족 BY(q 0.10 · 보고): 넘은 이름 %s" % (", ".join((pv.get("secondary_BY") or {}).get("admitted") or []) or "없음"))
    cn = pv.get("cumulative_N") or {}
    L.append("- 누적 N: 랩 %s + 이 굽기 팔 %s = %s" % (cn.get("lab"), cn.get("w_arms_A") or cn.get("w_arms_B"), cn.get("total")))
    ee = pv.get("expected_effect") or {}
    if ee:
        L.append("- 기대 효과(EB 수축 · 보고): 수축 계수 %s · %s" % (_f(ee.get("shrink"), 3), ", ".join("%s %s" % (k, _f(v, 2)) for k, v in (ee.get("t_shrunk") or {}).items())))
    ec = pv.get("eg30_compare") or {}
    L.append("- EG30 비교선(보고만 · 어떤 관문 · 귀무에도 없다): %s" % (("연 %s · t %s · n %s" % (_f(ec.get("ann"), 2, True), _f(ec.get("t"), 2), ec.get("n"))) if ec else "없음"))
    L.append("- 산출 sha256 앞 16자 `%s` · %s 바이트" % ((pv.get("out_sha256") or "")[:16], pv.get("out_bytes")))
    L.append("")
    L.append("채택 표시는 «펀드 슬리브 후보» 표지일 뿐이다 — 실제 펀드에 붙이는 것은 이 문서 뒤 사용자 결정이다(날짜 없음 · 갱신 나).")
    return "\n".join(L) + "\n"


# ══════════════════════════════════════════════════════════════════════════
#  굽기(부모) — 표식 → 태그 → 준비 자식 → G-EGD(w_cmp) → 굽기 자식 → 비교 줄 → 게시 칸 → 실행 기록 → FINISHED
# ══════════════════════════════════════════════════════════════════════════
def _push_start_tag(commit, reg="A"):
    tag = MARK[reg]["tag"]
    if _OVR["tag"]:
        _write_text(os.path.join(_OVR["tag"], tag), commit + "\n")
        return "override"
    have = _remote_start_tag(reg)
    if have == commit:
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", tag, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (tag, tag))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag(reg) != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다(%s) — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 WBATCH_RERUN)." % (r2.stderr or r1.stderr).strip()[:160])
    return "pushed"


def _mark_finished(P, sha):
    line = "%s %s %s\n" % (FINISHED, sha, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        with io.open(m, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)


def _child_env(extra):
    env = WC.pin_env()
    env.update(extra)
    return env


def _run_child(flag, env):
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__), flag], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r


def _run_cmp(args, env):
    t0 = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "w_cmp.py")] + args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return {"rc": r.returncode, "sec": round(time.time() - t0, 1), "tail": (r.stderr or "")[-300:] if r.returncode else ""}


def bake(commit, rerun=None, smoke_env=None, reg="A"):
    """frozen_check 를 통과한 뒤에만(연기는 가짜 커밋으로). 값은 찍지 않는다 — 경로 · sha256 · 초만."""
    t0 = time.time()
    P = paths(reg=reg)
    started = _read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip() if rerun else "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        if not os.path.exists(m):
            _write_text(m, started + "\n")
    tag = _push_start_tag(commit, reg)
    base = {"WBATCH_RUNNER_TOKEN": commit, "WBATCH_OUT_DIR": P["dir"], "WBATCH_REG": reg}
    if not smoke_env:
        base["WBATCH_COMMIT"] = os.environ.get("WBATCH_COMMIT", "")
        if reg == "B":
            base["WBATCH_B_COMMIT"] = os.environ.get("WBATCH_B_COMMIT", "")
    env = _child_env(dict(base, **(smoke_env or {})))
    if smoke_env:
        env.pop("WBATCH_COMMIT", None)
    tc = time.time()
    r = _run_child("--_prep-child", env)
    sec_prep = round(time.time() - tc, 1)
    if r.returncode != 0 or not os.path.exists(P["books"]):
        raise SystemExit("🚨 준비 자식 실패(rc %s) — 산출이 없으면 WBATCH_RERUN 으로 처음부터: %s" % (r.returncode, (r.stderr or "")[-900:]))
    cenv = _child_env({"WBATCH_CACHE": WC.CACHE})
    cenv.pop("WBATCH_COMMIT", None)
    cg = _run_cmp(["--gegd", "--in", P["books"], "--out", P["gegd"]], cenv)
    if cg["rc"] != 0 or not os.path.exists(P["gegd"]):
        raise SystemExit("🚨 G-EGD(w_cmp) 실패(rc %s): %s" % (cg["rc"], cg["tail"]))
    tc = time.time()
    r = _run_child("--_bake-child", env)
    sec_child = round(time.time() - tc, 1)
    if r.returncode != 0 or not os.path.exists(P["out"]):
        raise SystemExit("🚨 굽기 자식 실패(rc %s · 산출 %s) — 산출이 없으면 WBATCH_RERUN 으로 처음부터: %s" % (r.returncode, os.path.exists(P["out"]), (r.stderr or "")[-900:]))
    child = _read_json(P["child"]) if os.path.exists(P["child"]) else {}
    prep = _read_json(P["prep"]) if os.path.exists(P["prep"]) else {}
    menv = _child_env({"WBATCH_CACHE": WC.CACHE})
    if smoke_env:
        menv.pop("WBATCH_COMMIT", None)
    else:
        menv["WBATCH_COMMIT"] = os.environ.get("WBATCH_COMMIT", "")
    cm = _run_cmp(["--compare", "--out", P["cmp"]], menv)
    cm["written"] = os.path.exists(P["cmp"])
    cm["refused_without_registration"] = bool(smoke_env and cm["rc"] != 0 and not cm["written"])
    cmp_doc = _read_json(P["cmp"]) if cm["written"] else None
    blob = _bytes(P["out"])
    sha = hashlib.sha256(blob).hexdigest()
    out = json.loads(blob.decode("utf-8"))
    pub = public_view(out, sha, len(blob), cmp_doc, reg)
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    leaks = public_leaks(pub)
    del out
    mods = local_modules()
    unf = sorted(set(unfrozen_modules(mods)) | set(unfrozen_modules(child.get("local_modules") or [])) | set(unfrozen_modules(prep.get("local_modules") or [])))
    err = []
    if unf:
        err.append("얼리지 않은 build/ 모듈을 불렀다: %s" % ", ".join(unf))
    for rec, nm in ((child, "굽기"), (prep, "준비")):
        for k in ("runtime", "open_audit", "static"):
            if not (rec.get("noeg") or {}).get(k, {}).get("ok"):
                err.append("%s 자식 G-NoEG(%s) 거짓" % (nm, k))
        if rec.get("unregistered_data"):
            err.append("%s 자식이 판 점검 밖 랩 자료를 읽었다: %s" % (nm, ", ".join(rec["unregistered_data"][:5])))
        if rec.get("loaded_frozen_ok") is False:
            err.append("%s 자식의 불러온 로컬 모듈이 얼린 핀 밖" % nm)
    if leaks:
        err.append("게시 칸 누수: %s" % "; ".join(leaks[:5]))
    if not smoke_env and cm["rc"] != 0:
        err.append("EG30 비교 줄(w_cmp) 실패 rc %s — 보고 줄만 빠진다" % cm["rc"])
    rec = {"reg": reg, "prereg": PREREG if reg == "A" else PREREG_B, "prereg_commit": commit, "runner": RUNNER, "started": started, "rerun": rerun,
           "start_tag": tag, "stopped": child.get("stopped"), "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1),
           "sec_prep": sec_prep, "sec_gegd": cg["sec"], "sec_child": sec_child, "out": os.path.basename(P["out"]), "out_sha256": sha, "out_bytes": len(blob),
           "public": os.path.basename(P["public"]), "public_sha256": hashlib.sha256(_bytes(P["public"])).hexdigest(), "cmp": cm,
           "env": {k: os.environ.get(k) for k in WC.REQUIRED_ENV}, "versions": _versions(), "frozen": list(FROZEN), "local_modules_parent": mods,
           "local_modules_child": child.get("local_modules"), "local_modules_prep": prep.get("local_modules"), "unfrozen_modules": unf,
           "noeg_child": child.get("noeg"), "noeg_prep": prep.get("noeg"), "data_files_opened": child.get("data_files_opened"),
           "cache_files_opened": child.get("cache_files_opened"), "shape_child": child.get("shape"), "peak_mb_parent": peak_mb(), "peak_mb_child": child.get("peak_mb"),
           "peak_mb_prep": prep.get("peak_mb"), "clock_child": child.get("clock"), "registration_error": err, "smoke": bool(smoke_env),
           "note": "값 없음 — 결과는 _wbatch.public.json 의 칸만 결과 문서로 옮긴다"}
    _write_text(P["runlog"], json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    _mark_finished(P, sha)
    print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)%s" % (P["out"], sha[:16], rec["sec"], (" · 멈춤: %s" % child.get("stopped")) if child.get("stopped") else ""))
    return rec


def _same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def child_gate(token, d, reg="A", remote_tag=None, gitmark=None):
    """진짜 굽기 자식이 스스로 다시 보는 판(부모 frozen_check 를 건너뛴 직접 실행을 막는다)."""
    if not re.fullmatch(r"[0-9a-f]{40}", token or ""):
        raise SystemExit("🚨 러너 표가 등록 커밋(40자)이 아니다 — 굽기는 w_run.py(판 점검 → 시작 표식)로만.")
    r = _git("rev-parse", "--verify", "-q", token + "^{commit}")
    if r.returncode != 0 or r.stdout.strip() != token:
        raise SystemExit("🚨 러너 표 커밋을 찾지 못했다.")
    why = _first_added_ok(token, FIRST_ADDED[reg])
    if why:
        raise SystemExit("🚨 %s." % why)
    if _git("merge-base", "--is-ancestor", token, "origin/main").returncode != 0:
        raise SystemExit("🚨 러너 표 커밋이 origin/main 에 없다.")
    if WC.registered_commit() is None:
        raise SystemExit("🚨 WBATCH_COMMIT 가 등록 A 커밋(origin/main 조상 · 등록 문서 둘)이 아니다.")
    if not _same_path(d, os.path.join(WC.CACHE, "out")):
        raise SystemExit("🚨 진짜 굽기의 산출 폴더는 <캐시>/out 뿐이다.")
    gm = gitmark or _git_mark_path(reg)
    if not os.path.exists(gm) or not _read_text(gm).startswith(token):
        raise SystemExit("🚨 git 공용 폴더 시작 표식이 러너 표와 다르다.")
    tag = remote_tag if remote_tag is not None else _remote_start_tag(reg)
    if tag != token:
        raise SystemExit("🚨 origin 시작 태그가 러너 표 커밋이 아니다(계산 전에 밀지 않은 굽기).")
    return True


def smoke_gate(d):
    """연기 자식은 <캐시>/wbatch_runner_smoke_*/out 에서만."""
    parent = os.path.dirname(os.path.abspath(d))
    if _same_path(d, os.path.join(WC.CACHE, "out")):
        raise SystemExit("🚨 연기 굽기가 진짜 산출 폴더를 쓰려 한다.")
    if not (os.path.basename(parent).startswith("wbatch_runner_smoke_") and _same_path(os.path.dirname(parent), WC.CACHE)
            and os.path.basename(os.path.abspath(d)) == "out"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/wbatch_runner_smoke_*/out 이 아니다.")
    return True


def _child_common():
    token, d, reg = os.environ.get("WBATCH_RUNNER_TOKEN"), os.environ.get("WBATCH_OUT_DIR"), os.environ.get("WBATCH_REG") or "A"
    smoke = token == "SMOKE"
    if not token or not d:
        raise SystemExit("🚨 러너 표가 없다 — 굽기는 w_run.py(판 점검 → 시작 표식)로만.")
    P = paths(d, reg)
    if not os.path.exists(P["mark"]) or not _read_text(P["mark"]).startswith(token):
        raise SystemExit("🚨 시작 표식이 러너 표와 다르다 — 러너 밖 굽기 차단.")
    if smoke:
        smoke_gate(d)
    else:
        for k in ("WBATCH_SMOKE", "WBATCH_SMOKE_CAPS", "WBATCH_F0_FILE"):
            if os.environ.get(k):
                raise SystemExit("🚨 연기 전용 환경 변수 %s 가 진짜 굽기에 켜져 있다." % k)
        child_gate(token, d, reg)
        fb = f0_check(load_f0(), code_shas())
        if fb:
            raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:3]))
    probs = WC.env_problems()
    if probs:
        raise SystemExit("🚨 환경 핀: %s" % probs)
    return token, P, reg, smoke


def _arm_n(a):
    """팔의 보유 달 수(개수만) — "n" 칸이 없으면 X10 길이(Series · 목록 모두 · 진리값으로 쓰지 않는다)."""
    a = a if isinstance(a, dict) else {}
    n = a.get("n")
    if isinstance(n, int) and not isinstance(n, bool):
        return n
    x = a.get("X10")
    return int(len(x)) if x is not None else 0


def shape_of(out):
    """자식 기록의 모양 칸(개수 · 참/거짓만 — 수익 · γ · t 값 없음) · 연기가 빈 결과를 조용히 지나치지 않게."""
    def ok(v):
        return (v or {}).get("ok") if isinstance(v, dict) else None
    fam = out.get("family") or {}
    sh = {"stopped": out.get("stopped"), "lookahead": {k: ok(v) for k, v in (out.get("lookahead") or {}).items() if isinstance(v, dict)},
          "lookahead_n": {k: (v or {}).get("n") for k, v in (out.get("lookahead") or {}).items() if isinstance(v, dict)},
          "hygiene": {k: ok(v) for k, v in (out.get("hygiene") or {}).items() if isinstance(v, dict)},
          "family_T": {c: (v or {}).get("T") for c, v in (fam.get("stats") or {}).items()}, "holm_m": (fam.get("holm") or {}).get("m"),
          "tier2_n": {k: (v or {}).get("n") for k, v in (out.get("tier2") or {}).items()},
          "tier2_harmless_defined": {k: isinstance(((v or {}).get("harmless") or {}).get("harmless"), bool) for k, v in (out.get("tier2") or {}).items()},
          "steps_n": {k: _arm_n((v or {}).get("arm")) for k, v in (out.get("steps") or {}).items()},
          "adopt_defined": {c: isinstance((v or {}).get("adopt"), bool) for c, v in (out.get("adoption") or {}).items()},
          "n_arms": (out.get("n_arms") or {}).get("total")}
    for blk in ("W03", "W06", "W12"):
        if out.get(blk):
            b = out[blk]
            sh[blk] = {"tier2_n": ((b.get("tier2") or {}).get("n") if blk == "W03" else None), "n_trig": b.get("n_trig_S"),
                       "n_fomc": b.get("n_fomc_T1"), "sml_T": (b.get("sml") or {}).get("T"),
                       "pap_T": ((b.get("pap") or {}).get("summary") or {}).get("T"), "l_twin_T": (b.get("l_twin_public") or {}).get("T")}
    return sh


def _child_record(t0, extra):
    import numpy as np  # noqa: F401
    opened = data_files_opened()
    lf = WC.loaded_frozen_check()
    rec = {"local_modules": local_modules(), "data_files_opened": opened, "unregistered_data": unregistered_data(opened),
           "cache_files_opened": cache_files_opened(), "noeg": noeg_block(), "loaded_frozen_ok": lf["ok"], "loaded_frozen_bad": lf["bad"],
           "peak_mb": peak_mb(), "sec": round(time.time() - t0, 1), "note": "자식 과정 기록 — 값 없음"}
    rec.update(extra)
    return rec


def _prep_child():
    token, P, reg, smoke = _child_common()
    WG.install_open_audit()
    t0 = time.time()
    import warnings
    import numpy as np
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        warnings.simplefilter("ignore")
        ctx = build_ctx("blind" if smoke else "real")
        if reg == "A":
            info = run_prep(ctx, P["books"])
        else:
            info = run_prep_B(ctx, P["books"])
    rec = _child_record(t0, {"prep": info, "smoke": smoke, "reg": reg})
    _write_text(P["prep"], json.dumps(_clean(rec), ensure_ascii=False, indent=1) + "\n")
    print("준비 자식 끝 · %.0f초" % rec["sec"])
    return 0


def _bake_child():
    token, P, reg, smoke = _child_common()
    WG.install_open_audit()
    t0 = time.time()
    clock = {}
    gegd = _read_json(P["gegd"]) if os.path.exists(P["gegd"]) else {}
    import warnings
    import numpy as np
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        warnings.simplefilter("ignore")
        ctx = build_ctx("blind" if smoke else "real")
        ctx["f0_doc"] = None if smoke else load_f0()
        if reg == "A":
            out = run_batch_A(ctx, gegd_decisions(gegd), smoke=smoke, clock=clock)
        else:
            out = run_batch_B(ctx, gegd_decisions_B(gegd), smoke=smoke, clock=clock)
    out["prereg"], out["prereg_commit"] = (PREREG if reg == "A" else PREREG_B), token
    out["gegd_in_sha"] = gegd.get("in_sha")
    out["gegd_eg_inputs"] = gegd.get("eg_inputs")
    txt = json.dumps(_clean(out), ensure_ascii=False, allow_nan=False) + "\n"
    _write_text(P["out"], txt)
    rec = _child_record(t0, {"stopped": out.get("stopped"), "clock": clock, "smoke": smoke, "reg": reg, "n_arms": out.get("n_arms"), "shape": shape_of(out)})
    _write_text(P["child"], json.dumps(_clean(rec), ensure_ascii=False, indent=1) + "\n")
    print("자식 굽기 끝 · %.0f초" % rec["sec"])
    return 0


def main(reg="A"):
    commit = frozen_check(reg=reg)
    return bake(commit, rerun=os.environ.get("WBATCH_RERUN"), reg=reg)


# ══════════════════════════════════════════════════════════════════════════
#  등록 B(W02 GEO-X · W11 FRAG) — 제 등록 문서 · 제 시작 표식 · 제 Holm(갱신 나 — 오케스트레이터 결정)
# ══════════════════════════════════════════════════════════════════════════
GEGD_CARDS_B = ("W02", "W11")


def run_prep_B(ctx, books_path_out, log=_log):
    """등록 B G-EGD 넘김 — W02 · W11 θ = 1 책(w_geo.gegd_entry · w_frag.gegd_entry) · 신호(비중 · 신호만)."""
    import w_frag as FRAG
    import w_geo as GEO
    SU, X, dec = ctx["U"], ctx["X"], ctx["dec"]
    t0 = time.time()
    GEOP, _dens = GEO.geo_panel(SU, dec, log=lambda *_: None)
    FR = FRAG.frag_panel(SU, dec, log=lambda *_: None)
    doc = {"cards": list(GEGD_CARDS_B), "months": {}, "note": "w_run.run_prep_B — θ = 1 목표 책 · 신호 · w_B · 가격 키(수익 통계 없음)"}
    for m in dec:
        Xm = X.get(m)
        if Xm is None:
            continue
        d = {"wB": Xm.book(Xm.wB), "keys": {t: k for t, k in zip(Xm.t, Xm.k)}, "books": {}, "signals": {}}
        g = (GEOP.get(m) or {}).get("geo")
        if g:
            e = GEO.gegd_entry(Xm, g)
            if e["book"]:
                d["books"]["W02"], d["signals"]["W02"] = e["book"], e["signal"]
        fr = (FR.get(m) if isinstance(FR, dict) else None)
        rows = (fr or {}).get("rows") if isinstance(fr, dict) else None
        if rows:
            e = FRAG.gegd_entry(Xm, rows)
            if e["book"]:
                d["books"]["W11"], d["signals"]["W11"] = e["book"], e["signal"]
        doc["months"][m] = d
    os.makedirs(os.path.dirname(books_path_out), exist_ok=True)
    with gzip.open(books_path_out, "wt", encoding="utf-8") as f:
        json.dump(_clean(doc), f, ensure_ascii=False)
    return {"n_months": len(doc["months"]), "sec": round(time.time() - t0, 1)}


def gegd_decisions_B(gegd):
    cards = (gegd or {}).get("cards") or {}
    return {"gegd_pass": {c: bool((cards.get(c) or {}).get("pass") is True) for c in GEGD_CARDS_B},
            "gegd_label": {c: (cards.get(c) or {}).get("label", "칸 없음(fail closed)") for c in GEGD_CARDS_B},
            "gegd_summary": {c: {k: (cards.get(c) or {}).get(k) for k in ("n_months", "corr_EG30", "corr_QG30", "ovx_EG30", "ovx_QG30", "spear_abs", "pass")}
                             for c in GEGD_CARDS_B}}


def geo_lookahead(SU, months, n, seed, A):
    """R10(등록 B) — W02 G · 동료 수 · geo_same: 독 넣은 우주(d 뒤)에서 풀 · 세계 · G 를 다시 → 같다."""
    import numpy as np
    import w_geo as GEO
    import w_hygiene as H
    rng = np.random.default_rng(seed)

    def sig(U, m):
        pool = GEO.pool_month(U, m, A)
        focal = GEO.world_of(U, m)
        g = GEO.geo_month(pool, focal)
        ks = sorted(g)
        out = {k: np.array([np.nan if (g[t] or {}).get(k) is None else float(g[t][k]) for t in ks], float) for k in ("G", "geo_same", "n_peers")}
        out["names"] = np.array([float(int(hashlib.sha256(t.encode("utf-8")).hexdigest()[:12], 16)) for t in ks], float)
        return out
    return H.lookahead_shift(sig, SU, lambda U, m: U.poison_after(m, rng), months, seed, n=n, tol=0.0)


def frag_lookahead(SU, months, n, seed, Hd, LK):
    """R10(등록 B) — W11 F · 보유자 수: 독 넣은 우주(d 뒤 원장 · 가격)에서 frag_month 를 다시 → 같다(13F 보유는 접수 < d 만 쓴다)."""
    import numpy as np
    import w_frag as FRAG
    import w_hygiene as H
    rng = np.random.default_rng(seed)

    def sig(U, m):
        rows = FRAG.frag_month(U, m, Hd, LK)["rows"]
        ks = sorted(rows)
        return {"F": np.array([np.nan if rows[t].get("F") is None else float(rows[t]["F"]) for t in ks], float),
                "n_holders": np.array([float(rows[t].get("n_holders") or 0) for t in ks], float),
                "names": np.array([float(int(hashlib.sha256(t.encode("utf-8")).hexdigest()[:12], 16)) for t in ks], float)}
    return H.lookahead_shift(sig, SU, lambda U, m: U.poison_after(m, rng), months, seed, n=n, tol=0.0)


def run_batch_B(ctx, dec_g, smoke=False, clock=None, log=_log):
    """명세 차례대로 한 번(등록 B · 제 등록 문서 PREREG-*-WBATCH-B.md) — 신호 → 선견 → 위생(fail-closed) → 가족 B Tier-1 → Holm → Tier-2 · 무해 → 채택 표시 → 대조.
    W02 GEO-X(방향 +1 · 1개월 신호 책 · 상태 의존 비용 · 전량 체결) · W11 FRAG(교차항 방향 −1 · 방어 책). 규칙은 w_geo G1 ~ G13 · w_frag F1 ~ F11 · F4b 그대로."""
    import numpy as np
    import w_frag as FRAG
    import w_geo as GEO
    import w_hygiene as H
    import w_stagem as S
    clock = clock if clock is not None else {}
    cap = _caps(smoke)
    seed = ctx["seed"]
    P, X, E, SU = ctx["P"], ctx["X"], ctx["E"], ctx["U"]
    kind = ctx["pkind"]
    dec, dec_ok, drift = ctx["dec"], ctx["dec_ok"], ctx["drift"]
    out = {"reg": "B", "decisions": {"gegd_pass": dec_g["gegd_pass"], "gegd_label": dec_g["gegd_label"], "tier1_months": dec_ok,
                                     "drift_months": sorted(drift)}, "gegd": dec_g.get("gegd_summary"), "stopped": None, "smoke": bool(smoke)}
    tick = lambda k, t0: clock.__setitem__(k, round(time.time() - t0, 1))
    regs = _dm_regs(E)
    VD = WC.frozen("v_data")
    # ── 신호 ─────────────────────────────────────────────────────────────
    t0 = time.time()
    A = GEO.Addresses.load()
    GEOP, dens = GEO.geo_panel(SU, dec, A=A, log=lambda *_: None)
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    Hd = FRAG.Holdings()
    LK = FRAG.Linker(FRAG.ftd_intervals()[0], im.get("groups") or {})
    FR = FRAG.frag_panel(SU, dec, Hd, LK, with_x=True, log=lambda *_: None)
    AS = VD.read_json(VD.lab_path("data/assets.json"))
    s_t, _z = FRAG.stress_state(AS["macro"]["BAA10Y"], dec)
    sN = FRAG.nagel_s({m: E.spy_hold(WC.mshift(m, -1)) for m in ctx["months"]}, dec)
    Ea = WC.frozen("v_ear").Earnings(SU, sameday_primary=True)
    dall = {m: v[0] for m, v in dens.items()}
    for m in [x for x in SU.months if GEO.DENS_FROM <= x <= dec[-1] and x in SU.me_idx]:          # G8 — 확장창은 2014-06 부터(w_geo F0 와 같다)
        if m not in dall:
            dall[m] = GEO.density_month(SU.members(m), SU.d_of(m), Ea.key_of, Ea.ed)[0]
    zd = GEO.density_z(dall, sorted(dall))
    th02 = {m: GEO.theta_c(zd.get(m)) for m in dec}
    tick("signals", t0)
    # ── 선견(R10) ────────────────────────────────────────────────────────
    t0 = time.time()
    la = {"pit": pit_lookahead(SU, cap["pit_la"], seed + SEED_OFF["pit_la"], [m for m in ctx["months"] if m >= PIT_LA_FROM]),
          "geo": geo_lookahead(SU, dec, cap["w04_la"], seed + SEED_OFF["pit_la"] + 3, A),
          "frag": frag_lookahead(SU, dec, cap["w04_la"], seed + SEED_OFF["pit_la"] + 4, Hd, LK),
          "state": state_lookahead(ctx["macro"], ctx["months"], SU.d_of)}
    la["ok"] = all(v.get("ok") for v in la.values() if isinstance(v, dict))
    out["lookahead"] = la
    tick("lookahead", t0)
    if not la["ok"] and not smoke:
        out["stopped"] = "선견 점검 실패(%s)" % ", ".join(k for k, v in la.items() if isinstance(v, dict) and not v.get("ok"))
        return out
    # ── 위생(R10 · fail-closed) ─────────────────────────────────────────
    t0 = time.time()
    kG = lambda m: (GEO.xs_z(GEO._align(P["m"][m], GEOP[m]["geo"], "G")) if (m in P["m"] and m in GEOP) else None)
    kF = lambda m: (GEO.xs_z(FRAG._vals(P["m"][m], FR[m]["rows"], "F")) if (m in P["m"] and m in FR) else None)
    gseed = seed + SEED_OFF["leak"] + 700
    stat02 = lambda Pp: GEO.w02_fm(Pp, GEOP, Pp["kind"], months=[m for m in dec_ok if m in Pp["m"]], B=H.LEAK_B, seed=gseed + 1)["summary"]
    stat11 = lambda Pp: FRAG.w11_fm(Pp, FR, s_t, Pp["kind"], months=[m for m in dec_ok if m in Pp["m"]], B=H.LEAK_B, seed=gseed + 2)["interaction"]
    P02, P11 = with_signal(P, "sig_w02", kG), with_signal(P, "sig_w11", kF)
    hy = {}
    bl = H.blind_panel(P, seed + SEED_OFF["blind_panel"] + 7)
    try:
        tb = [stat02(bl), stat11(bl)]
        hy["blind_smoke"] = {"ok": all(x.get("t") is not None and x.get("p_wild_two") is not None for x in tb), "n": 2,
                             "rule": "가족 B 주 통계 · 부트스트랩 p 를 y 씨앗 잡음 패널에서 끝까지(값은 버린다)"}
    except Exception as e:                                                  # noqa: BLE001
        hy["blind_smoke"] = {"ok": False, "err": type(e).__name__}
    del bl
    nleak = cap["leak"] or H.LEAK_N
    hy["label_shuffle_leak"] = {"W02": H.label_shuffle_leak(stat02, P02, seed + SEED_OFF["leak"] + 5000, n=nleak),
                                "W11": H.label_shuffle_leak(stat11, P11, seed + SEED_OFF["leak"] + 6000, n=nleak)}
    hy["label_shuffle_leak"]["ok"] = all(v["ok"] for v in hy["label_shuffle_leak"].values() if isinstance(v, dict))
    npl = cap["plant"] or H.PLANT_REPS
    need = min(H.PLANT_NEED, npl) if smoke else H.PLANT_NEED
    res02p = H.residualizer(lambda m, D: GEO.w02_designs(D, GEOP[m]["geo"]) if m in GEOP else None)
    res11p = H.residualizer(lambda m, D: S.stage_m_w_design(D, [("frag", D["sig_w11"])], focal_miss="drop"))
    pr = {"W02": H.planted_recovery(stat02, P02, "sig_w02", +1, seed + SEED_OFF["plant"] + 300, reps=npl, need=need, resid_of=res02p)}
    good, d11 = 0, WC.CARD_DIRECTION["W11"]
    for i in range(npl):
        tt = stat11(plant_interaction(P11, "sig_w11", s_t, H.PLANT_IC, d11, np.random.default_rng(seed + SEED_OFF["plant"] + 400 + i), resid_of=res11p)).get("t")
        good += int(tt is not None and tt == tt and d11 * tt >= H.PLANT_T)
    pr["W11"] = {"ok": good >= need, "good": good, "reps": npl, "need": need, "residualized": True,
                 "rule": "교차항 IC %.3f 를 통제로 잔차화한 방향에 심는다(방향 −1 · R10)" % H.PLANT_IC}
    pr["ok"] = all(v["ok"] for v in pr.values() if isinstance(v, dict))
    hy["planted_recovery"] = pr
    hy["lookahead_shift"] = {"ok": la["ok"]}
    f0 = ctx.get("f0_doc") or {}
    same_t1 = (f0.get("tier1_months") or {}).get("months") == ctx["t1"]["months"] if f0 else None
    rb = (f0.get("reg_B_f0") or {}) if f0 else {}
    gate_b = bool(((rb.get("w02_f0") or {}).get("gate") or {}).get("coverage_pass") and ((rb.get("w11_f0") or {}).get("gate") or {}).get("gate_pass")) \
        if f0 else bool(smoke)
    hy["coverage_f0"] = {"ok": bool(same_t1 and gate_b) if f0 else bool(smoke), "same_as_registered_f0": same_t1, "reg_B_gates": gate_b, "T": ctx["t1"]["T"]}
    hy["run_all"] = H.run_all_scoped({k: hy[k] for k in H.PIPELINE_GATES + H.CARD_GATES}, WC.FAMILY["B"])
    out["hygiene"] = hy
    tick("hygiene", t0)
    del P02, P11
    card_ok = hy["run_all"]["card_ok"]
    if not hy["run_all"]["ok"] and not smoke:
        out["stopped"] = "위생 실패(%s)" % ", ".join(hy["run_all"]["failed"] + hy["run_all"]["missing"])
        return out
    # ── 가족 B Tier-1 · Holm ─────────────────────────────────────────────
    t0 = time.time()
    t1 = {}
    m02 = GEO.w02_fm(P, GEOP, kind, months=dec_ok, B=WC.WILD_B, seed=seed + WC.FAMILY_SEED_OFF["W02"])
    t1["W02"] = {"main": m02["summary"], "indmom": GEO.w02_fm(P, GEOP, kind, months=dec_ok, variant="indmom")["summary"]}
    g3 = GEO.smooth3({m: {t: v["G"] for t, v in GEOP[m]["geo"].items()} for m in GEOP}, dec_ok)
    t1["W02"]["smooth3"] = GEO.w02_fm(P, GEOP, kind, months=dec_ok, variant="smooth3", g3_by_month=g3)["summary"]
    try:
        t1["W02"]["sigma_analytic"] = S.sigma_analytic(m02["fm"]["parts"], "geo_g")
    except SystemExit:
        t1["W02"]["sigma_analytic"] = None
    nsh = min(cap["nperm"], GEO.N_SHUFFLE)
    sh = GEO.cbsa_shuffle(P, GEOP, kind, n=int(nsh), seed=GEO.SHUFFLE_SEED, months=dec_ok)
    t1["W02"]["cbsa_shuffle"] = {"n": int(nsh), "rank": S.placebo_rank(m02["summary"]["nw_t"], sh["t"], +1), "role": "주의 칸(K5 · G9)"}
    ms_k = [m for m in dec_ok if kG(m) is not None]
    ics = S.ic_series(ms_k, kG, lambda m: S.sector_demean(P["m"][m]["y"], P["m"][m]["sec"]), kind)
    t1["W02"]["ic"] = S.summarize(ics["months"], ics["ic"], +1)
    w11 = FRAG.w11_fm(P, FR, s_t, kind, months=dec_ok, B=WC.WILD_B, seed=seed + WC.FAMILY_SEED_OFF["W11"])
    t1["W11"] = {"interaction": w11["interaction"], "main": w11["main"], "n_state": w11["n_state"],
                 "xtwin": FRAG.w11_fm(P, FR, s_t, kind, months=dec_ok, key="X")["interaction"],
                 "nagel": FRAG.w11_fm(P, FR, sN, kind, months=dec_ok)["interaction"], "reversal_placebo_synth": FRAG.reversal_placebo()}
    fk = ("t", "T", "df", "p_wild_one", "p_wild_two", "B", "seed", "direction")
    fam = {"W02": {k: m02["summary"].get(k) for k in fk}, "W11": {k: w11["interaction"].get(k) for k in fk}}
    for c in fam:
        fam[c]["hygiene_fail"] = not card_ok.get(c, False)
    holm = WC.holm_family(fam, "B", alpha=WC.FAMILY_ALPHA)
    h5m = set(((ctx["t1"].get("sensitivity") or {}).get("count_and_cap_095") or {}).get("months") or [])      # R17 🔁 남은 가격 구멍 민감도(보고)
    t1["H5_sensitivity"] = {"T_months": len(h5m), "rule": "개수 ∧ 시총 몫 ≥ 0.95 달만(보고 · 가족 밖)",
                            "W02": GEO.w02_fm(P, GEOP, kind, months=[m for m in dec_ok if m in h5m])["summary"],
                            "W11": FRAG.w11_fm(P, FR, s_t, kind, months=[m for m in dec_ok if m in h5m])["interaction"]}
    out["tier1"], out["family"] = t1, {"stats": fam, "holm": holm, "note": WC.FAMILY_NOTE, "power": WC.HONEST_POWER}
    tick("tier1_family", t0)
    # ── Tier-2 · 무해 · 채택 ─────────────────────────────────────────────
    t0 = time.time()
    exe02 = lambda m, Ed, T: GEO.w02_execute(Ed, T)
    bk = {}
    for arm, thf in (("W02_S", lambda m: GEO.THETA0), ("W02_C", lambda m: th02.get(m))):
        b = {}
        for m in dec:
            if m in X and m in GEOP and m not in drift:
                w, _ = GEO.w02_book(X[m], GEOP[m]["geo"], thf(m))
                if w is not None:
                    b[m] = X[m].book(w)
        bk[arm] = b
    t2 = {k: tier2_arm(E, w_path(E, X, b, dec, rate="liq", executor=exe02, drift=drift), regs, k) for k, b in bk.items()}
    for var in ("main", "uncond", "beta", "xtwin"):
        b = {}
        for m in dec:
            if m in X and m in FR and m not in drift:
                rows = FR[m]["X"] if var == "xtwin" else FR[m]["rows"]
                w, _ = FRAG.w11_book(X[m], rows, s_t.get(m, 0.0), variant=var)
                b[m] = X[m].book(w)
        t2["W11_" + var.upper()] = tier2_arm(E, w_path(E, X, b, dec, drift=drift), regs, "W11_" + var.upper())
    nr = min(cap["nperm"], FRAG.N_RANDOM)
    rx = []
    for i in range(int(nr)):
        rr = np.random.default_rng(FRAG.RANDOM_SEED + 1000 * i)
        b = {}
        for m in dec:
            if m in X and m in FR and m not in drift:
                w, _ = FRAG.w11_book(X[m], FR[m]["rows"], s_t.get(m, 0.0), variant="random", rng=rr)
                b[m] = X[m].book(w)
        a = tier2_arm(E, w_path(E, X, b, dec, drift=drift), regs, "W11_RANDOM")
        rx.append(((a.get("s_tests") or {}).get("h1_10") or {}).get("mean"))
    obs = ((t2["W11_MAIN"].get("s_tests") or {}).get("h1_10") or {}).get("mean")
    out["w11_random"] = {"n": int(nr), "rank_main_X": pct_rank(obs, rx, +1), "rule": "같은 달 · 같은 s_t · 같은 개수 무작위 20% 축소(F9)"}
    act = FRAG.activity(s_t, dec)
    harm = {"W02": t2["W02_S"]["harmless"], "W11": t2["W11_MAIN"]["harmless"]}              # R22 🔁 W02 채택 책 = S 책(C 가닥은 쌍둥이로 강등)
    shr = t1["W02"]["cbsa_shuffle"]["rank"]
    caut = {"W02": {"cbsa_shuffle_rank_ge095": (None if shr is None else bool(shr >= 0.95)), "c_arm_demoted_twin": True},
            "W11": {"data_gate": (gate_b if f0 else None), "activity_label": act["label"], "hygiene_card_ok": card_ok.get("W11")}}
    caut["W02"]["hygiene_card_ok"] = card_ok.get("W02")
    out["adoption"] = WC.adoption_table(holm, harm, {c: dec_g["gegd_pass"].get(c) for c in ("W02", "W11")}, caut)
    out["tier2"] = t2
    out["tier2_delta"] = {"W02_C_minus_S": delta_arm(t2["W02_C"], t2["W02_S"], regs), "W11_MAIN_minus_UNCOND": delta_arm(t2["W11_MAIN"], t2["W11_UNCOND"], regs),
                          "W11_MAIN_minus_BETA": delta_arm(t2["W11_MAIN"], t2["W11_BETA"], regs)}
    out["w11_activity"] = {k: v for k, v in act.items() if k != "active"}
    tick("tier2_family", t0)
    out["secondary_BY"] = by_block(out)
    out["expected_effect"] = eb_block(fam)
    n1 = 8
    out["n_arms"] = {"tier1": n1, "tier2": len(t2) + 1, "total": n1 + len(t2) + 1,
                     "rule": "등록 B — Tier-1(W02 주 · INDMOM · 평활 · IC · W11 주 · X · Nagel · 주 효과) + Tier-2 책 팔 + 무작위 묶음 1"}
    out["cumulative_N"] = {"lab": LAB_N_BASE, "w_arms_B": out["n_arms"]["total"], "total": LAB_N_BASE + out["n_arms"]["total"],
                           "note": "등록 A 팔 수는 A 결과 문서에 따로 — 둘을 더한 누적은 B 결과 문서 머리에"}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  등록 전 F0(🚨 수익 · 신호-수익 통계 없음 — 개수 · 몫 · 날짜 · 라벨 · 시장 상태 셈)
# ══════════════════════════════════════════════════════════════════════════
def _f0_child():
    """F0 자식 과정 — open 감사 고리 · 우주 · 패널(y 없음) · 커버리지 · 위생 셈 · 스위치 활성 · 앵커 · FOMC · 등록 B F0 요약."""
    import numpy as np
    import warnings
    import w_cards as CD
    import w_ciq as CQ
    import w_ipca as IP
    import w_panel as WP
    WG.install_open_audit()
    out_path = os.environ.get("WBATCH_F0_OUT")
    if not out_path:
        raise SystemExit("🚨 F0 산출 경로가 없다")
    t0 = time.time()
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        warnings.simplefilter("ignore")
        ctx = build_ctx("f0", with_y=False)
        SU, P, dec = ctx["U"], ctx["P"], ctx["dec"]
        t1 = ctx["t1"]
        cov = ctx["cov"]
        yrs = {}
        for m, r in cov.items():
            y = yrs.setdefault(m[:4], {"months": 0, "pass": 0, "cov_n_min": 1.0, "cov_cap_min": 1.0, "n_med": []})
            b = t1["by_month"].get(m) if m in t1["by_month"] else None
            cn = r["n_px"] / r["n"] if r["n"] else 0.0
            cc = r["cap_px"] / r["cap"] if r["cap"] else 0.0
            y["months"] += 1
            y["pass"] += int(cc >= WP.COV_THR)
            y["cov_n_min"] = min(y["cov_n_min"], cn)
            y["cov_cap_min"] = min(y["cov_cap_min"], cc)
            y["n_med"].append(r["n_px"])
        for y in yrs.values():
            y["world_median"] = float(np.median(y.pop("n_med")))
            y["cov_n_min"] = round(y["cov_n_min"], 4)
            y["cov_cap_min"] = round(y["cov_cap_min"], 4)
        ms_flag = WP.me_flag_summary(SU, ctx["months"])
        hole = WP.price_hole_summary(SU, dec, last_month=WP.TIER1[1])
        anc = WC.frozen("v_px_split").anchors(U=SU)
        s4_fac = CQ.market_factors(SU, WC.months_between("2009-02", WC.mshift(IP.LAST_DECISION, 1)), {str(k): float(v) for k, v in rf_monthly().items()})
        wm = sorted(set([CQ.FIRST_DECISION] + [m for m in ctx["months"] if m >= CQ.FIRST_DECISION]))
        wins = CQ.run_windows(SU, wm, s4_fac)
        dz = CQ.state_z({m: w["d_last"] for m, w in wins.items()}, sorted(wins))
        th = {m: CQ.theta_c(dz.get(m)) for m in dec}
        conv = [bool(wins[m]["converged"]) for m in dec if m in wins]
        trig = CD.vol_trigger(CD.sp_daily())
        trig_ms = [m for m in dec if (trig.get(m) or {}).get("trig")]
        ev, prev = 0, None
        for m in trig_ms:
            if prev is None or WC.mno(m) - WC.mno(prev) > 2:
                ev += 1
            prev = m
        iqr = {}
        for m in P["months"]:
            v = np.asarray(P["m"][m]["tail"], float)
            v = v[np.isfinite(v)]
            if len(v) >= 20:
                iqr[m] = float(np.quantile(v, 0.75) - np.quantile(v, 0.25))
        ist = CD.iqr_state(iqr, P["months"])
        cal = CD.fomc_calendar(fetch=False)
        n_t1 = sum(1 for d in cal["dates"] if CD.FOMC_T1[0] <= d[:7] <= CD.FOMC_T1[1])
        nsec = {}
        for m in dec:
            ss = {SU.sector(r["t"], m, r["ndx_only"])[0] for r in SU.members(m)}
            nsec[m] = len([s for s in ss if s])
        cross = ctx["cross"]
        n_state = {k: sum(1 for m in dec if (cross.get(m) or {}).get(k) is not None) for k in ("z_baa", "z_vix")}
        regb = {}
        for nm in ("w02_f0", "w11_f0"):
            p = os.path.join(WC.CACHE, "f0", nm + ".json")
            if os.path.exists(p):
                d = _read_json(p)
                if nm == "w02_f0":
                    cv, dc = d.get("coverage") or {}, d.get("decision") or {}
                    tops = [sum(x.get("share") or 0.0 for x in (v.get("top") or [])[:15]) for v in (d.get("top_cbsa") or {}).values()]
                    rl = d.get("relocation") or {}
                    g = {"coverage_pass": cv.get("pass"), "median_share": cv.get("median_share"), "min_share": cv.get("min_share"), "gate": cv.get("gate"),
                         "close_card": dc.get("close_card"), "switch_to_sgml": dc.get("switch_to_sgml"), "sgml_changes_values": dc.get("sgml_changes_values"),
                         "relocation_mismatch": rl.get("n_mismatch"), "relocation_n": len(rl.get("rows") or []),
                         "sgml_same": "%s/%s" % ((d.get("sgml_check") or {}).get("n_same"), (d.get("sgml_check") or {}).get("n")),
                         "top15_share_min": (round(min(tops), 3) if tops else None), "top15_share_max": (round(max(tops), 3) if tops else None),
                         "density_theta_range": [(d.get("density") or {}).get("theta_min"), (d.get("density") or {}).get("theta_max")]}
                else:
                    gt, dc = d.get("gate") or {}, d.get("decision") or {}
                    g = {"gate_pass": gt.get("pass"), "start_listed": gt.get("start_listed"), "holders_min_by_quarter": gt.get("holders_min_by_quarter"),
                         "link_pooled": gt.get("link_pooled"), "link_min_by_quarter": gt.get("link_min_by_quarter"), "close_card": dc.get("close_card"),
                         "label": dc.get("label"), "n_active": (d.get("activity") or {}).get("n_active"), "n_events": (d.get("activity") or {}).get("n_events"),
                         "n_pos": (d.get("activity") or {}).get("n_pos"), "active_months": d.get("active_months"),
                         "io_flag_name_months": sum(int(v.get("n_io_flag") or 0) for v in (d.get("coverage") or {}).values())}
                regb[nm] = {"sha256_16": _sha_file(p)[:16], "gate": g,
                            "note": "등록 B F0(등록 전 · 개수만 · 🔁 고침 단계가 w_panel 세계(PN8 오버레이 우주)로 다시 셌다 — 비평 2 H1)"}
    noeg = noeg_block()
    doc = {"kind": "wbatch_f0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "note": "등록 전 F0 — 개수 · 몫 · 날짜 · 라벨 · 시장 상태 셈만(수익 · 신호-수익 통계 없음 · 값 계열 없음). G-EGD · P0 기록은 굽기 첫 단계(R1).",
           "coverage": {"rule": "PN2 — 달 판정 = 시총 몫 ≥ 0.95(가격 · 위생 시총 · PIT 섹터가 선 세계 후보 · w_panel.tier1_months) · 개수 몫은 보고 · "
                                "개수 ∧ 시총 ≥ 0.95(엔진 H5 판)과 배치 R 규칙은 민감도", "by_year": yrs, "vs_R": t1.get("vs_R")},
           "px_overlay": {k: v for k, v in (getattr(SU.inner, "px_overlay", None) or {}).items() if k != "env"},
           "price_hole": hole,
           "tier1_months": {"months": t1["months"], "fail": t1["fail"], "T": t1["T"], "window": list(WP.TIER1), "rule": t1["rule"],
                            "sensitivity": t1["sensitivity"], "count_share_min": t1["count_share_min"]},
           "kps_coverage": {"fail": ctx["kps"]["fail"], "min": ctx["kps"]["min"], "rule": ctx["kps"]["rule"], "w01_T": len(ctx["w01_ok"])},
           "me_sane": ms_flag, "anchors": {"gate_ok": anc.get("gate_ok"), "mae": anc.get("mae"), "n_rows": len(anc.get("rows") or []),
                                          "rows": [{k: r.get(k) for k in ("t", "m", "known_T", "calc_T", "err", "kind", "repaired")} for r in anc.get("rows") or [] if r.get("kind") == "gate"]},
           "switch_activity": {"W04_theta_ge_075_months": sum(1 for m in dec if th[m] >= 0.75), "W04_theta_le_025_months": sum(1 for m in dec if th[m] <= 0.25),
                               "W06_triggers_S": len(trig_ms), "W06_trigger_months": trig_ms, "W06_events": ev,
                               "W06_label": ("사건 측정만" if (len(trig_ms) * 2 < 12 or ev < 4) else None),
                               "W10m_state_months": sum(1 for m in dec if ist.get(m) is not None), "W01_cross_state_months": n_state,
                               "rule": "시장 상태만(수익 없음) — 이진 스위치 활성 달 < 12 또는 독립 사건 < 4 면 «사건 측정만»(규칙은 그대로 굽는다)"},
           "w04_qfa": {"converged_share_S": (float(np.mean(conv)) if conv else None), "n_windows": len(wins), "first_window_decision": CQ.FIRST_DECISION},
           "fomc": {"n": cal["n"], "n_T1": n_t1, "by_year": cal["by_year"], "source": cal["source"]},
           "w03_sectors": {"min": min(nsec.values()) if nsec else None, "max": max(nsec.values()) if nsec else None},
           "reg_B_f0": regb, "decisions_fixed": {"V06_use_sp": WP.V06_USE_SP, "twin_24_industry_groups": "삭제(빌드 없음 · F0 허용 결정)"},
           "noeg_child": {"static": noeg["static"]["ok"], "runtime": noeg["runtime"]["ok"], "open_audit": noeg["open_audit"]["ok"],
                          "n_opened": noeg["open_audit"]["n_opened"], "n_black": noeg["open_audit"]["n_black"]},
           "data_files_opened_unregistered": unregistered_data(data_files_opened()), "cache_files_opened": cache_files_opened(),
           "code_sha": code_shas(), "sec": round(time.time() - t0, 1), "peak_mb": peak_mb()}
    _write_text(out_path, json.dumps(_clean(doc), ensure_ascii=False, indent=1) + "\n")
    print("F0 자식 끝 · %.0f초" % doc["sec"])
    return 0


def f0(write_repo=True):
    """등록 전 F0 — 자식 과정에서 만든다(open 감사 · G-NoEG) → data/_wb_f0.json(공개 안전 · 값 계열 점검)."""
    tmp = WC.cache_dir("f0", "_wb_f0_tmp.json")
    env = _child_env({"WBATCH_F0_OUT": tmp})
    env.pop("WBATCH_COMMIT", None)
    t0 = time.time()
    r = _run_child("--_f0-child", env)
    if r.returncode != 0 or not os.path.exists(tmp):
        raise SystemExit("🚨 F0 자식 실패(rc %s): %s" % (r.returncode, (r.stderr or "")[-900:]))
    doc = _read_json(tmp)
    vl = WG.value_lists(doc)
    if vl:
        raise SystemExit("🚨 F0 문서에 값 계열 같은 숫자 목록: %s" % vl[:3])
    if doc.get("noeg_child", {}).get("open_audit") is not True or doc.get("data_files_opened_unregistered"):
        raise SystemExit("🚨 F0 자식 G-NoEG · 자료 범위 실패: %s" % doc.get("data_files_opened_unregistered"))
    if write_repo:
        _write_text(os.path.join(ROOT, *F0_FILE.split("/")), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    return {"sec": round(time.time() - t0, 1), "T": doc["tier1_months"]["T"], "fail": doc["tier1_months"]["fail"], "path": F0_FILE if write_repo else tmp}


def f0_table(doc=None):
    doc = doc or load_f0()
    if not doc:
        return "F0 문서 없음"
    L = []
    L.append("F0 문서 `%s` · 만든 때 %s · sha256 `%s`" % (F0_FILE, doc.get("generated_at"), _sha_lf(_bytes(os.path.join(ROOT, *F0_FILE.split("/"))))[:16]))
    L.append("")
    t1 = doc["tier1_months"]
    se = t1.get("sensitivity") or {}
    L.append("- Tier-1 결정 달(2016-08 ~ 2026-07 · PN2 시총 몫 ≥ 0.95): **T %d** · 못 넘은 달 %s(흘러간다) · 배치 R 목록과 같음 %s · 개수 몫 최소 %s" % (
        t1["T"], ", ".join(t1["fail"]) or "없음", _f(((doc.get("coverage") or {}).get("vs_R") or {}).get("same_fail")), _f(t1.get("count_share_min"), 3)))
    L.append("  - 민감도(보고): 개수 ∧ 시총 ≥ 0.95(엔진 H5 판) T %s · 배치 R 규칙(개수 ≥ 0.90 ∧ 시총 ≥ 0.95) T %s(못 넘은 달 %s)" % (
        (se.get("count_and_cap_095") or {}).get("T"), (se.get("R_rule_count090_cap095") or {}).get("T"),
        ", ".join((se.get("R_rule_count090_cap095") or {}).get("fail") or []) or "없음"))
    ov = doc.get("px_overlay") or {}
    L.append("- PN8 내부 가격 오버레이(비공개 파일 · sha256 `%s`): 채운 키 %s(새 키 %s) · 채운 종가 %s · 더한 보유월 멈춤 판정 %s" % (
        (ov.get("sha256") or "")[:16], ov.get("keys_filled"), ov.get("keys_new"), ov.get("values_filled"), ov.get("stops_added")))
    ph = (doc.get("price_hole") or {}).get("by_year") or {}
    if ph:
        L.append("- 남은 가격 구멍(오버레이 뒤 · 결정일 가격이 없는 세계 후보 · 달 평균 이름 수 · 그 가운데 창 끝 전에 명단을 떠나는 이름): %s" % (
            " · ".join("%s %s(%s)" % (y, _f(v.get("missing_mean"), 1), _f(v.get("later_exit_mean"), 1)) for y, v in sorted(ph.items()))))
    kc = doc["kps_coverage"]
    L.append("- W01 특성 커버리지(PN3): 못 넘은 달 %s · 최소 몫 %s · W01 FM 달 %s" % (", ".join(kc["fail"]) or "없음", _f(kc["min"], 3), kc["w01_T"]))
    ms = doc["me_sane"]
    L.append("- 시총 위생(PN1): 관측 %s · 결측으로 둔 이름-달 %s(사유 %s) · Tier-1 창 %s 건(%s)" % (
        ms["n_obs"], ms["n_flag"], ", ".join("%s %s" % kv for kv in ms["by_reason"].items()), ms["tier1_n_flag"],
        ", ".join("%s %s" % kv for kv in ms["tier1_names"].items()) or "없음"))
    an = doc["anchors"]
    L.append("- 시총 앵커(V 소유 표 · 위생 우주): 관문 %s · MAE %s · 관문 칸 %d" % (_f(an["gate_ok"]), _f(an["mae"], 4), len(an["rows"])))
    sw = doc["switch_activity"]
    L.append("- 스위치 활성(시장 상태만): W04 θ ≥ 0.75 달 %s · θ ≤ 0.25 달 %s · W06 발동 %s(독립 사건 %s · 라벨 %s) · W10m 상태 달 %s · W01 C 상태 달 %s" % (
        sw["W04_theta_ge_075_months"], sw["W04_theta_le_025_months"], sw["W06_triggers_S"], sw["W06_events"], sw["W06_label"] or "—",
        sw["W10m_state_months"], sw["W01_cross_state_months"]))
    q = doc["w04_qfa"]
    L.append("- W04 QFA 수렴 몫(S 창) %s · 창 %s" % (_f(q["converged_share_S"], 3), q["n_windows"]))
    fo = doc["fomc"]
    L.append("- FOMC 정례 결정일 %s(2014-06 ~ 2026-08 에 %s)" % (fo["n"], fo["n_T1"]))
    L.append("- W03 섹터 자산 수 %s ~ %s" % (doc["w03_sectors"]["min"], doc["w03_sectors"]["max"]))
    L.append("- F0 자식 G-NoEG: 정적 %s · 실행 %s · open 감사 %s(열린 파일 %s · 금지 %s)" % tuple(
        [_f(doc["noeg_child"][k]) for k in ("static", "runtime", "open_audit")] + [doc["noeg_child"]["n_opened"], doc["noeg_child"]["n_black"]]))
    L.append("")
    L.append("| 해 | 결정 달 | 통과 | 개수 몫 최소 | 시총 몫 최소 | 세계 중앙 |")
    L.append("|---|---|---|---|---|---|")
    for y, v in sorted(doc["coverage"]["by_year"].items()):
        L.append("| %s | %s | %s | %s | %s | %s |" % (y, v["months"], v["pass"], _f(v["cov_n_min"], 4), _f(v["cov_cap_min"], 4), _f(v["world_median"], 0)))
    return "\n".join(L)


# ══════════════════════════════════════════════════════════════════════════
#  얼린 파일 표 · 등록 직전 점검
# ══════════════════════════════════════════════════════════════════════════
def _blob(p):
    b = _bytes(p).replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def pins_table():
    L = ["| 파일 | git blob(앞 12자) | LF SHA-256(앞 16자) | 추적 |", "|---|---|---|---|"]
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        if not os.path.exists(fp):
            L.append("| `%s` | 없음 | 없음 | — |" % p)
            continue
        tracked = _git("ls-files", "--error-unmatch", p).returncode == 0
        L.append("| `%s` | `%s` | `%s` | %s |" % (p, _blob(fp)[:12], _sha_lf(_bytes(fp))[:16], "origin/main" if tracked else "새 파일(이 커밋)"))
    return "\n".join(L)


def precommit():
    res = {}
    res["names"] = name_check("A") == [] and name_check("B") == []
    for doc in (PREREG, CARDS_DOC, PREREG_B):
        fp = os.path.join(ROOT, *doc.split("/"))
        res["placeholders:" + os.path.basename(doc)] = placeholder_counts(_read_text(fp)) if os.path.exists(fp) else None
    res["manifest"] = manifest_problems(full=False) == []
    res["f0"] = f0_check(load_f0(), code_shas()) == []
    res["frozen_v"] = WC.frozen_check()["ok"]
    res["site_guard"] = site_guard()["ok"]
    ne = WG.noeg_static()
    res["noeg_static"] = ne["ok"] and "w_run" in ne["targets"]
    res["registered_constants"] = registered_constants_ok("A") == []
    res["closure_frozen"] = closure_in_frozen()
    res["versions"] = all(_versions().get(k) == v for k, v in VERSIONS.items())
    return res


def closure_in_frozen():
    """w_run(과 별도 과정 w_cmp · w_audit)의 로컬 폐포가 얼린 파일 안에 있다."""
    r = WG.closure(["w_run"])
    rc = WG.closure(["w_cmp"], stop_forbidden=False)
    need = sorted(set(r["reached"]) | {"w_cmp", "w_audit"})
    miss = ["build/%s.py" % m for m in need if "build/%s.py" % m not in FROZEN]
    cmp_side = [m for m in rc["reached"] if m.startswith(("v_", "w_")) and m != "w_cmp"]
    return {"ok": not miss and not cmp_side, "missing": miss, "cmp_reaches_w_or_v": cmp_side, "n": len(need)}


# ══════════════════════════════════════════════════════════════════════════
#  러너 눈가린 연기(산출 · 표식은 임시 폴더 · 열지 않고 지운다)
# ══════════════════════════════════════════════════════════════════════════
def smoke(reg="A"):
    import secrets
    t0 = time.time()
    base = tempfile.mkdtemp(prefix="wbatch_runner_smoke_%s_" % secrets.token_hex(3), dir=WC.CACHE)
    out = os.path.join(base, "out")
    gm = os.path.join(base, "gitmark")
    tg = os.path.join(base, "tag")
    for d in (out, gm, tg):
        os.makedirs(d, exist_ok=True)
    _OVR.update({"out": out, "gitmark": gm, "tag": tg})
    res = {"ok": False}
    try:
        rec = bake("SMOKE", smoke_env={"WBATCH_SMOKE": "1"}, reg=reg)
        P = paths(out, reg)
        exist = {k: os.path.exists(P[k]) for k in ("out", "public", "runlog", "child", "prep", "books", "gegd", "mark", "gitmark")}
        again = None
        try:
            start_guard("SMOKE", None, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], None)
            again = "열렸다(실패)"
        except SystemExit:
            again = "막혔다"
        sizes = {k: os.path.getsize(P[k]) for k in exist if exist[k]}
        res = {"ok": bool(all(exist.values()) and not rec["registration_error"] and rec["cmp"]["refused_without_registration"] and again == "막혔다"),
               "sec": round(time.time() - t0, 1), "sec_prep": rec["sec_prep"], "sec_gegd": rec["sec_gegd"], "sec_child": rec["sec_child"],
               "exist": exist, "bytes": sizes, "registration_error": rec["registration_error"], "cmp_refused": rec["cmp"]["refused_without_registration"],
               "second_start": again, "stopped": rec["stopped"], "peak_mb_child": rec["peak_mb_child"], "peak_mb_prep": rec["peak_mb_prep"],
               "local_modules_child": rec["local_modules_child"], "unfrozen": rec["unfrozen_modules"], "noeg_child": rec["noeg_child"],
               "data_files_opened_n": len(rec["data_files_opened"] or []), "cache_files_opened": rec.get("cache_files_opened"), "clock_child": rec["clock_child"],
               "shape_child": rec.get("shape_child")}
    finally:
        _OVR.update({"out": None, "gitmark": None, "tag": None})
        shutil.rmtree(base, ignore_errors=True)
        res["deleted_unread"] = not os.path.exists(base)
    return res


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 · 실자료 수익 없음)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_start_guard():
    full = "a" * 40
    assert start_guard(full, None, [], None)
    assert _raises(lambda: start_guard(full, None, [("m", full + " · x\nFINISHED y")], None))
    assert _raises(lambda: start_guard(full, "r", [("m", full + " · x\nFINISHED y")], None))
    assert _raises(lambda: start_guard(full, None, [], "b" * 40))
    assert _raises(lambda: start_guard(full, None, [("m", full + " · x")], None))
    assert _raises(lambda: start_guard(full, "r", [], None))
    assert _raises(lambda: start_guard(full, "r", [("m", "c" * 40 + " · x")], None))
    assert start_guard(full, "r", [("m", full + " · x")], None) and start_guard(full, "r", [("m", full + " · x")], full)
    assert _raises(lambda: start_guard(full, None, [], full))
    return "시작 표식 9 갈래(FINISHED · 다른 태그 · 표식만 · RERUN 조건 · 다른 커밋 · 태그만)"


def _st_frozen_check_env():
    assert _raises(lambda: frozen_check(env={}))
    assert _raises(lambda: frozen_check(env={"WBATCH_COMMIT": "0" * 40, "_WBATCH_NO_FETCH": "1"}))
    assert placeholder_counts("a %s b %s c" % (PLACEHOLDER + "⟩", DRAFT_MARK)) == (1, 1) and placeholder_counts("깨끗") == (0, 0)
    assert f0_check({}) and f0_check({"kind": "wbatch_f0"}) and _raises(lambda: child_gate("x", "y"))
    good = {"kind": "wbatch_f0", "anchors": {"gate_ok": True}, "noeg_child": {"runtime": True, "open_audit": True, "static": True},
            "tier1_months": {"months": ["2016-08"]}, "code_sha": {"build/w_run.py": "x"}}
    for k in F0_KEYS:
        good.setdefault(k, {})
    good["px_overlay"] = {"sha256": "a" * 64, "values_filled": 5}
    man = {"w_cache": {"px_overlay": {"sha256": "a" * 64}}}
    assert f0_check(good, manifest=man) == [] and f0_check(good, {"build/w_run.py": "y"}, manifest=man)
    assert f0_check(dict(good, anchors={"gate_ok": False}), manifest=man)
    assert f0_check(good, manifest={"w_cache": {"px_overlay": {"sha256": "b" * 64}}})                       # 오버레이 sha ≠ 명세
    assert f0_check(dict(good, px_overlay={}), manifest=man)                                                  # 오버레이 없는 F0 거부
    return "빈 환경 · 없는 커밋 · 빈칸 셈 · F0 거르개(PN8 오버레이 sha = 명세) · 자식 판"


def _st_constants():
    bad = registered_constants_ok("A")
    assert bad == [], bad
    VD = WC.frozen("v_data")
    assert tuple(VD.LAB_FILES) == V_LAB_FILES and tuple(VD.LAB_DIRS) == V_LAB_DIRS
    assert WC.FORWARD_LEDGER is None and all("_wfwd" not in p for p in FROZEN) and set(FIRST_ADDED["A"]) >= {F0_FILE, MANIFEST_FILE}
    assert set(WG.WB_ALLOWED) == {F0_FILE, MANIFEST_FILE}
    cl = closure_in_frozen()
    assert cl["ok"], cl
    return "등록 상수 %d · V 자료 목록 = frozen v_data · 전방 원장 없음 · 공개 파일 둘 · 폐포 ⊆ 얼린 파일(%d)" % (len(REGISTERED), cl["n"])


def _fake_E(months, names, seed=3):
    import numpy as np
    rng = np.random.default_rng(seed)
    H = {m: {t: float(rng.normal(0.005, 0.05)) for t in names} for m in months}
    E = types.SimpleNamespace()
    E.hold = lambda m: H[m]
    E.hold_split = lambda m: {t: (0.0, v) for t, v in H[m].items()}
    E.spy_hold = lambda m: 0.01
    E.liq_rate = lambda: {}
    return E, H


def _st_path():
    import numpy as np
    import w_cards as CD
    rng = np.random.default_rng(WC.SEED)
    n = 40
    names = ["N%02d" % j for j in range(n)]
    months = ["2020-%02d" % k for k in range(1, 13)]
    X = {}
    for m in months:
        me = rng.lognormal(3, 1, n)
        wB = me / me.sum()
        X[m] = CD.Cross(m, names, me, wB, ["S%d" % (j % 4) for j in range(n)], [False] * n, rng.normal(1, 0.2, n))
    sc = {m: {t: float(rng.normal()) for t in names} for m in months}
    bk = books_path(X, months, sc.get, lambda m: 0.75)
    assert set(bk) == set(months) and all(abs(sum(b.values()) - 1) < 1e-9 for b in bk.values())
    E, H = _fake_E(months, names)
    df = w_path(E, X, bk, months)
    assert len(df) == 12 and (df.index.astype(str)[0] == "2020-02") and df["traded"].iloc[0] == 0.0
    drift = {"2020-05"}
    bk2 = books_path(X, months, sc.get, lambda m: 0.75, drift=drift)
    assert "2020-05" not in bk2
    df2 = w_path(E, X, bk2, months, drift=drift)
    assert df2.loc[df2.index.astype(str) == "2020-06", "traded"].iloc[0] == 0.0            # 흘러간 달은 거래 0
    # θ = 0 → 슬리브 = w_B(투영 · β 띠 뒤) — X 는 0 근처(비용 없는 판)
    bk0 = books_path(X, months, sc.get, lambda m: 0.0)
    for m in months:
        wb = X[m].book(X[m].wB)
        assert max(abs(bk0[m].get(t, 0.0) - wb.get(t, 0.0)) for t in set(wb) | set(bk0[m])) < 1e-9
    fa = frictionless_active(E, X, bk0, months)
    assert all(abs(v) < 1e-12 for v in fa.values())
    assert theta_stat({m: 0.75 for m in months}, 0.75, {m: 1.0 for m in months}) == 0.0
    assert pct_rank(1.0, [0.0, 2.0], +1) == 0.5 and pct_rank(None, [1.0]) is None
    return "선정 경로 · 체결 경로(첫 달 미과금 · 흘러간 달 거래 0) · θ = 0 = w_B · 마찰 없는 능동 0 · 위약 순위"


def _st_public():
    fake = {"reg": "A", "prereg": PREREG, "prereg_commit": "0" * 40, "stopped": None, "smoke": True,
            "family": {"stats": {"W01": {"t": 1.0, "T": 100}}, "holm": {"reject": {"W01": False}, "p": {"W01": 0.2}, "m": 3, "alpha": 0.05,
                                                                        "family": ["W01", "W04", "W10m"], "direction": {"W01": 1}}},
            "adoption": {"W01": {"path": "x", "conds": {}, "adopt": False, "cautions": {}}},
            "W03": {"pap": {"summary": {"T": 120, "nw_t": 1.0}}, "diag": {"summary": {}}, "pep_pap": {"summary": {}},
                    "l_twin_internal": {"summary": {"mean": 0.1, "nw_t": 3.0}}, "l_twin_public": {"first_hold": "2006-09", "T": 240, "same_sign_as_S": True},
                    "placebo": {"n": 3}, "tier2": {"n": 0}}}
    pv = public_view(fake, "ab" * 32, 10, None)
    assert public_leaks(pv) == [], public_leaks(pv)
    s = json.dumps(pv, ensure_ascii=False)
    assert "l_twin_internal" not in s and '"nw_t": 3.0' not in s and "wbatch_public_view" in s
    bad = dict(pv, W03=dict(pv["W03"], l_twin={"mean": 0.1}))
    assert public_leaks(bad)
    doc = result_doc(pv)
    assert "배치 W" in doc and "채택 표시" in doc and "연기 산출" in doc and PLACEHOLDER not in doc
    import numpy as np
    import pandas as pd
    c = _clean({"a": np.float64("nan"), "b": pd.Series([1.0], index=pd.PeriodIndex(["2020-01"], freq="M")), (1, 2): np.int64(3)})
    assert c["a"] is None and "__series__" in c["b"] and c["1|2"] == 3
    json.dumps(c, allow_nan=False)
    return "게시 칸(내부 L 쌍둥이 수치 · 계열 없음) · 누수 점검 · 렌더러 · 직렬화"


def _st_state_la():
    """R10 상태 선견(합성 FRED 계열): 결정일 = 월말이면 통과 · 결정일을 그달 두 번째로 늦은 관측 날로 당기면(규칙이 결정일 값을 쓰는 꼴) 걸린다."""
    import datetime as _dt
    import numpy as np
    rng = np.random.default_rng(WC.SEED + 9)
    d0, d1 = _dt.date(1995, 1, 2), _dt.date(2026, 8, 31)
    days = [d0 + _dt.timedelta(days=i) for i in range((d1 - d0).days + 1)]
    days = [d for d in days if d.weekday() < 5]
    baa = {d.isoformat(): float(v) for d, v in zip(days, 2.0 + np.cumsum(rng.normal(0, 0.02, len(days))))}
    vix = {d.isoformat(): float(v) for d, v in zip(days, 18.0 + np.cumsum(rng.normal(0, 0.1, len(days))))}
    mac = {"BAA10Y": baa, "VIXCLS": vix}
    last, second = {}, {}
    for d in sorted(baa):
        m = d[:7]
        if m in last:
            second[m] = last[m]
        last[m] = d
    ms = WC.months_between("2016-08", "2017-07")
    ok = state_lookahead(mac, ms, lambda m: last[m])
    bad = state_lookahead(mac, ms, lambda m: second[m])
    assert ok["ok"] and ok["n"] == 12, ok
    assert not bad["ok"] and bad["n_bad"] == 12, bad
    return "결정일 = 월말 통과 · 결정일을 쓰인 관측 날로 당기면 12/12 적발(값 독 넣기)"


def _st_gegd_dec():
    g = {"cards": {"W01": {"pass": False}, "W01_KPS7": {"pass": True}, "W04": {"pass": True}}}
    d = gegd_decisions(g)
    assert d["w01_chars"] == "KPS7" and d["gegd_pass"]["W01"] is True and d["gegd_pass"]["W04"] is True and d["gegd_pass"]["W10m"] is False
    d2 = gegd_decisions({"cards": {"W01": {"pass": True}, "W01_KPS7": {"pass": False}}})
    assert d2["w01_chars"] == "KPS8" and d2["gegd_pass"]["W01"] is True
    d3 = gegd_decisions({})
    assert d3["w01_chars"] == "KPS7" and not any(d3["gegd_pass"].values())
    return "R2 W01 판 고르기 · fail-closed(칸 없음 = 거짓)"


def _st_plant():
    import numpy as np
    rng = np.random.default_rng(5)
    months = ["2018-%02d" % k for k in range(1, 13)] + ["2019-%02d" % k for k in range(1, 13)]
    P = {"kind": "synth", "months": months, "m": {m: {"sig": rng.normal(size=300), "y": rng.normal(size=300)} for m in months}}
    st = {m: float(rng.normal()) for m in months}
    Q = plant_interaction(P, "sig", st, 0.2, +1, np.random.default_rng(1))
    import w_hygiene as H
    g = []
    for m in months:
        u = np.nan_to_num(H.normal_scores(P["m"][m]["sig"]))
        g.append(float(np.corrcoef(u, Q["m"][m]["y"])[0, 1]))
    s = np.array([st[m] for m in months])
    assert np.corrcoef(g, s)[0, 1] > 0.8 and Q["kind"] == "synth"
    W = with_signal(P, "k", lambda m: np.ones(300) if m != months[0] else None)
    assert months[0] not in W["m"] and len(W["months"]) == len(months) - 1
    return "교차항 심기(달별 IC 가 상태와 함께 움직인다) · 신호 붙인 패널"


def _st_open_encoding():
    import ast
    src = _read_text(os.path.abspath(__file__))
    bad = []
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Call) and getattr(nd.func, "attr", getattr(nd.func, "id", None)) == "open":
            mode = next((a.value for a in nd.args[1:2] if isinstance(a, ast.Constant)), None)
            kw = {k.arg for k in nd.keywords}
            owner = getattr(getattr(nd.func, "value", None), "id", None)
            if owner in ("gzip",) or (mode and "b" in str(mode)):
                if owner == "gzip" and mode and "t" in str(mode) and "encoding" not in kw:
                    bad.append(nd.lineno)
                continue
            if "encoding" not in kw:
                bad.append(nd.lineno)
    assert not bad, bad
    return "open() 인코딩(텍스트 모드 모두 encoding)"


def selftest():
    res, ok = [], True
    for fn in (_st_start_guard, _st_frozen_check_env, _st_constants, _st_path, _st_public, _st_gegd_dec, _st_plant, _st_state_la, _st_open_encoding):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-22s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_run selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════
#  입구
# ══════════════════════════════════════════════════════════════════════════
def _arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else default


if __name__ == "__main__":
    reg = _arg("--reg", "A")
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--_prep-child" in sys.argv:
        raise SystemExit(_prep_child())
    if "--_bake-child" in sys.argv:
        raise SystemExit(_bake_child())
    if "--_f0-child" in sys.argv:
        raise SystemExit(_f0_child())
    if "--guard" in sys.argv:
        g = site_guard()
        ne = WG.noeg_static()
        print(json.dumps({"site_guard": {"ok": g["ok"], "bad": g["bad"][:5], "n_files": g["n_files"]}, "noeg_static": {k: ne[k] for k in ("ok", "n_reached", "hits", "unpinned")}},
                         ensure_ascii=False))
        raise SystemExit(0 if (g["ok"] and ne["ok"]) else 1)
    if "--manifest" in sys.argv:
        doc = data_manifest()
        vl = WG.value_lists(doc)
        if vl:
            raise SystemExit("🚨 명세에 값 계열 같은 숫자 목록: %s" % vl[:3])
        _write_text(os.path.join(ROOT, *MANIFEST_FILE.split("/")), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        print("→ %s · 랩 파일 %d · 폴더 %d" % (MANIFEST_FILE, len(doc["lab_files"]), len(doc["lab_dirs"])))
        raise SystemExit(0)
    if "--f0" in sys.argv:
        print(json.dumps(f0(), ensure_ascii=False))
        raise SystemExit(0)
    if "--f0-table" in sys.argv:
        print(f0_table())
        raise SystemExit(0)
    if "--pins" in sys.argv:
        print(pins_table())
        raise SystemExit(0)
    if "--precommit" in sys.argv:
        r = precommit()
        print(json.dumps(r, ensure_ascii=False, default=str))
        raise SystemExit(0)
    if "--smoke" in sys.argv:
        r = smoke(reg)
        print(json.dumps(_clean(r), ensure_ascii=False))
        raise SystemExit(0 if r.get("ok") else 1)
    if "--result-doc" in sys.argv:
        p = _arg("--result-doc")
        print(result_doc(_read_json(p)))
        raise SystemExit(0)
    if len(sys.argv) == 1 or sys.argv[1:] in (["--reg", "A"], ["--reg", "B"]):
        raise SystemExit(main(reg))
    print(__doc__)
