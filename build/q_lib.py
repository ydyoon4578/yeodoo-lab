# -*- coding: utf-8 -*-
"""build/q_lib.py — 배치 Q 부류 D(라이브러리 결합) · Q14 L2-resid-n «잔차 1/N» · Q15 L4-engine-tsm «엔진 자기추세 교체».

근본 이유(Q14): 랩 엔진의 초과수익은 대부분 공통 노출(시장 베타 < 1 · 동일가중 − 시총가중 · 가치 · 저변동 · 모멘텀)에서 나오고, 이 노출들은
  급락과 급등 가운데 한쪽에서만 이긴다. 구성상 급락월과 급등월에 동시에 양수일 수 있는 초과는 베타 1 · 스타일 0 의 잔차뿐이다 —
  엔진 54 개의 잔차를 1/N 로 묶으면 고유 잡음은 상쇄되고, 이상현상 프리미엄이 일부라도 진짜면 그것만 남는다(Treynor-Black · Kakushadze-Yu).
  평균 수익을 쓰지 않는 1/N 이라 생존 편향이 들어오는 첫째 모멘트 통로가 끊긴다. 미리 적는 기대값은 «SPY − 비용».
근본 이유(Q15): 요인 · 전략 수익은 양의 자기상관을 가진다(Ehsani-Linnainmaa 2022 · Moskowitz-Ooi-Pedersen 2012) — 국면이 천천히 바뀌고,
  프리미엄이 사라진 전략은 한동안 계속 잃고(McLean-Pontiff), 비용이 무거운 전략의 순손실은 지속된다(Carhart 1997). 12개월 순 상대부가 양인
  엔진만 들고 진 엔진의 칸은 현금이 아니라 SPY 로 돌린다(급등에서 베타를 잃지 않는다). 반대 증거(RRG t −0.11)가 분명해 정적 켜짐비율 위약 대비.

규칙(카드 원문 — scratchpad/qbatch_final.md «# Q14» · «# Q15» · 세부는 qbatch_research.json pool L2-resid-n · L4-engine-tsm):
  자료 lib_loader.load(end='2026-08', rev='9e8ebd40')(LIBMETA 와 같다 · sid/panel sha 대조) · r̃ = r − cost_drag/12 · ETF 는 같은 판 assets.json 월말 수정종가.
  Q14 U2 = 수익엔진 ∧ pit ∧ holds∈{종목, 없음} ∧ cost_kill ≠ True(54) · 매월 말 t(2019-09 ~ 2026-07) · W_t = t−35..t · U2_t = W_t 36개월 모두 r̃ 가 선 엔진
      1단계 OLS(절편 + MKT=SPY−rf · EW=RSP−SPY · GV=IVW−IVE · LV=SPLV−SPY · MOM=SPMO−SPY) — 엔진마다 · IVW · IVE · QQQ · SPHB · SPY ≡ (1,0,0,0,0) · T-bill ≡ 0
      2단계 w = 1/N · L_P = Σ w 적재
      L2-N(F-LIB H2 통계 · 보유 불가) 엔진 w + RSP −e · IVW −g · IVE +g · SPLV −l · SPMO −m · SPY (1−b)+e+l+m · 조달 −(1−b)·rf
           X^N = R − SPY − 10bp Σ|Δpos| − 차입료(연 1.00% · 0.25/0.50 줄)/12 × 공매도 명목
      L2-LO(보유 10% 슬리브) ½ 엔진 1/N + 보완 c ≥ 0 (H = SPY · IVW · IVE · QQQ · SPHB · T-bill · Σc = ½) · 슬리브 β = 1 · GV = 0 · Σ(SPY 밖 c) 최소
           — 3개 이하 부분집합 완전 열거(동률은 H 순서 앞) → 안 되면 GV 를 버리고 2개 이하 → 그래도 안 되면 c = ½ SPY(달마다 적는다)
      |U2_t| < 30 이면 그달은 SPY · 끊긴 계열은 그달 SPY 를 벌고 달말에 SPY 로(2 × 10bp)
      대조: 주 = SPY TR(β = 1 이라 C2 와 같다) · P1(가림 없는 1/N · 분해) · P1c(½ 엔진 + ½ SPY · 보완 분리) · K4 덮개 순서 섞기(같은 U2_t 구간 안 · 1000 · 뽑기 i 씨앗 20260925 + i)
            · P4 누출(NW(3) 결합 Wald χ²(5)) · P5 조건부 중립(CRASH-M · SURGE-M 안 MKT 1 ± 0.1 · 스타일 0 ± 0.1) · 보고만 쌍둥이 L2-ERC
  Q15 U4 = 수익엔진 ∧ pit ∧ holds = 종목(58) · 매월 말 t(2017-09 ~ 2026-07) · U4_t = t−11..t 모두 r̃ 가 선 엔진
      RW_i = Π(1 + r̃/100)/Π(1 + s/100) − 1 · z = 1(RW > 0) · 칸마다 1/|U4_t| — z = 1 이면 엔진 · 아니면 SPY(현금 · 재분배 없음) · 매달 되돌림 · 10bp
      대조: 주 = 정적 켜짐비율 위약(칸 i = f_i 엔진 + (1 − f_i) SPY · f_i = 실현 켜짐비율) · C1 늘 켜진 1/N · K4 칸별 켜짐/꺼짐 구간 순서 섞기(1000 · 씨앗 20260814 한 줄기)
            · 증분 1 RRG RS-Ratio ≥ 100(PREREG-2026-09-22-RRG §1 · n 12) · 증분 2 RSP/SPY 12개월 상대부 하나로 모든 칸 교체 · (L4 − SPY) 를 각 증분에 회귀한 절편 NW t
  펀드 = 90% SPY TR + 10% 슬리브 · 매월 되돌림(qbatch_core.fund_from_path 를 월말 격자 위에서 — 되돌림 비용 2 × 10bp × 벗어난 몫).
출처: DeMiguel-Garlappi-Uppal 2009 · Kakushadze-Yu 2017 · Fama-French 2010 · McLean-Pontiff 2016 · Treynor-Black 1973(미열람) ·
  Moskowitz-Ooi-Pedersen 2012 · Ehsani-Linnainmaa 2022 · Carhart 1997 · 랩 LIBMETA(F-LIB) · UNION(519) · RRG(548) · REGIME-K4 감사(2026-08-14).

🚨 부류 D — 표본 안(Q14 2019-10 ~ 2026-08 · Q15 2017-10 ~ 2026-08)은 «오염 측정»(판정 아님). 판정은 LIBMETA F-LIB 전방(H2 · H3)에서만.
   선행조건은 두 단계(prereq_status · lib["forward"]["prereq"]):
   «commit»(등록 커밋 전 · 이 파일이 채운다) — SPHB 적재기 = sphb_monthly(lib_loader 와 같은 식 · 로드 때 단언) · U2/U4 sid 동결 = U2_SHA · U4_SHA(로드 때 단언).
   «forward»(전방 첫 결정 FWD_T0 = 2026-10-30 종가 전) — 추가만 하는 원장(data/_lib_ledger.json) · 구간 날짜 NAV 내보내기 · 사건 계수기.
   이 파일이 기대는 코드(ml_core · rrg · lib_loader · lib_meta)는 DEP_SHA 로 가져올 때 단언한다(러너 FROZEN 밖인 ml_core · rrg 포함).
🚨 selftest · dry 는 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. F0 값(켜짐비율 · 일치율 · 보완 대체 · 총노출 · 예측 G1)도 run 에서만 낸다.

  python build/q_lib.py --selftest
  python build/q_lib.py --dry
"""
from __future__ import annotations
import hashlib, itertools, json, math, os, sys, warnings

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402
import lib_loader as LL               # noqa: E402
import lib_meta as LM                 # noqa: E402  metrics · tradeoff · factor_reg · nw_t · SID_SHA · PANEL_SHA
import ml_core as MC                  # noqa: E402  corr_clusters · erc_weights(L2-ERC 쌍둥이)
import rrg as RG                      # noqa: E402  rel_from · rrg_axes(증분 1)

CARDS = {"Q14": {"cls": "D", "slot": "F-LIB-H2"}, "Q15": {"cls": "D", "slot": "F-LIB-H3"}}
NPERM = 1000                          # K4 — 연기 시험에서 작게 덮어쓴다

ROOT = os.path.dirname(HERE)
DATA_REV = LM.DATA_REV                # 9e8ebd40 — LIBMETA 와 같은 판
END, LAST_DEC, W0, FORM0 = "2026-08", "2026-07", "2016-10", "2016-08"
COST_PCT, COST20_PCT = 0.10, 0.20     # 라이브러리 틀 편도(%) — 펀드 되돌림은 Q.COST(0.0010) · 0.0020
CASH, TBILL = "_CASH", "TBILL"        # 조달(rf · 거래 비용 없음) · T-bill 보완 다리(rf · 거래 비용 있음)
# Q14
L2_FIRST, L2_WIN, L2_MIN_N = "2019-09", 36, 30
LAMBDA = 0.5                          # 슬리브 안 엔진 몫(LIBMETA L1 ANCHOR)
BORROW, BORROW_ROWS = 1.00, (0.25, 0.50)   # 연 % — 선언한 보수 고정값(출처 없음)
FNAMES = ("MKT", "EW", "GV", "LV", "MOM")
HSET = ("SPY", "IVW", "IVE", "QQQ", "SPHB", TBILL)   # 보완 집합 — 순서가 동률 깨기 순서다
HEDGE_ETF = ("IVW", "IVE", "QQQ", "SPHB")
ERC_K, ERC_SHRINK = 10, 0.2
SEED_L2 = 20260925                    # = Q.SEED
GROSS_CAP, GROSS_SHARE, DROP_SHARE, G1_CAP = 1.50, 0.25, 0.10, 0.50
NEUT_TOL, P4_ALPHA = 0.10, 0.05
TOL_EQ, TOL_NEG, TOL_TIE = 1e-10, 1e-12, 1e-12       # 열거의 수치 허용(전략 매개변수 아님)
BLOCKS_L2 = [("2019-10", "2022-03"), ("2022-04", "2024-09"), ("2024-10", "2026-08")]
# Q15
L4_FIRST, L4_LOOK = "2017-09", 12
SEED_L4 = 20260814                    # 카드 · AUDIT-2026-08-14-REGIME-K4 §2
ONF_LO, ONF_HI, AGREE_CAP, FF0_MIN_SWITCH, U4_MIN_MED = 0.10, 0.90, 0.80, 6, 30
BLOCKS_L4 = [("2017-10", "2020-03"), ("2020-04", "2022-09"), ("2022-10", "2025-03"), ("2025-04", "2026-08")]
N_U2, N_U4 = 54, 58                   # 카드가 적은 수(9e8ebd40 에서 확인)
# 등록 커밋에 얼린다(선행조건 «commit») — 표본 안 판 9e8ebd40 의 U2 · U4 sid 목록(정렬 · "\n" 으로 이은 UTF-8 의 sha256) · 전방 원장은 같은 sid 를 적는다
U2_SHA = "4a51a3dbcb6f1dbd20c0ed0df43bfcc0ee74753ce81c22d2f624d2109b131e00"
U4_SHA = "5119fcf90b41486e7efbe6eece2c343fc2a5e18cdf601a3be5b6fa482c4d5157"
# 이 파일의 결과가 기대는 코드 — CRLF → LF 로 맞춘 바이트의 sha256(러너 FROZEN 과 같은 정규화) · 가져올 때 단언
DEP_SHA = {"ml_core.py": "594c9d6e1f13207eaeac36ecd35d7f19900fbf1d157ebf0518fead503e3acdb1",       # L2-ERC 쌍둥이
           "rrg.py": "2b99185c25acbd67ebffb3162a8a92a63d0bd25624fac223f3a79ff5b89a0c5a",           # 증분 1
           "lib_loader.py": "c3fca11c30b08ccd99a7d22dc48a7382bff2e53bcbab7f963b8ba992e7efc004",    # = f2a4c7d0(LIBMETA 동결)
           "lib_meta.py": "84ea3c46c6c903b3032f4e116c1c348323c82acb2acb5f4a5259a2e5a12b49b5"}      # = f2a4c7d0(LIBMETA 동결)
# 전방 시작 — 카드 «목표 2026-10-30» 을 날짜로 박는다: 첫 전방 결정 = 2026-10 월말 종가 · 전방 1개월 = 2026-11.
#   그 종가에 «forward» 선행조건(원장)이 없으면 원장이 생긴 뒤 첫 월말 종가로 미룬다(한 규칙 · «커밋 뒤 첫 월말» 은 쓰지 않는다).
FWD_T0 = "2026-10"
FWD_START = {"t0": FWD_T0, "t0_close": "2026-10-30", "month1": Q.mshift(FWD_T0, 1),
             "rule": "첫 전방 결정 = FWD_T0 월말 종가 · 100% SPY 에서 진입 거래를 물린다 · 그 종가에 원장이 없으면 원장이 생긴 뒤 첫 월말 종가로 미룬다 · "
                     "표본 안 끝(2026-08) 과 전방 사이 달(2026-09 · 2026-10 보유)은 어느 쪽도 아니다"}


def deps_check():
    """DEP_SHA 대조 — 가져온 ml_core · rrg · lib_loader · lib_meta 가 이 폴더(build/)의 파일이고 바이트가 등록 때와 같은가. 돌려준다: 어긋난 파일 이름."""
    bad = []
    here = os.path.normcase(os.path.abspath(HERE))
    for mod in (MC, RG, LL, LM):
        p = os.path.normcase(os.path.abspath(mod.__file__))
        name = os.path.basename(p)
        ok = os.path.dirname(p) == here and name in DEP_SHA
        if ok:
            with open(p, "rb") as fh:
                ok = hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest() == DEP_SHA[name]
        if not ok:
            bad.append(name)
    return bad


