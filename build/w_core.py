# -*- coding: utf-8 -*-
"""build/w_core.py — 배치 W 공통 바탕: 얼린 V 모듈 핀(ada1e16ae) · 20년 창 규칙 · 등록 가족(표본 안 확증 · Holm) · 채택 표시 ·
Tier-2 펀드 틀 무해 판정(frozen v_core.fund_x · 투영 재사용) · 재현성(스레드 · 해시 씨앗 · manifest) · 등록 자물쇠 · 캐시 경계.

설계 원본(구속): wbatch_research.json final(slate.common_frame · evaluation.tier2 · oos_protocol.reproducibility · build_plan.may_import ·
  registration · multiplicity) + 갱신 둘(2026-09-27 · 명세와 어긋나면 이것이 이긴다 — (가)는 사용자 말 · (나)는 그 귀결로 오케스트레이터가 정한 것):
  (가) 사용자 «이런 불필요한 미래 일정들은 다 꺼 · QFWD까지 모두 끄라» — 전방 원장이 없다: data/_wfwd/genesis.json · WFWD · FF1/FF2 · e-과정 전방 보고 · 날짜 박힌 미래 판정을 만들지 않는다 ·
       W13(전방 전용 카드)은 뺐다.
  (나) 🔎 오케스트레이터 결정(사용자 규칙 가의 귀결 · 계산 전 · 사용자가 구성원 · α · 채택 식을 고르지 않았다 — 비평 2 M4):
       전방 원장이 유일한 채택 경로였으므로 계산 전에 **표본 안 확증 가족**을 지금 고정한다:
       등록 A 가족 = {W01 IPCA-KPS8 · W04 CIQ-LT · W10m TAILX} · 등록 B 가족 = {W02 GEO-X · W11 FRAG}(B 를 등록할 때 제 Holm) ·
       카드마다 Tier-1 FM γ 의 NW(3) t 를 미리 적은 방향으로 한쪽 Holm α 0.05.
       채택 표시(펀드 슬리브 후보) = Holm 기각 ∧ Tier-2 무해(20bp 연 X ≥ 0 ∧ 하락월 X ≥ 0 ∧ 회전 ≤ 10 ∧ T+1 행) ∧ G-EGD 통과.
       W03 · W06 · W12 는 측정만 · 스텝 S3e/S2/S1 은 W01 위 Δ 로만 보고 · 채택 카드를 실제 펀드에 붙이는 것은 결과 문서 뒤 사용자 결정(날짜 없음).
       명세의 m = 0 + 전방 경로는 사용자 규칙 때문에 계산 전에 이 가족으로 바뀌었다(§0 · §8 에 공개) · 정직한 검정력 ≈ 0.2–0.3.
  사용자 규칙 2026-09-27 «백테스트 최대 기간은 최근 20년» — 모든 평가 창은 최근 20년 안(보유월 ≥ 2006-09) · 공개 사이트는 10년.

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  K1 🔁 가족 p(등록 전 보정 · 비평 1 C1 · M4) = **제약 야생 부트스트랩 p**(w_stagem S11 — 귀무 아래 제약 적합의 잔차에 Rademacher 부호 · B 9,999 ·
     씨앗 SEED + FAMILY_SEED_OFF[카드] · 통계 = 같은 NW(3) t) · p_one = (1 + #{d·t* ≥ d·t}) / (B + 1). 이유: NW(3) t 를 t(T−1) 로 읽으면 T 119 에서
     크기가 부풀고(합성: FM 두쪽 6.2% · α/3 한쪽 2.06%) 영이 많은 상태 교차항(W11)은 훨씬 더 부푼다(α/2 한쪽 5.6 ~ 8.4%) — 부트스트랩은 같은 설계 ·
     같은 상태 · 같은 |잔차| 로 귀무 분포를 만들어 지렛대 · 이분산을 그대로 싣는다. t(T−1) p(교차항은 t(n−2))는 보고 칸(p_t)으로 남는다.
  K2 Holm 은 frozen v_tests.holm(작은 p 부터 α/(m − j) · 한 번 못 넘으면 멈춘다 · 빠진 카드는 p 없음으로 분모에 남는다 — 가족을 줄이지 않는다) ·
     카드 위생(라벨 섞기 · 심은 신호 — 카드마다) 실패 카드도 p 없음으로 분모에 남는다(R10 · 기각 없음 · 표시 없음).
  K3 20년 창: 마지막 보유월 2026-08 에서 240개월 → 보유월 하한 2006-09(결정월 하한 2006-08). 추정 되돌아보기(예 IPCA S-E 2010-01~ · W03 Π̂ 60개월)는
     신호의 입력이지 평가 창이 아니다 — 평가 계열(Tier-1 γ 달 · Tier-2 X 달 · L 쌍둥이 월 계열)만 이 하한으로 자르고 점검한다.
  K4 Tier-2 무해: X = frozen v_core.fund_x(주 행 T+1 · 20bp = mult 2.0) · «20bp 연 X» = 월 평균 × 12(점) · «하락월 X» = 동결 mech_episodes down_m
     (S&P 500 가격수익 < 0 · 35달) 달의 X 평균(점) · 하락월이 창에 하나도 없으면 무해가 아니다(판정 불가 = 거짓).
  K5 채택 표시는 갱신(나 · 오케스트레이터 결정)의 세 조건 그대로다. 명세 adoption_marks 의 나머지 칸((v) «V 재포장» · (vi) 카드 조건 — W01 DM t > 0 ·
     W04 «DNBETA 재포장» · W02 CBSA 섞기 · W11 자료 관문)은 표시를 바꾸지 않는 **주의 칸**으로 함께 싣는다(사용자 식이 완결 정의라서 — 공개).
     위생 실패는 굽기 자체를 막는다(표시 이전 단계) · 시총 앵커 · 커버리지는 F0 관문.
  K6 씨앗 SEED = 20260927(배치 W 날짜) · 쓰는 곳마다 SEED + 0..4 를 명시한다.

  python build/w_core.py --selftest
  python build/w_core.py --frozen          얼린 V 모듈 핀 대조(디스크 · 불러온 모듈)
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import traceback

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ══════════════════════════════════════════════════════════════════════════
#  커밋 · 캐시
# ══════════════════════════════════════════════════════════════════════════
V_COMMIT = "ada1e16ae9772a95246198407acb2f1e51a1906f"          # 배치 V 등록 커밋 — 얼린 V 모듈 핀의 원천
V_RESULT_COMMIT = "889b1c63483313fb27c45ba62ad8e6c8700d7a09"   # 배치 V 결과(이미 봤다 · §0 공개)
R_REG_COMMIT = "168a072ff0b0ba8f895a79fd8dabaf34b35d8ed6"      # 배치 R 등록 커밋
R_RESULT_COMMIT = "958557496fbb5935f3c93a05ea47dc0fdd7255a3"   # 배치 R 결과(이미 봤다 · 짝맞춤 감사가 재현하는 공개 값)
CACHE = os.environ.get("WBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "wbatch_cache")
VB_CACHE = os.environ.get("VBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "vbatch_cache")   # 읽기 전용(V F0 입력 · G-EGD 표)
SEED = 20260927                                                # K6


def _inside(p, root):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(root))
    return a == r or a.startswith(r + os.sep)


def cache_dir(*parts, create=True):
    """저장소 밖 캐시(%TEMP%/wbatch_cache) 아래 경로 — 저장소 안이거나 V 캐시(읽기 전용) 안이면 멈춘다."""
    if _inside(CACHE, ROOT):
        raise SystemExit("🚨 WBATCH_CACHE 가 저장소 안이다 — 원자료 · 중간 산출은 저장소 밖에만")
    p = os.path.join(CACHE, *parts)
    if _inside(p, VB_CACHE):
        raise SystemExit("🚨 V 캐시는 읽기 전용이다: %s" % p)
    if create:
        os.makedirs(p if not os.path.splitext(p)[1] else os.path.dirname(p), exist_ok=True)
    return p


def assert_writable(path):
    """쓰기 대상 점검 — V 캐시(읽기 전용) · 저장소 data/_wfwd(전방 원장 없음) 에는 쓰지 않는다."""
    if _inside(path, VB_CACHE):
        raise SystemExit("🚨 V 캐시는 읽기 전용이다: %s" % path)
    assert_no_forward([path])
    return True


# ══════════════════════════════════════════════════════════════════════════
#  달 산수 · 20년 창(사용자 규칙 2026-09-27 · K3)
# ══════════════════════════════════════════════════════════════════════════
def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + int(k)
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def months_between(a, b):
    out, m = [], a[:7]
    while m <= b[:7]:
        out.append(m)
        m = mshift(m, 1)
    return out


def mno(ym):
    return int(ym[:4]) * 12 + int(ym[5:7]) - 1


MAX_YEARS = 20
LAST_HOLD = "2026-08"                                          # 마지막 보유월(S 창 끝 · 자료 끝)
HOLD_FLOOR = mshift(LAST_HOLD, -(12 * MAX_YEARS - 1))          # "2006-09" — 보유월 하한
DECISION_FLOOR = mshift(HOLD_FLOOR, -1)                        # "2006-08" — 결정월 하한
S_WIN = ("2016-09", "2026-08")                                 # Tier-2 보유월 120(명세 evaluation.tier2.window)
PUBLIC_YEARS = 10
PUBLIC_WIN = (mshift(LAST_HOLD, -(12 * PUBLIC_YEARS - 1)), LAST_HOLD)   # 공개 사이트 10년 = S 창
assert HOLD_FLOOR == "2006-09" and PUBLIC_WIN == S_WIN


def _mkey(x):
    s = str(x)
    if not re.match(r"^\d{4}-\d{2}", s):
        raise SystemExit("🚨 달 표기가 아니다: %r" % (x,))
    return s[:7]


def assert_window(months, what="", basis="hold"):
    """평가 계열의 달이 최근 20년 안인지 — basis="hold"(보유월 ≥ 2006-09) · "decision"(결정월 ≥ 2006-08). 넘으면 멈춘다."""
    floor = HOLD_FLOOR if basis == "hold" else DECISION_FLOOR
    ms = [_mkey(m) for m in months]
    bad = [m for m in ms if m < floor or m > LAST_HOLD]
    if bad:
        raise SystemExit("🚨 20년 창 위반(%s · %s ≥ %s ~ %s): %s%s" % (what, basis, floor, LAST_HOLD, bad[:5], " …" if len(bad) > 5 else ""))
    return True


def trim_window(obj, basis="hold"):
    """계열을 20년 창으로 자른다 — dict{달: 값} · pandas Series(PeriodIndex · 문자열 색인) · [(달, 값)]. W03 내부 L 쌍둥이(French) 등."""
    floor = HOLD_FLOOR if basis == "hold" else DECISION_FLOOR
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if floor <= _mkey(k) <= LAST_HOLD}
    if isinstance(obj, (list, tuple)):
        return [(k, v) for k, v in obj if floor <= _mkey(k) <= LAST_HOLD]
    import pandas as pd
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        keys = [_mkey(i) for i in obj.index]
        mask = [floor <= k <= LAST_HOLD for k in keys]
        return obj.loc[mask]
    raise TypeError("trim_window: 모르는 모양 %s" % type(obj).__name__)


# ══════════════════════════════════════════════════════════════════════════
#  등록 가족 · 카드 역할(사용자 갱신 (가)(나))
# ══════════════════════════════════════════════════════════════════════════
CARD_DIRECTION = {          # Tier-1 주 통계의 미리 적은 방향(명세 카드 primary_statistic · H1)
    "W01": +1,              # z(r̂) FM γ > 0
    "W04": +1,              # z(β^CIQ) FM γ > 0
    "W10m": +1,             # z(tail)·z(IQR) 교차항 γ > 0
    "W02": +1,              # G FM γ > 0
    "W11": -1,              # z(F)·s 교차항 γ < 0
    "W03": +1,              # PAP 롱숏 월수익 > 0(시계열 · 측정만)
    "W12": +1,              # 발표일 − 비발표일 베타 기울기 > 0(측정만)
}
FAMILY = {"A": ("W01", "W04", "W10m"), "B": ("W02", "W11")}
FAMILY_ALPHA = 0.05          # 한쪽 · Holm(가족마다)
MEASURE_ONLY = ("W03", "W06", "W12")
STEP_BASE, STEPS = "W01", ("S3e", "S2", "S1")                 # 스텝은 W01 위 Δ 로만 보고
DROPPED = {"W13": "사용자 갱신(가) — 전방 전용 카드 · 전방 원장 없음", "W05": "명세 removed(D19) · 자료 탐침만",
           "W07": "보류(U1 — PyTorch 설치하지 않는다)", "W08": "명세 removed(버림)", "W09": "명세 removed(종결 메모)"}
REGISTRATION = {"A": {"cards": ("W01", "W04", "W03", "W06", "W12", "W10m"), "steps": STEPS, "family": FAMILY["A"]},
                "B": {"cards": ("W02", "W11"), "family": FAMILY["B"]}}
HONEST_POWER = "카드당 Tier-1 1.645 검정력 ≈ 0.2–0.3(명세 honest_outlook · 합성) — Holm 가족 α 0.05 에서는 더 낮다"
FAMILY_NOTE = ("명세의 확증 가족 m = 0 과 전방 원장(WFWD) 채택 경로는 사용자 규칙(2026-09-27 «미래 일정은 다 꺼 · QFWD 까지 모두 끄라») 때문에 "
               "계산 전에 표본 안 확증 가족(등록 A {W01 · W04 · W10m} · 등록 B {W02 · W11} · 한쪽 Holm α 0.05)으로 바뀌었다 — 가족 구성원 · α · 채택 식은 "
               "그 규칙의 귀결로 오케스트레이터가 정했다(사용자가 고른 것이 아니다)")
FORWARD_LEDGER = None        # 사용자 갱신(가) — 전방 원장 없음
NO_FORWARD_MARKS = ("data/_wfwd", "wfwd", "genesis.json")


def assert_no_forward(paths):
    """전방 원장 산출이 없다 — data/_wfwd · WFWD · genesis.json 모양의 경로를 만들거나 쓰면 멈춘다(사용자 갱신 가)."""
    for p in paths or ():
        s = str(p).replace("\\", "/").lower()
        if any(mk in s for mk in NO_FORWARD_MARKS):
            raise SystemExit("🚨 전방 원장은 없다(사용자 갱신 2026-09-27) — %s" % p)
    return True


def one_sided_p(t, T, direction, df=None):
    """K1 보고 칸(p_t) — 한쪽 p = P(t(df) ≥ d·t) · df 기본 T − 1(평균 · FM) · 교차항(모수 둘)은 df = n − 2 를 넘긴다. t · T 가 없으면 None.
    가족 판정은 이 값이 아니라 야생 부트스트랩 p(w_stagem S11)다."""
    if t is None or T is None or not (t == t) or T < 3 or direction not in (+1, -1):
        return None
    from scipy.stats import t as td
    return float(td.sf(direction * float(t), int(df if df is not None else int(T) - 1)))


FAMILY_SEED_OFF = {"W01": 501, "W04": 502, "W10m": 503, "W02": 504, "W11": 505}   # K1 — 가족 p 의 부트스트랩 씨앗(SEED + 이 값)
WILD_B = 9999                                                                   # K1 — 가족 p 의 부트스트랩 반복


def holm_family(stats, reg, *, alpha):
    """등록 가족의 한쪽 Holm(K2) — stats = {카드: {"t": NW(3) t, "T": 달 수, "p_wild_one": 야생 부트스트랩 한쪽 p(K1), "direction", "B", "df",
    "hygiene_fail"}} · α 는 명시 인자(FAMILY_ALPHA 0.05 를 넘긴다 · 기본값 없음).
    가족은 고정: 가족 밖 카드가 들어오면 멈추고 빠진 카드는 p 없음.
    돌려주는 것 {reject{카드: bool}, p{카드}, threshold, order, m, alpha, family}."""
    fam = FAMILY[reg]
    extra = sorted(set(stats) - set(fam))
    if extra:
        raise SystemExit("🚨 가족 %s 밖 카드가 Holm 에 들어왔다: %s(가족은 등록 전 고정 %s)" % (reg, extra, fam))
    if alpha != FAMILY_ALPHA:
        raise SystemExit("🚨 가족 α 는 등록 값 %.2f 이다(넘긴 값 %r)" % (FAMILY_ALPHA, alpha))
    pv, pt = {}, {}
    for c in fam:
        st = stats.get(c) or {}
        if st.get("direction") is not None and st["direction"] != CARD_DIRECTION[c]:
            raise SystemExit("🚨 %s 의 가족 통계 방향 %r 가 등록 방향 %+d 와 다르다" % (c, st["direction"], CARD_DIRECTION[c]))
        if st.get("t") is not None and "p_wild_one" not in st:
            raise SystemExit("🚨 %s 의 가족 통계에 야생 부트스트랩 p(p_wild_one)가 없다(K1 — t(T−1) p 로 판정하지 않는다)" % c)
        p = st.get("p_wild_one")
        if p is not None and not (0.0 < float(p) <= 1.0):
            raise SystemExit("🚨 %s 의 p %r 가 (0, 1] 밖이다" % (c, p))
        if p is not None and st.get("B") not in (None, WILD_B):
            raise SystemExit("🚨 %s 의 부트스트랩 반복 %r 가 등록 값 %d 이 아니다" % (c, st.get("B"), WILD_B))
        pv[c] = None if (p is None or st.get("hygiene_fail")) else float(p)
        pt[c] = one_sided_p(st.get("t"), st.get("T"), CARD_DIRECTION[c], df=st.get("df"))
    H = frozen("v_tests").holm(pv, alpha=alpha)
    return dict(H, p=pv, p_t=pt, family=list(fam), reg=reg, direction={c: CARD_DIRECTION[c] for c in fam},
                hygiene_fail=sorted(c for c in fam if (stats.get(c) or {}).get("hygiene_fail")), p_rule="K1 — 제약 야생 부트스트랩(Rademacher · B %d)" % WILD_B)


def adoption_mark(holm_reject, harmless, gegd_pass):
    """채택 표시(갱신 나 — 오케스트레이터 결정 · K5) = Holm 기각 ∧ Tier-2 무해 ∧ G-EGD 통과 — 셋 모두 참(True)일 때만. None 은 거짓."""
    return bool(holm_reject is True and harmless is True and gegd_pass is True)


def adoption_table(holm, harmless, gegd, cautions=None):
    """가족 카드마다 표시 · 조건 · 주의 칸(K5 — 표시를 바꾸지 않는다). 측정만 · 뺀 카드는 표시 없음으로 싣는다."""
    out = {}
    for c in holm["family"]:
        conds = {"holm_reject": bool(holm["reject"].get(c)), "tier2_harmless": bool((harmless.get(c) or {}).get("harmless") is True),
                 "gegd_pass": bool(gegd.get(c) is True)}
        out[c] = {"path": "표본 안 확증 가족 %s" % holm["reg"], "conds": conds,
                  "adopt": adoption_mark(conds["holm_reject"], conds["tier2_harmless"], conds["gegd_pass"]),
                  "cautions": dict((cautions or {}).get(c) or {})}
    for c in MEASURE_ONLY:
        out.setdefault(c, {"path": "측정만", "adopt": False})
    for c, why in DROPPED.items():
        out.setdefault(c, {"path": "뺌 — " + why, "adopt": False})
    return out


# ══════════════════════════════════════════════════════════════════════════
#  얼린 V 모듈 — 등록 커밋 ada1e16ae 의 blob sha1(git) 핀 · 어긋나면 멈춘다
# ══════════════════════════════════════════════════════════════════════════
FROZEN_PINS = {       # may_import 폐포 26 모듈 — git rev-parse ada1e16ae:build/<m>.py (2026-09-27 · 작업 사본과 모두 같음)
    "edgar": "78bbeb3f81c6d81dfef234a70d8f852eb6aea7fa",
    "index_members": "7850ef55f5b89583b24e190b250a14c897c93395",
    "maxyears": "44dd6f9b82d06b95c875e43846dc65961c1c9efc",
    "mech_episodes": "161080fd9244c060a7a94c559044de3e3ddcc27c",
    "ml_core": "bc262ca8599d200d7883cee6b27c1ee9cf2030c8",
    "ml_strats": "dc43162ddf9f015dbf8eee89475f9ffac418fea4",
    "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b",
    "pit_backtest": "54c00f490ee46fc884556ea1f0f97943e986321c",
    "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38",
    "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513",
    "shares_clean": "8a08e449a33554ab4850c3e3ced7549c3fa889a4",
    "shares_split": "10ed619128087431f2efe4550e375e3ceaff0652",
    "t_pit": "e65e22b05da171bf19b740c2428fe0377683c721",
    "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
    "v_alloc": "dac72a669f55085b735772637c1ad4618e6c8213",
    "v_cards": "aadaf24f173579d3f3146014aa150a4ca07eb0a5",
    "v_cond": "d25914deb89490410ea2dca56b5999356628821e",
    "v_core": "bdba648f1d790748cd5008ceeea3c5eee9d733c8",
    "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a",
    "v_ear": "620fbcfd0cc0917e7062a1b8ab23145912559185",
    "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e",
    "v_guard": "33255c121c10fec2115136223948b1c75c917f08",
    "v_ins": "125fb1932a6da3f3c73ccf29afadb8ddac507f30",
    "v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689",
    "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
    "v_tests": "2f1ec4db1cd7458564da73ec5ad88cef8a0b2f2f",
}
FROZEN_DATA_PINS = {  # 평가에 쓰는 동결 자료(sha256 · 바이트 그대로 · ada1e16ae 판과 같음)
    "data/mech_episodes.json": "384b253059607dce84b0e38645ab79db5ecf82e09616693b386f4f762f9020df",
}


def blob_sha1(path):
    """git blob id(sha1('blob <n>\\0' + LF 바이트)) — CRLF 로 꺼낸 사본도 같은 id 가 되게 CRLF → LF 로 잰다."""
    with open(path, "rb") as f:
        b = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _check_file(name, path):
    pin = FROZEN_PINS.get(name)
    if pin is None:
        raise SystemExit("🚨 %s 는 얼린 V 핀 목록(may_import 폐포)에 없다" % name)
    got = blob_sha1(path)
    if got != pin:
        raise SystemExit("🚨 얼린 모듈 %s 가 V 등록 커밋 %s 판과 다르다(%s ≠ %s · %s)" % (name, V_COMMIT[:9], got[:12], pin[:12], path))
    return True


def frozen(name):
    """얼린 V 모듈을 불러 핀을 대조한다 — 이미 불러온 것이면 그 파일(어느 폴더든)을, 아니면 이 폴더의 파일을 잰다. 어긋나면 멈춘다."""
    if name not in FROZEN_PINS:
        raise SystemExit("🚨 %s 는 얼린 V 핀 목록에 없다 — W 는 may_import 폐포만 부른다" % name)
    mod = sys.modules.get(name)
    if mod is None:
        _check_file(name, os.path.join(HERE, name + ".py"))
        mod = importlib.import_module(name)
    _check_file(name, mod.__file__)
    return mod


def frozen_check(names=None, root=HERE):
    """디스크의 얼린 파일 전부(또는 names) 핀 대조 — 돌려주는 것 {ok, bad[], n}."""
    bad = []
    for nm in sorted(names or FROZEN_PINS):
        p = os.path.join(root, nm + ".py")
        if not os.path.isfile(p):
            bad.append("%s 없음" % nm)
            continue
        got = blob_sha1(p)
        if got != FROZEN_PINS.get(nm):
            bad.append("%s %s ≠ %s" % (nm, got[:12], str(FROZEN_PINS.get(nm))[:12]))
    for rel, pin in FROZEN_DATA_PINS.items():
        p = os.path.join(os.path.dirname(root), rel)
        if not os.path.isfile(p) or _sha256(p) != pin:
            bad.append("%s 동결 자료 sha 어긋남" % rel)
    return {"ok": not bad, "bad": bad, "n": len(names or FROZEN_PINS) + len(FROZEN_DATA_PINS)}


def loaded_frozen_check(dirs=(HERE,)):
    """실행 중 점검 — dirs 안에서 불러온 로컬 모듈이 모두 (가) 얼린 핀과 같거나 (나) w_ 모듈이어야 한다. 핀 밖 로컬 모듈이 섞이면 위반."""
    bad, seen = [], []
    roots = [os.path.normcase(os.path.abspath(d)) for d in dirs]
    for nm, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f or "." in nm:
            continue
        d = os.path.normcase(os.path.dirname(os.path.abspath(f)))
        if d not in roots:
            continue
        seen.append(nm)
        if nm.startswith("w_") or nm == "__main__":
            continue
        if nm not in FROZEN_PINS:
            bad.append("%s(핀 밖 로컬 모듈)" % nm)
        elif blob_sha1(f) != FROZEN_PINS[nm]:
            bad.append("%s(핀 어긋남)" % nm)
    return {"ok": not bad, "bad": bad, "loaded_local": sorted(seen)}


def data_pin_check(rel):
    pin = FROZEN_DATA_PINS[rel]
    p = os.path.join(ROOT, rel)
    if _sha256(p) != pin:
        raise SystemExit("🚨 동결 자료 %s 가 핀과 다르다" % rel)
    return p


# ── 얼린 V 함수 재사용(핀 대조 뒤) — 펀드 틀 · 투영 · 회전 · 파생 가드 · 사건
def fund_x(S, B, rate, traded=None, fixed=None, mult=1.0):
    """frozen v_core.fund_x — F = 0.9·B + 0.1·(S − 비용) · 월말 되돌림 비용 · X = F − B. 🚨 수익 계열(굽기 · 눈가린 연기에서만)."""
    return frozen("v_core").fund_x(S, B, rate, traded=traded, fixed=fixed, mult=mult)


def project_active(w, wB, sector, ndx_only, **kw):
    """frozen v_core.project_active — 발행사 |a| ≤ 0.05 · 섹터 띠 · NDX 전용 합 ≤ 0.10 · Σw = 1(V1)."""
    return frozen("v_core").project_active(w, wB, sector, ndx_only, **kw)


def beta_band(w, wB, beta, project, **kw):
    """frozen v_core.beta_band — |β̂_책 − β̂(w_B)| ≤ 0.03(V2)."""
    return frozen("v_core").beta_band(w, wB, beta, project, **kw)


def turnover_annual(traded, n_months=None):
    return frozen("v_core").turnover_annual(traded, n_months)


def assert_stock_book(book):
    """G-DER — frozen v_core.assert_stock_book(주식 종류 표식 · 옵션 코드) ∧ w_guard.no_derivative_positions(선물 월물 · 변동성 ETF 표식 —
    v_core 의 주식 정규식은 ESZ6 같은 월물 표식을 보지 않아 둘 다 건다)."""
    frozen("v_core").assert_stock_book(book)
    import w_guard as WG
    return WG.no_derivative_positions(book)


TURN_MAX = 10.0


def down_months():
    """동결 mech_episodes down_m(S&P 500 가격수익 < 0 · 35달) — 자료 핀 대조 뒤."""
    with io.open(data_pin_check("data/mech_episodes.json"), encoding="utf-8") as f:
        ME = json.load(f)
    dm = sorted(ME["months"]["down_m"])
    if len(dm) != 35:
        raise SystemExit("🚨 동결 down_m 이 35 가 아니다(%d)" % len(dm))
    return dm


def tier2_harmless(X20, turn_annual, t1_row, down=None, window=S_WIN):
    """Tier-2 무해(명세 evaluation.tier2.harmless · 갱신 나 — 오케스트레이터 결정 · K4) — X20 = 20bp 주 행(T+1) 펀드 X 월 계열({달: x} 또는 Series).
    조건 AND: 연 X 점 ≥ 0 · 하락월 평균 X 점 ≥ 0 · 편도 연 회전 ≤ 10 · T+1 행 있음. 🚨 수익 — 굽기에서만."""
    import numpy as np
    if hasattr(X20, "items"):
        pairs = [(_mkey(k), v) for k, v in X20.items()]
    else:
        pairs = [(_mkey(k), v) for k, v in X20]
    pairs = [(k, float(v)) for k, v in pairs if v is not None and v == v and window[0] <= k <= window[1]]
    assert_window([k for k, _ in pairs], "Tier-2 X", "hold")
    dm = set(down if down is not None else down_months())
    x = np.array([v for _, v in pairs], float)
    xd = np.array([v for k, v in pairs if k in dm], float)
    ann = float(x.mean() * 12) if len(x) else None
    dmean = float(xd.mean()) if len(xd) else None
    conds = {"ann_x20_ge0": ann is not None and ann >= 0.0, "down_x_ge0": dmean is not None and dmean >= 0.0,
             "turn_le10": turn_annual is not None and turn_annual <= TURN_MAX, "t1_row": bool(t1_row)}
    return {"harmless": all(conds.values()), "conds": conds, "ann_x20": ann, "down_mean_x20": dmean, "n": int(len(x)), "n_down": int(len(xd)),
            "turn": turn_annual}


# ══════════════════════════════════════════════════════════════════════════
#  재현성(명세 oos_protocol.reproducibility · D28)
# ══════════════════════════════════════════════════════════════════════════
REQUIRED_ENV = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def env_problems(env=None):
    env = os.environ if env is None else env
    return ["%s=%s 가 아니다(지금 %s)" % (k, v, env.get(k)) for k, v in REQUIRED_ENV.items() if env.get(k) != v]


def pin_env():
    """스레드 · 해시 씨앗 핀(자식 과정에 넘길 환경) — 이 과정의 BLAS 는 이미 떴을 수 있어 자식에만 확실하다."""
    e = dict(os.environ)
    e.update(REQUIRED_ENV)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def seeds(n=5):
    return [SEED + i for i in range(n)]


def manifest(data_paths=()):
    """재현성 기록 — 판 · BLAS 구성 · 스레드 · 씨앗 · 자료 sha256(값 없음)."""
    import numpy as np
    out = {"python": sys.version.split()[0], "platform": platform.platform(), "numpy": np.__version__}
    for m in ("scipy", "pandas"):
        try:
            out[m] = importlib.import_module(m).__version__
        except Exception:                                                    # noqa: BLE001
            out[m] = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            np.show_config()
    except Exception as e:                                                   # noqa: BLE001
        buf.write("show_config 실패 %s" % type(e).__name__)
    out["np_config_sha"] = hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest()[:16]
    out["env"] = {k: os.environ.get(k) for k in REQUIRED_ENV}
    out["seed"] = SEED
    out["frozen_v_commit"] = V_COMMIT
    files = {}
    for p in data_paths:
        ap = p if os.path.isabs(p) else os.path.join(ROOT, p)
        files[str(p)] = _sha256(ap) if os.path.isfile(ap) else None
    out["data_sha256"] = files
    return out


# ══════════════════════════════════════════════════════════════════════════
#  등록 자물쇠 — 실자료 신호-수익 계산은 등록 커밋 뒤에만
# ══════════════════════════════════════════════════════════════════════════
KINDS = ("synth", "blind", "real", "r_repro")


def _git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True, encoding="utf-8")


def registered_commit(env=None):
    """WBATCH_COMMIT = 등록 커밋(40자) · origin/main 의 조상 · 그 트리에 build/PREREG-*-WBATCH.md 와 -WBATCH-CARDS.md — 아니면 None."""
    c = (env or os.environ).get("WBATCH_COMMIT")
    if not c or not re.fullmatch(r"[0-9a-f]{40}", c):
        return None
    if _git("merge-base", "--is-ancestor", c, "origin/main").returncode != 0:
        return None
    p = _git("ls-tree", "-r", "--name-only", c, "build/")
    names = p.stdout.splitlines() if p.returncode == 0 else []
    ok = any(re.fullmatch(r"build/PREREG-\d{4}-\d{2}-\d{2}-WBATCH\.md", x) for x in names) and \
        any(re.fullmatch(r"build/PREREG-\d{4}-\d{2}-\d{2}-WBATCH-CARDS\.md", x) for x in names)
    return c if ok else None


def main_script():
    m = sys.modules.get("__main__")
    f = getattr(m, "__file__", None) or (sys.argv[0] if sys.argv else "")
    return os.path.basename(str(f))


def assert_kind_allowed(kind, what=""):
    """자료 종류별 자물쇠 — synth · blind 는 언제나 · real 은 등록 커밋(WBATCH_COMMIT) 뒤 · r_repro(배치 R 공개 값 재현)는 w_audit 주 스크립트만."""
    if kind not in KINDS:
        raise SystemExit("🚨 자료 종류 %r 를 모른다(%s)" % (kind, KINDS))
    if kind == "real" and registered_commit() is None:
        raise SystemExit("🚨 등록 전에는 실자료로 신호-수익 통계를 계산하지 않는다(%s) — WBATCH_COMMIT(등록 커밋)을 넘기는 러너만" % what)
    if kind == "r_repro" and main_script() != "w_audit.py":
        raise SystemExit("🚨 배치 R 공개 값 재현은 허용 목록 별도 과정(w_audit)에서만 — 주 스크립트 %s(%s)" % (main_script(), what))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 · 실자료 수익 없음)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_window():
    assert HOLD_FLOOR == "2006-09" and DECISION_FLOOR == "2006-08" and PUBLIC_WIN == ("2016-09", "2026-08")
    assert len(months_between(HOLD_FLOOR, LAST_HOLD)) == 240 and len(months_between(*S_WIN)) == 120
    assert assert_window(months_between("2006-09", "2026-08"), "st")
    assert _raises(lambda: assert_window(["2006-08"], "st"))
    assert assert_window(["2006-08"], "st", basis="decision") and _raises(lambda: assert_window(["2006-07"], "st", basis="decision"))
    assert _raises(lambda: assert_window(["2026-09"], "st"))
    d = {m: 1.0 for m in months_between("1990-01", "2026-08")}
    assert min(trim_window(d)) == "2006-09" and len(trim_window(d)) == 240
    import pandas as pd
    s = pd.Series(1.0, index=pd.period_range("1926-07", "2026-08", freq="M"))
    t = trim_window(s)
    assert str(t.index[0]) == "2006-09" and len(t) == 240
    s2 = pd.Series(1.0, index=[m for m in months_between("2001-01", "2026-08")])
    assert len(trim_window(s2)) == 240
    assert trim_window([("2005-01", 1), ("2010-01", 2)]) == [("2010-01", 2)]
    assert mshift("2026-01", -1) == "2025-12" and mshift("2025-12", 1) == "2026-01" and mno("2016-09") - mno("2016-08") == 1
    return "20년 창(보유 2006-09 · 결정 2006-08 · 240달) · 공개 10년 = S 창 · 자르기(dict · Series 두 색인 · 목록)"


def _st_family():
    import numpy as np
    assert FAMILY["A"] == ("W01", "W04", "W10m") and FAMILY["B"] == ("W02", "W11") and FAMILY_ALPHA == 0.05
    assert "W13" in DROPPED and FORWARD_LEDGER is None and set(MEASURE_ONLY) == {"W03", "W06", "W12"}
    assert not (set(FAMILY["A"]) & set(MEASURE_ONLY)) and not (set(FAMILY["A"]) & set(DROPPED))
    # 한쪽 p · 방향
    p_up = one_sided_p(2.0, 117, +1)
    p_dn = one_sided_p(2.0, 117, -1)
    assert abs(p_up + p_dn - 1.0) < 1e-12 and 0.02 < p_up < 0.03
    assert one_sided_p(-2.05, 116, -1) == one_sided_p(2.05, 116, +1)
    assert one_sided_p(None, 100, 1) is None and one_sided_p(1.0, 100, 0) is None
    # Holm(frozen v_tests.holm) — 가족 3 · α 0.05: 문턱 0.0167 · 0.025 · 0.05 · 판정 p = 야생 부트스트랩 p 칸(여기서는 합성으로 t(T−1) p 를 넣는다)
    def st(c, t, T=117):
        return {"t": t, "T": T, "p_wild_one": one_sided_p(t, T, CARD_DIRECTION[c]), "B": WILD_B, "direction": CARD_DIRECTION[c]}
    assert _raises(lambda: holm_family({"W01": {"t": 3.0, "T": 117}}, "A", alpha=FAMILY_ALPHA))              # 부트스트랩 p 없는 t 거부(K1)
    assert _raises(lambda: holm_family({"W01": dict(st("W01", 3.0), direction=-1)}, "A", alpha=FAMILY_ALPHA))  # 방향 어긋남 거부
    assert _raises(lambda: holm_family({"W01": dict(st("W01", 3.0), B=999)}, "A", alpha=FAMILY_ALPHA))         # 등록 B 밖 거부
    Hh = holm_family({"W01": dict(st("W01", 3.5), hygiene_fail=True), "W04": st("W04", 2.3), "W10m": st("W10m", 0.1)}, "A", alpha=FAMILY_ALPHA)
    assert Hh["p"]["W01"] is None and not Hh["reject"]["W01"] and Hh["hygiene_fail"] == ["W01"] and Hh["m"] == 3   # 위생 실패 카드 = p 없음 · 분모 3
    H = holm_family({"W01": st("W01", 3.0), "W04": st("W04", 2.1), "W10m": st("W10m", -0.5)}, "A", alpha=FAMILY_ALPHA)
    assert H["m"] == 3 and H["reject"] == {"W01": True, "W04": True, "W10m": False}, H
    assert abs(H["threshold"]["W01"] - 0.05 / 3) < 1e-15 and abs(H["threshold"]["W04"] - 0.025) < 1e-15
    H2 = holm_family({"W01": st("W01", 2.1), "W04": st("W04", 2.1)}, "A", alpha=FAMILY_ALPHA)        # W10m 빠짐 — 분모 3 그대로(p 0.019 > α/3)
    assert H2["m"] == 3 and H2["p"]["W10m"] is None and not any(H2["reject"].values()), H2
    assert _raises(lambda: holm_family({"W01": st("W01", 3), "W13": {"t": 9, "T": 117}}, "A", alpha=FAMILY_ALPHA))
    assert _raises(lambda: holm_family({"W01": st("W01", 3)}, "A", alpha=0.10))                   # 등록 α 밖 거부
    HB = holm_family({"W02": st("W02", 1.0), "W11": st("W11", -3.0)}, "B", alpha=FAMILY_ALPHA)          # W11 방향 −
    assert HB["reject"]["W11"] and not HB["reject"]["W02"]
    # 한 번 못 넘으면 멈춘다(두 번째가 못 넘으면 세 번째가 작아도 기각 없음)
    H3 = holm_family({"W01": st("W01", 3.5), "W04": st("W04", 1.9), "W10m": st("W10m", 1.95)}, "A", alpha=FAMILY_ALPHA)
    assert H3["reject"]["W01"] and not H3["reject"]["W04"] and not H3["reject"]["W10m"]
    # 채택 표시 · 표
    assert adoption_mark(True, True, True) and not adoption_mark(True, True, None) and not adoption_mark(True, False, True)
    T = adoption_table(H, {"W01": {"harmless": True}, "W04": {"harmless": False}}, {"W01": True, "W04": True, "W10m": True},
                       {"W01": {"dm_t_gt0": False}})
    assert T["W01"]["adopt"] and not T["W04"]["adopt"] and not T["W10m"]["adopt"] and T["W01"]["cautions"] == {"dm_t_gt0": False}
    assert T["W13"]["adopt"] is False and T["W03"]["path"] == "측정만"
    # 무해(합성 X)
    rng = np.random.default_rng(SEED)
    ms = months_between(*S_WIN)
    dm = down_months()
    X = {m: float(rng.normal(0.0002, 0.001)) for m in ms}
    for m in dm:
        X[m] = abs(X[m])
    h = tier2_harmless(X, 5.0, True)
    assert h["n"] == 120 and h["n_down"] == 35 and h["conds"]["down_x_ge0"] and h["conds"]["turn_le10"]
    X2 = dict(X)
    for m in dm:
        X2[m] = -0.01
    h2 = tier2_harmless(X2, 5.0, True)
    assert not h2["harmless"] and not h2["conds"]["down_x_ge0"]
    assert not tier2_harmless(X, 10.5, True)["harmless"] and not tier2_harmless(X, 5.0, False)["harmless"]
    assert not tier2_harmless(X, None, True)["harmless"]
    assert _raises(lambda: tier2_harmless({"2005-01": 0.1}, 1.0, True, window=("2005-01", "2026-08")))
    assert abs(one_sided_p(2.0, 119, +1, df=117) - __import__("scipy.stats").stats.t.sf(2.0, 117)) < 1e-15             # 교차항 df = n − 2
    return "가족 A {W01 · W04 · W10m} · B {W02 · W11} · 판정 p = 야생 부트스트랩 칸(없으면 거부 · B · 방향 대조) · 위생 실패 = p 없음 · Holm(분모 고정 · 멈춤 · 가족 밖 거부 · 방향) · 채택 3조건 · 무해 4조건"


def _st_frozen():
    r = frozen_check()
    assert r["ok"], r
    VT = frozen("v_tests")
    C = frozen("v_core")
    assert VT.__name__ == "v_tests" and C.__name__ == "v_core"
    L = loaded_frozen_check()
    assert L["ok"], L
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "v_core.py")
        with open(os.path.join(HERE, "v_core.py"), "rb") as f:
            b = f.read()
        with open(p, "wb") as f:
            f.write(b.replace(b"\n", b"\r\n"))
        assert blob_sha1(p) == FROZEN_PINS["v_core"]                 # CRLF 사본도 같은 blob id
        with open(p, "ab") as f:
            f.write(b"# x\n")
        assert blob_sha1(p) != FROZEN_PINS["v_core"]
        assert _raises(lambda: _check_file("v_core", p))
    assert _raises(lambda: frozen("r_" + "stagem")) and _raises(lambda: frozen("eg3" + "0plus"))   # 이름을 만들어 넘긴다(정적 점검이 import 로 읽지 않게)
    # 얼린 함수 재사용 — fund_x 식(합성)
    import numpy as np
    import pandas as pd
    idx = pd.period_range("2016-09", periods=24, freq="M")
    S = pd.Series(np.linspace(-0.02, 0.03, 24), index=idx)
    B = pd.Series(0.01, index=idx)
    X = fund_x(S, B, 0.0)
    assert np.allclose(X.to_numpy(), 0.1 * (S - B).to_numpy(), atol=1e-15)
    X2 = fund_x(S, B, 0.001, traded=pd.Series(0.2, index=idx), mult=2.0)
    assert (X2 < X).all()
    assert assert_stock_book({"AAPL": 0.5, "BRK.B": 0.5}) and _raises(lambda: assert_stock_book({"ESZ6": 1.0}))
    assert _raises(lambda: assert_stock_book({"SPY251219C00600000": 1.0})) and _raises(lambda: assert_stock_book({"VIXY": 1.0}))
    # 투영 · β 띠 · 회전(frozen v_core) — 합성 책: 상한 · 합 1 · β 띠 안
    rng = np.random.default_rng(SEED)
    n = 40
    wB = rng.dirichlet(np.ones(n))
    sec = np.array([i % 5 for i in range(n)])
    ndx = np.zeros(n, bool)
    ndx[:3] = True
    wB[:3] = 0.0
    wB = wB / wB.sum()
    w0 = wB.copy()
    w0[3:8] += 0.08
    w0 = w0 / w0.sum()
    pr = project_active(w0, wB, sec, ndx)
    wp = pr[0] if isinstance(pr, tuple) else pr
    assert abs(float(np.sum(wp)) - 1.0) < 1e-9 and float(np.max(np.abs(wp - wB))) <= 0.05 + 1e-9
    beta = rng.normal(1.0, 0.3, n)
    bb = beta_band(wp, wB, beta, lambda x: (lambda r: r[0] if isinstance(r, tuple) else r)(project_active(x, wB, sec, ndx)))
    wbb = bb[0] if isinstance(bb, tuple) else bb
    assert abs(float(np.dot(wbb, beta) - np.dot(wB, beta))) <= 0.03 + 1e-6 and abs(float(np.sum(wbb)) - 1.0) < 1e-9
    assert abs(turnover_annual([0.2] * 12) - 1.2) < 1e-12
    return "핀 %d(디스크 · 불러온 모듈 · CRLF 같은 id · 바뀐 파일 멈춤 · 핀 밖 모듈 거부) · fund_x · 투영 · β 띠 · 회전 · G-DER 재사용" % r["n"]


def _st_env_lock():
    assert env_problems({"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}) == []
    assert len(env_problems({})) == 4
    e = pin_env()
    assert all(e[k] == v for k, v in REQUIRED_ENV.items())
    assert seeds() == [SEED, SEED + 1, SEED + 2, SEED + 3, SEED + 4]
    m = manifest(["data/mech_episodes.json"])
    assert m["data_sha256"]["data/mech_episodes.json"] == FROZEN_DATA_PINS["data/mech_episodes.json"] and m["seed"] == SEED
    assert assert_kind_allowed("synth") and assert_kind_allowed("blind")
    old = os.environ.pop("WBATCH_COMMIT", None)
    try:
        assert registered_commit() is None
        assert _raises(lambda: assert_kind_allowed("real", "st"))
        os.environ["WBATCH_COMMIT"] = V_COMMIT                        # 조상이지만 W 등록 문서가 없다 → 거부
        assert registered_commit() is None and _raises(lambda: assert_kind_allowed("real", "st"))
        os.environ["WBATCH_COMMIT"] = "deadbeef"
        assert registered_commit() is None
    finally:
        os.environ.pop("WBATCH_COMMIT", None)
        if old is not None:
            os.environ["WBATCH_COMMIT"] = old
    assert _raises(lambda: assert_kind_allowed("r_repro", "st"))    # 주 스크립트가 w_audit 가 아니다
    assert _raises(lambda: assert_kind_allowed("mystery"))
    assert _raises(lambda: assert_no_forward(["data/_wfwd/genesis.json"])) and assert_no_forward(["data/_wb_f0.json"])
    cd = cache_dir("selftest")
    assert _inside(cd, CACHE) and not _inside(cd, ROOT)
    assert _raises(lambda: assert_writable(os.path.join(VB_CACHE, "x.json")))
    return "환경 핀 · 씨앗 · manifest · 등록 자물쇠(real · r_repro · 종류) · 전방 원장 없음 · 캐시 경계(V 캐시 읽기 전용)"


def selftest():
    res, ok = [], True
    for fn in (_st_window, _st_family, _st_frozen, _st_env_lock):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_core selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--frozen" in sys.argv:
        r = frozen_check()
        print(json.dumps(r, ensure_ascii=False))
        raise SystemExit(0 if r["ok"] else 1)
    print(__doc__)
