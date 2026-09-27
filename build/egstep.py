# -*- coding: utf-8 -*-
"""build/egstep.py — EG30 상태 조건 스텝 역할 검정(EGSTEP) 계산 엔진.
러너(build/egstep_run.py)가 핀 판 임시 뿌리 셋 안에서 자식 과정으로 부른다(이 파일은 뿌리마다 build/ 에 복사된다).

사전등록: build/PREREG-<등록 날짜>-EGSTEP.md 하나(글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).

무엇을 재나(역할 검정 — EG30 의 약점 둘을 상태 조건 스텝 둘이 고치는가 · 수익 · 반등을 내주지 않고)
  코어 C0   EG30 V0(얼린 qbatch_core.Ctx().V0_targets = eg30plus.v0_targets · 분기말 d_m 종가 재구성 · 시총가중 30 · 20% 상한 ·
            얼린 q_switch.offense_v0 장부) — 몫 ≡ 1 이면 data/_qbatch.json V0.ex 와 같아야 한다(F0 · 짝맞춤 E0).
  금리 스텝 R  D13 국면 그대로(dstk.regimes · DFII10 월말 − 3개월 전 월말 ≥ +0.20 · 부동소수 비교 = T17) 가 «가치» 인 결정 달에만
            슬리브 f_R 을 DSTK 가치 다리 V30(dstk: 빌더 val · N 30 · 시총가중 · 이름당 25% · 감싸기 ① 명단 · ② 채점 가격 · 월말 재선정 · T+1)으로.
  방어 스텝 D  Q06 상관 놀람 상태(얼린 q_corrsurp.states · HighMS_m ∧ MonthCS_m > 1 — 크기가 크고 업종 사이 상관이 평소와 갈라진 달)인 결정 달에만
            슬리브 f_D 를 배치 X 의 목적지 책 D(얼린 V02 LBS 선정 · 이름당 20% 상한 · x_adapter D 자식 · D 책 자식)로.
  RD        둘 다 — s_D = f_D·1[D] · s_V = min(f_R·1[R], ½ − s_D) · EG30 = 나머지(스텝 몫 합 ≤ ½ · 방어 먼저 · EG30 코어는 늘 ½ 이상 ·
            겹친 달 EG30 ½ · D ½ — 오케스트레이터 결정 ② · 계산 전). 1.0 쌍둥이 RD1 은 s_D = 1·1[D] · s_V = min(1·1[R], 1 − s_D).
  체결      각 장부의 자기 되맞춤은 등록된 그대로(V0 · D = d_m 종가 · V30 = T+1) · 스텝의 몫 교체만 보유월 첫 거래일(T+1) 종가
            (얼린 x_adapter.mix_t1 · 두 장부 · 세 장부 팔은 mix_t1_multi — 두 장부에서 mix_t1 과 같아야 한다 · 짝맞춤 E1) · 편도 10bp(20bp 판).
  펀드 틀    F = 0.9 × SPY TR + 0.1 × 슬리브(얼린 qbatch_core.fund_from_path · 매월 말 되돌림) 대 SPY TR · 보유 2016-09 ~ 2026-08(120).
  확증 가족  R · D · RD 각각 대 C0 · 팔마다 제 역할의 통계(오케스트레이터 결정 ① · 계산 전) —
            R: Δ_R = R 켜진 보유월(가치 국면 36) 위의 (R − C0) 월 펀드 초과 평균 · D · RD: Δ_down = 얼린 하락월 35(data/mech_episodes.json down_m ·
            SPY TR < 0) 위의 평균 · H1 > 0(한쪽) · 달력 시간 NW(3) HAC t(얼린 eg30plus.down_t 를 그 가면으로) · p = t 분포(가면 달 수 − 1 ·
            R 35 · D · RD 34) 꼬리 · Holm α 0.05 · m 3(v_tests.holm).
  무해      20bp 전 월 Δ 평균 ≥ 0 ∧ 반등 다리 이긴 수 ≥ C0 − 1(얼린 mech_episodes 반등 8) ∧ 슬리브 편도 연 회전 ≤ 10.
  채택 표시  Holm 기각 ∧ 무해 ∧ 지수 레버선(d1: 확증 통계 > 같은 달 · 같은 크기를 SPY 로 옮긴 지수 레버 대조의 같은 통계(같은 가면) ∧
            d2: 20bp 전 월 Δ ≥ 그 대조의 것). 지수 레버선은 목적지를 재지 방아쇠 시점을 재지 않는다 — 시점 · R 겹침 시점 · 바구니 · 꾸준함 · 효율은
            읽기(표시를 바꾸지 않는다). 첫 판의 금리 역할 읽기는 R 의 확증 통계(Holm)와 d1 이 됐다(오케스트레이터 결정 ①).
            펀드에 붙이는 것은 사용자 결정(날짜 없음 · 전방 원장 없음).
  대조 · 보고  지수 레버(R→SPY · D→SPY · RD→SPY · 오케스트레이터의 «희석 대조») · 같은 초과 희석(배치 X DIL 규칙 · c·EG30 + (1 − c)·SPY 상수) ·
            정적 혼합(같은 평균 몫) · 1.0 쌍둥이 · Q06 쌍둥이(T1 HighMS 만 · T2 HighMS ∧ CS ≤ 1) ·
            위약(D · R 상태의 구간 섞기 · 켜진 달 수 · 교체 수 보존 · 1,000 · 씨앗 고정 · D 는 R 겹침까지 맞춘 판 하나 더) ·
            상태별 자르기(R 켜짐 · D 켜짐 · D∧R · D∧¬R · R∧¬D · 둘 다 꺼짐) · V30 홀로 · D 홀로 · 부분 창 2019-06 ~.

🚨 랩 규율: 수익 경로를 만드는 자식(vleg · s · judge)은 등록 커밋이 origin 에 오른 뒤 러너의 한 번 굽기와 눈가린 연기에서만 돈다.
   f0v · f0s 는 개수 · 날짜 · 동일성(참/거짓 · 해시 · 얼린 V0 경로와의 최대 절대 차)만 돌려준다 — 수익 · 초과 · IR · Δ · 적중 통계 없음.
🚨 머리에서는 표준 라이브러리만 부른다(러너 · validate_site 가 numpy 없이 이 파일을 읽을 수 있게).
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import math
import os
import sys
import time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# ══════════════════════════════════════════════════════════════════════════
#  등록 상수(러너 REGISTERED 가 같은 값을 들고 판 점검에서 대조한다)
# ══════════════════════════════════════════════════════════════════════════
F_R = 0.5                              # 금리 스텝 크기(슬리브 몫) — 배치 X 에서 사용자가 고른 ½(U1) · 계산 전 고정
F_D = 0.5                              # 방어 스텝 크기 — 같은 까닭
F_TWIN = 1.0                           # 1.0 쌍둥이(가족 밖 · 보고만)
STEP_CAP = 0.5                         # RD 의 스텝 몫 합 상한 — 방어 먼저 · EG30 코어 ≥ ½(오케스트레이터 결정 ② · 계산 전) · 1.0 쌍둥이 RD1 의 상한은 F_TWIN
HOLD = ("2016-09", "2026-08")
N_HOLD = 120
FORM_FIRST, FORM_LAST = "2016-08", "2026-07"
COST = 0.0010
COST20 = 0.0020
TURN_MAX = 10.0
REB_SLACK = 1                          # 무해: 반등 다리 이긴 수 ≥ C0 − 1
HOLM_ALPHA = 0.05
DOWN_LAG = 3                           # eg30plus.down_t 의 Bartlett 시차(달력 달)
K_PLACEBO = 1000
SEED = 20260927                        # D 위약 · R 위약은 SEED + 1
SEED_STRAT = 20260929                  # D 의 R 겹침 맞춘 위약(구간 섞기 뽑기 가운데 R 과의 겹침이 참과 같은 것만 받는다) — 계산 전 고정
N_STRAT_PROBE = 20000                  # F0: 그 씨앗의 첫 20,000 뽑기 가운데 받아들인 수(상태 개수만 · 수익 없음)
STRAT_MAX_TRIES = 200000               # 굽기: 받아들인 뽑기가 K 에 닿지 못하면 여기서 멈춘다(못 닿으면 백분위 없음 → 시점 읽기 «약함»)
PCT_TIMING = 95.0                      # 시점 읽기: 위약 백분위 < 95 면 «시점 증거 약함»
LATE_FROM = "2019-06"                  # 부분 창(보고만) — DSTK 가치 채점 커버리지 ≥ 80% 가 끝까지 이어지는 첫 보유월(DSTK F0)
NV = 30                                # 가치 다리 이름 수(DSTK A30 의 가치 다리)
PRIMARY = ("R", "D", "RD")
ROLE = {"R": "r_on", "D": "down", "RD": "down"}   # 확증 통계의 가면(팔마다 제 역할 · 오케스트레이터 결정 ① · 계산 전) — r_on = R 켜진 보유월 36 · down = 얼린 하락월 35
DIL_OF ={"R": "R_SPY", "D": "D_SPY", "RD": "RD_SPY"}
STAT_OF = {"R": "R_STAT", "D": "D_STAT", "RD": "RD_STAT"}
ARMS = ("C0", "R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT", "R1", "D1", "RD1", "D_T1", "D_T2",
        "V_ALONE", "D_ALONE")
BOOK_KEYS = ("E", "V", "D", "S")       # E = EG30 V0 · V = DSTK 가치 다리 V30 · D = 배치 X D(V02) · S = SPY TR(90% 지수 바구니 대리 · 지수 레버 대조 · 같은 초과 희석만)
COUNTED = ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT", "R1", "D1", "RD1", "D_T1", "D_T2")
CUT_ARMS = ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT")   # 상태별 자르기(보고 · 판정 아님)
CUT_KEYS = ("r_on", "d_on", "d_and_r", "d_not_r", "r_not_d", "neither")
STATE_KEYS = ("r_on", "d_on", "both", "r_only", "d_only", "neither", "r_switch", "d_switch", "r_on_runs", "d_on_runs", "t1_on", "t2_on")
CUM_N_BEFORE = 1044                    # 누적 N 기저 = 보수적 맥락 합(배치마다 갈린 계수기의 증분을 모두 더한 값 · 가장 큰 단일 기록 값은 DSTK 결과 문서의 998) — 오케스트레이터 결정 ③(계산 전)
N_ROWS_COUNTED = 14
V0_FRESH_TOL = 1e-10                   # C0(몫 ≡ 1) 대 같은 뿌리에서 새로 지은 얼린 Ctx.V0() — 배치 X 짝맞춤 B 와 같은 문턱
V0_STORED_TOL = 5e-7 + 1e-10           # C0 대 data/_qbatch.json V0.ex — 저장 값이 소수 여섯째 자리로 반올림돼 있다(F0 판독: 120/120 이 1e−6 격자 위)
# 얼린 재사용 모듈이 이 값이어야 한다(자식이 단언 · 다르면 멈춘다)
DSTK_EXPECT = {"THR": 0.20, "W_V": {"value": 0.70, "neutral": 0.50, "growth": 0.30}, "LAG_M": 3, "CAP": 0.25, "NMAX": 30, "EXEC_LAG": 1,
               "HOLD": ("2016-09", "2026-08"), "FORM_WARM": "2016-07", "FORM_FIRST": "2016-08", "FORM_LAST": "2026-07",
               "STYLE_KEYS": {"V": "val", "G": "grow"}, "MIN_NAMES": 100, "LATE_FROM": "2019-06",
               "VD1_DIGEST": "1f552d177d0699c7aa4c9f7779e2c0c463e2f2057e3663b623b00e4adf6ffd4c"}
Q06_EXPECT = {"SPDR": ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"), "D0": "2006-01-04", "S0": "2009-01-02",
              "WMIN": 756, "WMAX": 2520, "PCT": 80, "NMIN_M": 36, "M0": "2009-01"}
# 뿌리마다 build/ 에서 단언하는 얼린 blob(LF 바이트의 git blob sha1)
ROOT_BLOBS = {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
              "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
              "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"}
DROOT_BLOBS = {"dstk": "60e634875df6a42f191b6ce91fd391dffc721d4f", "v_tests": "2f1ec4db1cd7458564da73ec5ad88cef8a0b2f2f",
               "t_signals": "35e2407d8f80c81aacec5a62128dd78a73b68c0b", "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d",
               "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628"}
# 등록 F0 개수(러너 --f0 가 핀 뿌리 셋으로 센 값 · 수익 없음) — 굽기 F0 가 같아야 표식을 쓴다
F0_EXPECT = {'dstk_ok': True, 'dstk_valid': 121, 'r_value': 36, 'r_same_as_t17': True, 'q06_timing_ok': True, 'q06_same_as_recorded': True, 'n_forms': 120, 'r_on': 36, 'd_on': 22, 'both': 12, 'r_only': 24, 'd_only': 10, 'neither': 74, 'r_switch': 25, 'd_switch': 23, 'r_on_runs': 13, 'd_on_runs': 12, 't1_on': 35, 't2_on': 13, 'v0_hash_ok': True, 'v0_identity_ok': True, 'grid_same': True, 'n_win_dates': 2513, 'down_frozen': 35, 'down_frozen_late': 29, 'late_months': 87, 'down_pr': 39, 'd_pairing_A': True, 'd_forms': 120, 'd_names_min': 106, 'd_names_max': 130, 'd_cov_ok': 120, 'd_sel_hash16': '24f37379ab36e2f8', 'd_strat_acc': 637}

ARM_LABEL = {"C0": "C0 · EG30 V0(코어 · 기준)", "R": "R · 금리 스텝 → 가치 다리 V30 · ½", "D": "D · 방어 스텝(Q06) → V02 책 D · ½",
             "RD": "RD · 두 스텝(방어 먼저 · 스텝 몫 합 ≤ ½)", "R_SPY": "R→SPY · 지수 레버 대조(같은 달 · 같은 크기를 지수 바구니로)",
             "D_SPY": "D→SPY · 지수 레버 대조", "RD_SPY": "RD→SPY · 지수 레버 대조", "R_STAT": "R 정적 혼합(같은 평균 몫 · 늘)",
             "D_STAT": "D 정적 혼합(같은 평균 몫 · 늘)", "RD_STAT": "RD 정적 혼합(같은 평균 몫 · 늘)", "R1": "R 1.0 쌍둥이",
             "D1": "D 1.0 쌍둥이", "RD1": "RD 1.0 쌍둥이(겹친 달은 D 먼저)", "D_T1": "D 쌍둥이 T1(HighMS 만 · Q06 얼린 쌍둥이)",
             "D_T2": "D 쌍둥이 T2(HighMS ∧ CS ≤ 1)", "V_ALONE": "참고 · V30 홀로(슬리브 전부)", "D_ALONE": "참고 · D 홀로(슬리브 전부)"}


class StopBake(RuntimeError):
    """등록된 멈춤 조건 · 결정적 자기 점검 실패 — 굽기 자식이 {"stopped": 사유} 로 돌려준다(다시 굽기로 풀리지 않는다)."""


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7]) + k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def months_between(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def forms():
    """결정(편입) 달 2016-08 ~ 2026-07 — 보유월 2016-09 ~ 2026-08."""
    return months_between(FORM_FIRST, FORM_LAST)


def _json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _wjson(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(p + ".part", p)


def _rbytes(p):
    with open(p, "rb") as f:
        return f.read()


def blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def assert_blobs(build_dir, want):
    """build_dir 의 모듈 blob(LF 바이트) 이 등록 값과 같아야 한다 — 다르면 멈춘다(부르지 않는다)."""
    bad = {}
    for m, b in want.items():
        p = os.path.join(build_dir, m + ".py")
        got = blob_sha1(_rbytes(p).replace(b"\r\n", b"\n")) if os.path.exists(p) else None
        if got != b:
            bad[m] = (got or "없음")[:12]
    if bad:
        raise StopBake("얼린 blob 불일치 %s" % bad)
    return True


def lines_sha(xs):
    return hashlib.sha256("\n".join(str(x) for x in xs).encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
#  순수 규칙(합성 selftest 가 모든 갈래를 본다)
# ══════════════════════════════════════════════════════════════════════════
def rd_shares(r, d, f_r, f_d, cap):
    """두 스텝 몫 — s_D = f_d·1[D] 먼저(사용자 원칙 «하락 방어 우선») · s_V = min(f_r·1[R], cap − s_D) · EG30 = 1 − s_V − s_D.
    cap = 스텝 몫 합의 상한 — RD 는 ½(STEP_CAP · EG30 코어는 늘 ½ 이상 · 오케스트레이터 결정 ② · 계산 전) · 1.0 쌍둥이 RD1 은 1.
    ½ · ½ · 상한 ½: 겹친 달 EG30 ½ · D ½(V 0) · R 만 켜진 달 EG30 ½ · V ½ · D 만 켜진 달 EG30 ½ · D ½ · 1.0 쌍둥이의 겹친 달은 D 가 다 든다.
    f_d 가 상한보다 크면 등록 규칙 밖이다(방어 몫 자체는 자르지 않는다)."""
    import numpy as np
    assert f_d <= cap + 1e-15 and 0.0 < cap <= 1.0
    r, d = np.asarray(r, float), np.asarray(d, float)
    s_d = f_d * d
    s_v = np.minimum(f_r * r, np.maximum(cap - s_d, 0.0))
    return s_v, s_d


def arm_shares(R, Dq, T1, T2):
    """팔마다 장부 몫 {장부 키: 보유월 몫 배열(120)} — E 는 1 − 나머지. 상태 배열은 결정 달 차례(0/1)."""
    import numpy as np
    R, Dq, T1, T2 = (np.asarray(x, float) for x in (R, Dq, T1, T2))
    n = len(R)
    one = np.ones(n)
    rdv, rdd = rd_shares(R, Dq, F_R, F_D, STEP_CAP)
    rd1v, rd1d = rd_shares(R, Dq, F_TWIN, F_TWIN, F_TWIN)
    sp = {"C0": {},
          "R": {"V": F_R * R}, "D": {"D": F_D * Dq}, "RD": {"V": rdv, "D": rdd},
          "R_SPY": {"S": F_R * R}, "D_SPY": {"S": F_D * Dq}, "RD_SPY": {"S": rdv + rdd},
          "R_STAT": {"V": np.full(n, float(np.mean(F_R * R)))}, "D_STAT": {"D": np.full(n, float(np.mean(F_D * Dq)))},
          "RD_STAT": {"V": np.full(n, float(np.mean(rdv))), "D": np.full(n, float(np.mean(rdd)))},
          "R1": {"V": F_TWIN * R}, "D1": {"D": F_TWIN * Dq}, "RD1": {"V": rd1v, "D": rd1d},
          "D_T1": {"D": F_D * T1}, "D_T2": {"D": F_D * T2},
          "V_ALONE": {"V": one.copy()}, "D_ALONE": {"D": one.copy()}}
    out = {}
    for a, s in sp.items():
        rest = np.zeros(n)
        for k in s:
            rest = rest + s[k]
        e = 1.0 - rest
        if e.min() < -1e-12 or rest.min() < -1e-12:
            raise StopBake("몫 음수(%s)" % a)
        out[a] = dict(s, E=np.clip(e, 0.0, 1.0))
    return out


def mean_share(sh):
    """팔의 달 가중 평균 몫(보고 · 정적 혼합의 크기)."""
    import numpy as np
    return {k: float(np.mean(v)) for k, v in sh.items()}


def mix_t1_multi(F, shares, books, c, fund_from_path, s_pre=None):
    """얼린 x_adapter.mix_t1 의 N 장부 판 — 같은 장부(각자의 비용 포함 일간 성장) · 보유월 k 의 첫 수익일(= 결정 d_m 다음 거래일 T+1)은
    앞 몫(흘러간 구성)으로 들고 그날 종가에 몫 shares[k] 로 되맞춘다(편도 c · 현금 장부는 무비용) · 창 첫 달의 앞 몫은 s_pre(기본 첫 장부 1).
    회전 = 몫 교체 거래 + 장부 자기 회전 × 평균 몫(mix_t1 과 같은 근사). 두 장부면 mix_t1 과 같은 값(selftest · 짝맞춤 E1)."""
    import numpy as np
    S = np.asarray(shares, float)
    nM, nB = S.shape
    assert nM == len(F.months) and nB == len(books) and S.min() >= -1e-15 and np.all(np.abs(S.sum(1) - 1.0) <= 1e-12)
    g = [np.exp(bk.lg0 + bk.lf.get(c, 0.0)) for bk in books]
    V = [0.0] * nB
    pre = [1.0] + [0.0] * (nB - 1) if s_pre is None else [float(x) for x in s_pre]
    for q in range(nB):
        V[q] = pre[q]
    path = {F.i0: 1.0}
    trs = 0.0
    for k in range(nM):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < nM else F.T
        for j in range(a, b):
            for q in range(nB):
                V[q] *= g[q][j]
            if j == a:
                Vt = sum(V)
                t = [abs(S[k, q] * Vt - V[q]) for q in range(nB)]
                cost = c * sum((0.0 if books[q].cash else t[q]) for q in range(nB))
                trs += sum(t) / Vt
                Vt -= cost
                V = [S[k, q] * Vt for q in range(nB)]
            path[int(F.day[j])] = sum(V)
    own = sum(float((1.0 - np.exp(bk.lf[c])).sum()) / c * float(np.mean(S[:, q])) for q, bk in enumerate(books) if c in bk.lf)
    fr = fund_from_path(F.G, {"path": path, "turn": (trs + own) / 2.0 / F.years}, F.months, cost=c, basis="TR")
    fr["cost_drag"] = float(c * (trs + own) / F.years * 100)
    return fr


def run_arm(F, sh, books, c, XA, Q):
    """팔 하나 — 장부가 E 와 다른 하나뿐이면 얼린 x_adapter.mix_t1(두 장부) · 둘이면 mix_t1_multi · 몫 ≡ 1(C0)이면 mix_t1(1, E, S)."""
    import numpy as np
    other = [k for k in ("V", "D", "S") if k in sh]
    if not other:
        return XA.mix_t1(F, np.ones(len(F.months)), books["E"], books["S"], c, Q.fund_from_path)
    if len(other) == 1:
        return XA.mix_t1(F, np.clip(sh["E"], 0.0, 1.0), books["E"], books[other[0]], c, Q.fund_from_path)
    cols = ["E"] + other
    M = np.column_stack([sh[k] for k in cols])
    return mix_t1_multi(F, M, [books[k] for k in cols], c, Q.fund_from_path)


def p_one_sided(t, nd):
    """한쪽 p — 얼린 eg30plus.down_t 의 설계대로 t(n_d − 1) 꼬리 · t 가 없으면 None(기각 못 함)."""
    if t is None or nd is None or nd < 2:
        return None
    from scipy.stats import t as _t
    return float(_t.sf(float(t), int(nd) - 1))


def delta_stats(ex, ex0, ex20, ex020, fz, crash, surge, E):
    """팔 − C0 월 펀드 초과 차(보고 · 가족 통계) — fz = 얼린 하락월 35 가면 · crash/surge = 얼린 CRASH-M · SURGE-M 가면."""
    import numpy as np
    d = np.asarray(ex, float) - np.asarray(ex0, float)
    d20 = np.asarray(ex20, float) - np.asarray(ex020, float)
    fz = np.asarray(fz, bool)
    nd = int(fz.sum())
    t = E.down_t(d, fz, DOWN_LAG)
    return {"n": len(d), "n_down": nd, "down_mean": float(d[fz].mean()), "down_t": t, "p": p_one_sided(t, nd),
            "up_mean": float(d[~fz].mean()), "all_mean_ann": float(d.mean() * 12), "all_nw_t": E.nw_t(d), "win": float(np.mean(d > 0) * 100),
            "all20_mean_ann": float(d20.mean() * 12), "down20_mean": float(d20[fz].mean()),
            "crash_m_mean": (float(d[np.asarray(crash, bool)].mean()) if np.asarray(crash, bool).any() else None),
            "surge_m_mean": (float(d[np.asarray(surge, bool)].mean()) if np.asarray(surge, bool).any() else None)}


def primary_stat(d, mask, E):
    """확증 통계(팔마다 제 역할 · 오케스트레이터 결정 ① · 계산 전) — 가면 위 (팔 − C0) 월 펀드 초과 평균 · 달력 HAC t(얼린 eg30plus.down_t 를
    그 가면으로 · Bartlett 3 · n/(n − 1)) · 한쪽 p = t(n − 1) 꼬리. R: 가면 = R 켜진 보유월(36 → t(35)) · D · RD: 얼린 하락월(35 → t(34) ·
    delta_stats 의 down_mean · down_t · p 와 같다)."""
    import numpy as np
    d = np.asarray(d, float)
    mk = np.asarray(mask, bool)
    n = int(mk.sum())
    t = E.down_t(d, mk, DOWN_LAG)
    return {"n": n, "mean": (float(d[mk].mean()) if n else None), "t": t, "p": p_one_sided(t, n)}


def placebo_stats(dp, fz, own):
    """위약 뽑기 하나의 (팔 − C0) 월 차 dp → (Δ_down · 전 월 Δ 연율 · 그 뽑기의 켜진 보유월 평균). 셋째는 R 위약의 확증 통계 Δ_R 이다
    (뽑기마다 제 켜진 달 — 켜진 달 수는 구간 섞기가 보존한다 · 읽기 ② 의 R)."""
    import numpy as np
    dp = np.asarray(dp, float)
    fz, own = np.asarray(fz, bool), np.asarray(own, bool)
    return float(dp[fz].mean()), float(dp.mean() * 12), (float(dp[own].mean()) if own.any() else None)


def pct_rank(draws, true):
    """랩 규약(eg30plus · q_switch.pct_rank) — 참값보다 작은 뽑기의 백분율."""
    import numpy as np
    return float(np.mean(np.asarray(draws, float) < true) * 100)


def holm_family(p):
    """한쪽 p(가족 R · D · RD) → 얼린 v_tests.holm(α 0.05) — None 은 기각 못 함(분모에 남는다)."""
    import v_tests as VT
    h = VT.holm(dict(p), HOLM_ALPHA)
    return {"p": dict(p), "reject": h["reject"], "threshold": h["threshold"], "order": h["order"], "m": h["m"], "alpha": HOLM_ALPHA}


def harmless(d_arm, reb_arm, reb_c0, turn):
    """무해(계산 전 고정) — ① 20bp 전 월 Δ 평균 ≥ 0 ② 반등 다리 이긴 수 ≥ C0 − 1 ③ 슬리브 편도 연 회전 ≤ 10."""
    c = {"all20_ge0": bool(d_arm.get("all20_mean_ann") is not None and d_arm["all20_mean_ann"] >= 0.0),
         "rebounds_ok": bool(reb_arm is not None and reb_c0 is not None and reb_arm >= reb_c0 - REB_SLACK),
         "turn_le10": bool(turn is not None and turn <= TURN_MAX)}
    return {"harmless": bool(all(c.values())), "conds": c, "all20_mean_ann": d_arm.get("all20_mean_ann"), "rebounds_win": reb_arm,
            "rebounds_c0": reb_c0, "turn": turn}


def beats_dilution(p_arm, p_dil, d_arm, d_dil):
    """지수 레버선(채택 표시의 추가 조건 · 오케스트레이터의 «희석 대조») — d1: 확증 통계(점 추정 · p_arm) > 같은 달 · 같은 크기를 SPY 로 옮긴 대조의
    같은 통계(같은 가면 · p_dil — R: R 켜진 달 Δ_R · D · RD: Δ_down · 오케스트레이터 결정 ①) ∧ d2: 20bp 전 월 Δ ≥ 그 대조의 것(d_arm · d_dil).
    🚨 이것은 배치 X 의 IDX 레버와 같은 꼴이다 — 목적지(V30 · D)가 지수 바구니보다 나은가를 잴 뿐 방아쇠 시점을 재지 않는다
    (β 가 낮은 D 는 하락월에 구조적으로 유리하다). 배치 X 의 «희석선»(같은 초과를 내는 상수 희석 DIL)은 dil_share · 효율 읽기가 따로 본다."""
    pp = p_arm.get("mean") is not None and p_dil.get("mean") is not None and p_arm["mean"] > p_dil["mean"]
    aa = (d_arm.get("all20_mean_ann") is not None and d_dil.get("all20_mean_ann") is not None
          and d_arm["all20_mean_ann"] >= d_dil["all20_mean_ann"])
    return {"stat": p_arm.get("stat"), "prim_gt_dil": bool(pp), "all20_ge_dil": bool(aa), "ok": bool(pp and aa),
            "dil_prim_mean": p_dil.get("mean"), "dil_all20_mean_ann": d_dil.get("all20_mean_ann")}


def adopt_mark(reject, hm, dil):
    return bool(reject and hm["harmless"] and dil["ok"])


def verdict(adopt, reject):
    """결과 문서 «판정:» — 채택 표시 ≥ 1 → 보류(펀드에 붙이기는 사용자 결정) · 기각 ≥ 1(표시 없음) → 측정만 · 기각 0 → 기각."""
    if any(adopt.values()):
        return "보류"
    if any(reject.values()):
        return "측정만"
    return "기각"


def judge_core(M):
    """판정 순수 규칙 — 팔마다 제 역할의 확증 통계(M["primary"] · R: R 켜진 달 Δ_R · D · RD: Δ_down)의 한쪽 p 로 Holm(m 3) · 무해 셋 ·
    지수 레버선(d1 = 같은 가면의 같은 통계 · d2 = 20bp 전 월 Δ) · 채택 표시 · 판정. 가면이 등록(ROLE)과 다르면 멈춘다."""
    P = M["primary"]
    bad = [x for a in PRIMARY for x in (a, DIL_OF[a]) if (P.get(x) or {}).get("stat") != ROLE[a]]
    if bad:
        raise StopBake("확증 통계의 가면이 등록과 다르다(%s)" % ", ".join(bad))
    fam = holm_family({a: P[a]["p"] for a in PRIMARY})
    fam["stat"] = {a: P[a]["stat"] for a in PRIMARY}
    fam["n"] = {a: P[a]["n"] for a in PRIMARY}
    reb0 = M["arms"]["C0"]["m"]["mech"]["rebounds"]["win"]
    gates, adopt = {}, {}
    for a in PRIMARY:
        hm = harmless(M["delta"][a], M["arms"][a]["m"]["mech"]["rebounds"]["win"], reb0, M["arms"][a]["turn"])
        idx = beats_dilution(P[a], P[DIL_OF[a]], M["delta"][a], M["delta"][DIL_OF[a]])   # 지수 레버선(게시 칸 열쇠는 첫 판 그대로 "dilution")
        gates[a] = {"harmless": hm, "dilution": idx}
        adopt[a] = adopt_mark(fam["reject"][a], hm, idx)
    return fam, gates, adopt, verdict(adopt, fam["reject"])


def readings(delta, placebo, years=None, dil=None, prim=None):
    """표시의 읽기(계산 전 고정 · 표시를 바꾸지 않는다 · 참 = 그 약점이 읽혔다 · None = 잴 수 없음) — 팔의 «확증 통계» 는 prim[a]
    (R: R 켜진 보유월 Δ_R · D · RD: 얼린 하락월 Δ_down · 오케스트레이터 결정 ①). 읽기는 그 팔의 확증 통계로 잰다.
    ① 바구니 읽기(R · D · RD): 같은 평균 몫을 늘 옮긴 정적 혼합이 D · RD 는 전 월 Δ(10bp) 와 Δ_down 둘 다, R 은 전 월 Δ 가 스텝보다 크거나 같으면
       «정적 혼합(바구니) 몫 — 상태 스텝 증거 아님». R 에 Δ_R 칸이 없는 까닭: 스텝은 켜진 달에 ½ 을 들고 정적 혼합은 늘 평균 몫(0.15)을 들어
       Δ_R 이 구성상 스텝 쪽으로 기운다(바구니와 시점을 가르지 못한다) — 같은 평균 몫에서 가르는 칸은 전 월 Δ 다.
    ② 시점 읽기(R · D · RD): 그 상태의 위약(구간 섞기) 백분위가 95 미만이면 «방아쇠 시점이 무작위 배치와 구별되지 않는다» — R 은 R 위약의 Δ_R
       (뽑기마다 그 뽑기의 켜진 달 평균) · D 는 D 위약의 Δ_down · RD 는 R · D 위약의 Δ_down 가운데 하나라도(RD 의 통계가 Δ_down 이라서).
    ③ R 겹침 시점 읽기(D · RD): R 과의 겹침까지 맞춘 D 위약 백분위(Δ_down)가 95 미만이거나 뽑기가 K 에 못 닿으면 «D 의 시점이 금리 상태 겹침과 가려지지 않는다».
    ④ 꾸준함 읽기(R · D · RD): 해마다 이긴 수(얼린 evaluate · 부분 연도 포함 11)가 C0 보다 적으면 «꾸준함(해마다)을 내줬다» — 여유 없음(읽기라 표시를 바꾸지 않는다).
    ⑤ 효율 읽기(R · D · RD): 확증 통계가 같은 초과 희석(배치 X DIL 규칙)의 같은 통계(같은 가면)를 넘지 못하면 «같은 초과를 EG30 을 덜 들어 얻는
       희석보다 못하다(배치 X 희석선 밑)».
    첫 판의 ⑥ 금리 역할 읽기(R 켜진 달 평균 Δ > 0 · > 같은 달 R→SPY)는 R 의 확증 통계(Holm · H1 Δ_R > 0)와 지수 레버선 d1 이 됐다 — 읽기에서 뺐다."""
    out = {}
    prim = prim or {}
    pr = (placebo.get("R") or {}).get("pct_down")
    prr = (placebo.get("R") or {}).get("pct_role")
    pdd = (placebo.get("D") or {}).get("pct_down")
    pdr = (placebo.get("D_R") or {}).get("pct_down")
    y0 = (years or {}).get("C0")
    for a in PRIMARY:
        st = STAT_OF[a]
        basket = None
        if st in delta and a in delta:
            basket = bool(delta[st]["all_mean_ann"] >= delta[a]["all_mean_ann"])
            if ROLE[a] == "down":
                basket = bool(basket and delta[st]["down_mean"] >= delta[a]["down_mean"])
        ps = {"R": [prr], "D": [pdd], "RD": [pr, pdd]}[a]
        weak = bool(any((p is None) or (p < PCT_TIMING) for p in ps))
        weak_r = None if a == "R" else bool(pdr is None or pdr < PCT_TIMING)
        ya = (years or {}).get(a)
        steady_lost = None if (ya is None or y0 is None) else bool(ya < y0)
        mine = (prim.get(a) or {}).get("mean")
        theirs = ((((dil or {}).get(a) or {}).get("prim")) or {}).get("mean")
        eff_weak = None if (mine is None or theirs is None) else bool(not (mine > theirs))
        out[a] = {"stat": ROLE[a], "static_basket": basket, "timing_weak": weak, "placebo_pct": ps, "timing_weak_r": weak_r,
                  "placebo_pct_r": (None if a == "R" else pdr), "steady_lost": steady_lost, "years_won": ya, "years_won_c0": y0,
                  "eff_weak": eff_weak, "eff_arm": mine, "eff_dil": theirs}
    return out


def reading_flags(r):
    """표시에 붙는 읽기(이름 목록) — 결과 문서가 «이 표시를 스텝이 약점을 고쳤다로 읽지 않는다» 를 적는 조건(등록 §6-6 · 읽기 다섯)."""
    f = []
    if r.get("static_basket"):
        f.append("바구니")
    if r.get("timing_weak"):
        f.append("시점")
    if r.get("timing_weak_r"):
        f.append("R 겹침 시점")
    if r.get("steady_lost"):
        f.append("꾸준함")
    if r.get("eff_weak"):
        f.append("효율")
    return f


def dil_share(e_ann, x_v0):
    """배치 X 의 같은 초과 희석(DIL) 규칙 그대로 — 슬리브 = c·EG30 V0 + (1 − c)·SPY(상수 몫) · c = 1 + e/x_V0 를 [0, 1] 로 자른다
    (e = 팔 − C0 전 월 Δ 연율 · x_V0 = C0 연 초과 · 둘 다 10bp). 팔이 C0 이상이거나(e ≥ 0) x_V0 ≤ 0 이면 c = 1(희석 없음 = C0).
    얼린 x_adapter._s_child 의 한 줄과 같은 식이다(합성 selftest 가 그 줄을 글자로 대조한다)."""
    import numpy as np
    return 1.0 if (x_v0 <= 0 or e_ann >= 0) else float(np.clip(1 + e_ann / x_v0, 0.0, 1.0))


def state_masks(aR, aD):
    """보유월 차례(결정 달 상태 = 다음 보유월)의 상태 가면 — 상태별 자르기(보고)."""
    import numpy as np
    r, d = np.asarray(aR) > 0, np.asarray(aD) > 0
    return {"r_on": r, "d_on": d, "d_and_r": d & r, "d_not_r": d & ~r, "r_not_d": r & ~d, "neither": ~r & ~d}


def state_cuts(d, masks, fz, E):
    """상태별 자르기(보고 · 판정 아님) — 가면마다 달 수 · (팔 − C0) 월 평균 · 달력 HAC t(얼린 down_t 를 그 가면으로 · 5달 미만이면 없음) ·
    그 가운데 얼린 하락월 수 · 평균."""
    import numpy as np
    d = np.asarray(d, float)
    fz = np.asarray(fz, bool)
    out = {}
    for nm in CUT_KEYS:
        mk = np.asarray(masks[nm], bool)
        n, nd = int(mk.sum()), int((mk & fz).sum())
        out[nm] = {"n": n, "mean": (float(d[mk].mean()) if n else None), "t": (E.down_t(d, mk, DOWN_LAG) if n >= 5 else None),
                   "n_down": nd, "down_mean": (float(d[mk & fz].mean()) if nd else None)}
    return out


def check_state_counts(sc, expect):
    """굽기의 상태 개수 = 등록 F0(등록 §7-5) — 다르면 멈춘다(StopBake)."""
    if expect is None:
        return True
    want = {"n": expect.get("n_forms")}
    want.update({k: expect.get(k) for k in STATE_KEYS})
    bad = sorted(k for k in want if sc.get(k) != want[k])
    if bad:
        raise StopBake("상태 개수가 등록 F0 와 다르다(%s)" % ", ".join(bad))
    return True


def strat_placebo(SW, aR, aD, seed, k_target, max_tries, run_one=None):
    """D 의 R 겹침 맞춘 위약 — 얼린 q_switch.seg_shuffle 뽑기(켜진 달 수 · 교체 수 보존) 가운데 R 과의 겹침이 참과 같은 것만 받아 run_one(p) 로 잰다.
    run_one 이 없으면 받아들인 수만 센다(F0 · 상태 개수만). 돌려주는 것 (받은 값 목록 · 뽑기 수 · 참 겹침)."""
    import numpy as np
    r = np.asarray(aR) > 0
    aD = np.asarray(aD)
    ov = int(np.sum((aD > 0) & r))
    n_on, n_sw = int(aD.sum()), int(np.sum(aD[1:] != aD[:-1]))
    rng = np.random.default_rng(seed)
    got, tries = [], 0
    while len(got) < k_target and tries < max_tries:
        p = SW.seg_shuffle(aD, rng)
        tries += 1
        if int(np.sum((p > 0) & r)) != ov:
            continue
        assert int(p.sum()) == n_on and int(np.sum(p[1:] != p[:-1])) == n_sw
        got.append(run_one(p) if run_one is not None else 1)
    return got, tries, ov


def predictions(M):
    """미리 적은 예측(계산 전 고정 · 결과 문서가 채점) — 참/거짓만."""
    dl, fam = M["delta"], M["family"]
    P = {}
    P["P1_no_rejection"] = bool(not any(fam["reject"].values()))
    P["P2_no_adoption"] = bool(not any(M["adopt"].values()))
    P["P3_d_small"] = bool(abs(dl["D"]["all_mean_ann"]) < 0.15)
    P["P4_d_placebo_lt95"] = bool(((M["placebo"].get("D") or {}).get("pct_down") or 0.0) < PCT_TIMING)
    P["P5_r_beats_spy_down"] = bool(dl["R"]["down_mean"] > dl["R_SPY"]["down_mean"])
    P["P6_r_step_gt_static"] = bool(dl["R"]["all_mean_ann"] > dl["R_STAT"]["all_mean_ann"])
    P["P7_rd_rebounds_ok"] = bool(M["gates"]["RD"]["harmless"]["conds"]["rebounds_ok"])
    P["P8_d_rmatched_lt95"] = bool(((M["placebo"].get("D_R") or {}).get("pct_down") or 0.0) < PCT_TIMING)
    pm = M.get("primary") or {}
    r_, rs_ = (pm.get("R") or {}).get("mean"), (pm.get("R_SPY") or {}).get("mean")
    P["P9_r_rate_role"] = bool(r_ is not None and rs_ is not None and r_ > 0 and r_ > rs_)    # R 의 Δ_R > 0 · > 같은 달 R→SPY(점 추정 · 첫 판의 금리 역할 읽기와 같은 조건)
    return P


def state_counts(R, Dq, T1, T2):
    """상태 개수 · 겹침 · 교체 수(시장 상태 · 수익 없음)."""
    R, Dq = [int(x) for x in R], [int(x) for x in Dq]
    sw = lambda x: int(sum(1 for a, b in zip(x, x[1:]) if a != b))
    runs = lambda x, v: int(sum(1 for q, a in enumerate(x) if a == v and (q == 0 or x[q - 1] != v)))
    return {"n": len(R), "r_on": int(sum(R)), "d_on": int(sum(Dq)), "both": int(sum(1 for a, b in zip(R, Dq) if a and b)),
            "r_only": int(sum(1 for a, b in zip(R, Dq) if a and not b)), "d_only": int(sum(1 for a, b in zip(R, Dq) if b and not a)),
            "neither": int(sum(1 for a, b in zip(R, Dq) if not a and not b)), "r_switch": sw(R), "d_switch": sw(Dq),
            "r_on_runs": runs(R, 1), "d_on_runs": runs(Dq, 1), "t1_on": int(sum(int(x) for x in T1)), "t2_on": int(sum(int(x) for x in T2))}


# ══════════════════════════════════════════════════════════════════════════
#  droot 자식(DSTK 핀 판 · 얼린 dstk 엔진) — 가치 다리 V30 · 금리 상태 · F0 개수 · 판정
# ══════════════════════════════════════════════════════════════════════════
def _dstk_check(DS):
    bad = [k for k, v in DSTK_EXPECT.items() if _norm(getattr(DS, k, None)) != _norm(v)]
    if bad:
        raise StopBake("얼린 dstk 상수가 등록 값과 다르다: %s" % bad)


def _norm(x):
    if isinstance(x, (list, tuple)):
        return tuple(_norm(v) for v in x)
    if isinstance(x, dict):
        return {str(k): _norm(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def r_states(DS, A):
    """금리 상태 R(결정 달 2016-08 ~ 2026-07) — 얼린 dstk.regimes(D13 · 부동소수 비교 = T17) 가 «value» 면 1."""
    rg = DS.regimes(A["macro"]["DFII10"], DS.formations())
    fm = forms()
    if any(rg.get(f) is None for f in fm):
        raise StopBake("국면 자료 없음")
    return {f: int(rg[f]["code"] == "value") for f in fm}, {f: rg[f]["code"] for f in fm}


def _win_dates(W, me):
    i0, iE = me[FORM_FIRST], me[HOLD[1]]
    return [W["dates"][i] for i in range(i0, iE + 1)]


def f0v_child(job):
    """F0(droot · 수익 없음) — 얼린 dstk.f0_child(DSTK 등록 F0 서명 대조) · 금리 상태 R · 창 거래일(해시 · 개수)."""
    t0 = time.time()
    assert_blobs(HERE, DROOT_BLOBS)
    import dstk as DS
    _dstk_check(DS)
    f = DS.f0_child()
    A = _json(os.path.join(DATA, "assets.json"))
    R, codes = r_states(DS, A)
    import pit_panel as PP
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        W = PP.load_world()
    wd = _win_dates(W, W["me"])
    return {"kind": "egstep_f0v", "dstk_ok": bool(f.get("ok")), "dstk_bad": list(f.get("bad") or [])[:6], "dstk_expect_diff": list(f.get("expect_diff") or []),
            "dstk_forms": {k: (f.get("forms") or {}).get(k) for k in ("n", "n_valid", "first_valid", "cov_late_from")},
            "dstk_regime": {k: (f.get("regime") or {}).get(k) for k in ("value", "neutral", "growth", "switches", "same_as_t17", "edge_1e9")},
            "dstk_down": f.get("down"), "R": R, "codes": codes, "win_dates_sha": lines_sha(wd), "n_win_dates": len(wd),
            "sec": round(time.time() - t0, 1)}


def vleg_child(job):
    """🚨 수익 경로 — 가치 다리 V30(DSTK LV30 과 같은 줄: 빌더 val · 감싸기 ② 채점 가격 · 상위 30 · 시총가중 25% · 월말 결정 · T+1 체결 ·
    얼린 dstk.book_path · 비용 0 · 10 · 20bp) · 금리 상태 R. 산출은 캐시 작업 폴더에만(부모는 열지 않고 S 자식에 넘긴다).
    얼린 dstk 의 등록된 멈춤(dstk.StopBake — 다리 채움 · 체결 가격 · 비중 합)은 이 엔진의 멈춤으로 옮긴다(멈춤 기록이 결과)."""
    assert_blobs(HERE, DROOT_BLOBS)
    import dstk as DS
    try:
        return _vleg_body(DS)
    except DS.StopBake as e:
        raise StopBake("가치 다리: %s" % str(e)[:200])


def _vleg_body(DS):
    t0 = time.time()
    _dstk_check(DS)
    S = _json(os.path.join(DATA, "stocks.json"))
    dg, _n, _m = DS.vd1_digest([s["t"] for s in S["stocks"]])
    if dg != DS.VD1_DIGEST:
        raise StopBake("V-D1 묶음 해시가 등록 값과 다르다")
    Wd = DS.build_world(with_vd1=True)
    W, P, CF = Wd["W"], Wd["P"], Wd["CF"]
    me, PX = W["me"], W["PX"]
    execs, n_drop, names = [], 0, []
    for f in DS.formations():
        i = me[f]
        pool, _k2t, _nl, _nk = DS.pool_at(W, f)
        lv = DS.leg(P, DS.STYLE_KEYS["V"], pool, i, CF)
        if not (lv["ok"] and lv["ok_n"][DS.NMAX]):
            raise StopBake("결정 %s 가치 다리를 채울 수 없다" % f)
        wv = DS.leg_weights(lv, NV, "cap")
        tgt, drop = DS.exec_target(PX, i + DS.EXEC_LAG, wv, None, 1.0)
        execs.append((i + DS.EXEC_LAG, tgt))
        n_drop += drop
        names.append(len(tgt))
    i0, iE = me[FORM_FIRST], me[HOLD[1]]
    wd = _win_dates(W, me)
    paths, turn = {}, {}
    for c in (0.0, COST, COST20):
        bp = DS.book_path(PX, execs, iE, c, i_window=i0)
        paths["%.4f" % c] = [float(bp["path"][i]) for i in range(i0, iE + 1)]
        turn["%.4f" % c] = float(bp["turn"])
    A = _json(os.path.join(DATA, "assets.json"))
    R, codes = r_states(DS, A)
    return {"kind": "egstep_vleg", "note": "🚨 가치 다리 일간 경로(수익) — 캐시 전용 · S 자식만 읽는다", "dates": wd, "paths": paths, "turn": turn,
            "R": R, "codes": codes, "n_exec": len(execs), "exec_drop": n_drop, "names_min": min(names), "names_max": max(names),
            "win_dates_sha": lines_sha(wd), "sec": round(time.time() - t0, 1)}


def judge_child(job):
    """판정(droot · 얼린 v_tests.holm) — S 자식 산출(스칼라 · 캐시)을 받아 Holm · 무해 · 지수 레버선 · 채택 표시 · 판정 · 읽기 · 예측 · 참고 줄."""
    t0 = time.time()
    assert_blobs(HERE, DROOT_BLOBS)
    S = _json(job["s_out"])
    if S.get("stopped"):
        return {"kind": "egstep_out", "stopped": S["stopped"]}
    M = {k: S[k] for k in ("window", "n_hold", "states", "arms", "delta", "primary", "placebo", "late", "pairing", "mean_share", "down", "cuts", "dil")
         if k in S}
    try:
        fam, gates, adopt, vd = judge_core(M)                  # 확증 통계 = 팔마다 제 역할(R: R 켜진 달 Δ_R · D · RD: Δ_down)
    except StopBake as e:
        return {"kind": "egstep_out", "stopped": str(e)[:300]}
    M.update({"family": fam, "gates": gates, "adopt": adopt, "verdict": vd})
    yw = {a: (M["arms"][a]["m"] or {}).get("years_won") for a in ("C0",) + PRIMARY}
    M["readings"] = readings(M["delta"], M["placebo"], yw, M.get("dil"), M.get("primary"))
    M["reading_flags"] = {a: reading_flags(M["readings"][a]) for a in PRIMARY}
    M["predictions"] = predictions(M)
    Q = _json(os.path.join(DATA, "_qbatch.json"))["V0"]
    M["refs"] = {"eg30_frozen": {k: Q["eval"].get(k) for k in ("ann_ex", "te", "ir", "nw_t", "win", "years_won", "n_years", "down_mean", "down_win",
                                                              "crash_won", "surge_won", "sleeve_beta")},
                 "eg30_frozen_mech": {k: (Q["eval"].get("mech") or {}).get(k) for k in ("crash_legs", "rebounds")}}
    M["multiplicity"] = {"m_confirmatory": len(PRIMARY), "alpha": HOLM_ALPHA, "cum_n_before": CUM_N_BEFORE, "rows_counted": N_ROWS_COUNTED,
                         "cum_n_after": CUM_N_BEFORE + N_ROWS_COUNTED, "counted": list(COUNTED)}
    M["kind"] = "egstep_out"
    M["sec"] = {"judge": round(time.time() - t0, 1), "s": S.get("sec")}
    return M


# ══════════════════════════════════════════════════════════════════════════
#  root 자식(얼린 V0 뿌리 · 1d81f083 build/ + bef4eea8 data/ + 940f0bda 가격 + P3) — F0 개수 · 동일성 · 굽기 S
# ══════════════════════════════════════════════════════════════════════════
def _root_ctx():
    assert_blobs(HERE, ROOT_BLOBS)
    import qbatch_core as Q
    import q_switch as SW
    import q_corrsurp as QC
    import x_adapter as XA
    bad = [k for k, v in Q06_EXPECT.items() if _norm(getattr(QC, k, None)) != _norm(v)]
    if bad:
        raise StopBake("얼린 q_corrsurp 상수가 등록 값과 다르다: %s" % bad)
    ctx = Q.Ctx()
    F = SW.frame(ctx)
    if list(F.months) != forms() or list(F.hold) != months_between(*HOLD):
        raise StopBake("틀의 결정 · 보유 달이 등록 창과 다르다")
    return Q, SW, QC, XA, ctx, F


def q06_states(QC, ctx, F):
    """Q06 상태(결정 달) — 얼린 q_corrsurp.states: st 0 = 수비(Signal) · s1 0 = HighMS · s2 0 = HighMS ∧ CS ≤ 1. 돌려주는 것 {달: 1 켜짐}."""
    st, s1, s2, _mon, _sig = QC.states(ctx)
    return ({m: int(st[m] == 0) for m in F.months}, {m: int(s1[m] == 0) for m in F.months}, {m: int(s2[m] == 0) for m in F.months})


def _v0_identity(Q, SW, XA, ctx, F, qjson):
    """C0 = 얼린 V0 — ① 목표 해시 둘 = QFWD 짝맞춤 표(x_adapter.V0_HASH_PIN) ② 몫 ≡ 1 의 mix_t1 펀드 월 초과 = 같은 뿌리에서 새로 지은 얼린 Ctx.V0()
    (최대 절대 차 ≤ 1e−10 · 배치 X 짝맞춤 B 와 같은 뜻) ③ = data/_qbatch.json V0.ex(저장 값이 소수 여섯째 자리로 반올림돼 있다 — 최대 절대 차 ≤ ½·10⁻⁶ + 1e−10)."""
    import numpy as np
    h = XA.v0_target_hashes(ctx.V0_targets)
    hash_ok = all(h[k] == XA.V0_HASH_PIN[k] for k in XA.V0_HASH_PIN)
    bE, bS = SW.offense_v0(ctx), SW.spy_book(ctx)
    fr = XA.mix_t1(F, np.ones(len(F.months)), bE, bS, COST, Q.fund_from_path)
    v0 = ctx.V0(basis="TR", cost=COST)
    fresh = float(np.max(np.abs(np.asarray(fr["ex"], float) - np.asarray(v0["ex"], float)))) if list(v0["hold"]) == list(fr["hold"]) else None
    V0 = _json(qjson)["V0"]
    same_hold = list(V0["hold"]) == list(fr["hold"])
    diff = float(np.max(np.abs(np.asarray(fr["ex"], float) - np.asarray(V0["ex"], float)))) if same_hold else None
    ok = bool(hash_ok and same_hold and fresh is not None and fresh <= V0_FRESH_TOL and diff is not None and diff <= V0_STORED_TOL)
    return {"hash_ok": bool(hash_ok), "same_hold": bool(same_hold), "fresh_max_abs_diff": fresh, "max_abs_diff": diff, "ok": ok}, bE, bS, fr


def f0s_child(job):
    """F0(root · 수익 없음 · 최종 합침) — Q06 시점(얼린 dry 의 단언) · 상태 개수 · 기록된 신호 달과 같은가 · V0 동일성(해시 · 최대 절대 차) ·
    뿌리 창 거래일 = droot 창 거래일 · D 목표 짝맞춤 A · 이름 수 · 옮긴 몫 · 얼린 하락월 개수 · 서명 · 등록 F0 대조."""
    import numpy as np
    t0 = time.time()
    Q, SW, QC, XA, ctx, F = _root_ctx()
    R0 = {"kind": "egstep_f0"}
    bad = []
    fv = _json(job["f0v"])
    R0["dstk"] = {k: fv.get(k) for k in ("dstk_ok", "dstk_bad", "dstk_expect_diff", "dstk_forms", "dstk_regime", "dstk_down")}
    if not fv.get("dstk_ok") or fv.get("dstk_expect_diff"):
        bad.append("DSTK F0(핀 판) 가 등록 서명과 다르다")
    try:
        dry = QC.dry(ctx)                                   # 얼린 단언: 결정 m 의 MonthMS · CS 는 그달 마지막 거래일 종가에서 닫힌다 · 두 격자 월말 같음
        R0["q06_dry"] = {"ok": True, "n_score_days": dry["n_score_days"], "n_months": dry["n_months"], "n_signal_months": dry["n_signal_months"],
                         "n_T1": dry["n_T1_months"], "n_T2": dry["n_T2_months"], "f0_ok": bool(dry["f0"]["ok"])}
    except AssertionError as e:
        R0["q06_dry"] = {"ok": False, "why": str(e)[:200]}
        bad.append("Q06 시점 단언 실패")
    Dq, T1, T2 = q06_states(QC, ctx, F)
    rec = (((_json(job["qbatch"]).get("cards") or {}).get("Q06") or {}).get("log") or {}).get("signal_months") or []
    mine = [m for m in F.months if Dq[m]]
    R0["q06_same_as_recorded"] = bool(mine == list(rec))
    if not R0["q06_same_as_recorded"]:
        bad.append("Q06 신호 달이 배치 Q 기록과 다르다")
    R = {m: int(fv["R"][m]) for m in F.months}
    R0["states"] = state_counts([R[m] for m in F.months], [Dq[m] for m in F.months], [T1[m] for m in F.months], [T2[m] for m in F.months])
    R0["r_codes"] = dict(collections.Counter(fv["codes"][m] for m in F.months))
    # R 겹침 맞춘 D 위약의 받아들임(상태 개수만 · 수익 없음) — 굽기와 같은 씨앗 · 같은 얼린 seg_shuffle 이라 굽기의 첫 뽑기들과 같다
    aR_ = np.array([R[m] for m in F.months], np.int8)
    aD_ = np.array([Dq[m] for m in F.months], np.int8)
    got, tries, ov = strat_placebo(SW, aR_, aD_, SEED_STRAT, N_STRAT_PROBE, N_STRAT_PROBE)
    R0["strat"] = {"overlap": ov, "probe": tries, "accepted": len(got)}
    del got
    vid, _bE, _bS, _fr = _v0_identity(Q, SW, XA, ctx, F, job["qbatch"])
    del _fr
    R0["v0_identity"] = vid
    if not vid["ok"]:
        bad.append("C0 가 얼린 V0 와 다르다(해시 · 경로)")
    G = ctx.G
    wd = [G.dates[i] for i in range(F.i0, F.iE + 1)]
    R0["grid"] = {"n_win_dates": len(wd), "same_as_droot": bool(lines_sha(wd) == fv.get("win_dates_sha") and len(wd) == fv.get("n_win_dates"))}
    if not R0["grid"]["same_as_droot"]:
        bad.append("뿌리 창 거래일이 DSTK 핀 판과 다르다")
    ME = _json(os.path.join(DATA, "mech_episodes.json"))
    hold = list(F.hold)
    fz = [h for h in ME["months"]["down_m"] if HOLD[0] <= h <= HOLD[1]]
    tr_neg = [h for h in hold if G.IX_TR[G.me[h]] / G.IX_TR[G.me[mshift(h, -1)]] - 1 < 0]
    R0["down"] = {"n_frozen": len(fz), "frozen_eq_spytr": bool(sorted(fz) == sorted(tr_neg)), "n_frozen_late": int(sum(1 for h in fz if h >= LATE_FROM)),
                  "n_late_months": int(sum(1 for h in hold if h >= LATE_FROM)), "n_pr": len(G.down_months(hold))}
    if not R0["down"]["frozen_eq_spytr"]:
        bad.append("얼린 하락월 = SPY TR < 0 이 아니다")
    dc = XA.d_check(job["d_targets"])
    D = _json(job["d_targets"])
    nn = [(D["months"].get(m) or {}).get("n") for m in F.months]
    R0["d_book"] = {"pairing_A": bool(dc["pairing_A_pass"]), "vb_books_sha_ok": bool(dc["vb_books_sha_ok"]), "n_with_target_all": dc["n_with_target"],
                    "max_w_le_cap": bool(dc["max_w_le_cap"]), "v_blobs_ok": bool(dc["v_blobs_ok"]), "sel_hash16": (dc.get("sel_hash") or "")[:16],
                    "names_min": (min(x for x in nn if x) if any(nn) else None), "names_max": (max(x for x in nn if x) if any(nn) else None),
                    "n_forms_with_target": int(sum(1 for x in nn if x))}
    del D
    sc = _json(job["s_cov"])
    R0["d_book"]["cov_ok_months"] = int(sc.get("n_ok") or 0)
    R0["d_book"]["cov_months"] = int(sc.get("n_months") or 0)
    if not (dc["pairing_A_pass"] and dc["max_w_le_cap"] and dc["v_blobs_ok"]) or R0["d_book"]["n_forms_with_target"] != N_HOLD:
        bad.append("D 목표 짝맞춤 A · 상한 · blob · 달 수")
    if R0["d_book"]["cov_ok_months"] != N_HOLD:
        bad.append("D 목표가 뿌리 World 로 옮겨지지 않은 달이 있다(K1 0.90)")
    R0["expect_keys"] = sorted(f0_signature(R0))
    if F0_EXPECT is not None:
        sig = f0_signature(R0)
        diff = sorted(k for k in set(sig) | set(F0_EXPECT) if sig.get(k) != F0_EXPECT.get(k))
        R0["expect_diff"] = diff
        if diff:
            bad.append("등록 F0 개수와 다름(%s)" % ", ".join(diff[:6]))
    R0["bad"] = bad
    R0["ok"] = not bad
    R0["sec"] = round(time.time() - t0, 1)
    return R0


def f0_signature(R0):
    """등록 커밋에 박는 F0 개수(정수 · 날짜 · 참/거짓 · 짧은 해시만 · 실수 없음) — 굽기 F0 가 같아야 표식을 쓴다."""
    st, dk, dn = R0["states"], R0["d_book"], R0["down"]
    return {"dstk_ok": bool(R0["dstk"]["dstk_ok"]), "dstk_valid": (R0["dstk"]["dstk_forms"] or {}).get("n_valid"),
            "r_value": (R0["dstk"]["dstk_regime"] or {}).get("value"), "r_same_as_t17": (R0["dstk"]["dstk_regime"] or {}).get("same_as_t17"),
            "q06_timing_ok": bool((R0.get("q06_dry") or {}).get("ok")), "q06_same_as_recorded": bool(R0["q06_same_as_recorded"]),
            "n_forms": st["n"], "r_on": st["r_on"], "d_on": st["d_on"], "both": st["both"], "r_only": st["r_only"], "d_only": st["d_only"],
            "neither": st["neither"], "r_switch": st["r_switch"], "d_switch": st["d_switch"], "r_on_runs": st["r_on_runs"], "d_on_runs": st["d_on_runs"],
            "t1_on": st["t1_on"], "t2_on": st["t2_on"], "v0_hash_ok": bool(R0["v0_identity"]["hash_ok"]), "v0_identity_ok": bool(R0["v0_identity"]["ok"]),
            "grid_same": bool(R0["grid"]["same_as_droot"]), "n_win_dates": R0["grid"]["n_win_dates"],
            "down_frozen": dn["n_frozen"], "down_frozen_late": dn["n_frozen_late"], "late_months": dn["n_late_months"], "down_pr": dn["n_pr"],
            "d_pairing_A": bool(dk["pairing_A"]), "d_forms": dk["n_forms_with_target"], "d_names_min": dk["names_min"], "d_names_max": dk["names_max"],
            "d_cov_ok": dk["cov_ok_months"], "d_sel_hash16": dk["sel_hash16"], "d_strat_acc": (R0.get("strat") or {}).get("accepted")}


def s_child(job):
    try:
        return _s_body(job)
    except StopBake as e:
        return {"kind": "egstep_s", "stopped": str(e)[:300]}


def _s_body(job):
    """🚨 굽기 본체(root) — 장부 넷 · 상태 개수 = 등록 F0 · 팔 17 · 10 · 20bp · 짝맞춤 E0 · E1 · 평가(얼린 qbatch_core.evaluate) · Δ ·
    확증 통계(팔마다 제 역할 — R 가족: R 켜진 달 · D · RD 가족: 얼린 하락월) · 상태별 자르기 · 같은 초과 희석 셋 · 위약 셋(D · R · R 겹침 맞춘 D ·
    R 은 Δ_R 도) · 부분 창. 산출은 캐시 작업 폴더에만."""
    import numpy as np
    import eg30plus as E
    t0 = time.time()
    Q, SW, QC, XA, ctx, F = _root_ctx()
    months, hold = list(F.months), list(F.hold)
    vid, bE, bS, fr0 = _v0_identity(Q, SW, XA, ctx, F, job["qbatch"])
    if not vid["ok"]:
        raise StopBake("C0 가 얼린 V0 와 다르다(짝맞춤 E0)")
    vbk = _json(job["v_book"])
    dbk = _json(job["d_book"])
    if list(dbk["months"]) != months:
        raise StopBake("D 책 달이 틀과 다르다")
    if not all(bool(x) for x in dbk["d_ok"]):
        raise StopBake("D 목표가 옮겨지지 않은 달(K1)")
    try:
        bV = XA._book_from_dates(SW, F, "V30", vbk)
        bD = XA._book_from_dates(SW, F, "D", dbk)
    except SystemExit as e:
        raise StopBake("장부 날짜가 뿌리 격자와 다르다: %s" % str(e)[:120])
    books = {"E": bE, "V": bV, "D": bD, "S": bS}
    Dq, T1, T2 = q06_states(QC, ctx, F)
    R = {m: int(vbk["R"][m]) for m in months}
    aR = np.array([R[m] for m in months], np.int8)
    aD = np.array([Dq[m] for m in months], np.int8)
    aT1 = np.array([T1[m] for m in months], np.int8)
    aT2 = np.array([T2[m] for m in months], np.int8)
    sc = state_counts(aR, aD, aT1, aT2)
    check_state_counts(sc, F0_EXPECT)                       # 굽기 상태 개수 = 등록 F0(§7-5) — 다르면 멈춘다
    SH = arm_shares(aR, aD, aT1, aT2)
    frs, frs20 = {}, {}
    for a in ARMS:
        frs[a] = run_arm(F, SH[a], books, COST, XA, Q)
        frs20[a] = run_arm(F, SH[a], books, COST20, XA, Q)
        if list(frs[a]["hold"]) != hold:
            raise StopBake("보유월이 창과 다르다(%s)" % a)
    # 짝맞춤 E1 — 두 장부 팔을 N 장부 식으로 다시 재면 얼린 mix_t1 과 같아야 한다(세 장부 팔의 식을 받친다)
    e1 = {}
    for a in ("C0", "R", "D", "R_SPY"):
        sh = SH[a]
        oth = [k for k in ("V", "D", "S") if k in sh] or ["S"]
        cols = ["E", oth[0], [k for k in ("V", "D") if k != oth[0]][0]]
        Mx = np.column_stack([sh["E"], (sh.get(oth[0]) if oth[0] in sh else np.zeros(len(months))), np.zeros(len(months))])
        frm = mix_t1_multi(F, Mx, [books[k] for k in cols], COST, Q.fund_from_path)
        e1[a] = float(np.max(np.abs(np.asarray(frm["ex"]) - np.asarray(frs[a]["ex"]))))
    pairing = {"E0_v0": vid, "E1_max_abs_diff": e1, "E1_ok": bool(max(e1.values()) <= 1e-10)}
    if not pairing["E1_ok"]:
        raise StopBake("짝맞춤 E1 실패(N 장부 식 ≠ 얼린 mix_t1)")
    # 평가
    dmask_pr = np.array([h in set(ctx.A.down_months(hold)) for h in hold])
    ME = _json(os.path.join(DATA, "mech_episodes.json"))
    fz = np.array([h in set(ME["months"]["down_m"]) for h in hold])
    crash = np.array([h in set(ME["months"]["crash_m"]) for h in hold])
    surge = np.array([h in set(ME["months"]["surge_m"]) for h in hold])
    keep = ("n", "ann_ex", "te", "ir", "t_iid", "nw_t", "down_n", "down_mean", "down_win", "up_mean", "win", "sleeve_beta", "years", "years_won",
            "n_years", "episodes", "crash_won", "surge_won", "mech", "halves", "blocks", "roll12", "down_capture", "up_capture")
    arms, delta = {}, {}
    ex0, ex020 = np.asarray(frs["C0"]["ex"], float), np.asarray(frs20["C0"]["ex"], float)
    for a in ARMS:
        ev = Q.evaluate(F.G, frs[a], dmask_pr)
        ex = np.asarray(frs[a]["ex"], float)
        arms[a] = {"m": {k: ev.get(k) for k in keep}, "turn": frs[a].get("turn"), "cost_drag": frs[a].get("cost_drag"),
                   "m20": {"ann_ex": float(np.asarray(frs20[a]["ex"]).mean() * 12), "nw_t": E.nw_t(np.asarray(frs20[a]["ex"], float))},
                   "down_frozen": {"n": int(fz.sum()), "mean": float(ex[fz].mean()), "win": float(np.mean(ex[fz] > 0) * 100)}}
    ev0 = arms["C0"]["m"]
    for a in ARMS:
        if a == "C0":
            continue
        dl = delta_stats(frs[a]["ex"], ex0, frs20[a]["ex"], ex020, fz, crash, surge, E)
        ya, y0 = arms[a]["m"]["years"] or {}, ev0["years"] or {}
        dl["years"] = {y: float(ya[y] - y0[y]) for y in sorted(set(ya) & set(y0))}
        e0 = {(e["kind"], e["name"]): e["ex"] for e in ev0["episodes"]}
        dl["episodes"] = [{"kind": e["kind"], "name": e["name"], "d": float(e["ex"] - e0[(e["kind"], e["name"])])}
                          for e in arms[a]["m"]["episodes"] if (e["kind"], e["name"]) in e0]
        delta[a] = dl
    # 상태별 자르기(보고 · 판정 아님) — 팔 − C0 를 R 켜짐 · D 켜짐 · D∧R · D∧¬R · R∧¬D · 둘 다 꺼짐 보유월로 가른다
    masks = state_masks(aR, aD)
    cuts = {a: state_cuts(np.asarray(frs[a]["ex"], float) - ex0, masks, fz, E) for a in CUT_ARMS}
    # 확증 통계(팔마다 제 역할 · 오케스트레이터 결정 ①) — 가족 R · D · RD 와 그 지수 레버 · 정적 혼합을 그 가족의 가면으로
    #   R 가족: R 켜진 보유월(결정 달 m 의 가치 국면 → 보유월 m+1 · 36) · D · RD 가족: 얼린 하락월 35
    pmask = {"r_on": aR > 0, "down": fz}
    fam_of = {x: fa for fa in PRIMARY for x in (fa, DIL_OF[fa], STAT_OF[fa])}
    primary = {x: dict(primary_stat(np.asarray(frs[x]["ex"], float) - ex0, pmask[ROLE[fa]], E), stat=ROLE[fa]) for x, fa in fam_of.items()}
    # 같은 초과 희석(배치 X DIL 규칙 · 보고 · 효율 읽기) — 팔마다 같은 연 초과를 내는 상수 c·EG30 + (1 − c)·SPY
    x_v0 = float(ex0.mean() * 12)
    dil = {}
    for a in PRIMARY:
        e_ann = float(delta[a]["all_mean_ann"])
        cd = dil_share(e_ann, x_v0)
        frd = XA.mix_t1(F, np.full(len(months), cd), bE, bS, COST, Q.fund_from_path)
        frd20 = XA.mix_t1(F, np.full(len(months), cd), bE, bS, COST20, Q.fund_from_path)
        dd = delta_stats(frd["ex"], ex0, frd20["ex"], ex020, fz, crash, surge, E)
        dil[a] = {"c": cd, "e_ann": e_ann, "turn": frd.get("turn"),
                  "delta": {k: dd[k] for k in ("down_mean", "down_t", "up_mean", "all_mean_ann", "all20_mean_ann", "crash_m_mean", "surge_m_mean")},
                  "prim": dict(primary_stat(np.asarray(frd["ex"], float) - ex0, pmask[ROLE[a]], E), stat=ROLE[a])}
    # 위약 — 상태(결정 달 0/1)의 구간 섞기(얼린 q_switch.seg_shuffle · 켜진 달 수 · 교체 수 보존) · 같은 크기 · 같은 목적지
    placebo = {}
    q = lambda xs, pc: float(np.percentile(np.asarray(xs), pc))

    def _pl_one(p, bk, f_):
        frp = XA.mix_t1(F, 1.0 - f_ * p.astype(float), bE, books[bk], COST, Q.fund_from_path)
        return placebo_stats(np.asarray(frp["ex"], float) - ex0, fz, p > 0)      # (Δ_down · 전 월 Δ · 그 뽑기의 켜진 달 평균)
    for nm, st, bk, f_, seed in (("D", aD, "D", F_D, SEED), ("R", aR, "V", F_R, SEED + 1)):
        rng = np.random.default_rng(seed)
        dn, al, ro = [], [], []
        for _ in range(K_PLACEBO):
            p = SW.seg_shuffle(st, rng)
            assert int(p.sum()) == int(st.sum()) and int(np.sum(p[1:] != p[:-1])) == int(np.sum(st[1:] != st[:-1]))
            x1, x2, x3 = _pl_one(p, bk, f_)
            dn.append(x1)
            al.append(x2)
            ro.append(x3)
        tr, ta = delta[nm]["down_mean"], delta[nm]["all_mean_ann"]
        placebo[nm] = {"k": K_PLACEBO, "seed": seed, "true_down": tr, "pct_down": pct_rank(dn, tr), "true_all": ta, "pct_all": pct_rank(al, ta),
                       "down_q": {"p05": q(dn, 5), "p50": q(dn, 50), "p95": q(dn, 95)}, "all_q": {"p05": q(al, 5), "p50": q(al, 50), "p95": q(al, 95)}}
        if nm == "R":                                       # R 의 확증 통계 Δ_R 위약(뽑기마다 제 켜진 달 · 읽기 ② 의 R · 오케스트레이터 결정 ①)
            trr = primary["R"]["mean"]
            placebo[nm].update({"role_stat": ROLE["R"], "true_role": trr, "pct_role": pct_rank(ro, trr),
                                "role_q": {"p05": q(ro, 5), "p50": q(ro, 50), "p95": q(ro, 95)}})
        del ro
    # R 겹침 맞춘 D 위약 — 같은 구간 섞기 뽑기 가운데 R 과의 겹침이 참(F0 12)과 같은 것만(켜진 달 · 교체 · R 겹침 보존 · K 에 못 닿으면 백분위 없음)
    got, tries, ov = strat_placebo(SW, aR, aD, SEED_STRAT, K_PLACEBO, STRAT_MAX_TRIES, lambda p: _pl_one(p, "D", F_D))
    dn, al = [g[0] for g in got], [g[1] for g in got]
    full = len(got) >= K_PLACEBO
    tr, ta = delta["D"]["down_mean"], delta["D"]["all_mean_ann"]
    placebo["D_R"] = {"k": len(got), "k_target": K_PLACEBO, "seed": SEED_STRAT, "tries": tries, "overlap": ov, "true_down": tr,
                      "pct_down": (pct_rank(dn, tr) if full else None), "true_all": ta, "pct_all": (pct_rank(al, ta) if full else None),
                      "down_q": ({"p05": q(dn, 5), "p50": q(dn, 50), "p95": q(dn, 95)} if full else None),
                      "all_q": ({"p05": q(al, 5), "p50": q(al, 50), "p95": q(al, 95)} if full else None)}
    del got, dn, al
    # 부분 창(보고만) — 같은 경로의 2019-06 ~ 보유월만
    lm = np.array([h >= LATE_FROM for h in hold])
    late = {"from": LATE_FROM, "window": [LATE_FROM, HOLD[1]], "n": int(lm.sum()), "n_down": int((fz & lm).sum()), "rows": {}}
    for a in PRIMARY + tuple(DIL_OF[x] for x in PRIMARY) + tuple(STAT_OF[x] for x in PRIMARY):
        d = np.asarray(frs[a]["ex"], float)[lm] - ex0[lm]
        f2 = fz[lm]
        pl2 = primary_stat(d, pmask[ROLE[fam_of[a]]][lm], E)                  # 그 가족의 확증 통계(부분 창 안 · 보고만)
        late["rows"][a] = {"down_mean": float(d[f2].mean()), "down_t": E.down_t(d, f2, DOWN_LAG), "all_mean_ann": float(d.mean() * 12), "all_nw_t": E.nw_t(d),
                           "prim": {"stat": ROLE[fam_of[a]], "n": pl2["n"], "mean": pl2["mean"], "t": pl2["t"]}}
    out = {"kind": "egstep_s", "window": list(HOLD), "n_hold": len(hold), "states": sc, "arms": arms, "delta": delta, "primary": primary, "cuts": cuts, "dil": dil,
           "placebo": placebo, "late": late, "pairing": pairing, "mean_share": {a: mean_share(SH[a]) for a in ARMS},
           "down": {"n_frozen": int(fz.sum()), "n_pr": int(dmask_pr.sum()), "n_crash_m": int(crash.sum()), "n_surge_m": int(surge.sum())},
           "series": {"hold": hold, "ex": {a: [float(x) for x in frs[a]["ex"]] for a in ARMS}, "ex20": {a: [float(x) for x in frs20[a]["ex"]] for a in ARMS},
                      "R": [int(x) for x in aR], "D": [int(x) for x in aD]},
           "sec": round(time.time() - t0, 1)}
    return out


# ══════════════════════════════════════════════════════════════════════════
def child_main(argv):
    """러너가 부른다: python -X utf8 <뿌리>/build/egstep.py --child f0v|f0s|vleg|s|judge --job <작업 파일> --out <경로>."""
    mode = argv[argv.index("--child") + 1]
    job = _json(argv[argv.index("--job") + 1])
    outp = argv[argv.index("--out") + 1]
    import warnings
    warnings.simplefilter("ignore")
    import numpy as np
    fn = {"f0v": f0v_child, "f0s": f0s_child, "vleg": vleg_child,"s": s_child, "judge": judge_child}.get(mode)
    if fn is None:
        raise SystemExit("모르는 자식 방식: %s" % mode)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        try:
            res = fn(job)
        except StopBake as e:
            if mode in ("s", "judge", "vleg"):
                res = {"kind": "egstep_%s" % mode, "stopped": str(e)[:300]}
            else:
                raise
    _wjson(outp, _clean(res))
    return 0


def _clean(o, depth=0):
    """JSON 으로(NaN · inf → None · numpy → 파이썬 · 튜플 → 목록 · 집합 → 정렬 목록)."""
    if depth > 60:
        return str(o)
    if o is None or isinstance(o, (str, bool)):
        return o
    if isinstance(o, int):
        return int(o)
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    try:
        import numpy as np
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            f = float(o)
            return f if math.isfinite(f) else None
        if isinstance(o, np.ndarray):
            return _clean(o.tolist(), depth + 1)
    except Exception:                                        # noqa: BLE001
        pass
    if isinstance(o, dict):
        return {str(k): _clean(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v, depth + 1) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(_clean(v, depth + 1) for v in o)
    return str(o)


if __name__ == "__main__":
    if "--child" in sys.argv:
        sys.exit(child_main(sys.argv))
    print(__doc__)
