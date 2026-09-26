# -*- coding: utf-8 -*-
"""build/r_stagem.py — 배치 R(RBATCH) Stage M 기전 엔진 · 통제 패널 · 관문 · 자료 어댑터 한 벌.

카드: R1-OPPSELL(기회주의 내부자 매도 OS · 1차 후보) · R2-LAZYRF(10-Q 위험요인 절 대규모 개정 CH · 1차 후보) · R3-8KNE(FL · 측정).
근본 이유: 두 단계는 «종목 고유 악재로 이름을 빼는» 일을 한다. 펀드 수준 Δ 는 10% 슬리브 · 120개월로는 검정력이 없어서
  (정직한 전망 1), 1차를 시점정확 대형주 세계 전체의 플래그 계수로 옮겼다 — 월별 횡단면 회귀 · NW t · 크기·B/M·모멘텀·반전·섹터 통제
  (batch_design_changes 3). 이 파일이 그 한 벌의 엔진이다. 카드마다 엔진을 따로 두면 반드시 갈린다(이 저장소가 되풀이 밟은 결함).

회귀(월 t 마다 · 등록 규칙 R1 (7) · R2 (9)):
  r_{i,t+1} ~ 1 + 플래그(OS_{t−k} · RS_{t−k} | CH_t · 결측 더미) + log 시총_t + log B/M_t(B/M ≤ 0 · 없음 → 결측 더미)
            + r_t + r_{t−12..t−2} + GICS 섹터 더미(시점정확 pit_gics_sectors)
  JT: k = 0, 1, 2 세 회귀의 계수를 달마다 평균한다(R1 · R3). R2 는 보유 창이 더미 안에 있어 단일 회귀다.
  주 통계: 평균 γ 월 계열의 NW(3) t(eg30plus.nw_t — 복제하지 않는다) · 한쪽 H1 γ < 0 · 임계는 t(T−1).
  변형: 시총가중 WLS(R1 관문 iii · R2 관문 i) · 추가 통제(52주 고점 괴리 + 12개월 수익 · R1 관문 ii) · Δlog(1A 단어수)(R2 관문 ii)
        · 상호작용(플래그 × Eg 상위 40 소속 · 측정) · 표본 제한(T3 · CMP 표본) · 합동 회귀(T5 · 월 고정효과 · 그룹 군집 SE).
  계산은 FWL(프리슈–워–로벨)이다: 통제 블록을 그람–슈미트로 직교화하고 플래그 블록을 잔차화해 푼다 — 전체 OLS 와 같은 계수
  (합성 시험이 명시 설계 lstsq 와 1e-8 로 맞춘다). 종속 열은 순서대로 버린다(절편 → 통제 → 결측 더미 → 섹터 → 플래그).
  플래그가 통제에 걸려 풀리지 않는 달은 None 이고, JT 는 세 k 가 모두 선 달만 평균한다.
  결측 더미: 빈 값을 상수로 채우고 더미를 넣는다 — 더미가 있으면 채운 상수는 계수에 영향이 없다(합성 시험).

표본(R1 (1) · R2 (1)):
  그달 말 S&P 500 ∪ NASDAQ 100(pit_panel.union_members · 날짜 인식 키) 가운데 시점정확 GICS 가 금융이 아니고,
  §A0 발행사 지도로 그룹이 풀리고, FPI(직전 연차보고 20-F·40-F)가 아닌 멤버-월 · 그룹당 한 행(시총이 큰 쪽) · 가격·시총이 선 행.
  r_t · r_{t−12..t−2} 가 없는 행은 뺀다(MISS · 등록 규칙이 결측 더미를 B/M 에만 준다). 보유월 수익은 pit_panel.month_rows 규약
  (달 중간 상장폐지 = 마지막 가격 · 다음 달 가격이 하나도 없으면 0 · 편향 방향은 결과 문서에 선언).
  시총 = 시총 가격 × pit_panel._shares(fx + fx_pit · 90일 지연 · AUDIT-2026-09-20-SHARES2 분할 되맞춤 판 — --construct 가 핀으로 확인).
  🚨 시총 가격(cap_basis): RBATCH_DATA/_px_raw.json(분할만 되맞춘 원 종가 · yfinance auto_adjust=False 'Close' · pit_px.json 과 같은
  {dates, px: {키: {i0, p}}} 모양)이 있으면 그것(raw) · 없으면 배당조정 종가 pxd(div_adjusted). pxd 의 과거 수준은 t 뒤에 받은 배당만큼
  낮다(XOM 2016-08-31 pxd 56.57 · 원 종가 87.14 — 35% 낮다 · VZ 42% · AAPL 8.6%). 그래서 div_adjusted 판의 크기 · B/M · WLS 가중 ·
  커버리지 시총 몫 · 중복 그룹 고르기에는 **미래 배당(삭감 포함)에 따른 누수**가 있다(선언 — --construct 의 고배당 핀 HY_PIN 이 잡는다 ·
  원 종가 판이 서면 그것이 1차 · 배당조정 판은 민감도). 수익 · 반전 · 모멘텀 · 52주 고점은 비율이라 t 뒤 배당 인자가 지워진다.
  B/M = tech_backtest.asof_fund(eq · 90일 지연) ÷ 시총 — 최신 제출본이라 재작성 누수가 있다(선언).
  시차 표지는 **지금 그룹**으로 읽는다 — 지도가 선행 CIK 를 이미 한 그룹으로 이어 붙였으므로, 같은 티커가 k 달 전 다른 그룹이면 그것은
  다른 발행사다(IR 2020-03 · FOXA 2019-03 · JCI 2016-09 — 티커 재사용 · 구성 기록 glag_foreign 으로 센다).
  월 커버리지 F0(가격·시총·B/M·모멘텀이 모두 선 멤버 · 개수 ≥ 0.90 · 시총 ≥ 0.95)와 지도 F0(위반율 ≤ 2%)를 넘은 달만 쓴다.
  남은 T < 84 면 R1 · R2 모두 측정으로 내린다(§F).
  🔒 2026-09-26 등록 전 결정(build_panel 머리말 · PREREG §0b): FPI = 지도 등록 표지(fpi_registered.tm_index · 모든 읽개 같은 칸) ·
  지도 F0 위반 멤버-월은 표본 · 분모 밖 · 시총 · 장부가는 관측 나이 ≤ 550일(TTM_STALE_DAYS) ∧ 펀드 파일 CIK 구간이 그달 §A0 CIK 집합과
  겹칠 때만(FundCik · fresh_consistent) · 시총 몫 가중 = 자기 → 12개월 이음 → 같은 지수 중앙값 · 섹터 더미 = SectorAt(issuer_map.sector_at
  규칙 — 수작업 섹터 표 포함) · 보유월 y = y_rule(계열이 월말 전에 끝나면 이름별 판정 data/_r_ytrunc.json — 거래가 이어진 이름은 결측).

관문(등록 규칙 그대로 · 모두 점 추정):
  R1 (i) γ_OS − γ_RS < 0 · (ii) 52주 고점 괴리 + 12개월 수익을 더 통제해도 γ_OS < 0 · (iii) 시총가중 WLS 에서도 γ_OS < 0
  R2 (i) WLS 에서도 γ_CH < 0 · (ii) Δlog(1A 단어수)를 더 통제해도 γ_CH < 0 · 보고만: 결측 더미 계수 < γ_CH → «분리 실패 오염»
  1차: Holm(가족 α 한쪽 2.5% · m 은 등록 커밋에 고정 · m=2 면 t(119) 2.27 → 1.98) · 자격은 P0 = q·π + (1−q)·α₁ ≥ 0.15
  (batch_design_changes 1 · σ_plan = max(분석적 σ, 칸 맞춘 위약 SD 의 90분위)).

자료 어댑터 — 아직 빌드 중인 세 자료(data/_issuer_map.json · data/_ins_pit/cikmonth.json · data/_tenq_rf.json)의 필드 이름은
  FIELDS 한 곳에만 적는다. 이름이 바뀌면 여기만 고친다. 찾는 필드가 없으면 조용히 0 으로 두지 않고 멈춘다.
  표지 규칙은 정본 빌더에 한 벌만 있다 — R1 = build/r_r1_flags.py(cikmonth: 그룹 → 가용월 → O·R·U·N·all·bO·bR 개수 · months_ok)
  · R2 = build/r_r2flags.py(r2_build → gm). 이 파일은 그 출력을 더미로 옮길 뿐이다(tenq_flags 는 정본을 못 부를 때의 잠정판).
  정본을 import 할 수 없으면 **멈춘다** — RBATCH_PROVISIONAL=1 이고 RBATCH_COMMIT · RBATCH_P0 가 없을 때만 잠정판으로 내려간다
  (ImportError 만 잡는다 · 정본 안의 오류는 그대로 올라간다 · 쓴 판과 정본 파일 sha256 을 FlagPanel.src 와 --construct 기록에 싣는다).
  snap_wt 에서 돌릴 때는 r_r1_flags.py · r_r2flags.py 를 이 파일 옆에 함께 복사한다(refresh_events · qbatch_core 는 이미 있다).
  R2 경계 분포(R2 (7) «직전 달력연도에 공개된 세계 전체 짝»)의 세계 = boundary_world — 표본 규칙(비금융 · FPI 아님 · 지도가 푼 그룹)의
  멤버-월 전체(가격 유무와 무관)를 BOUND_FROM = 2015-01 부터. 패널 행(가격 커버리지를 넘은 것)으로 재면 2016 경계가 없고 2017 경계가
  8~12월 공개분만으로 서며 생존편향을 물려받는다. 창 안 공개연도에 경계가 하나라도 없으면 멈춘다(bounds_gap).
  «모름»(R1 의 N · months_ok 밖 달)은 0 으로 채우고 <표지>_unk 더미를 통제 블록에 넣는다(창 안에서는 거의 없어야 한다 · 개수를 싣는다).
  쌍둥이 표지(r_r1_flags.cikmonth_doc 의 t1_os3 · t2_* · t4_* · t6_*)는 OS_T1 · OS_T2/RS_T2 · OS_T4/RS_T4 · OS_T6/RS_T6 로 옮긴다
  (T2 · T6 의 «모름»은 정본 cikmonth 가 판별 N 을 싣지 않아 1차 os_na · rs_na 로 가늠한다 — 선언 · T4 는 t4_*_na 를 그대로).
  자료가 있는 곳은 RBATCH_DATA(기본 = 이 파일 옆 data/)다 — snap_wt 에서 돌릴 때 저장소 data/ 를 가리킨다.

카드 한 벌(stage_m_r1 · stage_m_r2)은 카드 controls 목록을 **그대로** 돌리고 시도 목록(trials — 돌린 것 · 입력이 없어 못 돌린 것)을
  돌려준다(시도 수 · DSR N). R1 = 주 · 관문 ii · iii · OS×상위40 · 전체 매도 · T1~T6(T2 는 2023-04 전후 분할) · 2020-07 민감도
  [· 2014-07 넓힌 창 민감도 — 그 패널을 줄 때]. R2 = 주(결측 더미 포함) · 관문 i · ii · SimDoc 대조 · iXBRL 전환 · 코로나 진단 ·
  2020-07 민감도 [· 2014-07]. R2 에는 상호작용이 없다(카드에 없는 시도).
  판정(verdict)은 커버리지 T < 84(measure_only)나 표지 F0 실패면 측정으로 내린다 · R1 관문 i 는 RS 밀도 F0 가 실패하면 판정 불가(거짓).
  NW t 는 달력 위치를 지킨다 — 쓴 달이 이어지면 eg30plus.nw_t 그대로 · 빈 달이 끼면 시차 곱을 달력 위에서 잰 nw_t_gap(같은 식 ·
  빈 달 편차 0)을 주 통계로 쓰고 압축 계열 값(nw_t_compressed)과 빈 달 수를 함께 싣는다.

🚨 이 파일은 등록 전에 **실제 표지와 실제 미래 수익의 관계를 계산하지 않는다.** 등록 전에 되는 것은 셋뿐이다 —
  --selftest(합성 자료만) · --construct(PIT 세계로 통제 패널을 짓고 구성만 점검 · 회귀 없음 · 수익 통계 없음)
  · P0 용 σ(sigma_analytic · sigma_placebo — 실제 패널이면 RBATCH_P0=1 이 있어야 돈다 · 위약 평균은 계산도 저장도 않는다).
  실제 패널로 fm()·pooled_fe() 를 부르면 RBATCH_COMMIT(등록 커밋)이 없을 때 멈춘다 — 러너(§E)가 등록 커밋 뒤 한 번 부른다.

  python build/r_stagem.py --selftest
  cd $TEMP/snap_wt && RBATCH_DATA=<발행사 지도가 있는 data 경로> python -X utf8 build/r_stagem.py --construct [--out 경로]
  python build/r_stagem.py --ytrunc-scan [--overlay 스테이징 pit_px 모양 파일 …] [--out 경로]   # y 규칙 판정 대상 · 판정 없으면 종료 1
  (저장소 작업 트리는 가격 격자가 어긋나 pit_panel.load_world 가 멈춘다 — 자료 판 작업 사본 snap_wt 로 복사해서 돌린다)
  RBATCH_PX_OVERLAY=<저장소 밖 pit_px_stage/1 파일> python build/r_stagem.py --construct …   # 선언된 내부 가격 오버레이(load_world ·
      가격이 빈 멤버-날만 · 있는 값은 안 바꾼다 · 적용 요약과 sha256 을 기록에 싣는다 — PX_OVERLAY_ENV 머리말). 없으면 공개 판.
"""
from __future__ import annotations
import bisect, datetime as dt, hashlib, io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qbatch_core import mshift, months_between, SEED as QC_SEED   # noqa: E402  달 산수 · 씨앗은 한 벌(가벼운 모듈)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RDATA = os.environ.get("RBATCH_DATA") or DATA   # 배치 R 자료(지도 · 내부자 · 10-Q)가 있는 곳

# ── 등록 규칙의 수(카드 원문 · batch_design_changes 에서 옮김 — 여기서 바꾸지 않는다) ──────────────
M0, M1 = "2016-08", "2026-07"          # 신호월 t(보유월 t+1 = 2016-09 ~ 2026-08 · T = 120)
SENS_FROM = ("2014-07", "2020-07")     # 미리 등록한 민감도 창 시작(측정)
LAG = 3                                # NW(3)
JT_K = (0, 1, 2)                       # JT 3개월(CMP Figure 3 의 앞 절반 · 단계 보유 기간)
ALPHA = 0.025                          # 가족 α(한쪽) — Holm
Q_PRIOR, ALPHA1, T_P0, P0_GATE = 0.4, 0.0125, 2.27, 0.15
GAMMA_LIT = {"R1": -0.55, "R2": -0.80}   # CMP Table IX (2) · Lazy Prices A-15 동일가중 Q1 5요인(%/월)
FIN = "Financials"
EG_TOP = 40                            # 상호작용의 «Eg 상위 40 소속»
PX_BACK = 5                            # 과거 월말 가격이 비면 앞 5거래일 안의 마지막 값
H52_WIN, H52_MIN = 252, 200            # 52주 고점 창 · 최소 관측
COV_N, COV_CAP, T_MIN, IM_VIOL = 0.90, 0.95, 84, 0.02
CAP_CARRY = 12                         # 커버리지 시총 몫 — 가격이 빈 멤버는 마지막 시총을 12개월까지 잇는다
MIN_DOF = 10                           # 달 회귀의 최소 잔여 자유도
Q1_CUT, Q1_MIN_DOCS = 0.20, 50         # R2 하위 20% 경계(전년도 분포) · 경계를 세울 최소 문서 수
F0_FLAG = {"OS": (20, 5), "RS": (10, None), "CH": (30, None)}   # 월 종목 수 (중앙값 ≥ · 최소 ≥)
BASE_CTRL = ("size", "logbm", "r1", "mom")
EXTRA_R1 = ("h52", "r12")              # 관문 ii — 52주 고점 괴리 · 12개월 수익
MISS = {"size": "drop", "r1": "drop", "mom": "drop", "logbm": "dummy", "h52": "dummy", "r12": "dummy", "dlog": "dummy"}
N_PLACEBO, PLACEBO_Q = 200, 0.90
SEED = QC_SEED                         # 위약 씨앗 = 랩 공통 qbatch_core.SEED(default_rng(SEED + i)) — 형제 모듈과 같은 수
TOL = 1e-8                             # 종속 열 판정(잔차 크기 ÷ 원래 크기)
BOUND_FROM = "2015-01"                 # R2 경계 세계 시작 — 2016 공개분의 경계 = 2015 공개 짝
SPLIT_T2 = "2023-04"                   # R1 T2 전후 분할 보고(가용월 · r_r1_flags.SPLIT_T2 와 같은 수)
# 고배당 시총 핀 — 그 달 말 원 종가(분할만 되맞춤 · 배당조정 아님 · 달러). 시총 가격 ÷ 핀이 ±3% 밖이면 시총이 배당조정 종가에서 나온 것
HY_PIN = {("XOM", "2016-08"): 87.14, ("VZ", "2016-08"): 52.33, ("AAPL", "2016-08"): 106.10 / 4}
HY_TOL = 0.03

SPECS = {                              # 카드별 플래그 블록 — 첫 이름이 주 계수
    "R1":      {"card": "R1", "flags": ("OS", "RS"), "focal": "OS", "jt": JT_K},
    "R1_SALL": {"card": "R1", "flags": ("SALL",), "focal": "SALL", "jt": JT_K},          # 분류 없는 전체 매도(측정)
    "R1_T1":   {"card": "R1", "flags": ("OS_T1", "RS"), "focal": "OS_T1", "jt": JT_K},   # Officer · $10만 · 10b5-1 제외 · 3개월 룩백(RS 는 1차 — 정본이 T1 RS 를 싣지 않는다 · 선언)
    "R1_T1C":  {"card": "R1", "flags": ("OS_T1C", "RS"), "focal": "OS_T1C", "jt": JT_K}, # 선언된 민감도 — T1 과 같고 4/A 가 고친 금액(r_r1_flags 선언 q)
    "R1_T2":   {"card": "R1", "flags": ("OS_T2", "RS_T2"), "focal": "OS_T2", "jt": JT_K}, # 10b5-1 행 제외
    "R1_T4":   {"card": "R1", "flags": ("OS_T4", "RS_T4"), "focal": "OS_T4", "jt": JT_K}, # 분류 불가를 기회주의로
    "R1_T6":   {"card": "R1", "flags": ("OS_T6", "RS_T6"), "focal": "OS_T6", "jt": JT_K}, # 강제 매도를 빼지 않는다
    "R2":      {"card": "R2", "flags": ("CH", "CH_miss"), "focal": "CH", "jt": (0,)},
    "R3":      {"card": "R3", "flags": ("FL",), "focal": "FL", "jt": JT_K},
}


def _E():
    import eg30plus as E              # nw_t · World · EG_BASE · v0_targets — 처음 쓸 때 읽는다
    return E


# ══ 자료 어댑터 — 필드 이름은 여기 한 곳 ═══════════════════════════════════════════════════════
# 값은 «후보 이름 목록»이다. 레코드에서 앞의 것부터 찾는다. 빌더가 이름을 정하면 목록을 그 하나로 줄이면 된다.
FIELDS = {
    "issuer_map": {"file": "_issuer_map.json", "tm": "tm", "f0": ("f0", "by_month"), "f0_rate": 2,
                   "f0_viol": ("f0", "violations"),                 # [[티커, 달, 그룹, 주 CIK, n]] — 지도 F0 위반 멤버-월(표본 · 분모 밖)
                   # tm[티커] = [[첫 달, 끝 달, 그룹, 주 CIK, [CIK 집합], fpi, 출처, fpi_q]] (build/issuer_map.py tm_format)
                   # 🔒 fpi 칸은 박지 않는다 — 지도의 fpi_registered.tm_index(2026-09-25 권고 fpi_q = 7) · 없으면 사양 칸 5(옛 판)
                   "fpi_registered": "fpi_registered",
                   "row": {"first": 0, "last": 1, "grp": 2, "cik": 3, "ciks": 4, "fpi_spec": 5, "src": 6}},
    # 펀드 파일(data/fx · data/fx_pit — tech_backtest.load_fund 가 읽는 것)의 CIK 출처(커버리지 F0 · CIK 일치 · 2026-09-26 등록 전 결정).
    # 🔒 칸 이름: 최상위 "ciks" = [[CIK, 첫 관측 기간말, 끝 관측 기간말, 관측 수, 이름], …] — 선행 CIK 를 잇는 빌드(과제 B · build/refresh_facts.py
    #   _set_ck)가 모든 fx · fx_pit 파일에 싣는 «CIK 구간» 요약(날짜 'YYYY-MM-DD' · 양끝 포함). "cik_ranges"(같은 모양 · null = 열린 끝 ·
    #   [{"cik", "from", "to"}] 도 받는다)는 별칭. 관측 날짜를 덮는 구간의 CIK 들 가운데 하나라도 그달 §A0 CIK 집합에 있으면 일치.
    #   구간 칸이 없는 파일(빌드 전 옛 모양)이나 그 날짜를 덮는 구간이 없는 관측(마지막 SEC 관측 뒤 야후 메움 등)은 «출처 모름» →
    #   불일치로 본다(덮이지 않은 것으로 센다 · 오케스트레이터 지시 — 최상위 "cik" 하나로 넘겨짚지 않는다).
    "fund_cik": {"dirs": ("fx", "fx_pit"), "ranges": ("ciks", "cik_ranges"), "cik": "cik", "ticker": "t"},
    # 보유월 수익 y 가 월말 전에 끝나는 계열의 이름별 판정(2026-09-26 등록 전 결정 · 공개 지식) — build_panel 이 읽는다
    "ytrunc": {"file": "_r_ytrunc.json", "rows": "rows", "key": "key", "last": "last", "cls": "class",
               "classes": ("delisted", "kept_trading")},
    "ins": {"file": os.path.join("_ins_pit", "cikmonth.json"),     # §A (b) 그룹 × 가용월 집계(정본 r_r1_flags.cikmonth_doc)
            "root": ("groups", "cells", "gm", "data", "rows"),       # {그룹: {달: {…}}} · {"cols","rows"} · [{…}] 를 담은 최상위 키
            "months_ok": "months_ok",                                # 표지가 정의된 달(밖은 모름)
            "grp": ("_grp", "grp", "group", "g"), "month": ("_month", "m", "month", "ym"),
            # 정본은 0 인 칸을 뺀다(희소) — 레코드에 없으면 0 · 파일 전체에 한 번도 없으면 모양이 틀린 것이라 멈춘다
            "n_os": ("O", "os_n", "n_os"),          # 기회주의 매도 행 수(강제 매도 뺀 뒤)
            "n_rs": ("R", "rs_n", "n_rs"),          # 루틴
            "n_un": ("U", "un_n", "n_un"),          # 분류 불가
            "n_na": ("N", "na_n", "n_na"),          # 자료 부족(3년 이력이 아직 안 참) → OS · RS «모름»(r_r1_flags 선언 f)
            "n_s": ("all", "s_n", "n_s"),           # 재량 매도 전체(없으면 O + R + U + N)
            "n_ob": ("bO", "ob_n", "n_ob"), "n_rb": ("bR", "rb_n", "n_rb"),   # 분류된 매수(T3 표본 = 정본 MASK)
            "na_os": ("os_na",), "na_rs": ("rs_na",),                          # 정본이 단 1차 «모름»(1 = N 행)
            # 쌍둥이 — 표지 이름: (개수 칸 후보, 모름 칸 후보 | None, 칸이 파일에 없을 때 대신할 1차 식 | None).
            # t1_os3 은 이미 더미(1 · 0 · None). T2 · T6 은 정본이 판별 N 을 싣지 않아 1차 os_na · rs_na 로 가늠한다(선언).
            "twins": {"OS_T1": (("t1_os3",), None, None), "OS_T1C": (("t1c_os3",), None, None),
                      "OS_T2": (("t2_os_n",), ("os_na",), None), "RS_T2": (("t2_rs_n",), ("rs_na",), None),
                      "OS_T4": (("t4_os_n",), ("t4_os_na",), "O+U"), "RS_T4": (("t4_rs_n",), ("t4_rs_na",), "R"),
                      "OS_T6": (("t6_os_n",), ("os_na",), None), "RS_T6": (("t6_rs_n",), ("rs_na",), None)}},
    "px_raw": {"file": "_px_raw.json", "dates": "dates", "px": "px"},  # 시총용 원 종가(분할만 되맞춤) — 없으면 배당조정 pxd(선언)
    "r2_gm": {"ch": "ch", "miss": "miss", "dlog": "dlog_raw"},    # r_r2flags.ch_active 행(정본)
    "tenq": {"file": "_tenq_rf.json",                                 # §C 10-Q 문서별 특징
             "root": ("docs", "rows", "filings", "items"),
             "grp": ("grp", "group", "g"), "acc": ("acc", "accession", "accessionNumber"),
             "accepted_et": ("accepted_et", "acc_et", "avail_et"), "accepted_utc": ("accepted_utc", "acceptanceDateTime"),
             "shape": ("shape", "form_shape"), "prev_shape": ("prev_shape", "pair_shape"),
             "sim": ("SimRF", "sim_rf", "simrf"), "status": ("parse_status", "status"), "ok": ("ok",),
             "dlog": ("dlog_len_rf", "dlog_len", "dlog")},
}


def _pick(rec, names, what, required=True):
    for n in names:
        if n in rec:
            return rec[n]
    if required:
        raise SystemExit("🚨 %s 레코드에 %s 가 없다 — 있는 키 %s · r_stagem.FIELDS 를 고쳐라" % (what, list(names), sorted(rec)[:30]))
    return None


def _num(v):
    return 0.0 if v is None else float(v)


def _records(J, spec, what):
    """여러 모양을 레코드 목록 하나로 편다 — [{…}] · {"cols","rows"} · {root: {그룹: {달: {…}}}} · {root: [{…}]}."""
    def flat(X):
        if isinstance(X, list):
            return X
        if isinstance(X, dict) and "cols" in X and "rows" in X:
            return [dict(zip(X["cols"], r)) for r in X["rows"]]
        if isinstance(X, dict):
            out = []
            for g, mm in X.items():
                if not isinstance(mm, dict):
                    raise SystemExit("🚨 %s: %s 아래가 {달: {…}} 이 아니다" % (what, g))
                for m, rec in mm.items():
                    out.append(dict(rec, _grp=g, _month=m))
            return out
        raise SystemExit("🚨 %s 모양을 모른다(%s)" % (what, type(X).__name__))
    if isinstance(J, list) or (isinstance(J, dict) and "cols" in J and "rows" in J):
        return flat(J)
    for r in spec["root"]:
        if r in J:
            return flat(J[r])
    raise SystemExit("🚨 %s: 최상위 키 %s 가 없다 — 있는 키 %s · FIELDS 를 고쳐라" % (what, list(spec["root"]), sorted(J)[:20]))