_BAD_DEPS = deps_check()
if _BAD_DEPS:
    raise RuntimeError("🚨 q_lib 가 기대는 코드가 등록 때와 다르다(DEP_SHA): %s" % ", ".join(_BAD_DEPS))

INTERP_Q14 = [
    "결정은 매월 말 t(pool 원문 «Decide at every month-end t») · 첫 2019-09 · 끝 2026-07 · 보유 2019-10 ~ 2026-08(83개월).",
    "1단계 OLS 는 절편 a_i 를 넣는다(pool STEP 1 식). SPY 적재 ≡ (1,0,0,0,0) · T-bill ≡ 0(pool 항등식) · IVW/IVE/QQQ/SPHB 는 ETF 월 총수익(비용 없음) − rf.",
    "조달 −(1 − b_P)·rf 는 rf 를 버는 수익 항 — Σ|Δpos| 와 공매도 명목에서 뺀다. 공매도 명목 = 그달 시작 음의 비중 합(ETF · SPY 다리) · 차입료 = 연 %/12 × 명목.",
    "L2-LO 의 T-bill 은 거래되는 보완 다리 — rf 를 벌고 Σ|Δw| 에 10bp(LIBMETA C2 의 T-bill 다리와 같다).",
    "표본 안 첫 결정도 100% SPY 에서 시작해 진입 거래를 물린다(전방 규칙 · LIBMETA simulate 와 같다). 결정 달 끝 거래 비용은 다음 달 수익에서 뺀다(LIBMETA 관례).",
    "끊긴 계열: 그달 SPY 수익 · 달말 SPY 로 · 그달 2 × 편도(LIBMETA simulate). 다음 결정에서 U2_t 밖이므로 적재는 더 쓰지 않는다.",
    "보완 열거 순서: 크기 1 · 2 · 3, 크기 안은 H = [SPY, IVW, IVE, QQQ, SPHB, T-bill] 의 itertools.combinations 순서 — 최소를 처음 낸 부분집합이 남는다"
    "(1e-12 넘게 좋아야 바뀐다 = «H 순서 앞»). 등식 잔차 ≤ 1e-10 · c ≥ −1e-12(0 으로 자름). 계수 부족한 크기 3 은 최소 노름 해 — 그 꼭짓점은 작은 부분집합에서 이미 나온다.",
    "대체 1(GV 버림)은 Σc = ½ · β = 1 두 식으로 2개 이하 · 대체 2 는 c = ½ SPY. 달마다 level 0/1/2 를 log 에 적는다.",
    "|U2_t| < 30 이면 L2-N · L2-LO · 대조 · 쌍둥이 모두 그달 100% SPY(표시).",
    "K4: 덮개 벡터(b, e, g, l, m) 의 순서를 같은 U2_t 가 이어지는 결정 구간 안에서만 섞는다 · 엔진 1/N 은 그대로 · 비용 · 차입료를 다시 잰다 · "
    "뽑기 i 는 np.random.default_rng(20260925 + i)(계약 Q.SEED + i) 하나로 구간을 결정 순서대로 차례로 permutation. "
    "통계 = LIBMETA §1 K4 짝(주 대조 C2 = SPY): 평균 X^N(%/월) · Ψ_M = min(X_CM, X_SM). 백분위 = 참값보다 작은 뽑기 비율(LIBMETA).",
    "P4: X^N 을 보유월 [1, MKT, EW, GV, LV, MOM] 에 회귀 · NW(3) 공분산(eg30plus.nw_ols 와 같은 식 — selftest 에서 t 대조) · 다섯 기울기 Wald χ²(5) · p ≥ 0.05 이면 통과.",
    "P5: (L2-N 순수익 − rf) 를 [1, F] 에 CRASH-M 달끼리 · SURGE-M 달끼리 OLS(점추정 — NW 는 표준오차에만 닿는다). 새 최소 n 문턱은 두지 않는다 — "
    "점추정이 식별될 때(국면 달의 [1, F] 열 계수 = 모수 6 · 곧 n ≥ 6)만 잰다 · 아니면 None(측정 불가). 표본 안 창은 CRASH-M 11 · SURGE-M 23 달이라 잰다. "
    "전방: P5 가 식별되지 않으면(전방 CRASH-M 4 ~ 5 달 등) FF2 의 «P5 전방 통과» 는 충족되지 않은 것 → 보류(다음 재검정에서 다시).",
    "예측 G1(F0): 결정마다 슬리브 능동(− SPY) 적재 ℓ = ½L_P + Σc·적재_h − (1,0,0,0,0) · Σ_F = W_t 요인 공분산(ddof 1) · σ²_e = 슬리브 합성 창 안 OLS 잔차의 Σe²/(36 − 6) · "
    "몫 = Σ_{EW,LV,MOM} ℓ_k(Σ_F ℓ)_k / (ℓ'Σ_F ℓ + σ²_e)(오일러 위험기여) · 결정 평균 > 50% 이면 라벨. 실현 G1 은 같은 식을 보유월 추정으로(오염 측정).",
    "F0 총노출 = L2-N 의 조달 밖 다리 Σ|pos| · «보완 제약이 빠진 달» = level ≥ 1. |U2_t| < 30 이 한 달이라도 있거나 빠진 달 > 10% 면 f0.ok = False.",
    "L2-ERC(보고만): W_t 잔차 상관 → ml_core.corr_clusters(k 10) → 군집 안 잔차 공분산 erc_weights(축소 0.2 · 한 종목 군집은 1) → 군집 잔차 계열끼리 erc_weights · "
    "적재는 그 비중으로 · 덮개 · 차입료는 L2-N 과 같다.",
    "P1c(½ 엔진 1/N + ½ SPY)는 pool 원문의 보완 분리 대조 — 보고만.",
    "SPHB 적재기(카드 선행조건) = q_lib.sphb_monthly — lib_loader.spy_tr_monthly 와 같은 월말 식(etf_monthly)을 같은 판(9e8ebd40) assets.json 에. 로드 때 lib_loader 의 "
    "8 ETF 를 etf_monthly 로 다시 셈해 값이 똑같음을 단언한다. lib_loader.py 는 LIBMETA frozen_check(f2a4c7d0 대조) 때문에 고치지 않는다(카드 문구 수정 필요).",
    "U2 sid 동결: 등록 커밋에 U2_SHA(표본 안 판 9e8ebd40 의 54 sid · 정렬 · \\n 이음 sha256)를 박고 로드 때 단언 · 전방 원장은 같은 sid 를 적는다(원장에 없는 sid 는 끊긴 계열 → SPY). "
    "BATCH DESIGN §2(h) · §6 «sids … in the prereg commit» 를 따른다(카드의 «원장이 생긴 뒤 동결» 은 수정 필요).",
    "전방 시작 = FWD_T0 2026-10 월말 종가(전방 1개월 = 2026-11) · 100% SPY 에서 진입 거래를 물린다 · 그 종가에 원장이 없으면 원장이 생긴 뒤 첫 월말 종가로 미룬다.",
    "의존 코드 고정: ml_core.py · rrg.py · lib_loader.py · lib_meta.py 의 LF 정규화 sha256 을 DEP_SHA 로 박고 가져올 때 단언(러너 FROZEN 에 ml_core · rrg 가 없어서).",
    "펀드 틀: 월말 격자(LibGrid · 그달 마지막 거래일) 위에서 qbatch_core.fund_from_path · IX_TR = 라이브러리 SPY TR 누적(P2 assets 와 같음 — dry 에서 차 확인) · "
    "IX_PR = bench_px S&P 500 월말. 월 계열은 정확하다 · 일간 NAV 가 없어 이름 붙은 구간 · 급락 다리 · 반등 창은 비어 나온다(LIBMETA §1 과 같다).",
    "20bp 줄: 라이브러리 모든 다리 편도 20bp · 펀드 되돌림 2 × 20bp.",
    "M2 토막은 LIBMETA 와 같다(2019-10~2022-03 · 2022-04~2024-09 · 2024-10~2026-08 조각).",
]
INTERP_Q15 = [
    "결정은 매월 말 t 2017-09 ~ 2026-07 · 보유 2017-10 ~ 2026-08(107개월) · U4_t 는 t−11..t(≥ 2016-10) 모두 r̃ 가 선 엔진.",
    "RW 는 순수익 r̃ 대 SPY TR · z = 1 은 RW > 0(엄격) · 칸 비중 1/|U4_t| · 꺼진 칸은 SPY · 첫 결정도 100% SPY 에서 진입 거래를 물린다.",
    "정적 켜짐비율 위약: f_i = 표본 안 결정 중 칸 i 가 U4_t 에 있던 달의 z 평균(«실현 켜짐비율» 의 표본 안 판) · 매달 (f_i/N 엔진 · (1 − f_i)/N SPY) 로 되돌림.",
    "K4: 칸마다 z 가 같은 연속 결정을 한 구간으로 · 구간 순서만 섞는다(길이 보존 · 첫 상태는 보존하지 않는다 — AUDIT-2026-08-14-REGIME-K4 §2). "
    "난수는 카드 씨앗으로 한 번 만든 한 줄기 np.random.default_rng(20260814) — AUDIT §2 «시드 20260814 고정» · LIBMETA K4(lib_meta 한 줄기)와 같은 방식 · "
    "1000 뽑기가 차례로 그 줄기를 쓰고, 뽑기 안에서는 칸을 sid 정렬 순으로 돌며 칸마다 permutation(구간 수) 한 번. "
    "통계 = 평균(L4 − 위약)(%/월) · Ψ_M(L4). 켜진 달 수가 보존되므로 위약은 뽑기마다 같다.",
    "증분 1: rrg.rrg_axes(PREREG-2026-09-22-RRG §1 · n 12)를 r̃ 대 SPY TR 상대 NAV(max(2016-10, 첫 달)부터)에 · z1 = RS-Ratio ≥ 100. 결정 t 마다 t 에서 자른 계열로 "
    "다시 셈한다(앞보기 없음이 구성으로) · 전체 계열로 한 번 셈한 t 값과 같음을 매 결정 단언.",
    "증분 2: Z_t = 1(Π_{t−11..t}(1 + RSP)/Π(1 + SPY) − 1 > 0) 이면 C1(U4_t 1/N) · 아니면 100% SPY.",
    "증분 검정: (L4 − SPY) 를 [1, 증분 − SPY] 에 회귀 · 절편 NW(3) t(eg30plus.nw_ols).",
    "F0: 켜짐비율 = 결정마다 칸 평균 z 의 시간 평균 · 일치율 = z_i,t = Z_t 인 칸·달 비율 · FF0(전방 전환 ≤ 6)은 전방에서만 — 표본 안 전환 수는 적기만 한다.",
    "pool 에 있던 «잔차 z» 보고만 쌍둥이는 최종 카드에 없어 만들지 않았다.",
    "M2 토막은 pool 원문(2017-10~2020-03 · 2020-04~2022-09 · 2022-10~2025-03 · 2025-04~2026-08 조각).",
    "U4 sid 동결: 등록 커밋에 U4_SHA(표본 안 판 9e8ebd40 의 58 sid)를 박고 로드 때 단언 · 전방 원장은 같은 sid 를 적는다(카드의 «원장이 생긴 뒤 동결» 은 수정 필요).",
    "전방 시작 = FWD_T0 2026-10 월말 종가(전방 1개월 = 2026-11) · 100% SPY 에서 · 그 종가에 원장이 없으면 원장이 생긴 뒤 첫 월말 종가로 미룬다. "
    "위약 f_i 는 전방에서 전방 실현 켜짐비율로 다시 셈한다(표본 안 판은 표본 안 실현 켜짐비율).",
]


def mshift(ym, k):
    return Q.mshift(ym, k)


def mrange(a, b):
    return Q.months_between(a, b)


