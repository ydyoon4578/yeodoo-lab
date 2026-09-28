# -*- coding: utf-8 -*-
"""build/ssdix.py — 확률지배(SSD) 지수 강화 책 역할 검정(SSDIX) 계산 엔진.
러너(build/ssdix_run.py)가 핀 판 임시 뿌리 셋(EGSTEP 과 같은 뿌리 — 얼린 x_adapter.build_root · build_vroot · dstk_run.materialize) 안에서
자식 과정으로 부른다(이 파일은 뿌리마다 build/ 에 복사된다).

사전등록: build/PREREG-<등록 날짜>-SSDIX.md 하나(글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).

무엇을 재나(역할 검정 둘 · 확증 가족 = (A) 하나(m 1 · 한쪽 α 0.05 · 얼린 v_tests.holm) · (B) 는 등록 읽기 — 판정을 바꾸지 못한다)
  SSD 책   월말 d_m 마다 직전 200 거래일의 종목 일간 총수익(시나리오 S = 200 · 같은 날 SPY 총수익이 기준 분포)으로
           척도 2차 확률지배(scaled SSD · Fábián 외 2011 · Valle · Beasley 2026 의 200일 · 21일 틀) LP 를 푼다:
             최대화 V · Σw = 1 · 0 ≤ w ≤ 0.20 · 모든 s = 1 … 200 에서 (가장 나쁜 s 날의 합)(포트) ≥ (가장 나쁜 s 날의 합)(SPY) + s·V
           풀이 = 절단면(Fábián · Mitra · Roman 2011) · SciPy HiGHS 쌍대 단체법 · 동률 해소(랩 선택) = V ≥ V* − 1e−6(%/일) 에서 직전 보유(흘린 비중)
           대비 ℓ1 회전 최소 · 우주 = PIT S&P 500 ∪ NASDAQ 100(얼린 v_pit.Universe · 회사당 한 줄) 가운데 201 가격이 모두 선 이름 · 현금 없음 ·
           체결 T+1 종가(DSTK book_path 규약 — 체결 날 가격 없는 이름은 빼고 비례로 다시 나눈다) · 편도 10bp(20bp 판).
  (A) 독립 엔진   펀드 F = 0.9 × SPY TR + 0.1 × SSD 슬리브 · H1: 얼린 하락월 35 에서 같은 사전 β̂ 의 희석 쌍둥이보다 덜 잃는다 —
           Δ_A = 하락월 평균(X_SSD − X_DIL) · X = 펀드 월 수익 − SPY TR(%p) · 쌍둥이 슬리브 = β̂_k·SPY + (1 − β̂_k)·T-bill(측정용 항등식 · 비용 없음 ·
           β̂ = 얼린 v_pit.beta_fp 보유가중 · 없으면 1.0 · 체결 T+1 에 바뀐다).
  (B) 방어 스텝 목적지   얼린 EGSTEP RD 규칙 그대로(egstep.arm_shares · 방어 먼저 · 스텝 몫 합 ≤ ½) · D 자리의 책만 V02 D 책 → SSD 책 —
           Δ_B = 하락월 평균(X_RD-SSD − X_RD) · RD = 얼린 EGSTEP RD(짝맞춤 E-RD: EGSTEP 굽기 산출과 같아야 한다).
  t = 얼린 eg30plus.down_t(달력 HAC · Bartlett 3) · p = t(34) 위 꼬리 · Holm(얼린 v_tests.holm · m 1).
  (B) 를 확증에서 뺀 까닭(리드 결정 · 등록 전): RD 와 D 자리의 책이 달라지는 하락월이 약 7 개뿐이라 참 효과가 있어도 검정력 ≈ 0.05 —
  가족에 두면 (A) 의 α 만 깎는다. (B) 는 같은 식으로 계산해 읽기로 싣고(명목 참/거짓 · 관문) 가족 · 채택 표시 · 판정에 넣지 않는다.
  관문 — (A): G0 EG30 독립(G-EGD 수 둘 · 수익 전) · G1 반등 청구 · G2 연 80% 하한 > −0.15%p · G3 20bp 부호 · G4 네 토막 ≥ 3 ·
           G5 무작위 포트 위약 백분위 ≥ 95 · G6 French 49 산업 20년 기전 층(Δ > 0 ∧ t ≥ 1).  (B): 무해(20bp 전 월 Δ ≥ 0 · 반등 ≥ RD − 1 ·
           회전 ≤ 10) · 쌍둥이선(D 자리를 SSD 의 같은 β̂ 쌍둥이로 옮긴 RD-TWIN 보다 하락월 · 20bp 전 월 모두 낫다).
  대조(측정만) C0 지수 레버 · C1 쌍둥이 · C2 V02 D 책 홀로 · C3 평균 맞춘 최소 MAD(분산의 LP 대리) · C4 비척도 SSD · C5 평균 제약 5% CVaR ·
           C7a 동일가중 우주 · C7b 시총가중 우주 · C10 섹터 ±5%(상대) SSD · 앞 창 2015-04 ~ 2016-08(보고만).

🚨 랩 규율: 수익 경로를 만드는 자식(books · s · g6 굽기 · judge)은 등록 커밋이 origin 에 오른 뒤 러너의 한 번 굽기와 눈가린 연기에서만 돈다.
   targets · f0r · g6 F0 는 개수 · 날짜 · 해시 · 참/거짓 · 비중 통계(G0)만 돌려준다 — 보유 수익 · 초과 · IR · Δ · 적중 통계 없음.
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
S_WIN = 200                            # 시나리오 창(거래일) — Valle · Beasley(2026) 200일 · 21일 틀(문헌값)
CAP = 0.20                             # 이름 상한(랩 D 책과 같다 · 문헌은 상한 없음 — 랩 이탈 ①)
TIE_EPS = 1e-6                         # 동률 해소: V ≥ V* − 1e−6(%/일) · C3/C5 는 목적 값 ± s·1e−6(합 단위)
CUT_TOL = 1e-9                         # 절단면 위반 문턱(% 합 단위)
CUT_ROUND = 30                         # 한 번에 더하는 가장 크게 어긴 수준 수
CUT_MAX_IT = 400                       # 단계마다 절단면 되풀이 상한(넘으면 그달 풀이 실패 → 앞 달 목표를 잇는다 · 개수 공개)
W_ZERO = 1e-6                          # 해의 부스러기(1e−6 미만) 0 · 다시 합 1 · 상한 되맞춤
LP_METHOD = "highs-ds"                 # SciPy linprog HiGHS 쌍대 단체법(결정적)
LP_OPTS = {"presolve": True, "time_limit": 600.0, "primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}
SEED_LEVELS = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144)   # 첫 절단면(기준 분포 차례의 가장 나쁜 s 날 · 로그 격자) + s = 200(평균)
CVAR_S = 10                            # C5 — 5% CVaR = 200 날 가운데 가장 나쁜 10 날
SECTOR_BAND = 0.05                     # C10 — 섹터 비중을 우주 시총 섹터 비중의 ±5%(상대 폭) 안에(Valle · Beasley · Meade)
HOLD = ("2016-09", "2026-08")
N_HOLD = 120
FORM_WARM, FORM_FIRST, FORM_LAST = "2016-07", "2016-08", "2026-07"
PRE_HOLD = ("2015-04", "2016-08")      # 앞 창(보고만 · 판정 밖) — 따로 짓는 사슬(주 사슬과 섞이지 않는다)
PRE_WARM, PRE_FIRST, PRE_LAST = "2015-02", "2015-03", "2016-07"
G6_HOLD = ("2006-09", "2026-08")       # 기전 층(French 49 산업 가치가중 · 기준 French 시장) — 20년 규칙 안
G6_WARM, G6_FIRST, G6_LAST = "2006-07", "2006-08", "2026-07"
COST = 0.0010
COST20 = 0.0020
PRIMARY = ("A",)                       # 확증 가족(m 1)
READING_ARMS = ("B",)                  # 등록 읽기(판정 밖) — RD 와 달라지는 하락월 ≈ 7 · 검정력 ≈ 0.05
HOLM_ALPHA = 0.05
DOWN_LAG = 3
K_PLACEBO = 1000
SEED_PLACEBO = 20260930
BETA_BAND = 0.01                       # G5 — 무작위 포트의 사전 β̂ 를 SSD 의 것 ±0.01 안에(지수 기울기 이분법)
PLACEBO_TRIES = 50
PLACEBO_LAMBDA = 60.0
G0_CORR_MAX, G0_OVX_MAX = 0.30, 0.10   # G-EGD(v_cmp 문턱 그대로) — 능동비중 상관 · 겹침 초과의 달별 중앙값
G2_LB = -0.15                          # G2 — 펀드 틀 연 X_SSD 의 80% 한쪽 하한 > −0.15%p(배치 X E4 식)
Z80 = 0.8416
G4_MIN = 3                             # G4 — 30개월 토막 넷 가운데 Δ_A > 0 인 토막 ≥ 3
BLOCK_LEN = 30
G5_PCT = 95.0
G6_T_MIN = 1.0
TURN_MAX = 10.0
REB_SLACK = 1
FP_WIN, FP_MIN, FP_K, FP_W = 252, 200, 5, 0.5            # French 층 β̂ — v_pit.beta_fp 와 같은 식(252 · ≥ 200 · Dimson 5 · 축소 0.5)
LP_VARIANTS = ("SSD", "C10", "C4", "C3", "C5")           # 주 사슬 LP 판(SSD = 주 · 나머지 대조)
BASKETS = ("C7A", "C7B")
CHAINS = ("SSD", "PRE", "C10", "C4", "C3", "C5")          # PRE = 앞 창 SSD 사슬
CUM_N_BEFORE = 1063                    # 누적 N 기저(Q06HOLD 결과 문서의 1,058 → 1,063 · 리드 결정) — 이 등록이 센 줄을 더한다
COUNTED = ("A", "B", "C3", "C4", "C5", "C7A", "C10", "G6")
N_ROWS_COUNTED = 8
N_WORKERS = 5                          # 풀이 과정 수(속도만 — 해는 과정 수와 무관하다 · 등록 상수 아님)
EGSTEP_ENGINE_BLOB = "2749cbe238910e78e5ab4e36a98969b1553a7444"   # build/egstep.py(EGSTEP 등록 판) — 뿌리에서 단언
# 뿌리마다 build/ 에서 단언하는 얼린 blob(LF 바이트의 git blob sha1)
ROOT_BLOBS = {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
              "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
              "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2",
              "egstep": EGSTEP_ENGINE_BLOB}
VROOT_BLOBS = {"v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689", "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a",
               "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e", "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
               "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38", "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b",
               "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513", "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
               "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628", "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d",
               "v_tests": "2f1ec4db1cd7458564da73ec5ad88cef8a0b2f2f", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"}
FRENCH_FILES = {"ind49_d": ("49_Industry_Portfolios_daily_CSV.zip", "8f394fe34bea54d41b9aafed410425ee8f8e252ede3c71a7c1cd20bab83040de"),
                "ff3_d": ("F-F_Research_Data_Factors_daily_CSV.zip", "2f29e22546069914890a712680a6f81f3680ebc3543b52864484d209ca13a7db")}
FRENCH_VINTAGE = "202608"              # 두 파일 머리의 «202608 CRSP»
# 등록 F0 개수(러너 --f0 가 핀 뿌리 셋으로 센 값 · 수익 없음) — 굽기 F0 가 같아야 표식을 쓴다(첫 F0 전에는 None)
F0_EXPECT = {'egstep_f0_ok': True, 'g0_corr_x1000': -14, 'g0_months': 120, 'g0_ovx_x1000': -89, 'g0_pass': True, 'g6_carried': 0, 'g6_drops': 0, 'g6_elig_max': 49, 'g6_elig_min': 49, 'g6_first': '2005-01-03', 'g6_forms': 241, 'g6_hash16': 'ab1d973c4f8910b0', 'g6_last': '2026-08-31', 'g6_n_missing_cells': 0, 'g6_names_max': 15, 'g6_names_min': 6, 'g6_ok1': 241, 'g6_ok2': 241, 'g6_ties_gt5pct': 6, 'g6_vintage_ok': True, 'grid_same': True, 'n_eg_forms': 41, 'n_win_dates': 2513, 'spy_same': False, 't_C10_carried': 0, 't_C10_drops': 6, 't_C10_hash16': '93b695d15088abc5', 't_C10_names_max': 39, 't_C10_names_min': 13, 't_C10_ok1': 121, 't_C10_ok2': 121, 't_C10_tie_max_x1000': 52, 't_C10_tie_med_x1000': 11, 't_C10_ties_gt5pct': 1, 't_C3_carried': 0, 't_C3_drops': 6, 't_C3_hash16': 'da745ccf2970068e', 't_C3_names_max': 69, 't_C3_names_min': 17, 't_C3_ok1': 121, 't_C3_ok2': 121, 't_C3_tie_max_x1000': 87, 't_C3_tie_med_x1000': 15, 't_C3_ties_gt5pct': 7, 't_C4_carried': 0, 't_C4_drops': 7, 't_C4_hash16': '421ec4c0e8d91648', 't_C4_names_max': 42, 't_C4_names_min': 8, 't_C4_ok1': 121, 't_C4_ok2': 121, 't_C4_tie_max_x1000': 302, 't_C4_tie_med_x1000': 79, 't_C4_ties_gt5pct': 84, 't_C5_carried': 0, 't_C5_drops': 4, 't_C5_hash16': 'e290e106772e8d7f', 't_C5_names_max': 46, 't_C5_names_min': 10, 't_C5_ok1': 121, 't_C5_ok2': 121, 't_C5_tie_max_x1000': 147, 't_C5_tie_med_x1000': 2, 't_C5_ties_gt5pct': 3, 't_C7A_carried': 0, 't_C7A_drops': 51, 't_C7A_hash16': '19e2f00855d94653', 't_C7A_names_max': 511, 't_C7A_names_min': 461, 't_C7B_carried': 0, 't_C7B_drops': 50, 't_C7B_hash16': 'b70bc68c2d5c696b', 't_C7B_names_max': 511, 't_C7B_names_min': 459, 't_PRE_carried': 0, 't_PRE_drops': 1, 't_PRE_hash16': '466d36d9de0868c8', 't_PRE_names_max': 21, 't_PRE_names_min': 6, 't_PRE_ok1': 18, 't_PRE_ok2': 18, 't_PRE_tie_max_x1000': 36, 't_PRE_tie_med_x1000': 13, 't_PRE_ties_gt5pct': 0, 't_SSD_carried': 0, 't_SSD_drops': 4, 't_SSD_hash16': '376eb2b46e2174b0', 't_SSD_names_max': 35, 't_SSD_names_min': 6, 't_SSD_ok1': 121, 't_SSD_ok2': 121, 't_SSD_tie_max_x1000': 41, 't_SSD_tie_med_x1000': 10, 't_SSD_ties_gt5pct': 0, 't_beta_missing_elig_max': 0, 't_cov_med_x1000': 973, 't_cov_min_x1000': 895, 't_covw_min_x1000': 985, 't_elig_max': 511, 't_elig_med': 501, 't_elig_min': 461, 't_exec_bad_max': 37, 't_members_max': 521, 't_members_min': 509, 't_months_cov_lt90': 1, 't_n_forms_main': 121, 't_n_forms_pre': 18, 't_placebo_fallback': 2576, 't_placebo_hash16': '680f7bb04eab2d7f', 't_sec_none_max': 10, 'v0_hash_ok': True}

ARM_LABEL = {"SSD": "SSD 책(척도 SSD · 200일 · 상한 20%)", "DIL": "희석 쌍둥이(같은 사전 β̂ · SPY + T-bill 항등식)",
             "C2": "C2 V02 D 책 홀로", "C3": "C3 평균 맞춘 최소 MAD", "C4": "C4 비척도 SSD", "C5": "C5 평균 제약 5% CVaR",
             "C7A": "C7a 동일가중 우주", "C7B": "C7b 시총가중 우주(상한 20%)", "C10": "C10 섹터 ±5% SSD",
             "RD": "RD(얼린 EGSTEP · D 자리 = V02 D 책)", "RDSSD": "RD-SSD(D 자리 = SSD 책)", "RDTWIN": "RD-TWIN(D 자리 = SSD 의 β̂ 쌍둥이)",
             "C0": "C0 EG30 V0(참고)"}


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


def chain_forms(chain):
    """사슬의 결정 달 — 첫 달은 데우기(그 체결로 창 첫날에 책이 이미 든다 · DSTK FORM_WARM 규약)."""
    if chain == "PRE":
        return months_between(PRE_WARM, PRE_LAST)
    return months_between(FORM_WARM, FORM_LAST)


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
    """build_dir 의 모듈 blob(LF 바이트)이 등록 값과 같아야 한다 — 다르면 멈춘다(부르지 않는다)."""
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


def canon_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")).hexdigest()


def _tk(t):
    return (t or "").replace(".", "-")


# ══════════════════════════════════════════════════════════════════════════
#  LP — 척도 · 비척도 SSD(절단면) · 평균 제약 CVaR · 평균 맞춘 최소 MAD(모두 두 단계 · 순수 함수 · 합성 selftest)
#  단위: 시나리오 수익은 % (R · b × 100) — 풀이기 허용오차(1e−9)가 값의 크기에 비해 충분히 작도록.
# ══════════════════════════════════════════════════════════════════════════
def _lp(c, A_ub, b_ub, A_eq, b_eq, bounds):
    from scipy.optimize import linprog
    return linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method=LP_METHOD, options=dict(LP_OPTS))


def level_coef(S, scaled):
    """수준 s 의 V 계수 — 척도 판 a_s = s(«가장 나쁜 s 날의 평균» 개선이 모든 s 에서 V) · 비척도 판 a_s = S(꼬리 합 개선이 모든 s 에서 V/S … 같은 V)."""
    import numpy as np
    s = np.arange(1, S + 1, dtype=float)
    return s if scaled else np.full(S, float(S))


def ssd_violation(y, bsum, a, V):
    """수준마다 (기준의 가장 나쁜 s 날 합 + a_s·V) − (포트의 가장 나쁜 s 날 합) — 모두 ≤ 0 이면 지배 조건이 선다. (위반 배열, 포트 차례)."""
    import numpy as np
    y = np.asarray(y, float)
    order = np.argsort(y, kind="mergesort")
    cs = np.cumsum(y[order])
    return (bsum + a * V) - cs, order


def ssd_value(y, b, scaled=True):
    """V(y) = min_s [(포트 가장 나쁜 s 날 합 − 기준 가장 나쁜 s 날 합) / a_s] — 정렬로 잰 참값(selftest · 해 점검)."""
    import numpy as np
    S = len(b)
    a = level_coef(S, scaled)
    cy = np.cumsum(np.sort(np.asarray(y, float)))
    cb = np.cumsum(np.sort(np.asarray(b, float)))
    return float(np.min((cy - cb) / a))


class _Cuts:
    """절단면 (J, s): −Σ_{t∈J} y_t + a_s·V ≤ −(기준 가장 나쁜 s 날 합) — y · V 위의 성긴 행(Fábián · Mitra · Roman 2011)."""

    def __init__(self, iy, iV, a, bsum):
        self.iy, self.iV, self.a, self.bsum = iy, iV, a, bsum
        self.r, self.c, self.v, self.b = [], [], [], []
        self.keys = set()
        self.J = []
        self.n = 0

    def add(self, J, s):
        import numpy as np
        J = np.sort(np.asarray(J, np.int64))
        key = (int(s), J.tobytes())
        if key in self.keys:
            return False
        self.keys.add(key)
        r = self.n
        self.r.extend([r] * (len(J) + 1))
        self.c.extend((self.iy + J).tolist() + [self.iV])
        self.v.extend([-1.0] * len(J) + [float(self.a[s - 1])])
        self.b.append(-float(self.bsum[s - 1]))
        self.J.append((int(s), J))
        self.n += 1
        return True

    def matrix(self, nv):
        import numpy as np
        import scipy.sparse as sp
        return sp.csr_matrix((self.v, (self.r, self.c)), shape=(self.n, nv)), np.array(self.b, float)


def _eq_block(R, nv, iw, iy):
    """y − R w = 0 · Σw = 1."""
    import numpy as np
    import scipy.sparse as sp
    S, N = R.shape
    Rc = sp.coo_matrix(R)
    rows = np.concatenate([Rc.row, np.arange(S), np.full(N, S)])
    cols = np.concatenate([iw + Rc.col, iy + np.arange(S), iw + np.arange(N)])
    vals = np.concatenate([-Rc.data, np.ones(S), np.ones(N)])
    A = sp.csr_matrix((vals, (rows, cols)), shape=(S + 1, nv))
    b = np.zeros(S + 1)
    b[S] = 1.0
    return A, b


def _band_block(groups, lo, hi, nv, iw):
    """섹터 띠 lo_g ≤ Σ_{i∈g} w_i ≤ hi_g — ≤ 행 둘씩."""
    import numpy as np
    import scipy.sparse as sp
    rows, cols, vals, rhs = [], [], [], []
    r = 0
    for g in sorted(lo):
        idx = [i for i, gg in enumerate(groups) if gg == g]
        rows += [r] * len(idx)
        cols += [iw + i for i in idx]
        vals += [1.0] * len(idx)
        rhs.append(hi[g])
        r += 1
        rows += [r] * len(idx)
        cols += [iw + i for i in idx]
        vals += [-1.0] * len(idx)
        rhs.append(-lo[g])
        r += 1
    return sp.csr_matrix((vals, (rows, cols)), shape=(r, nv)), np.array(rhs, float)


def _l1_block(N, n_mid, p):
    """ℓ1 회전: u ≥ w − p · u ≥ p − w (변수 차례 w · [가운데 n_mid] · u)."""
    import numpy as np
    import scipy.sparse as sp
    I = sp.identity(N, format="csr")
    Z = sp.csr_matrix((N, n_mid))
    E = sp.vstack([sp.hstack([I, Z, -I]), sp.hstack([-I, Z, -I])]).tocsr()
    return E, np.concatenate([p, -p])


def ssd_stage1(R, b, cap=CAP, scaled=True, band=None):
    """1단계 — 최대 V(절단면 · HiGHS). 돌려주는 것 {status, rounds, V, w, cuts(묶인 절단면 [(s, J)]), n_cuts, viol, sec}.
    status 0 = 최적 · 99 = 되풀이 상한 · 그 밖 = HiGHS 상태."""
    import numpy as np
    import scipy.sparse as sp
    t0 = time.time()
    R = np.asarray(R, float)
    b = np.asarray(b, float)
    S, N = R.shape
    a = level_coef(S, scaled)
    bsum = np.cumsum(np.sort(b))
    iw, iy, iV = 0, N, N + S
    nv = N + S + 1
    cuts = _Cuts(iy, iV, a, bsum)
    cuts.add(np.arange(S), S)
    ob = np.argsort(b, kind="mergesort")
    for s in SEED_LEVELS:
        if s < S:
            cuts.add(ob[:s], s)
    c = np.zeros(nv)
    c[iV] = -1.0
    bnd = [(0.0, cap)] * N + [(None, None)] * S + [(None, None)]
    Aeq, beq = _eq_block(R, nv, iw, iy)
    bb = _band_block(*band, nv, iw) if band is not None else None
    it = 0
    while True:
        it += 1
        Aub, bub = cuts.matrix(nv)
        if bb is not None:
            Aub = sp.vstack([Aub, bb[0]]).tocsr()
            bub = np.concatenate([bub, bb[1]])
        res = _lp(c, Aub, bub, Aeq, beq, bnd)
        if res.status != 0:
            return {"status": int(res.status), "rounds": it, "sec": time.time() - t0}
        w = res.x[:N]
        V = float(res.x[iV])
        y = R @ w
        viol, order = ssd_violation(y, bsum, a, V)
        idx = np.flatnonzero(viol > CUT_TOL)
        idx = idx[np.argsort(-viol[idx], kind="mergesort")][:CUT_ROUND]
        added = sum(cuts.add(order[: j + 1], j + 1) for j in idx)
        if added == 0:
            break
        if it >= CUT_MAX_IT:
            return {"status": 99, "rounds": it, "sec": time.time() - t0}
    # 묶인 절단면(여유 ≤ 1e−7) — 2단계 씨앗
    bind = []
    for (s, J) in cuts.J:
        slack = float(y[J].sum()) - float(bsum[s - 1] + a[s - 1] * V)
        if slack <= 1e-7:
            bind.append((s, J))
    return {"status": 0, "rounds": it, "V": V, "w": w.copy(), "cuts": bind, "n_cuts": cuts.n, "viol": float(np.max(viol)), "sec": time.time() - t0}


def ssd_stage2(R, b, V_star, prev, seed_cuts=(), w1=None, cap=CAP, scaled=True, band=None):
    """2단계(동률 해소 · 랩 선택) — V ≥ V* − TIE_EPS 에서 Σ|w − prev| 최소(절단면을 이어 더한다). 씨앗 = 1단계 묶인 절단면 + w1 차례의 모든 수준."""
    import numpy as np
    import scipy.sparse as sp
    t0 = time.time()
    R = np.asarray(R, float)
    b = np.asarray(b, float)
    S, N = R.shape
    a = level_coef(S, scaled)
    bsum = np.cumsum(np.sort(b))
    iw, iy, iV, iu = 0, N, N + S, N + S + 1
    nv = N + S + 1 + N
    cuts = _Cuts(iy, iV, a, bsum)
    for (s, J) in seed_cuts:
        cuts.add(J, s)
    if w1 is not None:
        o1 = np.argsort(R @ np.asarray(w1, float), kind="mergesort")
        for s in range(1, S + 1):
            cuts.add(o1[:s], s)
    else:
        cuts.add(np.arange(S), S)
    p = np.asarray(prev, float)
    c = np.zeros(nv)
    c[iu:iu + N] = 1.0
    bnd = [(0.0, cap)] * N + [(None, None)] * S + [(V_star - TIE_EPS, None)] + [(0.0, None)] * N
    Aeq, beq = _eq_block(R, nv, iw, iy)
    E, Eb = _l1_block(N, S + 1, p)
    bb = _band_block(*band, nv, iw) if band is not None else None
    it = 0
    while True:
        it += 1
        Aub, bub = cuts.matrix(nv)
        Aub = sp.vstack([Aub, E] + ([bb[0]] if bb is not None else [])).tocsr()
        bub = np.concatenate([bub, Eb] + ([bb[1]] if bb is not None else []))
        res = _lp(c, Aub, bub, Aeq, beq, bnd)
        if res.status != 0:
            return {"status": int(res.status), "rounds": it, "sec": time.time() - t0}
        w = res.x[:N]
        V = float(res.x[iV])
        viol, order = ssd_violation(R @ w, bsum, a, V)
        idx = np.flatnonzero(viol > CUT_TOL)
        idx = idx[np.argsort(-viol[idx], kind="mergesort")][:CUT_ROUND]
        added = sum(cuts.add(order[: j + 1], j + 1) for j in idx)
        if added == 0:
            break
        if it >= CUT_MAX_IT:
            return {"status": 99, "rounds": it, "sec": time.time() - t0}
    return {"status": 0, "rounds": it, "w": w.copy(), "V": V, "viol": float(np.max(viol)), "l1": float(np.abs(w - p).sum()), "sec": time.time() - t0}


def cvar_solve(R, b, prev=None, s_level=CVAR_S, cap=CAP, obj_star=None):
    """C5 — 평균 제약(Σy ≥ Σb) 아래 가장 나쁜 s 날 합 최대(= 5% CVaR 최소 · Rockafellar · Uryasev 선형화).
    obj_star 가 없으면 1단계(최대화) · 있으면 2단계(목적 ≥ obj* − s·TIE_EPS 에서 Σ|w − prev| 최소)."""
    import numpy as np
    import scipy.sparse as sp
    t0 = time.time()
    R = np.asarray(R, float)
    b = np.asarray(b, float)
    S, N = R.shape
    iw, iy, ie, idd = 0, N, N + S, N + S + 1
    two = obj_star is not None
    iu = idd + S
    nv = iu + (N if two else 0)
    Aeq, beq = _eq_block(R, nv, iw, iy)
    q = np.arange(S)
    # η − y_t − d_t ≤ 0
    A1 = sp.csr_matrix((np.concatenate([np.ones(S), -np.ones(S), -np.ones(S)]),
                        (np.concatenate([q, q, q]), np.concatenate([np.full(S, ie), iy + q, idd + q]))), shape=(S, nv))
    # 평균: −Σy ≤ −Σb
    A2 = sp.csr_matrix((-np.ones(S), (np.zeros(S, int), iy + q)), shape=(1, nv))
    rows = [A1, A2]
    rhs = [np.zeros(S), np.array([-float(b.sum())])]
    bnd = [(0.0, cap)] * N + [(None, None)] * S + [(None, None)] + [(0.0, None)] * S
    if not two:
        c = np.zeros(nv)
        c[ie] = -float(s_level)
        c[idd:idd + S] = 1.0
    else:
        # −(s η − Σd) ≤ −(obj* − s·TIE_EPS)
        A3 = sp.csr_matrix((np.concatenate([[-float(s_level)], np.ones(S)]), (np.zeros(S + 1, int), np.concatenate([[ie], idd + q]))), shape=(1, nv))
        rows.append(A3)
        rhs.append(np.array([-(obj_star - s_level * TIE_EPS)]))
        E, Eb = _l1_block(N, S + 1 + S, np.asarray(prev, float))
        rows.append(E)
        rhs.append(Eb)
        bnd = bnd + [(0.0, None)] * N
        c = np.zeros(nv)
        c[iu:iu + N] = 1.0
    res = _lp(c, sp.vstack(rows).tocsr(), np.concatenate(rhs), Aeq, beq, bnd)
    if res.status != 0:
        return {"status": int(res.status), "rounds": 1, "sec": time.time() - t0}
    w = res.x[:N]
    obj = float(s_level * res.x[ie] - res.x[idd:idd + S].sum())
    out = {"status": 0, "rounds": 1, "w": w.copy(), "obj": obj, "sec": time.time() - t0}
    if two:
        out["l1"] = float(np.abs(w - np.asarray(prev, float)).sum())
    return out


def mad_solve(R, b, prev=None, cap=CAP, obj_star=None):
    """C3 — 평균 맞춘(Σy ≥ Σb) 최소 MAD(Σ|y_t − ȳ| · Konno · Yamazaki 1991 · 분산의 LP 대리). 두 단계는 cvar_solve 와 같은 꼴(목적 ≤ obj* + S·TIE_EPS)."""
    import numpy as np
    import scipy.sparse as sp
    t0 = time.time()
    R = np.asarray(R, float)
    b = np.asarray(b, float)
    S, N = R.shape
    iw, iy, im, iz = 0, N, N + S, N + S + 1
    two = obj_star is not None
    iu = iz + S
    nv = iu + (N if two else 0)
    Aeq0, beq0 = _eq_block(R, nv, iw, iy)
    q = np.arange(S)
    # S·m − Σy = 0
    Am = sp.csr_matrix((np.concatenate([[float(S)], -np.ones(S)]), (np.zeros(S + 1, int), np.concatenate([[im], iy + q]))), shape=(1, nv))
    Aeq = sp.vstack([Aeq0, Am]).tocsr()
    beq = np.concatenate([beq0, [0.0]])
    # y_t − m − z_t ≤ 0 · −y_t + m − z_t ≤ 0
    A1 = sp.csr_matrix((np.concatenate([np.ones(S), -np.ones(S), -np.ones(S)]), (np.concatenate([q, q, q]), np.concatenate([iy + q, np.full(S, im), iz + q]))), shape=(S, nv))
    A2 = sp.csr_matrix((np.concatenate([-np.ones(S), np.ones(S), -np.ones(S)]), (np.concatenate([q, q, q]), np.concatenate([iy + q, np.full(S, im), iz + q]))), shape=(S, nv))
    A3 = sp.csr_matrix((-np.ones(S), (np.zeros(S, int), iy + q)), shape=(1, nv))
    rows = [A1, A2, A3]
    rhs = [np.zeros(S), np.zeros(S), np.array([-float(b.sum())])]
    bnd = [(0.0, cap)] * N + [(None, None)] * S + [(None, None)] + [(0.0, None)] * S
    if not two:
        c = np.zeros(nv)
        c[iz:iz + S] = 1.0
    else:
        A4 = sp.csr_matrix((np.ones(S), (np.zeros(S, int), iz + q)), shape=(1, nv))
        rows.append(A4)
        rhs.append(np.array([obj_star + S * TIE_EPS]))
        E, Eb = _l1_block(N, S + 1 + S, np.asarray(prev, float))
        rows.append(E)
        rhs.append(Eb)
        bnd = bnd + [(0.0, None)] * N
        c = np.zeros(nv)
        c[iu:iu + N] = 1.0
    res = _lp(c, sp.vstack(rows).tocsr(), np.concatenate(rhs), Aeq, beq, bnd)
    if res.status != 0:
        return {"status": int(res.status), "rounds": 1, "sec": time.time() - t0}
    w = res.x[:N]
    out = {"status": 0, "rounds": 1, "w": w.copy(), "obj": float(res.x[iz:iz + S].sum()), "sec": time.time() - t0}
    if two:
        out["l1"] = float(np.abs(w - np.asarray(prev, float)).sum())
    return out


def clean_weights(w, cap=CAP):
    """부스러기(< W_ZERO) 0 · 합 1 · 상한 되맞춤(넘친 몫은 상한 밑 이름에 비례로)."""
    import numpy as np
    w = np.asarray(w, float).copy()
    w[w < W_ZERO] = 0.0
    s = float(w.sum())
    if s <= 0:
        raise StopBake("해가 비었다")
    w = w / s
    for _ in range(60):
        over = w > cap + 1e-12
        if not over.any():
            break
        ex = float((w[over] - cap).sum())
        w[over] = cap
        free = (~over) & (w > 0) & (w < cap - 1e-12)
        fs = float(w[free].sum())
        if fs <= 0:
            break
        w[free] += ex * w[free] / fs
    return w


def cap_norm(x, cap=CAP):
    """양의 점수 → 합 1 · 상한 cap(eg30plus.cap_weights 와 같은 반복 · 배열판)."""
    import numpy as np
    x = np.asarray(x, float)
    w = x / x.sum()
    for _ in range(100):
        over = w > cap + 1e-12
        if not over.any():
            break
        ex = float((w[over] - cap).sum())
        free = (~over) & (w < cap - 1e-12)
        fs = float(w[free].sum())
        if fs <= 0:
            break
        w[over] = cap
        w[free] += ex * w[free] / fs
    return w


# ══════════════════════════════════════════════════════════════════════════
#  책 경로 · 쌍둥이 · 펀드(순수 · 얼린 dstk.book_path · qbatch_core.fund_from_path 와 같은 값 — selftest · 굽기 짝맞춤)
# ══════════════════════════════════════════════════════════════════════════
def ffill_cols(P):
    """열마다 앞값 채움(첫 유효값 뒤로만 · 앞쪽 NaN 은 그대로)."""
    import numpy as np
    P = np.asarray(P, float)
    n = P.shape[0]
    ok = np.isfinite(P) & (P > 0)
    idx = np.where(ok, np.arange(n)[:, None], -1)
    idx = np.maximum.accumulate(idx, axis=0)
    out = np.full_like(P, np.nan)
    good = idx >= 0
    cols = np.broadcast_to(np.arange(P.shape[1])[None, :], P.shape)
    out[good] = P[idx[good], cols[good]]
    return out


def exec_drop(px_exec_ok, w, cap=CAP):
    """체결 날(T+1) 목표 — 그날 가격 없는 이름을 빼고 비례로 다시 나눈다(얼린 dstk.exec_target 의 한 다리 판) · 남은 이름이 상한을 채울 만큼
    (≥ ⌈1/cap⌉)이면 이름 상한 20% 를 다시 맞춘다(cap_norm · dstk 에는 없는 한 줄 — 상한이 등록 규칙이라서). (비중, 뺀 수)."""
    import numpy as np
    w = np.asarray(w, float)
    ok = np.asarray(px_exec_ok, bool)
    keep = w * ok
    s = float(keep.sum())
    if s <= 0:
        raise StopBake("체결 날 목표 전체 가격 없음")
    keep = keep / s
    if keep.max() > cap + 1e-12 and int((keep > 0).sum()) >= int(math.ceil(1.0 / cap - 1e-9)):
        keep = cap_norm(keep, cap)
    return keep, int(((w > 0) & ~ok).sum())


def book_paths(Pff, Praw, execs, i_end, cost, i_window=None, n_years=10.0):
    """체결 목록 → 일간 경로(여럿을 한 번에 · 얼린 dstk.book_path 와 같은 규약): execs = [(체결 날 i, 열 배열, 비중 행렬(뽑기 × 열))] ·
    첫 체결 전은 값 없음(첫 체결 비용 포함) · 체결 날 값 = 비용 뒤 값 · 값 없는 날은 마지막 값(인수 · 상장폐지 = 마지막 가격) ·
    회전 = i_window 뒤 체결의 (거래액 / 값) 합 ÷ 2 ÷ 창 연수. Pff = 앞값 채운 가격(날 × 열) · Praw = 원 가격(체결 날 가격 단언용).
    돌려주는 것 (첫 체결 날, 경로 행렬(뽑기 × [첫 체결 … i_end]), 회전 배열)."""
    import numpy as np
    execs = sorted(execs, key=lambda x: x[0])
    i_first = int(execs[0][0])
    nd = execs[0][2].shape[0]
    K = Pff.shape[1]
    path = np.full((nd, i_end - i_first + 1), np.nan)
    units = np.zeros((nd, K))
    held = np.zeros(K, bool)
    V = np.ones(nd)
    traded_in = np.zeros(nd)
    for j, (i, cols, W) in enumerate(execs):
        i = int(i)
        i_next = int(execs[j + 1][0]) if j + 1 < len(execs) else i_end + 1
        cols = np.asarray(cols, int)
        W = np.asarray(W, float)
        if held.any():
            hc = np.flatnonzero(held)
            cur_h = units[:, hc] * Pff[i, hc][None, :]
            V = cur_h.sum(axis=1)
        else:
            hc = np.array([], int)
            cur_h = np.zeros((nd, 0))
        s = W.sum(axis=1)
        if np.any(np.abs(s - 1.0) > 1e-9) or W.min() < 0:
            raise StopBake("비중 합 %.9f" % float(s[np.argmax(np.abs(s - 1.0))]))
        p0 = Praw[i, cols]
        need = (W > 0).any(axis=0)
        if not np.all(np.isfinite(p0[need]) & (p0[need] > 0)):
            raise StopBake("체결 가격 없음")
        uc = np.union1d(hc, cols)
        tv = np.zeros((nd, len(uc)))
        cur = np.zeros((nd, len(uc)))
        pos_new = np.searchsorted(uc, cols)
        pos_old = np.searchsorted(uc, hc)
        tv[:, pos_new] = V[:, None] * W
        cur[:, pos_old] = cur_h
        traded = np.abs(tv - cur).sum(axis=1)
        V2 = V - cost * traded
        units[:, hc] = 0.0
        held[:] = False
        with np.errstate(divide="ignore", invalid="ignore"):
            u = np.where(W > 0, V2[:, None] * W / np.where(need, p0, 1.0)[None, :], 0.0)
        units[:, cols] = u
        held[cols[need]] = True
        path[:, i - i_first] = V2
        if i_window is not None and i > i_window:
            traded_in += traded / V
        a, bnd = i + 1, min(i_next, i_end + 1)
        if bnd > a:
            hc2 = np.flatnonzero(held)
            path[:, a - i_first:bnd - i_first] = units[:, hc2] @ Pff[a:bnd, hc2].T
    return i_first, path, traded_in / 2.0 / n_years


def twin_growth(day_idx, g_spy, g_tb, exec_idx, betas):
    """희석 쌍둥이 슬리브의 일간 성장(측정용 항등식 · 비용 없음) — 날 j 의 노출 β = 날 j 보다 앞선 마지막 체결의 β̂(체결 날 수익은 앞 책의 것 ·
    책과 같은 T+1 교체) · g = 1 + β(g_SPY − 1) + (1 − β)(g_Tbill − 1). β̂ > 1 이면 차입 항등식(보유하지 않는다)."""
    import numpy as np
    day_idx = np.asarray(day_idx, int)
    e = np.asarray(exec_idx, int)
    bt = np.asarray(betas, float)
    pos = np.searchsorted(e, day_idx, side="left") - 1
    if np.any(pos < 0):
        raise StopBake("쌍둥이: 첫 체결 앞 날")
    beta = bt[pos]
    return 1.0 + beta * (np.asarray(g_spy, float) - 1.0) + (1.0 - beta) * (np.asarray(g_tb, float) - 1.0)


def fund_ex_closed(gI, gS, c):
    """펀드 월 초과(%p) — 월초 0.9/0.1 · 월말 되돌림 비용 2c·|슬리브 몫 − 0.1| · 얼린 qbatch_core.fund_from_path 와 같은 값(q_switch.fund_ex_closed 식)."""
    import numpy as np
    gI = np.asarray(gI, float)
    gS = np.asarray(gS, float)
    v = 0.9 * gI + 0.1 * gS
    dev = np.abs(0.1 * gS / v - 0.1)
    return (v * (1.0 - 2.0 * c * dev) - gI) * 100.0


# ══════════════════════════════════════════════════════════════════════════
#  통계 · 관문 · 판정(순수)
# ══════════════════════════════════════════════════════════════════════════
def p_one_sided(t, nd):
    """한쪽 p — 얼린 eg30plus.down_t 의 설계대로 t(n_d − 1) 꼬리 · t 가 없으면 None(기각 못 함)."""
    if t is None or nd is None or nd < 2:
        return None
    from scipy.stats import t as _t
    return float(_t.sf(float(t), int(nd) - 1))


def down_delta(d, mask, E):
    """가면 위 평균 · 달력 HAC t(얼린 eg30plus.down_t · Bartlett 3 · n/(n − 1)) · 한쪽 p(t(n − 1))."""
    import numpy as np
    d = np.asarray(d, float)
    mk = np.asarray(mask, bool)
    n = int(mk.sum())
    t = E.down_t(d, mk, DOWN_LAG) if n >= 5 else None
    return {"n": n, "mean": (float(d[mk].mean()) if n else None), "t": t, "p": p_one_sided(t, n)}


def lb80(x):
    """연 X 의 80% 한쪽 하한 = 연 평균 − 0.8416 × (월 sd × √12 / √(n/12)) — 배치 X E4 식(iid)."""
    import numpy as np
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return None
    return float(x.mean() * 12 - Z80 * (x.std(ddof=1) * math.sqrt(12) / math.sqrt(n / 12.0)))


def rebound_claim(x, crash, surge):
    """G1 반등 청구(배치 X G-C2 꼴) — Σ_SURGE-M X ≥ −½·Σ_CRASH-M X ∧ Σ_CRASH-M X > 0(얼린 mech_episodes 달)."""
    import numpy as np
    x = np.asarray(x, float)
    sc = float(x[np.asarray(crash, bool)].sum())
    su = float(x[np.asarray(surge, bool)].sum())
    return {"crash_sum": sc, "surge_sum": su, "ok": bool(sc > 0 and su >= -0.5 * sc)}


def block_deltas(d, mask, n_blocks=4, blen=BLOCK_LEN):
    """G4 — 보유월 30개월 토막 넷(qbatch_core.evaluate blocks 와 같은 자름)마다 가면(하락월) 평균 Δ."""
    import numpy as np
    d = np.asarray(d, float)
    mk = np.asarray(mask, bool)
    q = np.arange(len(d)) // blen
    out = []
    for k in range(n_blocks):
        sel = (q == k) & mk
        out.append(float(d[sel].mean()) if sel.any() else None)
    return out


def holm_family(p):
    """한쪽 p(확증 가족 = (A) 하나 · m 1) → 얼린 v_tests.holm(α 0.05) — None 은 기각 못 함(분모에 남는다)."""
    import v_tests as VT
    h = VT.holm(dict(p), HOLM_ALPHA)
    return {"p": dict(p), "reject": h["reject"], "threshold": h["threshold"], "order": h["order"], "m": h["m"], "alpha": HOLM_ALPHA}


def gates_A(G):
    """(A) 관문 G0 ~ G6 — 모두 참이어야 채택 표시(등록 §6). None 은 거짓."""
    names = ("G0", "G1", "G2", "G3", "G4", "G5", "G6")
    c = {k: bool(G.get(k) is True) for k in names}
    return {"conds": c, "ok": bool(all(c.values()))}


def gates_B(G):
    """(B) 관문 — 무해 h1 · h2 · h3 ∧ 쌍둥이선 d1 · d2(등록 §6)."""
    names = ("h1", "h2", "h3", "d1", "d2")
    c = {k: bool(G.get(k) is True) for k in names}
    return {"conds": c, "ok": bool(all(c.values()))}


def verdict(adopt, reject, stopped=False):
    """결과 문서 «판정:» — 멈춤 → 보류 · 채택 표시 ≥ 1 → 보류(붙이기는 사용자 결정) · 기각 ≥ 1(표시 없음) → 측정만 · 기각 0 → 기각."""
    if stopped:
        return "보류"
    if any(adopt.values()):
        return "보류"
    if any(reject.values()):
        return "측정만"
    return "기각"


def judge_core(M):
    """판정 순수 규칙 — 확증 가족 {A}(m 1 · 한쪽 α 0.05 · 얼린 v_tests.holm) · (A) 관문 · 채택 표시 · 판정.
    (B) 는 등록 읽기다: 같은 가면 · t · p · 관문을 계산해 family["reading_B"] 에 싣지만 가족 · 채택 표시 · 판정에 들어가지 않는다.
    확증 · 읽기 통계의 가면이 얼린 하락월 35 가 아니면 멈춘다."""
    P = M["primary"]
    bad = [a for a in PRIMARY + READING_ARMS if (P.get(a) or {}).get("mask") != "down_frozen" or (P.get(a) or {}).get("n") != 35]
    if bad:
        raise StopBake("확증 · 읽기 통계의 가면이 등록(얼린 하락월 35)과 다르다(%s)" % ", ".join(bad))
    fam = holm_family({a: P[a]["p"] for a in PRIMARY})
    gA, gB = gates_A(M["gates_in"]["A"]), gates_B(M["gates_in"]["B"])
    pB = P["B"].get("p")
    fam["reading_B"] = {"p": pB, "nominal_reject": bool(holm_family({"B": pB})["reject"]["B"]), "gates_ok": gB["ok"],
                        "in_verdict": False}
    adopt = {"A": bool(fam["reject"]["A"] and gA["ok"])}
    return fam, {"A": gA, "B": gB}, adopt, verdict(adopt, fam["reject"])


# ══════════════════════════════════════════════════════════════════════════
#  G0 — G-EGD 산수(얼린 v_cmp 의 두 식 그대로 · selftest 가 v_cmp 와 대조)
# ══════════════════════════════════════════════════════════════════════════
def active_corr(wf, wB, wE):
    """corr(w_f − w_B, w_EG − w_B) — 세 책 이름의 합집합 위 피어슨(하나라도 분산 0 이면 None)."""
    import numpy as np
    ks = sorted(set(wf) | set(wB) | set(wE))
    a = np.array([wf.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    e = np.array([wE.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    if a.std() == 0 or e.std() == 0:
        return None
    return float(np.corrcoef(a, e)[0, 1])


def overlap_excess(wf, wB, wE):
    """Σmin(w_f, w_EG) − Σmin(w_B, w_EG)."""
    ks = set(wE)
    return float(sum(min(wf.get(k, 0.0), wE[k]) for k in ks) - sum(min(wB.get(k, 0.0), wE[k]) for k in ks))


def hold_between(form, months):
    """형성 달 목표 {달: 책} → 달마다 가장 최근 형성 달의 목표(v_cmp C1)."""
    ks = sorted(form)
    out = {}
    j = -1
    for m in sorted(months):
        while j + 1 < len(ks) and ks[j + 1] <= m:
            j += 1
        if j >= 0:
            out[m] = form[ks[j]]
    return out


def g0_summary(ssd_t, wB_t, eg_t):
    """G0 — 달마다 능동비중 상관 · 겹침 초과(티커 · '.' → '-') → 달별 중앙값 · 통과(≤ 0.30 · ≤ 0.10)."""
    import numpy as np
    rows = []
    for m in sorted(ssd_t):
        wE = eg_t.get(m)
        wB = wB_t.get(m)
        if not wE or not wB:
            continue
        rows.append((m, active_corr(ssd_t[m], wB, wE), overlap_excess(ssd_t[m], wB, wE)))
    cs = [r[1] for r in rows if r[1] is not None]
    ov = [r[2] for r in rows]
    cm = float(np.median(cs)) if cs else None
    om = float(np.median(ov)) if ov else None
    ok = bool(cm is not None and om is not None and cm <= G0_CORR_MAX and om <= G0_OVX_MAX)
    return {"n_months": len(rows), "corr_med": cm, "ovx_med": om, "pass": ok, "label": (None if ok else "EG30 닮은 책")}


# ══════════════════════════════════════════════════════════════════════════
#  G5 위약 — 같은 이름 수 · 같은 이름 상한 · 같은 사전 β̂ 띠의 무작위 포트(순수 · 씨앗 고정)
# ══════════════════════════════════════════════════════════════════════════
def _beta_at(u, bb, lam, cap):
    import numpy as np
    z = lam * bb
    z = z - z.max()
    w = cap_norm(u * np.exp(z), cap)
    return w, float(w @ bb)


def placebo_draw(rng, n_elig, n_pick, betas, target, cap=CAP, band=BETA_BAND, tries=PLACEBO_TRIES):
    """이름 n_pick 개를 우주에서 고르게(되돌림 없이) · 비중 = 디리클레(1) × exp(λ β̂) 를 상한 20% 로 맞추고 λ 이분법으로 β̂ 를 목표 ±band 안에.
    못 닿으면 이름을 다시 뽑는다(tries 번) — 끝내 못 닿으면 가장 가까운 것(대체 · 개수 공개). 돌려주는 것 (열, 비중, β̂, 뽑은 번, 대체)."""
    import numpy as np
    betas = np.asarray(betas, float)
    best = None
    n_pick = int(max(n_pick, int(math.ceil(1.0 / cap - 1e-9))))
    for k in range(tries):
        cols = np.sort(rng.choice(n_elig, size=n_pick, replace=False))
        u = rng.dirichlet(np.ones(n_pick))
        bb = betas[cols]
        lo, hi = -PLACEBO_LAMBDA, PLACEBO_LAMBDA
        wl, bl = _beta_at(u, bb, lo, cap)
        wh, bh = _beta_at(u, bb, hi, cap)
        cand = []
        if bl <= target <= bh:
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                wm, bm = _beta_at(u, bb, mid, cap)
                if abs(bm - target) <= band * 0.5:
                    break
                if bm < target:
                    lo = mid
                else:
                    hi = mid
            cand = [(wm, bm)]
        else:
            cand = [(wl, bl), (wh, bh)]
        for w, bt in cand:
            if abs(bt - target) <= band:
                return cols, w, bt, k + 1, False
            if best is None or abs(bt - target) < abs(best[2] - target):
                best = (cols, w, bt)
    return best[0], best[1], best[2], tries, True


def placebo_rng(d):
    """뽑기 d 의 난수 — 뽑기마다 독립(SeedSequence([씨앗, d])) · 과정 수 · 차례와 무관."""
    import numpy as np
    return np.random.default_rng(np.random.SeedSequence([SEED_PLACEBO, int(d)]))


# ══════════════════════════════════════════════════════════════════════════
#  French(기전 층 G6) — 일간 49 산업 가치가중 · 일간 3요인(Mkt-RF · RF) 읽기(순수)
# ══════════════════════════════════════════════════════════════════════════
def parse_french_daily(txt, section="Average Value Weighted Returns -- Daily"):
    """French 일간 CSV 글 → (날짜 목록 'YYYY-MM-DD', 열 이름, 값 행렬 %) — section 이 있으면 그 절만 · −99.99 · −999 는 NaN."""
    import numpy as np
    lines = txt.splitlines()
    start = 0
    if section is not None:
        hit = [q for q, l in enumerate(lines) if l.strip() == section]
        if not hit:
            raise StopBake("French 절 없음: %s" % section)
        start = hit[0] + 1
    while start < len(lines) and not lines[start].strip().startswith(","):
        start += 1
    head = [h.strip() for h in lines[start].split(",")[1:]]
    dates, rows = [], []
    for l in lines[start + 1:]:
        s = l.strip()
        if not s or not s[0].isdigit():
            break
        parts = [x.strip() for x in s.split(",")]
        d = parts[0]
        if len(d) != 8:
            break
        dates.append("%s-%s-%s" % (d[:4], d[4:6], d[6:8]))
        vals = [float(x) for x in parts[1:1 + len(head)]]
        rows.append(vals)
    X = np.array(rows, float)
    X[(X <= -99.99 + 1e-9) | (X <= -999 + 1e-9)] = np.nan
    return dates, head, X


def french_zip_text(p):
    import zipfile
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        if len(names) != 1:
            raise StopBake("French zip 안 파일 수 %d" % len(names))
        return z.read(names[0]).decode("latin-1")


def fp_beta_block(y_ex, mex, i, win=FP_WIN, nmin=FP_MIN, K=FP_K, wshr=FP_W):
    """v_pit.beta_fp 와 같은 식(결정일 i 까지 win 거래일 · 관측 ≥ nmin · Dimson K 지연 · β = w·β_TS + (1 − w)) — 열마다(산업) 한 번에.
    y_ex(날 × 열) · mex(날) 는 무위험 초과 일간 수익. 모자라면 NaN."""
    import numpy as np
    n = len(mex)
    XL = np.full((n, K + 1), np.nan)
    for k in range(K + 1):
        XL[k:, k] = mex[:n - k]
    p0 = max(0, i - win + 1)
    X = XL[p0:i + 1]
    Y = y_ex[p0:i + 1]
    out = np.full(Y.shape[1], np.nan)
    okx = np.isfinite(X).all(axis=1)
    for j in range(Y.shape[1]):
        ok = okx & np.isfinite(Y[:, j])
        if ok.sum() < nmin:
            continue
        A = np.column_stack([np.ones(int(ok.sum())), X[ok]])
        coef, *_ = np.linalg.lstsq(A, Y[ok, j], rcond=None)
        out[j] = wshr * float(coef[1:].sum()) + (1 - wshr) * 1.0
    return out


def book_path_ref(PX, execs, i_end, cost, i_window=None, n_years=10.0):
    """얼린 dstk.book_path 의 한 줄씩 옮김(사전 · 키 판 — 굽기 짝맞춤 P1 · selftest 가 원본과 대조한다)."""
    execs = sorted(execs, key=lambda x: x[0])
    path, units, last = {}, {}, {}
    V = 1.0
    traded_in = 0.0
    for j, (i, w) in enumerate(execs):
        i_next = execs[j + 1][0] if j + 1 < len(execs) else i_end + 1
        if units:
            for k in units:
                p = PX[k][i]
                if p == p and p > 0:
                    last[k] = i
            cur = {k: units[k] * PX[k][last[k]] for k in units}
            V = sum(cur.values())
        else:
            cur = {}
        s = sum(w.values())
        if abs(s - 1.0) > 1e-9 or min(w.values(), default=0) < 0:
            raise StopBake("비중 합 %.9f" % s)
        tv = {k: V * x for k, x in w.items()}
        traded = sum(abs(tv.get(k, 0.0) - cur.get(k, 0.0)) for k in sorted(set(tv) | set(cur)))
        V2 = V - cost * traded
        units = {}
        for k, x in w.items():
            p0 = PX[k][i]
            if not (p0 == p0 and p0 > 0):
                raise StopBake("체결 가격 없음 %s" % k)
            units[k] = V2 * x / p0
        last = {k: i for k in units}
        path[i] = V2
        if i_window is not None and i > i_window:
            traded_in += traded / V
        for d in range(i + 1, min(i_next, i_end + 1)):
            tot = 0.0
            for k, u in units.items():
                p = PX[k][d]
                if p == p and p > 0:
                    last[k] = d
                tot += u * PX[k][last[k]]
            path[d] = tot
    return {"path": path, "turn": traded_in / 2.0 / n_years, "n_exec": len(execs)}


# ══════════════════════════════════════════════════════════════════════════
#  풀이 작업(과정 풀 · 윈도 spawn — 머리 단계 함수여야 한다)
# ══════════════════════════════════════════════════════════════════════════
def _load_month(p):
    import pickle
    with open(p, "rb") as f:
        return pickle.load(f)


def _band_of(M):
    """C10 섹터 띠 — 우주(자격 이름) 시총가중 섹터 비중 b_g 의 ±5%(상대) · 시총 없는 이름은 b_g 에 들지 않는다 · b_g = 0 인 무리는 0 으로 묶인다."""
    caps = M["caps"]
    secs = M["sectors"]
    tot = sum(c for c in caps if c)
    bw = {}
    for c, g in zip(caps, secs):
        bw.setdefault(g, 0.0)
        if c:
            bw[g] += c / tot
    lo = {g: (1.0 - SECTOR_BAND) * v for g, v in bw.items()}
    hi = {g: (1.0 + SECTOR_BAND) * v for g, v in bw.items()}
    return (list(secs), lo, hi)


def _task_stage1(args):
    """1단계 풀이 하나 — (판, 달, 달 파일) → 결과(해 · 묶인 절단면)."""
    variant, m, path = args
    import numpy as np
    import warnings
    warnings.simplefilter("ignore")
    M = _load_month(path)
    R, b = M["R"], M["b"]
    if variant in ("SSD", "C4", "C10"):
        r = ssd_stage1(R, b, CAP, scaled=(variant != "C4"), band=(_band_of(M) if variant == "C10" else None))
    elif variant == "C5":
        r = cvar_solve(R, b)
        if r["status"] == 0:
            r["V"] = r["obj"]
    elif variant == "C3":
        r = mad_solve(R, b)
        if r["status"] == 0:
            r["V"] = r["obj"]
    else:
        raise ValueError(variant)
    r["variant"], r["m"] = variant, m
    if "cuts" in r:
        r["cuts"] = [(int(s), np.asarray(J, np.int16)) for s, J in r["cuts"]]
    return r


def _stage2_one(chain, M, s1, prev):
    """2단계 하나(판별) — 실패하면 부르는 쪽이 1단계 해를 쓴다(개수 공개)."""
    R, b = M["R"], M["b"]
    if chain in ("SSD", "PRE", "C4", "C10"):
        return ssd_stage2(R, b, s1["V"], prev, seed_cuts=s1.get("cuts") or (), w1=s1["w"], cap=CAP, scaled=(chain != "C4"),
                          band=(_band_of(M) if chain == "C10" else None))
    if chain == "C5":
        return cvar_solve(R, b, prev=prev, obj_star=s1["obj"])
    if chain == "C3":
        return mad_solve(R, b, prev=prev, obj_star=s1["obj"])
    raise ValueError(chain)


def _task_chain(args):
    """사슬 하나(차례대로) — 달마다 기준 비중(첫 달 = 우주 시총가중 · 뒤 = 앞 체결 비중을 결정일까지 흘린 것) → 2단계 → 부스러기 정리 →
    T+1 체결 날 가격 없는 이름 빼기 → 체결 비중 · 흘림. 1단계가 실패한 달은 앞 체결 목표(흘린 비중)를 그달 우주로 옮겨 잇는다(개수 공개)."""
    chain, months, paths, s1_path = args
    import numpy as np
    import pickle
    import warnings
    warnings.simplefilter("ignore")
    with open(s1_path, "rb") as f:
        S1 = pickle.load(f)
    variant = "SSD" if chain == "PRE" else chain
    out = {}
    prev_keys, prev_w = None, None
    for m in months:
        M = _load_month(paths[m])
        keys = M["keys"]
        N = len(keys)
        if prev_keys is None:
            ref = np.asarray(M["cw"], float)
        else:
            pos = {k: q for q, k in enumerate(keys)}
            ref = np.zeros(N)
            for k, x in zip(prev_keys, prev_w):
                if k in pos:
                    ref[pos[k]] += x
        s1 = S1.get((variant, m))
        rec = {"status1": (s1 or {}).get("status"), "rounds1": (s1 or {}).get("rounds"), "sec1": (s1 or {}).get("sec")}
        if s1 is not None and s1.get("status") == 0:
            s2 = _stage2_one(chain, M, s1, ref)
            rec.update({"status2": s2.get("status"), "rounds2": s2.get("rounds"), "sec2": s2.get("sec")})
            if s2.get("status") == 0:
                w = s2["w"]
                rec["tie_l1"] = float(np.abs(np.asarray(s2["w"]) - np.asarray(s1["w"])).sum())
            else:
                w = s1["w"]
            rec["carried"] = False
        else:
            rec["carried"] = True
            if prev_keys is None:
                raise StopBake("사슬 %s 첫 결정 %s 풀이 실패" % (chain, m))
            w = ref.copy()
            if w.sum() <= 0:
                raise StopBake("사슬 %s 결정 %s 풀이 실패 · 이을 목표가 우주 밖" % (chain, m))
        wc = clean_weights(w)
        if variant in ("SSD", "C4", "C10"):
            V1 = (s1 or {}).get("V")
            rec["v_gap"] = (None if (V1 is None or rec["carried"]) else float(V1 - ssd_value(M["R"] @ wc, M["b"], scaled=(variant != "C4"))))
        we, nd = exec_drop(M["exec_ok"], wc)
        rec.update({"n": int((we > 0).sum()), "n_cap": int((we >= CAP - 1e-9).sum()), "drops": nd, "l1_ref": float(np.abs(we - ref).sum())})
        sel = np.flatnonzero(we > 0)
        rec["keys"] = [keys[q] for q in sel]
        rec["w"] = [float(we[q]) for q in sel]
        rec["tickers"] = [M["tickers"][q] for q in sel]
        rec["exec_i"] = int(M["i"] + 1)
        rec["exec_d"] = M.get("exec_d")
        bet = np.asarray(M["beta"], float)
        rec["beta"] = float(we @ np.where(np.isfinite(bet), bet, 1.0))
        rec["beta_cov"] = float(we[np.isfinite(bet)].sum())
        out[m] = rec
        # 다음 결정일까지 흘림(체결 날 → 다음 결정일 · 가격 비 · 없으면 마지막 값)
        dr = np.asarray(M["drift"], float)
        v = we * np.where(np.isfinite(dr), dr, 1.0)
        prev_keys = [keys[q] for q in sel]
        prev_w = list(v[sel] / v[sel].sum()) if v[sel].sum() > 0 else [float(x) for x in we[sel]]
    return chain, out


def _pool(n):
    import multiprocessing as mp
    return mp.get_context("spawn").Pool(processes=n)


POOL_TIMEOUT = 3600.0                  # 결과 하나를 기다리는 상한(초) — 과정이 죽어도 조용히 멈춰 서지 않게(넘으면 StopBake · 속도 설정이지 해가 아니다)


def pool_map(fn, tasks, n):
    """과정 풀(spawn · n) 로 차례대로 결과를 받는다 — 결과 하나마다 시간 상한(POOL_TIMEOUT). 돌려주는 차례 = tasks 차례(해는 과정 수와 무관)."""
    import multiprocessing as mp
    tasks = list(tasks)
    out = []
    with _pool(n) as pool:
        it = pool.imap(fn, tasks, chunksize=1)
        for _ in range(len(tasks)):
            try:
                out.append(it.next(timeout=POOL_TIMEOUT))
            except mp.TimeoutError:
                pool.terminate()
                raise StopBake("풀이 과정이 %d 초 안에 결과를 내지 못했다" % int(POOL_TIMEOUT))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  vroot 자식 — 목표(F0 · 굽기 공통 · 수익 없음): 우주 · 시나리오 · LP 판 다섯 · 바구니 둘 · β̂ · G0 입력 · 위약 뽑기 개수
# ══════════════════════════════════════════════════════════════════════════
def _vroot_pins(root):
    """vroot 자료 핀 — 얼린 x_adapter._v_pins_full(배치 V 파일 핀 · 폴더 요약 · 뿌리)."""
    import x_adapter as XA
    import v_data as VD
    ok, bad = XA._v_pins_full(VD, root)
    if not ok:
        raise StopBake("배치 V 자료 핀 불일치 — %s" % "; ".join(list(bad)[:3]))
    return True


def _window_idx(me):
    return me[FORM_FIRST], me[HOLD[1]]


def targets_child(job):
    """🚨 수익 없음 — 결정 달마다 우주 · 시나리오(직전 200 거래일 수익 · 결정일 이전 자료) · LP 해 · 체결 비중 · β̂ · 개수. 산출은 작업 폴더(캐시)에만."""
    import contextlib
    import numpy as np
    import pickle
    t0 = time.time()
    assert_blobs(HERE, VROOT_BLOBS)
    _vroot_pins(job.get("root") or ROOT)
    import v_pit as VP
    with contextlib.redirect_stdout(io.StringIO()):
        U = VP.Universe.real(with_vd1=True)
    work = job["work"]
    os.makedirs(work, exist_ok=True)
    me = U.me_idx
    dates = U.dates
    spy = np.asarray(U.spy, float)
    f_main, f_pre = chain_forms("SSD"), chain_forms("PRE")
    forms_all = sorted(set(f_main) | set(f_pre))
    t_u = round(time.time() - t0, 1)
    paths, meta = {}, {}
    for m in forms_all:
        i = me[m]
        mem = U.members(m)
        spy_w = spy[i - S_WIN:i + 1]
        if not (np.all(np.isfinite(spy_w)) and np.all(spy_w > 0)):
            raise StopBake("결정 %s SPY 가격 창 결측" % m)
        rows = []
        for r_ in mem:
            p = np.asarray(U.PX[r_["k"]], float)
            seg = p[i - S_WIN:i + 1]
            if len(seg) == S_WIN + 1 and np.all(np.isfinite(seg)) and np.all(seg > 0):
                rows.append((r_["k"], r_["t"], r_["ndx_only"], seg))
        rows.sort(key=lambda x: x[0])
        keys = [x[0] for x in rows]
        tick = [_tk(x[1]) for x in rows]
        Rm = np.column_stack([(x[3][1:] / x[3][:-1] - 1.0) * 100.0 for x in rows])
        bm = (spy_w[1:] / spy_w[:-1] - 1.0) * 100.0
        mev = U.me(m)
        caps = [(mev.get(x[1]) or (None, None))[0] for x in rows]
        sect = []
        n_sec_none = 0
        for x in rows:
            s_, _src = U.sector(x[1], m, x[2])
            if not s_:
                n_sec_none += 1
            sect.append(s_ or "(없음)")
        betas = []
        for x in rows:
            bf = U.beta_fp(x[0], m).get("beta")
            betas.append(float(bf) if bf is not None else float("nan"))
        ie = i + 1
        exec_ok = [bool(ie < len(dates) and np.isfinite(U.PX[k][ie]) and U.PX[k][ie] > 0) for k in keys]
        # 다음 결정일까지의 흘림 비(체결 날 T+1 → 다음 달 결정일 · 마지막 유효 값)
        i_next = me.get(mshift(m, 1))
        drift = []
        for k in keys:
            p = np.asarray(U.PX[k], float)
            if i_next is None or not (ie < len(p) and np.isfinite(p[ie]) and p[ie] > 0):
                drift.append(float("nan"))
                continue
            seg = p[ie:i_next + 1]
            okx = np.flatnonzero(np.isfinite(seg) & (seg > 0))
            drift.append(float(seg[okx[-1]] / p[ie]))
        capv = np.array([c if c else 0.0 for c in caps], float)
        cw = cap_norm(capv, CAP) if capv.sum() > 0 else np.full(len(keys), 1.0 / len(keys))
        wB = U.w_B(m)
        tset = set(tick)
        cov_w = float(sum(v for t_, v in wB.items() if _tk(t_) in tset))
        M = {"m": m, "i": int(i), "keys": keys, "tickers": tick, "R": Rm, "b": bm, "caps": caps, "sectors": sect, "beta": betas,
             "exec_ok": exec_ok, "drift": drift, "cw": [float(x) for x in cw], "exec_d": (dates[ie] if ie < len(dates) else None)}
        p_ = os.path.join(work, "m_%s.pkl" % m)
        with open(p_, "wb") as f:
            pickle.dump(M, f, protocol=5)
        paths[m] = p_
        n_list = len(set(U.W["lists"]["spx"].get(m) or []) | set(U.W["lists"]["ndx"].get(m) or []))
        meta[m] = {"n_list": n_list, "n_members": len(mem), "n_elig": len(keys), "n_cap": int((capv > 0).sum()),
                   "n_beta": int(np.isfinite(np.array(betas)).sum()), "n_sec_none": n_sec_none, "n_exec_bad": int(sum(1 for x in exec_ok if not x)),
                   "cov_w_spx": cov_w, "wB": {_tk(t_): float(v) for t_, v in wB.items()}}
    t_s = round(time.time() - t0, 1)
    # 1단계(병렬 · 달마다 독립)
    tasks = [("SSD", m, paths[m]) for m in forms_all] + [(v, m, paths[m]) for v in ("C10", "C4", "C3", "C5") for m in f_main]
    S1 = {}
    for r in pool_map(_task_stage1, tasks, int(job.get("workers") or N_WORKERS)):
        S1[(r["variant"], r["m"])] = r
    s1_path = os.path.join(work, "stage1.pkl")
    with open(s1_path, "wb") as f:
        pickle.dump(S1, f, protocol=5)
    t_1 = round(time.time() - t0, 1)
    # 2단계 사슬(사슬 안은 차례 · 사슬끼리 병렬)
    ch_args = [(c, chain_forms(c if c == "PRE" else "SSD"), paths, s1_path) for c in CHAINS]
    chains = {}
    for c, o in pool_map(_task_chain, ch_args, min(len(CHAINS), int(job.get("workers") or N_WORKERS) + 1)):
        chains[c] = o
    t_2 = round(time.time() - t0, 1)
    # 바구니 둘(LP 없음) — C7a 동일가중 · C7b 시총가중(상한 20%) · 같은 T+1 체결 빼기
    for bname in BASKETS:
        o = {}
        for m in f_main:
            M = _load_month(paths[m])
            n = len(M["keys"])
            w0 = np.full(n, 1.0 / n) if bname == "C7A" else np.asarray(M["cw"], float)
            we, nd = exec_drop(M["exec_ok"], w0)
            sel = np.flatnonzero(we > 0)
            bet = np.asarray(M["beta"], float)
            o[m] = {"keys": [M["keys"][q] for q in sel], "w": [float(we[q]) for q in sel], "tickers": [M["tickers"][q] for q in sel],
                    "exec_i": int(M["i"] + 1), "exec_d": M.get("exec_d"), "n": int(len(sel)), "drops": nd,
                    "beta": float(we @ np.where(np.isfinite(bet), bet, 1.0)),
                    "beta_cov": float(we[np.isfinite(bet)].sum()), "carried": False}
        chains[bname] = o
    # 위약 뽑기(F0 셈 · 굽기와 같은 흐름 — 비중만 · 수익 없음)
    pl = placebo_plan(chains["SSD"], f_main, paths)
    t_p = round(time.time() - t0, 1)
    # 창 날짜 · SPY 창 수익(뿌리 대조용 · 지수 · 전략 아님)
    i0, iE = _window_idx(me)
    win = [dates[q] for q in range(i0, iE + 1)]
    spy_r = [float(spy[q] / spy[q - 1] - 1.0) for q in range(i0 + 1, iE + 1)]
    doc = {"kind": "ssdix_targets", "note": "🚨 목표 비중 · 개수(보유 수익 없음) — 캐시 전용", "chains": chains, "meta": meta,
           "window": {"i0": int(i0), "iE": int(iE), "dates_sha": lines_sha(win), "n_dates": len(win), "spy_r": spy_r, "first": win[0], "last": win[-1]},
           "pre_window": {"i0": int(me[PRE_FIRST]), "iE": int(me[PRE_HOLD[1]])},
           "placebo_plan": pl["summary"], "grid_first": dates[0], "grid_last": dates[-1], "month_files": paths,
           "hash": {c: canon_hash({m: dict(zip(v["keys"], [round(x, 10) for x in v["w"]])) for m, v in chains[c].items()})[:16] for c in chains},
           "sec": {"universe": t_u, "scenarios": t_s, "stage1": t_1, "chains": t_2, "placebo": t_p, "total": round(time.time() - t0, 1)}}
    doc["counts"] = targets_counts(doc)
    return doc


def placebo_plan(ssd, months, paths, want_draws=False):
    """G5 뽑기 계획(비중만) — 뽑기 d 마다 달 k 에 SSD 체결 이름 수 · 체결 β̂ 목표 · 우주(자격 ∧ T+1 가격) 안에서 뽑는다.
    want_draws 면 뽑기 자체(키 · 비중 · β̂)도 돌려준다(굽기의 책 자식)."""
    import numpy as np
    uni = []
    for m in months:
        M = _load_month(paths[m])
        ok = np.flatnonzero(np.asarray(M["exec_ok"], bool))
        bet = np.asarray(M["beta"], float)
        uni.append((m, [M["keys"][q] for q in ok], np.where(np.isfinite(bet[ok]), bet[ok], 1.0)))
    draws = [] if want_draws else None
    n_fb, max_tries, h = 0, 0, hashlib.sha256()
    for d in range(K_PLACEBO):
        rng = placebo_rng(d)
        one = []
        for (m, ks, bb) in uni:
            cols, w, bt, tr, fb = placebo_draw(rng, len(ks), int(ssd[m]["n"]), bb, float(ssd[m]["beta"]))
            n_fb += int(fb)
            max_tries = max(max_tries, tr)
            h.update(("%d|%s|" % (d, m)).encode() + ",".join("%s:%.10f" % (ks[c], x) for c, x in zip(cols, w)).encode())
            if want_draws:
                one.append(([ks[c] for c in cols], [float(x) for x in w], float(bt)))
        if want_draws:
            draws.append(one)
    s = {"k": K_PLACEBO, "seed": SEED_PLACEBO, "band": BETA_BAND, "n_fallback": n_fb, "max_tries": max_tries, "hash16": h.hexdigest()[:16],
         "n_month_draws": K_PLACEBO * len(months)}
    return {"summary": s, "draws": draws, "months": months}


def targets_counts(doc):
    """F0 개수(정수 · 참/거짓 · 짧은 해시만) — 등록 F0 표 · 서명의 출처."""
    import numpy as np
    meta, ch = doc["meta"], doc["chains"]
    fm = months_between(FORM_FIRST, FORM_LAST)
    el = [meta[m]["n_elig"] for m in fm]
    mem = [meta[m]["n_members"] for m in fm]
    cov = [meta[m]["n_elig"] / max(1, meta[m]["n_members"]) for m in fm]
    covw = [meta[m]["cov_w_spx"] for m in fm]
    out = {"n_forms_main": len(chain_forms("SSD")), "n_forms_pre": len(chain_forms("PRE")),
           "elig_min": int(min(el)), "elig_med": int(np.median(el)), "elig_max": int(max(el)), "members_min": int(min(mem)), "members_max": int(max(mem)),
           "cov_min_x1000": int(round(min(cov) * 1000)), "cov_med_x1000": int(round(float(np.median(cov)) * 1000)),
           "covw_min_x1000": int(round(min(covw) * 1000)), "months_cov_lt90": int(sum(1 for x in cov if x < 0.90)),
           "beta_missing_elig_max": int(max(meta[m]["n_elig"] - meta[m]["n_beta"] for m in fm)),
           "sec_none_max": int(max(meta[m]["n_sec_none"] for m in fm)), "exec_bad_max": int(max(meta[m]["n_exec_bad"] for m in fm)),
           "placebo_fallback": int(doc["placebo_plan"]["n_fallback"]), "placebo_hash16": doc["placebo_plan"]["hash16"]}
    for c, o in ch.items():
        ms = sorted(o)
        if c not in BASKETS:
            out["%s_ok1" % c] = int(sum(1 for m in ms if o[m].get("status1") == 0))
            out["%s_ok2" % c] = int(sum(1 for m in ms if o[m].get("status2") == 0))
            tl = [float(o[m].get("tie_l1") or 0.0) for m in ms]
            out["%s_tie_med_x1000" % c] = int(round(float(np.median(tl)) * 1000))          # 2단계(동률 해소)가 1단계 해에서 옮긴 ℓ1 — 중앙 · 최대(‰)
            out["%s_tie_max_x1000" % c] = int(round(max(tl) * 1000))
            out["%s_ties_gt5pct" % c] = int(sum(1 for x in tl if x > 0.05))                     # 책의 5% 넘게 옮긴 달(해가 여럿이던 달의 대리)
        out["%s_carried" % c] = int(sum(1 for m in ms if o[m].get("carried")))
        nn = [o[m]["n"] for m in ms]
        out["%s_names_min" % c], out["%s_names_max" % c] = int(min(nn)), int(max(nn))
        out["%s_drops" % c] = int(sum(o[m]["drops"] for m in ms))
        out["%s_hash16" % c] = doc["hash"][c]
    return out


# ══════════════════════════════════════════════════════════════════════════
#  root 자식 F0(수익 없음) — G0(EG30 독립 · 비중만) · 창 날짜 동일 · SPY 일간 수익 동일(지수 자료 대조) · 얼린 V0 목표 해시
# ══════════════════════════════════════════════════════════════════════════
def f0r_child(job):
    import numpy as np
    t0 = time.time()
    assert_blobs(HERE, ROOT_BLOBS)
    import qbatch_core as Q
    import q_switch as SW
    import x_adapter as XA
    ctx = Q.Ctx()
    F = SW.frame(ctx)
    G = ctx.G
    months = list(F.months)
    if months != months_between(FORM_FIRST, FORM_LAST):
        raise StopBake("틀의 결정 달이 등록 창과 다르다")
    T = _json(job["targets"])
    win = [G.dates[i] for i in range(F.i0, F.iE + 1)]
    grid_same = bool(lines_sha(win) == T["window"]["dates_sha"] and len(win) == T["window"]["n_dates"])
    ix = np.asarray(G.IX_TR, float)
    r_root = ix[F.i0 + 1:F.iE + 1] / ix[F.i0:F.iE] - 1.0
    r_v = np.asarray(T["window"]["spy_r"], float)
    spy_diff = float(np.max(np.abs(r_root - r_v))) if len(r_v) == len(r_root) else None
    T0 = ctx.V0_targets
    h = XA.v0_target_hashes(T0)
    v0_hash_ok = bool(all(h[k] == XA.V0_HASH_PIN[k] for k in XA.V0_HASH_PIN))
    qf = set(Q.quarterly_forms())
    eg_form = {}
    for m, v in T0.items():
        if m not in qf:
            continue
        d = {}
        for k, w in v["w"].items():
            t = _tk(v["names"].get(k) or k.split("@")[0])
            d[t] = d.get(t, 0.0) + float(w)
        eg_form[m] = d
    eg_t = hold_between(eg_form, months)
    ssd_t = {}
    for m in months:
        r = T["chains"]["SSD"][m]
        d = {}
        for t, w in zip(r["tickers"], r["w"]):
            d[t] = d.get(t, 0.0) + float(w)
        ssd_t[m] = d
    wB_t = {m: T["meta"][m]["wB"] for m in months}
    g0 = g0_summary(ssd_t, wB_t, eg_t)
    return {"kind": "ssdix_f0r", "grid_same": grid_same, "n_win_dates": len(win), "spy_max_abs_diff": spy_diff,
            "spy_same": bool(spy_diff is not None and spy_diff <= 1e-9), "v0_hash_ok": v0_hash_ok, "g0": g0, "n_eg_forms": len(eg_form),
            "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
#  G6 자식 — French 49 산업(가치가중 · 일간) 기전 층. mode "f0" = 목표 · 개수만 · "bake" = 수익 · Δ(🚨 굽기 · 연기에서만)
# ══════════════════════════════════════════════════════════════════════════
def _french_inputs(job):
    import numpy as np
    got = {}
    for fid, (fn, sha) in FRENCH_FILES.items():
        p = (job.get("french") or {}).get(fid)
        if not p or not os.path.exists(p):
            raise StopBake("French 파일 없음(%s)" % fn)
        h = hashlib.sha256(_rbytes(p)).hexdigest()
        if h != sha:
            raise StopBake("French 파일 sha256 이 등록 값과 다르다(%s)" % fn)
        got[fid] = p
    t49 = french_zip_text(got["ind49_d"])
    tff = french_zip_text(got["ff3_d"])
    vint_ok = bool(("%s CRSP" % FRENCH_VINTAGE) in t49.splitlines()[0] and ("%s CRSP" % FRENCH_VINTAGE) in tff.splitlines()[0])
    d1, heads, X = parse_french_daily(t49)
    d2, h2, F3 = parse_french_daily(tff, section=None)
    if [h.strip() for h in h2] != ["Mkt-RF", "SMB", "HML", "RF"]:
        raise StopBake("French 3요인 열 이름이 다르다")
    s1 = d1.index("2005-01-03")
    s2 = d2.index("2005-01-03")
    D1, D2 = d1[s1:], d2[s2:]
    if D1 != D2:
        raise StopBake("French 두 파일 날짜가 다르다")
    X = X[s1:]
    mk = F3[s2:, 0] + F3[s2:, 3]
    rf = F3[s2:, 3]
    return {"dates": D1, "heads": heads, "X": X, "mkt": mk, "rf": rf, "vintage_ok": vint_ok, "n_head": len(heads)}


def g6_child(job):
    try:
        return _g6_body(job)
    except StopBake as e:
        if job.get("mode") == "bake":
            return {"kind": "ssdix_g6", "stopped": str(e)[:300]}
        raise


def _g6_body(job):
    import numpy as np
    import pickle
    t0 = time.time()
    assert_blobs(HERE, {"eg30plus": VROOT_BLOBS["eg30plus"]})
    FI = _french_inputs(job)
    dates, X, mkt, rf = FI["dates"], FI["X"], FI["mkt"], FI["rf"]
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    work = job["work"]
    os.makedirs(work, exist_ok=True)
    forms = months_between(G6_WARM, G6_LAST)
    n = len(dates)
    Praw = np.cumprod(1.0 + np.where(np.isfinite(X), X, 0.0) / 100.0, axis=0)
    Praw[~np.isfinite(X)] = np.nan
    Pff = ffill_cols(Praw)
    mex = mkt - rf
    yex = X - rf[:, None]
    paths, meta = {}, {}
    for m in forms:
        i = me[m]
        blk = X[i - S_WIN + 1:i + 1]
        elig = [j for j in range(X.shape[1]) if np.all(np.isfinite(blk[:, j]))]
        keys = [FI["heads"][j] for j in elig]
        R = blk[:, elig]
        b = mkt[i - S_WIN + 1:i + 1]
        ie = i + 1
        exec_ok = [bool(ie < n and np.isfinite(X[ie, j])) for j in elig]
        i_next = me.get(mshift(m, 1))
        drift = [float(Pff[i_next, j] / Praw[ie, j]) if (i_next is not None and ie < n and np.isfinite(Praw[ie, j])) else float("nan") for j in elig]
        bet = fp_beta_block(yex[:, elig], mex, i)
        M = {"m": m, "i": int(i), "keys": keys, "tickers": keys, "cols": elig, "R": R, "b": b, "caps": [None] * len(elig),
             "sectors": ["(없음)"] * len(elig), "beta": [float(x) for x in bet], "exec_ok": exec_ok, "drift": drift,
             "cw": [1.0 / len(elig)] * len(elig)}
        p_ = os.path.join(work, "g6_%s.pkl" % m)
        with open(p_, "wb") as f:
            pickle.dump(M, f, protocol=5)
        paths[m] = p_
        meta[m] = {"n_elig": len(elig), "n_beta": int(np.isfinite(bet).sum())}
    S1 = {}
    for r in pool_map(_task_stage1, [("SSD", m, paths[m]) for m in forms], int(job.get("workers") or N_WORKERS)):
        S1[(r["variant"], r["m"])] = r
    s1p = os.path.join(work, "g6_stage1.pkl")
    with open(s1p, "wb") as f:
        pickle.dump(S1, f, protocol=5)
    _c, chain = _task_chain(("SSD", forms, paths, s1p))
    hsh = canon_hash({m: dict(zip(v["keys"], [round(x, 10) for x in v["w"]])) for m, v in chain.items()})[:16]
    el = [meta[m]["n_elig"] for m in forms]
    counts = {"g6_forms": len(forms), "g6_elig_min": int(min(el)), "g6_elig_max": int(max(el)), "g6_ok1": int(sum(1 for m in forms if chain[m]["status1"] == 0)),
              "g6_ok2": int(sum(1 for m in forms if chain[m].get("status2") == 0)), "g6_carried": int(sum(1 for m in forms if chain[m]["carried"])),
              "g6_ties_gt5pct": int(sum(1 for m in forms if (chain[m].get("tie_l1") or 0.0) > 0.05)), "g6_drops": int(sum(chain[m]["drops"] for m in forms)),
              "g6_names_min": int(min(chain[m]["n"] for m in forms)), "g6_names_max": int(max(chain[m]["n"] for m in forms)),
              "g6_hash16": hsh, "g6_vintage_ok": bool(FI["vintage_ok"]), "g6_first": dates[0], "g6_last": dates[-1],
              "g6_n_missing_cells": int((~np.isfinite(X[me[G6_WARM] - S_WIN:me[G6_HOLD[1]] + 1])).sum())}
    out = {"kind": "ssdix_g6", "mode": job.get("mode"), "counts": counts, "sec": round(time.time() - t0, 1)}
    if job.get("mode") != "bake":
        return out
    # 🚨 굽기 — 책 경로 · 펀드 · 쌍둥이 · Δ(20년 수치는 캐시에만 · 게시 칸은 참/거짓 · 개수 · 2016-09 ~ 반쪽만)
    import eg30plus as E
    i0, iE = me[G6_FIRST], me[G6_HOLD[1]]
    execs = [(chain[m]["exec_i"], np.array([FI["heads"].index(k) for k in chain[m]["keys"]]), np.array([chain[m]["w"]])) for m in forms]
    hold = [mshift(m, 1) for m in months_between(G6_FIRST, G6_LAST)]
    mends = [me[m] for m in months_between(G6_FIRST, G6_LAST)] + [iE]
    Midx = np.cumprod(1.0 + mkt / 100.0)
    gI = np.array([Midx[mends[k + 1]] / Midx[mends[k]] for k in range(len(hold))])
    res = {}
    for c in (COST, COST20):
        i_first, P, turn = book_paths(Pff, Praw, execs, iE, c, i_window=i0, n_years=len(hold) / 12.0)
        pth = P[0]
        gS = np.array([pth[mends[k + 1] - i_first] / pth[mends[k] - i_first] for k in range(len(hold))])
        res[c] = (fund_ex_closed(gI, gS, c), float(turn[0]))
    ex_i = [chain[m]["exec_i"] for m in forms]
    bts = [chain[m]["beta"] for m in forms]
    days = np.arange(i0 + 1, iE + 1)
    gtw = twin_growth(days, 1.0 + mkt[days] / 100.0, 1.0 + rf[days] / 100.0, ex_i, bts)
    tw = np.concatenate([[1.0], np.cumprod(gtw)])
    gT = np.array([tw[mends[k + 1] - i0] / tw[mends[k] - i0] for k in range(len(hold))])
    xdil = fund_ex_closed(gI, gT, 0.0)
    down = gI < 1.0
    d10 = res[COST][0] - xdil
    d20 = res[COST20][0] - xdil
    st = down_delta(d10, down, E)
    h10 = np.array([h >= HOLD[0] for h in hold])
    st_h = down_delta(d10[h10], down[h10], E)
    passed = bool(st["mean"] is not None and st["mean"] > 0 and st["t"] is not None and st["t"] >= G6_T_MIN)
    out.update({"window": list(G6_HOLD), "n": len(hold), "n_down": int(down.sum()), "pass": passed,
                "delta_pos": bool(st["mean"] is not None and st["mean"] > 0), "t_ge1": bool(st["t"] is not None and st["t"] >= G6_T_MIN),
                "cache_only": {"window": list(G6_HOLD), "mean": st["mean"], "t": st["t"], "p": st["p"], "mean20": float(d20[down].mean()),
                               "x_ann": float(res[COST][0].mean() * 12), "turn": res[COST][1]},
                "half10": {"window": [HOLD[0], G6_HOLD[1]], "n": int(h10.sum()), "n_down": int((down & h10).sum()), "mean": st_h["mean"], "t": st_h["t"]}})
    return out


# ══════════════════════════════════════════════════════════════════════════
#  vroot 자식 — 책(🚨 수익 경로 · 굽기 · 연기에서만): SSD · 대조 · 앞 창 · G5 위약(vroot 틀) · 짝맞춤 P1 · P2
# ══════════════════════════════════════════════════════════════════════════
def _vgrid(W):
    """vroot 틀 — 얼린 qbatch_core.Grid(날짜 · SPY 총수익 = 랩 assets.json 수정종가 · 앞값 채움 · 무위험 월)."""
    import numpy as np
    import pandas as pd
    import qbatch_core as Q
    import v_data as VD
    spy = VD.lab_spy_daily().reindex(pd.DatetimeIndex(pd.to_datetime(W["dates"]))).ffill().to_numpy(float)
    G = Q.Grid(W["dates"], spy, spy)
    G.me = dict(W["me"])
    return G, np.asarray(G.IX_TR, float)


def _tbill_daily(G, forms, i0, iE):
    """T-bill 일간 성장(얼린 q_switch.tbill_book 과 같은 식 — 보유월 사이 거래일 수로 나눈 복리) · 날 i0+1 … iE."""
    import numpy as np
    mends = [G.me[m] for m in forms] + [iE]
    g = np.ones(iE - i0)
    for k, m in enumerate(forms):
        a, b = mends[k], mends[k + 1]
        rf_d = (1 + float(G.RF.get(mshift(m, 1), 0.0))) ** (1.0 / max(1, b - a)) - 1
        g[a + 1 - (i0 + 1): b + 1 - (i0 + 1)] = 1 + rf_d
    return g


def _monthly(path_row, mends, i_first):
    import numpy as np
    return np.array([path_row[mends[k + 1] - i_first] / path_row[mends[k] - i_first] for k in range(len(mends) - 1)])


def books_child(job):
    try:
        return _books_body(job)
    except StopBake as e:
        return {"kind": "ssdix_books", "stopped": str(e)[:300]}


def _books_body(job):
    import contextlib
    import numpy as np
    t0 = time.time()
    assert_blobs(HERE, VROOT_BLOBS)
    _vroot_pins(job.get("root") or ROOT)
    import pit_panel as PP
    import qbatch_core as Q
    import eg30plus as E
    if blob_sha1(_rbytes(os.path.join(DATA, "mech_episodes.json")).replace(b"\r\n", b"\n")) != "d67a2a74b486aff7f3a46d0f2a9bebe104df669f":
        raise StopBake("vroot mech_episodes 가 얼린 판이 아니다")
    with contextlib.redirect_stdout(io.StringIO()):
        W = PP.load_world()
    T = _json(job["targets"])
    me = W["me"]
    G, IX = _vgrid(W)
    f_main, f_pre = chain_forms("SSD"), chain_forms("PRE")
    plan = placebo_plan(T["chains"]["SSD"], f_main, T["month_files"], want_draws=True)
    if plan["summary"]["hash16"] != T["placebo_plan"]["hash16"]:
        raise StopBake("위약 뽑기가 목표 자식의 것과 다르다")
    keys = set()
    for c, o in T["chains"].items():
        for v in o.values():
            keys.update(v["keys"])
    for one in plan["draws"]:
        for ks, _w, _b in one:
            keys.update(ks)
    keys = sorted(keys)
    col = {k: q for q, k in enumerate(keys)}
    Praw = np.column_stack([np.asarray(W["PX"][k], float) for k in keys])
    Pff = ffill_cols(Praw)
    i0, iE = me[FORM_FIRST], me[HOLD[1]]
    p0, pE = me[PRE_FIRST], me[PRE_HOLD[1]]
    ME = _json(os.path.join(DATA, "mech_episodes.json"))
    hold = [mshift(m, 1) for m in months_between(FORM_FIRST, FORM_LAST)]
    fz = np.array([h in set(ME["months"]["down_m"]) for h in hold])
    mends = [me[m] for m in months_between(FORM_FIRST, FORM_LAST)] + [iE]
    gI = np.array([IX[mends[k + 1]] / IX[mends[k]] for k in range(len(hold))])
    out_books, turns, xv = {}, {}, {}
    for c in CHAINS + BASKETS:
        o = T["chains"][c]
        fm = f_pre if c == "PRE" else f_main
        execs = [(o[m]["exec_i"], np.array([col[k] for k in o[m]["keys"]]), np.array([o[m]["w"]])) for m in fm]
        a, z = (p0, pE) if c == "PRE" else (i0, iE)
        ny = (len(months_between(PRE_FIRST, PRE_LAST)) if c == "PRE" else N_HOLD) / 12.0
        pp, tt = {}, {}
        for cst in (0.0, COST, COST20):
            i_first, P, turn = book_paths(Pff, Praw, execs, z, cst, i_window=a, n_years=ny)
            pp["%.4f" % cst] = [float(x) for x in P[0][a - i_first:z - i_first + 1]]
            tt["%.4f" % cst] = float(turn[0])
            if cst == COST and c != "PRE":
                xv[c] = fund_ex_closed(gI, _monthly(P[0], mends, i_first), COST)
        out_books[c] = {"dates": [W["dates"][q] for q in range(a, z + 1)], "paths": pp, "turn": tt}
    # 짝맞춤 P1 — 벡터 책 = 얼린 dstk.book_path 옮김(SSD 주 · 10bp)
    o = T["chains"]["SSD"]
    ex_d = [(o[m]["exec_i"], dict(zip(o[m]["keys"], o[m]["w"]))) for m in f_main]
    ref = book_path_ref({k: np.asarray(W["PX"][k], float) for k in keys if any(k in d for _, d in ex_d)}, ex_d, iE, COST, i_window=i0)
    mine = out_books["SSD"]["paths"]["%.4f" % COST]
    p1 = float(max(abs(ref["path"][q] - mine[q - i0]) for q in range(i0, iE + 1)))
    p1t = abs(ref["turn"] - out_books["SSD"]["turn"]["%.4f" % COST])
    # 짝맞춤 P2 — 월 닫힌 식 = 얼린 qbatch_core.fund_from_path(vroot 틀 · SSD 주 · 10bp)
    fr = Q.fund_from_path(G, {"path": {i0 + q: v for q, v in enumerate(mine)}, "turn": None}, months_between(FORM_FIRST, FORM_LAST), cost=COST, basis="TR")
    p2 = float(np.max(np.abs(np.asarray(fr["ex"], float) - xv["SSD"])))
    # 쌍둥이(vroot 틀) · 참 Δ(vroot 틀 — 위약과 같은 틀)
    days = np.arange(i0 + 1, iE + 1)
    g_spy = IX[days] / IX[days - 1]
    g_tb = _tbill_daily(G, months_between(FORM_FIRST, FORM_LAST), i0, iE)

    def twin_x(exec_i, betas):
        g = twin_growth(days, g_spy, g_tb, exec_i, betas)
        tw = np.concatenate([[1.0], np.cumprod(g)])
        return fund_ex_closed(gI, np.array([tw[mends[k + 1] - i0] / tw[mends[k] - i0] for k in range(len(hold))]), 0.0)
    xd_ssd = twin_x([o[m]["exec_i"] for m in f_main], [o[m]["beta"] for m in f_main])
    d_true = xv["SSD"] - xd_ssd
    true_v = float(d_true[fz].mean())
    # G5 위약 — 뽑기 1,000(같은 이름 수 · 상한 · β̂ 띠) · 10bp · 같은 틀
    nd = len(plan["draws"])
    execs_p = []
    ex_idx = [o[m]["exec_i"] for m in f_main]
    for k, m in enumerate(f_main):
        cs = sorted({kk for one in plan["draws"] for kk in one[k][0]})
        pos = {kk: q for q, kk in enumerate(cs)}
        Wm = np.zeros((nd, len(cs)))
        for d, one in enumerate(plan["draws"]):
            ks, ws, _b = one[k]
            for kk, x in zip(ks, ws):
                Wm[d, pos[kk]] = x
        execs_p.append((ex_idx[k], np.array([col[kk] for kk in cs]), Wm))
    i_first, Pp, _turn_p = book_paths(Pff, Praw, execs_p, iE, COST, i_window=i0)
    Xp = np.stack([fund_ex_closed(gI, _monthly(Pp[d], mends, i_first), COST) for d in range(nd)])
    Bp = np.array([[one[k][2] for k in range(len(f_main))] for one in plan["draws"]])
    e_arr = np.asarray(ex_idx, int)
    pos_d = np.searchsorted(e_arr, days, side="left") - 1
    Xdp = []
    for d in range(nd):
        beta = Bp[d][pos_d]
        g = 1.0 + beta * (g_spy - 1.0) + (1.0 - beta) * (g_tb - 1.0)
        tw = np.concatenate([[1.0], np.cumprod(g)])
        Xdp.append(fund_ex_closed(gI, np.array([tw[mends[k + 1] - i0] / tw[mends[k] - i0] for k in range(len(hold))]), 0.0))
    Dp = (Xp - np.stack(Xdp))[:, fz].mean(axis=1)
    pct = float(np.mean(Dp < true_v) * 100.0)
    q_ = lambda pc: float(np.percentile(Dp, pc))
    g5 = {"window": list(HOLD), "k": nd, "seed": SEED_PLACEBO, "band": BETA_BAND, "true": true_v, "pct": pct, "pass": bool(pct >= G5_PCT),
          "q": {"p05": q_(5), "p50": q_(50), "p95": q_(95)}, "n_fallback": plan["summary"]["n_fallback"]}
    # 앞 창(보고만 · vroot 틀) — PRE 사슬 · 보유 2015-04 ~ 2016-08 · 하락월 = 그 틀의 SPY TR 월 < 0
    fpre = months_between(PRE_FIRST, PRE_LAST)
    hp = [mshift(m, 1) for m in fpre]
    mp = [me[m] for m in fpre] + [pE]
    gIp = np.array([IX[mp[k + 1]] / IX[mp[k]] for k in range(len(hp))])
    pth = out_books["PRE"]["paths"]["%.4f" % COST]
    gSp = np.array([pth[mp[k + 1] - p0] / pth[mp[k] - p0] for k in range(len(hp))])
    xp = fund_ex_closed(gIp, gSp, COST)
    dp = np.arange(p0 + 1, pE + 1)
    op = T["chains"]["PRE"]
    gtp = twin_growth(dp, IX[dp] / IX[dp - 1], _tbill_daily(G, fpre, p0, pE), [op[m]["exec_i"] for m in f_pre], [op[m]["beta"] for m in f_pre])
    twp = np.concatenate([[1.0], np.cumprod(gtp)])
    xdp = fund_ex_closed(gIp, np.array([twp[mp[k + 1] - p0] / twp[mp[k] - p0] for k in range(len(hp))]), 0.0)
    dnp = gIp < 1.0
    stp = down_delta(xp - xdp, dnp, E)
    pre = {"window": list(PRE_HOLD), "n": len(hp), "n_down": int(dnp.sum()), "delta_pos": bool(stp["mean"] is not None and stp["mean"] > 0),
           "x_down_pos": bool(dnp.any() and float(xp[dnp].mean()) > 0),
           "cache_only": {"window": list(PRE_HOLD), "mean": stp["mean"], "t": stp["t"], "x_ann": float(xp.mean() * 12),
                          "x_down": (float(xp[dnp].mean()) if dnp.any() else None)}}
    return {"kind": "ssdix_books", "books": out_books, "g5": g5, "pre": pre, "true_v": true_v,
            "pairing": {"P1_max_abs": p1, "P1_turn_abs": float(p1t), "P1_ok": bool(p1 <= 1e-10 and p1t <= 1e-10), "P2_max_abs": p2, "P2_ok": bool(p2 <= 1e-10)},
            "series_v": {"ssd_x": [float(x) for x in xv["SSD"]], "dil_x": [float(x) for x in xd_ssd], "placebo_delta": [float(x) for x in Dp]},
            "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
#  root 자식 S(🚨 굽기 본체) — (A) · (B) · 대조 · 짝맞춤 E0 · E-RD
# ══════════════════════════════════════════════════════════════════════════
def _twin_book(SW, F, name, g_day):
    """항등식 장부(측정용 · 보유하지 않는다) — 일간 성장 g_day · 비용 없음 · 몫 교체도 무비용(cash)."""
    import numpy as np
    bk = SW.Book.__new__(SW.Book)
    bk.name, bk.g0, bk.lg0 = name, np.asarray(g_day, float), np.log(np.asarray(g_day, float))
    bk.lf = {COST: np.zeros(F.T), COST20: np.zeros(F.T)}
    bk.turn, bk.reb_days, bk.cash = {COST: 0.0, COST20: 0.0}, np.array([], int), True
    return bk


def s_child(job):
    try:
        return _s_body(job)
    except StopBake as e:
        return {"kind": "ssdix_s", "stopped": str(e)[:300]}


def _s_body(job):
    import numpy as np
    t0 = time.time()
    assert_blobs(HERE, ROOT_BLOBS)
    import egstep as EG
    import eg30plus as E
    try:
        Q, SW, QC, XA, ctx, F = EG._root_ctx()
    except EG.StopBake as e:
        raise StopBake("EGSTEP 뿌리: %s" % str(e)[:200])
    months, hold = list(F.months), list(F.hold)
    vid, bE, bS, _fr0 = EG._v0_identity(Q, SW, XA, ctx, F, job["qbatch"])
    if not vid["ok"]:
        raise StopBake("C0 가 얼린 V0 와 다르다(짝맞춤 E0)")
    bT = SW.tbill_book(ctx)
    BK = _json(job["books"])
    if BK.get("stopped"):
        raise StopBake("책 자식: %s" % BK["stopped"])
    T = _json(job["targets"])
    try:
        books = {c: XA._book_from_dates(SW, F, c, BK["books"][c]) for c in CHAINS + BASKETS if c != "PRE"}
        vbk = _json(job["v_book"])
        dbk = _json(job["d_book"])
        bV = XA._book_from_dates(SW, F, "V30", vbk)
        bD = XA._book_from_dates(SW, F, "D", dbk)
    except SystemExit as e:
        raise StopBake("장부 날짜가 뿌리 격자와 다르다: %s" % str(e)[:120])
    if list(dbk["months"]) != months or not all(bool(x) for x in dbk["d_ok"]):
        raise StopBake("D 책 달 · 옮김(K1)이 얼린 것과 다르다")
    ones = np.ones(len(months))
    dmask_pr = np.array([h in set(ctx.A.down_months(hold)) for h in hold])
    ME = _json(os.path.join(DATA, "mech_episodes.json"))
    fz = np.array([h in set(ME["months"]["down_m"]) for h in hold])
    crash = np.array([h in set(ME["months"]["crash_m"]) for h in hold])
    surge = np.array([h in set(ME["months"]["surge_m"]) for h in hold])
    if int(fz.sum()) != 35:
        raise StopBake("얼린 하락월이 35 가 아니다")
    keep = ("n", "ann_ex", "te", "ir", "t_iid", "nw_t", "down_n", "down_mean", "down_win", "up_mean", "win", "sleeve_beta", "years", "years_won",
            "n_years", "episodes", "crash_won", "surge_won", "mech", "halves", "blocks", "roll12", "down_capture", "up_capture")
    arms, frs, frs20 = {}, {}, {}

    def put(name, fr, fr20=None):
        ev = Q.evaluate(F.G, fr, dmask_pr)
        ex = np.asarray(fr["ex"], float)
        arms[name] = {"m": {k: ev.get(k) for k in keep}, "turn": fr.get("turn"), "cost_drag": fr.get("cost_drag"),
                      "down_frozen": {"n": int(fz.sum()), "mean": float(ex[fz].mean()), "win": float(np.mean(ex[fz] > 0) * 100)}}
        if fr20 is not None:
            arms[name]["m20"] = {"ann_ex": float(np.asarray(fr20["ex"]).mean() * 12), "nw_t": E.nw_t(np.asarray(fr20["ex"], float))}
        frs[name] = ex
        if fr20 is not None:
            frs20[name] = np.asarray(fr20["ex"], float)

    def twin_of(exec_idx, betas, name):
        g = twin_growth(F.day, bS.g0, bT.g0, exec_idx, betas)
        return _twin_book(SW, F, name, g)
    di = ctx.G.di
    # ── (A) 독립 엔진 · 대조(슬리브 전부 · 첫날부터) — 체결 날은 날짜로 뿌리 격자에 옮긴다(vroot 격자 번호와 다를 수 있다) ──
    ctl = ("SSD", "C3", "C4", "C5", "C7A", "C7B", "C10")
    twins = {}
    for c in ctl:
        o = T["chains"][c]
        fm = chain_forms("SSD")
        if any(o[m].get("exec_d") not in di for m in fm):
            raise StopBake("체결 날짜가 뿌리 격자에 없다(%s)" % c)
        twins[c] = twin_of([di[o[m]["exec_d"]] for m in fm], [o[m]["beta"] for m in fm], "DIL_" + c)
        put(c, XA.mix_t1(F, ones, books[c], bS, COST, Q.fund_from_path), XA.mix_t1(F, ones, books[c], bS, COST20, Q.fund_from_path))
        put("DIL_" + c, XA.mix_t1(F, ones, twins[c], bS, 0.0, Q.fund_from_path))
    DT = _json(job["d_targets"])
    bD_beta = [((DT["months"].get(m) or {}).get("beta_D") if (DT["months"].get(m) or {}).get("beta_D") is not None else 1.0) for m in months]
    twins["C2"] = twin_of([ctx.G.me[m] for m in months], bD_beta, "DIL_C2")
    put("C2", XA.mix_t1(F, ones, bD, bS, COST, Q.fund_from_path), XA.mix_t1(F, ones, bD, bS, COST20, Q.fund_from_path))
    put("DIL_C2", XA.mix_t1(F, ones, twins["C2"], bS, 0.0, Q.fund_from_path))
    dA = frs["SSD"] - frs["DIL_SSD"]
    dA20 = frs20["SSD"] - frs["DIL_SSD"]
    primary = {"A": dict(down_delta(dA, fz, E), mask="down_frozen")}
    rb = rebound_claim(frs["SSD"], crash, surge)
    lb = lb80(frs["SSD"])
    blocks = block_deltas(dA, fz)
    gin_A = {"G1": rb["ok"], "G2": bool(lb is not None and lb > G2_LB), "G3": bool(float(dA20[fz].mean()) > 0),
             "G4": bool(sum(1 for x in blocks if x is not None and x > 0) >= G4_MIN)}
    detail_A = {"rebound": rb, "lb80": lb, "delta20_down": float(dA20[fz].mean()), "blocks": blocks,
                "halves": [float(dA[fz & np.array([h < "2021-09" for h in hold])].mean()), float(dA[fz & np.array([h >= "2021-09" for h in hold])].mean())],
                "x_down": float(frs["SSD"][fz].mean()), "x_up": float(frs["SSD"][~fz].mean()), "dil_down": float(frs["DIL_SSD"][fz].mean()),
                "beta_med": float(np.median([T["chains"]["SSD"][m]["beta"] for m in chain_forms("SSD")]))}
    ctrl = {}
    for c in ctl + ("C2",):
        d = frs[c] - frs["DIL_" + c]
        st = down_delta(d, fz, E)
        ctrl[c] = {"delta_down": st["mean"], "t": st["t"], "x_ann": float(frs[c].mean() * 12), "x_down": float(frs[c][fz].mean()),
                   "x_up": float(frs[c][~fz].mean()), "x20_ann": (float(frs20[c].mean() * 12) if c in frs20 else None),
                   "vs_ssd_down": float(frs[c][fz].mean() - frs["SSD"][fz].mean())}
    # ── (B) 방어 스텝 목적지(얼린 EGSTEP RD · D 자리만 바꾼다) ──
    Dq, T1, T2 = EG.q06_states(QC, ctx, F)
    R = {m: int(vbk["R"][m]) for m in months}
    aR = np.array([R[m] for m in months], np.int8)
    aD = np.array([Dq[m] for m in months], np.int8)
    aT1 = np.array([T1[m] for m in months], np.int8)
    aT2 = np.array([T2[m] for m in months], np.int8)
    sc = EG.state_counts(aR, aD, aT1, aT2)
    try:
        EG.check_state_counts(sc, EG.F0_EXPECT)
    except EG.StopBake as e:
        raise StopBake("EGSTEP 상태 개수: %s" % str(e)[:200])
    SH = EG.arm_shares(aR, aD, aT1, aT2)
    bk_D = {"E": bE, "V": bV, "D": bD, "S": bS}
    bk_S = {"E": bE, "V": bV, "D": books["SSD"], "S": bS}
    bk_T = {"E": bE, "V": bV, "D": twins["SSD"], "S": bS}
    for nm, bk in (("RD", bk_D), ("RDSSD", bk_S), ("RDTWIN", bk_T)):
        put(nm, EG.run_arm(F, SH["RD"], bk, COST, XA, Q), EG.run_arm(F, SH["RD"], bk, COST20, XA, Q))
    put("C0", EG.run_arm(F, SH["C0"], bk_D, COST, XA, Q), EG.run_arm(F, SH["C0"], bk_D, COST20, XA, Q))
    # 짝맞춤 E-RD — 이 굽기의 RD · C0 = EGSTEP 굽기 산출(sha 핀)의 RD · C0
    EGo = _json(job["egstep_out"])
    ser = ((EGo.get("series") or {}).get("ex") or {})
    e_rd = float(np.max(np.abs(np.asarray(ser.get("RD"), float) - frs["RD"]))) if ser.get("RD") else None
    e_c0 = float(np.max(np.abs(np.asarray(ser.get("C0"), float) - frs["C0"]))) if ser.get("C0") else None
    del EGo, ser
    e_ok = bool(e_rd is not None and e_c0 is not None and e_rd <= 1e-10 and e_c0 <= 1e-10)
    if not e_ok:
        raise StopBake("짝맞춤 E-RD 실패(이 굽기의 RD · C0 ≠ EGSTEP 굽기 산출)")
    dB = frs["RDSSD"] - frs["RD"]
    dB20 = frs20["RDSSD"] - frs20["RD"]
    dT = frs["RDTWIN"] - frs["RD"]
    dT20 = frs20["RDTWIN"] - frs20["RD"]
    primary["B"] = dict(down_delta(dB, fz, E), mask="down_frozen")
    reb = lambda nm: (arms[nm]["m"]["mech"] or {}).get("rebounds", {}).get("win")
    gin_B = {"h1": bool(float(dB20.mean()) >= 0), "h2": bool(reb("RDSSD") is not None and reb("RD") is not None and reb("RDSSD") >= reb("RD") - REB_SLACK),
             "h3": bool(arms["RDSSD"]["turn"] is not None and arms["RDSSD"]["turn"] <= TURN_MAX),
             "d1": bool(float(dB[fz].mean()) > float(dT[fz].mean())), "d2": bool(float(dB20.mean()) >= float(dT20.mean()))}
    masks = EG.state_masks(aR, aD)
    detail_B = {"all_ann": float(dB.mean() * 12), "all20_ann": float(dB20.mean() * 12), "twin_down": float(dT[fz].mean()), "twin_all20_ann": float(dT20.mean() * 12),
                "rebounds": {"RDSSD": reb("RDSSD"), "RD": reb("RD")}, "turn": arms["RDSSD"]["turn"],
                "d_on_down": {"n": int((masks["d_on"] & fz).sum()), "mean": (float(dB[masks["d_on"] & fz].mean()) if (masks["d_on"] & fz).any() else None)},
                "crash_m": float(dB[crash].mean()), "surge_m": float(dB[surge].mean()), "states": sc}
    ya = {a: (arms[a]["m"].get("years") or {}) for a in arms}
    out = {"kind": "ssdix_s", "window": list(HOLD), "n_hold": len(hold), "arms": arms, "primary": primary, "gates_in": {"A": gin_A, "B": gin_B},
           "detail": {"A": detail_A, "B": detail_B}, "controls": ctrl,
           "years_delta": {"A": {y: float(ya["SSD"][y] - ya["DIL_SSD"][y]) for y in sorted(set(ya["SSD"]) & set(ya["DIL_SSD"]))},
                           "B": {y: float(ya["RDSSD"][y] - ya["RD"][y]) for y in sorted(set(ya["RDSSD"]) & set(ya["RD"]))}},
           "pairing": {"E0": vid, "E_RD": {"rd_max_abs": e_rd, "c0_max_abs": e_c0, "ok": e_ok}},
           "down": {"n_frozen": int(fz.sum()), "n_pr": int(dmask_pr.sum()), "n_crash_m": int(crash.sum()), "n_surge_m": int(surge.sum())},
           "series": {"hold": hold, "ex": {a: [float(x) for x in frs[a]] for a in frs}, "ex20": {a: [float(x) for x in frs20[a]] for a in frs20}},
           "sec": round(time.time() - t0, 1)}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  vroot 자식 — 판정(얼린 v_tests.holm · dsr) · 관문 · 채택 표시 · 읽기 · 예측 · 다중성
# ══════════════════════════════════════════════════════════════════════════
def readings(S, B, G6):
    """표시의 읽기(계산 전 고정 · 표시를 바꾸지 않는다) — 참 = 그 약점이 읽혔다."""
    dA, dB = S["detail"]["A"], S["detail"]["B"]
    C = S["controls"]
    return {"A": {"bull_lag": bool(dA["x_up"] < 0), "variance_like": bool((C["C3"]["delta_down"] or -9) >= (S["primary"]["A"]["mean"] or 0)),
                  "sector_bet": bool((C["C10"]["delta_down"] or -9) < 0.5 * (S["primary"]["A"]["mean"] or 0)),
                  "size_like": bool((C["C7A"]["delta_down"] or -9) >= (S["primary"]["A"]["mean"] or 0)),
                  "pre_window_weak": bool(not (B.get("pre") or {}).get("delta_pos")), "half10_g6_weak": bool(not ((G6.get("half10") or {}).get("mean") or -1) > 0)},
            "B": {"beta_only": bool(not S["gates_in"]["B"]["d1"]), "surge_cost": bool(dB["surge_m"] < 0),
                  "few_months": bool((dB["d_on_down"]["n"] or 0) < 10)}}


def predictions(M):
    """미리 적은 예측(계산 전 고정 · 결과 문서가 채점) — 참/거짓만."""
    S = M["S"]
    P = {}
    P["P1_no_rejection"] = bool(not any(M["family"]["reject"].values()))
    P["P2_no_adoption"] = bool(not any(M["adopt"].values()))
    P["P3_beta_below1"] = bool(S["detail"]["A"]["beta_med"] < 1.0)
    P["P4_down_x_pos"] = bool(S["detail"]["A"]["x_down"] > 0)
    P["P5_delta_a_pos"] = bool((S["primary"]["A"]["mean"] or 0) > 0)
    P["P6_up_x_neg"] = bool(S["detail"]["A"]["x_up"] < 0)
    P["P7_rebound_claim_fails"] = bool(not S["gates_in"]["A"]["G1"])
    P["P8_delta_b_pos"] = bool((S["primary"]["B"]["mean"] or 0) > 0)
    P["P9_g6_delta_pos"] = bool(M["G6"].get("delta_pos"))
    return P


def judge_child(job):
    import numpy as np
    t0 = time.time()
    assert_blobs(HERE, VROOT_BLOBS)
    S = _json(job["s_out"])
    B = _json(job["books_out"])
    G6 = _json(job["g6_out"])
    F0 = _json(job["f0"])
    for nm, x in (("s", S), ("books", B), ("g6", G6)):
        if x.get("stopped"):
            return {"kind": "ssdix_out", "stopped": "%s: %s" % (nm, x["stopped"])}
    if (G6.get("counts") or {}) != (F0.get("g6") or {}):                  # 굽기의 G6 목표(다시 푼 LP) = 등록 F0 의 G6 개수 · 해시
        return {"kind": "ssdix_out", "stopped": "G6 목표가 등록 F0 와 다르다"}
    if not ((B.get("pairing") or {}).get("P1_ok") and (B.get("pairing") or {}).get("P2_ok")):
        return {"kind": "ssdix_out", "stopped": "짝맞춤 P1 · P2 실패(벡터 책 · 월 닫힌 식)"}
    gin = {"A": dict(S["gates_in"]["A"]), "B": dict(S["gates_in"]["B"])}
    gin["A"]["G0"] = bool(((F0.get("f0r") or {}).get("g0") or {}).get("pass"))
    gin["A"]["G5"] = bool((B.get("g5") or {}).get("pass"))
    gin["A"]["G6"] = bool(G6.get("pass"))
    M = {"primary": S["primary"], "gates_in": gin}
    try:
        fam, gates, adopt, vd = judge_core(M)
    except StopBake as e:
        return {"kind": "ssdix_out", "stopped": str(e)[:300]}
    import v_tests as VT
    n_after = CUM_N_BEFORE + N_ROWS_COUNTED
    dsr = VT.dsr(np.asarray(S["series"]["ex"]["SSD"], float), n_after)
    out = {k: S[k] for k in ("window", "n_hold", "arms", "primary", "detail", "controls", "years_delta", "pairing", "down") if k in S}
    out.update({"kind": "ssdix_out", "gates_in": gin, "family": fam, "gates": gates, "adopt": adopt, "verdict": vd,
                "g5": B.get("g5"), "pre": B.get("pre"), "books_pairing": B.get("pairing"), "g6": {k: G6[k] for k in G6 if k not in ("kind",)},
                "g0": ((F0.get("f0r") or {}).get("g0")), "dsr": {k: dsr.get(k) for k in ("N", "sr_m", "sr0", "dsr")},
                "multiplicity": {"m_confirmatory": len(PRIMARY), "alpha": HOLM_ALPHA, "cum_n_before": CUM_N_BEFORE, "rows_counted": N_ROWS_COUNTED,
                                 "cum_n_after": n_after, "counted": list(COUNTED)}})
    out["readings"] = readings(S, B, G6)
    out["predictions"] = predictions({"S": S, "family": fam, "adopt": adopt, "G6": G6})
    out["sec"] = {"judge": round(time.time() - t0, 1), "s": S.get("sec"), "books": B.get("sec"), "g6": G6.get("sec")}
    return out


# ══════════════════════════════════════════════════════════════════════════
def child_main(argv):
    """러너가 부른다: python -X utf8 <뿌리>/build/ssdix.py --child targets|f0r|g6|books|s|judge --job <작업 파일> --out <경로>."""
    mode = argv[argv.index("--child") + 1]
    job = _json(argv[argv.index("--job") + 1])
    outp = argv[argv.index("--out") + 1]
    import warnings
    warnings.simplefilter("ignore")
    import numpy as np
    fn = {"targets": targets_child, "f0r": f0r_child, "g6": g6_child, "books": books_child, "s": s_child, "judge": judge_child}.get(mode)
    if fn is None:
        raise SystemExit("모르는 자식 방식: %s" % mode)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        res = fn(job)
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