def _load(spec, path, what):
    path = path or os.path.join(RDATA, spec["file"])
    if not os.path.exists(path):
        raise SystemExit("🚨 %s 자료 %s 가 없다 — RBATCH_DATA 로 자료가 있는 data 경로를 넘겨라" % (what, path))
    return json.load(io.open(path, encoding="utf-8"))


class IssuerMap:
    """§A0 날짜 인식 발행사 지도 — (티커, 달) → {grp, cik, ciks, fpi, fpi_spec, src}. 명단 티커는 '-', 지도는 '.' 표기라 둘 다 찾는다.
    fpi = 등록 표지(지도의 fpi_registered.tm_index 칸 — 2026-09-25 권고 fpi_q · r_r1_flags · ins_pit_build 와 같은 칸) · fpi_spec = 사양 칸.
    viol_mm = 지도 F0 위반 멤버-월 {(티커 '.' 표기, 달)}(표본 · 커버리지 분모 밖 — 2026-09-26 등록 전 결정)."""

    def __init__(self, path=None, J=None):
        F = FIELDS["issuer_map"]
        J = J if J is not None else _load(F, path, "발행사 지도")
        self.tm = J[F["tm"]]
        f0 = J
        for key in F["f0"]:
            f0 = (f0 or {}).get(key) or {}
        self.viol = {m: v[F["f0_rate"]] for m, v in f0.items()} if isinstance(f0, dict) else {}
        vl = J
        for key in F["f0_viol"]:
            vl = (vl or {}).get(key) if isinstance(vl, dict) else None
        self.viol_mm = {(str(v[0]).replace("-", "."), v[1]) for v in (vl or [])}
        reg = J.get(F["fpi_registered"]) or {}
        self.fpi_index = int(reg.get("tm_index", self.R_spec())) if reg else self.R_spec()
        self.fpi_field = reg.get("field") or "fpi"
        self.R = F["row"]
        self.pins = J.get("pins")
        self._c = {}

    @staticmethod
    def R_spec():
        return FIELDS["issuer_map"]["row"]["fpi_spec"]

    def at(self, t, m):
        ck = (t, m)
        if ck in self._c:
            return self._c[ck]
        R, out, fx = self.R, None, self.fpi_index
        for c in (t, t.replace("-", "."), t.replace(".", "-")):
            for r in self.tm.get(c) or ():
                if r[R["first"]] <= m <= r[R["last"]]:
                    out = {"grp": r[R["grp"]], "cik": r[R["cik"]], "ciks": r[R["ciks"]],
                           "fpi": r[fx] if len(r) > fx else r[R["fpi_spec"]], "fpi_spec": r[R["fpi_spec"]], "src": r[R["src"]]}
                    break
            if out:
                break
        self._c[ck] = out
        return out

    def violated(self, t, m):
        """지도 F0 위반 멤버-월인가(명단 '-' · 지도 '.' 표기 둘 다)."""
        return (t.replace("-", "."), m) in self.viol_mm

    def month_ok(self, m):
        """지도 F0 — 그달 위반율 ≤ 2% 면 True · 표에 없는 달은 None(쓰지 않는다)."""
        v = self.viol.get(m)
        return None if v is None else bool(v <= IM_VIOL)


class FlagPanel(dict):
    """{(그룹, 달): {표지: 값}} + months_ok(표지가 정의된 달 · None 이면 전부) + src. 표에 없는 칸은 0(그달 사건 없음) ·
    값이 None 인 칸과 months_ok 밖의 달은 «모름»(엔진이 0 + <표지>_unk 더미로 넣는다)."""

    def __init__(self, *a, months_ok=None, src=None, names=None, notes=None, **k):
        super().__init__(*a, **k)
        self.months_ok = set(months_ok) if months_ok is not None else None
        self.src = src
        self.names = set(names) if names is not None else None      # 파일에 한 번이라도 있던 표지(없으면 값에서 센다)
        self.notes = list(notes or [])


def _has(fp, name):
    """표지 name 이 표에 한 번이라도 있는가(카드 한 벌이 쌍둥이를 돌릴지 · 못 돌린 시도로 적을지 정한다)."""
    nm = getattr(fp, "names", None)
    if nm is not None:
        return name in nm
    return any(name in v for v in fp.values())


def ins_flags(path=None, J=None):
    """§A cikmonth(그룹 × 가용월 · 정본 r_r1_flags.cikmonth_doc) → FlagPanel {OS, RS, SALL[, CLS][, 쌍둥이], d:<그 밖 수치 칸>}.

    뜻은 r_r1_flags.Flags.dummy 와 같다 — OS = O > 0 → 1 · 아니고 (N > 0 또는 os_na) → None(모름) · 아니면 0 · RS 같은 방식(R · rs_na)
    · SALL(분류 없는 판) = all > 0 · CLS(T3 표본 = MASK) = O + R + bO + bR > 0(매수 칸이 파일에 한 번도 없으면 싣지 않는다).
    쌍둥이(FIELDS["ins"]["twins"]) — 개수 칸 > 0 → 1 · 아니고 모름 칸 > 0 → None · 아니면 0(t1_os3 은 더미 그대로 · null = 모름).
    쌍둥이 칸이 파일에 한 번도 없으면 싣지 않는다(카드 한 벌이 «못 돌린 시도»로 적는다) — 단 T4 는 옛 모양 대체식(O + U · R)을 쓰고
    notes 에 적는다(정본 머리말: 1차 O + U 는 보고자 [R, U] 공동 행을 놓친다). months_ok 밖의 달은 모름. 표에 없는 (그룹, 달)은 엔진이
    0 으로 읽는다(그달 거래 없음) — 표본 밖 그룹과 구별하는 일은 지도(unresolved 는 표본에서 뺀다)가 한다.
    """
    F = FIELDS["ins"]
    J = J if J is not None else _load(F, path, "내부자 PIT")
    mo = J.get(F["months_ok"]) if isinstance(J, dict) else None
    fp = FlagPanel(months_ok=mo, src=(J.get("variant") if isinstance(J, dict) else None) or "cikmonth")
    TW = F["twins"]
    core = set()
    for key in ("grp", "month", "n_os", "n_rs", "n_un", "n_na", "n_s", "n_ob", "n_rb", "na_os", "na_rs"):
        core.update(F[key])
    for cnt, na, _ in TW.values():
        core.update(cnt)
        core.update(na or ())
    recs = _records(J, F, "내부자 PIT")
    seen = {"n_os": 0, "n_rs": 0, "buy": 0}
    tw_seen = {nm: any(any(c in r for c in TW[nm][0]) for r in recs) for nm in TW}
    got = lambda r, key: _num(_pick(r, F[key], "내부자 PIT", required=False))

    def dum(n, unk):
        return 1.0 if n > 0 else (None if unk else 0.0)
    for r in recs:
        g, m = _pick(r, F["grp"], "내부자 PIT"), _pick(r, F["month"], "내부자 PIT")
        seen["n_os"] += any(n in r for n in F["n_os"])
        seen["n_rs"] += any(n in r for n in F["n_rs"])
        seen["buy"] += any(n in r for n in F["n_ob"] + F["n_rb"])
        o, rr, u, na = got(r, "n_os"), got(r, "n_rs"), got(r, "n_un"), got(r, "n_na")
        ns = _pick(r, F["n_s"], "내부자 PIT", required=False)
        ns = (o + rr + u + na) if ns is None else float(ns)
        uo, ur = na > 0 or got(r, "na_os") > 0, na > 0 or got(r, "na_rs") > 0
        rec = {"OS": dum(o, uo), "RS": dum(rr, ur), "SALL": float(ns > 0),
               "CLS": float(o + rr + got(r, "n_ob") + got(r, "n_rb") > 0)}
        for nm, (cnt, nak, alt) in TW.items():
            if tw_seen[nm]:
                c = next((x for x in cnt if x in r), None)
                if nak is None:                                  # 이미 더미(t1_os3) — null 은 모름 · 칸 없음은 0
                    rec[nm] = (None if r[c] is None else float(r[c])) if c else 0.0
                else:
                    unk = any(_num(r.get(x)) > 0 for x in nak)
                    rec[nm] = dum(_num(r.get(c)) if c else 0.0, unk)
            elif alt == "O+U":
                rec[nm] = dum(o + u, uo)
            elif alt == "R":
                rec[nm] = rec["RS"]
        for key, v in r.items():                  # 밀도 칸 — 빌더가 더한 그 밖 수치 칸은 «> 0» 더미로 넘긴다
            if key not in core and isinstance(v, (int, float)) and not isinstance(v, bool):
                rec["d:" + key] = float(v > 0)
        if (str(g), m) in fp:
            raise SystemExit("🚨 내부자 PIT 에 (%s, %s) 가 두 번 있다" % (g, m))
        fp[(str(g), m)] = rec
    if fp and (not seen["n_os"] or not seen["n_rs"]):
        raise SystemExit("🚨 내부자 PIT 에 기회주의(%s)·루틴(%s) 칸이 한 번도 없다 — 모양이 다르다 · FIELDS 를 고쳐라" % (F["n_os"], F["n_rs"]))
    if not seen["buy"]:
        for rec in fp.values():
            rec.pop("CLS", None)
    if not tw_seen["OS_T4"]:
        fp.notes.append("T4 = 옛 모양 대체식(O + U · R) — 정본 t4_os_n · t4_rs_n 칸이 없다")
    missing = [nm for nm in TW if not tw_seen[nm] and TW[nm][2] is None]
    if missing:
        fp.notes.append("쌍둥이 칸 없음 %s — 그 쌍둥이는 못 돌린 시도로 적힌다" % missing)
    fp.names = {k for rec in fp.values() for k in rec}
    return fp