def thash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def _clean(o):
    """JSON 에 실을 모양 — numpy 스칼라 · 배열 · 튜플 · NaN 을 정리한다(러너가 D 카드의 lib · log · placebo 를 그대로 싣는다)."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_clean(v) for v in o.tolist()]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if math.isfinite(v) else None
    return o


# ── 자료 ─────────────────────────────────────────────────────────────────
def etf_monthly(A, tk):
    """ETF 월말 총수익(%) — lib_loader.spy_tr_monthly 와 한 글자도 다르지 않은 식(LibData 가 lib_loader 의 8 ETF 로 같음을 단언한다)."""
    me = LL._month_ends(A["dates"], A["px"][tk])
    ms = sorted(me)
    return {ms[i]: (me[ms[i]][1] / me[ms[i - 1]][1] - 1) * 100 for i in range(1, len(ms))}


def sphb_monthly(rev=DATA_REV, A=None):
    """Q14 의 등록 SPHB 적재기 — SPHB 월말 총수익(%) · SPY 월말 날짜(같은 판 assets.json · lib_loader.py 는 LIBMETA 동결이라 고치지 않는다)."""
    A = A if A is not None else LL._read("assets.json", rev)
    dts = {m: d for m, (d, _) in LL._month_ends(A["dates"], A["px"]["SPY"]).items()}
    return etf_monthly(A, "SPHB"), dts


def sid_sha(sids):
    return hashlib.sha256("\n".join(sids).encode("utf-8")).hexdigest()


def u2_member(it):
    return it.get("role") == "수익엔진" and it.get("basis") == "pit" and it.get("holds") in ("종목", "없음") and it.get("cost_kill") is not True


def u4_member(it):
    return it.get("role") == "수익엔진" and it.get("basis") == "pit" and it.get("holds") == "종목"


class LibData:
    """라이브러리 판 — U_LIB 순수익 패널(r̃) · ETF 월 총수익(SPHB 포함) · rf(%) · 구간(mech_episodes)."""

    def __init__(self, rev=DATA_REV, L=None, sphb=None, me_dates=None):
        self.real = L is None
        self.sphb_same_formula = None                  # 합성 판은 잴 것이 없다
        if L is None:
            L = LL.load(end=END, rev=rev)
            if (L["sha"]["sids"], L["sha"]["panel"]) != (LM.SID_SHA, LM.PANEL_SHA):
                raise SystemExit("🚨 유니버스 · 패널 해시가 LIBMETA 등록 때와 다르다(sid %s · panel %s)." % (L["sha"]["sids"][:12], L["sha"]["panel"][:12]))
            A = LL._read("assets.json", rev)
            # SPHB 적재기가 lib_loader 와 같은 식인가 — lib_loader 가 내는 8 ETF 를 같은 함수로 다시 셈해 값이 똑같아야 한다
            self.sphb_same_formula = bool(sorted(L["etf"]) and all(etf_monthly(A, tk) == L["etf"][tk] for tk in sorted(L["etf"])))
            if not self.sphb_same_formula:
                raise SystemExit("🚨 etf_monthly 가 lib_loader.spy_tr_monthly 와 다른 값을 낸다 — SPHB 적재기를 쓸 수 없다.")
            sphb, me_dates = sphb_monthly(rev, A)
        self.L = L
        self.reps = {it["sid"]: it for it in L["reps"]}
        self.panel = L["panel"]
        self.etf = {k: dict(v) for k, v in L["etf"].items()}
        self.etf["SPHB"] = dict(sphb)
        self.spy = self.etf["SPY"]
        self.rf = L["rf"]
        self.me_dates = me_dates or {}
        self.ME = Q.load("mech_episodes.json")
        self.U2 = sorted(s for s, it in self.reps.items() if u2_member(it) and s in self.panel)
        self.U4 = sorted(s for s, it in self.reps.items() if u4_member(it) and s in self.panel)
        assert not (set(self.panel) & (set(self.etf) | {CASH, TBILL})), "엔진 sid 와 다리 이름이 겹친다"
        self.U2_sha, self.U4_sha = sid_sha(self.U2), sid_sha(self.U4)
        if self.real:
            assert len(self.U2) == N_U2 and len(self.U4) == N_U4, (len(self.U2), len(self.U4))
            if (self.U2_sha, self.U4_sha) != (U2_SHA, U4_SHA):            # 등록 커밋에 얼린 sid 목록
                raise SystemExit("🚨 U2/U4 sid 목록이 등록 때와 다르다(U2 %s · U4 %s)." % (self.U2_sha[:12], self.U4_sha[:12]))

    def leg(self, k, m):
        """다리 k 의 달 m 수익(%) — 엔진은 없으면 None(끊김) · ETF 는 반드시 있어야 한다."""
        if k == "SPY":
            return self.spy[m]
        if k in self.panel:
            return self.panel[k].get(m)
        if k in (CASH, TBILL):
            return self.rf[m]
        return self.etf[k][m]

    def fac(self, m):
        s, rf, e = self.spy[m], self.rf[m], self.etf
        return [s - rf, e["RSP"][m] - s, e["IVW"][m] - e["IVE"][m], e["SPLV"][m] - s, e["SPMO"][m] - s]


class LibGrid(Q.Grid):
    """월말만 있는 격자 — fund_from_path · evaluate 를 라이브러리 월 계열에 그대로 쓴다(일간 구간 점수는 비어 나온다)."""

    def __init__(self, months, dates, spy_pct, pr):
        ix = [1.0]
        for m in months[1:]:
            ix.append(ix[-1] * (1 + spy_pct[m] / 100.0))
        super().__init__(dates, ix, pr)
        assert [d[:7] for d in self.dates] == list(months)


def make_grid(ctx, D):
    A = ctx.A
    months = mrange(FORM0, END)
    return LibGrid(months, [A.dates[A.me[m]] for m in months], D.spy, [float(A.IX_PR[A.me[m]]) for m in months])


# ── 모의(라이브러리 틀 · 월) ────────────────────────────────────────────────
def simulate(D, targets, months, cost=COST_PCT, borrow=0.0):
    """targets {결정월 t: {다리: 비중}} → ({달: 순수익 %}, {t: Σ|Δw|}). LIBMETA simulate 관례를 다리(ETF · T-bill · 조달 · 공매도)로 넓혔다:
    결정 달 끝 드리프트 뒤 Σ|Δw|(조달 제외) × 편도 → 다음 달 수익에서 뺀다 · 끊긴 엔진은 그달 SPY · 달말 SPY 로(2 × 편도) · 차입료 = borrow/12 × 음의 비중 합."""
    w, ret, turn, pend = {"SPY": 1.0}, {}, {}, 0.0
    for m in months:
        t = mshift(m, -1)
        if t in targets:
            tgt = targets[t]
            tv = sum(abs(tgt.get(k, 0.0) - w.get(k, 0.0)) for k in sorted(set(w) | set(tgt)) if k != CASH)
            turn[t] = tv
            pend = cost * tv
            w = dict(tgt)
        short = sum(-x for k, x in w.items() if k != CASH and x < 0)
        r, moved, new = 0.0, 0.0, {}
        for k in sorted(w):
            x = w[k]
            rk = D.leg(k, m)
            if rk is None:                               # 계열이 끊겼다 — 그달 SPY · 달말 SPY 로
                rk, k, moved = D.spy[m], "SPY", moved + abs(x)
            r += x * rk
            new[k] = new.get(k, 0.0) + x * (1 + rk / 100)
        tot = sum(new.values())
        w = {k: v / tot for k, v in new.items()}
        ret[m] = r - pend - 2 * cost * moved - borrow / 12.0 * short
        pend = 0.0
    return ret, turn


def ann_turn(turn):
    """편도 연 회전(qbatch 관례: 편입 평균 Σ|Δw| / 2 × 12)."""
    return float(np.mean(list(turn.values())) / 2 * 12) if turn else 0.0


def fund_fr(G, ret, forms, cost=Q.COST, basis="TR", turn=None):
    """라이브러리 월 순수익 → 슬리브 NAV(월말 격자) → qbatch_core.fund_from_path(펀드 90/10 · 매월 되돌림)."""
    path = {G.me[forms[0]]: 1.0}
    for t in forms:
        m = mshift(t, 1)
        path[G.me[m]] = path[G.me[t]] * (1 + ret[m] / 100.0)
    return Q.fund_from_path(G, {"path": path, "turn": turn}, forms, cost=cost, basis=basis)


def x_cm_sm(y, spy, months, ME):
    """LIBMETA §1 X_CM · X_SM · Ψ_M(lib_meta.metrics 와 같은 식 — selftest 대조)."""
    cm, sm = set(ME["months"]["crash_m"]), set(ME["months"]["surge_m"])
    a = np.array([y[m] - spy[m] for m in months])
    c = np.array([m in cm for m in months]); s = np.array([m in sm for m in months])
    xc = float(a[c].mean()) if c.any() else None
    xs = float(a[s].mean()) if s.any() else None
    return xc, xs, (min(xc, xs) if xc is not None and xs is not None else None)


# ── 통계 도구 ─────────────────────────────────────────────────────────────
def ols(Y, F):
    """Y(T × K) 를 [1, F] 에 OLS → 계수(6 × K) · 잔차(T × K)."""
    X = np.column_stack([np.ones(F.shape[0]), F])
    B = np.linalg.lstsq(X, Y, rcond=None)[0]
    return B, Y - X @ B


def nw_cov(y, X, lag=3):
    """OLS 계수 · NW(lag) 공분산 — eg30plus.nw_ols 와 같은 식(그쪽은 t 만 준다 · Wald 에 행렬이 필요하다)."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    g = X * (y - X @ b)[:, None]
    S = g.T @ g
    for L in range(1, lag + 1):
        Gm = g[L:].T @ g[:-L]
        S += (1 - L / (lag + 1)) * (Gm + Gm.T)
    return b, XtXi @ S @ XtXi


def wald5(y, F):
    from scipy.stats import chi2
    b, V = nw_cov(y, np.column_stack([np.ones(len(y)), F]))
    bs, Vs = b[1:], V[1:, 1:]
    W = float(bs @ np.linalg.solve(Vs, bs))
    p = float(chi2.sf(W, len(bs)))
    return {"wald": W, "df": len(bs), "p": p, "pass": bool(p >= P4_ALPHA), "b": dict(zip(FNAMES, map(float, bs)))}


def g1_share(l, SF, s2):
    """오일러 위험기여로 본 EW + LV + MOM 몫."""
    Sl = SF @ l
    tot = float(l @ Sl + s2)
    return float(sum(l[k] * Sl[k] for k in (1, 3, 4)) / tot) if tot > 0 else None


def cond_betas(y, F, mask):
    """P5 — 국면 달끼리 [1, F] OLS 점추정. 새 최소 n 문턱 없이 식별 조건만: [1, F] 의 열 계수 = 모수 수(1 + 5 = 6) · 아니면 측정 불가(None).
    전방에서 None 이면 FF2 의 «P5 전방 통과» 는 충족되지 않은 것(보류)."""
    n = int(mask.sum())
    k = 1 + len(FNAMES)
    X = np.column_stack([np.ones(n), F[mask]]) if n else None
    if n < k or np.linalg.matrix_rank(X) < k:
        return {"n": n, "identified": False, "betas": None, "pass": None}
    b = np.linalg.lstsq(X, y[mask], rcond=None)[0][1:]
    ok = abs(b[0] - 1.0) <= NEUT_TOL and all(abs(x) <= NEUT_TOL for x in b[1:])
    return {"n": n, "identified": True, "betas": dict(zip(FNAMES, map(float, b))), "pass": bool(ok)}


def pct_below(draws, true):
    return float(np.mean(np.array(draws) < true) * 100) if draws and true is not None else None


# ── Q14 구성 ─────────────────────────────────────────────────────────────
def l2_state(D, t):
    """결정 t — 창 · U2_t · 요인 · 엔진/ETF 적재와 잔차. t 월말까지의 달만 쓴다(단언)."""
    W = mrange(mshift(t, -(L2_WIN - 1)), t)
    assert W[0] >= W0 and W[-1] == t and len(W) == L2_WIN and all(m <= t for m in W), (t, W[0])
    U = [s for s in D.U2 if all(m in D.panel[s] for m in W)]
    F = np.array([D.fac(m) for m in W])
    st = {"t": t, "W": W, "U": U, "N": len(U), "F": F}
    if U:
        Y = np.array([[D.panel[s][m] - D.rf[m] for s in U] for m in W])
        B, E = ols(Y, F)
        Yh = np.array([[D.etf[h][m] - D.rf[m] for h in HEDGE_ETF] for m in W])
        Bh, Eh = ols(Yh, F)
        st.update(load=B[1:].T, alpha=B[0], E=E, loadH={h: Bh[1:, j] for j, h in enumerate(HEDGE_ETF)},
                  EH={h: Eh[:, j] for j, h in enumerate(HEDGE_ETF)})
    return st


def h_loadings(st):
    out = {"SPY": np.array([1.0, 0, 0, 0, 0]), TBILL: np.zeros(5)}
    for h in HEDGE_ETF:
        out[h] = np.asarray(st["loadH"][h], float)
    return out


def l2n_target(U, w, LP):
    """L2-N 보유 — 엔진 w + 덮개(RSP · IVW · IVE · SPLV · SPMO · SPY) + 조달."""
    b, e, g, l, mo = [float(x) for x in LP]
    tg = {s: float(x) for s, x in zip(U, w)}
    for k, v in (("RSP", -e), ("IVW", -g), ("IVE", g), ("SPLV", -l), ("SPMO", -mo), ("SPY", (1 - b) + e + l + mo), (CASH, -(1 - b))):
        tg[k] = tg.get(k, 0.0) + v
    return tg


def completion(bP, gP, HL, lam=LAMBDA):
    """보완 c ≥ 0(H 위 · Σc = 1 − λ) — 슬리브 β = 1 · GV = 0 · Σ(SPY 밖 c) 최소. 크기 ≤ 3 부분집합 완전 열거 → GV 버림(≤ 2) → ½ SPY.
    돌려준다: ({다리: c}, level 0/1/2, 부분집합)."""
    names = list(HSET)
    Bv = np.array([float(HL[h][0]) for h in names]); Gv = np.array([float(HL[h][2]) for h in names])
    A_full = np.vstack([np.ones(len(names)), Bv, Gv])
    rhs_full = np.array([1.0 - lam, 1.0 - lam * bP, -lam * gP])
    for level, (rows, kmax) in enumerate(((3, 3), (2, 2))):
        A, rhs = A_full[:rows], rhs_full[:rows]
        best = None
        for k in range(1, kmax + 1):
            for S in itertools.combinations(range(len(names)), k):
                As = A[:, S]
                c = np.linalg.lstsq(As, rhs, rcond=None)[0]
                if np.max(np.abs(As @ c - rhs)) > TOL_EQ or np.min(c) < -TOL_NEG:
                    continue
                c = np.clip(c, 0.0, None)
                obj = float(sum(x for x, j in zip(c, S) if names[j] != "SPY"))
                if best is None or obj < best[0] - TOL_TIE:
                    best = (obj, S, c)
        if best is not None:
            return {names[j]: float(x) for j, x in zip(best[1], best[2]) if x > 0}, level, [names[j] for j in best[1]]
    return {"SPY": 1.0 - lam}, 2, ["SPY"]


