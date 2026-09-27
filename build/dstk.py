# -*- coding: utf-8 -*-
"""build/dstk.py — D13 주식판(DSTK · 실질금리 스타일 로테이션을 ETF 없이 랩 스타일 명단으로) 계산 엔진.
러너(build/dstk_run.py)가 핀 판 임시 뿌리 안에서 자식 과정으로 부른다.

사전등록: build/PREREG-<등록 날짜>-DSTK.md 하나(글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).

무엇을 재나
  규칙(D13 · 한 글자도 안 바꾼다 · PREREG-2026-09-03-RATE2.md §2-1 · T17 `t_signals.dfii10_regime` 과 같은 뜻)
      DFII10 월말 값(그달 마지막 관측) − 3개월 전 월말 값  ≥ +0.20%p → 가치 70 / 성장 30 · ≤ −0.20%p → 30 / 70 · 그 사이 50 / 50 · 월말 판정
  다리(leg)   가치 = 랩 스타일 명단 «spval»(S&P U.S. Style 가치 — B/P · E/P · S/P z) = 빌더 키 `val`(style_top_pdf.sc_val)
              성장 = 랩 스타일 명단 «grow»(S&P U.S. Style 성장 — 3년 EPS 변화÷주가 · 3년 주당매출 성장 · 12개월 모멘텀) = 빌더 키 `grow`(sc_grow)
              매월 말 그날 자료로 다시 고른다(빌더의 채점 · 순위 · 발행사 하나 규칙 그대로) · 다리마다 상위 N(= 10 · 20 · 30)
  감싸기(PIT · 빌더 코드는 고치지 않는다 — 부르는 자리에서 감싼다 · 등록 §2)
      ① 명단 → 가격 키: style_pit_panel.members_at(티커 그대로) 대신 pit_panel.union_members(날짜 인식 별칭 · 재사용 티커 · 이중클래스 회사당 하나 ·
         재배정 티커 마지막 달 제외) — 10년 창에서 FB→META 같은 개명 · 재사용 티커가 빌더 그대로면 빠진다(F0 셈)
      ② 채점 가격 수준: 빌더는 배당조정 종가를 비율 분모(B/P · E/P · S/P · EPS 변화÷주가)와 시총에 쓴다(그 시점에 몰랐던 뒤 배당이 과거 주가를
         낮춘다 = 선견) → 오늘 518종은 결정일 수준을 그날 거래 가격 기준(V-D1 · yfinance auto_adjust=False Close · 빌더가 모르는 분할 행은
         되돌림 · 저장소 밖 캐시 · 묶음 해시 고정)으로 맞춘다. 12개월 모멘텀은 빌더와 같은 랩가 비율(총수익 · 두 날 사이 사건만 담아 선견 없음).
         수익 경로는 랩 배당조정 가격(총수익) 그대로다. 편출 · 별칭 키는 랩 가격 그대로(대부분 배당조정 — 셈을 싣는다 · 등록 §2-3)
  다리 안 가중(계산 전에 골랐다 · 등록 §2-4)  주 = 시총가중 · 종목 상한 25%(RIC 단일 발행사 한도) · 쌍둥이 = 동일가중(빌더 기본)
  슬리브     w_V × 가치 다리 + (1 − w_V) × 성장 다리 · 월말 결정 · 다음 거래일(T+1) 종가 체결 · 편도 10bp · 체결 사이 표류
  펀드 틀    F = 0.9 × SPY TR + 0.1 × 슬리브(qbatch_core.fund_from_path · 매월 말 되돌림 · 되돌림 비용 2 × 10bp × 벗어난 몫) 대 SPY TR
  창         보유월 2016-09 ~ 2026-08(120) · 첫 결정 2016-07(표류 시작 · 창 밖) · 결정 2016-08 ~ 2026-07
  확증 가족  A10 · A20 · A30 — 펀드 월 초과 NW(3) t 의 한쪽 p(H1: 평균 > 0 · 정규 꼬리) · Holm α 0.05 · m 3
  채택 표시  Holm 기각 ∧ 무해(20bp 연 X ≥ 0 ∧ 하락월 평균 X(20bp) ≥ 0 ∧ 편도 연 회전 ≤ 10) — 펀드에 붙이는 것은 사용자 결정(날짜 없음)
  대조 · 쌍둥이 · 참고  S{N} 같은 N 정적 50/50(기전 = A − S) · E{N} 동일가중 쌍둥이 · P{N} 채점 가격 감싸기 없는 판(빌더 가격 그대로 · 민감도) ·
             RETF(IVE/IVW 같은 규칙 · 같은 틀 · T+1 — 참고 줄 · 보유 아님) · EG30 V0(얼린 _qbatch.json · 참고 줄) · x-bmrot(얼린 _fund_mix.json · 참고 줄)

🚨 랩 규율: 이 모듈의 수익 경로(main_child)는 등록 커밋이 origin 에 오른 뒤 러너의 한 번 굽기와 눈가린 연기에서만 돈다.
   f0_child 는 개수 · 날짜 · 커버리지 · 동일성(참/거짓) · 시장 상태 개수(DFII10 국면 · S&P 500 하락월)만 돌려준다 — 수익 · 초과 · 신호-수익 통계 없음.
🚨 머리에서는 표준 라이브러리만 부른다(러너 · validate_site 가 numpy 없이 이 파일을 읽을 수 있게).
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import math
import os
import sys
import tempfile
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
NS = (10, 20, 30)                      # 다리마다 종목 수 — 사용자 «10종목이 너무 적으면 20 30 등» (2026-09-27)
NMAX = 30
CAP = 0.25                             # 시총가중 종목 상한(RIC 단일 발행사 25% 한도 · 계산 전 선택)
STYLE_KEYS = {"V": "val", "G": "grow"}                       # style_top_pdf.STYLES 키(빌더)
SCREEN_KEYS = {"V": "spval", "G": "grow"}                    # data/style_top.json 화면 키(사용자의 스타일 top10 명단)
STYLE_REFS = {"V": "S&P 500 Value (S&P U.S. Style)", "G": "S&P 500 Growth (S&P U.S. Style)"}
MIN_NAMES = 100                        # style_top_pdf.MIN_NAMES(빌더의 «자료가 얕다» 관문) — 같아야 한다
LAG_DAYS, ANN_LAG_DAYS = 45, 90        # style_top_pdf 재무 공시 지연(분기 · 연간 주식수) — 같아야 한다
THR = 0.20                             # D13 문턱(%p)
W_V = {"value": 0.70, "neutral": 0.50, "growth": 0.30}
LAG_M = 3                              # «3개월 전 월말»
SLEEVE = 0.10
COST = 0.0010                          # 편도 10bp(슬리브 체결 · 펀드 되돌림)
COST20 = 0.0020                        # 무해 판정용 편도 20bp
TURN_MAX = 10.0                        # 무해: 슬리브 편도 연 회전 ≤ 10
HOLD = ("2016-09", "2026-08")
N_HOLD = 120
FORM_WARM = "2016-07"                  # 첫 결정(체결 2016-08 첫 거래일 · 창 밖 · 비용도 창 밖)
FORM_FIRST, FORM_LAST = "2016-08", "2026-07"
ANCHOR_FORM = "2026-08"                # F0 명단 대조(data/style_perf.json 의 prev · 2026-08-31)
ANCHOR_MIN = 8                         # 빌더 가격판(P) N=10 명단과 게시 prev 가 다리마다 10 중 8 이상 같아야(구현 결함 관문)
EXEC_LAG = 1                           # T+1
HOLM_ALPHA = 0.05
NW_LAG = 3
DIRECTION = +1                         # H1: 펀드 월 초과 평균 > 0
F0A_CORR, F0A_GAP = 0.98, 0.30         # 가격 위생 관문(pit_panel.f0_gate 와 같은 문턱)
COV_LATE = 0.80                        # 커버리지 부분 창: 가치 채점 수 ÷ 명단(가격 선) ≥ 0.80 이 끝까지 이어지는 첫 결정 뒤
VD1_N = 518
# 채점 가격 판정(감싸기 ② · 등록 §2-3) — 랩가(야후 배당조정 · 소수 둘째 자리)를 V-D1 자신의 Dividends 열로 다시 만들어 본다
VD1_ROUND = 0.0051                     # 랩가 반올림(0.01 의 반 + 여유) — 절대 허용 폭
VD1_TOL = 0.002                        # 배당 모형과의 상대 허용 폭(반올림 폭 위에) — 넘는 날이 하나라도 있으면 «배당으로 설명 못 하는 계단» → 대체
VD1_END_TOL = 0.005                    # 마지막 공통 날 |랩가 ÷ V-D1 − 1| ≤ 0.005(같은 분할 기준 · 같은 증권)
SPLIT_TOL = 0.002                      # V-D1 분할 행 ↔ data/splits.json 행: 같은 날 · 비율 0.2% 안이면 빌더가 아는 분할(주식수 · EPS 되맞춤)
PRIMARY = ("A10", "A20", "A30")
ROWS = tuple("%s%d" % (p, n) for p in ("A", "S", "E", "P") for n in NS) + ("RETF",)
CUM_N_BEFORE = 985                     # build/PREREG-2026-09-27-WBATCH-RESULT.md «랩 945 + 이 굽기 팔 40 = 985»(문서마다 기저가 다르다 — 가장 큰 값)
N_ROWS_COUNTED = 13                    # A · S · E · P 각 3 + RETF 1(IVE/IVW 를 T+1 틀로 다시 잰 것도 센다) — 다리 단독 경로 · 위생 B0 는 전략이 아니다
# 등록 F0 개수(러너 --f0 가 핀 판 자료로 센 값 · 2026-09-27 · 수익 없음) — 굽기 F0 가 같아야 표식을 쓴다
F0_EXPECT = {'n_forms': 121, 'n_valid': 121, 'first_valid': '2016-07', 'cov_late_from': '2019-06', 'n_pool_min': 464, 'n_pool_max': 521, 'v_scored_min': 144, 'v_scored_max': 483, 'g_scored_min': 462, 'n_asis_min': 400, 'regime_value': 36, 'regime_neutral': 53, 'regime_growth': 31, 'regime_switches': 41, 'regime_warm': 'neutral', 'regime_edge': 5, 'down_n': 39, 'down_frozen_n': 35, 'vd1_n': 518, 'vd1_used': 518, 'vd1_fallback': 0, 'anchor_val_adj': 10, 'anchor_grow_adj': 10, 'anchor_val_wrap': 10, 'anchor_grow_wrap': 10, 'asis_missing_n_names': 140, 'split_rev_rows': 37, 'split_rev_names': 31, 'split_rev_cells': 1538, 'splits_json_not_vd1': 0, 'lvl_adj_first': 123, 'lvl_adj_min': 5, 'lvl_adj_max': 123, 'lvl_pr_first': 34, 'reassigned_cells': 10, 'seam_cut_names': 93, 'home_val_overlap': 8, 'home_grow_overlap': 9}
VD1_DIGEST = '1f552d177d0699c7aa4c9f7779e2c0c463e2f2057e3663b623b00e4adf6ffd4c'   # V-D1 묶음 해시(오늘 518종 · 규칙은 vd1_digest)
LATE_FROM = '2019-06'                    # 커버리지 부분 창 첫 보유월(F0 셈 · 가치 채점 ≥ 80% 가 끝까지 이어지는 첫 결정의 다음 달)

# 이름(표시용 · 계산에 쓰지 않는다)
ROW_LABEL = {"A": "주 — 금리 틸트 · 시총가중(상한 25%)", "S": "대조 — 같은 N 정적 50/50 · 시총가중", "E": "쌍둥이 — 금리 틸트 · 동일가중",
             "P": "민감도 — 금리 틸트 · 시총가중 · 빌더 가격(배당조정) 그대로 채점", "RETF": "참고 — IVE/IVW 같은 규칙(T+1 · 보유 아님)"}


class StopBake(RuntimeError):
    """등록된 멈춤 조건 · 결정적 자기 점검 실패 — 굽기 자식이 {"stopped": 사유} 로 돌려준다(다시 굽기로 풀리지 않는다 · 멈춤 기록이 결과다)."""


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


def formations():
    """결정 월 — 첫 결정(표류 시작) 2016-07 + 2016-08 ~ 2026-07."""
    return [FORM_WARM] + months_between(FORM_FIRST, FORM_LAST)


def _json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _wjson(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(p + ".part", p)


def _sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _ok(v):
    return v == v and v is not None and v > 0


# ══════════════════════════════════════════════════════════════════════════
#  규칙 — D13 국면(DFII10 · 월말 판정)
# ══════════════════════════════════════════════════════════════════════════
def dfii_month_last(series):
    """{날짜: 값} → {YYYY-MM: 그달 마지막 관측} — t_signals.month_last(d.dropna().groupby(월).last()) 와 같은 뜻."""
    out = {}
    for d in sorted(series):
        v = series[d]
        if v is None:
            continue
        out[d[:7]] = float(v)
    return out


def regime_at(ml, f):
    """결정 월 f → {d, code, w_v} · 자료 없으면 None. d = ml[f] − ml[f − 3](부동소수 그대로 비교 — T17 _regime 과 같다)."""
    a, b = ml.get(f), ml.get(mshift(f, -LAG_M))
    if a is None or b is None:
        return None
    d = a - b
    code = "value" if d >= THR else ("growth" if d <= -THR else "neutral")
    return {"d": d, "code": code, "w_v": W_V[code]}


def regimes(macro_dfii, forms):
    ml = dfii_month_last(macro_dfii)
    return {f: regime_at(ml, f) for f in forms}


# ══════════════════════════════════════════════════════════════════════════
#  자료 — 세계(pit_panel) · 빌더 패널(style_top_pdf.Panel) · 채점 가격(V-D1 감싸기)
# ══════════════════════════════════════════════════════════════════════════
def vd1_dir():
    return os.environ.get("DSTK_VD1") or os.path.join(tempfile.gettempdir(), "vbatch_cache", "raw", "vd1")


def vd1_path(t, d=None):
    return os.path.join(d or vd1_dir(), t.replace("^", "_") + ".csv")


def vd1_digest(tickers, d=None):
    """V-D1 묶음 해시 — sha256(«티커\\t파일 sha256\\n» 을 티커 차례로) · 없는 파일 목록."""
    lines, miss = [], []
    for t in sorted(tickers):
        p = vd1_path(t, d)
        if not os.path.exists(p):
            miss.append(t)
            continue
        lines.append("%s\t%s\n" % (t, _sha256_file(p)))
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(), len(lines), miss


def load_vd1(t, d=None):
    """V-D1 CSV(Date · Close · Dividends · Stock Splits) → [(날짜, Close, 배당, 분할비)] 날짜 차례 · 파일 없으면 None.
    Close 는 야후가 분할 행(분사를 분할로 적은 비정수 행 포함)으로 과거를 나눈 값이다 — 배당은 빠져 있다."""
    p = vd1_path(t, d)
    if not os.path.exists(p):
        return None
    out = []
    with io.open(p, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        head = next(rd)
        ci, dv, si = head.index("Close"), head.index("Dividends"), head.index("Stock Splits")
        for r in rd:
            if len(r) <= max(ci, dv, si) or r[ci] in ("", "nan", "NaN"):
                continue
            try:
                c = float(r[ci])
                x = float(r[dv] or 0)
                s = float(r[si] or 0)
            except ValueError:
                continue
            out.append((r[0][:10], c, x if x == x else 0.0, s if s == s else 0.0))
    out.sort(key=lambda z: z[0])
    return out


def load_vd1_close(dates, t, d=None):
    """V-D1 Close 를 격자 위로(격자에 없는 날은 NaN) · 파일 없으면 None."""
    import numpy as np
    rows = load_vd1(t, d)
    if rows is None:
        return None
    di = {x: j for j, x in enumerate(dates)}
    a = np.full(len(dates), np.nan)
    for dd, c, _x, _s in rows:
        j = di.get(dd)
        if j is not None and c > 0:
            a[j] = c
    return a


def suffix_prod(dates, events):
    """격자 j 마다 Π_{사건 날짜 > dates[j]} 인자 — events = [(날짜, 인자)]."""
    import numpy as np
    ev = sorted(events)
    out = np.ones(len(dates))
    k, acc = len(ev) - 1, 1.0
    for j in range(len(dates) - 1, -1, -1):
        while k >= 0 and ev[k][0] > dates[j]:
            acc *= ev[k][1]
            k -= 1
        out[j] = acc
    return out


def dividend_model(rows, dates):
    """V-D1 자신의 배당 행으로 야후 배당조정 인자를 다시 만든다 — M(d) = Π_{배당락 e > d}(1 − D_e / C_{e 전 행}) (CRSP 식 · 야후 Adj Close 와 같은 규칙)."""
    ev = [(rows[q][0], 1.0 - rows[q][2] / rows[q - 1][1]) for q in range(1, len(rows)) if rows[q][2] > 0 and rows[q - 1][1] > 0]
    return suffix_prod(dates, ev), len(ev)


def scoring_prices(dates, px_lab, today, lo, hi, d=None, splits=None):
    """채점 가격(감싸기 ②) — 오늘 이름 t 마다 **수준 인자** CF[t] = 채점 가격 ÷ 랩가(격자 위 배열)를 만든다.
    ① 판정(배당 모형): 랩가(야후 배당조정 · 소수 둘째 자리)를 V-D1 자신의 Dividends 열로 다시 만든다(dividend_model).
       [lo, hi] 의 모든 공통 날 |랩가 − C·M| ≤ VD1_ROUND + VD1_TOL·C·M ∧ 마지막 공통 날 |랩가/C − 1| ≤ VD1_END_TOL 이면
       «랩가와 V-D1 의 차이를 V-D1 의 배당 행이 다 설명한다» → V-D1 을 쓴다(특별배당 · 합병 특별배당도 배당 행이면 여기서 설명된다 — 대체하지 않는다).
       설명 못 하는 계단(분할 기준 어긋남 · 다른 증권)이 하나라도 있으면 그 이름은 랩가 그대로(대체 · 셈).
    ② 수준: 채점 가격 PS(d) = C(d) × Π_{빌더가 모르는 V-D1 분할 행 s > d} 비율_s. 빌더(tech_backtest._rebase)는 data/splits.json(비율 1.2 이상만)에 있는
       분할만 주식수 · EPS 에 되맞춘다 — 그 밖의 V-D1 분할 행(분사를 적은 비정수 행 · 작은 역분할)은 되돌려 당시 보고 주식수 · EPS 와 같은 기준
       (그날 거래 가격)에 둔다. splits.json 에 있는 행은 되돌리지 않는다(빌더가 주식수 · EPS 를 이미 오늘 기준으로 맞춘다).
    ③ CF(d) = S(d) / r̃(d) — r = 랩가/C(V-D1 이 빈 날은 앞 값 · 첫 값 앞은 첫 값) · S = ② 의 곱. 채점 때 결정일 i 의 CF[i] 를 계열 **전체**에 곱한다(priced):
       수준(비율 분모 · 시총)은 PS(i) · 12개월 모멘텀 a[i]/a[i−252] 는 랩가 비율 그대로(총수익 · 두 날 사이 사건만 담아 선견 없음 · 빌더와 같은 정의).
       랩가가 선 날에만 값이 선다(채점 가능 여부는 그대로 · 수준만 바뀐다). 편출 · 별칭 키는 여기 없다(랩가 그대로)."""
    import numpy as np
    spl = splits or {}
    CF, SR = {}, {}
    info = {"n_today": len(today), "vd1_used": 0, "fallback": [], "why": {}, "split_rev": [], "splits_json_not_vd1": [], "n_div_rows": 0}
    di = {x: j for j, x in enumerate(dates)}
    d_lo = dates[lo]
    for t in sorted(today):
        a = px_lab.get(t)
        if a is None:
            continue
        rows = load_vd1(t, d)
        why = None
        if rows is None:
            why = "V-D1 없음"
        else:
            c = np.full(len(dates), np.nan)
            for dd, cl, _x, _s in rows:
                j = di.get(dd)
                if j is not None and cl > 0:
                    c[j] = cl
            M, n_div = dividend_model(rows, dates)
            both = (~np.isnan(a)) & (~np.isnan(c)) & (a > 0)
            idx = np.flatnonzero(both[lo:hi + 1]) + lo
            if len(idx) < 50:
                why = "공통 날 부족"
            else:
                mod = c[idx] * M[idx]
                if not bool(np.all(np.abs(a[idx] - mod) <= VD1_ROUND + VD1_TOL * mod)):
                    why = "배당으로 설명 못 하는 계단"
                else:
                    allb = np.flatnonzero(both)
                    if abs(float(a[allb[-1]] / c[allb[-1]]) - 1.0) > VD1_END_TOL:
                        why = "끝 비율 1 아님"
        if why:
            info["fallback"].append(t)
            info["why"][why] = info["why"].get(why, 0) + 1
            continue
        info["n_div_rows"] += n_div
        # ② 빌더가 모르는 분할 행(결정 계열 첫 날 뒤) — 되돌린다
        have = [(str(s)[:10], float(r)) for s, r in (spl.get(t) or [])]
        vd_split = {dd: sp for dd, _cl, _x, sp in rows if sp > 0 and sp != 1.0}
        miss = [(dd, sp) for dd, sp in sorted(vd_split.items())
                if dd > d_lo and not any(s == dd and abs(r - sp) <= SPLIT_TOL * sp for s, r in have)]
        info["splits_json_not_vd1"] += [[t, s] for s, _r in have if s > d_lo and s not in vd_split]
        S = suffix_prod(dates, miss) if miss else None
        if miss:
            SR[t] = S
            info["split_rev"] += [[t, dd, sp] for dd, sp in miss]
        rr = np.full(len(dates), np.nan)
        rr[both] = a[both] / c[both]
        j0 = int(np.flatnonzero(both)[0])
        rr[:j0] = rr[j0]
        for j in range(j0 + 1, len(dates)):
            if rr[j] != rr[j]:
                rr[j] = rr[j - 1]
        CF[t] = (S / rr) if S is not None else (1.0 / rr)
        info["vd1_used"] += 1
    info["n_fallback"] = len(info["fallback"])
    info["n_split_rev_rows"] = len(info["split_rev"])
    info["n_split_rev_names"] = len(SR)
    return CF, SR, info


def fx_pit_names():
    out = {}
    d = os.path.join(DATA, "fx_pit")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json"):
                continue
            try:
                j = _json(os.path.join(d, f))
                out[j.get("t") or f[:-5]] = j.get("nm") or ""
            except Exception:                                  # noqa: BLE001
                pass
    return out


def build_world(with_vd1=True, quiet=True):
    """세계 한 벌 — W(pit_panel.load_world) · P(빌더 패널 + 편출 · 별칭 키 · 재무 fx + fx_pit) · CF(채점 가격 수준 인자) · SR(분할 행 되돌림 곱) · G(펀드 격자)."""
    import contextlib
    import numpy as np
    import g_fund as GF
    import pit_panel as PP
    import style_top_pdf as ST
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink if quiet else sys.stdout):
        W = PP.load_world()
        P = ST.Panel()
    if P.dates != W["dates"]:
        raise StopBake("빌더 패널 격자와 pit_panel 격자가 다르다")
    today = set(P.uni)
    P.fx = W["FUND"]
    nm = fx_pit_names()
    for k, a in W["PX"].items():
        if k not in P.px:
            P.px[k] = a
        if k not in P.uni:
            P.uni[k] = {"t": k, "name": nm.get(k) or k, "idx": []}
    if hasattr(P, "_iss"):
        del P._iss
    me = W["me"]
    lo = max(0, me[FORM_WARM] - 300)
    hi = me[ANCHOR_FORM]
    SPL = _json(os.path.join(DATA, "splits.json")).get("co") or {}
    if with_vd1:
        CF, SR, ps_info = scoring_prices(W["dates"], P.px, today, lo, hi, splits=SPL)
    else:
        CF, SR, ps_info = {}, {}, {"vd1_used": 0, "n_fallback": None}
    G = GF.make_grid(W)
    pxm = _json(os.path.join(DATA, "pit_px.json"))
    meta = {"basis": pxm.get("basis") or {}, "stage": pxm.get("stage_src") or {}}
    return {"W": W, "P": P, "CF": CF, "SR": SR, "ps_info": ps_info, "G": G, "today": today, "pxmeta": meta}


def level_basis(Wd, k, date):
    """채점 가격 **수준**의 기준(셈만 · 등록 §2-3) — 'raw'(그날 거래 가격 기준) · 'pr'(배당 없는 가격 계열) · 'adj'(배당조정 = 뒤 배당만큼 낮다).
    오늘 이름: CF 에 있으면 'raw'(V-D1) · 없으면 'adj'(대체 = 랩 배당조정). 편출 · 별칭 키(data/pit_px.json): stage_src 구간이 덮는 날은 그 구간
    basis(pr → 'pr' · tr · tr_derived → 'adj') · basis 표의 db_pr 새 키 → 'pr'(사내 DB 가격수익) · db_scaled → 'adj'(랩 배당조정 계열에 비율로 맞춤) ·
    그 밖 → 'adj'(yfinance auto_adjust=True — 편출 · 다운로드 날까지의 배당만큼 낮다)."""
    if k in Wd["today"]:
        return "raw" if k in Wd["CF"] else "adj"
    for rg in Wd["pxmeta"]["stage"].get(k) or []:
        if rg.get("from", "") <= date <= rg.get("to", ""):
            return "pr" if rg.get("basis") == "pr" else "adj"
    b = Wd["pxmeta"]["basis"].get(k) or {}
    if b.get("basis") == "db_pr" and b.get("new_key"):
        return "pr"
    return "adj"


# ══════════════════════════════════════════════════════════════════════════
#  명단 · 채점 · 순위(빌더 함수 그대로 · 부르는 자리에서 감싼다)
# ══════════════════════════════════════════════════════════════════════════
def pool_at(W, f):
    """결정 월 f 말의 명단(S&P 500 ∪ NASDAQ 100 · 날짜 인식 가격 키 · 이중클래스 하나 · 재배정 제외) 가운데 그날 가격이 선 키 · 키 → 명단 티커."""
    import pit_panel as PP
    i = W["me"][f]
    mem, n_list = PP.union_members(W, f, i)
    k2t = {}
    for t, k in mem:
        p = W["PX"][k][i]
        if p == p and p > 0:
            k2t.setdefault(k, t)
    return sorted(k2t), k2t, n_list, len(mem)


def priced(fn, CF):
    """채점 함수를 채점 가격 수준으로 감싼다 — 부르는 동안만 P.px[t] 를 «랩가 계열 × CF[t][i]»(결정일 i 의 수준 인자 한 개)로 바꾸고 반드시 되돌린다
    (style_pit_panel.narrowed 와 같은 꼴). 결정일 값 = 채점 가격 수준 · 두 날의 비율(모멘텀) = 랩가 비율 그대로."""
    def g(P, i):
        sp = P.px
        P.px = {t: ((a * CF[t][i]) if t in CF else a) for t, a in sp.items()}
        try:
            return fn(P, i)
        finally:
            P.px = sp
    return g


def style_fn(key):
    import style_top_pdf as ST
    return {"val": ST.sc_val, "grow": ST.sc_grow}[key]


def score(P, key, pool, i, CF=None):
    """빌더 채점(sc_val · sc_grow) — 채점 모집단까지 그 시점 명단으로 좁힌다(style_pit_panel.narrowed · PIT 의 정확한 뜻) · CF 면 채점 가격 수준으로."""
    import style_pit_panel as SPP
    fn = style_fn(key)
    inner = priced(fn, CF) if CF is not None else fn
    pset = set(pool)
    return SPP.narrowed(inner, lambda _i: pset)(P, i)


def ranked(P, s, tie, pool, i):
    """style_top_pdf.backtest 의 pick 그대로 — 가격 선 후보 · (−점수, −동점가르개, 티커) 차례 · 발행사 하나(클래스 A 우선) · 개수 제한 없음."""
    import numpy as np
    import style_top_pdf as ST
    pset = set(pool)
    ok = [t for t in s if t in P.px and not np.isnan(P.px[t][i]) and t in pset]
    ok.sort(key=lambda t: (-s[t], -tie.get(t, 0.0), t))
    _iss = ST.iss_of(P)
    groups = collections.OrderedDict()                       # 발행사 → 순위 차례 이름들(빌더의 same 목록과 같은 차례)
    for t in ok:
        groups.setdefault(_iss.get(t, t), []).append(t)
    ded = []
    for k, same in groups.items():
        a_ = next((x for x in same if ST.is_class_a(P, x)), None)
        ded.append(a_ or same[0])
    return ded


def mcaps(P, names, i, CF=None):
    """시총 = 채점 가격 수준(또는 빌더 가격) × 그 시점 주식수(style_top_pdf.mcap · 공시 지연 그대로)."""
    import style_top_pdf as ST
    sp = P.px
    if CF is not None:
        P.px = {t: ((sp[t] * CF[t][i]) if t in CF else sp[t]) for t in names if t in sp}
    try:
        return {t: ST.mcap(P, t, i) for t in names}
    finally:
        P.px = sp


def leg(P, key, pool, i, CF=None, nmax=NMAX):
    """한 다리 — 채점 수 < MIN_NAMES 면 못 고른다(빌더 관문) · 순위 차례로 시총이 선 이름만 nmax 개까지(두 가중이 같은 명단을 들게)."""
    s, tie = score(P, key, pool, i, CF)
    out = {"n_scored": len(s), "ok": False}
    if len(s) < MIN_NAMES:
        out["why"] = "min_names"
        return out
    ded = ranked(P, s, tie, pool, i)
    out["n_ranked"] = len(ded)
    names, mc, skip = [], {}, 0
    for q in range(0, len(ded), 40):
        chunk = ded[q:q + 40]
        m = mcaps(P, chunk, i, CF)
        for t in chunk:
            if m.get(t) and m[t] > 0:
                names.append(t)
                mc[t] = float(m[t])
                if len(names) >= nmax:
                    break
            else:
                skip += 1
        if len(names) >= nmax:
            break
    out.update({"names": names, "mcap": mc, "n_skip_mcap": skip, "ok": len(names) >= min(NS)})
    out["ok_n"] = {n: len(names) >= n for n in NS}
    return out


def cap_weights(mc, cap=CAP):
    """시총 비례 · 상한 cap(넘친 몫은 상한 안 걸린 이름에 시총 비례로 다시 나눈다 · 반복)."""
    names = sorted(mc)
    if len(names) * cap < 1 - 1e-12:
        raise StopBake("상한 %.2f 로 %d 종목을 채울 수 없다" % (cap, len(names)))
    tot = sum(mc[t] for t in names)
    w = {t: mc[t] / tot for t in names}
    fixed = set()
    for _ in range(len(names) + 1):
        over = [t for t in names if t not in fixed and w[t] > cap + 1e-15]
        if not over:
            break
        fixed.update(over)
        free = [t for t in names if t not in fixed]
        rem = 1.0 - cap * len(fixed)
        ft = sum(mc[t] for t in free)
        for t in fixed:
            w[t] = cap
        for t in free:
            w[t] = rem * mc[t] / ft if ft > 0 else rem / len(free)
    return w


def leg_weights(lg, n, scheme):
    names = lg["names"][:n]
    if len(names) < n:
        return None
    if scheme == "ew":
        return {t: 1.0 / n for t in names}
    return cap_weights({t: lg["mcap"][t] for t in names})


def exec_target(PX, i_exec, wv_leg, wg_leg, wv):
    """체결 날(T+1) 목표 — 다리마다 그날 가격 없는 이름을 빼고 다리 안에서 비례로 다시 나눈 뒤 w_V · (1 − w_V) 로 섞는다."""
    out, drop = {}, 0
    for lw, a in ((wv_leg, wv), (wg_leg, 1.0 - wv)):
        if a <= 0 or not lw:
            continue
        keep = {t: x for t, x in lw.items() if _ok(PX[t][i_exec])}
        drop += len(lw) - len(keep)
        s = sum(keep.values())
        if s <= 0:
            raise StopBake("체결 날 다리 전체 가격 없음")
        for t, x in keep.items():
            out[t] = out.get(t, 0.0) + a * x / s
    return out, drop


# ══════════════════════════════════════════════════════════════════════════
#  경로 · 펀드
# ══════════════════════════════════════════════════════════════════════════
def book_path(PX, execs, i_end, cost, i_window=None):
    """체결 목록 [(체결 날 i, {키: 비중})] → 일간 경로. 첫 체결 전은 현금 1(첫 체결 비용 포함) · 체결 날 값 = 비용 뒤 값(랩 규약) ·
    값 없는 날은 마지막 값(인수 · 상장폐지 = 마지막 가격). 회전 = i_window 뒤 체결의 (거래액 / 값) 합 ÷ 2 ÷ 창 연수."""
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
    return {"path": path, "turn": traded_in / 2.0 / (N_HOLD / 12.0), "n_exec": len(execs)}


def fund(G, path, forms, cost, turn=None):
    import qbatch_core as QC
    return QC.fund_from_path(G, {"path": path, "turn": turn}, forms, cost=cost, basis="TR")


def path_monthly(path, G, hold):
    """경로 → 보유월 수익(%) — 전달 말 → 그달 말."""
    import numpy as np
    return np.array([(path[G.me[h]] / path[G.me[mshift(h, -1)]] - 1.0) * 100 for h in hold])


# ══════════════════════════════════════════════════════════════════════════
#  판정 — Holm · 무해 · 채택 표시 · 예측
# ══════════════════════════════════════════════════════════════════════════
def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def holm_family(nw_t):
    """한쪽 p = norm_sf(DIRECTION × NW t) · v_tests.holm(α 0.05)."""
    import v_tests as VT
    p = {k: (norm_sf(DIRECTION * t) if t is not None else None) for k, t in nw_t.items()}
    h = VT.holm(p, HOLM_ALPHA)
    return {"p": p, "reject": h["reject"], "threshold": h["threshold"], "order": h["order"], "m": h["m"], "alpha": HOLM_ALPHA}


def frozen_down():
    """무해의 하락월 — 얼린 data/mech_episodes.json months.down_m(보유 창 안 · SPY TR 월 수익 < 0 · 35달 · 배치 W w_core.down_months 와 같은 목록)."""
    ME = _json(os.path.join(DATA, "mech_episodes.json"))
    return set(m for m in ME["months"]["down_m"] if HOLD[0] <= m <= HOLD[1])


def harmless(ex20, hold, down, turn):
    """무해 = 20bp 연 X ≥ 0 ∧ 하락월(얼린 down_m) 평균 X(20bp) ≥ 0 ∧ 슬리브 편도 연 회전 ≤ 10."""
    import numpy as np
    x = np.asarray(ex20, float)
    dm = np.array([h in down for h in hold])
    ann = float(x.mean() * 12)
    dmean = float(x[dm].mean()) if dm.any() else None
    c = {"ann_x20_ge0": ann >= 0.0, "down_x20_ge0": dmean is not None and dmean >= 0.0, "turn_le10": turn is not None and turn <= TURN_MAX}
    return {"harmless": bool(all(c.values())), "conds": c, "ann_x20": ann, "down_mean_x20": dmean, "n_down": int(dm.sum()), "turn": turn}


def verdict(adopt, reject):
    """결과 문서 «판정:» — 채택 표시 ≥ 1 → 보류(펀드에 붙이기는 사용자 결정) · 기각 ≥ 1(표시 없음) → 측정만 · 기각 0 → 기각."""
    if any(adopt.values()):
        return "보류"
    if any(reject.values()):
        return "측정만"
    return "기각"


def tilt_read(mech_mean_ann, a_nw_t, s_nw_t):
    """채택 표시의 읽기(등록 §5-2) — 기전 A − S 펀드 연 평균 ≤ 0 이거나(없으면) S 의 NW t ≥ A 의 NW t 이면 정적 바스켓 몫(참)."""
    basket = (mech_mean_ann is None or mech_mean_ann <= 0.0) or (a_nw_t is None) or (s_nw_t is not None and s_nw_t >= a_nw_t)
    return {"static_basket": bool(basket), "mech_mean_ann": mech_mean_ann, "a_nw_t": a_nw_t, "s_nw_t": s_nw_t}


def predictions(R):
    """미리 적은 예측(계산 전 고정 · 결과 문서가 채점) — 참/거짓만."""
    c = R["rows"]
    ann = lambda k: c[k]["m"]["ann_ex"]
    P = {}
    P["P1_no_rejection"] = bool(not any(R["holm"]["reject"].values()))
    P["P2_fund_excess_small"] = bool(all(abs(ann(k)) < 0.5 for k in PRIMARY))
    P["P3_tilt_positive_2of3"] = bool(sum(1 for n in NS if R["mech"][str(n)]["fund"]["mean_ann"] > 0) >= 2)
    P["P4_spread_corr_lt_0_9"] = bool(all((R["fidelity"][str(n)]["spread_corr"] or 0) < 0.9 for n in NS))
    P["P5_ew_below_cap_2of3"] = bool(sum(1 for n in NS if ann("E%d" % n) < ann("A%d" % n)) >= 2)
    P["P6_no_adoption"] = bool(not any(R["adopt"].values()))
    P["P7_price_wrap_small"] = bool(all(abs(R["diffs"]["A-P"][str(n)]["mean_ann"]) < 0.05 for n in NS))
    return P


# ══════════════════════════════════════════════════════════════════════════
#  결정마다 다리(F0 · 굽기가 같이 쓴다)
# ══════════════════════════════════════════════════════════════════════════
def all_legs(Wd, forms_=None, variants=("wrap", "adj")):
    """결정 월 → {variant: {"V": leg, "G": leg}} · 명단 셈."""
    W, P, CF = Wd["W"], Wd["P"], Wd["CF"]
    out, pools = {}, {}
    for f in (forms_ or formations()):
        i = W["me"][f]
        pool, k2t, n_list, n_key = pool_at(W, f)
        pools[f] = {"pool": pool, "k2t": k2t, "n_list": n_list, "n_key": n_key}
        out[f] = {}
        for v in variants:
            ps = CF if v == "wrap" else None
            out[f][v] = {s: leg(P, STYLE_KEYS[s], pool, i, ps) for s in ("V", "G")}
    return out, pools


# ══════════════════════════════════════════════════════════════════════════
#  F0 — 개수 · 날짜 · 동일성만(수익 없음)
# ══════════════════════════════════════════════════════════════════════════
def _asis_injectable(W, window_forms):
    """빌더 그대로(style_pit_panel.prepare)의 편출 주입 규칙을 10년 창에 건 것 — 원시 캐시(격리 뺀) 같은 티커 계열 ≥ 200 관측 · 60거래일 공백 없음."""
    import numpy as np
    import index_members as IM
    import pit_quarantine as PQ
    cp = os.path.join(DATA, "_pit_px_cache.json")
    cache = _json(cp) if os.path.exists(cp) else {}
    PQ.drop(cache, "DSTK F0 빌더 그대로 셈", say=lambda *a: None)
    mem, _c = IM.load()
    di = {d: j for j, d in enumerate(W["dates"])}
    today = W["today"]
    union = set()
    for f in window_forms:
        union |= IM.at(mem, f, label="x", say=lambda *a: None)
    inj = {}
    for t in sorted(union - today):
        c = cache.get(t) or {}
        a = np.full(len(W["dates"]), np.nan)
        n = 0
        for d, v in c.items():
            j = di.get(d)
            if j is not None and v is not None:
                a[j] = float(v)
                n += 1
        if n < 200:
            continue
        idx = np.flatnonzero(~np.isnan(a))
        if len(idx) > 1 and int(np.max(np.diff(idx))) >= 60:
            continue
        inj[t] = a
    return mem, inj


def f0_child():
    """F0 — 수익 없음. 개수 · 날짜 · 커버리지 · 동일성 · 시장 상태 개수(DFII10 국면 · S&P 500 하락월)만."""
    import numpy as np
    import index_members as IM
    import style_top_pdf as ST
    t0 = time.time()
    R = {"kind": "dstk_f0"}
    bad = []
    # 빌더 상수 · 스타일 대응(화면 spval ↔ 빌더 val · grow ↔ grow)
    st = {s[0]: s for s in ST.STYLES}
    R["builder"] = {"min_names": ST.MIN_NAMES, "lag_days": ST.LAG_DAYS, "ann_lag_days": ST.ANN_LAG_DAYS,
                    "val_ref": st["val"][2], "grow_ref": st["grow"][2],
                    "val_fn_is_sc_val": st["val"][3] is ST.sc_val, "grow_fn_is_sc_grow": st["grow"][3] is ST.sc_grow}
    if ST.MIN_NAMES != MIN_NAMES or ST.LAG_DAYS != LAG_DAYS or ST.ANN_LAG_DAYS != ANN_LAG_DAYS:
        bad.append("빌더 상수")
    if st["val"][2] != STYLE_REFS["V"] or st["grow"][2] != STYLE_REFS["G"] or not R["builder"]["val_fn_is_sc_val"] or not R["builder"]["grow_fn_is_sc_grow"]:
        bad.append("스타일 대응")
    scr = {s["key"]: s.get("index_ref") for s in _json(os.path.join(DATA, "style_top.json"))["styles"]}
    R["screen"] = {"spval_ref": scr.get("spval"), "grow_ref": scr.get("grow")}
    if scr.get("spval") != STYLE_REFS["V"] or scr.get("grow") != STYLE_REFS["G"]:
        bad.append("화면 명단 대응")
    # V-D1 묶음 해시
    S = _json(os.path.join(DATA, "stocks.json"))
    today_t = [s["t"] for s in S["stocks"]]
    dg, n_vd1, miss = vd1_digest(today_t)
    R["vd1"] = {"digest": dg, "n": n_vd1, "missing": miss, "n_today": len(today_t)}
    if VD1_DIGEST is not None and dg != VD1_DIGEST:
        bad.append("V-D1 묶음 해시")
    if n_vd1 != VD1_N:
        bad.append("V-D1 이름 수")
    Wd = build_world(with_vd1=True)
    W, P, G = Wd["W"], Wd["P"], Wd["G"]
    R["ps"] = {k: Wd["ps_info"].get(k) for k in ("n_today", "vd1_used", "n_fallback", "why", "n_split_rev_rows", "n_split_rev_names")}
    R["ps"]["fallback"] = sorted(Wd["ps_info"].get("fallback") or [])
    R["ps"]["split_rev"] = [[t, dd] for t, dd, _sp in (Wd["ps_info"].get("split_rev") or [])]       # 되돌린 V-D1 분할 행(이름 · 날짜 · 기업 행위 사실)
    R["ps"]["n_splits_json_not_vd1"] = len(Wd["ps_info"].get("splits_json_not_vd1") or [])
    if R["ps"]["n_splits_json_not_vd1"]:
        bad.append("splits.json 분할이 V-D1 에 없다(%d)" % R["ps"]["n_splits_json_not_vd1"])
    fm = formations()
    # 국면(시장 상태 개수 · 결정 2016-08 ~ 2026-07 = 보유 120)
    A = _json(os.path.join(DATA, "assets.json"))
    rg = regimes(A["macro"]["DFII10"], fm)
    hold_forms = fm[1:]
    if any(rg[f] is None for f in fm):
        bad.append("국면 자료 없음")
    cnt = collections.Counter(rg[f]["code"] for f in hold_forms if rg[f])
    sw = sum(1 for a, b in zip(hold_forms, hold_forms[1:]) if rg[a] and rg[b] and rg[a]["code"] != rg[b]["code"])
    edge = [f for f in fm if rg[f] and abs(abs(rg[f]["d"]) - THR) < 1e-9]
    R["regime"] = {"value": cnt.get("value", 0), "neutral": cnt.get("neutral", 0), "growth": cnt.get("growth", 0), "switches": sw,
                   "warm": rg[FORM_WARM]["code"] if rg[FORM_WARM] else None, "edge_1e9": len(edge),
                   "edge_months": [[f, rg[f]["code"]] for f in edge],
                   "mean_w_v_x1000": int(round(1000 * sum(rg[f]["w_v"] for f in hold_forms) / len(hold_forms)))}
    # T17 함수와 같은가(같은 계열 · pandas)
    try:
        import pandas as pd
        import t_signals as TS
        s = pd.Series({pd.Timestamp(k): v for k, v in A["macro"]["DFII10"].items() if v is not None}, dtype=float).sort_index()
        df = TS.dfii10_regime(s)
        code_map = {TS.VALUE_TILT: "value", TS.NEUTRAL: "neutral", TS.GROWTH_TILT: "growth"}
        same = all(code_map[int(df["regime"].loc[pd.Period(f, "M")])] == rg[f]["code"] for f in fm)
    except Exception as e:                                        # noqa: BLE001
        same = "예외 %s" % type(e).__name__
    R["regime"]["same_as_t17"] = same
    if same is not True:
        bad.append("국면 T17 함수와 다름")
    # 하락월 두 벌(시장 상태 개수) — 지표 표 = S&P 500 PR < 0(qbatch_core.evaluate) · 무해 = 얼린 mech_episodes down_m(SPY TR < 0 · 배치 W 무해와 같은 목록)
    hold = months_between(*HOLD)
    down = set(G.down_months(hold))
    frozen = frozen_down()
    tr_neg = {h for h in hold if G.IX_TR[G.me[h]] / G.IX_TR[G.me[mshift(h, -1)]] - 1 < 0}
    R["down"] = {"n": len(down), "n_frozen": len(frozen), "frozen_eq_spytr": frozen == tr_neg, "n_both": len(down & frozen)}
    if frozen != tr_neg:
        bad.append("얼린 하락월 = SPY TR < 0 이 아니다")
    # 결정마다 명단 · 채점 · 다리
    legs, pools = all_legs(Wd, fm + [ANCHOR_FORM])
    rows = []
    mem_im, inj = _asis_injectable(W, fm)
    for f in fm:
        i = W["me"][f]
        pl = pools[f]
        lw, la = legs[f]["wrap"], legs[f]["adj"]
        lb = collections.Counter(level_basis(Wd, k, W["dates"][i]) for k in pl["pool"])
        n_srev = sum(1 for k in pl["pool"] if k in Wd["SR"] and Wd["SR"][k][i] != 1.0)
        mem_raw = set(W["lists"]["spx"].get(f) or []) | set(W["lists"]["ndx"].get(f) or [])
        n_reas = sum(1 for t in mem_raw if t in W["reassigned"] and f >= W["reassigned"][t].get("last", "9999"))
        # 빌더 그대로의 명단(티커 그대로 · 오늘 유니버스 또는 같은 티커 편출 계열)
        m_im = IM.at(mem_im, f, label="x", say=lambda *a: None)
        asis = [t for t in m_im if (t in Wd["today"] and _ok(P.px[t][i])) or (t in inj and _ok(inj[t][i]))]
        n_rev3 = 0
        for k in pl["pool"]:
            rv, shs = P.asof(k, "rev", i, 16), P.asof(k, "sh", i, 16)
            if len(rv) > 12 and len(shs) > 12:
                n_rev3 += 1
        rows.append({"f": f, "n_list": pl["n_list"], "n_key": pl["n_key"], "n_pool": len(pl["pool"]), "n_asis": len(asis), "n_asis_list": len(m_im),
                     "v_scored": lw["V"]["n_scored"], "g_scored": lw["G"]["n_scored"], "v_scored_adj": la["V"]["n_scored"], "g_scored_adj": la["G"]["n_scored"],
                     "v_ok": bool(lw["V"]["ok"] and lw["V"]["ok_n"][NMAX]), "g_ok": bool(lw["G"]["ok"] and lw["G"]["ok_n"][NMAX]),
                     "v_ok_adj": bool(la["V"]["ok"] and la["V"]["ok_n"][NMAX]), "g_ok_adj": bool(la["G"]["ok"] and la["G"]["ok_n"][NMAX]),
                     "v_skip_mcap": lw["V"].get("n_skip_mcap"), "g_skip_mcap": lw["G"].get("n_skip_mcap"), "n_rev3": n_rev3,
                     "lvl_raw": lb.get("raw", 0), "lvl_adj": lb.get("adj", 0), "lvl_pr": lb.get("pr", 0), "n_srev": n_srev, "n_reas": n_reas,
                     "exec_next_month": W["dates"][i + EXEC_LAG][:7] == mshift(f, 1)})
    valid = [r["f"] for r in rows if r["v_ok"] and r["g_ok"] and r["v_ok_adj"] and r["g_ok_adj"]]
    first_valid = valid[0] if valid else None
    all_valid = len(valid) == len(rows)
    if not all_valid:
        bad.append("결정 %d/%d 만 채울 수 있다" % (len(valid), len(rows)))
    if not all(r["exec_next_month"] for r in rows):
        bad.append("T+1 체결 날이 다음 달 첫 거래일이 아니다")
    cov = [r["v_scored"] / r["n_pool"] for r in rows]
    late = None
    for q in range(len(rows)):
        if all(c >= COV_LATE for c in cov[q:]):
            late = mshift(rows[q]["f"], 1)
            break
    q_ = lambda xs: {"min": int(min(xs)), "med": int(sorted(xs)[len(xs) // 2]), "max": int(max(xs))}
    fr_ = lambda xs: {"min": round(min(xs), 3), "med": round(sorted(xs)[len(xs) // 2], 3), "max": round(max(xs), 3)}
    R["forms"] = {"n": len(rows), "n_valid": len(valid), "first_valid": first_valid, "all_valid": all_valid,
                  "n_list": q_([r["n_list"] for r in rows]), "n_pool": q_([r["n_pool"] for r in rows]), "n_asis": q_([r["n_asis"] for r in rows]),
                  "pool_frac_of_list": fr_([r["n_pool"] / r["n_list"] for r in rows]), "asis_frac_of_pool": fr_([r["n_asis"] / r["n_pool"] for r in rows]),
                  "v_scored": q_([r["v_scored"] for r in rows]), "g_scored": q_([r["g_scored"] for r in rows]),
                  "v_cov": fr_(cov), "g_cov": fr_([r["g_scored"] / r["n_pool"] for r in rows]),
                  "rev3_frac": fr_([r["n_rev3"] / r["n_pool"] for r in rows]),
                  "v_skip_mcap_max": max(r["v_skip_mcap"] or 0 for r in rows), "g_skip_mcap_max": max(r["g_skip_mcap"] or 0 for r in rows),
                  "cov_late_from": late,
                  "lvl_adj": q_([r["lvl_adj"] for r in rows]), "lvl_pr": q_([r["lvl_pr"] for r in rows]), "lvl_raw": q_([r["lvl_raw"] for r in rows]),
                  "lvl_adj_first": rows[0]["lvl_adj"], "lvl_pr_first": rows[0]["lvl_pr"],
                  "split_rev_cells": sum(r["n_srev"] for r in rows), "reassigned_cells": sum(r["n_reas"] for r in rows),
                  "by_year": {y: {"v_cov_min": round(min(c for r, c in zip(rows, cov) if r["f"][:4] == y), 3),
                                  "n_pool_min": min(r["n_pool"] for r in rows if r["f"][:4] == y),
                                  "n_asis_min": min(r["n_asis"] for r in rows if r["f"][:4] == y),
                                  "lvl_adj_max": max(r["lvl_adj"] for r in rows if r["f"][:4] == y)}
                              for y in sorted({r["f"][:4] for r in rows})}}
    if LATE_FROM is not None and late != LATE_FROM:
        bad.append("커버리지 부분 창")
    # 빌더 그대로 명단이 빠뜨리는 이름(날짜 인식 키로는 선다) — 이름 · 달 수만
    miss = collections.Counter()
    for f in fm:
        i = W["me"][f]
        m_im = IM.at(mem_im, f, label="x", say=lambda *a: None)
        have = {t for t in m_im if (t in Wd["today"] and _ok(P.px[t][i])) or (t in inj and _ok(inj[t][i]))}
        for k, t in pools[f]["k2t"].items():
            t_dot = t.replace("-", ".")
            if t_dot not in have and t not in have and k not in have:
                miss[t] += 1
    R["asis_missing_top"] = [[t, n] for t, n in sorted(miss.items(), key=lambda x: (-x[1], x[0]))[:15]]
    R["asis_missing_n_names"] = len(miss)
    # 명단 대조 — 빌더 가격판(P) N=10 vs 게시 style_perf.json prev(2026-08-31)
    sp = {s["key"]: s for s in _json(os.path.join(DATA, "style_perf.json"))["styles"]}
    anc = {}
    for s_, key in (("V", "val"), ("G", "grow")):
        pub = sp.get(key) or {}
        prev = pub.get("prev") or {}
        pn = [r["t"] for r in (prev.get("rows") or [])]
        mine_adj = legs[ANCHOR_FORM]["adj"][s_]["names"][:10] if legs[ANCHOR_FORM]["adj"][s_]["ok"] else []
        mine_wrap = legs[ANCHOR_FORM]["wrap"][s_]["names"][:10] if legs[ANCHOR_FORM]["wrap"][s_]["ok"] else []
        anc[key] = {"prev_date": prev.get("d"), "n_prev": len(pn), "overlap_adj": len(set(pn) & set(mine_adj)), "overlap_wrap": len(set(pn) & set(mine_wrap))}
        if prev.get("d") != W["dates"][W["me"][ANCHOR_FORM]] or anc[key]["overlap_adj"] < ANCHOR_MIN:
            bad.append("명단 대조 %s" % key)
    R["anchor"] = anc
    # 홈 화면 칩(data/style_top.json · build/style_top.py · 벤더 스냅샷 비율)과 빌더 명단(data/style_perf.json today · SEC 재무 45일 지연)의 겹침 — 게시 두 파일의 이름 수만
    home = {s["key"]: s for s in _json(os.path.join(DATA, "style_top.json"))["styles"]}
    R["home"] = {}
    for hk, bk in (("spval", "val"), ("grow", "grow")):
        hn = [r.get("t") for r in (home.get(hk) or {}).get("top") or []][:10]
        td = (sp.get(bk) or {}).get("today") or {}
        bn = [r["t"] for r in (td.get("rows") or [])][:10]
        R["home"][hk] = {"home_as_of": _json(os.path.join(DATA, "style_top.json")).get("as_of"), "builder_today_d": td.get("d"),
                         "n_home": len(hn), "n_builder": len(bn), "overlap": len(set(hn) & set(bn))}
    # 물려받은 선견 자격 규칙 두 개(등록 §2-2) — 개수만
    import tech_backtest as TBm
    SPLj = _json(os.path.join(DATA, "splits.json")).get("co") or {}
    R["inherited"] = {"reassigned_cells": R["forms"]["reassigned_cells"],
                      "seam_cut_names": sum(1 for t in (getattr(TBm, "SPLIT_BREAKS", {}) or {}) if t not in Wd["today"] and t not in SPLj)}
    # 등록 기대값(개수) 대조
    R["expect_keys"] = sorted(_f0_signature(R))
    if F0_EXPECT is not None:
        sig = _f0_signature(R)
        diff = sorted(k for k in set(sig) | set(F0_EXPECT) if sig.get(k) != F0_EXPECT.get(k))
        R["expect_diff"] = diff
        if diff:
            bad.append("등록 F0 개수와 다름(%s)" % ", ".join(diff[:6]))
    R["bad"] = bad
    R["ok"] = not bad
    R["sec"] = round(time.time() - t0, 1)
    return R


def _f0_signature(R):
    """등록 커밋에 박는 F0 개수(정수 · 날짜 · 참/거짓만) — 굽기 F0 가 같아야 표식을 쓴다."""
    fo, rg = R["forms"], R["regime"]
    return {"n_forms": fo["n"], "n_valid": fo["n_valid"], "first_valid": fo["first_valid"], "cov_late_from": fo["cov_late_from"],
            "n_pool_min": fo["n_pool"]["min"], "n_pool_max": fo["n_pool"]["max"], "v_scored_min": fo["v_scored"]["min"], "v_scored_max": fo["v_scored"]["max"],
            "g_scored_min": fo["g_scored"]["min"], "n_asis_min": fo["n_asis"]["min"],
            "regime_value": rg["value"], "regime_neutral": rg["neutral"], "regime_growth": rg["growth"], "regime_switches": rg["switches"],
            "regime_warm": rg["warm"], "regime_edge": rg["edge_1e9"], "down_n": R["down"]["n"], "down_frozen_n": R["down"]["n_frozen"],
            "vd1_n": R["vd1"]["n"], "vd1_used": R["ps"]["vd1_used"], "vd1_fallback": R["ps"]["n_fallback"],
            "anchor_val_adj": R["anchor"]["val"]["overlap_adj"], "anchor_grow_adj": R["anchor"]["grow"]["overlap_adj"],
            "anchor_val_wrap": R["anchor"]["val"]["overlap_wrap"], "anchor_grow_wrap": R["anchor"]["grow"]["overlap_wrap"],
            "asis_missing_n_names": R["asis_missing_n_names"],
            "split_rev_rows": R["ps"]["n_split_rev_rows"], "split_rev_names": R["ps"]["n_split_rev_names"], "split_rev_cells": fo["split_rev_cells"],
            "splits_json_not_vd1": R["ps"]["n_splits_json_not_vd1"],
            "lvl_adj_first": fo["lvl_adj_first"], "lvl_adj_min": fo["lvl_adj"]["min"], "lvl_adj_max": fo["lvl_adj"]["max"], "lvl_pr_first": fo["lvl_pr_first"],
            "reassigned_cells": R["inherited"]["reassigned_cells"], "seam_cut_names": R["inherited"]["seam_cut_names"],
            "home_val_overlap": R["home"]["spval"]["overlap"], "home_grow_overlap": R["home"]["grow"]["overlap"]}


# ══════════════════════════════════════════════════════════════════════════
#  굽기 본체(🚨 수익 — 등록 커밋 뒤 한 번 굽기 · 눈가린 연기에서만)
# ══════════════════════════════════════════════════════════════════════════
def main_child():
    try:
        return _main_body()
    except StopBake as e:
        return {"kind": "dstk_out", "stopped": str(e)[:300]}
    except Exception as e:                                        # noqa: BLE001
        import g_fund as GF
        if isinstance(e, GF.StopBake):
            return {"kind": "dstk_out", "stopped": str(e)[:300]}
        raise


def _main_body():
    import numpy as np
    import eg30plus as EP
    import g_fund as GF
    import pit_panel as PP
    import qbatch_core as QC
    t0 = time.time()
    S = _json(os.path.join(DATA, "stocks.json"))
    dg, n_vd1, _miss = vd1_digest([s["t"] for s in S["stocks"]])
    if VD1_DIGEST is not None and dg != VD1_DIGEST:
        raise StopBake("V-D1 묶음 해시가 등록 값과 다르다")
    Wd = build_world(with_vd1=True)
    W, P, G = Wd["W"], Wd["P"], Wd["G"]
    PX, me = W["PX"], W["me"]
    fm = formations()
    forms_hold = months_between(FORM_FIRST, FORM_LAST)             # fund_from_path 의 편입 월(보유 2016-09 ~ 2026-08)
    hold = [mshift(m, 1) for m in forms_hold]
    i0, iE = me[FORM_FIRST], me[HOLD[1]]
    ffm = GF.ff_monthly(W, _json(os.path.join(DATA, "ff_daily.json")))
    A = _json(os.path.join(DATA, "assets.json"))
    rg = regimes(A["macro"]["DFII10"], fm)
    if any(rg[f] is None for f in fm):
        raise StopBake("국면 자료 없음")
    down_pr = set(G.down_months(hold))                             # 지표 표(qbatch_core.evaluate 와 같다 · S&P 500 PR < 0)
    down = frozen_down()                                           # 무해(얼린 down_m · SPY TR < 0)
    R = {"kind": "dstk_out", "window": list(HOLD), "n_hold": len(hold), "down": {"n_pr": len(down_pr), "n_frozen": len(down)}}
    # ── 가격 위생 관문(패널 시총가중 S&P 500 대 S&P 500 PR · pit_panel.f0_gate) ───────────
    rows_b, _cover = PP.month_rows(W, "spx", forms_hold, HOLD[1])
    pr = {h: (G.IX_PR[me[h]] / G.IX_PR[me[mshift(h, -1)]] - 1) * 100 for h in hold}
    ok_a, corr_a, gap_a = PP.f0_gate(rows_b, {"S&P 500": pr}, "S&P 500", HOLD)
    R["f0a"] = {"ok": bool(ok_a), "corr": corr_a, "gap_pm": gap_a, "n": len(rows_b)}
    if not ok_a:
        raise StopBake("가격 위생 관문 실패(패널 시총가중 S&P 500 대 PR 상관 · 평균 차)")
    # ── 다리 ──────────────────────────────────────────────────────────────
    legs, pools = all_legs(Wd, fm)
    for f in fm:
        for v in ("wrap", "adj"):
            for s_ in ("V", "G"):
                if not (legs[f][v][s_]["ok"] and legs[f][v][s_]["ok_n"][NMAX]):
                    raise StopBake("결정 %s %s %s 다리를 채울 수 없다" % (f, v, s_))
    # ── 줄마다 체결 목록 ───────────────────────────────────────────────────
    specs = {}
    for n in NS:
        specs["A%d" % n] = (n, "cap", "tilt", "wrap")
        specs["S%d" % n] = (n, "cap", "static", "wrap")
        specs["E%d" % n] = (n, "ew", "tilt", "wrap")
        specs["P%d" % n] = (n, "cap", "tilt", "adj")
        specs["LV%d" % n] = (n, "cap", "vonly", "wrap")               # 다리 단독(충실도 · 전략 아님)
        specs["LG%d" % n] = (n, "cap", "gonly", "wrap")
    execs = {k: [] for k in specs}
    comp = {k: collections.Counter() for k in specs if k[0] in "ASEP"}
    for f in fm:
        i = me[f]
        ix = i + EXEC_LAG
        for k, (n, sch, tl, v) in specs.items():
            lv, lg_ = legs[f][v]["V"], legs[f][v]["G"]
            wv_leg, wg_leg = leg_weights(lv, n, sch), leg_weights(lg_, n, sch)
            wv = {"tilt": rg[f]["w_v"], "static": 0.5, "vonly": 1.0, "gonly": 0.0}[tl]
            tgt, drop = exec_target(PX, ix, wv_leg, wg_leg, wv)
            execs[k].append((ix, tgt))
            if k in comp and f != FORM_WARM:
                c = comp[k]
                k2t = pools[f]["k2t"]
                nd = set(W["lists"]["ndx"].get(f) or []) - set(W["lists"]["spx"].get(f) or [])
                both = set(wv_leg) & set(wg_leg)
                for t in set(wv_leg) | set(wg_leg):
                    c["names"] += 1
                    c["ndx_only"] += int(k2t.get(t) in nd)
                    c["not_today"] += int(t not in Wd["today"])
                    lb = level_basis(Wd, t, W["dates"][i]) if (v == "wrap" or t not in Wd["today"]) else "adj"      # P 판: 오늘 이름은 랩 배당조정
                    c["lvl_adj"] += int(lb == "adj")
                    c["lvl_pr"] += int(lb == "pr")
                    c["split_rev"] += int((v == "wrap") and t in Wd["SR"] and Wd["SR"][t][i] != 1.0)
                c["both_legs"] += len(both)
                c["exec_drop"] += drop
                c["forms"] += 1
                c["max_w_x1000"] = max(c["max_w_x1000"], int(round(1000 * max(tgt.values()))))
    # ── 경로 · 펀드 ───────────────────────────────────────────────────────
    frs, frs20, turns, paths = {}, {}, {}, {}
    for k in specs:
        bp = book_path(PX, execs[k], iE, COST, i_window=i0)
        paths[k], turns[k] = bp["path"], bp["turn"]
        if k[0] in "ASEP":
            frs[k] = fund(G, bp["path"], forms_hold, COST, bp["turn"])
            bp20 = book_path(PX, execs[k], iE, COST20, i_window=i0)
            frs20[k] = fund(G, bp20["path"], forms_hold, COST20, bp20["turn"])
    # RETF — IVE/IVW 같은 규칙 · 같은 틀 · T+1(참고 줄 · 보유 아님)
    pa = {d: j for j, d in enumerate(A["dates"])}
    PXE = {}
    for tk in ("IVE", "IVW"):
        arr = [A["px"][tk][pa[d]] if (d in pa and A["px"][tk][pa[d]] is not None) else float("nan") for d in W["dates"]]
        PXE[tk] = QC.ffill(arr)
    ex_e = [(me[f] + EXEC_LAG, {"IVE": rg[f]["w_v"], "IVW": 1.0 - rg[f]["w_v"]}) for f in fm]
    bpe = book_path(PXE, ex_e, iE, COST, i_window=i0)
    frs["RETF"] = fund(G, bpe["path"], forms_hold, COST, bpe["turn"])
    bpe20 = book_path(PXE, ex_e, iE, COST20, i_window=i0)
    frs20["RETF"] = fund(G, bpe20["path"], forms_hold, COST20, bpe20["turn"])
    turns["RETF"] = bpe["turn"]
    for k, fr in frs.items():
        if list(fr["hold"]) != hold:
            raise StopBake("보유월이 창과 다르다(%s)" % k)
    # ── 지표 ──────────────────────────────────────────────────────────────
    R["rows"] = {}
    for k in ROWS:
        m = GF.metrics(G, frs[k], ffm)
        m["turn"] = turns[k]
        x10 = [x for h, x in zip(hold, frs[k]["ex"]) if h in down]
        R["rows"][k] = {"m": m, "m20": {"ann_ex": float(np.mean(frs20[k]["ex"]) * 12), "nw_t": EP.nw_t(np.asarray(frs20[k]["ex"], float)),
                                        "down_mean": float(np.mean([x for h, x in zip(hold, frs20[k]["ex"]) if h in down]))},
                        "down_frozen": {"n": len(x10), "mean": float(np.mean(x10)), "win": float(np.mean(np.asarray(x10) > 0) * 100)},
                        "harmless": harmless(frs20[k]["ex"], hold, down, turns[k])}
    # ── 확증 가족 · 채택 표시 ───────────────────────────────────────────────
    R["holm"] = holm_family({k: R["rows"][k]["m"]["nw_t"] for k in PRIMARY})
    R["adopt"] = {k: bool(R["holm"]["reject"][k] and R["rows"][k]["harmless"]["harmless"]) for k in PRIMARY}
    R["verdict"] = verdict(R["adopt"], R["holm"]["reject"])
    # ── 기전 · 차이 ───────────────────────────────────────────────────────
    R["mech"], R["diffs"] = {}, {"A-E": {}, "A-P": {}, "A-RETF": {}}
    for n in NS:
        a_, s_ = frs["A%d" % n], frs["S%d" % n]
        dsl = np.asarray(a_["basket"], float) - np.asarray(s_["basket"], float)
        R["mech"][str(n)] = {"fund": GF.diff_stats(G, a_, s_, ffm),
                             "sleeve": {"mean_ann": float(dsl.mean() * 12), "nw_t": EP.nw_t(dsl), "win": float(np.mean(dsl > 0) * 100)}}
        for nm, b_ in (("A-E", frs["E%d" % n]), ("A-P", frs["P%d" % n]), ("A-RETF", frs["RETF"])):
            R["diffs"][nm][str(n)] = GF.diff_stats(G, a_, b_, ffm)
    # ── 채택 표시의 읽기(등록 §5-2 · 계산 전 고정 · 표시를 바꾸지 않는다) ──────────────
    #    같은 N 의 기전(A − S) 펀드 연 평균 ≤ 0 이거나 S{N} 의 NW t ≥ A{N} 의 NW t 이면 «정적 바스켓 몫 — 금리 틸트 증거 아님»
    R["tilt_read"] = {k: tilt_read(R["mech"][k[1:]]["fund"].get("mean_ann"), R["rows"][k]["m"].get("nw_t"), R["rows"]["S" + k[1:]]["m"].get("nw_t"))
                      for k in PRIMARY}
    # ── 충실도(ETF 판과 얼마나 같은가) ──────────────────────────────────────
    ive = path_monthly({d: PXE["IVE"][d] for d in range(i0, iE + 1)}, G, hold)
    ivw = path_monthly({d: PXE["IVW"][d] for d in range(i0, iE + 1)}, G, hold)
    R["fidelity"] = {}
    for n in NS:
        lv, lg_ = path_monthly(paths["LV%d" % n], G, hold), path_monthly(paths["LG%d" % n], G, hold)
        R["fidelity"][str(n)] = {"spread_corr": float(np.corrcoef(lv - lg_, ive - ivw)[0, 1]),
                                 "v_corr": float(np.corrcoef(lv, ive)[0, 1]), "g_corr": float(np.corrcoef(lg_, ivw)[0, 1]),
                                 "fund_ex_corr_retf": float(np.corrcoef(np.asarray(frs["A%d" % n]["ex"], float), np.asarray(frs["RETF"]["ex"], float))[0, 1]),
                                 "v_turn": turns["LV%d" % n], "g_turn": turns["LG%d" % n]}
    # ── 커버리지 부분 창(보고만) ─────────────────────────────────────────────
    R["late"] = None
    if LATE_FROM and LATE_FROM in hold and len(hold) - hold.index(LATE_FROM) >= 36:
        R["late"] = {"from": LATE_FROM, "rows": {}, "mech": {}}
        for k in PRIMARY + tuple("S%d" % n for n in NS):
            R["late"]["rows"][k] = GF.metrics(G, GF.sub_fr(G, frs[k], LATE_FROM), ffm)
        for n in NS:
            R["late"]["mech"][str(n)] = GF.diff_stats(G, GF.sub_fr(G, frs["A%d" % n], LATE_FROM), GF.sub_fr(G, frs["S%d" % n], LATE_FROM), ffm)
    # ── 구성(개수 · 수익 아님) ─────────────────────────────────────────────
    R["composition"] = {k: {"forms": c["forms"], "mean_names_x10": int(round(10 * c["names"] / max(1, c["forms"]))),
                            "ndx_only_share_x1000": int(round(1000 * c["ndx_only"] / max(1, c["names"]))),
                            "not_today_share_x1000": int(round(1000 * c["not_today"] / max(1, c["names"]))),
                            "lvl_adj_share_x1000": int(round(1000 * c["lvl_adj"] / max(1, c["names"]))),
                            "lvl_pr_share_x1000": int(round(1000 * c["lvl_pr"] / max(1, c["names"]))),
                            "split_rev_share_x1000": int(round(1000 * c["split_rev"] / max(1, c["names"]))),
                            "both_legs_total": c["both_legs"], "exec_drop_total": c["exec_drop"], "max_w_x1000": c["max_w_x1000"]}
                        for k, c in comp.items()}
    R["regime"] = {"value": sum(1 for f in fm[1:] if rg[f]["code"] == "value"), "neutral": sum(1 for f in fm[1:] if rg[f]["code"] == "neutral"),
                   "growth": sum(1 for f in fm[1:] if rg[f]["code"] == "growth")}
    # ── 참고 줄 ───────────────────────────────────────────────────────────
    Q = _json(os.path.join(DATA, "_qbatch.json"))["V0"]
    v0ex = np.asarray(Q["ex"], float)
    R["eg30_ref"] = {"window": [Q["hold"][0], Q["hold"][-1]],
                     "frozen_eval": {k: Q["eval"].get(k) for k in ("ann_ex", "te", "ir", "nw_t", "win", "years_won", "n_years", "down_mean", "down_win",
                                                                    "crash_won", "surge_won", "sleeve_beta")},
                     "corr_fund_ex": {k: (float(np.corrcoef(np.asarray(frs[k]["ex"], float), v0ex)[0, 1]) if list(Q["hold"]) == hold else None)
                                      for k in PRIMARY + ("RETF",)}}
    FM = _json(os.path.join(DATA, "_fund_mix.json"))
    B = ((FM.get("strategies") or {}).get("B") or {}).get("all") or {}
    R["xbmrot_ref"] = {"window": FM.get("window"), "basis": "S&P 500 PR(배당 없는 지수 · SPY TR 과 다른 잣대)",
                       "frozen": {k: B.get(k) for k in ("ann_ex", "te", "ir", "t", "win")}}
    R["predictions"] = predictions(R)
    R["multiplicity"] = {"m_confirmatory": len(PRIMARY), "alpha": HOLM_ALPHA, "cum_n_before": CUM_N_BEFORE, "rows_counted": N_ROWS_COUNTED,
                         "cum_n_after": CUM_N_BEFORE + N_ROWS_COUNTED}
    R["ps_info"] = {k: Wd["ps_info"].get(k) for k in ("vd1_used", "n_fallback", "n_split_rev_rows", "n_split_rev_names")}
    R["sec"] = round(time.time() - t0, 1)
    return R


def child_main(argv):
    """러너가 부른다: python -X utf8 <뿌리>/build/dstk.py --child f0|main --out <경로>."""
    mode = argv[argv.index("--child") + 1]
    outp = argv[argv.index("--out") + 1]
    import warnings
    warnings.simplefilter("ignore")
    import numpy as np
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        if mode == "f0":
            res = f0_child()
        elif mode == "main":
            res = main_child()
        else:
            raise SystemExit("모르는 자식 방식: %s" % mode)
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