def _sha(path):
    """파일 sha256(없으면 None) — 등록 기록에 쓴 판을 핀으로 남긴다."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, TypeError):
        return None


def _canon_mod(name):
    """정본 모듈 import — ImportError 만 잡는다(정본 안의 다른 오류는 그대로 올라간다). 못 부르면 멈춘다 —
    RBATCH_PROVISIONAL=1 이고 등록 러너(RBATCH_COMMIT · RBATCH_P0)가 아닐 때만 None(부르는 쪽이 잠정판을 고르고 src 에 적는다)."""
    try:
        return __import__(name)
    except ImportError as e:
        if os.environ.get("RBATCH_COMMIT") or os.environ.get("RBATCH_P0") or os.environ.get("RBATCH_PROVISIONAL") != "1":
            raise SystemExit("🚨 정본 %s 를 import 할 수 없다(%s) — 잠정판으로 조용히 내려가지 않는다. %s.py 를 이 파일 옆에 두거나"
                             "(snap_wt 로 복사) 시험에서만 RBATCH_PROVISIONAL=1 을 준다(RBATCH_COMMIT · RBATCH_P0 와 함께는 안 된다)."
                             % (name, e, name))
        return None


def bounds_gap(B, window=(M0, M1)):
    """경계가 없는 공개연도 목록 — 신호월 창 [M0, M1] 의 CH 창(t−2..t)이 닿는 공개연도 모두에 경계가 서야 한다.
    B = r_r2flags.boundaries({연도: {cut, n}}) 또는 잠정판 thr({연도: 값}) · 키는 정수든 문자열이든."""
    ys = range(int(mshift(window[0], -2)[:4]), int(window[1][:4]) + 1)
    out = []
    for y in ys:
        v = B.get(y, B.get(str(y)))
        cut = v.get("cut") if isinstance(v, dict) else v
        if cut is None:
            out.append(y)
    return out


def r2_flags(R, sha=None):
    """R2 정본(r_r2flags.r2_build 결과) → FlagPanel {CH, CH_miss, dlog}. 창에 10-Q 가 없는 (그룹, 달)은 표에 없다 → 엔진이 0 으로 읽는다
    (정본 GM_EMPTY 와 같다 · dlog 는 없음 → 결측 더미)."""
    F = FIELDS["r2_gm"]
    fp = FlagPanel(src="r_r2flags:%s%s" % (R.get("metric"), ("@" + sha[:12]) if sha else ""))
    for (g, t), row in R["gm"].items():
        fp[(str(g), t)] = {"CH": float(row[F["ch"]]), "CH_miss": float(row[F["miss"]]), "dlog": row.get(F["dlog"])}
    fp.names = {"CH", "CH_miss", "dlog"} if fp else set()
    return fp


def tenq_canonical(path=None, world=None, im_path=None, metric="rf", exclude=None, window=(M0, M1)):
    """R2 정본 — build/r_r2flags.py 의 load_tenq → r2_build 를 그대로 부른다(짝 · 형태 전환 · 조기폐장 마감 · 전년도 경계 · t−2..t 창).
    metric = 'rf'(1차) · 'doc'(SimDoc 대조) · exclude = None · 'ixbrl' · 'covid'(진단 — 정본 excl_ixbrl · excl_covid).
    world = boundary_world 의 {(그룹, 달)}(경계 분포의 세계 — 패널 행이 아니다). 창 안 공개연도에 경계가 없으면 멈춘다.
    돌려주는 것 (FlagPanel, R). 정본을 못 부르면 _canon_mod 가 멈춘다(RBATCH_PROVISIONAL=1 일 때만 None — 잠정판)."""
    R2 = _canon_mod("r_r2flags")
    if R2 is None:
        return None
    path = path or os.path.join(RDATA, FIELDS["tenq"]["file"])
    if not os.path.exists(path):
        raise SystemExit("🚨 10-Q 위험요인 자료 %s 가 없다" % path)
    imp = im_path or os.path.join(RDATA, FIELDS["issuer_map"]["file"])
    im = R2.IssuerMap.load(imp) if os.path.exists(imp) else None
    ex = getattr(R2, "excl_" + exclude) if exclude else None
    R = R2.r2_build(R2.load_tenq(path), R2.Cal(), gof=(im.group_of if im else None), world=world, metric=metric, exclude=ex)
    gap = bounds_gap(R["bounds"], window)
    if gap:
        raise SystemExit("🚨 R2 경계가 없는 공개연도 %s(metric %s) — 경계 세계가 %s 부터의 멤버-월을 담는지(boundary_world) 보라"
                         % (gap, metric, BOUND_FROM))
    fp = r2_flags(R, _sha(getattr(R2, "__file__", None)))
    if exclude:
        fp.src += ":excl_" + exclude
    return fp, R


def r2_variants(path=None, world=None, im_path=None, window=(M0, M1)):
    """R2 카드 한 벌의 표지 판 넷 — {'rf': 1차, 'doc': SimDoc 대조, 'ixbrl': iXBRL 전환 짝 제외, 'covid': 2020-03~08 공개분 제외}
    (값은 FlagPanel). stage_m_r2 에 그대로 넘긴다(fp=rf · fp_doc=doc · fp_ixbrl=ixbrl · fp_covid=covid). 정본을 못 부르면 None."""
    out = {}
    for key, kw in (("rf", {}), ("doc", {"metric": "doc"}), ("ixbrl", {"exclude": "ixbrl"}), ("covid", {"exclude": "covid"})):
        got = tenq_canonical(path, world, im_path, window=window, **kw)
        if got is None:
            return None
        out[key] = got[0]
    return out


def utc_to_et(s):
    """UTC 'YYYY-MM-DDTHH:MM[:SS][Z]' → ET 'YYYY-MM-DD HH:MM:SS'(미국 서머타임 2007 규칙 · 3월 둘째 일요일 2시 ~ 11월 첫째 일요일 2시)."""
    u = dt.datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19]) if len(s) >= 19 and s[17:19].isdigit() else 0)

    def nth_sunday(y, mo, nth):
        d = dt.datetime(y, mo, 1)
        d += dt.timedelta(days=(6 - d.weekday()) % 7)
        return d + dt.timedelta(days=7 * (nth - 1))
    y = u.year
    start = nth_sunday(y, 3, 2) + dt.timedelta(hours=2 + 5)    # 현지 2:00 EST = 7:00 UTC
    end = nth_sunday(y, 11, 1) + dt.timedelta(hours=2 + 4)     # 현지 2:00 EDT = 6:00 UTC
    off = 4 if start <= u < end else 5
    return (u - dt.timedelta(hours=off)).strftime("%Y-%m-%d %H:%M:%S")


def avail_day(s_et, days):
    """접수 시각(ET · 'YYYY-MM-DD[T ]HH:MM[:SS]') → 가용 거래일. 16:00 이후 접수면 다음 거래일 · 거래일이 아니면 다음 거래일.
    16:00:00 정각은 «이후»로 본다(보수적). days = 오름차순 거래일 문자열(세계 격자). 격자 밖이면 None."""
    d, hm = s_et[:10], (s_et[11:16] if len(s_et) >= 16 else "00:00")
    j = bisect.bisect_right(days, d) if hm >= "16:00" else bisect.bisect_left(days, d)
    return days[j] if j < len(days) else None


def _switch(a, b):
    """형태 전환 — 한쪽이 F(전문)이고 다른 쪽이 B·U(상용구)면 True(R2 (5)). 형태를 모르면 빌더의 parse_status 를 믿는다."""
    if a not in ("B", "U", "F") or b not in ("B", "U", "F"):
        return False
    return (a == "F") != (b == "F")


def tenq_flags(days, path=None, J=None, world=None, window=None):
    """R2 잠정판(정본 r_r2flags 를 부를 수 없을 때 · 시험용) — §C 10-Q 문서 특징(짝의 SimRF 가 문서에 이미 붙은 모양) → (FlagPanel, 기록).
    🚨 등록에 얼릴 판은 정본(tenq_canonical)이다. 정본에만 있는 것: 짝 짓기(70~200일) · 조기폐장 13:00 마감 · 같은 분기 중복 · 늦은 짝.

    가용 = 접수 시각 ET(16:00 규칙) · 공개월 = 가용일의 달(R2 (2)) · 유효 = 파싱 ok · SimRF 있음 · 형태 전환 아님.
    Q1 = SimRF < 직전 달력연도에 공개된 유효 짝 전체의 20% 분위(np.quantile 선형 보간 · R2 (7)) — 전년도 문서가 Q1_MIN_DOCS 보다
    적으면 경계가 없어 그해 문서는 결측으로 둔다(선언).
    CH_active(g, t) = 공개월 t−2..t 의 10-Q 가운데 Q1 이 하나라도 있으면 1(R2 (8) · A-15 «다음 달 진입 · 3개월 보유»).
    CH_miss = CH 가 0 이고 창 안에 무효 문서가 있으면 1(분리 실패 · 짝 없음 · 형태 전환 → CH = 0 + 결측 더미).
    창 안에 10-Q 가 없으면 CH = 0 · CH_miss = 0(새 사건 없음 — 3월 편입에 교체가 적은 이유) · dlog = 창 안 마지막 유효 문서의 Δlog(1A 단어수).
    world = {(그룹, 공개월)} 을 주면 경계 분포를 그 세계(boundary_world — 표본 규칙의 멤버-월 · 2015-01 부터)의 짝으로만 잰다
    («세계 전체 짝» · 표지는 전부 만든다). window = (M0, M1) 을 주면 그 창의 공개연도에 경계가 없을 때 멈춘다(bounds_gap).
    """
    F = FIELDS["tenq"]
    J = J if J is not None else _load(F, path, "10-Q 위험요인")
    docs, rec = [], {"n": 0, "beyond_grid": 0, "invalid": 0, "no_thr": 0}
    for r in _records(J, F, "10-Q 위험요인"):
        rec["n"] += 1
        g = _pick(r, F["grp"], "10-Q 위험요인")
        s = _pick(r, F["accepted_et"], "10-Q 위험요인", required=False)
        if s is None:
            s = utc_to_et(_pick(r, F["accepted_utc"], "10-Q 위험요인"))
        day = avail_day(str(s), days)
        if day is None:
            rec["beyond_grid"] += 1
            continue
        st = _pick(r, F["status"], "10-Q 위험요인", required=False)
        sim = _pick(r, F["sim"], "10-Q 위험요인", required=False)
        valid = (st is None or st in F["ok"]) and sim is not None and not _switch(
            _pick(r, F["shape"], "10-Q 위험요인", required=False), _pick(r, F["prev_shape"], "10-Q 위험요인", required=False))
        dl = _pick(r, F["dlog"], "10-Q 위험요인", required=False)
        docs.append((g, day, valid, None if sim is None else float(sim), None if dl is None else float(dl)))
        rec["invalid"] += int(not valid)
    by_year = {}
    for g, day, valid, sim, _ in docs:
        if valid and (world is None or (g, day[:7]) in world):
            by_year.setdefault(int(day[:4]), []).append(sim)
    thr = {y + 1: float(np.quantile(np.array(v), Q1_CUT)) for y, v in by_year.items() if len(v) >= Q1_MIN_DOCS}
    if window is not None and bounds_gap(thr, window):
        raise SystemExit("🚨 잠정 10-Q 경계가 없는 공개연도 %s — 경계 세계를 %s 부터 넘겨라" % (bounds_gap(thr, window), BOUND_FROM))
    cell = {}                               # (그룹, 달) → [CH 있음, 무효 있음, (가용일, dlog)]
    for g, day, valid, sim, dl in sorted(docs, key=lambda x: (x[0], x[1])):
        y = int(day[:4])
        if valid and y not in thr:
            valid = False
            rec["no_thr"] += 1
        q1 = valid and sim < thr[y]
        for j in range(3):
            c = cell.setdefault((g, mshift(day[:7], j)), [False, False, None])
            c[0] |= q1
            c[1] |= not valid
            if valid and dl is not None:
                c[2] = (day, dl)
    fp = FlagPanel({k: {"CH": float(c[0]), "CH_miss": float((not c[0]) and c[1]), "dlog": (c[2][1] if c[2] else None)}
                    for k, c in cell.items()}, src="r_stagem.tenq_flags(잠정 · 등록에 쓰지 않는다)")
    rec["thr"] = {str(y): v for y, v in sorted(thr.items())}
    return fp, rec


def flags_from_pairs(pairs, name="FL", months_ok=None):
    """R3 등 — [(그룹, 달)] 목록 → FlagPanel {name: 1}(§D ev_flags 가 그룹-월 목록을 주면 이것으로 넘긴다)."""
    return FlagPanel({(g, m): {name: 1.0} for g, m in pairs}, months_ok=months_ok, src="pairs")


# ══ 내부 가격 오버레이 — 선언된 입력(2026-09-26 · 환경변수 하나 · 없으면 공개 판) ═══════════════════════════════
#  RBATCH_PX_OVERLAY = pit_px 모양 스테이징 파일(format pit_px_stage/1 · {dates, px: {키: {i0, p}}, keys[키].tickers, stops, stage_m})의 경로.
#  🔒 저장소 밖 파일만 받는다(저장소 안이면 멈춘다) — 공개 저장소에 둘 수 없는 내부 종가를 담기 때문이다. 공개 판 = 이 변수 없이 돈 것.
#  뜻 — 세계 가격(pit_panel.load_world 의 PX = stocks.json sd + data/pit_px.json)의 **가격이 빈 멤버-날만** 채운다:
#    ① 그 키의 그날 값이 비었고 ② 그 키의 명단 티커(keys[키].tickers · 없으면 키) 가운데 그날이 멤버 창(월말 명단의 멤버 달 + 다음 달) 안인
#    것이 있고 ③ 그 티커가 pit_panel._key 로 그날 **다른 키** 의 값을 읽지 않을 때만(pit_px_db2 --merge-stage 와 같은 빈 칸 규칙).
#    있는 값은 한 칸도 바꾸지 않는다(같은 날 값이 다르면 수만 센다) · 오늘 유니버스 키(sd) · 격리 이름(pit_quarantine)은 채우지 않는다 ·
#    격자가 다르면 멈춘다. 판정은 모두 파일을 읽은 세계(오버레이 전) 위에서 하고, 채우기는 그 뒤 한 번에 한다(차례에 기대지 않는다).
#  보유월 규칙 — 채운 키의 stops({d, y})는 pit_px closed[키].stops 에 같은 날 판정이 없을 때만 더하고(by = "overlay"),
#    stage_m.ytrunc_proposals([{key, last, class}])는 data/_r_ytrunc.json 에 같은 (키, 날)이 없을 때만 load_ytrunc 가 더한다.
#  기록 — 적용 요약(sha256 · 바이트 · 채운 값 수 · 건너뛴 사유별 수 · 더한 판정 수 — 파일 경로 · 이름 · 값은 싣지 않는다)을
#    Wd.px_overlay · build_panel 의 P["f0_rules"]["px_overlay"] · provenance()["px_overlay"] 에 싣는다 → --construct · r_cov · r_run
#    (f0 · 굽기 기록의 coverage.rules)이 그 sha256 을 남긴다. 오버레이가 없으면 그 칸은 None 이다.
PX_OVERLAY_ENV = "RBATCH_PX_OVERLAY"
PX_OVERLAY_FORMAT = "pit_px_stage/1"
_OV_CACHE = {}


def px_overlay_path():
    """RBATCH_PX_OVERLAY 의 절대 경로 | None(공개 판). 파일이 없거나 저장소 안이면 멈춘다."""
    p = (os.environ.get(PX_OVERLAY_ENV) or "").strip()
    if not p:
        return None
    p = os.path.abspath(p)
    if not os.path.isfile(p):
        raise SystemExit("🚨 %s 가 가리키는 파일이 없다" % PX_OVERLAY_ENV)
    try:
        inside = os.path.commonpath([p.lower(), ROOT.lower()]) == ROOT.lower()
    except ValueError:                                     # 다른 드라이브 — 저장소 밖
        inside = False
    if inside:
        raise SystemExit("🚨 %s 가 저장소 안 파일이다 — 내부 가격 오버레이는 저장소 밖에만 둔다" % PX_OVERLAY_ENV)
    return p


def _overlay_doc(path):
    """(문서, sha256, 바이트) — 같은 파일은 한 번만 읽는다."""
    st = os.stat(path)
    ck = (path, st.st_size, st.st_mtime_ns)
    if ck not in _OV_CACHE:
        _OV_CACHE.clear()
        J = json.load(io.open(path, encoding="utf-8"))
        if J.get("format") != PX_OVERLAY_FORMAT:
            raise SystemExit("🚨 가격 오버레이 형식 %r — %s 만 받는다" % (J.get("format"), PX_OVERLAY_FORMAT))
        _OV_CACHE[ck] = (J, _sha(path), st.st_size)
    return _OV_CACHE[ck]


def _overlay_ytrunc(J):
    """오버레이 파일의 y 규칙 제안 {(키, 마지막 값 날짜): 판정}(stage_m.ytrunc_proposals)."""
    F = FIELDS["ytrunc"]
    out = {}
    for r in ((J.get("stage_m") or {}).get("ytrunc_proposals") or []):
        c = r.get("class")
        if c not in F["classes"]:
            raise SystemExit("🚨 가격 오버레이의 y 규칙 제안 %s %s 판정 %r 는 %s 가운데 하나여야 한다" % (r.get("key"), r.get("last"), c,
                                                                                  F["classes"]))
        out[(r["key"], r["last"])] = c
    return out


def apply_px_overlay(Wd, path):
    """가격 오버레이를 세계 Wd 에 얹는다(머리말 규칙 · 제자리) → 적용 요약(경로 · 값 없이)."""
    import pit_panel as PP
    import pit_quarantine as PQ
    J, sha, nbytes = _overlay_doc(path)
    W, dates = Wd.W, Wd.dates
    D = len(dates)
    if list(J.get("dates") or []) != list(dates):
        raise SystemExit("🚨 가격 오버레이 격자가 세계 pxd_dates 와 다르다 — 같은 판에서 다시 만들 것")
    Q, today = set(PQ.names()), set(W["today"])
    mon, days_of, wcache = {}, {}, {}
    for ix in ("spx", "ndx"):
        for m, ts in W["lists"][ix].items():
            for t in ts:
                mon.setdefault(t, set()).add(m)
    for i, d in enumerate(dates):
        days_of.setdefault(d[:7], []).append(i)

    def win(t):
        if t not in wcache:
            s = set()
            for m in mon.get(t, ()):
                for mm in (m, mshift(m, 1)):
                    s.update(days_of.get(mm, ()))
            wcache[t] = s
        return wcache[t]

    cnt, fills, meta = {}, {}, (J.get("keys") or {})
    bump = lambda n, v=1: cnt.__setitem__(n, cnt.get(n, 0) + v)
    for k in sorted(J.get("px") or {}):
        o = J["px"][k]
        i0 = int(o.get("i0") or 0)
        vals = [(i0 + j, float(v)) for j, v in enumerate(o.get("p") or []) if v is not None and 0 <= i0 + j < D]
        if k in today:
            bump("today_key", len(vals))
            continue
        if k in Q:
            bump("quarantined_key", len(vals))
            continue
        tks = list((meta.get(k) or {}).get("tickers") or [k])
        b = W["PX"].get(k)
        for i, v in vals:
            if not (v > 0):
                bump("nonpositive")
                continue
            if b is not None and b[i] == b[i]:
                bump("kept_existing")
                if abs(v / b[i] - 1) > 1e-9:
                    bump("kept_existing_value_differs")
                continue
            inw = [t for t in tks if i in win(t)]
            if not inw:
                bump("outside_member_window")
                continue
            other = False
            for t in inw:
                c = PP._key(W, t, i)
                if c is not None and c != k:
                    x = W["PX"][c][i]
                    if x == x and x > 0:
                        other = True
                        break
            if other:
                bump("priced_under_other_key")
                continue
            fills.setdefault(k, []).append((i, v))
    new_keys = 0
    for k, lst in fills.items():
        if k not in W["PX"]:
            W["PX"][k] = np.full(D, np.nan)
            new_keys += 1
        a = W["PX"][k]
        for i, v in lst:
            a[i] = v
    stops = W.setdefault("stops", {})
    st_add = st_keep = 0
    for k in sorted(fills):
        for s in ((J.get("stops") or {}).get(k) or []):
            if s.get("y") not in ("missing", "last_price", "short_cut"):
                continue
            have = stops.setdefault(k, {})
            if s["d"] in have:
                st_keep += 1
                continue
            have[s["d"]] = {"d": s["d"], "y": s["y"], "why": s.get("why") or "", "uncertain": bool(s.get("uncertain")), "by": "overlay"}
            st_add += 1
    return {"env": PX_OVERLAY_ENV, "sha256": sha, "bytes": nbytes, "format": J.get("format"), "visibility": J.get("visibility"),
            "made": J.get("made"), "keys_in_file": len(J.get("px") or {}), "keys_filled": len(fills), "keys_new": new_keys,
            "values_filled": sum(len(v) for v in fills.values()), "skipped": dict(sorted(cnt.items())),
            "stops_added": st_add, "stops_kept_existing": st_keep, "ytrunc_proposals": len(_overlay_ytrunc(J)),
            "rule": "price-missing member-days only · never overwrites · no today/quarantined keys · no other-key reads"}


# ══ 통제 패널 — PIT 세계(snap_wt)에서 ═════════════════════════════════════════════════════════
def load_world():
    """eg30plus.World — pit_panel 세계 + 시점정확 GICS + Eg(pitgics) + SPY TR. 자료 판 작업 사본에서만 선다.
    RBATCH_PX_OVERLAY 가 있으면 내부 가격 오버레이를 얹는다(위 머리말 · 적용 요약 = Wd.px_overlay · 없으면 None = 공개 판)."""
    Wd = _E().World()
    p = px_overlay_path()
    Wd.px_overlay = apply_px_overlay(Wd, p) if p else None
    return Wd


def _px_at(p, i, back=PX_BACK):
    for j in range(i, max(-1, i - back - 1), -1):
        v = p[j]
        if v == v and v > 0:
            return float(v)
    return None


def _members(Wd, m, i):
    """그달 명단 — 가격 키가 선 것(pit_panel.union_members 그대로)과 선 게 없는 것(커버리지 분모용 · 이중클래스 둘째 제외)."""
    import pit_panel as PP
    W = Wd.W
    pairs, _ = PP.union_members(W, m, i)
    mem = set(W["lists"]["spx"].get(m) or []) | set(W["lists"]["ndx"].get(m) or [])
    priced = {t for t, _ in pairs}
    cik = lambda t: PP._dedup_cik(W, t, i)           # union_members 와 같은 한 종 줄이기 CIK(날짜 인식 · 2026-09-26)
    seen = {cik(t) for t in priced} - {None}
    nokey = []
    for t in sorted(mem - priced):
        if t in W["reassigned"] and m >= W["reassigned"][t].get("last", "9999"):
            continue
        c = cik(t)
        if c and c in seen:
            continue
        if c:
            seen.add(c)
        nokey.append(t)
    return pairs, nokey


def _raw_px(Wd, path=None):
    """시총용 원 종가(분할만 되맞춤 · 배당조정 아님) {키: 배열} — FIELDS["px_raw"] 파일이 없으면 None(→ 배당조정 pxd · 선언).
    격자가 세계(stocks.json pxd_dates)와 다르면 멈춘다."""
    F = FIELDS["px_raw"]
    path = path or os.path.join(RDATA, F["file"])
    if not os.path.exists(path):
        return None
    J = json.load(io.open(path, encoding="utf-8"))
    if list(J.get(F["dates"]) or []) != list(Wd.dates):
        raise SystemExit("🚨 %s 의 격자가 세계 pxd_dates 와 다르다" % path)
    out, n = {}, len(Wd.dates)
    for t, obj in (J.get(F["px"]) or {}).items():
        a = np.full(n, np.nan)
        i0 = int(obj.get("i0") or 0)
        for j, v in enumerate(obj.get("p") or []):
            if v is not None and 0 <= i0 + j < n:
                a[i0 + j] = float(v)
        out[t] = a
    return out


# ══ 커버리지 F0 성분(2026-09-26 등록 전 결정) — 신선도 · CIK 일치 · 시총 대체 · 이름별 y 규칙 ═══════════════════════
FRESH_DAYS = 550        # 주식수 · 장부가 관측의 최대 나이(일) = tech_backtest.TTM_STALE_DAYS(랩의 값 · 여기서 바꾸지 않는다 · 시험이 대조)
Y_END_LOOK = 5          # 보유월 끝 뒤 이 거래일 안에 값이 다시 서면 «끊김(gap)» · 아니면 «계열 끝(end)»


class FundCik:
    """펀드 파일(tech_backtest.load_fund 가 읽는 data/fx · data/fx_pit — 같은 순서 · 같은 키 · 뒤 파일이 이긴다)의 CIK 출처.
    cik_of(키, 관측 기간말) → 그 날짜를 덮는 CIK 구간들의 CIK 집합(FIELDS["fund_cik"] 머리말 · 구간 칸이 없거나 덮는 구간이 없으면 None =
    출처 모름)."""

    def __init__(self, root=DATA, files=None):
        F = FIELDS["fund_cik"]
        self.ent, self.stat = {}, {"files": 0, "with_ranges": 0, "no_cik": 0}
        paths = files
        if paths is None:
            paths = []
            for d in F["dirs"]:
                dd = os.path.join(root, d)
                if os.path.isdir(dd):
                    paths += [os.path.join(dd, f) for f in sorted(os.listdir(dd)) if f.endswith(".json")]
        for p in paths:
            try:
                j = json.load(io.open(p, encoding="utf-8")) if isinstance(p, str) else p
            except Exception:
                continue
            key = j.get(F["ticker"]) or (os.path.basename(p)[:-5] if isinstance(p, str) else None)
            rng = None
            for nm in F["ranges"]:
                if j.get(nm):
                    rng = []
                    for x in j[nm]:
                        if isinstance(x, dict):
                            rng.append((int(x["cik"]), x.get("from"), x.get("to")))
                        else:
                            rng.append((int(x[0]), x[1] if len(x) > 1 else None, x[2] if len(x) > 2 else None))
                    break
            c = j.get(F["cik"])
            self.ent[key] = {"cik": int(c) if c not in (None, "") else None, "ranges": rng,
                             "path": os.path.relpath(p, ROOT).replace(os.sep, "/") if isinstance(p, str) else None}
            self.stat["files"] += 1
            self.stat["with_ranges"] += int(rng is not None)
            self.stat["no_ranges"] = self.stat.get("no_ranges", 0) + int(rng is None)
            self.stat["multi_cik"] = self.stat.get("multi_cik", 0) + int(bool(rng) and len({x[0] for x in rng}) > 1)
            self.stat["no_cik"] += int(rng is None and self.ent[key]["cik"] is None)

    def cik_of(self, key, obs_date):
        e = self.ent.get(key)
        if e is None or e["ranges"] is None:
            return None
        cs = {c for c, a, b in e["ranges"] if (a is None or a <= obs_date) and (b is None or obs_date <= b)}
        return cs or None


def _age_days(d, obs):
    return (dt.date.fromisoformat(d) - dt.date.fromisoformat(obs)).days


_YF_FIRST, _YF_BF = {}, {}                  # 펀드 키 → (앞 채움 날짜, 야후 첫 관측일) | None · (키, 계열) → 판정


def yf_backfill_date(c, sh):
    """펀드 키 c 의 주식수 계열 sh 에 tech_backtest.merge_shares_yf 가 둔 «야후 앞 채움» 관측의 날짜 | None.

    2026-09-26(3차 검토 지적 · 등록 전) — merge_shares_yf 는 SEC 계열이 야후 첫 관측 y0 뒤에 시작하거나 없으면 y0 − SHYF_BACK_DAYS(630)
    날짜에 y0 의 값(× 그 사이 분할)을 하나 더 둔다. 그 값은 y0 에야 알려졌다 — 날짜만 과거라 90일 지연 컷을 통과해 버린다(BKR 파일:
    2019-10-24 첫 관측이 2018-02-01 로 앞 채워져 BHGE 2018-05..2019-09 의 F0 주식수 · 행 시총에 쓰였다 = 그때는 알 수 없던 값).
    시점정확 읽기(_fund_obs 'sh')는 그 관측을 원 관측일 y0 에 본다 — 같은 값의 y0 관측이 계열에 이미 있으므로 앞 채움 줄을 빼는 것과 같다.
    판정(좁게): 계열의 가장 이른 관측 날짜 = y0 − SHYF_BACK_DAYS 이고 그다음 관측 날짜 = y0(앞 채움은 SEC 계열 시작 전에만 둔다 —
    둘 사이에 관측이 있으면 SEC 관측이다). y0 = tech_backtest.shares_yf(c) 의 가장 이른 날짜(_despike 는 끝 관측을 빼지 않는다).
    게시 엔진(tech_backtest · pit_panel._shares · EG30 순위)은 그대로다 — 배치 R 의 F0 · 행 시총만 이 규칙을 쓴다(r_cov 는 따로 짠다)."""
    if not sh or len(sh) < 2:
        return None
    if c not in _YF_FIRST:
        import tech_backtest as TB
        yr = TB.shares_yf(c)
        _YF_FIRST[c] = (TB._shift(min(x for x, _ in yr), TB.SHYF_BACK_DAYS), min(x for x, _ in yr)) if yr else None
    bf = _YF_FIRST[c]
    if bf is None:
        return None
    mk = (c, id(sh), len(sh), sh[0][0], sh[-1][0])
    if mk not in _YF_BF:
        ds = sorted(x for x, _ in sh)
        _YF_BF[mk] = bf[0] if (ds[0] == bf[0] and ds[1] == bf[1]) else None
    return _YF_BF[mk]


def _fund_obs(Wd, t, k, d, field):
    """(관측 기간말, 값, 쓴 펀드 키) — field = 'sh'(pit_panel._shares 와 같은 차례: 가격 키 → 명단 티커 · sh 가 있는 첫 파일) ·
    'eq'(eg30plus.World.fund 와 같은 차례: 가격 키 → 명단 티커 · 있는 첫 파일). 90일 공시 지연(tech_backtest.asof_all).
    'sh' 는 야후 앞 채움 관측을 원 관측일에 본다(yf_backfill_date · 2026-09-26 — 그 줄을 빼고 고른다)."""
    import tech_backtest as TB
    FUND = Wd.W["FUND"]
    if field == "sh":
        for c in (k, t):
            f = FUND.get(c) or {}
            sh = f.get("sh")
            if sh:
                obs = TB.asof_all(sh, d)
                bd = yf_backfill_date(c, sh) if obs else None
                if bd is not None:
                    obs = [o for o in obs if o[0] != bd]
                if obs and obs[0][1]:
                    return obs[0][0], float(obs[0][1]), c
        return None
    c = k if FUND.get(k) else (t if FUND.get(t) else None)
    if c is None:
        return None
    obs = TB.asof_all((FUND[c] or {}).get(field), d)
    return (obs[0][0], obs[0][1], c) if (obs and obs[0][1] is not None) else None


def fresh_consistent(Wd, FC, t, k, d, field, ciks):
    """커버리지 F0 성분 — (값 | None, 사유). 사유: ok · none(관측 없음) · stale(> FRESH_DAYS) · cik(펀드 파일의 그 관측 CIK 가 그달 §A0
    CIK 집합에 없음 · 출처 모름 포함). 값은 ok 일 때만(주식수는 양수 · 장부가는 ≤ 0 도 «있음» — B/M 결측 더미가 받는다)."""
    ob = _fund_obs(Wd, t, k, d, field)
    if ob is None:
        return None, "none"
    od, v, key = ob
    if _age_days(d, od) > FRESH_DAYS:
        return None, "stale"
    cs = FC.cik_of(key, od)
    if not cs or not ciks or not ({int(x) for x in cs} & {int(x) for x in ciks}):
        return None, "cik"
    if field == "sh" and not (v > 0):
        return None, "none"
    return v, "ok"


def mcap_f0(Wd, RAW, FC, t, k, i, ciks):
    """커버리지 F0 시총(백만 $) = 시총 가격 × 신선 · CIK 일치 주식수 → (시총 | None, 시총 가격 판, 주식수 사유)."""
    p, basis = _cap_px(Wd, RAW, k, i)
    if not p:
        return None, None, "noprice"
    sh, why = fresh_consistent(Wd, FC, t, k, Wd.dates[i], "sh", ciks)
    return ((p * sh) if sh else None), basis, why


class SectorAt:
    """그달 섹터 — build/issuer_map.py sector_src_at 과 같은 규칙(그 파일은 SEC_UA 없이 import 되지 않아 같은 자료 파일을 여기서 읽는다 ·
    SEC_UA 가 있으면 construct 가 issuer_map.sector_at 과 멤버-월마다 대조한다): 위키 GICS(pit_gics_sectors · SPX 표 · 섹터 칸이 빈 달은
    없는 것) → 수작업 표(_issuer_map_sector_manual.json · 그때 GICS) → index_history 섹터(비PIT) → stocks.json 오늘 섹터(비PIT).
    이름은 eg30plus.SEC_NORM 으로 맞춘다(위키 옛 표기 'Telecommunications Services'). 티커는 index_history 표기('.')로 찾는다."""

    def __init__(self, root=DATA):
        rj = lambda f: (json.load(io.open(os.path.join(root, f), encoding="utf-8")) if os.path.exists(os.path.join(root, f)) else {})
        self.G = (rj("pit_gics_sectors.json").get("months") or {})
        self.man = {}
        for x in rj("_issuer_map_sector_manual.json").get("rows") or []:
            self.man.setdefault(x["t"], []).append((x["from"], x["to"], x["sector"]))
        self.H = (rj("index_history.json").get("sector") or {})
        self.S = {s["t"]: s.get("sector") for s in (rj("stocks.json").get("stocks") or [])}
        self.inputs = {f: _sha(os.path.join(root, f)) for f in ("pit_gics_sectors.json", "_issuer_map_sector_manual.json",
                                                                  "index_history.json", "stocks.json")}
        self._c = {}

    def src_at(self, t, ym):
        t = t.replace("-", ".")
        ck = (t, ym)
        if ck in self._c:
            return self._c[ck]
        out = None
        g = self.G.get(ym)
        if g:
            for sec, ts in (g.get("sec") or {}).items():
                if t in ts and sec:
                    out = (sec, "wiki_pit")
                    break
        if out is None:
            for a, b, sec in self.man.get(t, ()):
                if a <= ym <= b:
                    out = (sec, "manual")
                    break
        if out is None and self.H.get(t):
            out = (self.H[t], "index_history")
        if out is None and self.S.get(t):
            out = (self.S[t], "stocks_today")
        out = out or (None, "none")
        self._c[ck] = out
        return out

    def at(self, t, ym):
        s = self.src_at(t, ym)[0]
        if s is None:
            return None
        E = _E()
        return E.SEC_NORM.get(s, s)


def load_ytrunc(path=None):
    """보유월 y 가 월말 전에 끝나는 계열의 이름별 판정 {(가격 키, 마지막 값 날짜): 'delisted' | 'kept_trading'} + 원문.
    파일이 없으면 ({}, None) — build_panel 은 판정 없는 «계열 끝» 을 y 결측으로 두고 이름을 싣는다(등록 러너는 하나라도 있으면 멈춘다)."""
    F = FIELDS["ytrunc"]
    ov = px_overlay_path() if path is None else None       # 기본 파일을 읽을 때만 — 가격 오버레이의 제안(파일에 없는 (키, 날)만 · 머리말)
    path = path or os.path.join(RDATA, F["file"])
    out, J = {}, None
    if os.path.exists(path):
        J = json.load(io.open(path, encoding="utf-8"))
        for r in J.get(F["rows"]) or []:
            c = r.get(F["cls"])
            if c not in F["classes"]:
                raise SystemExit("🚨 %s — %s 의 판정 %r 는 %s 가운데 하나여야 한다" % (path, r.get(F["key"]), c, F["classes"]))
            out[(r[F["key"]], r[F["last"]])] = c
    if ov:
        for kk, c in _overlay_ytrunc(_overlay_doc(ov)[0]).items():
            out.setdefault(kk, c)
    return out, J


def y_rule(p, i, i1, key, dates, YT):
    """보유월 수익 y(%) · 판정 — pit_panel.month_rows 규약 + 2026-09-26 등록 전 결정(이름별 · 공개 지식).
    · 보유월 끝(i1)에 값이 있으면 보통 수익('full').
    · 끝 전에 마지막 값이 있고 끝 뒤 Y_END_LOOK 거래일 안에 값이 다시 서면 «끊김»(DB 월말 행 없음 등) → 달 안 마지막 값 수익('gapcut' ·
      1~3일 이른 끝 · 선언) · 달 안에 값이 하나도 없으면 0('gap0').
    · 다시 서지 않으면 «계열 끝» — 판정 YT[(키, 마지막 값 날짜)]: delisted(인수 · 파산 · 비공개화 — 실제 상장폐지) → 마지막 가격
      수익(달 안에 값이 없으면 0 · 'delisted') · kept_trading(지수만 떠나고 거래가 이어짐) → 결측(None · 'kept_trading') ·
      판정 없음 → 결측(None · 'unclassified' — 조용히 마지막 가격을 쓰지 않는다)."""
    seg = p[i + 1:i1 + 1]
    ok = np.where(seg == seg)[0]
    if len(ok) and ok[-1] == len(seg) - 1:
        return float((seg[ok[-1]] / p[i] - 1) * 100), "full", None
    last = (i + 1 + ok[-1]) if len(ok) else i
    tail = p[i1 + 1:i1 + 1 + Y_END_LOOK]
    val = float((seg[ok[-1]] / p[i] - 1) * 100) if len(ok) else 0.0
    if len(tail) and np.any(tail == tail):
        return val, ("gapcut" if len(ok) else "gap0"), None
    if i1 + 1 >= len(p):
        return val, "grid_end", None
    c = YT.get((key, dates[last]))
    if c == "delisted":
        return val, "delisted", dates[last]
    if c == "kept_trading":
        return None, "kept_trading", dates[last]
    return None, "unclassified", dates[last]


def _cap_px(Wd, RAW, k, i):
    """시총 가격과 그 판 — RAW 가 있고 값이 서면 ('raw') · 아니면 배당조정 pxd('adj' · RAW 가 있는데 비면 'adj_fallback')."""
    if RAW is not None:
        a = RAW.get(k)
        v = a[i] if a is not None else float("nan")
        if v == v and v > 0:
            return float(v), "raw"
    p = Wd.PX[k][i]
    return (float(p) if (p == p and p > 0) else None), ("adj" if RAW is None else "adj_fallback")


def _mcap(Wd, RAW, t, k, i):
    """시총(백만 $) = 시총 가격 × pit_panel._shares — RAW 가 없으면 eg30plus.World.mcap(배당조정 pxd × 주식수)과 같은 값."""
    import pit_panel as PP
    if RAW is None:
        return Wd.mcap(t, k, i), "adj"
    p, basis = _cap_px(Wd, RAW, k, i)
    sh = PP._shares(Wd.W, t, k, Wd.dates[i])
    return ((p * sh) if (p and sh) else None), basis


def _glag(IM, t, m, a, kmax=max(JT_K)):
    """시차 표지를 읽을 그룹 — k = 0..kmax 모두 지금 그룹 a['grp'](지도가 선행 CIK 를 이미 이어 붙였다). 같은 티커가 m − k 에 다른
    그룹이면 다른 발행사(티커 재사용)라 쓰지 않는다 — 그런 시차 목록 [(k, 그 그룹)] 을 함께 돌려준다(구성 기록 glag_foreign)."""
    g = a["grp"]
    foreign = []
    for k in range(1, kmax + 1):
        b = IM.at(t, mshift(m, -k))
        if b and b["grp"] and b["grp"] != g:
            foreign.append((k, b["grp"]))
    return [g] * (kmax + 1), foreign


def boundary_world(Wd, IM, m0=BOUND_FROM, m1=M1):
    """R2 (7) «직전 달력연도에 공개된 세계 전체 짝» 의 세계 {(그룹, 달)} + 개수 — 그달 S&P 500 ∪ NDX 멤버(가격 키가 선 것 · 없는 것
    모두 · _members) 가운데 시점정확 GICS 비금융 · FPI 아님(등록 표지 fpi == 1 만 뺀다 · 표본과 같다) · 지도 F0 위반 멤버-월 아님 ·
    지도가 그룹을 푼 것. 가격 커버리지와 무관하다.
    m0 = 2015-01 — 2016 공개분의 경계에 2015 공개 짝이 든다(패널 행으로 재면 2016 경계가 없고 2017 경계가 8~12월만으로 선다)."""
    out, st = set(), {"months": 0, "member_months": 0, "fin": 0, "fpi": 0, "unres": 0}
    for m in months_between(m0, m1):
        if m not in Wd.me:
            continue
        pairs, nokey = _members(Wd, m, Wd.me[m])
        st["months"] += 1
        for t, k in list(pairs) + [(x, x) for x in nokey]:
            st["member_months"] += 1
            if Wd.sector(t, k, m) == FIN:
                st["fin"] += 1
                continue
            a = IM.at(t, m)
            if a and a["fpi"] == 1:
                st["fpi"] += 1
                continue
            if IM.violated(t, m):                      # 지도 F0 위반 멤버-월(표본 규칙과 같다 · 2026-09-26)
                st["im_viol"] = st.get("im_viol", 0) + 1
                continue
            if not a or not a["grp"]:
                st["unres"] += 1
                continue
            out.add((a["grp"], m))
    st["group_months"] = len(out)
    by_y = {}
    for _, m in out:
        by_y[m[:4]] = by_y.get(m[:4], 0) + 1
    st["by_year"] = dict(sorted(by_y.items()))
    return out, st


def _dedup(rows):
    """그룹당 한 행 — 시총이 큰 쪽(같으면 티커 사전순 첫째 · R1 data_build «CIK 당 한 종목»)."""
    best = {}
    for r in rows:
        b = best.get(r["grp"])
        if b is None or r["mc"] > b["mc"] or (r["mc"] == b["mc"] and r["t"] < b["t"]):
            best[r["grp"]] = r
    keep = sorted(best.values(), key=lambda r: r["t"])
    return keep, len(rows) - len(keep)


ARR = ("y", "mc", "size", "logbm", "r1", "mom", "r12", "h52", "top40", "eg")


def _arrays(rows):
    D = {k: np.array([r[k] for r in rows], float) for k in ARR}
    for k in ("t", "k", "grp", "sec"):
        D[k] = [r[k] for r in rows]
    D["glag"] = [tuple(r["glag"]) for r in rows]
    return D


def build_panel(Wd, IM, months=None, top=EG_TOP, FC=None, SA=None, YT=None):
    """PIT 세계 → Stage M 통제 패널 {kind, months, m: {달: 배열}, stat: {달: 구성 기록}, eg_rank: {달: 키 목록(상위 top)}}.

    달 t 의 행(표본 규칙은 머리말): y = r_{t+1}(%) · mc · size = ln 시총 · logbm = ln(B/M)(B ≤ 0 · 없음 → NaN) · r1 = r_t(%)
    · mom = r_{t−12..t−2}(%) · r12 = r_{t−11..t}(12개월 · %) · h52 = P_t ÷ 252일 최고가(George–Hwang · 배당조정 종가 · 선언)
    · top40 = EG30 순위(eg30plus.EG_BASE 의 score — 그 세계에서) 상위 40 · eg = 그 점수 · glag = 시차 k 표지를 읽을 그룹(_glag —
    모두 지금 그룹 · 다른 그룹이던 시차는 stat glag_foreign 으로 센다). 시총 가격은 _raw_px 가 서면 원 종가 · 아니면 배당조정(P cap_basis).
    stat[달]["names"] = 가격 키 없음 · 가격 없음 · 주식수 없음 멤버 티커(§F 명단 — construct 가 편출 여부로 나눈다).

    🔒 2026-09-26 등록 전 결정(커버리지 F0 · 수익 없음 — PREREG «F0 전에 정한 것»):
      세계(분모 = 표본) = 그달 멤버 가운데 비금융(Wd.sector) · FPI 아님(지도 등록 표지 fpi_registered) · 지도 F0 위반 멤버-월 아님.
      덮임 = 월말 가격 ∧ 시총(주식수 관측 나이 ≤ FRESH_DAYS 550일 · 그 관측의 펀드 파일 CIK ∈ 그달 §A0 CIK 집합) ∧ 장부가(≤ 0 허용 ·
      같은 나이 · 같은 CIK 규칙) ∧ 12-2 모멘텀. 행(회귀 표본)도 같은 시총 · 장부가를 쓴다(낡거나 다른 회사 것이면 시총 없음 → 행 빠짐 ·
      장부가 없음 → B/M 결측 더미).
      시총 몫의 가중 = 자기 시총 → 마지막 자기 시총 12개월까지(CAP_CARRY) → 그달 같은 지수(S&P 500 멤버면 S&P 500 · 아니면 NASDAQ 100)
      멤버 자기 시총의 중앙값(금융 · FPI 포함 그 지수 전체 — 지수 수준 대리값).
      y = y_rule(가격 계열이 보유월 끝 전에 끝나면 이름별 판정 — 실제 상장폐지만 마지막 가격 · 지수만 떠나 거래가 이어진 이름은 결측 ·
      판정 없는 끝은 결측으로 두고 P["y_unclassified"] 에 싣는다). 2026-09-26 — pit_panel.y_stop(data/pit_px.json closed[키].stops)이
      결측이라 하면 y_rule 이 값을 줘도 결측이다(판정 'y_stop_missing' · 두 표가 갈리면 결측 쪽 · 갈리는 곳은 없어야 한다 —
      r_cov y_crosstab 이 센다).
      섹터 더미 = SectorAt(issuer_map.sector_at 규칙 — 수작업 섹터 표가 Stage M 에 닿는다) · 금융 판정은 Wd.sector(경계 세계 · P0 세계와
      같은 판정 — 두 출처가 금융을 다르게 보는 멤버-월은 stat sec_fin_disagree 로 센다).
    🚨 수익을 계산하지 않는다 — y 를 배열에 담을 뿐이다. 통계는 fm() 만 내고, fm() 은 등록 커밋 없이 실제 패널을 받지 않는다.
    """
    E = _E()
    months = list(months or months_between(M0, M1))
    RAW = _raw_px(Wd)
    FC = FC if FC is not None else FundCik()
    SA = SA if SA is not None else SectorAt()
    if YT is None:
        YT, _ = load_ytrunc()
    W = Wd.W
    import pit_panel as PP                                  # y_stop(pit_px closed[키].stops) — y_rule 과 함께 본다(2026-09-26)
    P = {"kind": "real", "months": [], "m": {}, "stat": {}, "eg_rank": {}, "cap_basis": "raw" if RAW is not None else "div_adjusted",
         "y_unclassified": [], "f0_rules": {"fresh_days": FRESH_DAYS, "cap_carry": CAP_CARRY, "cap_fallback": "same_index_median",
                                            "cik_check": "fund file CIK (cik_ranges → cik) ∈ month §A0 CIK set", "fund_cik": FC.stat,
                                            "ytrunc_rows": len(YT),
                                            "px_overlay": getattr(Wd, "px_overlay", None)}}   # 선언된 내부 가격 오버레이(sha256 · 수) · None = 공개 판
    last_cap = {}
    mno = lambda ym: int(ym[:4]) * 12 + int(ym[5:7])
    kmax = max(JT_K)
    for m in months:
        m1 = mshift(m, 1)
        if m not in Wd.me or m1 not in Wd.me or mshift(m, -13) not in Wd.me:
            P["stat"][m] = {"skip": "grid"}
            continue
        i, i1, d = Wd.me[m], Wd.me[m1], Wd.dates[Wd.me[m]]
        ip1, ip2, ip12, ip13 = (Wd.me[mshift(m, -j)] for j in (1, 2, 12, 13))
        sc = Wd.score(dict(E.EG_BASE), m)                  # EG30 순위(시점정확 GICS Eg · union · 시총이 선 회사)
        rank = [x[1] for x, _ in sc]
        P["eg_rank"][m] = rank[:top]
        topset, egv = set(rank[:top]), {x[1]: s for x, s in sc}
        pairs, nokey = _members(Wd, m, i)
        spx, ndx = set(W["lists"]["spx"].get(m) or []), set(W["lists"]["ndx"].get(m) or [])
        st = {"members": len(pairs) + len(nokey), "fin": 0, "fpi": 0, "fpi_null": 0, "im_viol": 0, "nokey": 0, "noprice": 0,
              "nocap": 0, "unres": 0, "y_zero": 0, "be_none": 0, "be_nonpos": 0, "mom_nan": 0, "r1_nan": 0, "glag_foreign": 0,
              "cap_raw": 0, "cap_adj_fallback": 0, "sh_stale": 0, "sh_cik": 0, "sh_none": 0, "be_stale": 0, "be_cik": 0,
              "cap_w_own": 0, "cap_w_carry": 0, "cap_w_median": 0, "sec_fin_disagree": 0, "sec_src": {},
              "y": {}, "names": {"nokey": [], "noprice": [], "nocap": [], "glag_foreign": [], "stale_or_cik": [], "y_end": [],
                                 "sec_fin_disagree": []}}
        cov = {"n_den": 0, "n_full": 0, "cap_den": 0.0, "cap_full": 0.0, "cap_unknown": 0}
        # 1) 자기 시총(신선 · CIK 일치 주식수) — 모든 가격 키 멤버(금융 · FPI 포함: 같은 지수 중앙값 대리값의 모집단)
        own, med = {}, {}
        for t, k in pairs:
            pi = Wd.PX[k][i]
            if pi == pi and pi > 0:
                a = IM.at(t, m)
                own[t] = mcap_f0(Wd, RAW, FC, t, k, i, (a or {}).get("ciks"))
            else:
                own[t] = (None, None, "noprice")
        for ix, S_ in (("spx", spx), ("ndx", ndx)):          # 그 지수의 모든 멤버(금융 · FPI · 두 지수 겹침 포함 — r_cov rule F 와 같다)
            v = [own[t][0] for t, _ in pairs if t in S_ and own[t][0]]
            med[ix] = float(np.median(v)) if v else None

        def capw(t, mc):
            if mc:
                st["cap_w_own"] += 1
                return mc
            lc = last_cap.get(t)
            if lc and mno(m) - lc[0] <= CAP_CARRY:
                st["cap_w_carry"] += 1
                return lc[1]
            w = med["spx" if t in spx else "ndx"]
            if w:
                st["cap_w_median"] += 1
            return w

        def excluded(t, k):
            sec = Wd.sector(t, k, m)
            if (sec == FIN) != (SA.at(t, m) == FIN):
                st["sec_fin_disagree"] += 1
                st["names"]["sec_fin_disagree"].append(t)
            if sec == FIN:
                st["fin"] += 1
                return True, None
            a = IM.at(t, m)
            if a and a["fpi"] == 1:
                st["fpi"] += 1
                return True, a
            if IM.violated(t, m):
                st["im_viol"] += 1
                return True, a
            return False, a
        for t in nokey:                                   # 가격 키가 없는 멤버 — 커버리지 분모에만
            ex, _ = excluded(t, t)
            if ex:
                continue
            st["nokey"] += 1
            st["names"]["nokey"].append(t)
            cov["n_den"] += 1
            w = capw(t, None)
            if w:
                cov["cap_den"] += w
            else:
                cov["cap_unknown"] += 1
        rows = []
        for t, k in pairs:
            ex, a = excluded(t, k)
            if ex:
                continue
            st["fpi_null"] += int(bool(a) and a["fpi"] is None)
            cov["n_den"] += 1
            p = Wd.PX[k]
            pi = p[i]
            priced = bool(pi == pi and pi > 0)
            mc, basis, shwhy = own[t]
            if mc:
                last_cap[t] = (mno(m), mc)
                st["cap_raw"] += int(basis == "raw")
                st["cap_adj_fallback"] += int(basis == "adj_fallback")
            elif priced:
                st["sh_" + ("stale" if shwhy == "stale" else ("cik" if shwhy == "cik" else "none"))] += 1
            be, bewhy = fresh_consistent(Wd, FC, t, k, d, "eq", (a or {}).get("ciks")) if mc else (None, "nocap")
            if mc and bewhy in ("stale", "cik"):
                st["be_" + bewhy] += 1
            if priced and (shwhy in ("stale", "cik") or bewhy in ("stale", "cik")):
                st["names"]["stale_or_cik"].append([t, shwhy, bewhy])
            a13, a2 = _px_at(p, ip13), _px_at(p, ip2)
            mom = (a2 / a13 - 1) * 100 if (a13 and a2) else float("nan")
            w = capw(t, mc)
            if w:
                cov["cap_den"] += w
            else:
                cov["cap_unknown"] += 1
            if mc and be is not None and mom == mom:
                cov["n_full"] += 1
                cov["cap_full"] += mc
            if not priced:
                st["noprice"] += 1
                st["names"]["noprice"].append(t)
                continue
            if not mc:
                st["nocap"] += 1
                st["names"]["nocap"].append(t)
                continue
            if a is None or a["grp"] is None:
                st["unres"] += 1
                continue
            a1, a12 = _px_at(p, ip1), _px_at(p, ip12)
            y, yhow, ylast = y_rule(p, i, i1, k, Wd.dates, YT)
            if y is not None and PP.y_stop(W, k, i, i1) == "missing":
                y, yhow = None, "y_stop_missing"            # pit_px closed[키].stops 가 결측이라 한 보유월 — 두 표가 갈리면 결측 쪽(2026-09-26)
            st["y"][yhow] = st["y"].get(yhow, 0) + 1
            st["y_zero"] += int(yhow in ("gap0",) or (yhow == "delisted" and y == 0.0))
            if ylast is not None:
                st["names"]["y_end"].append([t, k, ylast, yhow])
                if yhow == "unclassified":
                    P["y_unclassified"].append([t, k, m, ylast])
            win = p[max(0, i - H52_WIN + 1):i + 1]
            win = win[(win == win) & (win > 0)]
            st["be_none"] += int(be is None)
            st["be_nonpos"] += int(be is not None and be <= 0)
            st["mom_nan"] += int(mom != mom)
            st["r1_nan"] += int(a1 is None)
            glag, foreign = _glag(IM, t, m, a, kmax)
            if foreign:
                st["glag_foreign"] += len(foreign)
                st["names"]["glag_foreign"].append([t, a["grp"]] + [list(x) for x in foreign])
            sec, ssrc = SA.src_at(t, m)
            st["sec_src"][ssrc] = st["sec_src"].get(ssrc, 0) + 1
            s = SA.at(t, m) or "_na"
            rows.append({"t": t, "k": k, "grp": a["grp"], "glag": glag, "sec": s,
                         "y": (float(y) if y is not None else float("nan")), "mc": float(mc),
                         "size": math.log(mc), "logbm": (math.log(be / mc) if (be is not None and be > 0) else float("nan")),
                         "r1": ((pi / a1 - 1) * 100 if a1 else float("nan")), "mom": mom,
                         "r12": ((pi / a12 - 1) * 100 if a12 else float("nan")),
                         "h52": (float(pi / win.max()) if len(win) >= H52_MIN else float("nan")),
                         "top40": float(k in topset), "eg": float(egv.get(k, float("nan")))})
        rows, st["dedup"] = _dedup(rows)
        st["rows"] = len(rows)
        st["cov_n"] = cov["n_full"] / cov["n_den"] if cov["n_den"] else None
        st["cov_cap"] = cov["cap_full"] / cov["cap_den"] if cov["cap_den"] else None
        st["cap_unknown"] = cov["cap_unknown"]
        st["n_den"] = cov["n_den"]
        st["n_full"] = cov["n_full"]
        st["im_ok"] = IM.month_ok(m)
        P["stat"][m] = st
        if rows:
            P["months"].append(m)
            P["m"][m] = _arrays(rows)
    if P["y_unclassified"] and (os.environ.get("RBATCH_COMMIT") or os.environ.get("RBATCH_P0")):
        raise SystemExit("🚨 보유월 가격이 월말 전에 끝난 계열 %d 곳에 판정이 없다(%s …) — data/%s 에 delisted/kept_trading 을 적고 "
                         "등록 커밋에 얼린다" % (len(P["y_unclassified"]), P["y_unclassified"][:4], FIELDS["ytrunc"]["file"]))
    return P


def f0_coverage(P):
    """커버리지 F0(§F · 2026-09-26 규칙 — build_panel 머리말) + 지도 F0(§A0) — 쓸 달 · T · T < 84 면 measure_only. 수익 없이.
    달의 판정: 덮인 멤버 몫(개수) ≥ COV_N ∧ 덮인 시총 몫 ≥ COV_CAP ∧ 지도 F0(위반율 ≤ 2%). 행이 없는 달도 by_month 에 싣는다."""
    rows, use = {}, []
    for m in sorted(P["stat"]):
        st = P["stat"][m]
        if st.get("skip"):
            continue
        okc = st.get("cov_n") is not None and st["cov_n"] >= COV_N and st.get("cov_cap") is not None and st["cov_cap"] >= COV_CAP
        oki = st.get("im_ok", True) is True
        has = m in P["m"]
        rows[m] = {"cov_n": st.get("cov_n"), "cov_cap": st.get("cov_cap"), "n_den": st.get("n_den"), "n_full": st.get("n_full"),
                   "im_ok": st.get("im_ok"), "use": bool(okc and oki and has)}
        if okc and oki and has:
            use.append(m)
    return {"months": use, "T": len(use), "measure_only": len(use) < T_MIN, "by_month": rows,
            "fail": [m for m in P["months"] if not rows[m]["use"]], "y_unclassified": len(P.get("y_unclassified") or []),
            "rules": P.get("f0_rules")}


def overlay_px(Wd, paths):
    """점검 전용 — pit_px.json 모양의 추가 가격 파일(스테이징 · 병합 전)을 세계 가격에 얹는다(없는 키는 더하고 · 있는 키는 빈 날만
    채운다). 격자가 다르면 멈춘다. y 판정 목록(ytrunc_scan)이 병합 뒤 생길 «계열 끝» 까지 미리 덮게 하려는 것이다 — 등록 굽기는 쓰지 않는다."""
    n = len(Wd.dates)
    added = {}
    for path in paths or ():
        J = json.load(io.open(path, encoding="utf-8"))
        if list(J.get("dates") or []) != list(Wd.dates):
            raise SystemExit("🚨 %s 의 격자가 세계 pxd_dates 와 다르다" % path)
        for k, obj in (J.get("px") or {}).items():
            a = np.full(n, np.nan)
            i0 = int(obj.get("i0") or 0)
            for j, v in enumerate(obj.get("p") or []):
                if v is not None and 0 <= i0 + j < n:
                    a[i0 + j] = float(v)
            if k in Wd.W["PX"]:
                b = Wd.W["PX"][k]
                fill = (b != b) & (a == a)
                b[fill] = a[fill]
                added[k] = added.get(k, 0) + int(fill.sum())
            else:
                Wd.W["PX"][k] = a
                added[k] = added.get(k, 0) + int((a == a).sum())
    return added


def ytrunc_scan(Wd, IM, months=None):
    """보유월 가격 계열이 보유월 끝 전에 «끝나는»(끝 뒤 Y_END_LOOK 거래일 안에 다시 서지 않는) 가격 키 멤버-월 목록 — 이름별 판정
    (data/_r_ytrunc.json: delisted · kept_trading) 을 적을 대상. 금융 · FPI 도 싣는다(표본 밖 표시). 수익을 계산하지 않는다(가격이
    있는 날짜만 본다)."""
    months = list(months or months_between(M0, M1))
    YT, _ = load_ytrunc()
    out = {}
    for m in months:
        m1 = mshift(m, 1)
        if m not in Wd.me or m1 not in Wd.me:
            continue
        i, i1 = Wd.me[m], Wd.me[m1]
        pairs, _ = _members(Wd, m, i)
        for t, k in pairs:
            p = Wd.PX[k]
            if not (p[i] == p[i] and p[i] > 0):
                continue
            y, how, last = y_rule(p, i, i1, k, Wd.dates, {})
            if last is None:
                continue
            a = IM.at(t, m)
            rec = out.setdefault((k, last), {"key": k, "last": last, "t": t, "signal_months": [], "fin": Wd.sector(t, k, m) == FIN,
                                             "fpi": bool(a and a["fpi"] == 1), "im_viol": IM.violated(t, m),
                                             "spx": t in set(Wd.W["lists"]["spx"].get(m) or []),
                                             "ndx": t in set(Wd.W["lists"]["ndx"].get(m) or []),
                                             "class": YT.get((k, last))})
            rec["signal_months"].append(m)
    rows = sorted(out.values(), key=lambda r: (r["last"], r["key"]))
    for r in rows:
        r["in_sample"] = not (r["fin"] or r["fpi"] or r["im_viol"])
        meta = Wd.W["meta"].get(r["t"]) or Wd.W["meta"].get(r["t"].replace("-", ".")) or []
        r["name"] = meta[0] if meta else None
    return rows


def panel_digest(P, with_y=False):
    """패널 해시(등록 커밋에 적을 핀) — 키 · 그룹 · 섹터 · 통제(반올림 1e-9). 기본은 y 를 넣지 않는다."""
    h = hashlib.sha256()
    cols = [c for c in ARR if with_y or c != "y"]
    for m in P["months"]:
        D = P["m"][m]
        h.update(m.encode())
        h.update(json.dumps([D["t"], D["grp"], D["sec"], [list(g) for g in D["glag"]]], ensure_ascii=False).encode("utf-8"))
        for c in cols:
            a = np.round(np.nan_to_num(D[c], nan=-9.99e9), 9)
            h.update(a.tobytes())
    return h.hexdigest()


# ══ 엔진 ═════════════════════════════════════════════════════════════════════════════════════
def _guard(P, what):
    if P.get("kind") != "real":
        return
    if what == "p0":
        if os.environ.get("RBATCH_P0") or os.environ.get("RBATCH_COMMIT"):
            return
        raise SystemExit("🚨 실제 패널의 P0 σ 는 RBATCH_P0=1 로만 돈다(자료 → F0 → P0 순서 · 위약 평균은 저장하지 않는다).")
    if not os.environ.get("RBATCH_COMMIT"):
        raise SystemExit("🚨 등록 전에는 실제 패널로 플래그 회귀를 돌리지 않는다 — RBATCH_COMMIT(등록 커밋)을 넘기는 러너만 부른다.")


def _gs(cols, tol=TOL, ref=None):
    """열 목록 [(이름, 벡터)] → (Q 직교 기저, 남긴 이름, 버린 이름). 순서대로 그람–슈미트(두 번 직교화) —
    앞 열로 설명되는 열(잔차 ≤ tol × 원래 크기 · ref 가 있으면 그 크기)은 버린다."""
    Q, kept, drop = [], [], []
    for j, (nm, v) in enumerate(cols):
        v = np.asarray(v, float)
        r0 = float(ref[j]) if ref is not None else float(np.sqrt(v @ v))
        if r0 <= 0:
            drop.append(nm)
            continue
        r = v.copy()
        if Q:
            Qm = np.column_stack(Q)
            r -= Qm @ (Qm.T @ r)
            r -= Qm @ (Qm.T @ r)
        nr = float(np.sqrt(r @ r))
        if nr <= tol * r0:
            drop.append(nm)
            continue
        Q.append(r / nr)
        kept.append(nm)
    n = len(cols[0][1]) if cols else 0
    return (np.column_stack(Q) if Q else np.zeros((n, 0))), kept, drop


def _flag_vec(D, fp, m, k, name, default=0.0):
    """k 달 전(m − k) 표지 — 그 달의 그룹(glag[k])으로 읽는다. 표에 없으면 default(표지 0 · 연속 통제는 NaN) ·
    값이 None 이거나 months_ok 밖의 달이면 NaN(모름)."""
    mk = mshift(m, -k)
    n = len(D["grp"])
    mo = getattr(fp, "months_ok", None)
    if mo is not None and mk not in mo:
        return np.full(n, np.nan)
    out = np.empty(n)
    for j, gl in enumerate(D["glag"]):
        g = gl[k] if k < len(gl) else D["grp"][j]
        rec = fp.get((g, mk))
        if rec is not None and name in rec:
            v = rec[name]
            out[j] = np.nan if v is None else float(v)
        else:
            out[j] = default
    return out


def _design(D, fp, m, k, spec, extra=(), fctrl=(), interact=None, sectors=True, fill=0.0, sample=None):
    """달 m · 시차 k 의 설계 — (y, 통제 열, 플래그 열, 시총, 행 번호). 결측 정책은 MISS(drop → 행 제외 · dummy → 채움 + 더미)."""
    vals = {c: np.asarray(D[c], float) for c in tuple(BASE_CTRL) + tuple(extra)}
    for c in fctrl:
        vals[c] = _flag_vec(D, fp, m, k, c, default=np.nan)
    keep = np.isfinite(np.asarray(D["y"], float))
    for c, v in vals.items():
        if MISS.get(c, "dummy") == "drop":
            keep &= np.isfinite(v)
    if sample:
        keep &= _flag_vec(D, fp, m, k, sample) >= 1
    idx = np.where(keep)[0]
    y = np.asarray(D["y"], float)[idx]
    cols = [("const", np.ones(len(idx)))]
    for c, v in vals.items():
        v = v[idx]
        miss = ~np.isfinite(v)
        if miss.any():
            cols.append((c, np.where(miss, fill, v)))
            cols.append((c + "_na", miss.astype(float)))
        else:
            cols.append((c, v))
    if interact:
        cols.append((interact[1], np.asarray(D[interact[1]], float)[idx]))
    if sectors:
        sec = np.asarray(D["sec"], object)[idx]
        for s in sorted(set(sec)):
            cols.append(("sec:" + str(s), (sec == s).astype(float)))
    fl = []
    for f in spec["flags"]:
        v = _flag_vec(D, fp, m, k, f)[idx]
        unk = ~np.isfinite(v)
        if unk.any():                                  # 모름 — 0 으로 채우고 더미를 통제 블록에(플래그보다 앞)
            v = np.where(unk, 0.0, v)
            cols.append((f + "_unk", unk.astype(float)))
        fl.append((f, v))
    if interact:
        a, b = interact
        fl.append((a + "x" + b, dict(fl)[a] * np.asarray(D[b], float)[idx]))
    return y, cols, fl, np.asarray(D["mc"], float)[idx], idx


def _solve(y, cols, fl, w=None, tol=TOL):
    """FWL — 통제 기저 Q 로 y · 플래그를 잔차화하고 플래그 계수를 푼다(전체 OLS/WLS 와 같은 계수). 자유도가 모자라면 None."""
    if w is not None:
        sw = np.sqrt(w / w.mean())
        y = y * sw
        cols = [(nm, v * sw) for nm, v in cols]
        fl = [(nm, v * sw) for nm, v in fl]
    n = len(y)
    if n == 0:
        return None
    Q, kc, dc = _gs(cols, tol)
    yr = y - Q @ (Q.T @ y)
    fr = [(nm, v - Q @ (Q.T @ v)) for nm, v in fl]
    _, kf, df = _gs(fr, tol, ref=[np.sqrt(v @ v) for _, v in fl])
    dof = n - len(kc) - len(kf)
    if dof < MIN_DOF:
        return None
    b = {nm: None for nm, _ in fl}
    e = yr
    if kf:
        F = np.column_stack([v for nm, v in fr if nm in kf])
        coef = np.linalg.lstsq(F, yr, rcond=None)[0]
        for nm, c in zip(kf, coef):
            b[nm] = float(c)
        e = yr - F @ coef
    return {"b": b, "n": n, "p": len(kc) + len(kf), "dof": dof, "s": float(np.sqrt(e @ e / dof)),
            "s_ctrl": float(np.sqrt(yr @ yr / max(1, n - len(kc)))), "drop": dc + df}


def _mno(ym):
    return int(ym[:4]) * 12 + int(ym[5:7]) - 1


def nw_t_gap(months, x, lag=LAG):
    """달력 위치를 지킨 NW t — eg30plus.nw_t 와 같은 식(바틀렛 가중 · n = 선 달 수)에 빈 달의 편차를 0 으로 둔다
    (시차 L 곱은 달력으로 L 달 떨어진 두 달이 모두 선 쌍만 더한다). 빈 달이 없으면 eg30plus.nw_t 와 같은 값(합성 시험)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 5:
        return None
    pos = np.array([_mno(m) for m in months])
    pos -= pos.min()
    e = np.zeros(int(pos.max()) + 1)
    e[pos] = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, len(e) - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else None