def sleeve_loadings(LP, c, HL, lam=LAMBDA):
    return lam * np.asarray(LP, float) + sum(x * HL[h] for h, x in c.items())


def pred_g1(st, LP, c, HL, lam=LAMBDA):
    """예측 G1 — 결정 때 적재 · 창 요인 공분산 · 슬리브 합성 잔차 분산."""
    l = sleeve_loadings(LP, c, HL, lam) - np.array([1.0, 0, 0, 0, 0])
    e = lam * st["E"].mean(axis=1)
    for h, x in c.items():
        if h in HEDGE_ETF:
            e = e + x * st["EH"][h]
    s2 = float(e @ e) / (len(e) - 6)
    SF = np.cov(st["F"].T, ddof=1)
    return g1_share(l, SF, s2)


def erc_resid(E):
    """L2-ERC 비중 — 잔차 상관 군집(k 10) · 군집 안 · 군집 사이 ERC(축소 0.2). 돌려준다: (비중, 기록)."""
    N = E.shape[1]
    C = np.corrcoef(E.T)
    bad = int((~np.isfinite(C)).sum())
    if bad:
        C = np.where(np.isfinite(C), C, 0.0)
        np.fill_diagonal(C, 1.0)
    lab = MC.corr_clusters(C, ERC_K)
    cl = sorted(set(int(x) for x in lab))
    win, series, fb = {}, [], 0
    for c in cl:
        idx = [i for i in range(N) if lab[i] == c]
        if len(idx) == 1:
            wi = np.array([1.0])
        else:
            wi = MC.erc_weights(np.cov(E[:, idx].T, ddof=1), shrink=ERC_SHRINK)
            if wi is None:
                wi, fb = np.full(len(idx), 1.0 / len(idx)), fb + 1
        win[c] = (idx, np.asarray(wi, float))
        series.append(E[:, idx] @ np.asarray(wi, float))
    S = np.column_stack(series)
    wa = MC.erc_weights(np.cov(S.T, ddof=1), shrink=ERC_SHRINK) if len(cl) > 1 else np.array([1.0])
    if wa is None:
        wa, fb = np.full(len(cl), 1.0 / len(cl)), fb + 1
    w = np.zeros(N)
    for j, c in enumerate(cl):
        idx, wi = win[c]
        w[idx] = wa[j] * wi
    w = w / w.sum()
    return w, {"k": len(cl), "fallback": fb, "nonfinite_corr": bad}


def l2_build(D, decs, erc=True):
    """결정마다 목표 — L2N · L2LO · P1 · P1C · L2ERC(구성만 · 수익 없음) · 결정 기록."""
    T = {k: {} for k in ("L2N", "L2LO", "P1", "P1C", "L2ERC")}
    per = {}
    for t in decs:
        st = l2_state(D, t)
        N, U = st["N"], st["U"]
        rec = {"N": N, "U": tuple(U), "W": [st["W"][0], st["W"][-1]]}
        if N < L2_MIN_N:
            for k in T:
                T[k][t] = {"SPY": 1.0}
            rec.update(spy_month=True, LP=None, level=None, subset=None, c=None, gross=1.0, short=0.0, g1=None, erc=None)
            per[t] = rec
            continue
        w = np.full(N, 1.0 / N)
        LP = w @ st["load"]
        T["L2N"][t] = l2n_target(U, w, LP)
        HL = h_loadings(st)
        c, level, subset = completion(LP[0], LP[2], HL)
        lo = {s: LAMBDA / N for s in U}
        for h, x in c.items():
            lo[h] = lo.get(h, 0.0) + x
        T["L2LO"][t] = lo
        T["P1"][t] = {s: 1.0 / N for s in U}
        p1c = {s: LAMBDA / N for s in U}
        p1c["SPY"] = 1.0 - LAMBDA
        T["P1C"][t] = p1c
        einfo = None
        if erc:
            we, einfo = erc_resid(st["E"])
            T["L2ERC"][t] = l2n_target(U, we, we @ st["load"])
        pos = T["L2N"][t]
        sl = sleeve_loadings(LP, c, HL)
        rec.update(spy_month=False, LP=[float(x) for x in LP], level=level, subset=subset, c=c,
                   gross=float(sum(abs(v) for k, v in pos.items() if k != CASH)),
                   short=float(sum(-v for k, v in pos.items() if k != CASH and v < 0)),
                   g1=pred_g1(st, LP, c, HL), sleeve_beta=float(sl[0]), sleeve_gv=float(sl[2]), erc=einfo)
        per[t] = rec
    return T, per


def l2_runs(per, decs):
    """같은 U2_t 가 이어지는 결정 구간."""
    runs, cur = [], []
    for t in decs:
        if cur and per[t]["U"] != per[cur[-1]]["U"]:
            runs.append(cur)
            cur = []
        cur.append(t)
    if cur:
        runs.append(cur)
    return runs


def l2_k4_targets(per, runs, i):
    """K4 뽑기 i — 구간 안에서 덮개 벡터 순서만 섞은 L2-N 목표(씨앗 20260925 + i)."""
    rng = np.random.default_rng(SEED_L2 + i)
    tg, src = {}, {}
    for run in runs:
        order = rng.permutation(len(run))
        for j, t in enumerate(run):
            s = run[int(order[j])]
            src[t] = s
            if per[t]["LP"] is None:
                tg[t] = {"SPY": 1.0}
                continue
            U = list(per[t]["U"])
            tg[t] = l2n_target(U, np.full(len(U), 1.0 / len(U)), per[s]["LP"])
    return tg, src


def _check_book(w, long_only):
    s = sum(w.values())
    assert abs(s - 1.0) < 1e-9, s
    if long_only:
        assert all(x >= -1e-15 for x in w.values()), min(w.values())
        assert CASH not in w
    return s


# ── Q15 구성 ─────────────────────────────────────────────────────────────
def rs_ratio_series(D, s, last=LAST_DEC):
    """증분 1 — 엔진 s 의 r̃ 대 SPY TR 상대 NAV 에 rrg.rrg_axes(n 12). {달: RS-Ratio}(앞 11칸 없음)."""
    ms = [m for m in mrange(W0, last) if m in D.panel[s]]
    if not ms:
        return {}
    assert ms == mrange(ms[0], ms[-1]), "%s 계열에 빈 달" % s
    assert ms[0] >= W0 and ms[-1] <= last, (s, ms[0], ms[-1], last)      # last 월말까지의 달만
    rel = RG.rel_from([D.panel[s][m] for m in ms], [D.spy[m] for m in ms])
    ratio, _ = RG.rrg_axes(rel)
    return {m: ratio[j] for j, m in enumerate(ms) if ratio[j] is not None}


def l4_signals(D, decs):
    """결정마다 U4_t · RW · z · z1(RRG) · Z(RSP/SPY) — t 월말까지의 달만(단언).
    z1 은 t 에서 자른 계열의 RS-Ratio(앞보기 없음이 구성으로) · 전체 계열로 한 번 셈한 t 값과 같음을 매 결정 단언."""
    rsr = {s: rs_ratio_series(D, s) for s in D.U4}
    sig = {}
    for t in decs:
        LB = mrange(mshift(t, -(L4_LOOK - 1)), t)
        assert LB[0] >= W0 and LB[-1] == t and all(m <= t for m in LB), t
        U = [s for s in D.U4 if all(m in D.panel[s] for m in LB)]
        ps = float(np.prod([1 + D.spy[m] / 100 for m in LB]))
        rw = {s: float(np.prod([1 + D.panel[s][m] / 100 for m in LB]) / ps - 1) for s in U}
        rwc = float(np.prod([1 + D.etf["RSP"][m] / 100 for m in LB]) / ps - 1)
        z1 = {}
        for s in U:
            v = rs_ratio_series(D, s, last=t).get(t)
            assert v is not None and abs(v - rsr[s][t]) <= 1e-12 * max(1.0, abs(v)), (s, t)
            z1[s] = int(v >= RG.CUT)
        sig[t] = {"U": U, "rw": rw, "z": {s: int(rw[s] > 0) for s in U}, "z1": z1, "Z": int(rwc > 0), "rwc": rwc}
    return sig


def slot_target(U, z):
    """칸마다 1/N — 켜진 칸은 엔진 · 꺼진 칸은 SPY(재분배 · 현금 없음)."""
    if not U:
        return {"SPY": 1.0}
    N = len(U)
    tg = {s: 1.0 / N for s in U if z[s]}
    off = sum(1 for s in U if not z[s])
    if off:
        tg["SPY"] = off / N
    return tg


def onfrac(sig, decs):
    cnt, on = {}, {}
    for t in decs:
        for s in sig[t]["U"]:
            cnt[s] = cnt.get(s, 0) + 1
            on[s] = on.get(s, 0) + sig[t]["z"][s]
    return {s: on[s] / cnt[s] for s in sorted(cnt)}


def placebo_target(U, f):
    if not U:
        return {"SPY": 1.0}
    N = len(U)
    tg = {s: f[s] / N for s in U if f[s] > 0}
    rest = sum((1 - f[s]) / N for s in U)
    if rest > 0:
        tg["SPY"] = rest
    return tg


def l4_targets(sig, decs, key="z"):
    return {t: slot_target(sig[t]["U"], sig[t][key]) for t in decs}


def l4_slot_runs(sig, decs):
    """칸마다 (결정 달 목록, [(z, 길이) …])."""
    seqs = {}
    for t in decs:
        for s in sig[t]["U"]:
            seqs.setdefault(s, []).append((t, sig[t]["z"][s]))
    out = {}
    for s in sorted(seqs):
        R = []
        for _, z in seqs[s]:
            if R and R[-1][0] == z:
                R[-1][1] += 1
            else:
                R.append([z, 1])
        out[s] = ([t for t, _ in seqs[s]], [tuple(r) for r in R])
    return out


def l4_k4_stream():
    """Q15 K4 의 난수 한 줄기 — 카드 씨앗 20260814 로 한 번(AUDIT-2026-08-14-REGIME-K4 §2 «시드 고정» · LIBMETA K4 와 같은 방식)."""
    return np.random.default_rng(SEED_L4)


def l4_k4_z(runs, rng):
    """K4 뽑기 하나 — 칸마다(sid 정렬 순) 구간 순서만 섞는다(길이 보존). rng = l4_k4_stream() 한 줄기를 뽑기들이 차례로 쓴다."""
    zp = {}
    for s in sorted(runs):
        ts, R = runs[s]
        order = rng.permutation(len(R))
        seq = [R[int(j)][0] for j in order for _ in range(R[int(j)][1])]
        for t, v in zip(ts, seq):
            zp.setdefault(t, {})[s] = v
    return zp


# ── 전방 선행조건 ─────────────────────────────────────────────────────────
def prereq_status(D=None):
    """선행조건 두 단계 — «commit»(등록 커밋 전 · 이 파일이 채우고 로드 때 단언) · «forward»(전방 첫 결정 FWD_T0 전 · 표본 안 굽기는 쓰지 않는다).
    D = 실제 LibData 일 때만 commit 항목이 참이 된다(합성 판은 거짓)."""
    ex = lambda p: os.path.exists(os.path.join(ROOT, p))
    real = D is not None and getattr(D, "real", False)
    return [
        {"name": "SPHB loader", "stage": "commit", "paths": ["build/q_lib.py"], "exists": bool(real and D.sphb_same_formula),
         "needed": "Q14 등록 커밋 전",
         "what": "q_lib.sphb_monthly(etf_monthly) — lib_loader.spy_tr_monthly 와 같은 식 · 같은 판(9e8ebd40) · 로드 때 lib_loader 의 8 ETF 를 같은 함수로 다시 셈해 "
                 "값이 똑같음을 단언. lib_loader.py 는 LIBMETA frozen_check(f2a4c7d0 대조) 때문에 고치지 않는다 — 카드 문구 «lib_loader.spy_tr_monthly 에 SPHB» 를 이것으로 바꾼다"},
        {"name": "frozen U2/U4 sids", "stage": "commit", "paths": ["build/q_lib.py"],
         "exists": bool(real and (D.U2_sha, D.U4_sha) == (U2_SHA, U4_SHA)), "needed": "등록 커밋(BATCH DESIGN §2(h) · §6)",
         "what": "U2_SHA %s… · U4_SHA %s… — 표본 안 판 9e8ebd40 의 54 · 58 sid(정렬 · \\n 이음 sha256)를 이 파일 상수로 얼리고 로드 때 단언. "
                 "전방 원장은 같은 sid 를 적는다(원장에 없는 sid 는 끊긴 계열 → SPY) — 카드의 «원장이 생긴 뒤 동결» 은 이것으로 바꾼다" % (U2_SHA[:8], U4_SHA[:8])},
        {"name": "append-only ledger", "stage": "forward", "paths": ["build/lib_ledger.py", "data/_lib_ledger.json"],
         "exists": bool(ex("build/lib_ledger.py") and ex("data/_lib_ledger.json")),
         "needed": "전방 첫 결정(FWD_T0 %s 월말 종가) 전 · 표본 안 판의 끝(%s) 다음 달(%s)부터 처음 게시된 r 을 담는다 — 전방 W_t 의 %s 이후 달이 여기서 온다"
                   "(%s 이전 달은 표본 안 판 %s). «처음 게시» 를 잡으려면 %s r 이 처음 게시되는 라이브러리 굽기 전에 원장이 돌아야 한다"
                   % (FWD_T0, END, mshift(END, 1), mshift(END, 1), mshift(END, 1), DATA_REV, mshift(END, 1)),
         "what": "sid 마다 처음 게시된 월 r 을 달마다 적는다 · 재작성은 경고만 · 전방 수익은 이것만 읽는다(strategy_charts 재굽기가 아니다)"},
        {"name": "pivot-date NAV export", "stage": "forward", "paths": [], "exists": False,
         "needed": "전방 첫 급락 다리 확정 전(없으면 전방 T1 · T2 는 월 부분만 · 그렇다고 적는다)",
         "what": "U2 · U4 엔진과 ETF 의 지그재그 전환점(급락 다리 · 반등 창) 날짜 NAV — 라이브러리 차트는 월 점뿐이다 · 경로 미등록"},
        {"name": "forward start", "stage": "forward", "paths": [], "exists": False,
         "needed": "FWD_T0 = %s 월말 종가(전방 1개월 = %s) · 그 종가에 원장이 없으면 원장이 생긴 뒤 첫 월말 종가로 미룬다(한 규칙)" % (FWD_T0, mshift(FWD_T0, 1)),
         "what": "100% SPY 에서 시작 · 진입 거래를 물린다 · 코드 해시 동결 · 바꾸면 전방 시계를 다시 켠다"},
        {"name": "forward event counter", "stage": "forward", "paths": ["build/mech_episodes.py"], "exists": bool(ex("build/mech_episodes.py")),
         "needed": "FF2(36개월 이상) 전",
         "what": "등록 뒤 시작 고점의 급락 다리 · 반등 · CRASH-M 을 σ_pre 동결값으로 센다(사건 최소 3 · 3 · 4)"},
    ]


