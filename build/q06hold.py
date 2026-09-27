# -*- coding: utf-8 -*-
"""build/q06hold.py — Q06 방어 스텝 방아쇠의 기전 검정 · 랩이 안 본 창(Q06HOLD) 계산 엔진.
러너(build/q06hold_run.py)가 핀 판 임시 뿌리 둘(root · vroot) 안에서 자식 과정으로 부른다(이 파일은 두 뿌리의 build/ 에 복사된다).

사전등록: build/PREREG-<등록 날짜>-Q06HOLD.md 하나(글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).

무엇을 재나(역할 검정 — 방어 스텝의 방아쇠 기전이 랩이 잰 적 없는 창에서도 서나 · 생존 편향 없는 기전 대리로)
  상태 s     «Q06 긴 이력판» — 얼린 q_corrsurp 의 함수(scores · monthly · signals)를 한 글자도 안 바꾸고, 이력 상수만 자료 첫날로 옮긴다:
            원조 SPDR 9종 일간 수정종가(상장 1998-12-22 부터 · 저장소 밖에 뜬 판 · sha256 로 핀) · 창은 첫 수익일부터(최소 756 · 최대 2,520 ·
            t − 1 에서 끝) · HighMS = 첫 점수 달부터의 확장 80 백분위(36개월 전엔 거짓) · D_m = HighMS_m ∧ MonthCS_m > 1.
            결정 달 m 의 월말에 정하고 다음 달력 달(보유월 m+1)에 붙인다. 표본 안 창에서는 얼린 실운용 상태(배치 Q 등록 판)와 맞는 달 수를 센다.
  창        보유 2006-09 ~ 2016-08(120 · 결정 2006-08 ~ 2016-07) — 긴 이력판이 서는 첫 달(2004-11)보다 뒤라 20년 한도의 첫 달부터.
  주 목적지 L  French «BIG LoBETA»(25_Portfolios_ME_BETA_5x5 · 시총가중 · 월) · M = French 시장(Mkt-RF + RF) — 배치 V 의 얼린 L 대리
            v_data.l_proxy("V02") = L − M 그대로(생존 편향 없음 · 기전 대리 · 랩의 D 책이 아니다).
  주 통계    총 Δ_timing = 켜진 보유월의 (L − M) 평균 − 꺼진 보유월의 (L − M) 평균(교체 비용 없음) · H1(한쪽) > 0(양 = 기전이 선다).
            판정은 이 점 추정의 부호만 읽는다. 🚨 F0 규칙(카드 Q06 자신의 것): 창의 켜진 달 < 6 이면 «측정 불가» — 부호를 읽지 않는다.
  읽기(보고)  같은 Δ 의 순 판(교체마다 20bp 를 켜진 쪽에) · NW(Bartlett 3) t · 구간 섞기 위약(켜진 달 수 · 교체 수 보존) · KT 시장 방향 ·
            헛경보(켜진 달 가운데 시장이 오른 몫 · 바탕 · 비용 · 이득) · 쌍둥이 T1 · T2 · 표본 안 참고(2016-09 ~ 2026-08 · 얼린 실운용 상태 · French · 오염).
            주식 대리 P1(보유 2012-01 ~ 2016-08)은 F0 에서 그 창의 긴 이력판 켜진 달이 0(얼린 실운용 5)이라 같은 F0 규칙으로 «측정 불가» —
            수익 경로를 짓지 않고 켜진 달 수만 싣는다.

🚨 랩 규율: 수익 계열을 만드는 자식(leg · stat)은 등록 커밋이 origin 에 오른 뒤 러너의 한 번 굽기와 눈가린 연기에서만 돈다.
   st · f0v 는 상태 개수 · 맞는 달 수 · 시점 단언 · French 핀 · 값이 선 달 수만 돌려준다 — 수익 · 초과 · Δ · 적중 통계 없음.
🚨 머리에서는 표준 라이브러리만 부른다(러너 · validate_site 가 numpy 없이 이 파일을 읽을 수 있게).
"""
from __future__ import annotations

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
HOLD = ("2006-09", "2016-08")          # 보유월(창) — 20년 한도의 첫 보유월 · 긴 이력판 상태가 서는 달(2004-11)보다 뒤다([F0])
FORM_FIRST, FORM_LAST = "2006-08", "2016-07"
N_HOLD = 120
REF_HOLD = ("2016-09", "2026-08")      # 표본 안 참고 창(이미 본 창 · 오염 · 얼린 실운용 상태 · 보고만)
REF_FIRST, REF_LAST = "2016-08", "2026-07"
N_REF = 120
P1_FIRST, P1_LAST = "2011-12", "2016-07"      # 주식 대리 P1 읽기의 결정 달(보유 2012-01 ~ 2016-08) — [F0] 긴 이력판 켜짐 0 → 측정 불가(수익 경로 없음)
N_P1 = 56
COST = 0.0010                          # 순 판 읽기: 편도(한 쪽) — 교체는 두 쪽을 판다
LEGS = 2                               # → 교체마다 20bp 를 켜진 쪽에(더하기 꼴)
HAC_LAG = 3
K_PLACEBO = 10000
SEED = 20260930
PCT_READ = 95.0                        # 위약 읽기 문턱(읽기 · 판정 아님)
ALPHA_READ = 0.05                      # 유의성 읽기(한쪽 · 판정 아님)
F0_MIN_ON = 6                          # 카드 Q06 자신의 F0 규칙(얼린 q_corrsurp.F0_MIN · «신호 달 < 6 → 측정 불가»)
SPDR_LONG_N = 9
SPDR_LONG_FIRST, SPDR_LONG_END = "1998-12-22", "2026-08-31"
SPDR_LONG_DIGEST = "4a01c8502dcf17fdf87f169fb7111046419b551b4a0699d9bf68e4be71fc4f2b"   # 뜬 판 묶음 해시(러너가 떴다 · 저장소 밖)
COUNTED = ("F_HOLD", "T1_HOLD", "T2_HOLD", "KT_HOLD", "F_REF")
N_ROWS_COUNTED = 5
CUM_N_BEFORE = 1058                    # 누적 N 기저 = EGSTEP 뒤의 보수적 맥락 합(1,044 + 14)
EGSTEP_REF_STATES = {"n": 120, "on": 22, "switch": 23, "runs": 12, "t1": 35, "t2": 13}   # EGSTEP 등록 F0 의 D 상태(표본 안 창 · 얼린 실운용)
Q06_EXPECT = {"SPDR": ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"), "D0": "2006-01-04", "S0": "2009-01-02",
              "WMIN": 756, "WMAX": 2520, "PCT": 80, "NMIN_M": 36, "M0": "2009-01", "F0_MIN": 6}