def summarize(res, nm):
    """계수 월 계열 → 평균 · SD · NW(3) t · 한쪽 p(H1 γ < 0 · t(T−1)). 쓴 달(None 이 아닌 달)이 달력으로 이어지면 eg30plus.nw_t 그대로 ·
    빈 달(자유도로 건너뛴 달 · 풀리지 않은 달 · 흩어진 커버리지 실패 달)이 끼면 nw_t_gap 을 주 통계로 쓰고 압축 계열 값과 빈 달 수를 싣는다."""
    from scipy.stats import t as td
    pr = sorted((m, v) for m, v in zip(res["months"], res["g"][nm]) if v is not None)
    ms = [m for m, _ in pr]
    x = np.array([v for _, v in pr], float)
    T = len(x)
    if T < 5:
        return {"T": T, "mean": None, "sd": None, "nw_t": None, "p_one": None, "contiguous": None, "gaps": None}
    gaps = _mno(ms[-1]) - _mno(ms[0]) + 1 - T
    t_lab = _E().nw_t(x, LAG)
    t = t_lab if gaps == 0 else nw_t_gap(ms, x, LAG)
    return {"T": T, "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "nw_t": t,
            "contiguous": gaps == 0, "gaps": int(gaps), "nw_t_compressed": None if gaps == 0 else t_lab,
            "first": ms[0], "last": ms[-1],
            "t_iid": float(x.mean() / (x.std(ddof=1) / math.sqrt(T))) if x.std(ddof=1) > 0 else None,
            "p_one": float(td.cdf(t, T - 1)) if t is not None else None}