def commit_ready(pre):
    """«commit» 단계 선행조건이 모두 채워졌는가."""
    return all(p["exists"] for p in pre if p["stage"] == "commit")


# ── 계약 함수 ─────────────────────────────────────────────────────────────
def _lib(ctx):
    D = getattr(ctx, "_qlib", None)
    if D is None:
        D = LibData()
        ctx._qlib = D
    return D


def dry(ctx) -> dict:
    """랩 자료로 구성만 — 판 · 해시 · 유니버스 수 · ETF 커버리지 · 창 · 비중 합 · 롱온리 · 보완 등식 · PIT 단언 · 월말 격자.
    수익 · 켜짐비율 · 일치율 · 보완 대체 수 · 총노출 · G1 은 계산하지도 찍지도 않는다(F0 는 run 에서만)."""
    D = _lib(ctx)
    A = ctx.A
    months = mrange(FORM0, END)
    for m in months:                                                   # 월말 자리 = 그달 마지막 거래일
        i = A.me[m]
        assert A.dates[i][:7] == m and (i + 1 >= len(A.dates) or A.dates[i + 1][:7] > m)
    LG = make_grid(ctx, D)
    spy_gap = max(abs((A.IX_TR[A.me[m]] / A.IX_TR[A.me[mshift(m, -1)]] - 1) * 100 - D.spy[m]) for m in months[1:])
    dates_same = all(D.me_dates.get(m) == LG.dates[j] for j, m in enumerate(months)) if D.me_dates else None
    tick = ("SPY", "RSP", "IVW", "IVE", "SPLV", "SPMO", "QQQ", "SPHB", "AGG")
    cov = {tk: all(m in D.etf[tk] for m in mrange(W0, END)) for tk in tick}
    rf_cov = all(m in D.rf for m in mrange(W0, END))
    # Q14
    d2 = mrange(L2_FIRST, LAST_DEC)
    T2, per = l2_build(D, d2)
    Ns = [per[t]["N"] for t in d2]
    dev = {"L2N": 0.0, "L2LO": 0.0, "P1": 0.0, "P1C": 0.0, "L2ERC": 0.0}
    eqres = 0.0
    for t in d2:
        for k in dev:
            dev[k] = max(dev[k], abs(_check_book(T2[k][t], long_only=k in ("L2LO", "P1", "P1C")) - 1.0))
        r = per[t]
        if r["LP"] is not None:
            assert abs(sum(r["c"].values()) - (1 - LAMBDA)) < 1e-9
            if r["level"] <= 1:
                eqres = max(eqres, abs(r["sleeve_beta"] - 1.0))
            if r["level"] == 0:
                eqres = max(eqres, abs(r["sleeve_gv"]))
    runs = l2_runs(per, d2)
    tg0, src0 = l2_k4_targets(per, runs, 0)
    runmap = {t: j for j, run in enumerate(runs) for t in run}
    k4_ok = all(runmap[t] == runmap[src0[t]] for t in d2) and all(
        sorted(tuple(per[src0[t]]["LP"] or ()) for t in run) == sorted(tuple(per[t]["LP"] or ()) for t in run) for run in runs)
    # Q15
    d4 = mrange(L4_FIRST, LAST_DEC)
    sig = l4_signals(D, d4)
    f = onfrac(sig, d4)
    dev4 = 0.0
    for t in d4:
        c1 = {s: 1.0 / len(sig[t]["U"]) for s in sig[t]["U"]}
        for w in (slot_target(sig[t]["U"], sig[t]["z"]), slot_target(sig[t]["U"], sig[t]["z1"]), c1, placebo_target(sig[t]["U"], f)):
            dev4 = max(dev4, abs(_check_book(w, True) - 1.0))
    r4 = l4_slot_runs(sig, d4)
    ok4 = True
    rng4 = l4_k4_stream()
    for _ in range(2):
        zp = l4_k4_z(r4, rng4)
        for s, (ts, R) in r4.items():
            seq = [zp[t][s] for t in ts]
            ok4 &= sum(seq) == sum(z * n for z, n in R) and len(seq) == sum(n for _, n in R)
    N4 = [len(sig[t]["U"]) for t in d4]
    pre = prereq_status(D)
    return {"data_rev": DATA_REV, "sha_match": True, "families": len(D.reps), "U2": len(D.U2), "U4": len(D.U4),
            "U2_sha": D.U2_sha, "U4_sha": D.U4_sha, "U2_U4_sha_eq_frozen": (D.U2_sha, D.U4_sha) == (U2_SHA, U4_SHA),
            "sphb_loader_same_formula_as_lib_loader": D.sphb_same_formula, "deps_sha_bad": deps_check(),
            "commit_ready": commit_ready(pre), "forward_t0": FWD_T0,
            "etf_coverage_2016-10..2026-08": cov, "rf_coverage": rf_cov,
            "spy_tr_lib_vs_P2_assets_max_abs_diff_pct": float(spy_gap), "month_end_dates_same": dates_same,
            "Q14": {"decisions": len(d2), "first": d2[0], "last": d2[-1], "hold": [mshift(d2[0], 1), mshift(d2[-1], 1)],
                    "U2_t": {"min": min(Ns), "median": float(np.median(Ns)), "max": max(Ns)}, "runs_identical_U2": len(runs),
                    "book_sum_max_dev": dev, "long_only_ok": True, "completion_sum_ok": True,
                    "completion_eq_max_resid": float(eqres), "k4_within_runs_ok": bool(k4_ok),
                    "pit_asserts": "ok (W_t = t−35..t · 끝 = t)"},
            "Q15": {"decisions": len(d4), "first": d4[0], "last": d4[-1], "hold": [mshift(d4[0], 1), mshift(d4[-1], 1)],
                    "U4_t": {"min": min(N4), "median": float(np.median(N4)), "max": max(N4)},
                    "book_sum_max_dev": dev4, "long_only_ok": True, "k4_run_lengths_on_counts_ok (2 draws)": bool(ok4),
                    "pit_asserts": "ok (t−11..t · 끝 = t · RRG 는 t 에서 자른 계열 = 전체 계열 값 매 결정 단언)",
                    "k4_stream": "default_rng(%d) 한 줄기" % SEED_L4},
            "prereq": [{"name": p["name"], "stage": p["stage"], "exists": p["exists"]} for p in pre]}


def _lib_payload(D, months, blocks, ser, fund, dmask, LG):
    """라이브러리 틀(대 SPY) · 펀드 틀 지표 — 오염 측정(판정 아님)."""
    M = {k: LM.metrics(v, D.spy, months, D.ME, blocks=blocks) for k, v in ser.items() if k != "SPY"}
    fs = {k: {m: float(x) for m, x in zip(fr["hold"], fr["fund"])} for k, fr in fund.items()}
    ixd = {m: float(x) for m, x in zip(next(iter(fund.values()))["hold"], next(iter(fund.values()))["index"])}
    FM = {k: LM.metrics(v, ixd, months, D.ME, blocks=blocks) for k, v in fs.items()}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        FE = {k: Q.evaluate(LG, fr, dmask) for k, fr in fund.items()}
    lite = {k: {"hold": fr["hold"], "ex": fr["ex"], "fund": fr["fund"], "basket": fr["basket"], "index": fr["index"], "turn": fr.get("turn")}
            for k, fr in fund.items()}
    return {"monthly": {k: {m: round(float(v[m]), 6) for m in months} for k, v in ser.items()},
            "metrics": M, "fund_metrics": FM, "fund_eval": FE, "fund": lite}


