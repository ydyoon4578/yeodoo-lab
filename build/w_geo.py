# -*- coding: utf-8 -*-
"""build/w_geo.py — 배치 W 등록 B · W02 GEO-X(섹터를 가로지르는 지리 연결 전이): 본사 주소 패널(SEC 재무제표 자료집 sub.txt · 시점정확) ·
ZIP → CBSA(HUD-USPS 2016Q1 한 빈티지) · 동료 풀 · G 신호 · C 팔(발표 밀도 연속 θ) · CBSA 라벨 섞기(주 위약) · 3개월 평활 쌍둥이 ·
F0(커버리지 · 본사 이전 PIT 점검 · 상위 15 CBSA 몫 — 개수만) · SEC 접속 규약(w_frag 와 함께 쓴다).

설계 원본(구속): wbatch_research.json final.slate.strategies[W02] · common_frame(tier1_world «W02 동료 풀은 금융 포함» · buffer_fill «1개월 신호 카드는
  버퍼 없음 · 전량 체결» · costs «상태 의존 c_t = 10bp × max(1, σ_t/중앙값)» · G_NoEG_inputs · no_derivatives · c_arm_principle) · data_plan(edgar_address ·
  zip_cbsa · earnings_dates · coverage_gates_F0 · public_repo_rule) · registration(allowed_F0_decisions) · build_plan.modules[w_geo] ·
  갱신 2026-09-27(가 사용자 말 — 전방 원장 없음 · 나 오케스트레이터 결정 — 등록 B 가족 {W02 · W11} 한쪽 Holm α 0.05 · 채택 표시 = Holm 기각 ∧ Tier-2 무해 ∧
  G-EGD — w_core) ·
  사용자 규칙(최근 20년 · G-NoEG · 주식 중심 · 카드마다 근본 이유). 설계를 다시 짓지 않는다.

근본 이유(명세 그대로): 애널리스트와 투자자는 섹터 단위로 일하고 주의가 제한되어 있어, 섹터를 가로지르는 지역 충격(지역 노동 · 수요 · 정책)이 천천히 퍼진다.
  효과가 감시 수준과 무관하다는 점(Parsons · Sabbatucci · Titman 2020 RFS)이 대형주 우주에 유리하다. C 팔: 발표가 몰리면 주의가 분산돼 전파가 느려진다
  (Hirshleifer · Lim · Teoh 2009) → 다음 달 선후행이 크다.

카드(명세 base · conditional_C · primary_statistic 그대로)
  신호  G_{i,t} = Σ_{j∈동료(i,t)} ME_j·(r_{j,t} − r_{sec(j),t}) / Σ ME_j — 동료의 «섹터 초과수익»(휴스턴 비에너지 기업의 G 가 에너지 섹터 수익이 되지 않게) ·
        동료 = t 시점 합집합 회원(금융 포함) 가운데 같은 CBSA · 다른 GICS 섹터 · 동료 3곳 미만이면 결측(순위 0 + 결측 더미) · 창 1개월 · 교차표 빈티지 고정.
  통제  Stage M-W(w_stagem) + 자기 섹터 VW 수익 r_{sec(i),t} + 같은 CBSA · 같은 섹터 동료의 섹터 초과수익(geo_same).
  주 통계 z(G) 의 FM γ · NW(3) · H1 γ > 0(방향 +1 · w_core.CARD_DIRECTION) · 주 위약 = CBSA 라벨 섞기(달마다 · 섹터 구성 보존 · 1,000회).
  슬리브 1개월 신호: θ0 0.5 · q 0.3 · 버퍼 없음 · 전량 체결 · 상태 의존 비용(frozen v_core.liq_cost_rate) · 회전 상한 건너뛰기(w_cards B2).
  C 팔  θ_t = 0.5 + 0.3·clip(z(발표 밀도_t), −1, 1) ∈ [0.2, 0.8] — 고정 기울기 · 추정 없음 · V 의 한 달 |Δθ| ≤ 0.10 면제(명세) · 가설 하나(C 대 S).
        🔁 등록 B(러너 R22): Hirshleifer–Lim–Teoh 2009 를 등록 전에 열지 못해 C 팔은 쌍둥이(보고)로 내린다 · 채택 책 = S 책(θ0 0.5).
  쌍둥이(보고만) 3개월 평활 G. 대조(보고만) 랩 INDMOM(산업 모멘텀 12-1) 통제를 더한 판.
  F0(개수만 · 등록 B 자료 관문) ① 커버리지: Stage M-W 이름 가운데 동료 ≥ 3 을 가진 비율의 달별 중앙값 ≥ 50% — 못 미치면 등록 전에 카드를 닫는다 ·
     ② PIT 주소 점검: 알려진 본사 이전(Boeing 2022 · Caterpillar 2022 · Tesla 2021 · Oracle 2020 · Honeywell 2019 · HPE 2022 [지식])이 제출물 주소에서
        그 날짜 근처에 바뀌는지 — 셋 이상 어긋나면 주소 원천을 SGML 머리로 바꾼다 · ③ 상위 15 CBSA 몫(보고) · 발표 밀도 z 분포(스위치 활성 · 시장 상태만).

🔎 명세가 정하지 않은 산수(선언 — 등록 B 문서에 옮긴다)
  G1 주소 = FSDS sub.txt 의 사업장 주소(countryba · stprba · cityba · zipba · 제출 때 EDGAR 머리 값 = 시점정확)(명세 «t 이전에 접수된 최신 10-K/10-Q»):
     서식 10-K · 10-Q · 10-KT · 10-QT 와 그 /A · 그룹 CIK(§A0 지도 groups[g].ciks)의 효력 구간 안에서 접수된 것 · 접수일 filed < 결정일 d
     (다음 NYSE 거래일 가용 ≤ d 와 같다 — 13F 와 같은 규칙) · 가장 늦은 접수(같으면 accepted · adsh) · 550일보다 낡으면 없음 ·
     countryba ≠ US 이거나 ZIP5 가 아니면 CBSA 없음. FSDS 마지막 분기(받은 목록의 끝) 뒤 접수는 보이지 않는다(더 낡은 주소를 쓴다 · 선견 아님).
  G2 ZIP5 → CBSA = HUD-USPS ZIP_CBSA_032016(2016Q1 · 한 빈티지 · 명세 목표). 🔎 F0 탐침: 이 판의 CBSA 칸은 대도시 분할(metropolitan division ·
     11 대도시 31 분할 — 뉴욕 35614 · 시카고 16974 · 샌프란시스코 41884 …) 코드를 쓴다 → 같은 빈티지 OMB 13-01 획정(NBER cbsa2fipsxw2013.csv ·
     분할 31 → CBSA 11)으로 CBSA 로 올린다(명세 «CBSA» 그대로) · ZIP 마다 올린 CBSA 별 비율을 더한 뒤 BUS_RATIO 최대(본사 = 사업장 주소) · 같으면
     TOT_RATIO · 그래도 같으면 작은 코드 · 99999(CBSA 밖) → 없음 · 교차표에 없는 ZIP → 없음(개수 공개). 원자료 · 파생 지도는 저장소 밖 캐시에만.
  G3 동료 풀 = 그달 합집합 회원 전부(금융 포함 · 회사당 한 줄) 가운데 CBSA · 섹터(v_pit.sector) · r_{j,t} · ME_{j,t−1} 이 선 이름.
     동료(i) = 풀 ∩ 같은 CBSA ∩ 섹터 ≠ sec(i) ∩ 발행사 그룹 ≠ 그룹(i). 초점 이름 = Stage M-W 세계(비금융 · 비FPI · 그룹당 한 줄 — 굽기는 w_panel,
     F0 · 연기는 w_cards.smoke_world B8 근사).
  G4 r_{j,t} = frozen v_pit.month_ret(월말 수정종가 비 · 총수익) · 가중 ME_j = t−1 월말 시총(v_pit.me_row · 분할만 조정) ·
     r_{sec,t} = 풀 안 같은 섹터 이름의 ME_{t−1} 가중 평균(CBSA 와 무관 · 자기 포함) · 자기 섹터 수익 통제 = r_{sec(i),t}.
  G5 z(G) = 세계 안 단면 z(평균 0 · SD ddof 1 — w_cards.xs_z 와 같은 식) · 결측은 0 + 결측 더미(w_stagem.design focal_miss="dummy").
  G6 geo_same = 같은 CBSA · 같은 섹터 동료(자기 · 같은 그룹 제외)의 ME_{t−1} 가중 섹터 초과수익 · 동료 1 이상이면 선다(통제라 문턱을 두지 않는다) ·
     결측은 0 + 결측 더미(design extra).
  G7 INDMOM 대조 = 자기 섹터 이름의 ME_{t−1} 가중 12-1 모멘텀(frozen v_pit.mom12_2 = P_{t−1}/P_{t−12} − 1 · 랩 INDMOM 12-1 과 같은 형성 ·
     24 산업그룹 빌드 전이라 GICS 섹터 수준 — 이탈 공개).
  G8 발표 밀도_t = 그달 합집합 회원 가운데 8-K 2.02 접수일(랩 data/earn_dates.json · frozen v_ear.Earnings.key_of)이 그달 1일 ~ d 에 있는 비율 ·
     분모 = 발표일 표에 키가 있는 회원 · 확장창 z(2014-06 PIT 첫 달부터 · 관측 ≥ 24 · 아니면 None → θ0) · 계절성 그대로(명세).
  G9 CBSA 라벨 섞기: 달마다 풀 안 같은 섹터 이름끼리 CBSA 라벨을 섞는다(CBSA 없는 이름은 그대로) — (CBSA, 섹터) 쌍의 개수가 그대로라 도시권 크기 ·
     섹터 구성이 보존된다 · G · geo_same 을 다시 계산하고 같은 통제로 FM · 씨앗 default_rng(SEED + 2 + 1000·i)(K6) · 백분위 = placebo_rank(방향 +1) ·
     «백분위 ≥ 0.95» 는 채택 표시를 바꾸지 않는 주의 칸(w_core K5).
  G10 3개월 평활 G = G_t · G_{t−1} · G_{t−2}(각 달의 동료로 잰 값)의 평균 · 셋 모두 선 이름만.
  G11 슬리브 책(1개월 신호) = w_cards.select_top(buffer=False) → sleeve_target(θ_t) · 체결 = 목표 전량(½ 체결 없음) → 회전 예산 건너뛰기(w_cards.turnover_skip) ·
     비율 = frozen v_core.liq_cost_rate(격자 SPY · 상태 의존 · 20bp 판은 mult 2).
  G12 PIT 이전 점검: 이전 이름마다 결정일 d 의 주소 주(stprba)가 옛 주에서 새 주로 바뀐 첫 접수를 찾고, 그 접수일이 [발표월, 발표월 + 18개월] 안이면 일치.
     못 찾거나 창 밖이면 어긋남 · 셋 이상 어긋나면 «SGML 머리로 원천 교체» 판정(registration.allowed_F0_decisions).
     G12b 교체의 실행: FSDS sub.txt 의 주소 칸은 EDGAR 제출 머리(SGML <BUSINESS-ADDRESS>)에서 온다 — 먼저 어긋난 이름의 창 안 제출(과 창 앞 하나)의
     .hdr.sgml 을 받아 주 · ZIP5 가 FSDS 와 같은지 대조한다(표본 · 요청 수 공개). 모두 같으면 교체는 어떤 값도 바꾸지 않으므로 같은 값인 FSDS 를 그대로 쓰고
     «EDGAR 주소 지연» 을 한계로 공개한다(Boeing 은 2022 까지 옛 Seattle 주소) · 하나라도 다르면 전수 SGML 주소 패널을 새로 지어야 한다
     (요청 수 = 그룹 × 분기 · 0.5 req/s 에서 수 시간 — 재개 계획에 적는다).
  G13 SEC 접속(명세 U4 · 과제 지시): 연락처는 사용자 환경변수 SEC_UA 로만(과정 환경에 없으면 HKCU\\Environment 에서 읽는다 · 찍지 않는다 · 저장소에 쓰지 않는다) ·
     요청은 frozen edgar.fetch_bytes 한 곳(validate_site «SEC 호출 경로» 규칙) · 과정 사이 잠금 파일로 요청 시작 간격 ≥ 2.0초(≤ 0.5 req/s) ·
     429 · 5xx · 연결 오류는 지수 대기(15초부터 두 배 · 한 번 600초 상한 · Retry-After 존중) · 막힌 시간 합이 30분을 넘으면 그 파일을 미루고(SecDeferred)
     미룸을 노트(WBATCH_NOTES 또는 캐시 _sec_deferrals.md)에 적고 다른 단계를 이어간다 · 받은 원파일의 sha256 · 바이트 수를 추출본에 적는다.
     SEC 밖 원천(HUD)은 requests 로 받고 SEC 연락처를 보내지 않는다.

🚨 랩 규율 — 등록 커밋 전에는 실자료로 수익 · IC · FM γ · 신호-수익 통계를 계산하지 않는다. 수익을 받는 공개 함수(w02_fm · cbsa_shuffle)는 kind 자물쇠
   (w_core.assert_kind_allowed)를 지난다. 이 모듈의 실자료 명령(--build · --f0)은 주소 · CBSA · 동료 · 밀도의 **개수 · 비율 · 날짜**만 찍는다.
   G 값(과거 수익으로 만든 신호)도 F0 에서는 찍지 않는다 — 동료 수만 센다.

  python build/w_geo.py --selftest
  python build/w_geo.py --build [--from 2015q1]    FSDS sub.txt 추출(재개 가능 · SEC) + HUD 교차표(캐시) — 개수만 찍는다
  python build/w_geo.py --f0                       F0 개수(커버리지 · 이전 점검 · 상위 15 CBSA · 밀도 z 분포) → 캐시 f0/w02_f0.json
  python build/w_geo.py --sgml-check               G12b 이전 이름의 SGML 머리 주소 대조(SEC · 요청 수 한 자리) → 캐시 f0/w02_sgml_check.json
  python build/w_geo.py --blind-smoke              실자료 눈가린 연기(y · 평가 수익 = 씨앗 잡음 · 산출 열지 않고 삭제 · 참/거짓 · 시간만)
  python build/w_geo.py --manifest                 자료 핀(FSDS 분기별 원 ZIP · 추출 sha256 · HUD · 획정) → 캐시 f0/w02_manifest.json
  python build/w_geo.py --plan                     재개 계획(받은 · 남은 · 미룬 파일)
"""
from __future__ import annotations