def _sub(res, pred):
    """fm 결과를 달 술어로 자른 요약(달 회귀는 달끼리 독립이라 그 달만 다시 돌린 것과 같다 — T2 2023-04 전후 분할 보고)."""
    keep = [j for j, m in enumerate(res["months"]) if pred(m)]
    r = {"months": [res["months"][j] for j in keep], "g": {nm: [v[j] for j in keep] for nm, v in res["g"].items()}}
    return {nm: summarize(r, nm) for nm in r["g"]}


def fm(P, fp, spec, months=None, wls=False, extra=(), fctrl=(), interact=None, sectors=True, fill=0.0, sample=None,
       require_all_k=True):
    """월별 횡단면 회귀(FM) — spec(SPECS 한 줄)의 플래그 계수 월 계열 · JT 평균 · 요약.

    wls → 시총가중 · extra → 추가 통제(EXTRA_R1) · fctrl → 표지 자료의 연속 통제(R2 'dlog') · interact=(플래그, 'top40')
    → 주효과 top40 은 통제로, 플래그×top40 은 플래그 블록으로 · sample → 그 표지가 1 인 행만(T3) · sectors=False 는 시험용.
    """
    _guard(P, "fm")
    months = list(months or P["months"])
    names = list(spec["flags"]) + ([interact[0] + "x" + interact[1]] if interact else [])
    res = {"spec": dict(spec, jt=list(spec["jt"])), "variant": {"wls": wls, "extra": list(extra), "fctrl": list(fctrl),
           "interact": list(interact) if interact else None, "sectors": sectors, "sample": sample},
           "months": [], "g": {nm: [] for nm in names}, "n": [], "n1": {f: [] for f in spec["flags"]}, "skip": {},
           "none": {nm: 0 for nm in names}, "drop": {}}
    for m in months:
        D = P["m"].get(m)
        if D is None:
            res["skip"][m] = "no_panel"
            continue
        rk = []
        for k in spec["jt"]:
            y, cols, fl, mc, _ = _design(D, fp, m, k, spec, extra, fctrl, interact, sectors, fill, sample)
            r = _solve(y, cols, fl, mc if wls else None)
            if r is None:
                break
            r["n1"] = {f: int(np.sum(v != 0)) for f, v in fl if f in spec["flags"]}
            r["unk"] = {nm[:-4]: int(v.sum()) for nm, v in cols if nm.endswith("_unk")}
            rk.append(r)
        if len(rk) < len(spec["jt"]):
            res["skip"][m] = "dof"
            continue
        res["months"].append(m)
        res["n"].append(int(round(np.mean([r["n"] for r in rk]))))
        for r in rk:
            for nm in r["drop"]:
                res["drop"][nm] = res["drop"].get(nm, 0) + 1
        for nm in names:
            v = [r["b"].get(nm) for r in rk]
            vv = [x for x in v if x is not None]
            val = None if ((require_all_k and len(vv) < len(v)) or not vv) else float(np.mean(vv))
            res["none"][nm] += int(val is None)
            res["g"][nm].append(val)
        for f in spec["flags"]:
            res["n1"][f].append(float(np.mean([r["n1"][f] for r in rk])))
            u = sum(r["unk"].get(f, 0) for r in rk)
            if u:
                res.setdefault("unk", {}).setdefault(f, {})[m] = u
    res["sum"] = {nm: summarize(res, nm) for nm in names}
    return res


def pooled_fe(P, fp, spec, months=None, k=0, cluster="grp"):
    """T5 합동 회귀판(측정) — 월 고정효과(달 안 평균 빼기) · 같은 통제 · 그룹 군집 SE(CR1: G/(G−1) · (N−1)/(N−K))."""
    _guard(P, "fm")
    months = list(months or P["months"])
    Ys, Cs, Fs, Gs, names_c = [], [], [], [], None
    for m in months:
        D = P["m"].get(m)
        if D is None:
            continue
        y, cols, fl, _, idx = _design(D, fp, m, k, spec, sectors=True)
        if len(y) < 3:
            continue
        cd = dict(cols)
        if names_c is None:
            names_c = []
        for nm, _ in cols:
            if nm != "const" and nm not in names_c:
                names_c.append(nm)
        Ys.append(y - y.mean())
        Cs.append({nm: v - v.mean() for nm, v in cd.items() if nm != "const"})
        Fs.append(np.column_stack([v - v.mean() for _, v in fl]))
        Gs.extend(np.asarray(D[cluster], object)[idx])
    y = np.concatenate(Ys)
    C = [(nm, np.concatenate([c.get(nm, np.zeros(len(yy))) for c, yy in zip(Cs, Ys)])) for nm in names_c]
    Fm = np.vstack(Fs)
    fl = [(f, Fm[:, j]) for j, f in enumerate(spec["flags"])]
    Q, kc, _ = _gs(C)
    fr = [(nm, v - Q @ (Q.T @ v)) for nm, v in fl]
    _, kf, _ = _gs(fr, ref=[np.sqrt(v @ v) for _, v in fl])
    X = np.column_stack([v for nm, v in C if nm in kc] + [v for nm, v in fl if nm in kf])
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    G = np.asarray(Gs, object)
    S = np.zeros((X.shape[1], X.shape[1]))
    order = np.argsort(G, kind="mergesort")
    Gs_, Xs, es = G[order], X[order], e[order]
    cut = np.flatnonzero(Gs_[1:] != Gs_[:-1]) + 1
    for a, bb in zip(np.r_[0, cut], np.r_[cut, len(G)]):
        u = Xs[a:bb].T @ es[a:bb]
        S += np.outer(u, u)
    N, K, nG = len(y), X.shape[1] + len(Ys), len(cut) + 1       # K = 계수 + 월 고정효과
    V = XtXi @ S @ XtXi * (nG / (nG - 1)) * ((N - 1) / max(1, N - K))
    off = len(kc)
    out = {}
    for f in spec["flags"]:
        if f in kf:
            j = off + kf.index(f)
            out[f] = {"b": float(b[j]), "t": float(b[j] / math.sqrt(V[j, j])) if V[j, j] > 0 else None}
        else:
            out[f] = {"b": None, "t": None}
    return {"N": N, "G": nG, "months": len(Ys), "coef": out}


# ── 관문 · 1차 판정 ────────────────────────────────────────────────────────────────────────────
def _mean(res, nm):
    x = [v for v in res["g"].get(nm, []) if v is not None]
    return float(np.mean(x)) if x else None


def _mean_diff(res, a, b):
    x = [u - v for u, v in zip(res["g"][a], res["g"][b]) if u is not None and v is not None]
    return float(np.mean(x)) if x else None


def gates_r1(main, extra, wls, rs_f0_ok=None):
    """R1 통과 뒤 관문(모두 점 추정) — (i) γ_OS − γ_RS < 0(같은 달끼리) · (ii) 추가 통제판 γ_OS < 0 · (iii) WLS 판 γ_OS < 0.
    rs_f0_ok = RS 밀도 F0(월 RS 종목 수 중앙값 ≥ 10 — 카드: 관문 i 의 조건) — False 면 (i) 은 판정 불가라 거짓(i_na)."""
    v = {"i": _mean_diff(main, "OS", "RS"), "ii": _mean(extra, "OS") if extra else None, "iii": _mean(wls, "OS") if wls else None}
    g = {k: bool(x is not None and x < 0) for k, x in v.items()}
    na = rs_f0_ok is False
    if na:
        g["i"] = False
    return dict(g, all=all(g.values()), vals=v, i_na=na)


def gates_r2(main, wls, lenctl):
    """R2 통과 뒤 관문 — (i) WLS 판 γ_CH < 0 · (ii) Δlog(1A 단어수) 통제판 γ_CH < 0 · 보고만: 결측 더미 계수 < γ_CH → 분리 실패 오염."""
    v = {"i": _mean(wls, "CH") if wls else None, "ii": _mean(lenctl, "CH") if lenctl else None,
         "miss": _mean(main, "CH_miss"), "ch": _mean(main, "CH")}
    g = {k: bool(v[k] is not None and v[k] < 0) for k in ("i", "ii")}
    contam = bool(v["miss"] is not None and v["ch"] is not None and v["miss"] < v["ch"])
    return dict(g, all=all(g.values()), contam=contam, vals=v)


def holm(stats, m, alpha=ALPHA):
    """Holm(한쪽 H1 γ < 0) — stats = {카드: (NW t, T)} · m 은 등록 커밋에 고정한 가족 크기(0 · 1 · 2).
    🚨 m 은 받은 그대로 쓴다 — 가족 수와 다르면 멈춘다(등록 뒤 사건으로 m 이 바뀌지 않게 · R3 조건부 승격을 없앤 이유)."""
    from scipy.stats import t as td
    if m == 0:
        if stats:
            raise ValueError("m = 0 인데 가족이 있다")
        return {}
    if len(stats) != m:
        raise ValueError("가족 크기 %d ≠ 고정 m %d" % (len(stats), m))
    p = {c: (float(td.cdf(t, T - 1)) if t is not None else 1.0) for c, (t, T) in stats.items()}
    out, alive = {}, True
    for j, c in enumerate(sorted(p, key=lambda c: (p[c], c))):
        a = alpha / (m - j)
        ok = alive and p[c] <= a
        out[c] = {"t": stats[c][0], "T": stats[c][1], "p": p[c], "alpha": a, "crit": float(td.ppf(1 - a, stats[c][1] - 1)), "pass": ok}
        alive = ok
    return out


def verdict(qualified, holm_row, gates, measure_only=False, f0_ok=None):
    """Stage M 판정 — 1차 = 커버리지 T ≥ 84(f0_coverage measure_only 가 거짓) ∧ 표지 F0 통과 ∧ 자격(P0 ≥ 0.15) ∧ Holm ∧ 관문 전부.
    measure_only(T < 84 · §F)나 f0_ok 가 False(표지 밀도 F0 실패)거나 자격이 없으면 측정(why 에 까닭)."""
    why = [w for w, bad in (("coverage_T<84", measure_only), ("flag_F0", f0_ok is False), ("P0<0.15", not qualified)) if bad]
    if why:
        return {"class": "measure", "pass": False, "why": why}
    ok = bool(holm_row and holm_row["pass"] and gates["all"])
    return {"class": "primary", "pass": ok, "holm": bool(holm_row and holm_row["pass"]), "gates": bool(gates["all"])}


class _Trials:
    """카드 한 벌의 시도 목록 — 돌린 것(run) · 입력이 없어 못 돌린 것(missing). 시도 수 · DSR N 은 이 목록에서 센다."""

    _SELF = object()

    def __init__(self, card, fp):
        self.card, self.fp, self.rows, self.out = card, fp, [], {}

    def run(self, key, what, fn, need=(), fp=_SELF, blocked=None):
        f = self.fp if fp is _Trials._SELF else fp
        if blocked:
            miss = list(blocked)
        elif f is None:
            miss = ["표지 판 없음"]
        else:
            miss = [n for n in need if not _has(f, n)]
        if miss:
            self.rows.append({"id": "%s.%s" % (self.card, key), "what": what, "run": False, "missing": miss})
            return None
        self.out[key] = fn()
        self.rows.append({"id": "%s.%s" % (self.card, key), "what": what, "run": True})
        return self.out[key]


def stage_m_r1(P, fp, months, rs_f0_ok=None, P_wide=None, fp_wide=None):
    """R1 Stage M 한 벌 — 카드 controls 그대로(모두 시도 수 · DSR N 에 센다):
    주(OS · RS · JT) · 관문 ii(52주 고점 · 12개월) · 관문 iii(WLS) · OS × Eg 상위 40 · 분류 없는 전체 매도 · 쌍둥이 T1~T6 · 선언된 민감도 T1C
    (T2 는 2023-04 전후 분할 요약 · T3 = CLS 표본 · T5 = 합동 회귀) · 2020-07 민감도 · [2014-07 넓힌 창 — P_wide(2014-07 부터 지은 패널)를
    줄 때]. 표지가 없는 쌍둥이는 돌리지 않고 trials 에 missing 으로 적는다. rs_f0_ok 는 관문 i 로 간다."""
    S = SPECS["R1"]
    tr = _Trials("R1", fp)
    tr.run("main", "OS·RS JT k=0..2 (7)", lambda: fm(P, fp, S, months), ("OS", "RS"))
    tr.run("extra", "관문 ii — 52주 고점 괴리 + 12개월 수익", lambda: fm(P, fp, S, months, extra=EXTRA_R1), ("OS", "RS"))
    tr.run("wls", "관문 iii — 시총가중 WLS", lambda: fm(P, fp, S, months, wls=True), ("OS", "RS"))
    tr.run("inter", "OS × Eg 상위 40 상호작용", lambda: fm(P, fp, S, months, interact=("OS", "top40")), ("OS", "RS"))
    tr.run("sall", "분류 없는 전체 매도 더미", lambda: fm(P, fp, SPECS["R1_SALL"], months), ("SALL",))
    tr.run("t1", "T1 Officer · $10만 · 10b5-1 제외 · 3개월 룩백", lambda: fm(P, fp, SPECS["R1_T1"], months), ("OS_T1", "RS"))
    tr.run("t1c", "T1C 선언된 민감도 — T1 과 같고 4/A 가 고친 금액(1차 · T1 은 제출된 그대로)",
           lambda: fm(P, fp, SPECS["R1_T1C"], months), ("OS_T1C", "RS"))

    def t2():
        r = fm(P, fp, SPECS["R1_T2"], months)
        r["split"] = {"pre": _sub(r, lambda m: m < SPLIT_T2), "post": _sub(r, lambda m: m >= SPLIT_T2), "at": SPLIT_T2}
        return r
    tr.run("t2", "T2 10b5-1 행 제외(2023-04 전후 분할)", t2, ("OS_T2", "RS_T2"))
    tr.run("t3", "T3 CMP 표본 한정(분류된 거래가 있는 회사-월)", lambda: fm(P, fp, S, months, sample="CLS"), ("OS", "RS", "CLS"))
    tr.run("t4", "T4 분류 불가를 기회주의로", lambda: fm(P, fp, SPECS["R1_T4"], months), ("OS_T4", "RS_T4"))
    tr.run("t5", "T5 합동 회귀(월 고정효과 · 그룹 군집)", lambda: pooled_fe(P, fp, S, months), ("OS", "RS"))
    tr.run("t6", "T6 순수 CMP(강제 매도 포함)", lambda: fm(P, fp, SPECS["R1_T6"], months), ("OS_T6", "RS_T6"))
    tr.run("sens2020", "민감도 — 신호월 %s 부터" % SENS_FROM[1],
           lambda: fm(P, fp, S, [m for m in months if m >= SENS_FROM[1]]), ("OS", "RS"))
    tr.run("sens2014", "민감도 — 넓힌 창 %s 부터" % SENS_FROM[0],
           lambda: fm(P_wide, fp_wide or fp, S, [m for m in P_wide["months"] if m >= SENS_FROM[0]]), ("OS", "RS"),
           fp=fp_wide or fp, blocked=None if P_wide is not None else ["P_wide(%s 부터 지은 패널)" % SENS_FROM[0]])
    out = dict(tr.out)
    if "main" in out:
        out["gates"] = gates_r1(out["main"], out.get("extra"), out.get("wls"), rs_f0_ok)
    out["trials"] = tr.rows
    return out


def stage_m_r2(P, fp, months, fp_doc=None, fp_ixbrl=None, fp_covid=None, P_wide=None, fp_wide=None):
    """R2 Stage M 한 벌 — 카드 controls 그대로: 주(CH + 결측 더미 — 결측 더미 계수도 여기서) · 관문 i(WLS) · 관문 ii(Δlog 1A 단어수)
    · SimDoc 대조(fp_doc = r2_variants 'doc') · 진단 iXBRL 전환 짝 제외(fp_ixbrl) · 코로나 2020-03~08 공개분 제외(fp_covid)
    · 2020-07 민감도 · [2014-07 넓힌 창]. 상호작용은 카드에 없어 돌리지 않는다(시도 수를 늘리지 않게)."""
    S = SPECS["R2"]
    tr = _Trials("R2", fp)
    tr.run("main", "CH_active + 결측 더미 (9)", lambda: fm(P, fp, S, months), ("CH",))
    tr.run("wls", "관문 i — 시총가중 WLS", lambda: fm(P, fp, S, months, wls=True), ("CH",))
    tr.run("len", "관문 ii — Δlog(1A 단어수) 통제", lambda: fm(P, fp, S, months, fctrl=("dlog",)), ("CH",))
    tr.run("simdoc", "SimDoc 대조(문서 전체 코사인 하위 20%)", lambda: fm(P, fp_doc, S, months), ("CH",), fp=fp_doc)
    tr.run("diag_ixbrl", "진단 — iXBRL 전환 짝 제외", lambda: fm(P, fp_ixbrl, S, months), ("CH",), fp=fp_ixbrl)
    tr.run("diag_covid", "진단 — 2020-03~08 공개분 제외", lambda: fm(P, fp_covid, S, months), ("CH",), fp=fp_covid)
    tr.run("sens2020", "민감도 — 신호월 %s 부터" % SENS_FROM[1],
           lambda: fm(P, fp, S, [m for m in months if m >= SENS_FROM[1]]), ("CH",))
    tr.run("sens2014", "민감도 — 넓힌 창 %s 부터" % SENS_FROM[0],
           lambda: fm(P_wide, fp_wide or fp, S, [m for m in P_wide["months"] if m >= SENS_FROM[0]]), ("CH",),
           fp=fp_wide or fp, blocked=None if P_wide is not None else ["P_wide(%s 부터 지은 패널)" % SENS_FROM[0]])
    out = dict(tr.out)
    if "main" in out:
        out["gates"] = gates_r2(out["main"], out.get("wls"), out.get("len"))
    out["trials"] = tr.rows
    return out


# ── P0 (batch_design_changes 1 · §E) ────────────────────────────────────────────────────────────
def p0(gamma_lit, sigma_plan, T, q=Q_PRIOR, alpha1=ALPHA1, tcrit=T_P0):
    """P0 = q·π + (1−q)·α₁ · π = 1 − Φ(2.27 − 0.5·|γ_lit|·√T / σ_plan). 돌려주는 것 (P0, π)."""
    from scipy.stats import norm
    pi = float(1 - norm.cdf(tcrit - 0.5 * abs(gamma_lit) * math.sqrt(T) / sigma_plan))
    return q * pi + (1 - q) * alpha1, pi


def sigma_gate(gamma_lit, T, gate=P0_GATE, q=Q_PRIOR, alpha1=ALPHA1, tcrit=T_P0):
    """P0 = gate 가 되는 σ_plan(이하면 1차 자격) — R1 T=120 에서 1.58 · R2 2.30 · T=84 면 1.32 · 1.93."""
    from scipy.stats import norm
    pi = (gate - (1 - q) * alpha1) / q
    return 0.5 * abs(gamma_lit) * math.sqrt(T) / (tcrit - float(norm.ppf(1 - pi)))


def _cells(D, idx):
    """섹터 × 시총 3분위 칸(그달 표본 안)."""
    sz = np.asarray(D["size"], float)[idx]
    q1, q2 = np.quantile(sz, [1 / 3, 2 / 3])
    ter = (sz > q1).astype(int) + (sz > q2).astype(int)
    sec = np.asarray(D["sec"], object)[idx]
    return np.array([str(s) + "|" + str(t) for s, t in zip(sec, ter)], object)


def sigma_analytic(P, fp, spec, months=None):
    """σ_analytic = √(평균_t [s_t² · (1/n1_t + 1/n0_t)]) — s_t = 월별 «통제만» 회귀 잔차 SD · n1 = 그달 주 표지 수(k = 0).
    JT 카드(R1 · R3)에서는 k = 0 단일 회귀의 SD 라 JT 평균 SD 의 위쪽 경계다(표지가 완전히 지속하지 않는 한 세 계수 평균이 더 작다 —
    보수 · 선언). 그래서 σ_plan = max(분석적, 위약 90분위) 에서 위약은 두꺼운 꼬리 · 군집으로 분석값을 넘을 때만 일한다."""
    _guard(P, "p0")
    focal = spec["focal"]
    acc, per = [], {}
    for m in (months or P["months"]):
        D = P["m"].get(m)
        if D is None:
            continue
        y, cols, fl, _, _ = _design(D, fp, m, 0, spec)
        Q, kc, _ = _gs(cols)
        n = len(y)
        if n - len(kc) < MIN_DOF:
            continue
        e = y - Q @ (Q.T @ y)
        s = float(np.sqrt(e @ e / (n - len(kc))))
        n1 = int(np.sum(dict(fl)[focal] != 0))
        if n1 == 0 or n1 == n:
            continue
        v = s * s * (1.0 / n1 + 1.0 / (n - n1))
        acc.append(v)
        per[m] = math.sqrt(v)
    return {"sigma": float(math.sqrt(np.mean(acc))) if acc else None, "months": len(acc), "by_month": per}


def sigma_placebo(P, fp, spec, months=None, reps=N_PLACEBO, q=PLACEBO_Q, seed=SEED):
    """σ_placebo — 매월 t 섹터 × 시총 3분위 칸 안에서 발행사 자리를 섞는다(칸 안 순열 π · 한 달에 하나). 가짜 표지는 섞인 자리의
    실제 주 표지 **이력 전체**다 — 시차 k = 0..2 의 실제 표지 벡터에 같은 π 를 건다. 그래서 칸별 표지 수가 시차마다 그대로고, 표지의
    달 사이 지속성(같은 회사가 k 끼리 겹치는 것 → JT 세 계수의 상관)이 남는다. 시차마다 독립으로 새로 뽑으면 그 상관이 지워져
    JT 평균의 SD 가 작게 나온다(합성 · 머무름 0.8 에서 참 귀무 SD 의 0.65 배 — 검토 지적 · 이 판은 selftest 13b 가 잰다).
    단일 회귀 사양(R2)에서는 칸 안 무작위 부분집합 추출과 분포가 같다. 같은 통제로 회귀(주 표지 하나만 — 다른 실제 표지는 넣지 않는다 ·
    선언) · JT 평균 γ 월 계열의 SD 를 reps 번 잰다 → q 분위. 씨앗 default_rng(seed + i).
    🚨 위약 γ 의 평균은 돌려주지도 저장하지도 않는다 — SD 만."""
    _guard(P, "p0")
    focal = spec["focal"]
    prep = []
    for m in (months or P["months"]):
        D = P["m"].get(m)
        if D is None:
            continue
        per_k, idx0 = [], None
        for k in spec["jt"]:
            y, cols, fl, _, idx = _design(D, fp, m, k, spec)
            if idx0 is None:
                idx0 = idx
            elif not np.array_equal(idx, idx0):
                raise SystemExit("🚨 위약 — 시차마다 표본 행이 다르다(sample · fctrl 이 있는 사양은 위약에 쓰지 않는다)")
            Q, kc, _ = _gs(cols)
            if len(y) - len(kc) < MIN_DOF:
                per_k = None
                break
            per_k.append((Q, y - Q @ (Q.T @ y), (dict(fl)[focal] != 0).astype(float)))
        if not per_k:
            continue
        cell = _cells(D, idx0)
        anyf = np.zeros(len(idx0), bool)
        for _, _, f in per_k:
            anyf |= f > 0
        cells = [mem for mem in (np.flatnonzero(cell == c) for c in sorted(set(cell))) if len(mem) > 1 and anyf[mem].any()]
        prep.append((per_k, cells, len(idx0)))
    sds = []
    for i in range(reps):
        rng = np.random.default_rng(seed + i)
        g = []
        for per_k, cells, n in prep:
            perm = np.arange(n)
            for mem in cells:
                perm[mem] = mem[rng.permutation(len(mem))]
            vals = []
            for Q, yr, f in per_k:
                fq = f[perm]
                fr = fq - Q @ (Q.T @ fq)
                den = float(fr @ fr)
                if den > 1e-12:
                    vals.append(float(fr @ yr) / den)
            if len(vals) == len(per_k):
                g.append(float(np.mean(vals)))
        sds.append(float(np.std(g, ddof=1)) if len(g) > 2 else float("nan"))
    sds = np.array(sds)
    return {"sigma": float(np.nanquantile(sds, q)), "q": q, "reps": reps, "months": len(prep),
            "sd_median": float(np.nanmedian(sds)), "scheme": "칸 안 발행사 순열(시차 이력을 함께 옮긴다)"}