def run_q14(ctx, D, LG):
    import eg30plus as E
    decs = mrange(L2_FIRST, LAST_DEC)
    hold = [mshift(t, 1) for t in decs]
    T, per = l2_build(D, decs)
    R = {"L2N": simulate(D, T["L2N"], hold, COST_PCT, BORROW), "L2ERC": simulate(D, T["L2ERC"], hold, COST_PCT, BORROW),
         "L2N_20bp": simulate(D, T["L2N"], hold, COST20_PCT, BORROW),
         "L2LO": simulate(D, T["L2LO"], hold, COST_PCT), "L2LO_20bp": simulate(D, T["L2LO"], hold, COST20_PCT),
         "P1": simulate(D, T["P1"], hold, COST_PCT), "P1C": simulate(D, T["P1C"], hold, COST_PCT)}
    for b in BORROW_ROWS:
        R["L2N_b%03d" % round(b * 100)] = simulate(D, T["L2N"], hold, COST_PCT, b)
    ser = {k: v[0] for k, v in R.items()}
    ser["SPY"] = {m: D.spy[m] for m in hold}
    turn = {k: ann_turn(v[1]) for k, v in R.items()}
    ff = lambda k, cost=Q.COST, basis="TR", src=None: fund_fr(LG, ser[src or k], decs, cost, basis, turn[src or k])
    fr, fr_pr, fr20 = ff("L2LO"), ff("L2LO", basis="PR"), ff("L2LO_20bp", cost=0.0020)
    controls = {"P1": ff("P1"), "P1C": ff("P1C")}
    arms = {"L2N": ff("L2N"), "L2ERC": ff("L2ERC")}
    dmask = ctx.dmask(fr["hold"])
    spy = np.array([D.spy[m] for m in hold])
    rf = np.array([D.rf[m] for m in hold])
    F = np.array([D.fac(m) for m in hold])
    xn = np.array([ser["L2N"][m] for m in hold]) - spy
    # K4 — 같은 U2_t 구간 안 덮개 순서 섞기
    runs = l2_runs(per, decs)
    xc, xs, psi = x_cm_sm(ser["L2N"], D.spy, hold, D.ME)
    d_mean, d_psi = [], []
    for i in range(NPERM):
        tg, _ = l2_k4_targets(per, runs, i)
        r, _ = simulate(D, tg, hold, COST_PCT, BORROW)
        d_mean.append(float(np.mean([r[m] - D.spy[m] for m in hold])))
        d_psi.append(x_cm_sm(r, D.spy, hold, D.ME)[2])
    placebo = {"K4_mean_XN": {"stat": "L2-N 평균 X^N(라이브러리 틀 · 대 SPY TR · 10bp · 차입 1% · %/월) — 같은 U2_t 구간 안 덮개 벡터 순서 섞기",
                              "draws": d_mean, "true": float(xn.mean())},
               "K4_PsiM": {"stat": "L2-N Ψ_M = min(X_CM, X_SM)(%/월) — 같은 섞기", "draws": d_psi, "true": psi}}
    # P4 · P5 · 실현 G1
    p4 = wald5(xn, F)
    ME = D.ME
    cmask = np.array([m in set(ME["months"]["crash_m"]) for m in hold])
    smask = np.array([m in set(ME["months"]["surge_m"]) for m in hold])
    yN = xn + spy - rf
    p5 = {"crash_m": cond_betas(yN, F, cmask), "surge_m": cond_betas(yN, F, smask)}
    p5["pass"] = None if any(v["pass"] is None for v in (p5["crash_m"], p5["surge_m"])) else bool(p5["crash_m"]["pass"] and p5["surge_m"]["pass"])
    act = np.array([ser["L2LO"][m] for m in hold]) - spy
    B, Er = ols(act[:, None], F)
    g1r = g1_share(B[1:, 0], np.cov(F.T, ddof=1), float(Er[:, 0] @ Er[:, 0]) / (len(act) - 6))
    # F0(비중 · 적재만)
    live = [t for t in decs if per[t]["LP"] is not None]
    Ns = [per[t]["N"] for t in decs]
    drop = float(np.mean([per[t]["level"] >= 1 for t in live])) if live else None
    gshare = float(np.mean([per[t]["gross"] > GROSS_CAP for t in live])) if live else None
    g1p = [per[t]["g1"] for t in live if per[t]["g1"] is not None]
    g1m = float(np.mean(g1p)) if g1p else None
    stop_u = min(Ns) < L2_MIN_N
    stop_d = drop is not None and drop > DROP_SHARE
    labels = [x for x, c in (("구현 불가 규모(L2-N)", gshare is not None and gshare > GROSS_SHARE),
                             ("공통요인 베팅 — 측정만(L2-LO)", g1m is not None and g1m > G1_CAP)) if c]
    why = []
    if stop_u:
        why.append("|U2_t| < 30 인 달 %d" % sum(n < L2_MIN_N for n in Ns))
    if stop_d:
        why.append("보완 제약이 빠진 달 %.0f%% > 10%%(λ = ½ 에서 측정 불가 · G4)" % (drop * 100))
    f0 = {"ok": not (stop_u or stop_d), "why": " · ".join(why) if why else "F0 통과 — 라벨 %s" % (labels or "없음")}
    # 기술 · 분해(오염 측정)
    fx = lambda a: np.asarray(a["ex"], float)
    skill = {"XN_mean_pm": float(xn.mean()), "XN_nw_t": E.nw_t(xn),
             "L2N_minus_P1_nw_t": E.nw_t(np.array([ser["L2N"][m] - ser["P1"][m] for m in hold])),
             "L2LO_fund_minus_P1_fund_nw_t": E.nw_t(fx(fr) - fx(controls["P1"])),
             "L2LO_fund_minus_P1C_fund_nw_t": E.nw_t(fx(fr) - fx(controls["P1C"])),
             "IR_L2LO_fund": None, "IR_P1_fund": None, "G1_realized": g1r}
    pay = _lib_payload(D, hold, BLOCKS_L2, ser, {"L2LO": fr, "P1": controls["P1"], "P1C": controls["P1C"], "L2N": arms["L2N"], "L2ERC": arms["L2ERC"]}, dmask, LG)
    skill["IR_L2LO_fund"] = pay["fund_eval"]["L2LO"]["ir"]
    skill["IR_P1_fund"] = pay["fund_eval"]["P1"]["ir"]
    gates = {"note": "표본 안 오염 측정 — 판정 아님(전방 FF2 · 배치 조건만 같은 식으로 적어 둔다)",
             "P4_leak_pass": p4["pass"], "P5_neutral_pass": p5["pass"], "K4_mean_XN_ge95": bool(pct_below(d_mean, float(xn.mean())) >= 95),
             "K4_PsiM_ge95": bool(psi is not None and pct_below([x for x in d_psi if x is not None], psi) >= 95),
             "G1_realized_le_50": None if g1r is None else bool(g1r <= G1_CAP),
             "IR_L2LO_gt_P1_and_t_ge_1": bool(skill["IR_L2LO_fund"] is not None and skill["IR_P1_fund"] is not None
                                              and skill["IR_L2LO_fund"] > skill["IR_P1_fund"]
                                              and (skill["L2LO_fund_minus_P1_fund_nw_t"] or -9) >= 1.0)}
    pre = prereq_status(D)
    lib = {"frame": "LIBMETA F-LIB H2(Holm m 4 · 2.50/2.39/2.24/1.96)", "status": "오염 측정(표본 안) — 판정 아님 · 판정은 전방 FF1 ~ FF4",
           "window": [hold[0], hold[-1]], "data_rev": DATA_REV, "universe": {"name": "U2", "n": len(D.U2),
           "sha256": D.U2_sha, "frozen_sha256": U2_SHA, "sids": D.U2},
           "statistic": "X^N = L2N − SPY(라이브러리 틀 · 순 · 차입 1.00%)", **pay,
           "skill": skill, "k4": {"mean_XN_pct": pct_below(d_mean, float(xn.mean())), "PsiM_pct": pct_below([x for x in d_psi if x is not None], psi),
                                  "n": NPERM, "seed": SEED_L2, "rng": "뽑기 i = default_rng(%d + i)" % SEED_L2, "runs": len(runs)},
           "P4": p4, "P5": p5, "tradeoff_vs_P1": LM.tradeoff(ser["L2N"], ser["P1"], D.spy, hold, D.ME),
           "factor_T6": LM.factor_reg(ser["L2N"], hold, D.etf, D.rf), "gates_insample": gates,
           "f0": {"U2_t_min": min(Ns), "U2_t_lt30_months": sum(n < L2_MIN_N for n in Ns), "completion_dropped_share": drop,
                  "gross_gt150_share": gshare, "pred_G1_mean": g1m, "labels": labels, "stop": not f0["ok"]},
           "forward": {"FF1": "24 전방 개월 누적 X^N ≤ 0 → 기각(L2-LO 도 닫는다)",
                       "FF2": "≥ 36 전방 개월 + 사건 최소(급락 다리 ≥ 3 · 반등 ≥ 3 · CRASH-M ≥ 4): X^N NW(3) t ≥ F-LIB Holm 문턱 · T1~T4 대 SPY · P4 · P5 전방 통과 · K4 ≥ 95 · FF4 없음",
                       "L2LO_deploy": "L2 FF2 통과 + 펀드 틀 T1~T4(상대 MDD ≤ 2%p · 24개월 안 회복) + 실현 G1 ≤ 50% + IR(L2-LO 펀드) > IR(P1 펀드) · 차 NW t ≥ 1.0",
                       "FK": "24 전방 개월 누적 XF ≤ 0 이고 ≤ P1 펀드 → 기각", "FF3": "60개월에 한 번 더 · 사건 최소 미달이면 기각",
                       "power": "t 2.50 은 36개월 IR ≈ 1.44 · 60개월 ≈ 1.12 — 현실적 결과는 2031 무렵까지 보류",
                       "P5_rule": "P5 는 국면 달의 [1, F] 열 계수 = 6 일 때만 식별 · 식별되지 않으면 FF2 의 P5 조건은 충족되지 않은 것 → 보류",
                       "start": FWD_START, "prereq": pre, "commit_ready": commit_ready(pre)}}
    log = {"interpretation": INTERP_Q14, "nperm": NPERM, "seed": SEED_L2, "turn_oneway_annual": turn,
           "per_decision": {t: {k: v for k, v in per[t].items() if k != "U"} for t in decs},
           "completion_levels": {str(lv): sum(1 for t in live if per[t]["level"] == lv) for lv in (0, 1, 2)},
           "spy_months": [mshift(t, 1) for t in decs if per[t]["LP"] is None]}
    return {"code": "Q14", "cls": "D", "slot": CARDS["Q14"]["slot"], "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
            "controls": controls, "arms": arms, "placebo": placebo, "perm": None, "g4": {},
            "label_caps": {"common_factor_bet_G1": bool("공통요인 베팅 — 측정만(L2-LO)" in labels)},
            "f0": f0, "targets_hash": thash({"L2N": T["L2N"], "L2LO": T["L2LO"]}), "log": log, "lib": _clean(lib)}


def run_q15(ctx, D, LG):
    import eg30plus as E
    decs = mrange(L4_FIRST, LAST_DEC)
    hold = [mshift(t, 1) for t in decs]
    sig = l4_signals(D, decs)
    f = onfrac(sig, decs)
    T = {"L4": l4_targets(sig, decs, "z"), "INC1": l4_targets(sig, decs, "z1"),
         "C1": {t: ({s: 1.0 / len(sig[t]["U"]) for s in sig[t]["U"]} if sig[t]["U"] else {"SPY": 1.0}) for t in decs},
         "PLACEBO": {t: placebo_target(sig[t]["U"], f) for t in decs}}
    T["INC2"] = {t: (dict(T["C1"][t]) if sig[t]["Z"] else {"SPY": 1.0}) for t in decs}
    R = {k: simulate(D, T[k], hold, COST_PCT) for k in ("L4", "PLACEBO", "C1", "INC1", "INC2")}
    R["L4_20bp"] = simulate(D, T["L4"], hold, COST20_PCT)
    ser = {k: v[0] for k, v in R.items()}
    ser["SPY"] = {m: D.spy[m] for m in hold}
    turn = {k: ann_turn(v[1]) for k, v in R.items()}
    ff = lambda k, cost=Q.COST, basis="TR": fund_fr(LG, ser[k], decs, cost, basis, turn[k])
    fr, fr_pr, fr20 = ff("L4"), ff("L4", basis="PR"), ff("L4_20bp", cost=0.0020)
    controls = {k: ff(k) for k in ("PLACEBO", "C1", "INC1", "INC2")}
    dmask = ctx.dmask(fr["hold"])
    spy = np.array([D.spy[m] for m in hold])
    y = np.array([ser["L4"][m] for m in hold]) - spy
    dpl = np.array([ser["L4"][m] - ser["PLACEBO"][m] for m in hold])
    # K4 — 칸별 구간 순서 섞기
    runs = l4_slot_runs(sig, decs)
    xc, xs, psi = x_cm_sm(ser["L4"], D.spy, hold, D.ME)
    d_mean, d_psi = [], []
    rng = l4_k4_stream()
    for _ in range(NPERM):
        zp = l4_k4_z(runs, rng)
        tg = {t: slot_target(sig[t]["U"], zp.get(t, {})) for t in decs}
        r, _ = simulate(D, tg, hold, COST_PCT)
        d_mean.append(float(np.mean([r[m] - ser["PLACEBO"][m] for m in hold])))
        d_psi.append(x_cm_sm(r, D.spy, hold, D.ME)[2])
    placebo = {"K4_mean_vs_placebo": {"stat": "평균(L4 − 정적 켜짐비율 위약)(라이브러리 틀 · 10bp · %/월) — 칸별 켜짐/꺼짐 구간 순서 섞기(길이 보존)",
                                      "draws": d_mean, "true": float(dpl.mean())},
               "K4_PsiM": {"stat": "L4 Ψ_M = min(X_CM, X_SM)(대 SPY TR · %/월) — 같은 섞기", "draws": d_psi, "true": psi}}
    inc = {}
    for k in ("INC1", "INC2"):
        x = np.array([ser[k][m] for m in hold]) - spy
        b, t = E.nw_ols(y, np.column_stack([np.ones(len(y)), x]))
        inc[k] = {"alpha_pm": float(b[0]), "alpha_t": float(t[0]), "slope": float(b[1]), "slope_t": float(t[1])}
    # F0(신호 · 비중만)
    N4 = [len(sig[t]["U"]) for t in decs]
    onf = float(np.mean([np.mean([sig[t]["z"][s] for s in sig[t]["U"]]) for t in decs if sig[t]["U"]]))
    agree = float(np.mean([sig[t]["z"][s] == sig[t]["Z"] for t in decs for s in sig[t]["U"]]))
    switches = int(sum(max(0, len(R_) - 1) for _, R_ in runs.values()))
    stop = float(np.median(N4)) < U4_MIN_MED
    labels = [x for x, c in (("≈SPY", onf < ONF_LO), ("≈C1", onf > ONF_HI), ("공통요인 스위치 재포장", agree > AGREE_CAP)) if c]
    f0 = {"ok": not stop, "why": ("|U4_t| 중앙 %.0f < 30" % float(np.median(N4))) if stop else "F0 통과 — 라벨 %s" % (labels or "없음")}
    skill = {"L4_minus_placebo_mean_pm": float(dpl.mean()), "L4_minus_placebo_nw_t": E.nw_t(dpl),
             "L4_minus_C1_nw_t": E.nw_t(np.array([ser["L4"][m] - ser["C1"][m] for m in hold])),
             "L4_minus_SPY_nw_t": E.nw_t(y),
             "fund_L4_minus_placebo_fund_nw_t": E.nw_t(np.asarray(fr["ex"]) - np.asarray(controls["PLACEBO"]["ex"]))}
    pay = _lib_payload(D, hold, BLOCKS_L4, ser, {"L4": fr, **controls}, dmask, LG)
    gates = {"note": "표본 안 오염 측정 — 판정 아님(전방 FF2 · FF3 조건만 같은 식으로 적어 둔다)",
             "INC1_alpha_t_ge_1": bool(inc["INC1"]["alpha_t"] >= 1.0), "INC2_alpha_t_ge_1": bool(inc["INC2"]["alpha_t"] >= 1.0),
             "FF3_INC2_alpha_t_lt_0": bool(inc["INC2"]["alpha_t"] < 0), "K4_mean_ge95": bool(pct_below(d_mean, float(dpl.mean())) >= 95),
             "K4_PsiM_ge95": bool(psi is not None and pct_below([x for x in d_psi if x is not None], psi) >= 95)}
    pre = prereq_status(D)
    lib = {"frame": "LIBMETA F-LIB H3(Holm m 4 · 2.50/2.39/2.24/1.96)", "status": "오염 측정(표본 안) — 판정 아님 · 판정은 전방 FF1 ~ FF4",
           "window": [hold[0], hold[-1]], "data_rev": DATA_REV, "universe": {"name": "U4", "n": len(D.U4),
           "sha256": D.U4_sha, "frozen_sha256": U4_SHA, "sids": D.U4},
           "statistic": "L4 − 정적 켜짐비율 위약(라이브러리 틀 · 순)", **pay, "skill": skill,
           "k4": {"mean_vs_placebo_pct": pct_below(d_mean, float(dpl.mean())), "PsiM_pct": pct_below([x for x in d_psi if x is not None], psi),
                  "n": NPERM, "seed": SEED_L4, "rng": "한 줄기 default_rng(%d) · 뽑기 안 칸은 sid 정렬 순" % SEED_L4},
           "increments": inc, "tradeoff_vs_C1": LM.tradeoff(ser["L4"], ser["C1"], D.spy, hold, D.ME),
           "factor_T6": LM.factor_reg(ser["L4"], hold, D.etf, D.rf), "gates_insample": gates,
           "onfrac_by_slot": f,
           "f0": {"U4_t_median": float(np.median(N4)), "onfrac_mean": onf, "agree_Z": agree, "insample_slot_switches": switches,
                  "labels": labels, "stop": stop, "FF0": "전방 전환 ≤ 6 → 측정 불가(창을 늘린다) — 전방에서만"},
           "forward": {"FF1": "24 전방 개월 누적(L4 − 켜짐비율 위약) ≤ 0 → 기각 · 위약 f_i 는 전방 실현 켜짐비율",
                       "FF2": "≥ 36 전방 개월 + 사건 최소: (L4 − 위약) NW(3) t ≥ F-LIB Holm 문턱 · (L4 − SPY) 를 (증분 − SPY) 에 회귀한 절편 NW t ≥ 1.0(증분 1 · 2 모두) · 틀 라벨 ≥ «양면(노출)»",
                       "FF3": "36개월에 증분 2 절편 t < 0 → «공통요인(동일가중 − 시총가중) 타이밍» 기각 · 60개월에 한 번 더",
                       "FF4": "틀의 한 달 · 한 다리 뒤집힘 규칙", "power": "Q14 와 같다(t 2.50 은 36개월 IR ≈ 1.44)",
                       "start": FWD_START, "prereq": pre, "commit_ready": commit_ready(pre)}}
    log = {"interpretation": INTERP_Q15, "nperm": NPERM, "seed": SEED_L4, "turn_oneway_annual": turn,
           "per_decision": {t: {"N": len(sig[t]["U"]), "on": int(sum(sig[t]["z"].values())), "on_rrg": int(sum(sig[t]["z1"].values())),
                                "Z": sig[t]["Z"], "rw_rsp_spy": sig[t]["rwc"]} for t in decs}}
    return {"code": "Q15", "cls": "D", "slot": CARDS["Q15"]["slot"], "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
            "controls": controls, "arms": {}, "placebo": placebo, "perm": None, "g4": {},
            "label_caps": {"common_switch_repack": bool("공통요인 스위치 재포장" in labels)},
            "f0": f0, "targets_hash": thash(T["L4"]), "log": log, "lib": _clean(lib)}