# 뿌리마다 build/ 에서 단언하는 얼린 blob(LF 바이트의 git blob sha1)
ROOT_BLOBS = {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
              "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
              "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea"}
VROOT_BLOBS = {"v_cards": "aadaf24f173579d3f3146014aa150a4ca07eb0a5", "v_core": "bdba648f1d790748cd5008ceeea3c5eee9d733c8",
               "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a", "v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689",
               "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e", "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
               "v_cond": "d25914deb89490410ea2dca56b5999356628821e", "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38",
               "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
               "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea",
               "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513", "stoploss": "e2408e98d03216146cf809d6643c68947130c727",
               "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"}
F0_EXPECT = {"spdr_digest16": '4a01c8502dcf17fd', "spdr_n": 9, "spdr_first": '1998-12-22', "spdr_days": 6964, "long_d0": '1998-12-23', "long_s0": '2001-12-28',
              "long_m0": '2001-12', "long_first_hi": '2004-11', "long_timing_ok": True, "hold_n": 120, "hold_on": 7, "hold_switch": 10,
              "hold_runs": 5, "hold_t1": 29, "hold_t2": 22, "hold_pre": 0, "hold_post": 0, "hold_f0_rule_ok": True,
              "p1win_on": 0, "p1win_switch": 0, "long_ref_on": 18, "long_ref_switch": 19, "agree_ref": 116, "agree_both_on": 18,
              "frozen_timing_ok": True, "ref_on": 22, "ref_switch": 23, "ref_runs": 12, "ref_t1": 35, "ref_t2": 13,
              "ref_pre": 0, "ref_same_as_record": True, "ref_same_as_egstep": True, "frozen_old_on": 5, "fr_pins_ok": True, "fr_months": 240,
              "fr_crsp": '202608'}                        # 등록 F0 개수(러너 --f0 가 핀 뿌리 둘로 센 값 · 수익 없음) — 굽기 F0 가 같아야 표식을 쓴다

ROW_LABEL = {"F_HOLD": "주 통계 · 창 · French BIG LoBETA − Mkt · 긴 이력판 상태 · 총", "T1_HOLD": "쌍둥이 T1(HighMS 만) · 창",
             "T2_HOLD": "쌍둥이 T2(HighMS ∧ CS ≤ 1) · 창", "KT_HOLD": "KT 시장 방향 · 창", "F_REF": "표본 안 참고 · French · 얼린 실운용 상태"}


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
    """창의 결정 달 2006-08 ~ 2016-07 — 보유월 2006-09 ~ 2016-08."""
    return months_between(FORM_FIRST, FORM_LAST)


def ref_forms():
    return months_between(REF_FIRST, REF_LAST)


def p1_forms():
    return months_between(P1_FIRST, P1_LAST)


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