# ══ F0 밀도(수익 없이) ════════════════════════════════════════════════════════════════════════
def f0_density(P, fp, flag, months=None, k=0):
    """Stage M 표본 안 월 표지 종목 수 — 중앙값 · 최소 · 달별(F0: OS 중앙값 ≥ 20 · 최소 ≥ 5 · RS 중앙값 ≥ 10 · CH 중앙값 ≥ 30)."""
    by = {}
    for m in (months or P["months"]):
        D = P["m"].get(m)
        if D is not None:
            by[m] = int(np.sum(_flag_vec(D, fp, m, k, flag) >= 1))
    v = np.array(list(by.values())) if by else np.array([0])
    rule = F0_FLAG.get(flag)
    ok = None
    if rule:
        ok = bool(np.median(v) >= rule[0] and (rule[1] is None or v.min() >= rule[1]))
    return {"median": float(np.median(v)), "min": int(v.min()), "ok": ok, "by_month": by}


# ══ 구성 점검(--construct · PIT 세계 · 회귀 없음 · 수익 통계 없음) ═════════════════════════════════
# 시총 단위는 백만 달러(fx 주식수가 백만 주) — 감사 SHARES2 의 «실제» 값: AMZN 1.7조$ · TSLA 1.1조$(이 판 1.28조 — fx sh 가 희석 주식수라 높다)
# · WMT 0.31조$(분할 되맞춤 전 0.09 · 0.38 · 0.10). 이 핀은 분할 되맞춤만 본다 — 저배당 이름이라 배당조정 누수는 HY_PIN 이 본다.
SHARES_PIN = {("AMZN", "2021-06"): (1.4e6, 2.0e6), ("TSLA", "2021-11"): (0.9e6, 1.4e6), ("WMT", "2019-06"): (0.25e6, 0.37e6)}


def _git_head(root=ROOT):
    """작업 사본 HEAD · 바뀐 파일 수(등록 기록의 출처 핀) — git 이 없으면 None."""
    import subprocess
    try:
        h = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip()
        d = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True, timeout=60).stdout
        return {"head": h or None, "dirty": len([x for x in d.splitlines() if x.strip()])}
    except Exception:
        return {"head": None, "dirty": None}


def provenance():
    """구성 · 굽기 기록에 싣는 출처 — 작업 사본 HEAD · RBATCH_DATA · 자료 파일과 정본 모듈의 sha256 · 씨앗 · 시총 가격 판."""
    files = {k: os.path.join(RDATA, FIELDS[k]["file"]) for k in ("issuer_map", "ins", "tenq", "px_raw")}
    mods = {n: os.path.join(HERE, n + ".py") for n in ("r_stagem", "r_r1_flags", "r_r2flags", "pit_panel", "eg30plus", "qbatch_core")}
    ov = px_overlay_path()
    return {"root": ROOT, "git": _git_head(), "rdata": RDATA, "seed": SEED,
            "files": {k: {"path": p, "sha256": _sha(p)} for k, p in files.items()},
            "modules": {k: _sha(p) for k, p in mods.items()},
            "px_overlay": ({"env": PX_OVERLAY_ENV, "sha256": _sha(ov)} if ov else None)}   # 경로는 싣지 않는다(저장소 밖 내부 파일)


def _exit_class(Wd, t, m1=M1):
    """가격 없는 멤버의 편출 분류(§F · 이 저장소 자료로 알 수 있는 만큼) — 마지막 멤버 달 · 티커 재사용 여부 · 이름.
    실제 편출 사유(인수 · 상장폐지 · 파산)는 로컬 자료에 없다(선언 — 집 PC 가격 복구 때 붙인다)."""
    W = Wd.W
    last = None
    for ix in ("spx", "ndx"):
        for m, ts in W["lists"][ix].items():
            if t in ts and (last is None or m > last):
                last = m
    meta = W["meta"].get(t) or W["meta"].get(t.replace("-", ".")) or []
    return {"name": meta[0] if meta else None, "last_member": last, "left_index": bool(last and last < m1),
            "reassigned": t in W["reassigned"]}