def run(ctx) -> dict:
    D = _lib(ctx)
    LG = make_grid(ctx, D)
    out = {"Q14": run_q14(ctx, D, LG), "Q15": run_q15(ctx, D, LG)}
    for r in out.values():                                   # 러너가 싣는 몫은 JSON 으로 깨끗해야 한다
        for k in ("placebo", "log", "f0", "g4", "label_caps"):
            r[k] = _clean(r[k])
    return out


# ── 단위 시험(합성 자료만) ─────────────────────────────────────────────────
def _fake(n_eng=34, seed=11, noise=0.0, drop=None):
    """합성 라이브러리 — 엔진 = rf + a + 적재 · 요인(잡음 선택) · ETF 는 요인에서 정확히 만든다. 돌려준다: (LibData, 참 적재, 참 알파, 달)."""
    rng = np.random.default_rng(seed)
    months = mrange("2015-01", END)
    rf = {m: 0.1 + 0.05 * math.sin(j / 7.0) for j, m in enumerate(months)}
    Fm = {m: rng.normal([0.8, 0.0, 0.0, 0.0, 0.0], [4.0, 1.5, 1.8, 1.2, 1.5]) for m in months}
    spy = {m: rf[m] + Fm[m][0] for m in months}
    etf = {"SPY": spy, "RSP": {m: spy[m] + Fm[m][1] for m in months},
           "IVW": {m: spy[m] + 0.5 * Fm[m][2] for m in months}, "IVE": {m: spy[m] - 0.5 * Fm[m][2] for m in months},
           "SPLV": {m: spy[m] + Fm[m][3] for m in months}, "SPMO": {m: spy[m] + Fm[m][4] for m in months},
           "QQQ": {m: rf[m] + 1.1 * Fm[m][0] - 0.1 * Fm[m][1] + 0.8 * Fm[m][2] for m in months},
           "AGG": {m: rf[m] + float(rng.normal(0, 1)) for m in months}}
    sphb = {m: rf[m] + 1.5 * Fm[m][0] + 0.2 * Fm[m][1] - 0.3 * Fm[m][2] for m in months}
    load, alpha, reps, panel = {}, {}, [], {}
    for j in range(n_eng):
        s = "t-syn%02d" % j
        L = np.array([rng.uniform(0.6, 1.0), rng.uniform(0.0, 0.8), rng.uniform(-0.4, 0.2), rng.uniform(-0.2, 0.3), rng.uniform(-0.2, 0.2)])
        a = float(rng.normal(0.0, 0.3))
        load[s], alpha[s] = L, a
        start = "2016-09" if j % 5 else "2016-10"
        panel[s] = {m: rf[m] + a + float(L @ Fm[m]) + (float(rng.normal(0, noise)) if noise else 0.0) for m in months if m >= start}
        reps.append({"sid": s, "role": "수익엔진", "basis": "pit", "holds": "종목", "cost_kill": False})
    reps.append({"sid": "t-syn-kill", "role": "수익엔진", "basis": "pit", "holds": "종목", "cost_kill": True})
    panel["t-syn-kill"] = {m: spy[m] for m in months if m >= "2016-09"}
    reps.append({"sid": "t-syn-ovl", "role": "타이밍오버레이", "basis": "pit", "holds": "노출", "cost_kill": False})
    panel["t-syn-ovl"] = {m: spy[m] for m in months if m >= "2016-09"}
    if drop:
        for s, m in drop:
            panel[s].pop(m, None)
    L_ = {"reps": reps, "panel": panel, "etf": etf, "rf": rf, "sha": {"sids": "", "panel": ""}}
    D = LibData(L=L_, sphb=sphb, me_dates={})
    return D, load, alpha, months, Fm


def _fake_ctx(D, months):
    """합성 ctx — 월말 하나짜리 날짜 격자(qbatch_core.Assets 메서드 그대로)."""
    A = object.__new__(Q.Assets)
    A.dates = ["%s-28" % m for m in months]
    A.di = {d: i for i, d in enumerate(A.dates)}
    A.me = {m: i for i, m in enumerate(months)}
    A.RF = {m: D.rf[m] / 100 for m in months}
    ix = [100.0]
    for m in months[1:]:
        ix.append(ix[-1] * (1 + D.spy[m] / 100))
    A.IX_TR = np.array(ix)
    A.IX_PR = np.array(ix) * np.linspace(1.0, 0.8, len(ix))
    A.px, A.macro = {"SPY": A.IX_TR}, {}
    ctx = Q.Ctx()
    ctx._A, ctx._qlib = A, D
    return ctx