def _norm(x):
    if isinstance(x, (list, tuple)):
        return tuple(_norm(v) for v in x)
    if isinstance(x, dict):
        return {str(k): _norm(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def file_sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def spdr_digest(d, tickers):
    """뜬 판 묶음 해시 — sha256(«티커\\t파일 sha256\\n» 을 티커 차례로) · 선 파일 수(러너 spdr_digest_std 와 같은 규칙)."""
    lines = []
    for t in sorted(tickers):
        p = os.path.join(d, t.replace("^", "_") + ".csv")
        if os.path.exists(p):
            lines.append("%s\t%s\n" % (t, file_sha256(p)))
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(), len(lines)


# ══════════════════════════════════════════════════════════════════════════
#  순수 규칙(합성 selftest 가 모든 갈래를 본다)
# ══════════════════════════════════════════════════════════════════════════
def state_counts(s):
    """0/1 계열의 개수 · 교체 · 켜진 구간(수익 없음)."""
    s = [int(x) for x in s]
    return {"n": len(s), "on": int(sum(s)), "switch": int(sum(1 for a, b in zip(s, s[1:]) if a != b)),
            "runs": int(sum(1 for q, a in enumerate(s) if a == 1 and (q == 0 or s[q - 1] != 1)))}


def agreement(a, b):
    """두 0/1 계열(같은 달 차례)의 맞는 달 수 · 둘 다 켜짐 · 각자 켜짐(수익 없음)."""
    a, b = [int(x) for x in a], [int(x) for x in b]
    assert len(a) == len(b)
    return {"n": len(a), "agree": int(sum(1 for x, y in zip(a, b) if x == y)), "both_on": int(sum(1 for x, y in zip(a, b) if x and y)),
            "a_on": int(sum(a)), "b_on": int(sum(b))}


def charged_switches(s, s_pre, s_post):
    """켜진 쪽에 물리는 교체 — 달마다 (들어감, 나옴) 목록과 합. 들어감: 앞 상태가 꺼짐(창 첫 달은 s_pre) · 나옴: 다음 상태가 꺼짐 또는 모름
    (창 끝 달은 s_post · None 이면 문다 — 보수적)."""
    s = [int(x) for x in s]
    n = len(s)
    per = []
    for k in range(n):
        if not s[k]:
            per.append((0, 0))
            continue
        prev = s[k - 1] if k > 0 else int(s_pre)
        nxt = s[k + 1] if k + 1 < n else (None if s_post is None else int(s_post))
        per.append((int(not prev), int(nxt is None or not nxt)))
    return per, sum(p[0] for p in per), sum(p[1] for p in per)


def net_series(y, s, s_pre, s_post, c=COST, legs=LEGS):
    """순 판(읽기) — 켜진 달의 (L − M) 에서 교체마다 legs × c(편도 10bp × 두 쪽 = 20bp)를 뺀다(더하기 꼴) · 꺼진 달은 그대로."""
    per, _e, _x = charged_switches(s, s_pre, s_post)
    f = legs * c
    return [float(v) - f * (a + b) for v, (a, b) in zip(y, per)]


def on_off(y, s):
    """켜진 · 꺼진 평균과 차(%p/월 — y 는 소수 · 결과는 ×100)."""
    on = [float(v) for v, x in zip(y, s) if int(x)]
    off = [float(v) for v, x in zip(y, s) if not int(x)]
    mo = (sum(on) / len(on) * 100.0) if on else None
    mf = (sum(off) / len(off) * 100.0) if off else None
    return {"n_on": len(on), "n_off": len(off), "mean_on": mo, "mean_off": mf,
            "delta": (mo - mf) if (mo is not None and mf is not None) else None}


def p_upper(t, df):
    if t is None or df is None or df < 1:
        return None
    from scipy.stats import t as _t
    return float(_t.sf(float(t), int(df)))


def t_crit(df, alpha=ALPHA_READ):
    from scipy.stats import t as _t
    return float(_t.ppf(1.0 - alpha, int(df)))


def hac_diff(y, s, E, lag=HAC_LAG):
    """켜짐 계수(= 켜진 평균 − 꺼진 평균)의 NW(Bartlett lag) t — 얼린 eg30plus.nw_ols(y, [1, s]) · 한쪽 p = t(n − 2) 위 꼬리."""
    import numpy as np
    y = np.asarray(y, float) * 100.0
    s = np.asarray(s, float)
    if s.sum() < 1 or s.sum() > len(s) - 1:
        return {"b": None, "t": None, "p": None, "df": None}
    with np.errstate(invalid="ignore", divide="ignore"):
        b, t = E.nw_ols(y, np.column_stack([np.ones(len(y)), s]), lag=lag)
    tt = float(t[1]) if np.isfinite(t[1]) else None
    return {"b": float(b[1]), "t": tt, "p": p_upper(tt, len(y) - 2), "df": len(y) - 2}


def timing(y, s, s_pre, s_post, E, c=COST):
    """Δ_timing 한 줄 — 총(교체 비용 없음 · 주 통계의 꼴) · 순(교체마다 20bp 를 켜진 쪽 · 읽기) · 총의 NW t · p · 켜진 · 꺼진 평균 · 들어감 · 나옴."""
    g = on_off(y, s)
    ns = net_series(y, s, s_pre, s_post, c)
    nt = on_off(ns, s)
    h = hac_diff(y, s, E)
    _per, ent, ext = charged_switches(s, s_pre, s_post)
    return {"n": len(y), "n_on": g["n_on"], "n_off": g["n_off"], "delta": g["delta"], "mean_on": g["mean_on"], "mean_off": g["mean_off"],
            "delta_net": nt["delta"], "mean_on_net": nt["mean_on"], "t": h["t"], "p": h["p"], "df": h["df"],
            "hac_b_eq_delta": (None if (h["b"] is None or g["delta"] is None) else bool(abs(h["b"] - g["delta"]) < 1e-9)),
            "n_entry": int(ent), "n_exit": int(ext)}


def pct_rank(draws, true):
    """랩 규약(eg30plus · q_switch.pct_rank) — 참값보다 작은 뽑기의 백분율."""
    if true is None or not draws:
        return None
    return float(sum(1 for d in draws if d < true) / len(draws) * 100.0)


def placebo(SW, y, s, k, seed):
    """구간 섞기 위약(총 Δ) — 얼린 q_switch.seg_shuffle(켜진 구간 길이 · 꺼진 구간 길이를 따로 섞어 참 첫 상태부터 번갈아 엮는다 → 켜진 달 수 ·
    교체 수 보존) · 같은 (L − M) 계열 · 뽑기마다 총 Δ. 돌려주는 것 뽑기 목록 · 서로 다른 뽑기 수."""
    import numpy as np
    x = np.asarray([int(v) for v in s], np.int8)
    rng = np.random.default_rng(seed)
    out, seen = [], set()
    for _ in range(k):
        p = SW.seg_shuffle(x, rng)
        assert int(p.sum()) == int(x.sum()) and int(np.sum(p[1:] != p[:-1])) == int(np.sum(x[1:] != x[:-1]))
        seen.add(p.tobytes())
        out.append(on_off(y, p)["delta"])
    return out, len(seen)


def quantiles(xs, qs=(5, 50, 95)):
    import numpy as np
    a = np.asarray([x for x in xs if x is not None], float)
    return {("p%02d" % q): (float(np.percentile(a, q)) if len(a) else None) for q in qs}


def kt_direction(mex, s, E):
    """Kinlaw–Turkington 시장 방향 — 켜진 뒤 보유월의 시장 초과(Mkt − RF) 평균 < 꺼진 뒤(기전이면 참) · NW t(켜짐 계수 · 음이 기전 쪽)."""
    oo = on_off(mex, s)
    h = hac_diff(mex, s, E)
    return {"n_on": oo["n_on"], "n_off": oo["n_off"], "ex_on": oo["mean_on"], "ex_off": oo["mean_off"], "diff": oo["delta"], "t": h["t"],
            "direction_ok": (None if oo["delta"] is None else bool(oo["delta"] < 0))}


def false_alarm(mkt, y, s):
    """헛경보 — 켜진 보유월 가운데 시장 총수익이 오른(> 0) 몫 · 바탕(모든 보유월의 오른 몫) · 헛경보 달의 (L − M) 총 평균(비용) ·
    참경보 달(켜짐 ∧ 시장 ≤ 0)의 평균(이득)."""
    on = [k for k in range(len(s)) if int(s[k])]
    up = [k for k in range(len(mkt)) if float(mkt[k]) > 0]
    fa = [k for k in on if float(mkt[k]) > 0]
    ta = [k for k in on if not float(mkt[k]) > 0]
    m = lambda ks: (sum(float(y[k]) for k in ks) / len(ks) * 100.0) if ks else None
    return {"n": len(mkt), "n_up": len(up), "n_on": len(on), "n_on_up": len(fa), "n_on_down": len(ta),
            "fa_mean": m(fa), "ta_mean": m(ta), "fa_cost_neg": (None if not fa else bool(m(fa) < 0)),
            "ta_benefit_pos": (None if not ta else bool(m(ta) > 0)),
            "fa_share_lt_base": (None if not on or not mkt else bool(len(fa) / len(on) < len(up) / len(mkt)))}


def verdict(delta, n_on, stopped=None):
    """결과 문서 «판정:» — 등록된 멈춤 → 보류 · 창 켜진 달 < 6(카드 Q06 F0 규칙) → 측정 불가 · 총 점 추정 > 0 → 측정만(기전 부호가 선다 ·
    유의성과 무관) · ≤ 0 → 기각(기전 부호 틀림)."""
    if stopped or n_on is None:
        return "보류"
    if n_on < F0_MIN_ON:
        return "측정 불가"
    if delta is None:
        return "보류"
    return "측정만" if delta > 0 else "기각"


def verdict_line(v):
    """«판정:» 줄의 낱말 — 랩 판정 어휘(기각 · 게시 · 측정만 · 보류) 가운데 하나를 품어야 한다(verdict_wire) · 측정 불가는 «보류(측정 불가)»."""
    return "보류(측정 불가)" if v == "측정 불가" else v


def predictions(M):
    """미리 적은 예측(계산 전 고정 · 결과 문서가 채점) — 참/거짓만."""
    P = {}
    h = M["hold"]
    pr = h["primary"]
    P["P1_gross_pos"] = bool(pr["delta"] is not None and pr["delta"] > 0)
    P["P2_not_significant"] = bool(pr["p"] is None or pr["p"] >= ALPHA_READ)
    P["P3_kt_direction_ok"] = bool(h["kt"]["direction_ok"] is True)
    P["P4_t2_below_primary"] = bool(h["t2"]["delta"] is not None and pr["delta"] is not None and h["t2"]["delta"] < pr["delta"])
    P["P5_net_same_sign"] = bool(pr["delta_net"] is not None and pr["delta"] is not None and ((pr["delta_net"] > 0) == (pr["delta"] > 0)))
    P["P6_fa_share_below_base"] = bool(h["fa"].get("fa_share_lt_base") is True)
    P["P7_ref_pos"] = bool(M["ref"]["f"]["delta"] is not None and M["ref"]["f"]["delta"] > 0)
    return P


def f0_signature(R0):
    """등록 커밋에 박는 F0 개수(정수 · 날짜 · 참/거짓 · 짧은 해시만 · 실수 없음) — 굽기 F0 가 같아야 표식을 쓴다."""
    L, Fz, fr = R0["st"]["long"], R0["st"]["frozen"], R0["french"]
    h, ag = L["hold"], L["agree_ref"]
    return {"spdr_digest16": L["digest"][:16], "spdr_n": L["n_files"], "spdr_first": L["d_first"], "spdr_days": L["n_days"],
            "long_d0": L["d0"], "long_s0": L["s0"], "long_m0": L["m0"], "long_first_hi": L["first_hi"], "long_timing_ok": bool(L["timing_ok"]),
            "hold_n": h["n"], "hold_on": h["on"], "hold_switch": h["switch"], "hold_runs": h["runs"], "hold_t1": L["hold_t1"]["on"],
            "hold_t2": L["hold_t2"]["on"], "hold_pre": L["pre"]["d"], "hold_post": L["post"]["d"], "hold_f0_rule_ok": bool(h["on"] >= F0_MIN_ON),
            "p1win_on": L["p1win"]["on"], "p1win_switch": L["p1win"]["switch"], "long_ref_on": L["ref"]["on"], "long_ref_switch": L["ref"]["switch"],
            "agree_ref": ag["agree"], "agree_both_on": ag["both_on"],
            "frozen_timing_ok": bool(Fz["timing_ok"]), "ref_on": Fz["ref"]["on"], "ref_switch": Fz["ref"]["switch"], "ref_runs": Fz["ref"]["runs"],
            "ref_t1": Fz["ref_t1"]["on"], "ref_t2": Fz["ref_t2"]["on"], "ref_pre": Fz["ref_pre"], "ref_same_as_record": bool(Fz["ref_same_as_record"]),
            "ref_same_as_egstep": bool(Fz["ref_same_as_egstep"]), "frozen_old_on": Fz["oldwin"]["on"],
            "fr_pins_ok": bool(fr["pins_ok"]), "fr_months": fr["n_months"], "fr_crsp": fr["crsp"]}


# ══════════════════════════════════════════════════════════════════════════
#  root 자식(배치 Q 등록 판 뿌리) — 얼린 실운용 상태 · 긴 이력판 상태 · 개수 · 시점 단언(수익 없음)
# ══════════════════════════════════════════════════════════════════════════
def _root_q06():
    assert_blobs(HERE, ROOT_BLOBS)
    import qbatch_core as Q
    import q_corrsurp as QC
    bad = [k for k, v in Q06_EXPECT.items() if _norm(getattr(QC, k, None)) != _norm(v)]
    if bad:
        raise StopBake("얼린 q_corrsurp 상수가 등록 값과 다르다: %s" % bad)
    return Q, QC


def q06_frozen(QC, ctx):
    """얼린 실운용 상태 — 얼린 q_corrsurp.states · signals(배치 Q 등록 판 자료 · 이력 2009-01 ~) · 모든 달의 (Signal, HighMS, T2)."""
    st, s1, s2, mon, sig = QC.states(ctx)
    hi, sig2, t2 = QC.signals(mon)
    if sig2 != sig:
        raise StopBake("얼린 states 와 signals 의 신호가 다르다")
    return {m: int(bool(v)) for m, v in sig.items()}, {m: int(bool(v)) for m, v in hi.items()}, {m: int(bool(v)) for m, v in t2.items()}


def _timing_frozen(QC, ctx, fms):
    """결정 달 m 의 MonthMS · CS 는 그달 마지막 거래일 종가에서 닫힌다(얼린 q_corrsurp.dry 의 단언 · 뿌리 자산 격자)."""
    sc, _ = QC._series(ctx)
    A = ctx.A
    last = {}
    for t in sc:
        last[A.dates[t][:7]] = max(t, last.get(A.dates[t][:7], -1))
    bad = [m for m in fms if not (last.get(m) == A.me[m] and A.dates[A.me[m] + 1][:7] != m)]
    return not bad, bad[:3]


def spdr_load(d, tickers):
    """뜬 판(<티커>.csv · Date,Close)을 한 격자로 — 아홉 날짜 목록이 같아야 한다 · 빈 값이 없어야 한다. 돌려주는 것 (날짜, 가격 행렬 T × 9)."""
    import numpy as np
    dates, cols = None, []
    for t in tickers:
        with io.open(os.path.join(d, t + ".csv"), encoding="utf-8") as f:
            rows = [l.split(",") for l in f.read().splitlines()[1:] if l.strip()]
        ds = [r[0] for r in rows]
        if dates is None:
            dates = ds
        elif ds != dates:
            raise StopBake("뜬 판의 날짜 목록이 종목마다 다르다(%s)" % t)
        cols.append([float(r[1]) for r in rows])
    P = np.array(cols, float).T
    if not np.isfinite(P).all() or (P <= 0).any():
        raise StopBake("뜬 판에 빈 값 · 0 이하 값")
    return dates, P


def q06_long(QC, d, tickers, need_last):
    """«Q06 긴 이력판» — 얼린 q_corrsurp.scores · monthly · signals 를 그대로 · 이력 상수만 자료 첫날로(D0 = 첫 수익일 · S0 = 첫 수익일 + WMIN ·
    M0 = S0 의 달). 돌려주는 것 (D, T1, T2 · 달 → 0/1, 점수 날 사전, 날짜, 월말 색인, 메타)."""
    import numpy as np
    dates, P = spdr_load(d, tickers)
    Y = np.full_like(P, np.nan)
    Y[1:] = P[1:] / P[:-1] - 1.0
    me = {}
    for i, x in enumerate(dates):
        me[x[:7]] = i
    if need_last not in me or mshift(need_last, 1) not in me:
        raise StopBake("뜬 판이 결정 달 %s 뒤 한 달까지 닿지 않는다" % need_last)
    i_st = 1                                                 # D0 → 첫 수익일(첫 가격 날 다음 날)
    i_first = i_st + QC.WMIN                                 # S0 → 창이 WMIN 을 처음 채우는 날(창은 t − 1 에서 끝)
    i_last = me[need_last]
    if np.isnan(Y[i_st:i_last + 1]).any():
        raise StopBake("뜬 판 수익에 빈 값")
    sc = QC.scores(Y, i_st, i_first, i_last)

    class _A:
        pass
    A = _A()
    A.dates = dates
    mon = QC.monthly(A, sc)
    m0 = dates[i_first][:7]
    hi, sig, t2 = QC.signals(mon, m0)
    ms = sorted(m for m in mon if m >= m0)
    meta = {"d_first": dates[0], "n_days": len(dates), "d0": dates[i_st], "s0": dates[i_first], "m0": m0, "n_score_days": len(sc),
            "n_months": len(ms), "first_hi": (ms[QC.NMIN_M - 1] if len(ms) >= QC.NMIN_M else None), "last_month": ms[-1] if ms else None}
    return ({m: int(bool(v)) for m, v in sig.items()}, {m: int(bool(v)) for m, v in hi.items()}, {m: int(bool(v)) for m, v in t2.items()},
            sc, dates, me, meta)


def _timing_long(sc, dates, me, fms):
    """긴 이력판의 시점 — 결정 달 m 의 마지막 점수 날 = 그달 마지막 거래일(뜬 판 격자) · 그 다음 날은 다음 달."""
    last = {}
    for t in sc:
        last[dates[t][:7]] = max(t, last.get(dates[t][:7], -1))
    bad = [m for m in fms if not (last.get(m) == me[m] and dates[me[m] + 1][:7] != m)]
    return not bad, bad[:3]


def st_child(job):
    """F0 · 굽기 공용(root · 수익 없음) — 얼린 실운용 상태(표본 안 개수 · 배치 Q 기록 · EGSTEP F0 대조 · 옛 창 켜진 달 수) ·
    «Q06 긴 이력판»(뜬 판 해시 · 창 · P1 창 · 표본 안 개수 · 얼린 실운용 상태와 맞는 달) · 시점 단언. 🚨 상태 날짜는 굽기 자식(stat)만 읽는다."""
    t0 = time.time()
    Q, QC = _root_q06()
    d = job["spdr_dir"]
    dg, nf = spdr_digest(d, Q06_EXPECT["SPDR"])
    if nf != SPDR_LONG_N or dg != SPDR_LONG_DIGEST:
        raise StopBake("뜬 SPDR 판의 묶음 해시 · 파일 수가 등록 값과 다르다")
    ctx = Q.Ctx()
    Df, T1f, T2f = q06_frozen(QC, ctx)
    rf = ref_forms()
    ok_f, bad_f = _timing_frozen(QC, ctx, [mshift(REF_FIRST, -1)] + rf)
    rec = (((_json(job["qbatch"]).get("cards") or {}).get("Q06") or {}).get("log") or {}).get("signal_months") or []
    ref = state_counts([Df[m] for m in rf])
    ref_t1, ref_t2 = state_counts([T1f[m] for m in rf]), state_counts([T2f[m] for m in rf])
    same_eg = bool(ref["on"] == EGSTEP_REF_STATES["on"] and ref["switch"] == EGSTEP_REF_STATES["switch"] and ref["runs"] == EGSTEP_REF_STATES["runs"]
                   and ref_t1["on"] == EGSTEP_REF_STATES["t1"] and ref_t2["on"] == EGSTEP_REF_STATES["t2"] and ref["n"] == EGSTEP_REF_STATES["n"])
    frozen = {"timing_ok": bool(ok_f), "timing_bad": bad_f, "ref": ref, "ref_t1": ref_t1, "ref_t2": ref_t2, "ref_pre": Df[mshift(REF_FIRST, -1)],
              "ref_same_as_record": bool([m for m in rf if Df[m]] == list(rec)), "ref_same_as_egstep": same_eg,
              "oldwin": state_counts([Df[m] for m in p1_forms()])}
    D, T1, T2, sc, dates, me, meta = q06_long(QC, d, Q06_EXPECT["SPDR"], REF_LAST)
    fm = forms()
    need = [mshift(FORM_FIRST, -1)] + fm + rf
    miss = [m for m in need if m not in D]
    if miss:
        raise StopBake("긴 이력판 상태가 없는 결정 달: %s" % miss[:3])
    ok_l, bad_l = _timing_long(sc, dates, me, need)
    ag = agreement([D[m] for m in rf], [Df[m] for m in rf])
    long = dict(meta, digest=dg, n_files=nf, timing_ok=bool(ok_l), timing_bad=bad_l,
                hold=state_counts([D[m] for m in fm]), hold_t1=state_counts([T1[m] for m in fm]), hold_t2=state_counts([T2[m] for m in fm]),
                pre={"m": mshift(FORM_FIRST, -1), "d": D[mshift(FORM_FIRST, -1)], "t1": T1[mshift(FORM_FIRST, -1)], "t2": T2[mshift(FORM_FIRST, -1)]},
                post={"m": REF_FIRST, "d": D[REF_FIRST], "t1": T1[REF_FIRST], "t2": T2[REF_FIRST]},
                p1win=state_counts([D[m] for m in p1_forms()]), ref=state_counts([D[m] for m in rf]), agree_ref=ag)
    keep_l = [mshift(FORM_FIRST, -1)] + months_between(FORM_FIRST, REF_LAST)
    keep_f = [mshift(REF_FIRST, -1)] + rf
    return {"kind": "q06hold_st", "frozen": frozen, "long": long,
            "states": {"long": {"D": {m: D[m] for m in keep_l}, "T1": {m: T1[m] for m in keep_l}, "T2": {m: T2[m] for m in keep_l}},
                       "frozen": {"D": {m: Df[m] for m in keep_f}}},
            "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
#  vroot 자식(배치 V 핀 판) — French 주 목적지 · 시장(얼린 v_data · 핀 SHA · CRSP 202608)
# ══════════════════════════════════════════════════════════════════════════
def _vroot_check(job):
    assert_blobs(HERE, VROOT_BLOBS)
    import v_data as VD
    import x_adapter as XA
    ok, bad = XA._v_pins_full(VD, job.get("root"))
    if not ok:
        raise StopBake("배치 V 자료 핀 불일치 — %s" % bad[:3])
    return VD, XA


def french_months(VD, months):
    """French 주 목적지 · 시장(달력 달 · 소수) — y = 얼린 v_data.l_proxy("V02")(BIG LoBETA − Mkt) · Mkt-RF · RF · Mkt(= Mkt-RF + RF).
    돌려주는 것 {y, mex, rf, mkt} 목록과 빈 달 목록."""
    import pandas as pd
    yF = VD.l_proxy("V02")
    ff = VD.ff3("m")
    out, miss = {"y": [], "mex": [], "rf": [], "mkt": []}, []
    for h in months:
        p = pd.Period(h, "M")
        vals = []
        for s_, col in ((yF, None), (ff, "Mkt-RF"), (ff, "RF"), (ff, "Mkt")):
            try:
                v = s_.loc[p] if col is None else s_.loc[p, col]
                v = float(v)
            except Exception:                                  # noqa: BLE001
                v = float("nan")
            vals.append(v)
        if any(v != v for v in vals):
            miss.append(h)
        out["y"].append(vals[0])
        out["mex"].append(vals[1])
        out["rf"].append(vals[2])
        out["mkt"].append(vals[3])
    return out, miss


def f0v_child(job):
    """F0(vroot · 수익 없음) — French 핀(v_data.check_pins · 폴더 요약 · 뿌리) · CRSP 판 · 창 + 표본 안 보유월(2006-09 ~ 2026-08)의 값이 선 달 수만."""
    t0 = time.time()
    VD, XA = _vroot_check(job)
    okp, badp = VD.check_pins()
    fr_n, crsp = 0, None
    try:
        crsp = VD.load_french("me_beta")["crsp"]
        _fm, miss = french_months(VD, months_between(HOLD[0], REF_HOLD[1]))
        fr_n = len(months_between(HOLD[0], REF_HOLD[1])) - len(miss)
        del _fm
    except Exception as e:                                       # noqa: BLE001
        badp = list(badp) + ["French 를 읽지 못함: %s" % type(e).__name__]
        okp = False
    return {"kind": "q06hold_f0v", "french": {"pins_ok": bool(okp), "bad": list(badp)[:4], "n_months": int(fr_n), "crsp": crsp},
            "sec": round(time.time() - t0, 1)}


def leg_child(job):
    try:
        return _leg_body(job)
    except StopBake as e:
        return {"kind": "q06hold_leg", "stopped": str(e)[:300]}


def _leg_body(job):
    """🚨 수익 계열(vroot) — French 주 목적지 · 시장(창 + 표본 안 보유월 2006-09 ~ 2026-08 · 빈 달이면 등록된 멈춤). 산출은 캐시 작업 폴더에만."""
    t0 = time.time()
    VD, XA = _vroot_check(job)
    ok, bad = VD.check_pins()
    if not ok:
        raise StopBake("French · 배치 V 자료 핀 불일치")
    hm = months_between(*HOLD)
    rm = months_between(*REF_HOLD)
    F, miss = french_months(VD, hm + rm)
    if miss:
        raise StopBake("French 값이 없는 보유월: %s" % miss[:3])
    n1 = len(hm)
    hold = {"months": hm, **{k: v[:n1] for k, v in F.items()}}
    ref = {"months": rm, **{k: v[n1:] for k, v in F.items()}}
    return {"kind": "q06hold_leg", "note": "🚨 보유월 수익(캐시 전용 · stat 자식만 읽는다)", "hold": hold, "ref": ref,
            "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
#  root 자식 — 통계 · 읽기 · 판정(얼린 eg30plus.nw_ols · q_switch.seg_shuffle)
# ══════════════════════════════════════════════════════════════════════════
def stat_child(job):
    try:
        return _stat_body(job)
    except StopBake as e:
        return {"kind": "q06hold_out", "stopped": str(e)[:300]}


def _stat_body(job):
    """🚨 굽기 본체(root) — 주 통계(창 · French · 긴 이력판 · 총) · F0 규칙 · NW t · 위약 · 순 판 · KT · 헛경보 · T1 · T2 · P1 켜진 달 수 ·
    표본 안 참고(French · 얼린 실운용 상태 · 두 판 상태 달) · 판정 · 예측."""
    t0 = time.time()
    assert_blobs(HERE, ROOT_BLOBS)
    import eg30plus as E
    import q_switch as SW
    L = _json(job["leg"])
    if L.get("stopped"):
        return {"kind": "q06hold_out", "stopped": L["stopped"]}
    S = _json(job["st"])
    Dl, T1l, T2l = S["states"]["long"]["D"], S["states"]["long"]["T1"], S["states"]["long"]["T2"]
    Df = S["states"]["frozen"]["D"]
    fm, rfm = forms(), ref_forms()
    if list(L["hold"]["months"]) != [mshift(m, 1) for m in fm] or list(L["ref"]["months"]) != [mshift(m, 1) for m in rfm]:
        raise StopBake("보유월이 등록과 다르다")
    exp = job.get("f0_expect") or {}
    hc = state_counts([Dl[m] for m in fm])
    if exp and (hc["on"] != exp.get("hold_on") or hc["switch"] != exp.get("hold_switch") or hc["runs"] != exp.get("hold_runs")):
        raise StopBake("창의 상태 개수가 등록 F0 와 다르다")
    h = L["hold"]
    y, mex, mkt = h["y"], h["mex"], h["mkt"]
    s = [int(Dl[m]) for m in fm]
    pre, post = int(Dl[mshift(FORM_FIRST, -1)]), int(Dl[REF_FIRST])
    prim = timing(y, s, pre, post, E)
    draws, n_distinct = placebo(SW, y, s, K_PLACEBO, SEED)
    pl = {"k": K_PLACEBO, "seed": SEED, "n_distinct": n_distinct, "true": prim["delta"], "pct": pct_rank(draws, prim["delta"]), "q": quantiles(draws)}
    crit = t_crit(prim["df"]) if prim["df"] else None
    kt = kt_direction(mex, s, E)
    fa = false_alarm(mkt, y, s)
    s1 = [int(T1l[m]) for m in fm]
    s2 = [int(T2l[m]) for m in fm]
    t1 = timing(y, s1, int(T1l[mshift(FORM_FIRST, -1)]), int(T1l[REF_FIRST]), E)
    t2 = timing(y, s2, int(T2l[mshift(FORM_FIRST, -1)]), int(T2l[REF_FIRST]), E)
    p1c = state_counts([int(Dl[m]) for m in p1_forms()])
    p1r = {"window": [mshift(P1_FIRST, 1), mshift(P1_LAST, 1)], "n": p1c["n"], "n_on": p1c["on"],
           "n_on_frozen": int(((S.get("frozen") or {}).get("oldwin") or {}).get("on", -1)), "measurable": bool(p1c["on"] >= F0_MIN_ON)}
    # 표본 안 참고(2016-09 ~ 2026-08 · 얼린 실운용 상태 · French · 오염) — 창 끝 다음 상태는 모른다(순 판은 나오는 비용을 문다)
    r = L["ref"]
    sr = [int(Df[m]) for m in rfm]
    rpre = int(Df[mshift(REF_FIRST, -1)])
    rf_ = timing(r["y"], sr, rpre, None, E)
    ref = {"window": list(REF_HOLD), "n": len(sr), "states": state_counts(sr), "f": rf_, "kt": kt_direction(r["mex"], sr, E),
           "fa": false_alarm(r["mkt"], r["y"], sr), "on_months_frozen": [m for m in rfm if Df[m]], "on_months_long": [m for m in rfm if Dl[m]],
           "agree": agreement([Dl[m] for m in rfm], sr)}
    hold = {"window": list(HOLD), "n": len(s), "states": hc, "pre": pre, "post": post, "f0_rule_ok": bool(hc["on"] >= F0_MIN_ON),
            "on_months": [m for m in fm if Dl[m]], "primary": prim, "placebo": pl, "t_crit": crit, "kt": kt, "fa": fa, "t1": t1, "t2": t2, "p1": p1r}
    M = {"kind": "q06hold_out", "hold": hold, "ref": ref, "verdict": verdict(prim["delta"], hc["on"]),
         "multiplicity": {"cum_n_before": CUM_N_BEFORE, "rows_counted": N_ROWS_COUNTED, "cum_n_after": CUM_N_BEFORE + N_ROWS_COUNTED,
                          "counted": list(COUNTED)},
         "series": {"hold": {"y": [float(v) for v in y], "s": s}, "ref": {"y": [float(v) for v in r["y"]], "s": sr}}}
    M["predictions"] = predictions(M)
    M["sec"] = {"stat": round(time.time() - t0, 1), "leg": L.get("sec")}
    return M


# ══════════════════════════════════════════════════════════════════════════
def child_main(argv):
    """러너가 부른다: python -X utf8 <뿌리>/build/q06hold.py --child st|f0v|leg|stat --job <작업 파일> --out <경로>."""
    mode = argv[argv.index("--child") + 1]
    job = _json(argv[argv.index("--job") + 1])
    outp = argv[argv.index("--out") + 1]
    import warnings
    warnings.simplefilter("ignore")
    import numpy as np
    fn = {"st": st_child, "f0v": f0v_child, "leg": leg_child, "stat": stat_child}.get(mode)
    if fn is None:
        raise SystemExit("모르는 자식 방식: %s" % mode)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        try:
            res = fn(job)
        except StopBake as e:
            if mode in ("leg", "stat"):
                res = {"kind": "q06hold_%s" % mode, "stopped": str(e)[:300]}
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