def construct(out=None, m0=M0, m1=M1):
    t0 = time.time()
    E = _E()
    Wd = load_world()
    IM = IssuerMap()
    months = months_between(m0, m1)
    P = build_panel(Wd, IM, months)
    rep = {"kind": "r_stagem.construct", "months": [m0, m1], "built": len(P["months"]), "digest": panel_digest(P),
           "cap_basis": P["cap_basis"], "prov": provenance(), "im_pins": IM.pins, "sec": None}
    cov = f0_coverage(P)
    rep["coverage"] = {"T": cov["T"], "measure_only": cov["measure_only"], "fail": cov["fail"], "months": cov["months"],
                       "by_month": cov["by_month"], "rules": cov["rules"], "y_unclassified": P.get("y_unclassified")}
    # 연도별 중앙값
    yrs = {}
    keys = ("members", "n_den", "rows", "fin", "fpi", "fpi_null", "nokey", "noprice", "nocap", "unres", "dedup", "y_zero",
            "be_none", "be_nonpos", "mom_nan", "r1_nan", "cap_unknown", "cov_n", "cov_cap", "glag_foreign", "cap_raw", "cap_adj_fallback",
            "im_viol", "sh_stale", "sh_cik", "sh_none", "be_stale", "be_cik", "cap_w_carry", "cap_w_median", "sec_fin_disagree")
    for m in P["months"]:
        st = P["stat"][m]
        for kk in keys:
            yrs.setdefault(m[:4], {}).setdefault(kk, []).append(st.get(kk))
    rep["by_year"] = {y: {kk: (float(np.median([x for x in v if x is not None])) if any(x is not None for x in v) else None)
                          for kk, v in d.items()} for y, d in sorted(yrs.items())}
    # §F 가격 없는 멤버 명단(달별 · 이름별 편출 분류) · 시차 그룹이 다른 티커(재사용)
    by_m, by_name = {}, {}
    for m in months:
        nm = (P["stat"].get(m) or {}).get("names")
        if not nm:
            continue
        by_m[m] = {k2: nm[k2] for k2 in ("nokey", "noprice", "nocap") if nm[k2]}
        for kind in ("nokey", "noprice", "nocap"):
            for t in nm[kind]:
                r = by_name.setdefault(t, {"kind": {}, "first": m, "last": m})
                r["kind"][kind] = r["kind"].get(kind, 0) + 1
                r["last"] = m
    for t, r in by_name.items():
        r.update(_exit_class(Wd, t, m1))
    rep["no_price"] = {"n_names": len(by_name), "left_index": sum(1 for r in by_name.values() if r["left_index"]),
                       "by_name": dict(sorted(by_name.items())), "by_month": by_m}
    rep["glag_foreign"] = {m: P["stat"][m]["names"]["glag_foreign"] for m in P["months"] if P["stat"][m]["names"]["glag_foreign"]}
    # 2026-09-26 규칙 — 신선도 · CIK 불일치 이름 · y 규칙 · 섹터 출처 · 금융 판정 불일치
    ys, sec_src, sod, yend, fdis = {}, {}, {}, [], {}
    for m in P["months"]:
        st_ = P["stat"][m]
        for k_, v_ in (st_.get("y") or {}).items():
            ys[k_] = ys.get(k_, 0) + v_
        for k_, v_ in (st_.get("sec_src") or {}).items():
            sec_src[k_] = sec_src.get(k_, 0) + v_
        for t_, a_, b_ in st_["names"].get("stale_or_cik") or ():
            r_ = sod.setdefault(t_, {"months": 0, "first": m, "last": m, "sh": {}, "be": {}})
            r_["months"] += 1
            r_["last"] = m
            r_["sh"][a_] = r_["sh"].get(a_, 0) + 1
            r_["be"][b_] = r_["be"].get(b_, 0) + 1
        yend += [[m] + x for x in st_["names"].get("y_end") or ()]
        for t_ in st_["names"].get("sec_fin_disagree") or ():
            fdis[t_] = fdis.get(t_, 0) + 1
    rep["f0_components"] = {"y_rule": ys, "y_end_rows": yend, "sector_source_rows": sec_src, "stale_or_cik_names": dict(sorted(sod.items())),
                            "fin_disagree_member_months": dict(sorted(fdis.items())), "fund_cik": P["f0_rules"]["fund_cik"]}
    if (os.environ.get("SEC_UA") or "").strip():               # issuer_map.sector_src_at 대조(SEC 요청 없음 · import 만)
        try:
            import issuer_map as _IMM
            R_ = _IMM.load_refs()
            SA_ = SectorAt()
            nn = bad = 0
            exs = []
            for t_, runs in IM.tm.items():
                for r_ in runs:
                    for ym in months_between(max(r_[0], "2014-06"), min(r_[1], m1)):
                        nn += 1
                        a_, b_ = SA_.src_at(t_, ym), _IMM.sector_src_at(R_, t_, ym)
                        if tuple(a_) != tuple(b_):
                            bad += 1
                            if len(exs) < 10:
                                exs.append([t_, ym, a_, b_])
            rep["sector_vs_issuer_map"] = {"compared": nn, "differ": bad, "examples": exs}
        except SystemExit as e_:
            rep["sector_vs_issuer_map"] = {"skipped": str(e_)[:120]}
    else:
        rep["sector_vs_issuer_map"] = {"skipped": "SEC_UA 없음 — issuer_map import 생략(SectorAt 는 같은 규칙 · selftest 18)"}
    # 통제 분포(수익 y 는 넣지 않는다)
    q = {}
    for c in ("size", "logbm", "r1", "mom", "r12", "h52"):
        a = np.concatenate([P["m"][m][c] for m in P["months"]])
        f = a[np.isfinite(a)]
        q[c] = {"n": int(len(a)), "nan": float(1 - len(f) / len(a)), "q05": float(np.quantile(f, .05)),
                "q50": float(np.quantile(f, .5)), "q95": float(np.quantile(f, .95))}
    rep["controls"] = q
    secs = {}
    for m in P["months"]:
        for s in P["m"][m]["sec"]:
            secs[s] = secs.get(s, 0) + 1
    rep["sec"] = dict(sorted(secs.items(), key=lambda kv: -kv[1]))
    # 시총 핀(AUDIT-2026-09-20-SHARES2 분할 되맞춤) · 고배당 핀(시총 가격이 원 종가인가 — 배당조정 누수)
    RAW = _raw_px(Wd)
    pin = {}
    for (t, m), (lo, hi) in SHARES_PIN.items():
        v, _ = _mcap(Wd, RAW, t, t, Wd.me[m])
        pin["%s@%s" % (t, m)] = {"mcap": v, "ok": bool(v and lo <= v <= hi)}
    rep["shares_pin"] = pin
    hy = {}
    for (t, m), ref in HY_PIN.items():
        pc, basis = _cap_px(Wd, RAW, t, Wd.me[m])
        r_ = (pc / ref) if pc else None
        hy["%s@%s" % (t, m)] = {"cap_px": pc, "raw_ref": round(ref, 4), "ratio": r_, "basis": basis,
                                "ok": bool(r_ is not None and abs(r_ - 1) <= HY_TOL)}
    rep["hy_pin"] = hy
    rep["hy_pin_ok"] = all(v["ok"] for v in hy.values())
    # EG30 V0 명단 = 내 Eg 순위 앞 30(편입월마다)
    T0 = E.v0_targets(Wd)
    mis = [m for m in T0 if m in P["eg_rank"] and set(P["eg_rank"][m][:30]) != set(T0[m]["w"])]
    in_s = []
    for m in P["months"]:
        ks = set(P["m"][m]["k"])
        in_s.append(sum(1 for k in P["eg_rank"][m] if k in ks))
    rep["eg"] = {"v0_forms": len(T0), "v0_mismatch": mis, "top40_in_sample_median": float(np.median(in_s)), "top40_in_sample_min": int(min(in_s))}
    # 지도 조회 표본
    rep["im_lookup"] = {"%s@%s" % (t, m): IM.at(t, m) for t, m in (("AAPL", "2020-01"), ("BRK-B", "2020-01"), ("DIS", "2019-01"),
                                                                    ("DIS", "2019-06"), ("XOM", "2016-08"), ("ASML", "2020-01"))}
    # 표지 밀도(자료가 있으면 · 개수만)
    dens = {}
    ins_p = os.path.join(RDATA, FIELDS["ins"]["file"])
    if os.path.exists(ins_p):
        fp = ins_flags(ins_p)
        for f in ("OS", "RS", "SALL", "OS_T1", "OS_T2", "OS_T4", "OS_T6"):
            if _has(fp, f):
                dd = f0_density(P, fp, f, cov["months"])
                dens[f] = {k2: dd[k2] for k2 in ("median", "min", "ok")}
        dens["_ins"] = {"src": fp.src, "notes": fp.notes}
    bw, bst = boundary_world(Wd, IM, BOUND_FROM, m1)      # R2 경계 세계(10-Q 자료가 없어도 구성만 잰다)
    rep["r2_world"] = bst
    tq_p = os.path.join(RDATA, FIELDS["tenq"]["file"])
    if os.path.exists(tq_p):
        got = tenq_canonical(tq_p, world=bw)
        if got is None:                                   # RBATCH_PROVISIONAL=1 일 때만 여기로 온다
            fp2, _ = tenq_flags(Wd.dates, tq_p, world=bw, window=(m0, m1))
        else:
            fp2 = got[0]
            rep["r2_bounds"] = {str(y): v for y, v in sorted(got[1]["bounds"].items())}
        dd = f0_density(P, fp2, "CH", cov["months"])
        dens["CH"] = dict({k2: dd[k2] for k2 in ("median", "min", "ok")}, src=fp2.src)
    rep["density"] = dens or "표지 자료 없음(빌드 중)"
    rep["sec_elapsed"] = round(time.time() - t0, 1)
    # 찍기
    print("r_stagem --construct · 달 %s..%s · 지은 달 %d · 쓸 달 T=%d%s · %.1f초" % (m0, m1, rep["built"], cov["T"],
          " (측정으로 내림)" if cov["measure_only"] else "", rep["sec_elapsed"]))
    g = rep["prov"]["git"]
    print("  패널 해시(y 없음) %s · 시총 가격 %s · HEAD %s(바뀐 파일 %s) · 지도 sha256 %s" % (
        rep["digest"][:16], P["cap_basis"], (g["head"] or "?")[:10], g["dirty"],
        (rep["prov"]["files"]["issuer_map"]["sha256"] or "?")[:16]))
    ovr = getattr(Wd, "px_overlay", None)
    print("  가격 오버레이(%s) %s" % (PX_OVERLAY_ENV, "없음 — 공개 판" if not ovr else "sha256 %s · %s · 채운 값 %d(키 %d · 새 키 %d) · 건너뜀 %s · 더한 멈춤 %d" % (
        ovr["sha256"][:16], ovr["visibility"], ovr["values_filled"], ovr["keys_filled"], ovr["keys_new"], ovr["skipped"], ovr["stops_added"])))
    for y, d in rep["by_year"].items():
        print("  %s 멤버 %4.0f · 세계 %4.0f · 행 %4.0f · 금융 %3.0f · FPI %2.0f · 가격키없음 %2.0f · 가격없음 %2.0f · 주식수없음 %2.0f"
              " · 지도못풂 %2.0f · 중복 %1.0f · 시차그룹다름 %1.0f · 커버 개수 %.3f 시총 %.3f" % (
                  y, d["members"], d["n_den"], d["rows"], d["fin"], d["fpi"], d["nokey"], d["noprice"], d["nocap"], d["unres"],
                  d["dedup"], d["glag_foreign"] or 0, d["cov_n"] or 0, d["cov_cap"] or 0))
    for c, v in q.items():
        print("  통제 %-5s 결측 %.3f · 5%% %.3f · 50%% %.3f · 95%% %.3f" % (c, v["nan"], v["q05"], v["q50"], v["q95"]))
    print("  시총 핀 %s" % {k2: v["ok"] for k2, v in pin.items()})
    print("  고배당 핀(시총 가격 ÷ 원 종가) %s%s" % ({k2: (round(v["ratio"], 3) if v["ratio"] else None) for k2, v in hy.items()},
          "" if rep["hy_pin_ok"] else " 🚨 실패 — 시총이 배당조정 종가에서 나왔다(크기 · B/M · WLS 가중에 미래 배당 누수 · 선언 · 원 종가 판 필요)"))
    print("  EG30 V0 명단 = Eg 순위 앞 30 · 어긋난 편입 %d/%d · 표본 안 상위 40 중앙값 %.0f(최소 %d)" % (
        len(mis), len(T0), rep["eg"]["top40_in_sample_median"], rep["eg"]["top40_in_sample_min"]))
    print("  커버리지 F0 실패 달 %d(%s..%s) · 쓸 달 %s..%s · 시총을 모르는 멤버(가격이 한 번도 없음) 연 중앙값 %s" % (
        len(cov["fail"]), (cov["fail"] or ["-"])[0], (cov["fail"] or ["-"])[-1], (cov["months"] or ["-"])[0], (cov["months"] or ["-"])[-1],
        {y: d["cap_unknown"] for y, d in rep["by_year"].items()}))
    print("  y 규칙 %s · 판정 없는 계열 끝 %d · 섹터 출처 %s · 금융 판정 불일치 멤버-월 %d · 섹터 대 issuer_map %s" % (
        rep["f0_components"]["y_rule"], len(P.get("y_unclassified") or []), rep["f0_components"]["sector_source_rows"],
        sum(rep["f0_components"]["fin_disagree_member_months"].values()),
        {k2: v for k2, v in rep["sector_vs_issuer_map"].items() if k2 != "examples"}))
    print("  가격 없는 멤버 %d 종(편출 %d) · 시차 그룹이 다른 행이 있는 달 %d" % (
        rep["no_price"]["n_names"], rep["no_price"]["left_index"], len(rep["glag_foreign"])))
    print("  R2 경계 세계(%s..%s · 비금융 · FPI 아님 · 지도가 푼 그룹-월 · 가격 무관) 연도별 %s" % (BOUND_FROM, m1, bst["by_year"]))
    print("  표지 밀도: %s" % (json.dumps(dens, ensure_ascii=False) if dens else "자료 없음(빌드 중)"))
    if out:
        json.dump(rep, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("  → %s" % out)
    return rep


# ══ 합성 자료 시험(--selftest · 실제 자료를 하나도 읽지 않는다 — 발행사 지도 조회 점검만 파일이 있으면 읽는다) ═════
def _synth(seed=1, T=60, N=400, nsec=10, m0="2016-08"):
    """합성 패널(y 없이) — 그룹 g<i> · 섹터 s<i % nsec> · 크기(로그정규 · 퍼짐 1.2) · B/M 5% 결측 · 모멘텀 2% 결측 ·
    52주 고점 U(0.5, 1) · 상위 40 = 무작위. 달마다 3% 는 표본에서 빠진다. y 와 표지는 시험마다 채운다."""
    rng = np.random.default_rng(seed)
    months = months_between(m0, mshift(m0, T - 1))
    base = rng.normal(23.0, 1.2, N)
    sec = np.array(["s%02d" % (j % nsec) for j in range(N)], object)
    P = {"kind": "synth", "months": [], "m": {}, "stat": {}, "eg_rank": {}}
    for m in months:
        keep = np.flatnonzero(rng.random(N) > 0.03)
        n = len(keep)
        size = base[keep] + rng.normal(0, 0.1, n)
        lbm = rng.normal(-1.0, 0.8, n)
        lbm[rng.random(n) < 0.05] = np.nan
        mom = rng.normal(8, 25, n)
        mom[rng.random(n) < 0.02] = np.nan
        top = np.zeros(n)
        top[rng.choice(n, 40, replace=False)] = 1
        D = {"t": ["T%03d" % j for j in keep], "k": ["T%03d" % j for j in keep], "grp": ["g%d" % j for j in keep],
             "glag": [("g%d" % j,) * 3 for j in keep], "sec": list(sec[keep]), "y": np.zeros(n), "mc": np.exp(size),
             "size": size, "logbm": lbm, "r1": rng.normal(1, 7, n), "mom": mom, "r12": rng.normal(10, 30, n),
             "h52": rng.uniform(0.5, 1.0, n), "top40": top, "eg": rng.random(n), "_j": keep}
        P["months"].append(m)
        P["m"][m] = D
    return P, rng


def _bern_flags(P, rng, name, prob, pre=2):
    """표지 — 그룹 · 달마다 독립 베르누이(prob 는 상수 또는 (D, m) → 행별 확률). 앞 pre 달도 만든다(JT 시차)."""
    fp = {}
    ms = [mshift(P["months"][0], -j) for j in range(pre, 0, -1)] + P["months"]
    for m in ms:
        D = P["m"].get(m) or P["m"][P["months"][0]]
        pr = prob(D, m) if callable(prob) else np.full(len(D["grp"]), prob)
        hit = rng.random(len(pr)) < pr
        for g, h in zip(D["grp"], hit):
            if h:
                fp.setdefault((g, m), {})[name] = 1.0
    return fp


def _merge(*fps):
    out = {}
    for f in fps:
        for k, v in f.items():
            out.setdefault(k, {}).update(v)
    return out


def _set_y(P, fp, noise, rng, effect):
    """y = 섹터 효과 + 0.4·(size − 23) + 0.02·r1 + effect(D, m) + 잡음."""
    for m in P["months"]:
        D = P["m"][m]
        n = len(D["grp"])
        sec_eff = np.array([0.3 * int(s[1:]) - 1.0 for s in D["sec"]])
        D["y"] = sec_eff + 0.4 * (D["size"] - 23) + 0.02 * D["r1"] + effect(D, m) + rng.normal(0, noise, n)


def selftest():
    from scipy.stats import t as td
    E = _E()
    fails, skipped, n_ok = [], [], 0

    def check(name, cond, info=""):
        nonlocal n_ok
        if cond:
            n_ok += 1
            print("  ✓ %s %s" % (name, info))
        else:
            fails.append(name)
            print("  ✗ %s %s" % (name, info))

    def skip(name, why):
        """정본 모듈 · 자료가 없어 못 한 점검 — 통과로 세지 않는다(따로 센다)."""
        skipped.append(name)
        print("  · 건너뜀 %s — %s" % (name, why))

    def sib(name):
        """형제 정본 모듈 — 없으면 None(건너뜀) · import 중 다른 오류면 실패로 적고 None(시험 전체를 죽이지 않는다)."""
        try:
            return __import__(name)
        except ImportError:
            return None
        except Exception as e:                       # 정본이 고쳐지는 중이거나 깨졌다 — 조용히 넘기지 않는다
            check("정본 %s import" % name, False, "%s: %s" % (type(e).__name__, e))
            return None

    def se(res, nm):
        s = res["sum"][nm]
        return s["sd"] / math.sqrt(s["T"])
    print("r_stagem --selftest (합성 자료)")

    # 1. FWL = 명시 설계 lstsq (OLS · WLS · 결측 더미 · 섹터 · 종속 열)
    P, rng = _synth(seed=11, T=3)
    fp = _merge(_bern_flags(P, rng, "OS", 0.08), _bern_flags(P, rng, "RS", 0.05))
    _set_y(P, fp, 5.0, rng, lambda D, m: 0.0)
    m = P["months"][1]
    D = P["m"][m]
    for wls in (False, True):
        y, cols, fl, mc, _ = _design(D, fp, m, 1, SPECS["R1"], extra=EXTRA_R1, interact=("OS", "top40"))
        cols = cols + [("dup_size", 2 * dict(cols)["size"])]        # 종속 열 — 버려져야 한다
        r = _solve(y, cols, fl, mc if wls else None)
        _, kc, _ = _gs(cols)
        X = np.column_stack([v for nm, v in cols if nm in kc] + [v for _, v in fl])
        sw = np.sqrt(mc / mc.mean()) if wls else np.ones(len(y))
        b = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0][-len(fl):]
        diff = max(abs(r["b"][nm] - bb) for (nm, _), bb in zip(fl, b))
        check("FWL=lstsq(%s)" % ("WLS" if wls else "OLS"), diff < 1e-8 and "dup_size" in r["drop"] and "sec:s09" in r["drop"],
              "최대 차 %.1e · 버린 열 %s" % (diff, r["drop"]))
    # 채운 상수 불변(결측 더미)
    b0 = _solve(*_design(D, fp, m, 0, SPECS["R1"], fill=0.0)[:3])["b"]["OS"]
    b5 = _solve(*_design(D, fp, m, 0, SPECS["R1"], fill=5.0)[:3])["b"]["OS"]
    check("결측 더미 — 채운 상수 불변", abs(b0 - b5) < 1e-10, "%.2e" % abs(b0 - b5))
    y, cols, fl, _, idx = _design(D, fp, m, 0, SPECS["R1"])
    check("결측 정책 — B/M 결측 행 유지 · 모멘텀 결측 행 제외",
          len(idx) == int(np.isfinite(D["mom"]).sum()) and "logbm_na" in dict(cols), "n %d / %d" % (len(idx), len(D["y"])))
    # 풀리지 않는 표지 → None
    fz = {k2: {"RS": v.get("RS", 0.0)} for k2, v in fp.items()}
    r = _solve(*_design(D, fz, m, 0, SPECS["R1"])[:3])
    check("표지가 전부 0 이면 None", r["b"]["OS"] is None and r["b"]["RS"] is not None)

    # 2. 회복 — JT 평균(세 시차에 모두 −0.5 → −0.5 · 시차 0 에만 −0.6 → −0.2)
    P, rng = _synth(seed=21, T=120)
    fo, fr_ = _bern_flags(P, rng, "OS", 0.08), _bern_flags(P, rng, "RS", 0.05)
    fp = _merge(fo, fr_)
    lagsum = lambda D, m, ks, g: sum(_flag_vec(D, fp, m, k, "OS") for k in ks) * g
    _set_y(P, fp, 4.0, rng, lambda D, m: lagsum(D, m, (0, 1, 2), -0.5))
    res = fm(P, fp, SPECS["R1"])
    s = res["sum"]["OS"]
    check("JT 회복(세 시차 −0.5)", abs(s["mean"] + 0.5) < 4 * se(res, "OS") and s["nw_t"] < -5,
          "γ̂ %.3f ± %.3f · NW t %.1f · T %d" % (s["mean"], se(res, "OS"), s["nw_t"], s["T"]))
    check("NW t 는 eg30plus.nw_t", abs(s["nw_t"] - E.nw_t(np.array(res["g"]["OS"]), 3)) < 1e-12)
    check("RS 는 0 근처", abs(res["sum"]["RS"]["mean"]) < 4 * se(res, "RS"), "γ̂_RS %.3f" % res["sum"]["RS"]["mean"])
    _set_y(P, fp, 4.0, rng, lambda D, m: lagsum(D, m, (0,), -0.6))
    res = fm(P, fp, SPECS["R1"])
    s = res["sum"]["OS"]
    check("JT 회복(시차 0 에만 −0.6 → −0.2)", abs(s["mean"] + 0.2) < 4 * se(res, "OS"), "γ̂ %.3f" % s["mean"])

    # 3. 섹터 더미 — 표지가 약한 섹터에 몰려도 참 γ = 0 이면 0
    P, rng = _synth(seed=31, T=120)
    fp = _merge(_bern_flags(P, rng, "OS", lambda D, m: np.where(np.array(D["sec"]) == "s00", 0.25, 0.05)),
                _bern_flags(P, rng, "RS", 0.05))
    _set_y(P, fp, 4.0, rng, lambda D, m: np.where(np.array(D["sec"]) == "s00", -2.0, 0.0))
    r1_, r0_ = fm(P, fp, SPECS["R1"]), fm(P, fp, SPECS["R1"], sectors=False)
    check("섹터 더미가 섹터 효과를 흡수", abs(r1_["sum"]["OS"]["mean"]) < 4 * se(r1_, "OS") and r0_["sum"]["OS"]["mean"] < -0.5,
          "섹터 있음 %.3f · 없음 %.3f" % (r1_["sum"]["OS"]["mean"], r0_["sum"]["OS"]["mean"]))

    # 4. 관문 ii — 52주 고점 괴리로만 난 효과는 추가 통제에서 사라진다
    P, rng = _synth(seed=41, T=120)
    fp = _merge(_bern_flags(P, rng, "OS", lambda D, m: 0.02 + 0.3 * (1 - D["h52"])), _bern_flags(P, rng, "RS", 0.05))
    S0 = dict(SPECS["R1"], jt=(0,))                            # 표지월 = 그달(k = 0) 의 h52 가 확률을 정했다 → JT 없이 본다
    _set_y(P, fp, 4.0, rng, lambda D, m: 8.0 * (D["h52"] - 0.75))
    rb, re_ = fm(P, fp, S0), fm(P, fp, S0, extra=EXTRA_R1)
    check("관문 ii — 추가 통제가 52주 고점 효과를 걷어낸다", rb["sum"]["OS"]["mean"] < -0.3 and abs(re_["sum"]["OS"]["mean"]) < 4 * se(re_, "OS"),
          "기본 %.3f · 추가 통제 %.3f" % (rb["sum"]["OS"]["mean"], re_["sum"]["OS"]["mean"]))

    # 5. WLS — 작은 회사에만 효과가 있으면 시총가중이 0 쪽으로
    P, rng = _synth(seed=51, T=120)
    fp = _merge(_bern_flags(P, rng, "OS", 0.08), _bern_flags(P, rng, "RS", 0.05))
    _set_y(P, fp, 4.0, rng, lambda D, m: np.where(D["size"] < 23, -1.5, 0.0) * _flag_vec(D, fp, m, 0, "OS"))
    S0 = dict(SPECS["R1"], jt=(0,))
    ro, rw = fm(P, fp, S0), fm(P, fp, S0, wls=True)
    check("WLS 가 큰 회사 쪽 효과를 잰다", rw["sum"]["OS"]["mean"] > ro["sum"]["OS"]["mean"] + 0.3 and ro["sum"]["OS"]["mean"] < -0.4,
          "OLS %.3f · WLS %.3f" % (ro["sum"]["OS"]["mean"], rw["sum"]["OS"]["mean"]))

    # 6. 상호작용 — 효과가 상위 40 안에만
    P, rng = _synth(seed=61, T=120)
    fp = _merge(_bern_flags(P, rng, "OS", 0.10), _bern_flags(P, rng, "RS", 0.05))
    _set_y(P, fp, 3.0, rng, lambda D, m: -2.0 * D["top40"] * _flag_vec(D, fp, m, 0, "OS"))
    ri = fm(P, fp, dict(SPECS["R1"], jt=(0,)), interact=("OS", "top40"))
    si, so = ri["sum"]["OSxtop40"], ri["sum"]["OS"]
    check("상호작용 회복", abs(si["mean"] + 2.0) < 4 * se(ri, "OSxtop40") and abs(so["mean"]) < 4 * se(ri, "OS"),
          "γ_int %.3f · γ_OS %.3f" % (si["mean"], so["mean"]))

    # 7. 시차 표지 — 엔진은 glag[k] 로 읽고(기구) · 패널은 glag 를 모두 지금 그룹으로 짓는다(티커 재사용 = 다른 발행사)
    P, rng = _synth(seed=71, T=6)
    m = P["months"][3]
    D = P["m"][m]
    D["glag"][0] = ("gNEW", "gOLD", "gOLD")
    fpl = {("gOLD", mshift(m, -1)): {"OS": 1.0}, ("gNEW", mshift(m, -1)): {"OS": 0.0}, ("gNEW", m): {"OS": 1.0}}
    v0, v1, v2 = (_flag_vec(D, fpl, m, k, "OS")[0] for k in (0, 1, 2))
    check("시차 표지 기구 — _flag_vec 은 glag[k] 그룹으로 조회", (v0, v1, v2) == (1.0, 1.0, 0.0), "(%s, %s, %s)" % (v0, v1, v2))
    IMr = IssuerMap(J={"tm": {"IR": [["2014-06", "2020-02", "gOLD", 1, [1], 0, "dera", 0], ["2020-03", "2026-09", "gNEW", 2, [2], 0, "dera", 0]]}})
    gl, fo = _glag(IMr, "IR", "2020-03", IMr.at("IR", "2020-03"))
    gl2, fo2 = _glag(IMr, "IR", "2020-06", IMr.at("IR", "2020-06"))
    check("시차 그룹 정책 — 티커 재사용이면 지금 그룹 · 다른 그룹 시차를 센다", gl == ["gNEW"] * 3 and fo == [(1, "gOLD"), (2, "gOLD")]
          and gl2 == ["gNEW"] * 3 and fo2 == [], "%s %s" % (gl, fo))

    # 8. 중복 그룹 · 가용일 · UTC→ET
    rows = [{"grp": "g1", "mc": 5.0, "t": "B"}, {"grp": "g1", "mc": 9.0, "t": "A2"}, {"grp": "g2", "mc": 1.0, "t": "C"}]
    kp, nd = _dedup(rows)
    check("그룹당 한 행(시총 큰 쪽)", nd == 1 and {r["t"] for r in kp} == {"A2", "C"})
    days = [d.strftime("%Y-%m-%d") for d in (dt.date(2019, 5, 1) + dt.timedelta(j) for j in range(120)) if d.weekday() < 5]
    check("가용일 16:00 규칙", avail_day("2019-05-31T15:59:00", days) == "2019-05-31" and avail_day("2019-05-31 16:00:00", days) == "2019-06-03"
          and avail_day("2019-06-01T09:00:00", days) == "2019-06-03")
    check("UTC→ET(서머타임)", utc_to_et("2019-05-31T20:30:00Z") == "2019-05-31 16:30:00" and utc_to_et("2019-12-02T21:00:00") == "2019-12-02 16:00:00"
          and utc_to_et("2019-03-10T06:59:00") == "2019-03-10 01:59:00" and utc_to_et("2019-03-10T07:00:00") == "2019-03-10 03:00:00")

    # 9. 10-Q 어댑터 — 전년도 20% 경계 · 3개월 창 · 결측 더미 · Δlog
    days = [d.strftime("%Y-%m-%d") for d in (dt.date(2016, 1, 4) + dt.timedelta(j) for j in range(1200)) if d.weekday() < 5]
    rng2 = np.random.default_rng(9)
    docs = [{"grp": "w%d" % j, "accepted_et": "2017-05-10T10:00:00", "parse_status": "ok", "SimRF": float(s), "dlog_len_rf": 0.0}
            for j, s in enumerate(rng2.uniform(0.5, 1.0, 100))]
    thr17 = float(np.quantile([d["SimRF"] for d in docs], 0.2))
    docs += [{"grp": "A", "accepted_et": "2018-05-31 16:30:00", "parse_status": "ok", "SimRF": thr17 - 0.01, "dlog_len_rf": 0.3},
             {"grp": "B", "accepted_et": "2018-05-10T10:00:00", "parse_status": "ok", "SimRF": thr17 + 0.01, "dlog_len_rf": 0.1},
             {"grp": "C", "accepted_et": "2018-08-01T10:00:00", "parse_status": "fail", "SimRF": None},
             {"grp": "D", "accepted_et": "2018-08-01T10:00:00", "parse_status": "ok", "SimRF": 0.1, "shape": "F", "prev_shape": "B"},
             {"grp": "E", "accepted_et": "2016-03-01T10:00:00", "parse_status": "ok", "SimRF": 0.1}]
    ftq, rtq = tenq_flags(days, J={"docs": docs})
    A = [ftq.get(("A", mm), {}).get("CH") for mm in ("2018-05", "2018-06", "2018-07", "2018-08", "2018-09")]
    check("10-Q CH — 16:00 뒤 접수는 다음 거래일 달 · 3개월 창", A == [None, 1.0, 1.0, 1.0, None], str(A))
    check("10-Q 경계는 전년도 분포 · 첫해는 결측", abs(float(rtq["thr"]["2018"]) - thr17) < 1e-12 and ftq[("E", "2016-03")]["CH_miss"] == 1.0
          and ftq[("B", "2018-05")] == {"CH": 0.0, "CH_miss": 0.0, "dlog": 0.1})
    check("10-Q 무효(분리 실패 · 형태 전환) → CH 0 · 결측 1", ftq[("C", "2018-09")] == {"CH": 0.0, "CH_miss": 1.0, "dlog": None}
          and ftq[("D", "2018-08")]["CH_miss"] == 1.0 and ftq[("A", "2018-06")]["dlog"] == 0.3)
    ftw, rtw = tenq_flags(days, J={"docs": docs}, world={("w%d" % j, "2017-05") for j in range(60)})
    check("10-Q 경계 — 세계 제한", abs(float(rtw["thr"]["2018"]) - float(np.quantile([d["SimRF"] for d in docs[:60]], 0.2))) < 1e-12)
    try:
        tenq_flags(days, J={"docs": [{"group_id": "x"}]})
        check("10-Q 필드 없으면 멈춘다", False)
    except SystemExit:
        check("10-Q 필드 없으면 멈춘다", True)

    # 10. 내부자 어댑터 — 세 모양이 같은 표지
    recs = [{"grp": "g1", "m": "2019-03", "os_n": 2, "rs_n": 0, "un_n": 0, "s_n": 2, "t1_os_n": 1},
            {"grp": "g2", "m": "2019-03", "os_n": 0, "rs_n": 1, "un_n": 3, "s_n": 4, "t1_os_n": 0}]
    a = ins_flags(J={"rows": recs})
    b = ins_flags(J={"cols": list(recs[0]), "rows": [list(r.values()) for r in recs]})
    c = ins_flags(J={"cells": {"g1": {"2019-03": {"os_n": 2, "rs_n": 0, "un_n": 0, "s_n": 2, "t1_os_n": 1}},
                               "g2": {"2019-03": {"os_n": 0, "rs_n": 1, "un_n": 3, "s_n": 4, "t1_os_n": 0}}}})
    check("내부자 어댑터 — 모양 셋 같음 · OS/RS/SALL · T4 옛 모양 대체식 · 그 밖 칸", a == b == c and a[("g1", "2019-03")] ==
          {"OS": 1.0, "RS": 0.0, "OS_T4": 1.0, "RS_T4": 0.0, "SALL": 1.0, "d:t1_os_n": 1.0} and a[("g2", "2019-03")]["OS_T4"] == 1.0
          and a[("g2", "2019-03")]["OS"] == 0.0 and not _has(a, "OS_T2") and any("T4" in x for x in a.notes))
    # 10a. 정본 쌍둥이 칸(cikmonth_doc — t1_os3 · t2_* · t4_* · t6_* · os_na · rs_na)
    ct = {"months_ok": ["2019-03"], "groups": {
        "g1": {"2019-03": {"O": 0, "R": 1, "U": 1, "all": 2, "t1_os3": 1, "t1c_os3": 0, "t2_os_n": 0, "t2_rs_n": 1, "t4_os_n": 0, "t4_rs_n": 1,
                           "t4_os_na": 0, "t4_rs_na": 0, "t6_os_n": 2, "t6_rs_n": 0, "os_na": 0, "rs_na": 0}},
        "g2": {"2019-03": {"N": 1, "all": 1, "t1_os3": None, "t2_os_n": 0, "t4_os_n": 0, "t4_os_na": 1, "os_na": 1, "rs_na": 1}},
        "g3": {"2019-03": {"O": 1, "all": 1, "t4_os_n": 1, "t6_os_n": 1}}}}
    ft = ins_flags(J=ct)
    r1_, r2_, r3_ = ft[("g1", "2019-03")], ft[("g2", "2019-03")], ft[("g3", "2019-03")]
    check("쌍둥이 칸 — T4 는 t4_* 를 그대로(O+U 아님) · T1 null = 모름 · T2/T6 모름은 1차 os_na", r1_["OS_T4"] == 0.0 and r1_["RS_T4"] == 1.0
          and r1_["OS_T1"] == 1.0 and r1_["OS_T2"] == 0.0 and r1_["RS_T2"] == 1.0 and r1_["OS_T6"] == 1.0 and r1_["RS_T6"] == 0.0
          and r2_["OS_T1"] is None and r2_["OS_T4"] is None and r2_["OS_T2"] is None and r2_["OS"] is None and r2_["RS_T6"] is None
          and r3_["OS_T1"] == 0.0 and r3_["OS_T4"] == 1.0 and r3_["OS_T2"] == 0.0 and not ft.notes
          and r1_["OS_T1C"] == 0.0 and r2_["OS_T1C"] == 0.0,
          "g1 %s" % {k2: r1_[k2] for k2 in ("OS_T1", "OS_T2", "RS_T2", "OS_T4", "RS_T4", "OS_T6")})
    try:
        ins_flags(J={"rows": [{"grp": "g1", "m": "2019-03", "opp": 1}]})
        check("내부자 필드 없으면 멈춘다", False)
    except SystemExit:
        check("내부자 필드 없으면 멈춘다", True)

    # 10b. 정본 cikmonth(희소 · months_ok · N = 모름) — r_r1_flags.Flags.dummy 와 같은 뜻인지 정본 함수로 대조
    cm = {"variant": "primary", "months_ok": ["2019-03", "2019-04"],
          "groups": {"g1": {"2019-03": {"O": 2, "all": 2, "sO": 2}}, "g2": {"2019-03": {"R": 1, "N": 1, "all": 2}},
                     "g3": {"2019-03": {"U": 1, "all": 1, "bO": 1}}, "g4": {"2019-03": {"N": 2, "all": 2}},
                     "g5": {"2019-03": {"bR": 1}}, "g6": {"2019-04": {"O": 1, "R": 1, "U": 2, "all": 4}}}}
    fc = ins_flags(J=cm)
    agree = None
    R1F = sib("r_r1_flags")
    if R1F is not None:
        import collections as _co

        class _Fk:
            pass
        agree = True
        for u_as_o in (False, True):
            fk = _Fk()
            fk.months_ok, fk.spec = set(cm["months_ok"]), {"u_as_o": u_as_o}
            for g, bym in cm["groups"].items():
                for ym, cnt in bym.items():
                    fk.counts = (lambda c: (lambda gid, y: _co.Counter(c)))(cnt)
                    for kind, mine in (("OS", "OS_T4" if u_as_o else "OS"), ("RS", "RS"), ("ALL", "SALL"), ("MASK", "CLS")):
                        if kind != "OS" and u_as_o:
                            continue
                        ref = R1F.Flags.dummy(fk, g, ym, kind)
                        my = fc[(g, ym)][mine]
                        agree &= (ref is None and my is None) or (ref is not None and my is not None and float(ref) == my)
    check("정본 cikmonth — 희소 칸 · N 모름 · months_ok", fc[("g2", "2019-03")]["OS"] is None
          and fc[("g2", "2019-03")]["RS"] == 1.0 and fc[("g5", "2019-03")]["CLS"] == 1.0 and fc.months_ok == {"2019-03", "2019-04"}
          and fc[("g1", "2019-03")]["d:sO"] == 1.0)
    if agree is None:
        skip("정본 대조 r_r1_flags.Flags.dummy", "r_r1_flags 를 import 할 수 없다(이 파일 옆에 복사할 것)")
    else:
        check("정본 대조 r_r1_flags.Flags.dummy(OS · RS · ALL · MASK · u_as_o)", agree is True)
    Pk, rk_ = _synth(seed=97, T=4)
    fpk = FlagPanel(_merge(_bern_flags(Pk, rk_, "OS", .1), _bern_flags(Pk, rk_, "RS", .05)), months_ok=Pk["months"][1:])
    D0 = Pk["m"][Pk["months"][2]]
    fpk[(D0["grp"][0], Pk["months"][2])] = {"OS": None, "RS": 0.0}
    _set_y(Pk, fpk, 4.0, rk_, lambda D, m: 0.0)
    yk, ck, flk, _, _ = _design(D0, fpk, Pk["months"][2], 0, SPECS["R1"])
    rk2 = fm(Pk, fpk, SPECS["R1"], Pk["months"][2:])
    v_out = _flag_vec(D0, fpk, Pk["months"][2], 2, "OS")
    check("모름 — 0 + <표지>_unk 더미 · months_ok 밖 달은 NaN", "OS_unk" in dict(ck) and dict(flk)["OS"][0] == 0.0
          and np.isnan(v_out).all() and rk2["unk"]["OS"][Pk["months"][2]] >= 1)
    R2F = sib("r_r2flags")
    ok_keys = (set(FIELDS["r2_gm"].values()) <= set(R2F.GM_EMPTY)) if R2F is not None else None
    f2 = r2_flags({"metric": "rf", "gm": {("g1", "2019-06"): {"ch": 1, "miss": 0, "dlog_raw": 0.2},
                                          ("g2", "2019-06"): {"ch": 0, "miss": 1, "dlog_raw": None}}})
    check("R2 정본 어댑터(r2_build gm → CH · CH_miss · dlog)", f2[("g1", "2019-06")] == {"CH": 1.0, "CH_miss": 0.0, "dlog": 0.2}
          and f2[("g2", "2019-06")]["CH_miss"] == 1.0)
    if ok_keys is None:
        skip("R2 정본 칸 이름(r_r2flags.GM_EMPTY)", "r_r2flags 를 import 할 수 없다(이 파일 옆에 복사할 것)")
    else:
        check("R2 정본 칸 이름 ⊂ r_r2flags.GM_EMPTY", ok_keys is True)
    # 10c. 정본을 못 부르면 멈춘다(ImportError 만 · RBATCH_PROVISIONAL=1 이고 등록 러너가 아닐 때만 None)
    old = {k2: os.environ.pop(k2, None) for k2 in ("RBATCH_COMMIT", "RBATCH_P0", "RBATCH_PROVISIONAL")}
    res_g = []
    try:
        for env in ({}, {"RBATCH_PROVISIONAL": "1"}, {"RBATCH_PROVISIONAL": "1", "RBATCH_COMMIT": "x"}):
            os.environ.update(env)
            try:
                res_g.append(_canon_mod("r_stagem_no_such_module_"))
            except SystemExit:
                res_g.append("stop")
            for k2 in env:
                os.environ.pop(k2, None)
    finally:
        for k2, v in old.items():
            if v is not None:
                os.environ[k2] = v
    check("정본 import 가드 — 기본 멈춤 · PROVISIONAL=1 만 None · COMMIT 과 함께면 멈춤", res_g == ["stop", None, "stop"], str(res_g))
    # 10d. 경계 빈 해 — 창 [2016-08, 2026-07] 의 CH 창은 2016-06 공개분부터 닿는다
    Bg = {y: {"cut": 0.9, "n": 1000} for y in range(2016, 2027)}
    Bg2 = {**Bg, 2016: {"cut": None, "n": 0}}
    check("경계 빈 해 점검(bounds_gap)", bounds_gap(Bg) == [] and bounds_gap(Bg2) == [2016] and bounds_gap({str(y): 0.9 for y in range(2017, 2027)}) == [2016]
          and bounds_gap({y: v for y, v in Bg.items() if y != 2026}) == [2026])

    # 10e. 정본 R2 감싸기(tenq_canonical · r2_variants) — 합성 10-Q 파일. 경계 세계가 2015 부터면 2016 경계가 서고,
    #      2015 달을 덮으면서 2015 짝을 하나도 담지 않는 세계면 2016 경계가 없어 멈춘다(bounds_gap — 검토 지적의 가드)
    if R2F is None:
        skip("정본 R2 감싸기(tenq_canonical)", "r_r2flags 를 import 할 수 없다(이 파일 옆에 복사할 것)")
    else:
        import shutil, tempfile
        rng4 = np.random.default_rng(44)
        docs4 = []
        for gi in range(30):
            for y in range(2014, 2018):
                for qm, rdd in ((5, "03-31"), (8, "06-30"), (11, "09-30")):
                    sv_ = float(rng4.uniform(0.6, 1.0))
                    docs4.append({"acc": "%010d-%02d-%06d" % (gi, y % 100, qm), "gid": "g%d" % gi, "form": "10-Q", "rd": "%d-%s" % (y, rdd),
                                  "acceptanceDateTime": "%d-%02d-10T14:00:00Z" % (y, qm), "shape": "F", "parse_status": "ok",
                                  "SimRF": sv_, "SimDoc": float(rng4.uniform(0.8, 1.0)), "n_words_rf": 1000 + gi,
                                  # 등록 형태 판 v3 열(r_r2flags.REG_SHAPE_VER · 2026-09-26) — 같은 값
                                  "shape_v3": "F", "parse_status_v3": "ok", "SimRF_v3": sv_})
        tmpd = tempfile.mkdtemp()
        try:
            tp, nim = os.path.join(tmpd, "tenq.json"), os.path.join(tmpd, "no_map.json")
            with io.open(tp, "w", encoding="utf-8") as fh:
                json.dump({"docs": docs4}, fh)
            W15 = {("g%d" % gi, mm) for gi in range(30) for mm in months_between(BOUND_FROM, "2017-12")}
            W16 = {kk for kk in W15 if kk[1] >= "2016-01"} | {("gX", mm) for mm in months_between(BOUND_FROM, "2015-12")}
            win = ("2016-08", "2017-07")
            fpc, Rc = tenq_canonical(tp, world=W15, im_path=nim, window=win)
            try:
                tenq_canonical(tp, world=W16, im_path=nim, window=win)
                stopped = False
            except SystemExit:
                stopped = True
            vv = r2_variants(tp, W15, nim, window=win)
        finally:
            shutil.rmtree(tmpd, ignore_errors=True)
        check("정본 R2 감싸기 — 2015 부터 세계면 2016 경계 · 2015 짝 없는 세계면 멈춤 · 판 넷 · src 에 정본 sha",
              Rc["bounds"][2016]["cut"] is not None and Rc["bounds"][2016]["n"] == 90 and stopped and fpc.src.startswith("r_r2flags:rf@")
              and set(vv) == {"rf", "doc", "ixbrl", "covid"} and vv["doc"].src.startswith("r_r2flags:doc@")
              and vv["covid"].src.endswith(":excl_covid") and _has(fpc, "CH"),
              "2016 경계 n %s · 멈춤 %s · %s" % (Rc["bounds"][2016]["n"], stopped, fpc.src))

    # 11. Holm · P0 · σ 문턱(카드 원문의 수)
    c2, c1 = td.ppf(1 - 0.0125, 119), td.ppf(1 - 0.025, 119)
    check("Holm 임계 t(119) 2.27 → 1.98", abs(c2 - 2.27) < 0.005 and abs(c1 - 1.98) < 0.005, "%.3f · %.3f" % (c2, c1))
    h = holm({"R1": (-2.1, 120), "R2": (-2.4, 120)}, 2)
    check("Holm 계단(R2 먼저 2.27 통과 → R1 1.98 통과)", h["R2"]["pass"] and h["R1"]["pass"] and abs(h["R1"]["crit"] - c1) < 1e-9)
    h = holm({"R1": (-2.1, 120), "R2": (-2.2, 120)}, 2)
    check("Holm 계단(첫 단계 실패면 둘 다 실패)", not h["R1"]["pass"] and not h["R2"]["pass"])
    try:
        holm({"R1": (-3.0, 120)}, 2)
        check("Holm m 고정(가족 크기가 다르면 멈춘다)", False)
    except ValueError:
        check("Holm m 고정(가족 크기가 다르면 멈춘다)", True)
    want = [(-0.55, 1.2, 0.245), (-0.55, 1.8, 0.118), (-0.80, 1.2, 0.37), (-0.80, 1.8, 0.23), (-0.80, 2.4, 0.14)]
    got = [p0(g, s, 120)[0] for g, s, _ in want]
    check("P0 = 카드 원문 값", all(abs(x - w[2]) < 0.006 for x, w in zip(got, want)), " · ".join("%.3f" % x for x in got))
    sg = [sigma_gate(-0.55, 120), sigma_gate(-0.80, 120), sigma_gate(-0.55, 84), sigma_gate(-0.80, 84)]
    check("σ 문턱 1.58 · 2.30 · 1.32 · 1.93", all(abs(x - w) < 0.006 for x, w in zip(sg, (1.58, 2.30, 1.32, 1.93))),
          " · ".join("%.3f" % x for x in sg))

    # 12. 관문 함수
    mk = lambda **g: {"g": {k2: v for k2, v in g.items()}}
    g1 = gates_r1(mk(OS=[-1.0, -0.2], RS=[0.1, 0.0]), mk(OS=[-0.1, -0.1]), mk(OS=[0.2, -0.1]))
    check("관문 R1 (i)(ii) 참 · (iii) 거짓 → all 거짓", g1["i"] and g1["ii"] and not g1["iii"] and not g1["all"])
    g2 = gates_r2(mk(CH=[-0.5], CH_miss=[-0.9]), mk(CH=[-0.1]), mk(CH=[-0.2]))
    check("관문 R2 all 참 · 분리 실패 오염 표시", g2["all"] and g2["contam"])
    check("판정 — 자격 없으면 측정", verdict(False, {"pass": True}, g2)["class"] == "measure" and verdict(True, {"pass": True}, g2)["pass"])
    vm, vf = verdict(True, {"pass": True}, g2, measure_only=True), verdict(True, {"pass": True}, g2, f0_ok=False)
    check("판정 — 커버리지 T < 84 · 표지 F0 실패면 측정", vm["class"] == "measure" and vm["why"] == ["coverage_T<84"]
          and vf["class"] == "measure" and vf["why"] == ["flag_F0"] and verdict(True, {"pass": True}, g2, False, True)["class"] == "primary")
    g1n = gates_r1(mk(OS=[-1.0, -0.2], RS=[0.1, 0.0]), mk(OS=[-0.1, -0.1]), mk(OS=[-0.2, -0.1]), rs_f0_ok=False)
    g1y = gates_r1(mk(OS=[-1.0, -0.2], RS=[0.1, 0.0]), mk(OS=[-0.1, -0.1]), mk(OS=[-0.2, -0.1]), rs_f0_ok=True)
    check("관문 R1 (i) — RS 밀도 F0 실패면 판정 불가(거짓)", not g1n["i"] and g1n["i_na"] and not g1n["all"] and g1y["all"] and not g1y["i_na"])
    # 12b. NW t — 이어진 달은 eg30plus.nw_t 그대로 · 빈 달이 끼면 달력 시차(nw_t_gap)
    rng3 = np.random.default_rng(5)
    ms60 = months_between("2016-08", mshift("2016-08", 59))
    x60 = rng3.normal(-0.2, 1.0, 60) + np.convolve(rng3.normal(0, .6, 62), [1, 1, 1], "valid")[:60]
    same = abs(nw_t_gap(ms60, x60) - E.nw_t(x60, 3)) < 1e-12
    hole = [j for j in range(60) if j not in (10, 11, 30)]
    rg = {"months": [ms60[j] for j in hole], "g": {"X": [float(x60[j]) for j in hole]}}
    sg_ = summarize(rg, "X")
    xs = x60[hole]
    e = np.zeros(60)
    e[hole] = xs - xs.mean()
    s_ = (e @ e) / 57 + sum(2 * (1 - L / 4) * (e[L:] @ e[:-L]) / 57 for L in (1, 2, 3))
    man = xs.mean() / math.sqrt(s_ / 57)
    rc = {"months": ms60, "g": {"X": [float(v) for v in x60]}}
    check("NW t — 이어지면 eg30plus.nw_t · 빈 달 3 이면 달력 시차판(손 계산과 같다)", same and summarize(rc, "X")["contiguous"]
          and summarize(rc, "X")["nw_t"] == E.nw_t(x60, 3) and sg_["gaps"] == 3 and not sg_["contiguous"]
          and abs(sg_["nw_t"] - man) < 1e-12 and abs(sg_["nw_t_compressed"] - E.nw_t(xs, 3)) < 1e-12 and sg_["nw_t"] != sg_["nw_t_compressed"],
          "빈 달판 %.4f · 압축판 %.4f" % (sg_["nw_t"], sg_["nw_t_compressed"]))

    # 13. P0 σ — 위약 SD ≈ 분석적 σ(단일 회귀 사양) · 평균을 내지 않는다
    P, rng = _synth(seed=81, T=60)
    fp = _bern_flags(P, rng, "CH", 0.10)
    _set_y(P, fp, 5.0, rng, lambda D, m: 0.0)
    SC = dict(SPECS["R2"], flags=("CH",))
    sa = sigma_analytic(P, fp, SC)
    sp = sigma_placebo(P, fp, SC, reps=40)
    check("위약 SD 중앙값 ≈ 분석적 σ", 0.8 < sp["sd_median"] / sa["sigma"] < 1.25 and "mean" not in sp,
          "분석 %.3f · 위약 중앙 %.3f · 90분위 %.3f" % (sa["sigma"], sp["sd_median"], sp["sigma"]))
    fpx = _bern_flags(P, rng, "CH", 0.10)
    sp2 = sigma_placebo(P, fpx, SC, reps=3)
    sp3 = sigma_placebo(P, fpx, SC, reps=3)
    check("위약 씨앗 고정(재현)", sp2 == sp3)

    # 13b. JT 사양 · 지속성 있는 표지(마르코프 머무름 0.8) — 위약 SD 가 귀무 아래 실제 JT γ 계열 SD 와 맞는다
    #      (시차마다 독립 추출이던 옛 판은 0.65 배 — 검토 지적)
    def markov(P_, rng_, name, pi=0.08, stay=0.8, pre=2):
        ms = [mshift(P_["months"][0], -j) for j in range(pre, 0, -1)] + P_["months"]
        groups = sorted({g for m_ in P_["months"] for g in P_["m"][m_]["grp"]}, key=lambda s_: int(s_[1:]))
        stt = {g: rng_.random() < pi for g in groups}
        q_ = pi * (1 - stay) / (1 - pi)
        out_ = {}
        for m_ in ms:
            for g in groups:
                stt[g] = (rng_.random() < stay) if stt[g] else (rng_.random() < q_)
                if stt[g]:
                    out_[(g, m_)] = {name: 1.0}
        return out_
    rat = []
    SJ = dict(SPECS["R1"], flags=("OS",))
    for sd_ in (0, 1):
        Pm, rm = _synth(seed=130 + sd_, T=120)
        fmk = markov(Pm, rm, "OS")
        sdr = []
        for rep in range(3):                       # 참 귀무 SD — 같은 표지 · y 를 세 번 새로 뽑아 평균(한 번이면 SD 추정 잡음이 6% 쯤)
            _set_y(Pm, fmk, 5.0, np.random.default_rng(7000 + 10 * sd_ + rep), lambda D, m: 0.0)
            sdr.append(np.array([v for v in fm(Pm, fmk, SJ)["g"]["OS"] if v is not None]).std(ddof=1))
        spm = sigma_placebo(Pm, fmk, SJ, reps=20)
        rat.append(spm["sd_median"] / float(np.mean(sdr)))
    check("위약 — 지속성 있는 표지(머무름 0.8)에서 JT SD 를 맞춘다(순열이 시차 이력을 옮긴다)", all(0.85 < r_ < 1.18 for r_ in rat),
          "위약 ÷ 귀무 실제 SD %s(옛 시차별 독립 추출은 0.65)" % " · ".join("%.2f" % r_ for r_ in rat))

    # 14. 합동 회귀(T5) — 월 고정효과 · 군집 SE
    P, rng = _synth(seed=91, T=60)
    fp = _merge(_bern_flags(P, rng, "OS", 0.08), _bern_flags(P, rng, "RS", 0.05))
    _set_y(P, fp, 4.0, rng, lambda D, m: -0.7 * _flag_vec(D, fp, m, 0, "OS") + rng.normal(0, 2) )
    pf = pooled_fe(P, fp, SPECS["R1"])
    b_, t_ = pf["coef"]["OS"]["b"], pf["coef"]["OS"]["t"]
    check("합동 회귀 회복(−0.7 · 4 SE 안)", abs(b_ + 0.7) < 4 * abs(b_ / t_) and t_ < -5, "b %.3f · t %.1f · G %d" % (b_, t_, pf["G"]))
    # 정확성 — 달 더미를 명시한 전체 설계 lstsq 와 같은 계수
    sub = P["months"][:4]
    pf4 = pooled_fe(P, fp, SPECS["R1"], sub)
    Ys, Xs, names = [], [], None
    for j, mm in enumerate(sub):
        y, cols, fl, _, _ = _design(P["m"][mm], fp, mm, 0, SPECS["R1"])
        cd = dict(cols)
        names = names or [nm for nm, _ in cols if nm != "const"]
        md = [np.full(len(y), float(j == q)) for q in range(len(sub))]
        Xs.append(np.column_stack([cd.get(nm, np.zeros(len(y))) for nm in names] + md + [v for _, v in fl]))
        Ys.append(y)
    Xf = np.vstack(Xs)
    _, kf_, _ = _gs([("c%d" % j, Xf[:, j]) for j in range(Xf.shape[1])])
    keep = [int(c[1:]) for c in kf_]
    bf = np.linalg.lstsq(Xf[:, keep], np.concatenate(Ys), rcond=None)[0]
    check("합동 회귀 = 달 더미 명시 lstsq", abs(pf4["coef"]["OS"]["b"] - bf[-2]) < 1e-8 and abs(pf4["coef"]["RS"]["b"] - bf[-1]) < 1e-8,
          "차 %.1e" % abs(pf4["coef"]["OS"]["b"] - bf[-2]))

    # 14b. 카드 한 벌(stage_m_r1 · stage_m_r2) — 합성 연기 시험(모양 · 관문 키)
    Pq, rq = _synth(seed=95, T=24, m0="2022-08")
    fl_all = (("OS", .08), ("RS", .05), ("SALL", .15), ("OS_T4", .10), ("RS_T4", .05), ("CLS", .6), ("OS_T1", .1), ("OS_T1C", .1),
              ("OS_T2", .07), ("RS_T2", .05), ("OS_T6", .09), ("RS_T6", .05))
    fi = _merge(*(_bern_flags(Pq, rq, f, pr) for f, pr in fl_all))
    _set_y(Pq, fi, 4.0, rq, lambda D, m: 0.0)
    o1 = stage_m_r1(Pq, fi, Pq["months"], rs_f0_ok=True)
    ran1 = {r["id"].split(".")[1] for r in o1["trials"] if r["run"]}
    miss1 = {r["id"].split(".")[1] for r in o1["trials"] if not r["run"]}
    fi2 = {k2: {f: v for f, v in rec.items() if not f.endswith(("_T2", "_T6"))} for k2, rec in fi.items()}
    o1b = stage_m_r1(Pq, fi2, Pq["months"])
    miss1b = {r["id"].split(".")[1]: r["missing"] for r in o1b["trials"] if not r["run"]}
    ftq2 = _merge(_bern_flags(Pq, rq, "CH", .12), _bern_flags(Pq, rq, "CH_miss", .03))
    for key in list(ftq2)[::2]:
        ftq2[key]["dlog"] = float(rq.normal(0, .2))
    o2 = stage_m_r2(Pq, ftq2, Pq["months"], fp_doc=ftq2, fp_ixbrl=ftq2)
    ran2 = {r["id"].split(".")[1] for r in o2["trials"] if r["run"]}
    miss2 = {r["id"].split(".")[1] for r in o2["trials"] if not r["run"]}
    check("카드 한 벌 R1 — controls 목록 그대로(+ 선언된 민감도 T1C) · 시도 목록 · T2 분할", ran1 == {"main", "extra", "wls", "inter", "sall", "t1",
          "t1c", "t2", "t3", "t4", "t5", "t6", "sens2020"} and miss1 == {"sens2014"} and set(o1["gates"]) >= {"i", "ii", "iii", "all"}
          and o1["t2"]["split"]["pre"]["OS_T2"]["T"] + o1["t2"]["split"]["post"]["OS_T2"]["T"] == o1["t2"]["sum"]["OS_T2"]["T"]
          and o1["sens2020"]["sum"]["OS"]["T"] == 24 and set(miss1b) == {"t2", "t6", "sens2014"} and miss1b["t2"] == ["OS_T2", "RS_T2"],
          "돌림 %d · 못 돌림 %s" % (len(ran1), sorted(miss1)))
    check("카드 한 벌 R2 — 상호작용 없음 · SimDoc · 진단 둘 · 민감도 · 판이 없으면 못 돌린 시도",
          ran2 == {"main", "wls", "len", "simdoc", "diag_ixbrl", "sens2020"} and miss2 == {"diag_covid", "sens2014"} and "inter" not in o2
          and set(o2["gates"]) >= {"i", "ii", "contam", "all"} and o2["len"]["drop"].get("dlog", 0) == 0 and len(o2["main"]["months"]) == 24,
          "돌림 %s · 못 돌림 %s" % (sorted(ran2), sorted(miss2)))

    # 15. 실제 패널 가드 · F0 밀도 · 커버리지
    P["kind"] = "real"
    for fn, what in ((lambda: fm(P, fp, SPECS["R1"]), "fm"), (lambda: sigma_analytic(P, fp, SPECS["R1"]), "p0")):
        old = {k2: os.environ.pop(k2, None) for k2 in ("RBATCH_COMMIT", "RBATCH_P0")}
        try:
            fn()
            check("실제 패널 가드(%s)" % what, False)
        except SystemExit:
            check("실제 패널 가드(%s)" % what, True)
        finally:
            for k2, v in old.items():
                if v is not None:
                    os.environ[k2] = v
    P["kind"] = "synth"
    dd = f0_density(P, fp, "OS")
    check("F0 밀도(OS 중앙값 · 최소 · 문턱)", dd["ok"] and dd["min"] >= 5, "중앙값 %.0f · 최소 %d" % (dd["median"], dd["min"]))
    for j, m in enumerate(P["months"]):
        P["stat"][m] = {"cov_n": 0.95 if j % 7 else 0.85, "cov_cap": 0.97, "im_ok": True}
    cv = f0_coverage(P)
    check("커버리지 F0 — 실패 달 제외 · T < 84 면 측정", cv["T"] == 60 - len([j for j in range(60) if j % 7 == 0]) and cv["measure_only"])
    d1 = panel_digest(P)
    P["m"][P["months"][0]]["y"][0] = 99.0
    d2, d3 = panel_digest(P), panel_digest(P, with_y=True)
    P["m"][P["months"][0]]["size"][0] += 1e-3
    check("패널 해시 — y 를 바꿔도 같고 통제를 바꾸면 달라진다", d1 == d2 and d3 != d2 and panel_digest(P) != d1)

    # 16. 발행사 지도(파일이 있으면 · 조회만)
    ip = os.path.join(RDATA, FIELDS["issuer_map"]["file"])
    if os.path.exists(ip):
        IM = IssuerMap(ip)
        a1, a2, a3, a4 = IM.at("AAPL", "2020-01"), IM.at("BRK-B", "2020-01"), IM.at("DIS", "2019-01"), IM.at("DIS", "2019-06")
        check("지도 조회(AAPL · BRK-B 점 표기 · DIS 재편 — 한 그룹 · 주 CIK 바뀜)", a1["grp"] == "g320193" and a2 and a2["grp"] == "g1067983"
              and a3["grp"] == a4["grp"] and a3["cik"] != a4["cik"] and IM.month_ok("2020-01") is True,
              "%s · %s · DIS %s %s→%s" % (a1["grp"], a2["grp"], a3["grp"], a3["cik"], a4["cik"]))
        rg_ = {}
        for t, m in (("IR", "2020-03"), ("FOXA", "2019-03"), ("JCI", "2016-09")):
            a_ = IM.at(t, m)
            gl_, fo_ = _glag(IM, t, m, a_)
            rg_[t] = (gl_ == [a_["grp"]] * 3, len(fo_))
        check("티커 재사용 회귀(IR 2020-03 · FOXA 2019-03 · JCI 2016-09) — 시차도 지금 그룹 · 옛 그룹은 foreign 으로",
              all(ok and nf == 2 for ok, nf in rg_.values()), str(rg_))
    else:
        skip("지도 조회 · 티커 재사용 회귀", "발행사 지도 없음(%s)" % ip)
    # 17. 시총 가격 판 — 원 종가가 서면 raw · 비면 배당조정 대체(adj_fallback) · 파일이 없으면 adj
    class _Wk:
        PX = {"A": np.array([10.0, 11.0, np.nan])}
    rawk = {"A": np.array([15.0, np.nan, np.nan])}
    check("시총 가격 판(_cap_px)", _cap_px(_Wk, rawk, "A", 0) == (15.0, "raw") and _cap_px(_Wk, rawk, "A", 1) == (11.0, "adj_fallback")
          and _cap_px(_Wk, None, "A", 1) == (11.0, "adj") and _cap_px(_Wk, rawk, "A", 2) == (None, "adj_fallback"))
    IMs = IssuerMap(J={"tm": {"X.Y": [["2016-01", "2018-12", "gA", 1, [1], 0, "dera", 0], ["2019-01", "2026-09", None, None, [], None, "conflict", None]]},
                       "f0": {"by_month": {"2016-01": [10, 0, 0.0], "2016-02": [10, 1, 0.1]}}})
    check("지도 어댑터(합성) — '-' 표기 · 못 푼 달 · F0", IMs.at("X-Y", "2017-05")["grp"] == "gA" and IMs.at("X-Y", "2019-05")["grp"] is None
          and IMs.at("X-Y", "2015-05") is None and IMs.month_ok("2016-01") is True and IMs.month_ok("2016-02") is False and IMs.month_ok("2016-03") is None)

    # 18. 2026-09-26 등록 전 결정 — 지도 등록 FPI 칸 · 위반 멤버-월 · 펀드 CIK 출처 · 신선도 550일 · y 규칙 · 섹터 출처
    tmx = {"AAA": [["2017-01", "2017-12", "gA", 1, [1], 1, "dera", 0]], "BR.K": [["2017-01", "2017-12", "gB", 2, [2], 0, "dera", 0]]}
    IMf = IssuerMap(J={"tm": tmx, "fpi_registered": {"field": "fpi_q", "tm_index": 7},
                       "f0": {"by_month": {}, "violations": [["BR.K", "2017-05", "gB", 2, 0]]}})
    IMo = IssuerMap(J={"tm": tmx})
    check("지도 등록 FPI 칸(fpi_registered.tm_index) · 위반 멤버-월", IMf.at("AAA", "2017-06")["fpi"] == 0
          and IMf.at("AAA", "2017-06")["fpi_spec"] == 1 and IMo.at("AAA", "2017-06")["fpi"] == 1 and IMf.fpi_index == 7
          and IMo.fpi_index == 5 and IMf.violated("BR-K", "2017-05") and not IMf.violated("BR-K", "2017-06") and not IMo.violated("BR-K", "2017-05"))
    import tech_backtest as _TB

    class _Wf:
        W = {"FUND": {"AAA": {"sh": [("2019-03-31", 100.0), ("2016-12-31", 90.0)], "eq": [("2019-03-31", -5.0)]},
                      "RNG": {"sh": [("2019-06-30", 10.0), ("2018-06-30", 9.0)], "eq": [("2019-06-30", 1.0)]},
                      "NOC": {"sh": [("2019-03-31", 7.0)]}}}
    FCs = FundCik(files=[{"t": "AAA", "cik": 1, "ciks": [[1, "2010-03-31", "2026-06-30", 40, "A"]]},
                         {"t": "RNG", "cik": 9, "cik_ranges": [[7, None, "2018-12-31"], [9, "2019-01-01", None]]},
                         {"t": "NOC", "cik": 3}, {"t": "OVL", "cik": 9, "ciks": [[8, "2010-03-31", "2019-06-30", 9, "old"],
                                                                                   [9, "2019-03-31", "2026-06-30", 9, "new"]]}])
    fc = lambda t, d, f, c: fresh_consistent(_Wf, FCs, t, t, d, f, c)
    check("커버리지 성분 — 신선도 550일 · 펀드 CIK(cik_ranges → cik → 모름) · 장부가 ≤ 0 허용",
          FRESH_DAYS == _TB.TTM_STALE_DAYS and fc("AAA", "2019-08-30", "sh", [1]) == (100.0, "ok")
          and fc("AAA", "2020-11-30", "sh", [1]) == (None, "stale") and fc("AAA", "2019-08-30", "sh", [5]) == (None, "cik")
          and fc("AAA", "2019-08-30", "eq", [1]) == (-5.0, "ok") and fc("RNG", "2018-11-30", "sh", [9]) == (None, "cik")
          and fc("RNG", "2018-11-30", "sh", [7]) == (9.0, "ok") and fc("RNG", "2019-10-31", "sh", [9]) == (10.0, "ok")
          and fc("NOC", "2019-08-30", "sh", [3]) == (None, "cik") and fc("ZZZ", "2019-08-30", "sh", [1]) == (None, "none")
          and FCs.cik_of("RNG", "2018-12-31") == {7} and FCs.cik_of("RNG", "2019-01-01") == {9} and FCs.cik_of("NOC", "2019-01-01") is None
          and FCs.cik_of("OVL", "2019-06-30") == {8, 9} and FCs.cik_of("OVL", "2009-12-31") is None
          and FCs.cik_of("AAA", "2026-09-30") is None and FCs.stat["with_ranges"] == 3 and FCs.stat["multi_cik"] == 2)
    # 야후 앞 채움(yf_backfill_date · 2026-09-26 BHGE) — 첫 야후 관측 2019-10-24 를 630일 앞(2018-02-01)에 둔 줄은 원 관측일에 본다 ·
    # 앞 채움 날짜와 첫 야후 관측 사이에 다른 관측(SEC)이 있으면 앞 채움이 아니다(그대로 쓴다)
    _YF_FIRST.update({"BFY": ("2018-02-01", "2019-10-24"), "BFN": ("2018-02-01", "2019-10-24")})
    _Wf.W["FUND"].update({"BFY": {"sh": [("2019-11-05", 101.0), ("2019-10-24", 102.6), ("2018-02-01", 102.6)]},
                          "BFN": {"sh": [("2019-10-24", 102.6), ("2018-12-31", 99.0), ("2018-02-01", 50.0)]}})
    FCb = FundCik(files=[{"t": "BFY", "cik": 4, "ciks": [[4, "2010-03-31", "2026-06-30", 9, "A"]]},
                         {"t": "BFN", "cik": 4, "ciks": [[4, "2010-03-31", "2026-06-30", 9, "A"]]}])
    fb = lambda t, d: fresh_consistent(_Wf, FCb, t, t, d, "sh", [4])
    check("야후 앞 채움 관측은 원 관측일에 본다(2018-05..2019-09 에 없음 · 2020-01 부터 첫 관측) · SEC 가 끼면 앞 채움 아님",
          yf_backfill_date("BFY", _Wf.W["FUND"]["BFY"]["sh"]) == "2018-02-01"
          and yf_backfill_date("BFN", _Wf.W["FUND"]["BFN"]["sh"]) is None
          and fb("BFY", "2018-05-31") == (None, "none") and fb("BFY", "2019-07-31") == (None, "none")
          and fb("BFY", "2020-01-31") == (102.6, "ok") and fb("BFN", "2018-06-29") == (50.0, "ok")
          and fb("BFN", "2019-07-31") == (99.0, "ok"))
    for _k in ("BFY", "BFN"):
        _YF_FIRST.pop(_k, None)
        _Wf.W["FUND"].pop(_k, None)
    dd_ = ["d%02d" % j for j in range(12)]
    nan = float("nan")
    arr = lambda *v: np.array([nan if x is None else float(x) for x in v])
    YTs = {("E", "d05"): "delisted", ("K", "d05"): "kept_trading"}
    ok_y = (y_rule(arr(10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21), 2, 6, "F", dd_, YTs)[:2] == ((16 / 12 - 1) * 100, "full")
            and y_rule(arr(10, 11, 12, 13, 14, 15, None, 17, 18, 19, 20, 21), 2, 6, "G", dd_, YTs)[:2] == ((15 / 12 - 1) * 100, "gapcut")
            and y_rule(arr(10, 11, 12, 13, 14, 15, None, None, None, None, None, None), 2, 6, "E", dd_, YTs) == ((15 / 12 - 1) * 100, "delisted", "d05")
            and y_rule(arr(10, 11, 12, 13, 14, 15, None, None, None, None, None, None), 2, 6, "K", dd_, YTs) == (None, "kept_trading", "d05")
            and y_rule(arr(10, 11, 12, 13, 14, 15, None, None, None, None, None, None), 2, 6, "U", dd_, YTs) == (None, "unclassified", "d05")
            and y_rule(arr(10, 11, 12, None, None, None, None, 17, 18, 19, 20, 21), 2, 6, "G", dd_, YTs)[:2] == (0.0, "gap0")
            and y_rule(arr(10, 11, 12, None, None, None, None, None, None, None, None, None), 2, 6, "K", dd_, {("K", "d02"): "kept_trading"})
            == (None, "kept_trading", "d02"))
    check("보유월 y 규칙(y_rule) — 보통 · 끊김 · 상장폐지 · 거래 계속 · 판정 없음", ok_y)
    SAs = SectorAt.__new__(SectorAt)
    SAs.G = {"2017-05": {"sec": {"Financials": ["BR.K"], "Telecommunications Services": ["TT"], "": ["BL"]}}}
    SAs.man = {"BL": [("2017-01", "2017-12", "Health Care")], "NQ": [("2017-01", "2017-06", "Industrials")]}
    SAs.H, SAs.S, SAs._c = {"NQ": "Materials", "HX": "Energy"}, {"ST": "Utilities"}, {}
    check("섹터 출처(SectorAt = issuer_map.sector_src_at 규칙 · SEC_NORM)",
          SAs.src_at("BR-K", "2017-05") == ("Financials", "wiki_pit") and SAs.at("TT", "2017-05") == "Telecommunication Services"
          and SAs.src_at("BL", "2017-05") == ("Health Care", "manual") and SAs.src_at("NQ", "2017-05") == ("Industrials", "manual")
          and SAs.src_at("NQ", "2017-09") == ("Materials", "index_history") and SAs.src_at("ST", "2017-05") == ("Utilities", "stocks_today")
          and SAs.src_at("QQ", "2017-05") == (None, "none") and SAs.at("QQ", "2017-05") is None)

    print("r_stagem --selftest: %d 통과 · %d 실패 · %d 건너뜀%s%s" % (n_ok, len(fails), len(skipped),
          (" — 실패 " + ", ".join(fails)) if fails else "", (" — 건너뜀 " + ", ".join(skipped)) if skipped else ""))
    return 1 if fails else 0


def main() -> int:
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    if "--construct" in a:
        out = a[a.index("--out") + 1] if "--out" in a else None
        m0 = a[a.index("--from") + 1] if "--from" in a else M0
        m1 = a[a.index("--to") + 1] if "--to" in a else M1
        construct(out, m0, m1)
        return 0
    if "--ytrunc-scan" in a:                                # y 규칙 판정 대상(수익 없음) — 판정 없는 계열 끝이 있으면 종료 코드 1
        ov = [a[j + 1] for j, x in enumerate(a) if x == "--overlay"]
        Wd = load_world()
        added = overlay_px(Wd, ov)
        rows = ytrunc_scan(Wd, IssuerMap())
        miss = [r for r in rows if r["class"] is None]
        print(json.dumps({"overlay": ov, "overlay_keys": len(added), "px_overlay": Wd.px_overlay, "n": len(rows), "unclassified": miss},
                         ensure_ascii=False, indent=1))
        if "--out" in a:
            json.dump(rows, io.open(a[a.index("--out") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 1 if miss else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