def selftest() -> dict:
    import eg30plus as E
    from scipy.optimize import linprog
    tests = {}
    D, load, alpha, months, Fm = _fake()
    tests["universe_filters"] = D.U2 == sorted(s for s in load) and "t-syn-kill" in D.U4 and "t-syn-kill" not in D.U2 and "t-syn-ovl" not in D.U4
    # 1단계 적재 — 잡음 없는 합성에서 정확히 되찾는다
    st = l2_state(D, "2019-09")
    tests["window_36_ends_t"] = st["W"][0] == "2016-10" and st["W"][-1] == "2019-09" and len(st["W"]) == 36
    tests["ols_recovers_loadings"] = all(np.allclose(st["load"][j], load[s], atol=1e-9) for j, s in enumerate(st["U"]))
    tests["ols_recovers_hedge_loadings"] = (np.allclose(st["loadH"]["IVW"], [1, 0, 0.5, 0, 0], atol=1e-9)
                                            and np.allclose(st["loadH"]["SPHB"], [1.5, 0.2, -0.3, 0, 0], atol=1e-9))
    # 덮개 항등식 — 비용 · 차입 0 이면 X^N = 엔진 알파 평균(β 1 · 스타일 0)
    decs = mrange("2019-09", "2020-08")
    hold = [mshift(t, 1) for t in decs]
    T, per = l2_build(D, decs, erc=False)
    r, _ = simulate(D, T["L2N"], hold, cost=0.0, borrow=0.0)
    ap = float(np.mean([alpha[s] for s in per[decs[0]]["U"]]))
    tests["overlay_identity_XN_eq_alpha"] = all(abs(r[m] - D.spy[m] - ap) < 1e-9 for m in hold)
    tests["overlay_book_sums_to_1"] = all(abs(sum(T["L2N"][t].values()) - 1) < 1e-12 for t in decs)
    # 보완 — β · GV 등식 · SPY 밖 최소가 선형계획 최적과 같다(무작위 200판) · 불가능 판정도 같다
    HL = h_loadings(st)
    c, lv, S = completion(per[decs[0]]["LP"][0], per[decs[0]]["LP"][2], HL)
    sl = sleeve_loadings(per[decs[0]]["LP"], c, HL)
    tests["completion_constraints"] = lv == 0 and abs(sl[0] - 1) < 1e-9 and abs(sl[2]) < 1e-9 and abs(sum(c.values()) - 0.5) < 1e-12
    rng = np.random.default_rng(3)
    agree = True
    for k in range(200):
        HLr = {"SPY": np.array([1.0, 0, 0, 0, 0]), TBILL: np.zeros(5)}
        for h in HEDGE_ETF:
            HLr[h] = np.array([rng.uniform(0.5, 1.8), 0, rng.uniform(-0.8, 0.9), 0, 0])
        bP, gP = rng.uniform(0.2, 1.3), rng.uniform(-0.8, 0.6)
        cc, lvl, _ = completion(bP, gP, HLr)
        Aeq = np.vstack([np.ones(6), [HLr[h][0] for h in HSET], [HLr[h][2] for h in HSET]])
        beq = np.array([0.5, 1 - 0.5 * bP, -0.5 * gP])
        cost = np.array([0.0 if h == "SPY" else 1.0 for h in HSET])
        lp = linprog(cost, A_eq=Aeq, b_eq=beq, bounds=[(0, None)] * 6, method="highs")
        if lp.status == 0:
            agree &= lvl == 0 and abs(sum(v for h, v in cc.items() if h != "SPY") - lp.fun) < 1e-8
        else:
            lp2 = linprog(cost, A_eq=Aeq[:2], b_eq=beq[:2], bounds=[(0, None)] * 6, method="highs")
            agree &= (lvl == 1 and abs(sum(v for h, v in cc.items() if h != "SPY") - lp2.fun) < 1e-8) if lp2.status == 0 else lvl == 2
    tests["completion_eq_lp_optimum_200"] = bool(agree)
    HLt = {"SPY": np.array([1.0, 0, 0, 0, 0]), TBILL: np.zeros(5), "IVW": np.array([1.0, 0, 0.5, 0, 0]), "IVE": np.array([1.0, 0, -0.5, 0, 0]),
           "QQQ": np.array([1.0, 0, 0.5, 0, 0]), "SPHB": np.array([1.5, 0, 0.3, 0, 0])}
    ct, lt, St = completion(1.0, -0.2, HLt)                       # IVW 와 QQQ 가 똑같다 — 최적 SPY 0.3 + (IVW | QQQ) 0.2 · H 순서 앞 IVW
    tests["completion_tie_earlier_in_H"] = (lt == 0 and St == ["SPY", "IVW"] and abs(ct["IVW"] - 0.2) < 1e-12 and abs(ct["SPY"] - 0.3) < 1e-12)
    HLg = dict(HLt, IVW=np.array([1.2, 0, -0.1, 0, 0]), QQQ=np.array([1.3, 0, -0.2, 0, 0]), SPHB=np.array([1.5, 0, -0.3, 0, 0]))
    tests["completion_drop_gv"] = completion(0.8, -0.5, HLg)[1] == 1
    tests["completion_spy_fallback"] = completion(0.0, 0.0, HLt) == ({"SPY": 0.5}, 2, ["SPY"])
    # 모의 — LIBMETA simulate 와 같다(엔진 + SPY) · 끊긴 계열 · 조달 · 차입료
    D2, *_ = _fake(drop=[("t-syn03", "2020-02")])
    tg = {t: {"t-syn03": 0.3, "t-syn04": 0.2, "SPY": 0.5} for t in decs}
    a1, t1 = simulate(D2, tg, hold, cost=COST_PCT)
    a2, t2 = LM.simulate(D2, tg, hold)
    tests["simulate_eq_libmeta"] = all(abs(a1[m] - a2[m]) < 1e-10 for m in hold) and all(abs(t1[t] - t2[t]) < 1e-12 for t in t1)
    m0 = "2019-10"
    b1, _ = simulate(D, {"2019-09": {"SPY": 1.5, "RSP": -0.5}}, [m0], cost=0.0, borrow=1.0)
    b2, _ = simulate(D, {"2019-09": {"SPY": 2.0, CASH: -1.0}}, [m0], cost=COST_PCT, borrow=1.0)
    tests["borrow_charge"] = abs(b1[m0] - (1.5 * D.spy[m0] - 0.5 * D.etf["RSP"][m0] - 1.0 / 12 * 0.5)) < 1e-12
    tests["cash_no_cost_no_borrow"] = abs(b2[m0] - (2 * D.spy[m0] - D.rf[m0] - COST_PCT * 1.0)) < 1e-12
    # K4(Q14) — 구간 안에서만 · 같은 덮개 집합 · 씨앗 재현
    per_k = {t: {"U": ("a",) if j < 5 else ("a", "b"), "LP": [float(j), 0, 0, 0, 0]} for j, t in enumerate(decs)}
    runs = l2_runs(per_k, decs)
    rm = {t: j for j, run in enumerate(runs) for t in run}
    ta, sa = l2_k4_targets(per_k, runs, 0)
    tb, sb = l2_k4_targets(per_k, runs, 0)
    tc, sc = l2_k4_targets(per_k, runs, 1)
    tests["k4_q14_within_runs"] = len(runs) == 2 and all(rm[t] == rm[sa[t]] for t in decs) and sorted(sa.values()) == sorted(decs)
    tests["k4_q14_reproducible"] = sa == sb and sa != sc
    # 예측 G1 — 스타일 노출이 없으면 0 · 있으면 (0, 1]
    HL0 = h_loadings(st)
    st_noise = dict(st, E=np.random.default_rng(1).normal(0, 1, st["E"].shape))
    tests["g1_zero_without_style"] = abs(pred_g1(st_noise, np.array([1.0, 0, 0, 0, 0]), {"SPY": 0.5}, HL0)) < 1e-12
    g1v = pred_g1(st, per[decs[0]]["LP"], per[decs[0]]["c"], HL0)
    tests["g1_one_without_residual"] = g1v is not None and abs(g1v - 1.0) < 1e-9          # β · GV 가 0 이고 잔차가 없으면 능동 분산은 전부 EW+LV+MOM
    Dn, *_ = _fake(noise=0.5, seed=13)
    _, pn = l2_build(Dn, ["2019-09"], erc=False)
    g1n = pn["2019-09"]["g1"]
    tests["g1_in_0_1_with_residual"] = g1n is not None and 0 < g1n < 1 and pn["2019-09"]["level"] == 0
    # NW 공분산 — eg30plus.nw_ols 의 t 와 같다 · Wald 는 영가설 자료에서 크지 않다
    yv = np.random.default_rng(5).normal(0, 1, 120)
    Xv = np.column_stack([np.ones(120), np.random.default_rng(6).normal(0, 1, (120, 5))])
    bb, VV = nw_cov(yv, Xv)
    b0, t0 = E.nw_ols(yv, Xv)
    tests["nw_cov_matches_eg30plus"] = np.allclose(bb / np.sqrt(np.diag(VV)), t0, atol=1e-10) and np.allclose(bb, b0)
    tests["wald_shape"] = (lambda w: w["df"] == 5 and 0 <= w["p"] <= 1)(wald5(yv, Xv[:, 1:]))
    # 조건부 베타(P5) — 새 n 문턱 없이 식별 조건만: n < 6 이나 계수 부족이면 None · n = 6 이면 정확히 풀린다
    Fv = Xv[:, 1:]
    tests["cond_betas_unidentified_n5"] = cond_betas(yv, Fv, np.arange(120) < 5)["identified"] is False
    tests["cond_betas_none_n0"] = cond_betas(yv, Fv, np.zeros(120, bool))["betas"] is None
    Fd = Fv.copy(); Fd[:, 2] = Fd[:, 1]                                  # 두 요인이 같다 — 계수 5
    tests["cond_betas_rank_deficient"] = cond_betas(yv, Fd, np.arange(120) < 20)["identified"] is False
    y6 = 0.2 + Fv @ np.array([1.0, 0, 0, 0, 0])
    c6 = cond_betas(y6, Fv, np.arange(120) < 6)
    tests["cond_betas_exact_n6"] = (c6["identified"] and c6["pass"] is True and abs(c6["betas"]["MKT"] - 1) < 1e-9
                                    and all(abs(c6["betas"][k]) < 1e-9 for k in FNAMES[1:]))
    # 의존 코드 고정 · 선행조건 두 단계 · ETF 월말 식
    tests["deps_pinned"] = deps_check() == []
    pre_f = prereq_status(D)
    fakeD = type("R", (), {"real": True, "sphb_same_formula": True, "U2_sha": U2_SHA, "U4_sha": U4_SHA})()
    pre_r = prereq_status(fakeD)
    tests["prereq_stages"] = ({p["stage"] for p in pre_f} == {"commit", "forward"} and len({p["name"] for p in pre_f}) == len(pre_f)
                              and not commit_ready(pre_f) and commit_ready(pre_r)
                              and all(p["exists"] for p in pre_r if p["stage"] == "commit")
                              and FWD_T0 in next(p["needed"] for p in pre_f if p["name"] == "forward start"))
    Ax = {"dates": ["2020-01-30", "2020-01-31", "2020-02-27", "2020-02-28", "2020-03-31"], "px": {"X": [1.0, 2.0, 2.2, None, 2.42]}}
    ex_ = etf_monthly(Ax, "X")
    tests["etf_monthly_month_end_formula"] = sorted(ex_) == ["2020-02", "2020-03"] and abs(ex_["2020-02"] - 10) < 1e-9 and abs(ex_["2020-03"] - 10) < 1e-9
    # L2-ERC — 합 1 · 음수 없음 · 두 덩이 합성에서 덩이마다 위험 몫이 비슷
    Ee = np.random.default_rng(8).normal(0, 1, (36, 12))
    Ee[:, :6] += np.random.default_rng(9).normal(0, 2, (36, 1))
    we, ei = erc_resid(Ee)
    tests["erc_weights_valid"] = abs(we.sum() - 1) < 1e-12 and we.min() >= 0 and ei["k"] == 10
    # Ψ_M — lib_meta.metrics 와 같은 식
    yy = {m: D.spy[m] + 0.3 * math.sin(j) for j, m in enumerate(mrange("2017-10", END))}
    mm = mrange("2017-10", END)
    tests["psi_matches_libmeta"] = abs(x_cm_sm(yy, D.spy, mm, D.ME)[2] - LM.metrics(yy, D.spy, mm, D.ME)["Psi_M"]) < 1e-12
    # Q15 신호 — 늘 이기는 엔진 켜짐 · 늘 지는 엔진 꺼짐 · RRG 는 잘라서 다시 셈과 같다(앞보기 없음)
    D3, *_ = _fake(n_eng=34, seed=12)
    for m in months:
        if m >= "2016-09":
            D3.panel["t-syn00"][m] = D3.spy[m] + 0.5
            D3.panel["t-syn01"][m] = D3.spy[m] - 0.5
    d4 = mrange(L4_FIRST, "2019-06")
    sg = l4_signals(D3, d4)
    tests["l4_sign_rule"] = all(sg[t]["z"]["t-syn00"] == 1 and sg[t]["z"]["t-syn01"] == 0 for t in d4)
    full = rs_ratio_series(D3, "t-syn05")
    cut = rs_ratio_series(D3, "t-syn05", last="2018-03")
    tests["rrg_no_lookahead"] = abs(full["2018-03"] - cut["2018-03"]) < 1e-12 and "2017-08" not in full and "2017-09" in full
    rel = RG.rel_from([D3.panel["t-syn05"][m] for m in mrange(W0, "2018-03")], [D3.spy[m] for m in mrange(W0, "2018-03")])
    w12 = np.array(rel[-12:])
    tests["rrg_formula"] = abs(full["2018-03"] - (100 + (w12[-1] - w12.mean()) / w12.std(ddof=1))) < 1e-9
    tb4 = slot_target(sg[d4[0]]["U"], sg[d4[0]]["z"])
    tests["l4_slots_sum_1_no_cash"] = abs(sum(tb4.values()) - 1) < 1e-12 and all(v > 0 for v in tb4.values())
    f4 = onfrac(sg, d4)
    tests["placebo_onfrac"] = f4["t-syn00"] == 1.0 and f4["t-syn01"] == 0.0 and abs(sum(placebo_target(sg[d4[0]]["U"], f4).values()) - 1) < 1e-12
    r4 = l4_slot_runs(sg, d4)
    ok = True
    g1s = l4_k4_stream()
    draws4 = [l4_k4_z(r4, g1s) for _ in range(5)]                         # 한 줄기를 뽑기들이 차례로 쓴다
    for zp in draws4:
        for s, (ts, R) in r4.items():
            seq = [zp[t][s] for t in ts]
            ok &= sum(seq) == sum(z * n for z, n in R) and len(seq) == len(ts)      # 켜진 달 수 · 길이 보존
            # 구간 길이 보존 — 섞은 순서대로 이으면 원래 구간들이 그대로 나온다(이웃한 같은 상태는 합쳐 보일 뿐)
            ok &= sorted(n for _, n in _runs_of(seq)) == sorted(n for _, n in R) or len(_runs_of(seq)) < len(R)
    g2s = l4_k4_stream()
    tests["k4_q15_preserves_on_counts"] = bool(ok)
    tests["k4_q15_single_stream_reproducible"] = draws4 == [l4_k4_z(r4, g2s) for _ in range(5)] and draws4[0] != draws4[1]
    # 증분 1 — 매 결정 t 에서 자른 계열 값(z1)이 전체 계열 값과 같다(l4_signals 안 단언이 통과했다) · RS-Ratio ≥ 100
    tests["rrg_z1_from_truncated"] = all(sg[t]["z1"][s] == int(rs_ratio_series(D3, s, last=t)[t] >= RG.CUT) for t in d4[::6] for s in sg[t]["U"])
    # 펀드 틀 — 슬리브 = SPY 이면 초과 0 · 손으로 푼 한 달
    ctx = _fake_ctx(D, mrange(FORM0, END))
    LG = make_grid(ctx, D)
    fz = fund_fr(LG, {m: D.spy[m] for m in hold}, decs)
    tests["fund_frame_spy_zero_ex"] = float(np.max(np.abs(fz["ex"]))) < 1e-10 and fz["hold"] == hold
    fo = fund_fr(LG, {m: D.spy[m] + 1.0 for m in hold}, decs)
    s0 = D.spy[hold[0]] / 100
    v = 0.9 * (1 + s0) + 0.1 * (1 + s0 + 0.01)
    dev = 0.1 * (1 + s0 + 0.01) / v - 0.1
    tests["fund_frame_hand"] = abs(fo["ex"][0] - ((v * (1 - 2 * Q.COST * abs(dev)) - 1) - s0) * 100) < 1e-10
    # 끝까지 — 합성 ctx 로 run(수익은 합성 · 모양만 본다)
    global NPERM
    old = NPERM
    NPERM = 3
    try:
        Dr, *_ = _fake(noise=0.5, seed=21)
        out = run(_fake_ctx(Dr, mrange(FORM0, END)))
        q14, q15 = out["Q14"], out["Q15"]
        store = {c: {k: v for k, v in r.items() if k not in ("fr", "fr_pr", "fr20", "controls", "arms")} for c, r in out.items()}
        js = json.dumps(store, ensure_ascii=False, allow_nan=False)
        # K4 뽑기 0 이 선언한 난수 방식과 같다(합성 수익만) — Q15 는 한 줄기 default_rng(20260814) · Q14 는 뽑기 i = default_rng(20260925 + i)
        decs4 = mrange(L4_FIRST, LAST_DEC)
        hold4 = [mshift(t, 1) for t in decs4]
        sgr = l4_signals(Dr, decs4)
        fr_ = onfrac(sgr, decs4)
        plc, _ = simulate(Dr, {t: placebo_target(sgr[t]["U"], fr_) for t in decs4}, hold4, COST_PCT)
        zp0 = l4_k4_z(l4_slot_runs(sgr, decs4), l4_k4_stream())
        r0, _ = simulate(Dr, {t: slot_target(sgr[t]["U"], zp0.get(t, {})) for t in decs4}, hold4, COST_PCT)
        decs2 = mrange(L2_FIRST, LAST_DEC)
        hold2 = [mshift(t, 1) for t in decs2]
        _, per2 = l2_build(Dr, decs2, erc=False)
        r2, _ = simulate(Dr, l2_k4_targets(per2, l2_runs(per2, decs2), 0)[0], hold2, COST_PCT, BORROW)
        tests["k4_draw0_matches_declared_rng"] = (
            abs(q15["placebo"]["K4_mean_vs_placebo"]["draws"][0] - float(np.mean([r0[m] - plc[m] for m in hold4]))) < 1e-12
            and abs(q14["placebo"]["K4_mean_XN"]["draws"][0] - float(np.mean([r2[m] - Dr.spy[m] for m in hold2]))) < 1e-12)
        tests["run_forward_block"] = all({"start", "prereq", "commit_ready"} <= set(r["lib"]["forward"]) and r["lib"]["forward"]["commit_ready"] is False
                                         and r["lib"]["forward"]["start"]["t0"] == FWD_T0 for r in out.values())
        tests["run_synthetic_shape"] = (len(q14["placebo"]["K4_mean_XN"]["draws"]) == 3 and len(q15["placebo"]["K4_PsiM"]["draws"]) == 3
                                        and q14["fr"]["hold"][0] == "2019-10" and q14["fr"]["hold"][-1] == "2026-08" and len(q14["fr"]["ex"]) == 83
                                        and q15["fr"]["hold"][0] == "2017-10" and len(q15["fr"]["ex"]) == 107
                                        and set(q14["controls"]) == {"P1", "P1C"} and set(q15["controls"]) == {"PLACEBO", "C1", "INC1", "INC2"}
                                        and len(q14["targets_hash"]) == 64 and isinstance(q14["f0"]["ok"], bool) and len(js) > 1000)
    finally:
        NPERM = old
    return {"ok": all(bool(v) for v in tests.values()), "tests": {k: bool(v) for k, v in tests.items()}}


def _runs_of(seq):
    R = []
    for z in seq:
        if R and R[-1][0] == z:
            R[-1][1] += 1
        else:
            R.append([z, 1])
    return R


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r["ok"] else 1)
    if "--dry" in sys.argv:
        print(json.dumps(_clean(dry(Q.Ctx())), ensure_ascii=False, indent=1))
        sys.exit(0)
    print(__doc__)