import bisect
import collections
import datetime as _dt
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
import time
import traceback
import urllib.error
import zipfile

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402

# ══════════════════════════════════════════════════════════════════════════
#  카드 상수(명세 W02 그대로 · 지금 고정)
# ══════════════════════════════════════════════════════════════════════════
CARD = {"id": "W02", "name": "GEO-X", "role": "가족 B", "direction": +1, "ic_lit": 0.014, "sigma_cat": 0.07,
        "p0_synth": "0.109(σ 0.047) · 0.054(σ 0.07)", "sleeve": {"q": 0.30, "theta0": 0.50, "buffer": False, "fill": 1.0, "cost": "liq"},
        "c_arm": "θ_t = 0.5 + 0.3·clip(z(발표 밀도_t), −1, 1)", "twins": ["3개월 평활 G"], "controls": ["INDMOM(섹터 12-1)", "CBSA 라벨 섞기(주 위약)"],
        "cautions": ["cbsa_shuffle_pct_ge95", "v_repack"]}
assert CARD["direction"] == WC.CARD_DIRECTION["W02"] and "W02" in WC.FAMILY["B"]
MIN_PEERS = 3
MIN_SAME = 1                                                  # G6
THETA0, THETA_SLOPE, Z_CLIP = 0.50, 0.30, 1.0
DENS_FROM, DENS_MIN_N = "2014-06", 24                         # G8
N_SHUFFLE = 1000
SHUFFLE_SEED = WC.SEED + 2                                    # K6 — G9
COV_GATE = 0.50
ADDR_STALE_DAYS = 550
FIN_SECTOR = "Financials"

FSDS_INDEX = "https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets"
FSDS_FROM = "2015q1"                                          # 첫 결정 달 2016-08 보다 18개월 앞 · 이전 점검(2019~2022) 포함
FSDS_FORMS = ("10-K", "10-Q", "10-KT", "10-QT", "10-K/A", "10-Q/A", "10-KT/A", "10-QT/A")
FSDS_COLS = ("adsh", "cik", "name", "countryba", "stprba", "cityba", "zipba", "form", "period", "filed", "accepted")
HUD_URL = "https://www.huduser.gov/portal/datasets/usps/ZIP_CBSA_032016.xlsx"
HUD_VINTAGE = "2016Q1(032016)"
DELIN_URL = "https://data.nber.org/cbsa-csa-fips-county-crosswalk/2013/cbsa2fipsxw2013.csv"   # OMB 13-01 판(HUD 2016Q1 의 분할 코드와 같은 빈티지)
SGML_URL = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s.hdr.sgml"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

# 알려진 본사 이전(명세 f0_gates [지식]) — (명단 티커, 발표월, 옛 주, 새 주, 설명)
RELOCATIONS = (
    ("BA", "2022-05", "IL", "VA", "Boeing Chicago → Arlington"),
    ("CAT", "2022-06", "IL", "TX", "Caterpillar Deerfield → Irving"),
    ("TSLA", "2021-10", "CA", "TX", "Tesla Palo Alto → Austin"),
    ("ORCL", "2020-12", "CA", "TX", "Oracle Redwood City → Austin"),
    ("HON", "2018-06", "NJ", "NC", "Honeywell Morris Plains → Charlotte"),
    ("HPE", "2020-12", "CA", "TX", "HPE San Jose → Houston"),
)
RELOC_WINDOW_M = 18
RELOC_FAIL_SWITCH = 3

GEO_UNITS = [WG.unit("geo_g", source="SEC FSDS sub.txt business address + HUD ZIP-CBSA 2016Q1 + data/pit_px.json",
                     concept="cross-sector same-CBSA peers' sector-excess return (ME-weighted)", use="signal"),
             WG.unit("own_sec_ret", source="data/pit_px.json + v_pit.me_row", concept="own GICS sector value-weighted return", use="control"),
             WG.unit("geo_same", source="SEC FSDS sub.txt business address + HUD ZIP-CBSA 2016Q1 + data/pit_px.json",
                     concept="same-CBSA same-sector peers' sector-excess return", use="control"),
             WG.unit("indmom", source="data/pit_px.json", concept="sector value-weighted 12-1 momentum (lab INDMOM formation)", use="control"),
             WG.unit("ann_density", source="data/earn_dates.json (8-K Item 2.02)", concept="share of union members announcing in month",
                     use="theta_state"),
             WG.unit("geo_g3", source="SEC FSDS sub.txt business address + HUD ZIP-CBSA 2016Q1 + data/pit_px.json",
                     concept="3-month mean of cross-sector geographic peer signal", use="signal")]
WG.assert_units(GEO_UNITS, "w_geo 입력(모듈 적재)")


def _log(msg):
    print(msg, flush=True)


# ══════════════════════════════════════════════════════════════════════════
#  SEC 접속 규약(G13) — w_frag 도 이것을 쓴다
# ══════════════════════════════════════════════════════════════════════════
SEC_GAP = 2.0
SEC_BLOCK_LIMIT = 30 * 60
SEC_WAIT0, SEC_WAIT_MAX = 15.0, 600.0
SEC_HOSTS = ("www.sec.gov", "data.sec.gov")


class SecDeferred(Exception):
    """막힌 시간 합이 30분을 넘어 이 파일을 미뤘다(재개 계획에 남는다)."""


def user_env_ua():
    """SEC_UA — 과정 환경 → 사용자 환경변수(HKCU\\Environment). 값을 찍지 않는다. 없으면 None."""
    v = os.environ.get("SEC_UA")
    if v:
        return v
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _ = winreg.QueryValueEx(k, "SEC_UA")
        except OSError:
            v = None
    return v or None


def _host(url):
    m = re.match(r"^https://([^/]+)/", str(url))
    return m.group(1).lower() if m else None


def notes_path():
    return os.environ.get("WBATCH_NOTES") or os.path.join(WC.cache_dir("sec_gate"), "_sec_deferrals.md")


def note_deferral(what, url, code, blocked):
    p = notes_path()
    with io.open(p, "a", encoding="utf-8") as f:
        f.write("- %s SEC 미룸(%s): %s · 마지막 응답 %s · 막힌 시간 %.0f초 > %d초 — 재개: python build/%s.py --build\n"
                % (_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), what, url.rsplit("/", 1)[-1], code, blocked, SEC_BLOCK_LIMIT,
                   "w_frag" if what.startswith("13F") or what.startswith("FTD") else "w_geo"))
    return p


class SecClient:
    """SEC 요청 한 곳(G13) — frozen edgar.fetch_bytes(재시도 없이 한 번) + 과정 사이 잠금 · 간격 ≥ 2초 · 지수 대기 · 30분 넘으면 미룸.
    edgar 를 주입할 수 있다(selftest 는 가짜 edgar · 망 없음)."""

    def __init__(self, edgar=None, gap=SEC_GAP, block_limit=SEC_BLOCK_LIMIT, wait0=SEC_WAIT0, sleep=time.sleep, gate_dir=None, log=_log):
        if edgar is None:
            ua = user_env_ua()
            if not ua:
                raise SystemExit("🚨 SEC_UA(사용자 환경변수)가 없다 — SEC 에 접속하지 않는다(명세 U4 · 연락처는 환경변수로만)")
            os.environ["SEC_UA"] = ua                                          # edgar 는 불러올 때 SEC_UA 를 읽는다
            edgar = WC.frozen("edgar")
            if getattr(edgar, "UA", None) != ua:
                raise SystemExit("🚨 불러온 edgar 의 UA 가 SEC_UA 와 다르다(먼저 불러온 edgar) — 새 과정에서 다시")
        self.E = edgar
        self.gap, self.block_limit, self.wait0, self.sleep, self.log = gap, block_limit, wait0, sleep, log
        self.gate = gate_dir or WC.cache_dir("sec_gate")
        self.n_req, self.n_bytes, self.blocked = 0, 0, 0.0

    # ── 과정 사이 잠금(mkdir 원자성) · 간격 ──────────────────────────────
    def _acquire(self):
        lock = os.path.join(self.gate, "lock.d")
        t0 = time.time()
        while True:
            try:
                os.mkdir(lock)
                return lock
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(lock) > 900:                    # 죽은 과정의 잠금(15분)
                        os.rmdir(lock)
                        continue
                except OSError:
                    pass
                if time.time() - t0 > 3600:
                    raise SystemExit("🚨 SEC 잠금을 한 시간 동안 못 얻었다")
                time.sleep(0.25)

    def _last(self):
        p = os.path.join(self.gate, "last.txt")
        try:
            with io.open(p, encoding="utf-8") as f:
                return float(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0.0

    def _stamp(self):
        p = os.path.join(self.gate, "last.txt")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write("%.6f" % time.time())

    def get(self, url, what=""):
        """바이트 한 건 — 404 는 그대로 올린다 · 막힘 합 > 30분이면 SecDeferred."""
        if _host(url) not in SEC_HOSTS:
            raise SystemExit("🚨 SecClient 는 SEC 호스트만(%s)" % _host(url))
        wait, blocked, last_code = self.wait0, 0.0, None
        while True:
            lock = self._acquire()
            try:
                dt = time.time() - self._last()
                if dt < self.gap:
                    self.sleep(self.gap - dt)
                try:
                    b = self.E.fetch_bytes(url, timeout=300, max_wait=0)
                    self.n_req += 1
                    self.n_bytes += len(b)
                    return b
                except urllib.error.HTTPError as e:
                    self.n_req += 1
                    if e.code == 404:
                        raise
                    last_code = e.code
                    ra = (e.headers.get("Retry-After") if e.headers else None) or ""
                    if str(ra).strip().isdigit():
                        wait = max(wait, min(float(str(ra).strip()), SEC_WAIT_MAX))
                except Exception as e:                                             # noqa: BLE001 — 연결 오류 · 시간 초과
                    self.n_req += 1
                    last_code = type(e).__name__
                finally:
                    self._stamp()
            finally:
                try:
                    os.rmdir(lock)
                except OSError:
                    pass
            if blocked + wait > self.block_limit:
                self.blocked += blocked
                note_deferral(what or "SEC", url, last_code, blocked)
                raise SecDeferred("%s 막힘 %.0f초(%s)" % (url.rsplit("/", 1)[-1], blocked, last_code))
            self.log("  ⚠ SEC %s — %.0f초 뒤 재시도(막힘 합 %.0f초) %s" % (last_code, wait, blocked, url.rsplit("/", 1)[-1]))
            self.sleep(wait)
            blocked += wait
            wait = min(wait * 2.0, SEC_WAIT_MAX)


def index_zips(html, pattern):
    """색인 쪽 → [(파일 이름, 절대 URL)] — 정규식에 맞는 href 만(중복 없이 쪽 차례)."""
    out, seen = [], set()
    for h in re.findall(r'href="([^"]+\.zip)"', html, re.I):
        fn = h.rsplit("/", 1)[-1]
        if not re.fullmatch(pattern, fn, re.I) or fn in seen:
            continue
        seen.add(fn)
        out.append((fn, h if h.startswith("http") else "https://www.sec.gov" + h))
    return out


def web_get(url, timeout=120):
    """SEC 밖 원천(HUD 등) — requests · 브라우저 UA · SEC 연락처를 보내지 않는다."""
    if _host(url) in SEC_HOSTS or (_host(url) or "").endswith("sec.gov"):
        raise SystemExit("🚨 SEC 호스트는 SecClient 로만")
    import requests
    r = requests.get(url, headers={"User-Agent": UA_BROWSER}, timeout=timeout)
    r.raise_for_status()
    return r.content


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def write_json_gz(path, doc):
    WC.assert_writable(path)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return path


def read_json_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════
#  FSDS sub.txt(G1)
# ══════════════════════════════════════════════════════════════════════════
def fsds_dir():
    return WC.cache_dir("raw", "fsds")


def fsds_extract_path(q):
    return os.path.join(fsds_dir(), "%s_sub10.json.gz" % q)


def fsds_extract(zbytes):
    """FSDS ZIP 바이트 → (열 이름, 10-K/10-Q 계열 행, 전체 행 수). sub.txt 만 읽는다(num · pre · tag 는 열지 않는다)."""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    with z.open("sub.txt") as fh:
        txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
        hdr = txt.readline().rstrip("\r\n").split("\t")
        pos = [hdr.index(c) for c in FSDS_COLS]
        rows, n = [], 0
        fi = hdr.index("form")
        for line in txt:
            p = line.rstrip("\r\n").split("\t")
            if len(p) < len(hdr):
                continue
            n += 1
            if p[fi] not in FSDS_FORMS:
                continue
            rows.append([p[j] for j in pos])
    return list(FSDS_COLS), rows, n


def fsds_quarters(client, q_from=FSDS_FROM):
    html = client.get(FSDS_INDEX, "FSDS 색인").decode("utf-8", "ignore")
    zs = index_zips(html, r"\d{4}q[1-4]\.zip")
    return sorted([(fn[:6], u) for fn, u in zs if fn[:6] >= q_from])


def build_fsds(client=None, q_from=FSDS_FROM, log=_log):
    """FSDS 추출(재개 가능) — 이미 있는 분기는 건너뛴다 · ZIP 은 메모리에서만(디스크에 두지 않는다) · 개수만 찍는다."""
    client = client or SecClient()
    qs = fsds_quarters(client, q_from)
    done, new, deferred = [], [], []
    for q, u in qs:
        p = fsds_extract_path(q)
        if os.path.isfile(p):
            done.append(q)
            continue
        try:
            b = client.get(u, "FSDS %s" % q)
        except SecDeferred:
            deferred.append(q)
            continue
        cols, rows, n = fsds_extract(b)
        write_json_gz(p, {"q": q, "url": u, "zip_sha256": sha256_bytes(b), "zip_bytes": len(b), "n_sub": n, "n_rows": len(rows),
                          "cols": cols, "rows": rows, "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        new.append(q)
        log("  FSDS %s · sub 행 %d · 10-K/10-Q 계열 %d · %.1f MB" % (q, n, len(rows), len(b) / 1e6))
        del b
    return {"listed": [q for q, _ in qs], "done_before": done, "new": new, "deferred": deferred, "n_req": client.n_req}


def hud_path():
    return os.path.join(WC.cache_dir("raw", "geo"), "ZIP_CBSA_032016.xlsx")


def delin_path():
    return os.path.join(WC.cache_dir("raw", "geo"), "cbsa2fipsxw2013.csv")


def build_hud(log=_log):
    out = {}
    for p, u, nm in ((hud_path(), HUD_URL, "hud"), (delin_path(), DELIN_URL, "delineation")):
        if not os.path.isfile(p):
            b = web_get(u)
            WC.assert_writable(p)
            with open(p, "wb") as f:
                f.write(b)
            log("  %s · %.1f MB" % (nm, len(b) / 1e6))
        with open(p, "rb") as f:
            out[nm] = {"path": p, "sha256": sha256_bytes(f.read()), "url": u}
    out["vintage"] = HUD_VINTAGE
    out["sha256"] = out["hud"]["sha256"]
    return out


def delineation(path=None):
    """OMB 13-01 획정(NBER) → ({분할 코드: CBSA}, {CBSA: 이름})."""
    import csv
    with io.open(path or delin_path(), encoding="latin-1", newline="") as f:
        rd = list(csv.DictReader(f))
    div, title = {}, {}
    for r in rd:
        c = (r.get("cbsacode") or "").strip()
        dv = (r.get("metrodivisioncode") or "").strip()
        if c:
            title.setdefault(c, (r.get("cbsatitle") or "").strip())
        if c and dv:
            div[dv] = c
    return div, title


# ══════════════════════════════════════════════════════════════════════════
#  ZIP → CBSA(G2)
# ══════════════════════════════════════════════════════════════════════════
def zip_cbsa_rows(path):
    """HUD xlsx → [(zip5, cbsa, res, bus, oth, tot)]."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h or "").strip().upper() for h in next(it)]
    ix = {k: hdr.index(k) for k in ("ZIP", "CBSA", "RES_RATIO", "BUS_RATIO", "OTH_RATIO", "TOT_RATIO")}
    out = []
    for r in it:
        z = r[ix["ZIP"]]
        c = r[ix["CBSA"]]
        if z is None or c is None:
            continue
        out.append(("%05d" % int(z) if not isinstance(z, str) else z.strip().zfill(5), str(int(c)) if not isinstance(c, str) else c.strip(),
                    float(r[ix["RES_RATIO"]] or 0), float(r[ix["BUS_RATIO"]] or 0), float(r[ix["OTH_RATIO"]] or 0), float(r[ix["TOT_RATIO"]] or 0)))
    wb.close()
    return out


def zip_cbsa_map(rows, div2cbsa=None):
    """G2 — 분할 코드를 CBSA 로 올리고(div2cbsa) ZIP · CBSA 별 비율을 더한 뒤 BUS_RATIO 최대 · 같으면 TOT_RATIO · 같으면 작은 코드 · 99999 → None.
    돌려주는 것 ({zip5: cbsa|None}, 개수)."""
    div2cbsa = div2cbsa or {}
    acc = {}
    n_div = 0
    for z, c, _res, bus, _oth, tot in rows:
        if c in div2cbsa:
            c = div2cbsa[c]
            n_div += 1
        a = acc.setdefault(z, {}).setdefault(c, [0.0, 0.0])
        a[0] += bus
        a[1] += tot
    out = {}
    for z, by in acc.items():
        c = max(by, key=lambda k: (by[k][0], by[k][1], -int(k) if k.isdigit() else 0))
        out[z] = None if c == "99999" else c
    return out, {"n_zip": len(out), "n_cbsa": len({c for c in out.values() if c}), "n_non_cbsa": sum(1 for c in out.values() if c is None),
                 "n_rows_div_rolled": n_div}


# ══════════════════════════════════════════════════════════════════════════
#  주소 패널(G1)
# ══════════════════════════════════════════════════════════════════════════
def _iso8(s):
    s = str(s or "")
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8]) if re.fullmatch(r"\d{8}", s) else None


def _days(a, b):
    return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days


def zip5(z):
    m = re.match(r"^\s*(\d{5})", str(z or ""))
    return m.group(1) if m else None


class Addresses:
    """그룹 → 시점정확 사업장 주소. by_cik = {cik: [(filed, accepted, adsh, form, country, state, city, zip5)]} · zmap = {zip5: cbsa} ·
    groups = §A0 지도 groups({g: {ciks: [[CIK, 시작, 끝, 근거, 이름]] …}})."""

    def __init__(self, by_cik, zmap, groups, stale=ADDR_STALE_DAYS):
        self.by_cik = {int(k): sorted(v) for k, v in by_cik.items()}
        self.zmap = zmap
        self.groups = groups
        self.stale = stale
        self._g = {}

    @classmethod
    def load(cls, quarters=None):
        by = {}
        n_files = 0
        for fn in sorted(os.listdir(fsds_dir())):
            if not fn.endswith("_sub10.json.gz") or (quarters and fn[:6] not in quarters):
                continue
            doc = read_json_gz(os.path.join(fsds_dir(), fn))
            n_files += 1
            c = {k: i for i, k in enumerate(doc["cols"])}
            for r in doc["rows"]:
                f = _iso8(r[c["filed"]])
                if not f:
                    continue
                by.setdefault(int(r[c["cik"]]), []).append((f, r[c["accepted"]], r[c["adsh"]], r[c["form"]], r[c["countryba"]].strip().upper(),
                                                            r[c["stprba"]].strip().upper(), r[c["cityba"]].strip().upper(), zip5(r[c["zipba"]])))
        zmap, _ = zip_cbsa_map(zip_cbsa_rows(hud_path()), delineation()[0])
        VD = WC.frozen("v_data")
        im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
        A = cls(by, zmap, im.get("groups") or {})
        A.n_files = n_files
        return A

    def filings(self, gid):
        """그룹의 제출(효력 구간 안) — 접수일 차례."""
        if gid in self._g:
            return self._g[gid]
        out = []
        for row in (self.groups.get(gid) or {}).get("ciks") or []:
            cik, a, b = int(row[0]), row[1], row[2]
            for x in self.by_cik.get(cik, ()):
                if (a is None or x[0] >= a) and (b is None or x[0] <= b):
                    out.append(x + (cik,))
        out.sort()
        self._g[gid] = out
        return out

    def at(self, gid, d):
        """결정일 d 의 주소 — filed < d 인 가장 늦은 접수(550일 안) · dict | None."""
        fs = self.filings(gid) if gid else []
        j = bisect.bisect_left(fs, (d,)) - 1
        if j < 0:
            return None
        x = fs[j]
        if _days(x[0], d) > self.stale:
            return None
        return {"filed": x[0], "adsh": x[2], "form": x[3], "country": x[4], "state": x[5], "city": x[6], "zip5": x[7], "cik": x[8]}

    def cbsa(self, gid, d):
        """(cbsa | None, 사유) — 사유: ok · no_filing · non_us · no_zip · zip_not_in_hud · non_cbsa."""
        a = self.at(gid, d)
        if a is None:
            return None, "no_filing"
        if a["country"] != "US":
            return None, "non_us"
        if not a["zip5"]:
            return None, "no_zip"
        if a["zip5"] not in self.zmap:
            return None, "zip_not_in_hud"
        c = self.zmap[a["zip5"]]
        return (c, "ok") if c else (None, "non_cbsa")


# ══════════════════════════════════════════════════════════════════════════
#  동료 · G(G3 ~ G7 · G10) — 순수 함수(합성 selftest 가 무작정 계산과 대조)
# ══════════════════════════════════════════════════════════════════════════
def sector_vw(sec, me0, r):
    """{섹터: ME_{t−1} 가중 평균 r}(G4) — 결측 · 0 이하 가중은 뺀다."""
    acc = {}
    for s, w, x in zip(sec, me0, r):
        if s is None or not (w == w) or w is None or w <= 0 or x is None or not (x == x):
            continue
        a = acc.setdefault(s, [0.0, 0.0])
        a[0] += w * x
        a[1] += w
    return {s: a[0] / a[1] for s, a in acc.items() if a[1] > 0}


def geo_month(pool, focal_t, min_peers=MIN_PEERS, min_same=MIN_SAME, cbsa=None):
    """한 달 — pool = {t, cbsa, sec, gid, me0, r, mom}(목록 · 풀 전부) · focal_t = 초점 티커 목록 · cbsa = 바꾼 라벨(섞기) 또는 None.
    돌려주는 것 {t: {G, n_peers, geo_same, n_same, own_sec_ret, indmom}}."""
    lab = list(pool["cbsa"] if cbsa is None else cbsa)
    sec, gid, me0, r = pool["sec"], pool["gid"], pool["me0"], pool["r"]
    n = len(pool["t"])
    rsec = sector_vw(sec, me0, r)
    mom = pool.get("mom")
    isec = sector_vw(sec, me0, mom) if mom is not None else {}
    ok = [lab[j] is not None and sec[j] is not None and me0[j] is not None and me0[j] == me0[j] and me0[j] > 0 and r[j] is not None
          and r[j] == r[j] and sec[j] in rsec for j in range(n)]
    ex = [(r[j] - rsec[sec[j]]) if ok[j] else None for j in range(n)]
    S, W, N = {}, {}, {}
    byg = {}
    for j in range(n):
        if not ok[j]:
            continue
        k = (lab[j], sec[j])
        S[k] = S.get(k, 0.0) + me0[j] * ex[j]
        W[k] = W.get(k, 0.0) + me0[j]
        N[k] = N.get(k, 0) + 1
        byg.setdefault((lab[j], gid[j]), []).append(j)
    secs_in = {}
    for (c, s) in N:
        secs_in.setdefault(c, set()).add(s)
    pos = {t: j for j, t in enumerate(pool["t"])}
    out = {}
    for t in focal_t:
        j = pos.get(t)
        rec = {"G": None, "n_peers": 0, "geo_same": None, "n_same": 0, "own_sec_ret": None, "indmom": None}
        if j is None:
            out[t] = rec
            continue
        s_i, c_i, g_i = sec[j], lab[j], gid[j]
        rec["own_sec_ret"] = rsec.get(s_i) if s_i is not None else None
        rec["indmom"] = isec.get(s_i) if s_i is not None else None
        if c_i is None or s_i is None:
            out[t] = rec
            continue
        sw, ww, nn = 0.0, 0.0, 0
        for s in secs_in.get(c_i, ()):
            if s == s_i:
                continue
            sw += S[(c_i, s)]
            ww += W[(c_i, s)]
            nn += N[(c_i, s)]
        same_g = byg.get((c_i, g_i), []) if g_i is not None else ([j] if ok[j] else [])
        for jj in same_g:                                                         # 같은 그룹의 다른 섹터 줄(거의 없다)
            if sec[jj] != s_i:
                sw -= me0[jj] * ex[jj]
                ww -= me0[jj]
                nn -= 1
        rec["n_peers"] = nn
        if nn >= min_peers and ww > 0:
            rec["G"] = sw / ww
        k = (c_i, s_i)
        if k in N:
            s2, w2, n2 = S[k], W[k], N[k]
            for jj in same_g:                                                     # 자기 · 같은 그룹 줄을 뺀다
                if sec[jj] == s_i:
                    s2 -= me0[jj] * ex[jj]
                    w2 -= me0[jj]
                    n2 -= 1
            rec["n_same"] = n2
            if n2 >= min_same and w2 > 1e-12:
                rec["geo_same"] = s2 / w2
        out[t] = rec
    return out


def xs_z(x):
    """G5 — 단면 z(ddof 1) · 결측 NaN · 선 값 < 3 이면 모두 NaN(w_cards.xs_z 와 같은 식)."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    out = np.full(len(x), np.nan)
    if ok.sum() >= 3:
        sd = float(x[ok].std(ddof=1))
        out[ok] = (x[ok] - x[ok].mean()) / sd if sd > 0 else 0.0
    return out


def smooth3(geo_by_month, months):
    """G10 — {달: {t: G}} → 3개월 평활 {달: {t: 평균}}(셋 모두 선 이름)."""
    out = {}
    for m in months:
        a = geo_by_month.get(m) or {}
        b = geo_by_month.get(WC.mshift(m, -1)) or {}
        c = geo_by_month.get(WC.mshift(m, -2)) or {}
        out[m] = {t: (a[t] + b[t] + c[t]) / 3.0 for t in a if a.get(t) is not None and b.get(t) is not None and c.get(t) is not None}
    return out


def shuffle_labels(cbsa, sec, rng):
    """G9 — 같은 섹터 안에서 CBSA 라벨을 섞는다(라벨 없는 이름 · 섹터 없는 이름은 그대로)."""
    lab = list(cbsa)
    by = {}
    for j, (c, s) in enumerate(zip(cbsa, sec)):
        if c is not None and s is not None:
            by.setdefault(s, []).append(j)
    for s in sorted(by, key=str):
        idx = by[s]
        perm = rng.permutation(len(idx))
        vals = [cbsa[idx[p]] for p in perm]
        for j, v in zip(idx, vals):
            lab[j] = v
    return lab


# ══════════════════════════════════════════════════════════════════════════
#  C 팔(G8)
# ══════════════════════════════════════════════════════════════════════════
def density_month(members, d, key_of, ed):
    """발표 밀도 — members = [{t, k}] · key_of(t, k) → 발표일 표 키 | None · ed{키: 정렬된 날짜}. 돌려주는 것 (밀도 | None, 분모, 분자)."""
    lo = d[:7] + "-01"
    num = den = 0
    for r in members:
        key = key_of(r["t"], r["k"])
        if key is None:
            continue
        den += 1
        ds = ed.get(key) or []
        j = bisect.bisect_left(ds, lo)
        if j < len(ds) and ds[j] <= d:
            num += 1
    return (num / den if den else None), den, num


def density_z(dens, months, start=DENS_FROM, min_n=DENS_MIN_N):
    """확장창 z(start 부터 · 관측 ≥ min_n · 아니면 None) — 그 달까지의 값만(선견 없음)."""
    hist, out = [], {}
    for m in sorted(months):
        v = dens.get(m)
        if m < start or v is None or not (v == v):
            out[m] = None
            continue
        hist.append(float(v))
        if len(hist) < min_n:
            out[m] = None
            continue
        sd = float(np.std(hist, ddof=1))
        out[m] = (float(v) - float(np.mean(hist))) / sd if sd > 0 else 0.0
    return out


def theta_c(z):
    """θ_t = 0.5 + 0.3·clip(z, −1, 1) ∈ [0.2, 0.8] · z 결측 → θ0."""
    if z is None or not (z == z):
        return THETA0
    return THETA0 + THETA_SLOPE * min(max(float(z), -Z_CLIP), Z_CLIP)


# ══════════════════════════════════════════════════════════════════════════
#  실자료 월 입력(굽기 · 연기 · F0 — 수익 통계 없음)
# ══════════════════════════════════════════════════════════════════════════
def pool_month(U, m, A):
    """그달 풀(G3 · G4) — {t, k, gid, sec, cbsa, why, me0, r, mom, fin} 목록. r · mom 은 과거 수익(신호 입력)이다 — 이 함수는 찍지 않는다."""
    m0 = WC.mshift(m, -1)
    d = U.d_of(m)
    out = {k: [] for k in ("t", "k", "gid", "sec", "cbsa", "why", "me0", "r", "mom", "fin", "ndx_only")}
    for r in U.members(m):
        sec, _ = U.sector(r["t"], m, r["ndx_only"])
        me0 = U.me_row(r, m0)[0] if m0 in U.me_idx else None
        cb, why = A.cbsa(r["gid"], d) if r.get("gid") else (None, "no_gid")
        out["t"].append(r["t"])
        out["k"].append(r["k"])
        out["gid"].append(r.get("gid"))
        out["sec"].append(sec)
        out["cbsa"].append(cb)
        out["why"].append(why)
        out["me0"].append(me0)
        out["r"].append(U.month_ret(r["k"], m))
        out["mom"].append(U.mom12_2(r["k"], m))
        out["fin"].append(sec == FIN_SECTOR)
        out["ndx_only"].append(bool(r["ndx_only"]))
    return out


def world_of(U, m):
    """초점 = Stage M-W 세계(굽기는 w_panel · 없으면 w_cards.smoke_world B8 근사) — 티커 목록."""
    try:
        import w_panel as WPN                                                     # 다른 단계가 지으면 그것
        f = getattr(WPN, "stage_world", None)
        if f is not None:
            return [r["t"] for r in f(U, m)]
    except ImportError:
        pass
    import w_cards as WCD
    world, _rows = WCD.smoke_world(U, m)
    return [r["t"] for r in world]


def geo_panel(U, months, A=None, E=None, log=_log):
    """실자료 W02 입력 — {달: {"pool", "focal", "geo"{t: …}}} · 밀도 {달: (밀도, 분모, 분자)}. 🚨 신호 값을 찍지 않는다(개수만 기록)."""
    A = A or Addresses.load()
    if E is None:
        E = WC.frozen("v_ear").Earnings(U, sameday_primary=True)
    out, dens, t0 = {}, {}, time.time()
    for i, m in enumerate(months):
        if m not in U.me_idx or WC.mshift(m, -1) not in U.me_idx:
            continue
        pool = pool_month(U, m, A)
        focal = world_of(U, m)
        out[m] = {"pool": pool, "focal": focal, "geo": geo_month(pool, focal)}
        dens[m] = density_month(U.members(m), U.d_of(m), E.key_of, E.ed)
        if i % 24 == 0:
            log("  W02 입력 %s · 풀 %d · 초점 %d · %.0fs" % (m, len(pool["t"]), len(focal), time.time() - t0))
    return out, dens


# ══════════════════════════════════════════════════════════════════════════
#  카드 계산(kind 자물쇠 — 등록 전에는 synth · blind 만)
# ══════════════════════════════════════════════════════════════════════════
def _align(D, rec_of_t, key):
    return np.array([np.nan if (rec_of_t.get(t) or {}).get(key) is None else float(rec_of_t[t][key]) for t in D["t"]], float)


def w02_designs(D, geo, variant="main", g3=None):
    """패널 달 D 와 그달 geo{t: …} → Stage M-W 설계 한 개. variant: main · indmom(대조) · smooth3(쌍둥이 · g3{t: 값})."""
    import w_stagem as S
    if variant == "smooth3":
        g = np.array([np.nan if (g3 or {}).get(t) is None else float(g3[t]) for t in D["t"]], float)
        focal = [("geo_g3", xs_z(g))]
    else:
        focal = [("geo_g", xs_z(_align(D, geo, "G")))]
    extra = [("own_sec_ret", _align(D, geo, "own_sec_ret")), ("geo_same", _align(D, geo, "geo_same"))]
    if variant == "indmom":
        extra.append(("indmom", _align(D, geo, "indmom")))
    return S.stage_m_w_design(D, focal, extra=extra, focal_miss="dummy", where="W02 %s" % variant)


def w02_fm(P, GEO, kind, months=None, variant="main", g3_by_month=None, B=None, seed=None):
    """W02 Tier-1 — FM(z(G) · Stage M-W + 두 통제) · NW(3) · 방향 +1. P = 패널{kind, months, m{달: D}} · GEO{달: {"geo": {t: …}}}.
    🚨 kind 자물쇠(w_stagem.fm)."""
    import w_stagem as S
    if P.get("kind") != kind:
        raise SystemExit("🚨 패널 종류 %s ≠ %s" % (P.get("kind"), kind))
    ms = [m for m in (months or P["months"]) if m in P["m"] and m in GEO]
    nm = "geo_g3" if variant == "smooth3" else "geo_g"

    def des(m):
        g3 = (g3_by_month or {}).get(m) if variant == "smooth3" else None
        return [w02_designs(P["m"][m], GEO[m]["geo"], variant, g3)]
    res = S.fm(ms, des, [nm], kind)
    if B is not None:                                                  # 가족 판정 칸 — w_stagem S11 야생 부트스트랩 p(등록 전 보정)
        summ = S.family_fm(res["months"], res["g"][nm], CARD["direction"], int(B), int(seed))
    else:
        summ = S.summarize(res["months"], res["g"][nm], CARD["direction"])
    return {"fm": res, "summary": summ, "variant": variant}


def cbsa_shuffle(P, GEO, kind, n=N_SHUFFLE, seed=SHUFFLE_SEED, months=None):
    """G9 — CBSA 라벨 섞기 위약: 반복마다 달마다 섹터 안 라벨을 섞어 G · geo_same 을 다시 계산하고 같은 통제로 FM t. 🚨 kind 자물쇠.
    돌려주는 것 {t[], n, seed, scheme}(위약 γ 평균은 돌려주지 않는다)."""
    import w_stagem as S
    WC.assert_kind_allowed(kind, "w_geo.cbsa_shuffle")
    if not isinstance(n, int) or n < 1:
        raise SystemExit("🚨 n 은 명시 정수")
    ms = [m for m in (months or P["months"]) if m in P["m"] and m in GEO]
    ts = []
    for i in range(n):
        rng = np.random.default_rng(seed + 1000 * i)
        g_perm = {}
        for m in ms:
            pool = GEO[m]["pool"]
            lab = shuffle_labels(pool["cbsa"], pool["sec"], rng)
            g_perm[m] = {"geo": geo_month(pool, GEO[m]["focal"], cbsa=lab)}
        res = S.fm(ms, lambda m: [w02_designs(P["m"][m], g_perm[m]["geo"])], ["geo_g"], kind)
        s = S.summarize(res["months"], res["g"]["geo_g"], CARD["direction"])
        ts.append(s["nw_t"] if s["nw_t"] is not None else float("nan"))
    return {"t": np.array(ts, float), "n": n, "seed": seed, "scheme": "달마다 섹터 안 CBSA 라벨 섞기((CBSA, 섹터) 개수 보존)"}


def w02_book(X, geo_m, theta, q=CARD["sleeve"]["q"]):
    """G11 — 1개월 신호 책: 점수 z(G)(결측은 선정 밖) · 버퍼 없음 · sleeve_target(θ). 돌려주는 것 (w | None, info)."""
    import w_cards as WCD
    g = np.array([np.nan if (geo_m.get(t) or {}).get("G") is None else float(geo_m[t]["G"]) for t in X.t], float)
    mask = WCD.select_top(X, xs_z(g), q, prev=None, buffer=False)
    return WCD.sleeve_target(X, mask, theta)


def w02_execute(w_drift, target):
    """G11 — 전량 체결(½ 체결 없음) → 회전 예산 건너뛰기(w_cards B2). (책, 거래량, 건너뛴 수)."""
    import w_cards as WCD
    return WCD.turnover_skip(w_drift, target)


def gegd_entry(X, geo_m):
    """G-EGD 입력 한 달(w_cmp 의 wb_books 모양 조각) — θ = 1 책 {티커: 비중} · 신호 {티커: G}(선 이름만). 러너가 wB · keys 와 합친다."""
    w, _ = w02_book(X, geo_m, 1.0)
    sig = {t: float(v["G"]) for t, v in geo_m.items() if v.get("G") is not None}
    return {"book": (X.book(w) if w is not None else None), "signal": sig}


def w02_cost_rate(U):
    """상태 의존 편도 비율(frozen v_core.liq_cost_rate · 격자 SPY) — {결정 달: 비율}."""
    return WC.frozen("v_core").liq_cost_rate(U.spy, U.dates)


# ══════════════════════════════════════════════════════════════════════════
#  SGML 머리(G12b)
# ══════════════════════════════════════════════════════════════════════════
def sgml_business_address(txt):
    """.hdr.sgml 본문 → {state, zip5, city}(첫 <BUSINESS-ADDRESS> 묶음 · 제출자 칸) | None."""
    m = re.search(r"<BUSINESS-ADDRESS>(.*?)(?:</BUSINESS-ADDRESS>|<MAIL-ADDRESS>|</FILER>|<FILER>)", txt, re.S | re.I)
    if not m:
        return None
    blk = m.group(1)

    def tag(t):
        x = re.search(r"<%s>([^\r\n<]*)" % t, blk, re.I)
        return x.group(1).strip().upper() if x else None
    return {"state": tag("STATE"), "zip5": zip5(tag("ZIP")), "city": tag("CITY")}


def sgml_check(A, rel, client=None, per_name=3, log=_log):
    """G12b — 어긋난 이전 이름마다 창 안 제출(최대 per_name − 1)과 창 앞 제출 하나의 SGML 머리 주소를 FSDS 와 대조. 요청 수 공개."""
    client = client or SecClient()
    rows = []
    for r in rel["rows"]:
        if r["match"] or not r["gid"]:
            continue
        fs = A.filings(r["gid"])
        lo, hi = r["window"][0] + "-01", WC.mshift(r["window"][1], 1) + "-01"
        inw = [x for x in fs if lo <= x[0] < hi]
        before = [x for x in fs if x[0] < lo][-1:]
        pick = before + inw[:max(per_name - 1, 1)]
        for x in pick:
            adsh, cik = x[2], x[8]
            url = SGML_URL % (cik, adsh.replace("-", ""), adsh)
            try:
                txt = client.get(url, "SGML %s" % r["t"]).decode("latin-1", "ignore")
                sa = sgml_business_address(txt)
            except urllib.error.HTTPError as e:
                sa = {"error": e.code}
            except SecDeferred:
                sa = {"error": "deferred"}
            same = bool(sa and "error" not in sa and sa.get("state") == x[5] and sa.get("zip5") == x[7])
            rows.append({"t": r["t"], "filed": x[0], "adsh": adsh, "fsds": {"state": x[5], "zip5": x[7], "city": x[6]}, "sgml": sa, "same": same})
    ok = [x for x in rows if x["sgml"] and "error" not in x["sgml"]]
    doc = {"rule": "G12b", "n": len(rows), "n_ok": len(ok), "n_same": sum(1 for x in ok if x["same"]),
           "all_same": bool(ok) and all(x["same"] for x in ok) and len(ok) == len(rows), "rows": rows, "n_req": client.n_req,
           "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    p = os.path.join(WC.cache_dir("f0"), "w02_sgml_check.json")
    WC.assert_writable(p)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


# ══════════════════════════════════════════════════════════════════════════
#  F0 — 개수만(G12)
# ══════════════════════════════════════════════════════════════════════════
def relocation_check(A, tm, relocs=RELOCATIONS, window=RELOC_WINDOW_M):
    """G12 — 이전 이름마다 주 변경 첫 접수일 · 창 안 여부. tm = §A0 지도 tm(발표월에 효력인 그룹)."""
    rows = []
    for t, ann, s_old, s_new, why in relocs:
        gid = None
        for r in tm.get(t) or []:
            if r[0] <= ann <= r[1] and r[2]:
                gid = r[2]
        fs = A.filings(gid) if gid else []
        first_new, last_old = None, None
        for x in fs:
            st = x[5]
            if st == s_old:
                last_old = x[0]
                first_new = None
            elif st == s_new and last_old is not None and first_new is None:
                first_new = x[0]
        hi = WC.mshift(ann, window)
        ok = bool(first_new and ann <= first_new[:7] <= hi)
        rows.append({"t": t, "gid": gid, "announce": ann, "old": s_old, "new": s_new, "last_old_filed": last_old, "first_new_filed": first_new,
                     "window": [ann, hi], "match": ok, "n_filings": len(fs), "why": why})
    miss = sum(1 for r in rows if not r["match"])
    return {"rows": rows, "n_mismatch": miss, "switch_to_sgml": miss >= RELOC_FAIL_SWITCH, "rule": "G12"}


def coverage_rows(GEO, months):
    """커버리지 F0 — 달마다 초점 수 · 동료 ≥ 3 수 · 비율 · 주소 사유 개수(초점 기준). 값(G)은 보지 않는다(n_peers 만)."""
    out = {}
    for m in months:
        g = GEO.get(m)
        if not g:
            continue
        foc = g["focal"]
        pos = {t: j for j, t in enumerate(g["pool"]["t"])}
        wl = g["pool"].get("why") or ["?"] * len(g["pool"]["t"])
        why = collections.Counter(wl[pos[t]] for t in foc if t in pos)
        n3 = sum(1 for t in foc if (g["geo"].get(t) or {}).get("n_peers", 0) >= MIN_PEERS)
        out[m] = {"n_focal": len(foc), "n_peers3": n3, "share": (n3 / len(foc)) if foc else None, "addr_why": dict(sorted(why.items())),
                  "n_pool": len(g["pool"]["t"]), "n_pool_cbsa": sum(1 for c in g["pool"]["cbsa"] if c)}
    return out


def top_cbsa(GEO, m, k=15, titles=None):
    """그달 초점 이름의 CBSA 분포 — 상위 k 개(코드 · 이름 · 개수 · 몫)."""
    g = GEO[m]
    pos = {t: j for j, t in enumerate(g["pool"]["t"])}
    cnt = collections.Counter(g["pool"]["cbsa"][pos[t]] for t in g["focal"] if t in pos and g["pool"]["cbsa"][pos[t]])
    tot = sum(cnt.values())
    titles = titles or {}
    return {"m": m, "n_with_cbsa": tot, "top": [{"cbsa": c, "name": titles.get(c), "n": n, "share": n / tot} for c, n in cnt.most_common(k)],
            "top_share": (sum(n for _, n in cnt.most_common(k)) / tot) if tot else None, "n_cbsa": len(cnt)}


def f0_main(months=None, log=_log):
    """F0(개수만) → 캐시 f0/w02_f0.json. 🚨 수익 · 신호 값을 찍지 않는다."""
    WG.install_open_audit()
    T0 = time.time()
    A = Addresses.load()
    log("주소 패널 · FSDS 파일 %d · CIK %d · ZIP→CBSA %d · %.0fs" % (A.n_files, len(A.by_cik), len(A.zmap), time.time() - T0))
    import w_panel as _WPN
    U = _WPN.real_universe()   # PN8 내부 가격 오버레이를 얹은 세계
    ms = months or [m for m in U.months if "2016-06" <= m <= "2026-07" and WC.mshift(m, 1) in U.me_idx]
    E = WC.frozen("v_ear").Earnings(U, sameday_primary=True)
    GEO, dens = geo_panel(U, ms, A, E)
    cov = coverage_rows(GEO, ms)
    tier = [m for m in ms if m >= "2016-08"]
    sh = [cov[m]["share"] for m in tier if m in cov and cov[m]["share"] is not None]
    med = float(np.median(sh)) if sh else None
    VD = WC.frozen("v_data")
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    rel = relocation_check(A, im.get("tm") or {})
    titles = delineation()[1]
    tops = {m: top_cbsa(GEO, m, titles=titles) for m in ("2016-08", "2021-08", "2026-07") if m in GEO}
    sg = None
    sp = os.path.join(WC.cache_dir("f0"), "w02_sgml_check.json")
    if os.path.isfile(sp):
        with io.open(sp, encoding="utf-8") as f:
            sg = json.load(f)
    dall = {m: v[0] for m, v in dens.items()}
    months_all = [m for m in U.months if DENS_FROM <= m <= "2026-07" and m in U.me_idx]
    for m in months_all:
        if m not in dens:
            dall[m] = density_month(U.members(m), U.d_of(m), E.key_of, E.ed)[0]
    zs = density_z(dall, months_all)
    zt = [zs[m] for m in tier if zs.get(m) is not None]
    th = [theta_c(zs.get(m)) for m in tier]
    doc = {"card": "W02", "rule": "F0 개수만(명세 f0_gates · 등록 B 자료 관문) — 수익 · 신호 값 없음", "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "fsds": {"n_files": A.n_files, "n_cik": len(A.by_cik)}, "hud": build_hud(log=lambda *_: None),
           "coverage": {"gate": COV_GATE, "median_share": med, "pass": med is not None and med >= COV_GATE, "T": len(sh),
                        "min_share": min(sh) if sh else None, "max_share": max(sh) if sh else None, "by_month": cov},
           "relocation": rel, "sgml_check": sg, "top_cbsa": tops,
           "density": {"n_state": len(zt), "z_quantiles": [float(np.quantile(zt, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)] if zt else None,
                       "n_z_gt1": sum(1 for z in zt if z > 1), "n_z_lt_m1": sum(1 for z in zt if z < -1),
                       "theta_min": min(th) if th else None, "theta_max": max(th) if th else None, "n_theta_off": sum(1 for x in th if x != THETA0)},
           "decision": {"close_card": not (med is not None and med >= COV_GATE), "switch_to_sgml": rel["switch_to_sgml"],
                        "sgml_changes_values": (None if sg is None else not sg.get("all_same")),
                        "address_source": ("FSDS sub.txt(= SGML 머리 · 표본 대조 같음 · G12b)" if (rel["switch_to_sgml"] and sg and sg.get("all_same"))
                                           else ("SGML 전수 필요" if rel["switch_to_sgml"] else "FSDS sub.txt"))},
           "noeg": {k: v for k, v in WG.noeg_report().items() if k in ("ok",)}, "sec": round(time.time() - T0, 1)}
    p = os.path.join(WC.cache_dir("f0"), "w02_f0.json")
    WC.assert_writable(p)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(실자료 신호 · y 와 평가 수익은 씨앗 잡음 · 산출은 열지 않고 삭제 — w_hygiene.blind_smoke)
# ══════════════════════════════════════════════════════════════════════════
SMOKE_FROM, SMOKE_TO = "2016-06", "2026-07"
TIER_FROM, TIER_TO = "2016-08", "2026-07"
N_SMOKE_SHUFFLE = 3                                           # 연기는 모양만(굽기는 N_SHUFFLE 1,000)


def smoke_setup(log=_log):
    """연기 공통 — 우주 · 일간 행렬 · 합집합 시장 · Stage M-W 연기 패널(w_cards.smoke_panel · kind real → 곧바로 눈가림) · 슬리브 단면."""
    import w_cards as WCD
    import w_ipca as IP
    T0 = time.time()
    import w_panel as _WPN
    U = _WPN.real_universe()   # PN8 내부 가격 오버레이를 얹은 세계
    keys = sorted(U.PX)
    kcol = {k: j for j, k in enumerate(keys)}
    DR = np.column_stack([U.daily_ret(k) for k in keys])
    months = [m for m in U.months if SMOKE_FROM <= m <= SMOKE_TO and WC.mshift(m, 1) in U.me_idx]
    mkt_d = IP.union_daily_market(U, [WC.mshift(months[0], -1)] + months, DR=DR, kcol=kcol)
    P, X = WCD.smoke_panel(U, months, DR, kcol, mkt_d, log=lambda *_: None)
    log("연기 준비 · 패널 달 %d · 슬리브 단면 %d · %.0fs" % (len(P["months"]), len(X), time.time() - T0))
    return U, P, X, months


def d0_path(books, ret_of, execute):
    """연기 · 굽기 D0 경로(체결 규칙을 받는다) — (S{보유 달}, traded{보유 달})."""
    C = WC.frozen("v_core")
    S, T, Ed = {}, {}, None
    for m in sorted(books):
        tgt = books[m]
        if Ed is None:
            E, tr = dict(tgt), 0.0
        else:
            E, tr, _ = execute(Ed, tgt)
        Ed, R, _ = C.drift_book(E, ret_of(m))
        h = WC.mshift(m, 1)
        S[h], T[h] = R, tr
    return S, T


def _noise_ret(pb, X, seed):
    rng = np.random.default_rng(seed)
    base = {m: {t: float(v) / 100.0 for t, v in zip(pb["m"][m]["t"], pb["m"][m]["y"]) if v == v} for m in pb["m"]}

    def ret_of(m):
        b = dict(base.get(m, {}))
        for t in (X[m].t if m in X else []):
            if t not in b:
                b[t] = float(rng.normal(0, 0.08))
        return b
    return ret_of


def blind_run(U, GEOP, dens, X, seed):
    """w_hygiene.blind_smoke 에 넘기는 run(pb, out) — W02 주 · INDMOM · 평활 · CBSA 섞기(3) · σ · S/C 책 · D0 · 펀드 X · 무해. 🚨 수익은 pb.y 또는 잡음."""
    import pickle
    import pandas as pd
    import w_stagem as S

    def run(pb, out):
        assert pb["kind"] == "blind"
        rng = np.random.default_rng(seed + 1)
        ms = [m for m in pb["months"] if TIER_FROM <= m <= TIER_TO and m in GEOP]
        res = {"main": w02_fm(pb, GEOP, "blind", months=ms), "indmom": w02_fm(pb, GEOP, "blind", months=ms, variant="indmom")}
        g3 = smooth3({m: {t: v["G"] for t, v in GEOP[m]["geo"].items()} for m in GEOP}, ms)
        res["smooth3"] = w02_fm(pb, GEOP, "blind", months=ms, variant="smooth3", g3_by_month=g3)
        res["sigma"] = S.sigma_analytic(res["main"]["fm"]["parts"], "geo_g")
        sh = cbsa_shuffle(pb, GEOP, "blind", n=N_SMOKE_SHUFFLE, seed=SHUFFLE_SEED, months=ms)
        res["shuffle_pct"] = S.placebo_rank(res["main"]["summary"]["nw_t"], sh["t"], +1)
        zs = density_z(dens, sorted(dens))
        th = {m: theta_c(zs.get(m)) for m in ms}
        ret_of = _noise_ret(pb, X, seed + 2)
        rate = w02_cost_rate(U)
        for arm, thf in (("S", lambda m: THETA0), ("C", lambda m: th[m])):
            books = {}
            for m in ms:
                if m not in X:
                    continue
                w, _ = w02_book(X[m], GEOP[m]["geo"], thf(m))
                if w is not None:
                    books[m] = X[m].book(w)
            Sx, Tx = d0_path(books, ret_of, w02_execute)
            idx = pd.PeriodIndex(sorted(Sx), freq="M")
            Ss = pd.Series([Sx[str(p)] for p in idx], index=idx)
            Bs = pd.Series(rng.normal(0.008, 0.04, len(idx)), index=idx)
            rt = pd.Series([rate.get(WC.mshift(str(p), -1), 0.001) for p in idx], index=idx)
            Xf = WC.fund_x(Ss, Bs, rt, traded=pd.Series([Tx[str(p)] for p in idx], index=idx), mult=2.0)
            res["tier2_" + arm] = WC.tier2_harmless({str(p): float(v) for p, v in Xf.items()}, WC.turnover_annual(list(Tx.values())), True)
            res["books_" + arm] = len(books)
            assert len(books) >= 100 and res["tier2_" + arm]["n"] >= 100 and res["tier2_" + arm]["n_down"] >= 20, "모양: 책 · Tier-2 달 수"
        assert res["main"]["summary"]["T"] >= 100 and res["indmom"]["summary"]["T"] >= 100 and res["smooth3"]["summary"]["T"] >= 100, "모양: FM 달 수"
        assert len(sh["t"]) == N_SMOKE_SHUFFLE and np.isfinite(sh["t"]).all(), "모양: 섞기"
        with open(os.path.join(out, "w02_blind.pkl"), "wb") as f:
            pickle.dump(res, f)
        return res
    return run


def blind_smoke_main(log=_log):
    """W02 실자료 눈가린 연기 — 찍는 것: 참/거짓 · 시간 · 개수 · G-NoEG 세 겹 · 얼린 모듈. 값(수익 · γ · t · IC)은 찍지 않는다."""
    import w_hygiene as H
    WG.install_open_audit()
    probs = WC.env_problems()
    if probs:
        raise SystemExit("🚨 환경 핀: %s" % probs)
    fz = WC.frozen_check()
    if not fz["ok"]:
        raise SystemExit("🚨 얼린 V 모듈 핀 어긋남: %s" % fz["bad"])
    T0 = time.time()
    U, P, X, months = smoke_setup(log)
    A = Addresses.load()
    E = WC.frozen("v_ear").Earnings(U, sameday_primary=True)
    GEOP, dens = geo_panel(U, months, A, E, log=lambda *_: None)
    for m in [m for m in U.months if DENS_FROM <= m < SMOKE_FROM]:
        dens[m] = density_month(U.members(m), U.d_of(m), E.key_of, E.ed)
    dv = {m: v[0] for m, v in dens.items()}
    log("W02 입력 · 달 %d · %.0fs" % (len(GEOP), time.time() - T0))
    r = H.blind_smoke(blind_run(U, GEOP, dv, X, WC.SEED), P, WC.SEED)
    nr = WG.noeg_report()
    lf = WC.loaded_frozen_check()
    out = {"blind_smoke": {k: r[k] for k in ("ok", "sec", "n_files", "bytes", "deleted", "err", "returned")},
           "noeg": {"ok": nr["ok"], "static": nr["static"]["ok"], "runtime": nr["runtime"]["ok"], "open_audit": nr["open_audit"].get("ok"),
                    "n_opened": nr["open_audit"].get("n_opened"), "n_black": nr["open_audit"].get("n_black")},
           "loaded_frozen": lf["ok"], "frozen_pins": fz["ok"], "total_sec": round(time.time() - T0, 1)}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if (r["ok"] and nr["ok"] and lf["ok"]) else 1


def file_sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def digest(rows):
    """[(id, …)] 목록의 sha256(정렬 JSON) — 자료 핀 한 줄."""
    return hashlib.sha256(json.dumps(sorted(rows), ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def manifest():
    """W02 자료 핀(등록 B 문서 · 러너 manifest 용) — FSDS 분기마다 원 ZIP sha256 · 추출 파일 sha256 · 행 수 · HUD · 획정 파일 sha256 · 전체 요약 sha."""
    rows = []
    for fn in sorted(os.listdir(fsds_dir())):
        if not fn.endswith("_sub10.json.gz"):
            continue
        p = os.path.join(fsds_dir(), fn)
        d = read_json_gz(p)
        rows.append([d["q"], d["zip_sha256"], file_sha256(p), d["n_rows"]])
    h = build_hud(log=lambda *_: None)
    doc = {"card": "W02", "fsds": rows, "fsds_digest": digest(rows), "hud": h["hud"], "delineation": h["delineation"], "vintage": HUD_VINTAGE,
           "earn_dates_sha256": file_sha256(WC.frozen("v_data").lab_path("data/earn_dates.json")),
           "issuer_map_sha256": file_sha256(WC.frozen("v_data").lab_path("data/_issuer_map.json"))}
    doc["digest"] = digest([["fsds", doc["fsds_digest"]], ["hud", h["hud"]["sha256"]], ["delin", h["delineation"]["sha256"]],
                            ["earn", doc["earn_dates_sha256"]], ["im", doc["issuer_map_sha256"]]])
    p = os.path.join(WC.cache_dir("f0"), "w02_manifest.json")
    WC.assert_writable(p)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


def plan():
    """재개 계획 — 받은 FSDS 분기 · HUD · 미룸 기록."""
    have = sorted(fn[:6] for fn in os.listdir(fsds_dir()) if fn.endswith("_sub10.json.gz"))
    notes = notes_path()
    return {"fsds_have": have, "fsds_from": FSDS_FROM, "hud": os.path.isfile(hud_path()), "deferral_notes": notes if os.path.isfile(notes) else None,
            "resume": "python build/w_geo.py --build(있는 분기는 건너뛴다)"}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 · 망 없음)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn, exc=SystemExit):
    try:
        fn()
    except exc:
        return True
    return False


class _FakeEdgar:
    UA = "x"

    def __init__(self, fails):
        self.fails = list(fails)
        self.calls = 0

    def fetch_bytes(self, url, timeout=60, max_wait=None, accept=None):
        self.calls += 1
        if self.fails:
            code = self.fails.pop(0)
            if code == "conn":
                raise ConnectionError("x")
            raise urllib.error.HTTPError(url, code, "x", {}, None)
        return b"ok"


def _st_sec():
    td = tempfile.mkdtemp(prefix="wg_sec_", dir=WC.cache_dir("selftest"))
    slept = []
    E = _FakeEdgar([429, 503, "conn"])
    C = SecClient(edgar=E, gap=0.0, block_limit=1000, wait0=15, sleep=slept.append, gate_dir=td, log=lambda *_: None)
    assert C.get("https://www.sec.gov/x.zip") == b"ok" and E.calls == 4 and [x for x in slept if x >= 1] == [15, 30, 60], slept
    E2 = _FakeEdgar([404])
    C2 = SecClient(edgar=E2, gap=0.0, sleep=slept.append, gate_dir=td, log=lambda *_: None)
    assert _raises(lambda: C2.get("https://www.sec.gov/y.zip"), urllib.error.HTTPError) and E2.calls == 1
    old = os.environ.get("WBATCH_NOTES")
    os.environ["WBATCH_NOTES"] = os.path.join(td, "notes.md")
    try:
        E3 = _FakeEdgar([429] * 20)
        sl3 = []
        C3 = SecClient(edgar=E3, gap=0.0, block_limit=100, wait0=15, sleep=sl3.append, gate_dir=td, log=lambda *_: None)
        big = [x for x in sl3 if x >= 1]
        assert _raises(lambda: C3.get("https://www.sec.gov/z.zip", "FSDS t"), SecDeferred)
        big = [x for x in sl3 if x >= 1]
        assert sum(big) <= 100 and big == [15, 30], sl3
        with io.open(os.environ["WBATCH_NOTES"], encoding="utf-8") as f:
            assert "z.zip" in f.read()
    finally:
        if old is None:
            os.environ.pop("WBATCH_NOTES", None)
        else:
            os.environ["WBATCH_NOTES"] = old
    assert _raises(lambda: C.get("https://www.huduser.gov/a.xlsx")) and _raises(lambda: web_get("https://www.sec.gov/files/x.zip"))
    # 간격 — 실제 시계로 두 요청 사이 ≥ gap
    E4 = _FakeEdgar([])
    C4 = SecClient(edgar=E4, gap=0.3, gate_dir=td, log=lambda *_: None)
    t0 = time.time()
    C4.get("https://www.sec.gov/a")
    C4.get("https://www.sec.gov/b")
    assert time.time() - t0 >= 0.29
    html = '<a href="/files/dera/data/financial-statement-data-sets/2016q1.zip">x</a><a href="/files/x/readme.zip">r</a>' \
           '<a href="/files/dera/data/financial-statement-data-sets/2016q1.zip">dup</a>'
    assert index_zips(html, r"\d{4}q[1-4]\.zip") == [("2016q1.zip", "https://www.sec.gov/files/dera/data/financial-statement-data-sets/2016q1.zip")]
    import shutil
    shutil.rmtree(td, ignore_errors=True)
    return "SEC 규약(지수 대기 15·30·60 · 404 즉시 · 30분 한도 → 미룸 + 노트 · SEC 밖 호스트 거부 · 간격 · 색인 파싱) — 망 없음"


def _fake_fsds_zip(rows):
    hdr = ["adsh", "cik", "name", "sic", "countryba", "stprba", "cityba", "zipba", "bas1", "form", "period", "filed", "accepted"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        lines = ["\t".join(hdr)] + ["\t".join(str(r.get(h, "")) for h in hdr) for r in rows]
        z.writestr("sub.txt", "\n".join(lines) + "\n")
        z.writestr("num.txt", "x")
    return buf.getvalue()


def _st_address():
    rows = [dict(adsh="a1", cik=11, name="OLD CO", countryba="US", stprba="IL", cityba="CHICAGO", zipba="60606", form="10-Q", period="20190630",
                 filed="20190801", accepted="2019-08-01 10:00:00.0"),
            dict(adsh="a2", cik=11, name="OLD CO", countryba="US", stprba="VA", cityba="ARLINGTON", zipba="22202-1234", form="10-Q",
                 period="20220630", filed="20220727", accepted="2022-07-27 10:00:00.0"),
            dict(adsh="a3", cik=11, countryba="US", stprba="VA", zipba="22202", form="8-K", filed="20220801"),
            dict(adsh="a4", cik=22, countryba="IE", stprba="", cityba="DUBLIN", zipba="-", form="10-K", filed="20200301"),
            dict(adsh="a5", cik=33, countryba="US", stprba="TX", cityba="AUSTIN", zipba="78741", form="10-K/A", filed="20210301"),
            dict(adsh="a6", cik=44, countryba="US", stprba="TX", cityba="X", zipba="99999", form="10-K", filed="20210301")]
    cols, kept, n = fsds_extract(_fake_fsds_zip(rows))
    assert n == 6 and len(kept) == 5 and cols == list(FSDS_COLS)                    # 8-K 는 뺀다
    by = {}
    c = {k: i for i, k in enumerate(cols)}
    for r in kept:
        by.setdefault(int(r[c["cik"]]), []).append((_iso8(r[c["filed"]]), r[c["accepted"]], r[c["adsh"]], r[c["form"]], r[c["countryba"]],
                                                    r[c["stprba"]], r[c["cityba"]], zip5(r[c["zipba"]])))
    zmap = {"60606": "16980", "22202": "47900", "78741": "12420", "99999": None}
    groups = {"g11": {"ciks": [[11, None, None, "x", "OLD"]]}, "g2": {"ciks": [[22, None, None, "x", "IE"]]},
              "g33": {"ciks": [[33, "2021-01-01", "2021-12-31", "x", "A"]]}, "g44": {"ciks": [[44, None, None, "x", "B"]]},
              "gx": {"ciks": [[33, "2022-01-01", None, "x", "late"]]}}
    A = Addresses(by, zmap, groups)
    assert A.cbsa("g11", "2019-08-01") == (None, "no_filing")                     # 접수 당일은 아직(filed < d)
    assert A.cbsa("g11", "2019-08-02") == ("16980", "ok") and A.cbsa("g11", "2022-07-28") == ("47900", "ok")
    assert A.at("g11", "2022-07-28")["zip5"] == "22202" and A.cbsa("g11", "2020-07-27") == ("16980", "ok")
    assert A.cbsa("g11", "2022-07-27") == (None, "no_filing")                     # 앞 접수가 550일보다 낡음
    assert A.cbsa("g11", "2021-06-01") == (None, "no_filing")                      # 550일보다 낡음
    assert A.cbsa("g2", "2020-06-01") == (None, "non_us") and A.cbsa("g33", "2021-06-01") == ("12420", "ok")
    assert A.cbsa("gx", "2021-06-01") == (None, "no_filing")                        # 효력 구간 밖 제출은 그 그룹 것이 아니다
    assert A.cbsa("g44", "2021-06-01") == (None, "non_cbsa")
    rel = relocation_check(A, {"OLD": [["2014-06", "2026-09", "g11", 11, [11], 0, "x", 0]]},
                           relocs=(("OLD", "2022-05", "IL", "VA", "t"), ("OLD", "2018-01", "IL", "VA", "early")))
    assert rel["rows"][0]["match"] and rel["rows"][0]["first_new_filed"] == "2022-07-27" and not rel["rows"][1]["match"] and rel["n_mismatch"] == 1
    zm, st = zip_cbsa_map([("00501", "35620", 0, 1.0, 0, 1.0), ("10001", "35620", 0.4, 0.2, 0, 0.3), ("10001", "35614", 0.6, 0.8, 0, 0.7),
                           ("20001", "99999", 0, 1, 0, 1), ("30001", "12060", 0, 0.5, 0, 0.5), ("30001", "12000", 0, 0.5, 0, 0.5)])
    assert zm == {"00501": "35620", "10001": "35614", "20001": None, "30001": "12000"} and st["n_non_cbsa"] == 1
    zr, st2 = zip_cbsa_map([("10001", "35614", 0, 0.3, 0, 0.3), ("10001", "35084", 0, 0.3, 0, 0.3), ("10001", "10000", 0, 0.4, 0, 0.4)],
                           {"35614": "35620", "35084": "35620"})
    assert zr == {"10001": "35620"} and st2["n_rows_div_rolled"] == 2                 # 분할을 올려 더한 뒤 최대(0.6 > 0.4)
    hdr = ("<SEC-HEADER>\n<FILER>\n<COMPANY-DATA>\n<CONFORMED-NAME>X CO\n</COMPANY-DATA>\n<BUSINESS-ADDRESS>\n<STREET1>1 MAIN\n"
           "<CITY>ARLINGTON\n<STATE>VA\n<ZIP>22202-4321\n<PHONE>1\n</BUSINESS-ADDRESS>\n<MAIL-ADDRESS>\n<STATE>IL\n</MAIL-ADDRESS>\n")
    assert sgml_business_address(hdr) == {"state": "VA", "zip5": "22202", "city": "ARLINGTON"} and sgml_business_address("x") is None
    # HUD xlsx 읽기(합성 파일)
    import openpyxl
    td = tempfile.mkdtemp(prefix="wg_hud_", dir=WC.cache_dir("selftest"))
    p = os.path.join(td, "h.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ZIP", "CBSA", "RES_RATIO", "BUS_RATIO", "OTH_RATIO", "TOT_RATIO"])
    ws.append([501, 35620, 0, 1, 0, 1])
    ws.append(["07950", "35620", 0.1, 0.9, 0, 0.5])
    wb.save(p)
    rr = zip_cbsa_rows(p)
    assert rr[0][:2] == ("00501", "35620") and rr[1][:2] == ("07950", "35620")
    import shutil
    shutil.rmtree(td, ignore_errors=True)
    return "FSDS sub.txt 추출(서식 거르기) · 주소 PIT(filed < d · 550일 · 효력 구간 · 비미국 · CBSA 밖) · 이전 점검(창 안/밖) · ZIP→CBSA 규칙 · xlsx"


def _brute_geo(pool, t, min_peers=MIN_PEERS):
    n = len(pool["t"])
    rsec = sector_vw(pool["sec"], pool["me0"], pool["r"])
    j = pool["t"].index(t)
    if pool["sec"][j] is None or pool["cbsa"][j] is None:
        return None, 0, None, 0
    num = den = 0.0
    k = 0
    num2 = den2 = 0.0
    k2 = 0
    for q in range(n):
        if pool["cbsa"][q] is None or pool["cbsa"][q] != pool["cbsa"][j] or pool["gid"][q] == pool["gid"][j]:
            continue
        if pool["sec"][q] is None or pool["me0"][q] is None or not pool["me0"][q] > 0 or pool["r"][q] is None or pool["sec"][q] not in rsec:
            continue
        ex = pool["r"][q] - rsec[pool["sec"][q]]
        if pool["sec"][q] != pool["sec"][j]:
            num += pool["me0"][q] * ex
            den += pool["me0"][q]
            k += 1
        else:
            num2 += pool["me0"][q] * ex
            den2 += pool["me0"][q]
            k2 += 1
    return (num / den if k >= min_peers else None), k, (num2 / den2 if k2 >= 1 else None), k2


def _synth_pool(rng, n=240, n_cbsa=12, secs=("A", "B", "C", "D", FIN_SECTOR)):
    cb = [("c%02d" % rng.integers(0, n_cbsa)) if rng.random() > 0.1 else None for _ in range(n)]
    sec = [secs[rng.integers(0, len(secs))] if rng.random() > 0.03 else None for _ in range(n)]
    me0 = [float(rng.lognormal(3, 1)) if rng.random() > 0.02 else None for _ in range(n)]
    r = [float(rng.normal(0.01, 0.08)) if rng.random() > 0.02 else None for _ in range(n)]
    mom = [float(rng.normal(0.1, 0.3)) for _ in range(n)]
    return {"t": ["T%03d" % i for i in range(n)], "k": ["T%03d" % i for i in range(n)], "gid": ["g%03d" % i for i in range(n)], "sec": sec,
            "cbsa": cb, "me0": me0, "r": r, "mom": mom}


def _st_signal():
    rng = np.random.default_rng(WC.SEED)
    for rep in range(4):
        P = _synth_pool(rng)
        foc = [t for t, s in zip(P["t"], P["sec"]) if s != FIN_SECTOR]
        got = geo_month(P, foc)
        for t in foc:
            G, k, G2, k2 = _brute_geo(P, t)
            g = got[t]
            assert g["n_peers"] == k and g["n_same"] == k2, (t, g, k, k2)
            assert (G is None and g["G"] is None) or abs(G - g["G"]) < 1e-12
            assert (G2 is None and g["geo_same"] is None) or abs(G2 - g["geo_same"]) < 1e-12
    # 섹터 수익이 곧 이름 수익이면(초과 0) G = 0
    P = _synth_pool(rng)
    rs = {s: 0.03 for s in set(P["sec"]) if s}
    P0 = dict(P, r=[rs.get(s) if s else None for s in P["sec"]])
    g0 = geo_month(P0, P["t"])
    assert all(abs(v["G"]) < 1e-12 for v in g0.values() if v["G"] is not None)
    assert any(v["G"] is not None for v in g0.values())
    # 섹터 VW · 자기 섹터 통제 · INDMOM
    rsec = sector_vw(P["sec"], P["me0"], P["r"])
    t = next(t for t, s in zip(P["t"], P["sec"]) if s == "A")
    assert abs(geo_month(P, [t])[t]["own_sec_ret"] - rsec["A"]) < 1e-15
    assert abs(geo_month(P, [t])[t]["indmom"] - sector_vw(P["sec"], P["me0"], P["mom"])["A"]) < 1e-15
    # 같은 그룹 두 줄(다른 섹터)은 동료가 아니다
    P2 = {k: list(v) for k, v in P.items()}
    P2["t"].append("DUP")
    P2["k"].append("DUP")
    j = P["t"].index(t)
    P2["gid"].append(P["gid"][j])
    P2["sec"].append("B")
    P2["cbsa"].append(P["cbsa"][j] or "c00")
    P2["cbsa"][j] = P2["cbsa"][-1]
    P2["me0"].append(5.0)
    P2["r"].append(0.2)
    P2["mom"].append(0.0)
    a = geo_month(P2, [t])[t]
    b = _brute_geo(P2, t)
    assert a["n_peers"] == b[1] and ((a["G"] is None and b[0] is None) or abs(a["G"] - b[0]) < 1e-12)
    # 섞기 — (CBSA, 섹터) 개수 보존 · 라벨 없는 자리 그대로
    lab = shuffle_labels(P["cbsa"], P["sec"], np.random.default_rng(1))
    assert collections.Counter(zip(lab, P["sec"])) == collections.Counter(zip(P["cbsa"], P["sec"]))
    assert all(lab[j] is None for j in range(len(lab)) if P["cbsa"][j] is None)
    assert lab != P["cbsa"]
    # 평활 쌍둥이
    gm = {"2020-01": {"a": 1.0, "b": 2.0}, "2020-02": {"a": 2.0, "b": None}, "2020-03": {"a": 3.0, "b": 1.0}}
    s3 = smooth3(gm, ["2020-03"])
    assert s3 == {"2020-03": {"a": 2.0}}
    # z
    z = xs_z([1.0, 2.0, 3.0, np.nan])
    assert np.isnan(z[3]) and abs(z[0] + 1.0) < 1e-12
    return "G = 무작정 계산과 1e−12(4 합성 달) · 동료 문턱 · 같은 섹터 · 같은 그룹 제외 · 초과 0 → G 0 · 섹터 VW · INDMOM · 섞기 보존 · 평활 · z"


def _st_theta():
    assert theta_c(None) == 0.5 and abs(theta_c(5) - 0.8) < 1e-15 and abs(theta_c(-5) - 0.2) < 1e-15 and abs(theta_c(0.5) - 0.65) < 1e-15
    ms = WC.months_between("2014-01", "2020-12")
    rng = np.random.default_rng(WC.SEED)
    dens = {m: float(rng.uniform(0.1, 0.9)) for m in ms}
    z = density_z(dens, ms)
    assert all(z[m] is None for m in ms if m < "2014-06")
    first = [m for m in ms if z[m] is not None][0]
    assert first == WC.mshift("2014-06", DENS_MIN_N - 1)
    cut = "2018-06"
    z2 = density_z({m: v for m, v in dens.items() if m <= cut}, [m for m in ms if m <= cut])
    assert all(z2[m] == z[m] for m in z2)                                            # 선견 없음(자른 자료 = 전체)
    ed = {"A": ["2020-01-15", "2020-02-03"], "B": ["2020-02-28"], "C": []}
    mem = [{"t": "A", "k": "A"}, {"t": "B", "k": "B"}, {"t": "C", "k": "C"}, {"t": "D", "k": "D"}]
    kf = lambda t, k: t if t in ed else None
    assert density_month(mem, "2020-02-27", kf, ed) == (1 / 3, 3, 1) and density_month(mem, "2020-02-28", kf, ed) == (2 / 3, 3, 2)
    return "θ 사상 [0.2, 0.8] · 결측 θ0 · 밀도(그달 1일 ~ d · 분모 = 키 있는 회원) · 확장창 z(2014-06 · 24 관측 · 선견 없음)"


def _synth_panel(seed, months, n=200, beta=0.0, kind="synth"):
    """합성 패널 + GEO — y = β·z(G) + 잡음. 통제 · 풀 구조는 실자료 꼴과 같다."""
    rng = np.random.default_rng(seed)
    P = {"kind": kind, "months": list(months), "m": {}}
    GEO = {}
    secs = ("A", "B", "C", "D", "E")
    for m in months:
        pool = _synth_pool(rng, n=n, secs=secs)
        foc = list(pool["t"])
        geo = geo_month(pool, foc)
        g = np.array([np.nan if geo[t]["G"] is None else geo[t]["G"] for t in foc])
        zg = xs_z(g)
        y = np.where(np.isfinite(zg), beta * zg, 0.0) + rng.normal(0, 1.0, len(foc))
        D = {"t": foc, "y": y, "log_me": rng.normal(8, 1, len(foc)), "r1": rng.normal(0, 0.08, len(foc)), "mom": rng.normal(0.1, 0.3, len(foc)),
             "val": np.where(rng.random(len(foc)) < 0.05, np.nan, rng.normal(0, 1, len(foc))),
             "sec": np.array([s if s else "A" for s in pool["sec"]], object), "me": np.exp(rng.normal(8, 1, len(foc)))}
        P["m"][m] = D
        GEO[m] = {"pool": pool, "focal": foc, "geo": geo}
    return P, GEO


def _st_card():
    ms = WC.months_between("2016-08", "2021-07")
    P0, G0 = _synth_panel(WC.SEED, ms, beta=0.0)
    P1, G1 = _synth_panel(WC.SEED, ms, beta=0.25)
    r0 = w02_fm(P0, G0, "synth")
    r1 = w02_fm(P1, G1, "synth")
    assert r0["summary"]["T"] == len(ms) and r1["summary"]["nw_t"] > 3.0 and abs(r0["summary"]["nw_t"]) < 3.5, (r0["summary"], r1["summary"])
    ri = w02_fm(P1, G1, "synth", variant="indmom")
    assert ri["summary"]["T"] == len(ms)
    g3 = smooth3({m: {t: v["G"] for t, v in G1[m]["geo"].items()} for m in ms}, ms)
    rs = w02_fm(P1, G1, "synth", variant="smooth3", g3_by_month=g3, months=ms[2:])
    assert rs["summary"]["T"] == len(ms) - 2
    sh = cbsa_shuffle(P1, G1, "synth", n=12, seed=SHUFFLE_SEED, months=ms[:24])
    import w_stagem as S
    r1b = w02_fm(P1, G1, "synth", months=ms[:24])
    pct = S.placebo_rank(r1b["summary"]["nw_t"], sh["t"], +1)
    assert len(sh["t"]) == 12 and np.isfinite(sh["t"]).all() and pct >= 0.9, (pct, sh["t"])
    assert _raises(lambda: w02_fm(dict(P1, kind="real"), G1, "real"))                 # 등록 전 실자료 거부
    assert _raises(lambda: cbsa_shuffle(dict(P1, kind="real"), G1, "real", n=2))
    assert _raises(lambda: w02_fm(P1, G1, "blind"))                                   # 종류 어긋남
    cov = coverage_rows(G1, ms[:3])
    assert all(0 <= v["share"] <= 1 and v["n_focal"] == 200 for v in cov.values())
    return "FM(심은 효과 t > 3 · 효과 0 에서 작음) · INDMOM · 평활 쌍둥이 · CBSA 섞기 백분위 · kind 자물쇠 · 커버리지 개수"


def _st_book():
    import w_cards as WCD
    rng = np.random.default_rng(WC.SEED + 1)
    n = 60
    t = ["N%02d" % i for i in range(n)]
    sec = [("S%d" % (i % 5)) if i % 7 else FIN_SECTOR for i in range(n)]
    me = rng.lognormal(4, 1, n)
    X = WCD.Cross("2020-01", t, me, me, sec, np.zeros(n, bool), rng.normal(1, 0.2, n))
    geo = {tt: {"G": float(rng.normal())} for tt in t[:50]}
    w, info = w02_book(X, geo, 0.5)
    assert w is not None and abs(w.sum() - 1) < 1e-9 and info["n_sel"] == round(0.3 * sum(1 for i in range(50) if sec[i] != FIN_SECTOR))
    fin = np.array([s == FIN_SECTOR for s in sec])
    wB = X.wB
    assert np.max(np.abs(w - wB)) <= 0.05 + 1e-9
    ge = gegd_entry(X, geo)
    assert abs(sum(ge["book"].values()) - 1) < 1e-9 and len(ge["signal"]) == 50
    w0, _ = w02_book(X, geo, 0.0)
    assert np.max(np.abs(w0 - wB)) < 1e-6                                           # θ 0 → w_B(β 띠 뒤)
    b, tr, sk = w02_execute(X.book(wB), X.book(w))
    assert abs(sum(b.values()) - 1) < 1e-9 and tr <= WCD.TURN_BUDGET_MONTH + 1e-9
    assert fin.any()
    return "1개월 신호 책(버퍼 없음 · q 0.3 · 발행사 상한 · 합 1) · 전량 체결 → 회전 예산"


def _st_static():
    r = WG.noeg_static(targets=["w_geo"])
    assert r["ok"], {k: r[k] for k in ("hits", "literal_hits", "unpinned", "separate_violations")}
    import ast
    with io.open(os.path.abspath(__file__), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    calls = [nd for nd in ast.walk(tree) if isinstance(nd, ast.Call) and
             ((isinstance(nd.func, ast.Attribute) and nd.func.attr == "urlopen") or (isinstance(nd.func, ast.Name) and nd.func.id == "urlopen"))]
    assert not calls                                                                   # validate_site «SEC 호출 경로» — urlopen 없음
    return "G-NoEG 정적(w_geo 폐포 %d · 금지 없음 · 핀 안) · urlopen 호출 없음(SEC 는 edgar 한 곳)" % r["n_reached"]


def selftest():
    res, ok = [], True
    for fn in (_st_sec, _st_address, _st_signal, _st_theta, _st_card, _st_book, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                              # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_geo selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--build" in sys.argv:
        qf = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else FSDS_FROM
        r = build_fsds(q_from=qf)
        h = build_hud()
        print(json.dumps({"fsds": {k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()}, "fsds_deferred": r["deferred"],
                          "hud_sha256": h["sha256"][:16]}, ensure_ascii=False))
        raise SystemExit(0 if not r["deferred"] else 2)
    if "--f0" in sys.argv:
        doc, p = f0_main()
        print(json.dumps({"coverage_median": doc["coverage"]["median_share"], "coverage_pass": doc["coverage"]["pass"],
                          "relocation_mismatch": doc["relocation"]["n_mismatch"], "switch_to_sgml": doc["relocation"]["switch_to_sgml"],
                          "path": p, "sec": doc["sec"]}, ensure_ascii=False))
        raise SystemExit(0)
    if "--blind-smoke" in sys.argv:
        raise SystemExit(blind_smoke_main())
    if "--manifest" in sys.argv:
        doc, p = manifest()
        print(json.dumps({"n_fsds": len(doc["fsds"]), "digest": doc["digest"], "path": p}, ensure_ascii=False))
        raise SystemExit(0)
    if "--sgml-check" in sys.argv:
        A = Addresses.load()
        VD = WC.frozen("v_data")
        rel = relocation_check(A, VD.read_json(VD.lab_path("data/_issuer_map.json")).get("tm") or {})
        doc, p = sgml_check(A, rel)
        print(json.dumps({k: doc[k] for k in ("n", "n_ok", "n_same", "all_same", "n_req")}, ensure_ascii=False))
        raise SystemExit(0)
    if "--plan" in sys.argv:
        print(json.dumps(plan(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    print(__doc__)
