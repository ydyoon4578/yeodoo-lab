# -*- coding: utf-8 -*-
"""build/x_intl.py — 배치 X · I 층(국외 재현) 패널: 국가 ETF 10 → 현지 통화 TR · 현지 3개월 금리 초과 · T+1 행 · 커버리지 · 대체 · USD 전환.

설계 원본(구속): xbatch_research.json evaluation.I_international_20y · data_plan.international · availability_lags ·
  rule_20y_compliance · build_plan(x_intl · selftests «I 층 FX 역수 방향») · decisions D-7 · D-8 — 저장소 밖 스크래치.
  이 파일은 설계를 다시 짓지 않는다. 옮기는 것은 명세의 시장 목록 · FX 방향 · 대체 순서 · 수익 정의 · 현지 금리 · T+1 체결 · USD 전환 규칙뿐이다.
  BEAR 상태 기계(x_signals) · 관문 I-C1~C4 · 풀링 DK t(x_eval)는 이 파일에 없다 — 이 파일은 패널 자료만 낸다.

명세 옮김(그대로):
  시장      JP EWJ DEXJPUS · GB EWU DEXUSUK(역수) · DE EWG DEXUSEU(역수) · FR EWQ DEXUSEU(역수) · IT EWI DEXUSEU(역수) ·
            CH EWL DEXSZUS · SE EWD DEXSDUS · CA EWC DEXCAUS · AU EWA DEXUSAL(역수) · KR EWY DEXKOUS
  대체 순서 NL EWN → ES EWP (FX 는 둘 다 DEXUSEU(역수) · 금리 IR3TIB01{NL,ES}M156N)
  수익      ETF 수정종가(분배 재투자 · USD) × FX 비(현지/USD) − 1 = 현지 통화 TR
            X_t = 현지 통화 / USD (직접 호가 DEXxxUS 는 그대로 · DEXUSxx 는 USD/현지라 역수) · TR_loc = (P_t·X_t)/(P_{t−1}·X_{t−1}) − 1
  초과      현지 3개월 금리 OECD MEI (FRED IR3TIB01{cc}M156N · 대안 OECD SDMX) · 보유월 u 의 rf = u−1 월평균 / 12 (%/년 → /1200)
  일정      결정 d_m = 달 마지막 NYSE 거래일 종가 · 체결 T+1 = d_m 다음 거래일 종가 · 보유 = 다음 T+1 까지 (ETF 일간 · FX 일간)
  가용      ETF = d_m 종가 · FRED FX = d_m 값(정오 NY) · 없으면 직전 영업일 · OECD 월 금리 = u−1 월평균 · 늦으면 마지막 공표값 유지(선언)
  신호 입력 re_sig[t] = D0 달(d_{t−1} 종가 → d_t 종가) 현지 초과 — 결정 d_t 에 다 관측된다 (x_signals 가 BEAR(12 · 1 · 0)를 건다)
  보유 행   re_hold[u] = T+1 달(T1(d_{u−1}) 종가 → T1(d_u) 종가) 현지 초과 − rf_u — 채점 보유월 2006-09 ~ 2026-08(240)만 값이 있다
  하락월    각 시장 현지 지수 초과 < 0 (D0 달 · S&P PR 달력 달 라벨의 대응 · 라벨일 뿐 신호 입력 아님)
  USD 판    usd_* = ETF 수정종가 USD TR · 초과 = DGS3MO(u−1 월평균)/12 (data/rf_monthly.json 월복리를 연율로 되돌려 /12) — 보고 판이자 전환 판
  전환 규칙 F0 커버리지(2005-08 ~ 2026-08 · 날짜 · 개수만): 한 시장이 FX 나 금리(또는 ETF)가 비면 대체 목록 순서로 바꾼다 ·
            셋 이상 비면 패널 전체를 USD TR − DGS3MO 판으로 한 번에 바꾼다 (수익을 보고 고르지 않는다)

기계적 보충(명세가 비워 둔 문턱 — 자료를 받기 전에 여기 고정했다 · 수익과 무관):
  «빈다»의 정의   ETF: 필요한 날(모든 d_m · T+1) 가운데 값이 없는 날이 하나라도(직전 행 채움은 달력 5일 안만) ·
                  FX: 필요한 날 가운데 직전 관측이 달력 7일 안에 없는 날이 하나라도 ·
                  금리: 필요한 달(2005-08 ~ 2026-07) 가운데 앞 · 안쪽 빈 달이 하나라도(끝 빈 달은 명세 «늦으면 마지막 공표값 유지» 그대로 —
                        길이 상한 없음 · 끝 빈 달 수는 F0 에 센다 · 검토 반영 2026-09-27: 국외 단계가 더했던 «최대 3개월» 문턱은 명세에 없어 뺐다)
                  금리 원천은 FRED 먼저 · FRED 가 비면 OECD SDMX 같은 계열(명세 «대안») · 둘 다 비면 그 시장이 빈다
  대체가 모자람   빈 주 시장이 1~2 개인데 덮인 대체가 그보다 적으면 10개 패널을 만들 수 없으므로 USD 판으로 바꾼다(전환 규칙의 완결)
  USD 판에서 ETF  USD 판은 주 시장 10개 그대로다 — 주 시장 ETF 가 비면 규칙 밖이라 멈춘다(SystemExit · 사람이 새 등록으로)

🚨 20년 규칙(사용자 2026-09-27): 채점 보유월 2006-09 ~ 2026-08 · 입력은 2005-08-01 이후만(워밍업 2005-09 ~ 2006-08 · 채점 안 함).
   받기부터 cosd/start = 2005-08-01 이고, 읽을 때 한 번 더 [2005-08-01, T1(2026-08 말)] 로 자른 뒤 단언한다(assert_window).
🚨 랩 규율: 등록 커밋 전에는 실자료로 수익 · 초과수익 · 신호 통계를 하나도 찍지 않는다. --selftest 는 합성만(망 · 캐시 읽지 않음) ·
   --smoke 는 실자료로 패널을 끝까지 만들되 값은 보지 않고 모양 · 개수 · 시간만 돌려준다(산출은 캐시에 쓰고 읽지 않고 지운다).
   --coverage 는 F0 셈(원천별 처음/끝 날짜 · 행 수 · 빈 날 · 참/거짓 · 대체/USD 판정)만. 20년 값은 캐시에만 — 저장소 경로 쓰기는 가드가 막는다.
라이선스: yfinance(개인 · 캐시만) · FRED H.10 · OECD(출처 표기) · French(출처 표기 · 재게시 없음) — 원자료는 %XBATCH_CACHE%(없으면 %TEMP%/xbatch_cache)/raw/intl 에만.

  python build/x_intl.py --selftest        합성 시험(FX 역수 방향 포함 · 망/캐시 없음)
  python build/x_intl.py --fetch           없는 원자료만 받는다(호스트마다 1초 1회 이하 · 있으면 손대지 않는다 = 판 동결)
  python build/x_intl.py --coverage        F0 셈(개수 · 날짜 · 참/거짓)과 대체/USD 판정 → 캐시 f0/intl_coverage.json · 공개 안전 요약 출력
  python build/x_intl.py --smoke           실자료 눈가린 연기(모양 · 개수 · 시간만)
  python build/x_intl.py --fetch-oecd      FRED 금리가 빈 시장만 OECD SDMX 대안을 받는다(실패도 시도 표지로 남긴다 — 그 전 판정은 «보류»)
  python build/x_intl.py --manifest        data/_xb_manifest.json 에 intl 절(원천 판 · SHA · 행 수 · 날짜 · 규칙 · 판정 — x_data --manifest 뒤에)
  python build/x_intl.py --f0-merge        data/_xb_f0.json 에 intl 절(f0_block — x_run --f0 뒤에)
  python build/x_intl.py --check           굽기 전 관문(캐시 SHA == 명세 intl 절 · 판정 같음)

쓰는 법(x_eval · x_run):
  frames, meta = x_intl.build_panel()          # 판정대로 10 시장(대체 반영) · meta["mode"] ∈ {local, usd} · 값은 메모리에만
  v = x_intl.primary_view(frames, meta)        # cc → re_sig(D0 달 초과 · BEAR 입력) · re_hold(T+1 보유 초과) · down(하락월 라벨) · tr(달 TR)
  a_i = BEAR(v[cc].re_sig)(월말 t)  →  Δ_{i,u} = −(a_{i,u−1} − ā_i)·v[cc].re_hold[u]   (BEAR · 관문 · DK t 는 x_signals · x_eval)
  D0 행(결정일 종가 체결 가정)은 re_d0[u] · USD 판 보고는 x_intl.view(frames, "usd") · CRASH/SURGE 라벨 x_intl.crash_labels(v)
  French 충실도(보고) x_intl.french_sign_agreement(x_intl.build_panel(include_all=True)[0], x_intl.load_french_intl())
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.environ.get("XBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "xbatch_cache")
RAW = os.path.join(CACHE, "raw", "intl")
SPY_CAL = os.environ.get("XB_SPY_CSV") or os.path.join(tempfile.gettempdir(), "tbatch_cache", "raw", "yf", "SPY.csv")   # 명세 data_plan.market_US (읽기만 · NYSE 거래일 달력)
RF_US_JSON = os.path.join(CACHE, "raw", "us", "lab", "rf_monthly.json")      # 명세: DGS3MO(data/rf_monthly.json) — x_data 가 SHA 로 고정한 캐시 사본을 읽는다
#   (작업 트리의 data/rf_monthly.json 은 CI 가 매주 갱신한다 — 굽기가 작업 트리 랩 자료에 기대지 않게 · 검토 반영 2026-09-27)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
UA_HOST = {"fred": "Python-urllib/3.12"}                 # FRED 는 브라우저 UA 요청을 붙잡아 둔다(랩 t_data UA_PY 관례 · 2026-09-27 확인)

# ── 20년 창(사용자 규칙 · 명세 rule_20y_compliance) ─────────────────────────
INPUT_MIN = "2005-08-01"                 # 입력 최소 날짜(워밍업 · 추정 전용)
BASE_MONTH = "2005-08"                   # d_{2005-08} = 첫 D0 달(2005-09)의 기준 종가
WARM = ("2005-09", "2006-08")            # BEAR 12개월 워밍업 · 채점 안 함
SCORE = ("2006-09", "2026-08")           # 채점 보유월(240)
N_SCORE = 240
RATE_MONTHS = ("2005-08", "2026-07")     # rf_u = rate(u−1) — u 2005-09 ~ 2026-08

# ── 기계적 보충 문턱(위 docstring · 자료 받기 전 고정) ────────────────────
PX_STALE_DAYS = 5                        # ETF 행이 빈 거래일 → 직전 행(달력 5일 안)
FX_STALE_DAYS = 7                        # FX 빈 날 → 직전 영업일 관측(달력 7일 안 · 명세 «없으면 직전 영업일»)
RATE_TAIL_MAX = None                     # 금리 끝 빈 달 → 마지막 공표값 유지 · 상한 없음(명세 «늦으면 마지막 공표값 유지» 그대로 · 검토 반영 2026-09-27 —
                                         #   국외 단계의 «최대 3개월» 은 명세 밖 문턱이라 뺐다 · GB 는 빈 시장이 아니다)
USD_SWITCH_AT = 3                        # 명세: 셋 이상 비면 USD 판

# ── 명세 시장 표(글자 그대로 옮김 — selftest 가 역수 표지와 FRED 호가 이름 규칙을 대조한다) ──
SPEC_MARKETS = (
    {"cc": "JP", "etf": "EWJ", "fx": "DEXJPUS"},
    {"cc": "GB", "etf": "EWU", "fx": "DEXUSUK(역수)"},
    {"cc": "DE", "etf": "EWG", "fx": "DEXUSEU(역수)"},
    {"cc": "FR", "etf": "EWQ", "fx": "DEXUSEU(역수)"},
    {"cc": "IT", "etf": "EWI", "fx": "DEXUSEU(역수)"},
    {"cc": "CH", "etf": "EWL", "fx": "DEXSZUS"},
    {"cc": "SE", "etf": "EWD", "fx": "DEXSDUS"},
    {"cc": "CA", "etf": "EWC", "fx": "DEXCAUS"},
    {"cc": "AU", "etf": "EWA", "fx": "DEXUSAL(역수)"},
    {"cc": "KR", "etf": "EWY", "fx": "DEXKOUS"},
)
SPEC_SUBSTITUTES = ("NL EWN", "ES EWP")  # 명세 substitutes_in_order (FX 는 유로 · DEXUSEU(역수))
LOCAL_CCY = {"JP": "JPY", "GB": "GBP", "DE": "EUR", "FR": "EUR", "IT": "EUR", "CH": "CHF", "SE": "SEK", "CA": "CAD", "AU": "AUD", "KR": "KRW",
             "NL": "EUR", "ES": "EUR"}
# 현지/USD 수준의 넓은 타당 띠(자료 방향 점검 · 수익 아님): 20년 안 어떤 날도 이 밖이면 방향이나 단위가 틀린 것이다
FX_LEVEL_BAND = {"JPY": (60.0, 200.0), "GBP": (0.40, 1.05), "EUR": (0.55, 1.20), "CHF": (0.55, 1.40), "SEK": (4.5, 13.0),
                 "CAD": (0.85, 1.60), "AUD": (0.85, 2.10), "KRW": (800.0, 1800.0)}
# French 국제 국가 포트폴리오(USD) 파일 이름(F-F_International_Countries.zip 의 *.Dat) — 충실도 대조(보고)만 · KR 은 French 국가 목록에 없다
FRENCH_COUNTRY = {"JP": "Japan", "GB": "UK", "DE": "Germany", "FR": "France", "IT": "Italy", "CH": "Swtzrlnd", "SE": "Sweden",
                  "CA": "Canada", "AU": "Austrlia", "KR": None, "NL": "Nethrlnd", "ES": "Spain"}
FRENCH_INTL_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_International_Countries.zip"


def _parse_fx(tok):
    """'DEXUSUK(역수)' → ('DEXUSUK', True)."""
    tok = tok.strip()
    inv = tok.endswith("(역수)")
    return (tok[:-len("(역수)")].strip() if inv else tok), inv


def _markets():
    out = []
    for m in SPEC_MARKETS:
        fid, inv = _parse_fx(m["fx"])
        out.append({"cc": m["cc"], "etf": m["etf"], "fx": fid, "inverse": inv, "rate": "IR3TIB01%sM156N" % m["cc"], "role": "primary"})
    for s in SPEC_SUBSTITUTES:
        cc, etf = s.split()
        out.append({"cc": cc, "etf": etf, "fx": "DEXUSEU", "inverse": True, "rate": "IR3TIB01%sM156N" % cc, "role": "substitute"})
    return out


MARKETS = _markets()
MK = {m["cc"]: m for m in MARKETS}
PRIMARY = [m["cc"] for m in MARKETS if m["role"] == "primary"]
SUBSTITUTES = [m["cc"] for m in MARKETS if m["role"] == "substitute"]
FX_IDS = sorted({m["fx"] for m in MARKETS})
RATE_IDS = [m["rate"] for m in MARKETS]
ETF_IDS = [m["etf"] for m in MARKETS]


# ══════════════════════════════════════════════════════════════════════════
#  가드 · 해시 · 쓰기
# ══════════════════════════════════════════════════════════════════════════
def _inside(p, root):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(root))
    return a == r or a.startswith(r + os.sep)


def cache_guard(cache=None, root=None):
    """캐시가 저장소 안이면 멈춘다(라이선스 원자료 · 20년 값은 저장소 밖에만)."""
    c, r = cache or CACHE, root or ROOT
    if _inside(c, r):
        raise SystemExit("🚨 캐시(%s)가 저장소 안이다 — 20년 값 · 원자료는 저장소 밖에만 둔다." % c)
    return os.path.abspath(c)


def guard_write_path(path, cache=None, root=None):
    """x_intl 이 쓰는 모든 파일은 캐시 안 · 저장소 밖이어야 한다(20년 수치 누출 가드)."""
    c, r = cache or CACHE, root or ROOT
    cache_guard(c, r)
    if _inside(path, r) or not _inside(path, c):
        raise SystemExit("🚨 x_intl 쓰기 경로가 캐시 밖이거나 저장소 안이다: %s" % path)
    return path


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_bytes(path, blob):
    guard_write_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)


def write_json_cache(path, obj):
    guard_write_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
    os.replace(tmp, path)
    return path


def no_value_series(doc, path="", max_len=4):
    """공개 요약에 값 계열이 없는지 — 숫자 다섯 개 넘는 목록 · 정수 아닌 수가 있으면 멈춘다(개수 · 날짜 · 참/거짓만 허용)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            no_value_series(v, path + "/" + str(k), max_len)
    elif isinstance(doc, list):
        nums = [x for x in doc if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) > max_len:
            raise SystemExit("🚨 공개 요약에 값 계열 같은 숫자 목록: %s" % path)
        for x in doc:
            no_value_series(x, path + "[]", max_len)
    elif isinstance(doc, float):
        raise SystemExit("🚨 공개 요약에 정수 아닌 수(값일 수 있음): %s" % path)
    return True


# ══════════════════════════════════════════════════════════════════════════
#  원천 목록 · 받기(호스트마다 1초 1회 이하 · 있으면 손대지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def fred_url(sid):
    return "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=%s" % (sid, INPUT_MIN)


def oecd_url(cc):
    """OECD SDMX(명세 «대안») — 단기 금리 IR3TIB · 월 · 연율 %. FRED 가 빈 시장에서만 부른다."""
    return ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/%s.M.IR3TIB.PA.....?startPeriod=%s&format=csvfilewithlabels"
            % ({"GB": "GBR", "JP": "JPN", "DE": "DEU", "FR": "FRA", "IT": "ITA", "CH": "CHE", "SE": "SWE", "CA": "CAN", "AU": "AUS", "KR": "KOR",
                "NL": "NLD", "ES": "ESP"}[cc], BASE_MONTH))


def oecd_fail_marker(cc):
    return os.path.join(RAW, "oecd", "IR3TIB_%s.fail.json" % cc)


def registry():
    """받을 원자료 전부(키 → 종류 · 식별자 · 캐시 경로 · URL · 라이선스). x_data 가 판 목록에 합칠 수 있다(값 없음)."""
    R = {}
    for m in MARKETS:
        R["yf/" + m["etf"]] = {"kind": "yf", "id": m["etf"], "path": os.path.join(RAW, "yf", m["etf"] + ".csv"),
                               "url": "yfinance:Ticker(%r).history(start=%r, auto_adjust=False, actions=True)" % (m["etf"], INPUT_MIN),
                               "license": "yfinance: 개인 사용 — 캐시만"}
        R["fred/" + m["rate"]] = {"kind": "fred", "id": m["rate"], "path": os.path.join(RAW, "fred", m["rate"] + ".csv"), "url": fred_url(m["rate"]),
                                  "license": "OECD MEI via FRED — 출처 표기"}
        R["oecd/" + m["cc"]] = {"kind": "oecd", "id": m["cc"], "path": os.path.join(RAW, "oecd", "IR3TIB_%s.csv" % m["cc"]), "url": oecd_url(m["cc"]),
                                "license": "OECD — 출처 표기", "on_demand": True}
    for f in FX_IDS:
        R["fred/" + f] = {"kind": "fred", "id": f, "path": os.path.join(RAW, "fred", f + ".csv"), "url": fred_url(f), "license": "FRB H.10 via FRED"}
    R["french/intl_countries"] = {"kind": "http", "id": "F-F_International_Countries", "path": os.path.join(RAW, "french", "F-F_International_Countries.zip"),
                                  "url": FRENCH_INTL_URL, "license": "Kenneth R. French Data Library — 출처 표기 · 재게시 없음"}
    return R


_LAST_HIT = {}


def _throttle(host, gap=1.1):
    t = _LAST_HIT.get(host)
    if t is not None:
        w = gap - (time.monotonic() - t)
        if w > 0:
            time.sleep(w)
    _LAST_HIT[host] = time.monotonic()


def _http_get(url, host, timeout=60, tries=3):
    last = None
    for k in range(tries):
        _throttle(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA_HOST.get(host, UA)})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 410):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(2.0 * (k + 1))
    raise last


def _yf_blob(ticker):
    import yfinance as yf
    _throttle("yahoo")
    df = yf.Ticker(ticker).history(start=INPUT_MIN, auto_adjust=False, actions=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance %s: 빈 응답" % ticker)
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "Date"
    cols = [c for c in ("Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits", "Capital Gains") if c in df.columns]
    txt = df[cols].to_csv(date_format="%Y-%m-%d", float_format="%.10g", lineterminator="\n")
    return txt.encode("utf-8"), getattr(yf, "__version__", "?")


def manifest_entries():
    """data/_xb_manifest.json 용 공개 안전 원천 목록(키 · URL · 받은 때 · SHA-256 · 바이트 · 라이선스 — 값 없음). x_data 가 합친다."""
    out = {}
    for key, ds in registry().items():
        mp = ds["path"] + ".meta.json"
        if not os.path.exists(mp):
            continue
        with open(mp, "r", encoding="utf-8") as f:
            m = json.load(f)
        ok = os.path.exists(ds["path"]) and sha256_file(ds["path"]) == m.get("sha256")
        out[key] = {"url": m.get("url"), "fetched_at": m.get("fetched_at"), "sha256": m.get("sha256"), "bytes": m.get("bytes"),
                    "license": m.get("license"), "sha_ok": bool(ok), **({"yfinance": m["yfinance"]} if "yfinance" in m else {})}
    no_value_series(out)
    return out


def fetch_one(key, force=False):
    ds = registry()[key]
    p = ds["path"]
    if os.path.exists(p) and not force:
        return p, False
    extra = {}
    if ds["kind"] == "yf":
        blob, ver = _yf_blob(ds["id"])
        extra["yfinance"] = ver
    elif ds["kind"] == "fred":
        blob, _ = _http_get(ds["url"], "fred")
        if not blob[:200].lower().lstrip().startswith((b"observation_date", b"date")):
            raise RuntimeError("FRED %s: CSV 머리가 아니다" % ds["id"])
    elif ds["kind"] == "oecd":
        blob, _ = _http_get(ds["url"], "oecd")
    else:
        blob, _ = _http_get(ds["url"], "french")
    _write_bytes(p, blob)
    write_json_cache(p + ".meta.json", {"key": key, "url": ds["url"], "fetched_at": _now(), "sha256": sha256_bytes(blob), "bytes": len(blob),
                                        "license": ds["license"], **extra})
    return p, True


def fetch_all(force=False, include_oecd=False):
    cache_guard()
    got, kept, fail = [], [], {}
    for key, ds in registry().items():
        if ds.get("on_demand") and not include_oecd:
            continue
        try:
            _, new = fetch_one(key, force=force)
            (got if new else kept).append(key)
        except Exception as e:
            fail[key] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return {"fetched": got, "kept": kept, "failed": fail}


# ══════════════════════════════════════════════════════════════════════════
#  읽기(자르고 단언)
# ══════════════════════════════════════════════════════════════════════════
def parse_yf_text(txt):
    df = pd.read_csv(io.StringIO(txt), parse_dates=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def parse_fred_text(txt):
    """FRED 그래프 CSV → Series(일 DatetimeIndex · 월이면 PeriodIndex) · «.»/빈칸은 NaN."""
    lines = [ln for ln in txt.replace("\r\n", "\n").split("\n") if ln.strip()]
    hdr = lines[0].split(",")
    dates, vals = [], []
    for ln in lines[1:]:
        a = ln.split(",")
        dates.append(a[0].strip())
        v = a[1].strip() if len(a) > 1 else ""
        vals.append(float(v) if v not in ("", ".") else np.nan)
    idx = pd.to_datetime(dates, format="%Y-%m-%d")
    monthly = len(idx) > 1 and bool((idx.day == 1).all()) and 27 <= float(np.median(np.diff(idx.values).astype("timedelta64[D]").astype(float))) <= 32
    s = pd.Series(vals, index=pd.PeriodIndex(idx, freq="M") if monthly else pd.DatetimeIndex(idx), name=hdr[1].strip() if len(hdr) > 1 else "v")
    return s[~s.index.duplicated(keep="first")].sort_index()


def parse_oecd_text(txt):
    """OECD SDMX csvfilewithlabels → 월 Series(TIME_PERIOD · OBS_VALUE)."""
    df = pd.read_csv(io.StringIO(txt))
    cols = {}
    for c in df.columns:                                                  # 부호 열(대문자)이 이름표 열(«Measure» 등)보다 앞선다
        if c.upper() not in cols or c == c.upper():
            cols[c.upper()] = c
    tp, ov = cols.get("TIME_PERIOD"), cols.get("OBS_VALUE")
    if tp is None or ov is None:
        raise ValueError("OECD CSV 열(TIME_PERIOD · OBS_VALUE) 없음")
    for col, want in (("MEASURE", "IR3TIB"), ("FREQ", "M"), ("UNIT_MEASURE", "PA")):
        if col in cols:
            df = df[df[cols[col]].astype(str) == want]
    if "METHODOLOGY" in cols and df[cols["METHODOLOGY"]].nunique() > 1:
        raise ValueError("OECD CSV 에 계산 방법이 여럿 — 한 계열로 정해지지 않는다")
    s = pd.Series(pd.to_numeric(df[ov], errors="coerce").to_numpy(), index=pd.PeriodIndex(df[tp].astype(str), freq="M"))
    return s[~s.index.duplicated(keep="first")].sort_index()


def _read_text(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_sessions(path=None):
    """NYSE 거래일 달력 = SPY 일간 행의 날짜(명세 data_plan.market_US · 읽기만) — [INPUT_MIN, …] 로 자른다."""
    p = path or SPY_CAL
    parts = [x.lower() for x in os.path.normpath(os.path.abspath(p)).replace("\\", "/").split("/")]
    if "_tbatch" in os.path.basename(p).lower() or ("tbatch_cache" in parts and "out" in parts):
        raise SystemExit("🚨 tbatch_cache/out(T01 C:bearonly 등 굽기 산출)은 읽지 않는다: %s" % p)
    df = parse_yf_text(_read_text(p))
    d = pd.DatetimeIndex(df.index[df["Close"].notna()]).normalize()
    return d[d >= pd.Timestamp(INPUT_MIN)]


def schedule(sessions, first=BASE_MONTH, last=SCORE[1]):
    """달마다 d_m(마지막 거래일)과 T1(d_m 다음 거래일). 반환 DataFrame(index = 달 · 열 d, t1)."""
    s = pd.DatetimeIndex(sessions).sort_values().unique()
    per = s.to_period("M")
    months = pd.period_range(first, last, freq="M")
    d, t1 = [], []
    for m in months:
        mm = s[per == m]
        if len(mm) == 0:
            raise SystemExit("🚨 달력에 %s 거래일이 없다" % m)
        dm = mm[-1]
        k = s.searchsorted(dm, side="right")
        if k >= len(s):
            raise SystemExit("🚨 달력이 %s 의 T+1(다음 거래일)까지 닿지 않는다" % m)
        d.append(dm)
        t1.append(s[k])
    return pd.DataFrame({"d": d, "t1": t1}, index=months)


def clip_daily(s, end):
    s = s[(s.index >= pd.Timestamp(INPUT_MIN)) & (s.index <= pd.Timestamp(end))]
    if len(s) and s.index.min() < pd.Timestamp(INPUT_MIN):
        raise SystemExit("🚨 입력 최소 날짜 < %s" % INPUT_MIN)
    return s


def clip_monthly(s, first=RATE_MONTHS[0], last=RATE_MONTHS[1]):
    s = s[(s.index >= pd.Period(first, "M")) & (s.index <= pd.Period(last, "M"))]
    if len(s) and s.index.min() < pd.Period(BASE_MONTH, "M"):
        raise SystemExit("🚨 입력 최소 달 < %s" % BASE_MONTH)
    return s


def value_asof(series, dates, max_stale_days):
    """날짜마다 그날 또는 직전 관측(달력 max_stale_days 안) — (값 배열, 정확히 그날 관측인가, 채움인가, 없음인가, 가장 긴 늦음 일)."""
    s = series.dropna()
    idx = s.index.values.astype("datetime64[D]")
    q = pd.DatetimeIndex(dates).values.astype("datetime64[D]")
    k = np.searchsorted(idx, q, side="right") - 1
    vals = np.full(len(q), np.nan)
    exact = np.zeros(len(q), bool)
    stale = np.zeros(len(q), np.int64)
    ok = k >= 0
    lag = np.where(ok, (q - idx[np.clip(k, 0, None)]).astype(np.int64), 10 ** 6)
    use = ok & (lag <= max_stale_days)
    vals[use] = s.to_numpy(float)[k[use]]
    exact[use] = lag[use] == 0
    stale[use] = lag[use]
    filled = use & ~exact
    missing = ~use
    return vals, exact, filled, missing, int(stale.max()) if len(stale) else 0


def local_per_usd(raw, inverse):
    """FRED 호가 → 현지 통화 / USD. inverse(DEXUSxx = USD/현지)면 역수."""
    raw = pd.Series(raw, dtype=float)
    return 1.0 / raw if inverse else raw


def rate_series(cc, source=None):
    """현지 3개월 금리(월 · %/년) · (계열, 원천). source None 이면 FRED 먼저."""
    m = MK[cc]
    R = registry()
    if source in (None, "fred"):
        p = R["fred/" + m["rate"]]["path"]
        if os.path.exists(p):
            s = parse_fred_text(_read_text(p))
            if isinstance(s.index, pd.PeriodIndex):
                return clip_monthly(s), "fred"
        if source == "fred":
            return None, "fred"
    p = R["oecd/" + cc]["path"]
    if os.path.exists(p):
        return clip_monthly(parse_oecd_text(_read_text(p))), "oecd"
    return None, "oecd"


def rate_fill(s, first=RATE_MONTHS[0], last=RATE_MONTHS[1], tail_max=RATE_TAIL_MAX):
    """필요한 달로 다시 색인 · 끝 빈 달은 마지막 공표값 유지(tail_max 가 None 이면 끝까지 · 수를 주면 그 수까지) · 안쪽 빈 달은 NaN 그대로.
    반환 (계열, 셈{present, interior_missing, tail_missing, tail_carried, head_missing})."""
    months = pd.period_range(first, last, freq="M")
    x = (s.dropna() if s is not None else pd.Series(dtype=float)).reindex(months)
    have = x.notna().to_numpy()
    n = len(months)
    if not have.any():
        return x, {"present": 0, "head_missing": n, "interior_missing": 0, "tail_missing": 0, "tail_carried": 0, "last_obs": None}
    i0, i1 = int(np.argmax(have)), int(n - 1 - np.argmax(have[::-1]))
    tail = n - 1 - i1
    interior = int((~have[i0:i1 + 1]).sum())
    carried = tail if tail_max is None else min(tail, tail_max)
    y = x.copy()
    if carried:
        y.iloc[i1 + 1:i1 + 1 + carried] = x.iloc[i1]
    return y, {"present": int(have.sum()), "head_missing": i0, "interior_missing": interior, "tail_missing": tail, "tail_carried": carried,
               "last_obs": str(months[i1])}


def rf_us_monthly(path=None):
    """USD 판 rf_u = DGS3MO(u−1 월평균)/12 — data/rf_monthly.json 은 (1 + y)^(1/12) − 1 이라 y 로 되돌려 /12 (명세 식 그대로)."""
    with open(path or RF_US_JSON, "r", encoding="utf-8") as f:
        R = json.load(f)["monthly"]
    ks = sorted(R)
    m = pd.Series([float(R[k]) for k in ks], index=pd.PeriodIndex(ks, freq="M"))
    y = (1.0 + m) ** 12 - 1.0
    y = clip_monthly(y)
    rf = y / 12.0
    rf.index = rf.index + 1                                  # 관측 달 u−1 → 보유월 u
    return rf


# ══════════════════════════════════════════════════════════════════════════
#  커버리지(F0 · 개수 · 날짜 · 참/거짓만)
# ══════════════════════════════════════════════════════════════════════════
def _need_dates(sched):
    """필요한 날: D0 기준 d_{2005-08} ~ d_{2026-08} 와 T+1 T1(d_{2006-08}) ~ T1(d_{2026-08})."""
    hold_prev = pd.period_range(pd.Period(SCORE[0], "M") - 1, SCORE[1], freq="M")
    d = pd.DatetimeIndex(sched["d"])
    t1 = pd.DatetimeIndex(sched.loc[hold_prev, "t1"])
    return pd.DatetimeIndex(sorted(set(d) | set(t1)))


def _span(s):
    s = s.dropna()
    return (str(s.index.min())[:10], str(s.index.max())[:10]) if len(s) else (None, None)


def coverage_market(cc, sched, sessions, end, loaders=None):
    """한 시장의 ETF · FX · 금리 커버리지(개수 · 날짜 · 참/거짓). loaders 는 합성 시험용 주입({etf, fx, rate})."""
    m = MK[cc]
    need = _need_dates(sched)
    win = sessions[(sessions >= pd.Timestamp(INPUT_MIN)) & (sessions <= pd.Timestamp(end))]
    out = {"cc": cc, "role": m["role"], "etf": m["etf"], "fx": m["fx"], "fx_inverse": m["inverse"], "rate": m["rate"]}
    L = loaders or {}
    # ETF
    try:
        px = L["etf"](cc) if "etf" in L else load_etf(cc)
    except FileNotFoundError:
        px = None
    if px is None or len(px.dropna()) == 0:
        out["etf_cov"] = {"ok": False, "why": "없음"}
    else:
        px = clip_daily(px, end)
        v, ex, fi, mi, st = value_asof(px, need, PX_STALE_DAYS)
        miss_sess = int((~pd.DatetimeIndex(win).isin(px.dropna().index)).sum())
        f0, f1 = _span(px)
        out["etf_cov"] = {"first": f0, "last": f1, "n_rows": int(px.notna().sum()), "n_sessions": int(len(win)), "n_sessions_missing": miss_sess,
                          "n_need": int(len(need)), "n_need_exact": int(ex.sum()), "n_need_filled": int(fi.sum()), "n_need_missing": int(mi.sum()),
                          "max_fill_days": st, "ok": bool(mi.sum() == 0)}
        if "etf_capgain_rows" in L:
            out["etf_cov"]["n_capgain_rows"] = int(L["etf_capgain_rows"](cc))
        else:
            out["etf_cov"]["n_capgain_rows"] = _capgain_rows(cc, end)
    # FX
    try:
        fxr = L["fx"](m["fx"]) if "fx" in L else load_fx_raw(m["fx"])
    except FileNotFoundError:
        fxr = None
    if fxr is None or len(fxr.dropna()) == 0:
        out["fx_cov"] = {"ok": False, "why": "없음"}
    else:
        n_blank = int(clip_daily(fxr, end).isna().sum())
        fxr = clip_daily(fxr, end)
        v, ex, fi, mi, st = value_asof(fxr, need, FX_STALE_DAYS)
        lvl = local_per_usd(fxr.dropna(), m["inverse"])
        lo, hi = FX_LEVEL_BAND[LOCAL_CCY[cc]]
        f0, f1 = _span(fxr)
        out["fx_cov"] = {"first": f0, "last": f1, "n_obs": int(fxr.notna().sum()), "n_blank": n_blank, "n_need": int(len(need)),
                         "n_need_exact": int(ex.sum()), "n_need_filled": int(fi.sum()), "n_need_missing": int(mi.sum()), "max_fill_days": st,
                         "level_band_ok": bool(len(lvl) and lvl.min() >= lo and lvl.max() <= hi), "ok": bool(mi.sum() == 0)}
        out["fx_cov"]["ok"] = out["fx_cov"]["ok"] and out["fx_cov"]["level_band_ok"]
    # 금리 — FRED 먼저 · FRED 가 비면 OECD
    rc = {}
    chosen = None
    for src in ("fred", "oecd"):
        try:
            s, _ = (L["rate"](cc, src), src) if "rate" in L else rate_series(cc, src)
        except FileNotFoundError:
            s = None
        _, c = rate_fill(s)
        c["ok"] = bool(s is not None and c["head_missing"] == 0 and c["interior_missing"] == 0
                       and (RATE_TAIL_MAX is None or c["tail_missing"] <= RATE_TAIL_MAX))
        c["available"] = s is not None
        if src == "oecd":
            c["attempted"] = True if "rate" in L else bool(s is not None or os.path.exists(oecd_fail_marker(cc)))
        rc[src] = c
        if c["ok"]:
            chosen = src
            break
    pending = chosen is None and not rc.get("oecd", {}).get("attempted", True)      # FRED 가 비었는데 OECD 대안을 아직 받아 보지 않았다
    out["rate_cov"] = {"by_source": rc, "source": chosen, "n_need": len(pd.period_range(*RATE_MONTHS, freq="M")), "ok": chosen is not None,
                       "pending_oecd": bool(pending)}
    out["ok"] = bool(out["etf_cov"]["ok"] and out["fx_cov"]["ok"] and out["rate_cov"]["ok"])
    return out


def decide(cov):
    """명세 전환 규칙(기계적): 빈 주 시장 0 → 그대로 · 1~2 → 대체 목록 순서(덮인 것만) · 셋 이상(또는 대체가 모자람) → USD 판 전체."""
    pend = [cc for cc in cov if cov[cc]["rate_cov"].get("pending_oecd")]
    if pend:
        return {"mode": "pending", "markets": [], "empty": [], "substituted": {}, "pending_oecd": pend,
                "why": "FRED 금리가 빈 시장 %s — OECD 대안을 먼저 받는다(--fetch-oecd) · 판정 보류" % ",".join(pend)}
    ok = {cc: bool(cov[cc]["ok"]) for cc in cov}
    empty = [cc for cc in PRIMARY if not ok.get(cc, False)]
    subs_ok = [cc for cc in SUBSTITUTES if ok.get(cc, False)]
    if len(empty) == 0:
        return {"mode": "local", "markets": list(PRIMARY), "empty": [], "substituted": {}, "why": "빈 시장 없음"}
    if len(empty) < USD_SWITCH_AT and len(subs_ok) >= len(empty):
        rep = dict(zip(empty, subs_ok[:len(empty)]))
        mk = [rep.get(cc, cc) for cc in PRIMARY]
        return {"mode": "local", "markets": mk, "empty": empty, "substituted": rep, "why": "빈 시장 %d → 대체 순서 %s" % (len(empty), "·".join(SUBSTITUTES))}
    etf_bad = [cc for cc in PRIMARY if not cov[cc]["etf_cov"]["ok"]]
    if etf_bad:
        raise SystemExit("🚨 USD 판 전환인데 주 시장 ETF 가 빈다(%s) — 규칙 밖 · 멈춘다(새 등록)" % ",".join(etf_bad))
    why = ("빈 시장 %d ≥ %d" % (len(empty), USD_SWITCH_AT)) if len(empty) >= USD_SWITCH_AT else ("빈 시장 %d 인데 덮인 대체 %d — 대체가 모자람" % (len(empty), len(subs_ok)))
    return {"mode": "usd", "markets": list(PRIMARY), "empty": empty, "substituted": {}, "why": why + " → 패널 전체 USD TR − DGS3MO"}


def coverage(sessions=None, loaders=None, rf_us=None):
    """12 시장(주 10 · 대체 2) 커버리지 + US rf 커버리지 + 판정. 값 없음(개수 · 날짜 · 참/거짓)."""
    ses = load_sessions() if sessions is None else pd.DatetimeIndex(sessions)
    sched = schedule(ses)
    end = sched["t1"].iloc[-1]
    cov = {m["cc"]: coverage_market(m["cc"], sched, ses, end, loaders) for m in MARKETS}
    dec = decide(cov)
    rfu = rf_us_monthly() if rf_us is None else rf_us
    hold = pd.period_range(pd.Period(WARM[0], "M"), SCORE[1], freq="M")
    rfu_cov = {"n_need": int(len(hold)), "n_present": int(rfu.reindex(hold).notna().sum())}
    rfu_cov["ok"] = rfu_cov["n_present"] == rfu_cov["n_need"]
    return {"window": {"input_min": INPUT_MIN, "warm": list(WARM), "score": list(SCORE), "rate_months": list(RATE_MONTHS),
                       "d_first": str(sched["d"].iloc[0].date()), "t1_last": str(end.date()), "n_months_sched": int(len(sched))},
            "rules": {"px_stale_days": PX_STALE_DAYS, "fx_stale_days": FX_STALE_DAYS, "rate_tail_max": RATE_TAIL_MAX, "usd_switch_at": USD_SWITCH_AT},
            "markets": cov, "rf_us": rfu_cov, "decision": dec}


def f0_block(cov):
    """data/_xb_f0.json 에 넣을 공개 안전 I 층 블록(개수 · 날짜 · 참/거짓 · 라벨 — 값 없음). x_run/x_data 가 합친다."""
    mk = {}
    for cc, c in cov["markets"].items():
        e, f, r = c["etf_cov"], c["fx_cov"], c["rate_cov"]
        mk[cc] = {"role": c["role"], "etf": c["etf"], "fx": c["fx"], "fx_inverse": c["fx_inverse"], "rate": c["rate"], "ok": c["ok"],
                  "etf_first": e.get("first"), "etf_last": e.get("last"), "etf_n_sessions_missing": e.get("n_sessions_missing"),
                  "etf_n_need_filled": e.get("n_need_filled"), "etf_n_need_missing": e.get("n_need_missing"), "etf_ok": e["ok"],
                  "fx_first": f.get("first"), "fx_last": f.get("last"), "fx_n_blank": f.get("n_blank"), "fx_n_need_filled": f.get("n_need_filled"),
                  "fx_n_need_missing": f.get("n_need_missing"), "fx_level_band_ok": f.get("level_band_ok"), "fx_ok": f["ok"],
                  "rate_source": r["source"], "rate_ok": r["ok"],
                  "rate_by_source": {s: {k: v for k, v in rc.items() if k in ("present", "head_missing", "interior_missing", "tail_missing", "tail_carried",
                                                                                  "last_obs", "ok", "available", "attempted")} for s, rc in r["by_source"].items()}}
    d = cov["decision"]
    out = {"layer": "I", "window": cov["window"], "rules": cov["rules"], "markets": mk, "rf_us_ok": cov["rf_us"]["ok"],
           "decision": {"mode": d["mode"], "markets": d["markets"], "empty": d["empty"], "substituted": d["substituted"], "why": d["why"],
                        "pending_oecd": d.get("pending_oecd", [])},
           "note": "개수 · 날짜 · 참/거짓만 — 수익 · 켜짐 비율 없음 (명세 data_plan.F0_counts_only «I 층 커버리지와 대체/USD 전환 판정»)"}
    no_value_series(out)
    return out


def _source_summary(key):
    """원천 하나의 모양(행 수 · 처음/끝 · 빈 칸) — 값 없음."""
    ds = registry()[key]
    p = ds["path"]
    if ds["kind"] == "yf":
        s = parse_yf_text(_read_text(p))["Adj Close"]
    elif ds["kind"] == "fred":
        s = parse_fred_text(_read_text(p))
    elif ds["kind"] == "oecd":
        s = parse_oecd_text(_read_text(p))
    else:
        with zipfile.ZipFile(p) as z:
            return {"members": len(z.namelist())}
    return {"rows": int(len(s)), "first": str(s.index.min())[:10], "last": str(s.index.max())[:10], "n_nan": int(s.isna().sum())}


def manifest_section(cov=None):
    """data/_xb_manifest.json 의 «intl» 절(x_data 명세 머리 «국외 원천은 x_intl 명세 절이 더한다») — 원천 판 · 규칙 · 판정. 값 계열 없음."""
    cov = cov or coverage()
    src = manifest_entries()
    for key in src:
        try:
            src[key]["summary"] = _source_summary(key)
        except Exception as e:                                           # noqa: BLE001
            src[key]["summary"] = {"error": type(e).__name__}
    cal = {"file": "tbatch_cache/raw/yf/SPY.csv (읽기만 · NYSE 거래일 달력)", "sha256": sha256_file(SPY_CAL) if os.path.exists(SPY_CAL) else None}
    with open(RF_US_JSON, "rb") as f:
        rf_sha = sha256_bytes(f.read().replace(b"\r\n", b"\n"))
    d = cov["decision"]
    doc = {"note": ("I 층 국외 패널 원천(build/x_intl.py --manifest) — 국가 ETF(yfinance · 캐시만) · FRB H.10 FX · OECD MEI 3개월 금리(FRED · 대안 OECD SDMX) · "
                    "French 국제 국가(충실도 보고만). 판 · 해시 · 행 수 · 날짜 · 규칙만 — 수익 · 값 계열 없음."),
           "generated_at": _now(), "cache_root": "%TEMP%/xbatch_cache/raw/intl",
           "spec_markets": [dict(m) for m in SPEC_MARKETS], "substitutes_in_order": list(SPEC_SUBSTITUTES),
           "rules": {"returns": "현지 TR = (P_t·X_t)/(P_{t−1}·X_{t−1}) − 1 · X = 현지/USD(DEXUS* 는 역수) · P = ETF 수정종가(USD)",
                     "excess": "rf_u = IR3TIB01{cc}M156N(u−1 월평균)/1200 · USD 판 rf_u = DGS3MO(u−1 월평균)/12",
                     "timing": "결정 d_m 종가 · T+1 체결(다음 NYSE 거래일 종가) · 보유 다음 T+1 까지 · FX 는 그날 또는 직전 영업일(달력 %d일 안)" % FX_STALE_DAYS,
                     "px_stale_days": PX_STALE_DAYS, "fx_stale_days": FX_STALE_DAYS, "rate_tail_max_months": RATE_TAIL_MAX, "usd_switch_at": USD_SWITCH_AT,
                     "empty_rule": "ETF · FX · 금리 가운데 하나라도 필요한 날/달을 못 덮으면 그 시장이 빈다 · 금리는 FRED 먼저 · FRED 가 비면 OECD SDMX",
                     "switch_rule": "빈 주 시장 1~2 → 대체 NL → ES 순서(덮인 것만) · 셋 이상 또는 대체 모자람 → 패널 전체 USD TR − DGS3MO"},
           "window": {"input_min": INPUT_MIN, "warm": list(WARM), "score": list(SCORE), "rate_months": list(RATE_MONTHS)},
           "calendar": cal, "rf_us": {"file": "%TEMP%/xbatch_cache/raw/us/lab/rf_monthly.json(x_data lab/rf_monthly 고정 사본 · 원본 data/rf_monthly.json)",
                                     "sha256_lf": rf_sha},
           "sources": src,
           "decision": {"mode": d["mode"], "markets": d["markets"], "empty": d["empty"], "substituted": d["substituted"], "why": d["why"]}}
    no_value_series(doc)
    return doc


def _x_data():
    """저장소 쓰기는 x_data 의 허용 목록 · 공개 안전 점검(repo_write_json)으로만 한다."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import x_data as XD                                                  # noqa: E402
    return XD


def write_manifest_section(cov=None):
    """data/_xb_manifest.json 에 «intl» 절을 넣는다(다른 절은 그대로). x_data --manifest 가 명세를 다시 쓰면 이 명령을 다시 부른다."""
    XD = _x_data()
    rel = "data/_xb_manifest.json"
    p = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(p):
        raise SystemExit("🚨 %s 가 없다 — x_data --manifest 먼저" % rel)
    with open(p, "r", encoding="utf-8") as f:
        M = json.load(f)
    M["intl"] = manifest_section(cov)
    bad = XD.public_safe(M)
    if bad:
        raise SystemExit("🚨 명세 intl 절이 공개 안전 점검에 걸렸다: %s" % bad[:3])
    return XD.repo_write_json(rel, M)


def merge_f0_block(cov=None):
    """data/_xb_f0.json 에 «intl» 절(f0_block)을 넣는다 — 파일은 x_run --f0 가 만든다(없으면 멈춘다)."""
    XD = _x_data()
    rel = "data/_xb_f0.json"
    p = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(p):
        raise SystemExit("🚨 %s 가 없다 — x_run --f0 먼저" % rel)
    with open(p, "r", encoding="utf-8") as f:
        F = json.load(f)
    F["intl"] = f0_block(cov or coverage())
    return XD.repo_write_json(rel, F)


def check_pins():
    """굽기 전 관문 — 캐시 원자료 SHA == 명세 intl 절 · 달력 SHA · 판정이 명세와 같다."""
    p = os.path.join(ROOT, "data", "_xb_manifest.json")
    if not os.path.exists(p):
        return {"ok": False, "bad": ["명세 없음"]}
    with open(p, "r", encoding="utf-8") as f:
        M = json.load(f).get("intl")
    if not M:
        return {"ok": False, "bad": ["명세에 intl 절 없음 — x_intl --manifest"]}
    bad = []
    R = registry()
    for key, ent in M.get("sources", {}).items():
        path = R[key]["path"]
        if not os.path.exists(path):
            bad.append("%s: 고정본 없음" % key)
        elif sha256_file(path) != ent.get("sha256"):
            bad.append("%s: SHA 가 명세와 다르다" % key)
    need = ["yf/" + MK[c]["etf"] for c in M["decision"]["markets"]] + ["fred/" + MK[c]["fx"] for c in M["decision"]["markets"]]
    bad += ["%s: 명세에 없음" % k for k in need if k not in M.get("sources", {})]
    if os.path.exists(SPY_CAL) and M.get("calendar", {}).get("sha256") != sha256_file(SPY_CAL):
        bad.append("달력(SPY.csv) SHA 가 명세와 다르다")
    if not os.path.exists(RF_US_JSON):
        bad.append("USD rf 고정 사본(x_data lab/rf_monthly)이 캐시에 없다")
    else:
        with open(RF_US_JSON, "rb") as f:
            if sha256_bytes(f.read().replace(b"\r\n", b"\n")) != (M.get("rf_us") or {}).get("sha256_lf"):
                bad.append("USD rf 고정 사본 SHA 가 명세와 다르다")
    d = coverage()["decision"]
    if [d["mode"], d["markets"]] != [M["decision"]["mode"], M["decision"]["markets"]]:
        bad.append("판정이 명세와 다르다")
    return {"ok": not bad, "bad": bad, "n_sources": len(M.get("sources", {}))}


# ══════════════════════════════════════════════════════════════════════════
#  원자료 읽기(캐시)
# ══════════════════════════════════════════════════════════════════════════
def load_etf(cc):
    p = registry()["yf/" + MK[cc]["etf"]]["path"]
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    df = parse_yf_text(_read_text(p))
    return df["Adj Close"].astype(float)


def _capgain_rows(cc, end):
    p = registry()["yf/" + MK[cc]["etf"]]["path"]
    if not os.path.exists(p):
        return 0
    df = parse_yf_text(_read_text(p))
    if "Capital Gains" not in df.columns:
        return 0
    df = df[(df.index >= pd.Timestamp(INPUT_MIN)) & (df.index <= pd.Timestamp(end))]
    return int((df["Capital Gains"].fillna(0) != 0).sum())


def load_fx_raw(fid):
    p = registry()["fred/" + fid]["path"]
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    s = parse_fred_text(_read_text(p))
    if isinstance(s.index, pd.PeriodIndex):
        raise SystemExit("🚨 %s 가 일간이 아니다" % fid)
    return s


# ══════════════════════════════════════════════════════════════════════════
#  패널(값 — 캐시 · 메모리에만 · 저장소에 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
COLS = ("tr_d0", "rf", "re_d0", "tr_t1", "re_t1", "usd_d0", "rf_us", "re_usd_d0", "usd_t1", "re_usd_t1")


def market_frame(px_usd, fx_raw, inverse, rate_m, rf_us, sched):
    """한 시장의 달 행. index = 2005-09 ~ 2026-08(252). T+1 열은 채점 보유월(2006-09 ~ 2026-08)만 값."""
    months = pd.period_range(WARM[0], SCORE[1], freq="M")
    base = pd.period_range(BASE_MONTH, SCORE[1], freq="M")
    d = pd.DatetimeIndex(sched.loc[base, "d"])
    t1 = pd.DatetimeIndex(sched.loc[base, "t1"])
    P_d = value_asof(px_usd, d, PX_STALE_DAYS)[0]
    P_t = value_asof(px_usd, t1, PX_STALE_DAYS)[0]
    X_d = local_per_usd(value_asof(fx_raw, d, FX_STALE_DAYS)[0], inverse).to_numpy()
    X_t = local_per_usd(value_asof(fx_raw, t1, FX_STALE_DAYS)[0], inverse).to_numpy()
    Ld, Lt = P_d * X_d, P_t * X_t
    f = pd.DataFrame(index=months, columns=list(COLS), dtype=float)
    f["tr_d0"] = Ld[1:] / Ld[:-1] - 1.0                                  # 달 t: d_{t−1} → d_t (현지)
    f["usd_d0"] = P_d[1:] / P_d[:-1] - 1.0
    rm, _ = rate_fill(rate_m)
    rf_loc = rm / 1200.0
    rf_loc.index = rf_loc.index + 1                                      # 관측 달 u−1 → 보유월 u
    f["rf"] = rf_loc.reindex(months).to_numpy()
    f["rf_us"] = pd.Series(rf_us).reindex(months).to_numpy()
    f["re_d0"] = f["tr_d0"] - f["rf"]
    f["re_usd_d0"] = f["usd_d0"] - f["rf_us"]
    hold = pd.period_range(SCORE[0], SCORE[1], freq="M")
    pos = base.get_indexer(hold)
    f.loc[hold, "tr_t1"] = Lt[pos] / Lt[pos - 1] - 1.0                   # 보유월 u: T1(d_{u−1}) → T1(d_u)
    f.loc[hold, "usd_t1"] = P_t[pos] / P_t[pos - 1] - 1.0
    f["re_t1"] = f["tr_t1"] - f["rf"]
    f["re_usd_t1"] = f["usd_t1"] - f["rf_us"]
    return f


def view(frames, mode):
    """주 열 이름으로 — re_sig(신호 입력 · D0 달) · re_hold(T+1 보유 행) · down(하락월 라벨: 그 달 현지(또는 USD) 지수 초과 < 0) · tr(CRASH/SURGE 라벨용 달 TR)."""
    if mode not in ("local", "usd"):
        raise ValueError("mode 는 local · usd")
    a, b, c = ("re_d0", "re_t1", "tr_d0") if mode == "local" else ("re_usd_d0", "re_usd_t1", "usd_d0")
    out = {}
    for cc, f in frames.items():
        g = pd.DataFrame({"re_sig": f[a], "re_hold": f[b], "tr": f[c]}, index=f.index)
        g["down"] = (g["re_sig"] < 0).where(g["re_sig"].notna())
        out[cc] = g
    return out


def assert_window(frames, input_min_seen=None):
    """20년 규칙 단언: 채점 보유월 = 2006-09 ~ 2026-08(240) · 신호 행 첫 달 2005-09 · 입력 최소 날짜 ≥ 2005-08-01."""
    for cc, f in frames.items():
        h = f["re_t1"].dropna() if "re_t1" in f else f["re_hold"].dropna()
        if len(h) and (str(h.index.min()) < SCORE[0] or str(h.index.max()) > SCORE[1]):
            raise SystemExit("🚨 %s 보유 행이 채점 창 밖: %s ~ %s" % (cc, h.index.min(), h.index.max()))
        if str(f.index.min()) < WARM[0]:
            raise SystemExit("🚨 %s 신호 행이 워밍업 앞: %s" % (cc, f.index.min()))
    if input_min_seen is not None and pd.Timestamp(input_min_seen) < pd.Timestamp(INPUT_MIN):
        raise SystemExit("🚨 입력 최소 날짜 %s < %s" % (input_min_seen, INPUT_MIN))
    return True


def build_panel(cov=None, sessions=None, rf_us=None, include_all=False):
    """판정대로 패널을 만든다 → (frames{cc: DataFrame(COLS)}, meta). include_all 이면 덮인 12 시장 모두(USD 판 보고 · 충실도용).
    값은 메모리에만 — 저장이 필요하면 write_json_cache(캐시 안)만 쓴다."""
    cache_guard()
    ses = load_sessions() if sessions is None else pd.DatetimeIndex(sessions)
    sched = schedule(ses)
    end = sched["t1"].iloc[-1]
    cov = cov or coverage(sessions=ses, rf_us=rf_us)
    dec = cov["decision"]
    if dec["mode"] == "pending":
        raise SystemExit("🚨 I 층 판정 보류 — %s" % dec["why"])
    rfu = rf_us_monthly() if rf_us is None else rf_us
    want = [m["cc"] for m in MARKETS if cov["markets"][m["cc"]]["ok"] or (dec["mode"] == "usd" and m["cc"] in PRIMARY)] if include_all else list(dec["markets"])
    frames, seen_min, src = {}, [], {}
    for cc in want:
        m = MK[cc]
        px = clip_daily(load_etf(cc), end)
        c = cov["markets"][cc]
        if c["fx_cov"]["ok"] and c["rate_cov"]["ok"]:
            fx = clip_daily(load_fx_raw(m["fx"]), end)
            rate, rs = rate_series(cc, c["rate_cov"]["source"])
        else:                                                            # USD 판(주 시장 · 현지 자료가 빔) — 현지 열은 NaN
            fx = pd.Series(np.nan, index=px.index)
            rate, rs = None, None
        seen_min += [px.index.min()] + ([fx.dropna().index.min()] if fx.notna().any() else [])
        frames[cc] = market_frame(px, fx, m["inverse"], rate, rfu, sched)
        src[cc] = {"etf": m["etf"], "fx": m["fx"], "fx_inverse": m["inverse"], "rate": m["rate"], "rate_source": rs}
    input_min = min(seen_min) if seen_min else None
    assert_window(frames, input_min)
    meta = {"mode": dec["mode"], "markets": dec["markets"], "substituted": dec["substituted"], "empty": dec["empty"], "sources": src,
            "input_min": str(pd.Timestamp(input_min).date()) if input_min is not None else None, "t1_last": str(end.date()),
            "calendar": os.path.basename(SPY_CAL), "calendar_sha256": sha256_file(SPY_CAL) if sessions is None and os.path.exists(SPY_CAL) else None}
    return frames, meta


def primary_view(frames, meta):
    """판정 모드(local · usd)의 주 시장 10 만 re_sig · re_hold · down · tr 로."""
    return view({cc: frames[cc] for cc in meta["markets"]}, meta["mode"])


# ══════════════════════════════════════════════════════════════════════════
#  라벨 · 충실도 도우미(굽기 전용 — 등록 전 실자료에선 눈가린 연기로만 부른다)
# ══════════════════════════════════════════════════════════════════════════
def crash_labels(v):
    """시장별 CRASH-M / SURGE-M: 그 시장 달 TR(tr · 판정 모드)의 창 안(채점 240개월) SD 로 ≤ −σ / ≥ +σ (명세 «시장별 창 안 SD»)."""
    hold = pd.period_range(SCORE[0], SCORE[1], freq="M")
    out = {}
    for cc, g in v.items():
        r = g["tr"].reindex(hold)
        sd = float(r.std(ddof=1))
        out[cc] = pd.DataFrame({"crash": r <= -sd, "surge": r >= sd}, index=hold)
    return out


def load_french_intl(path=None):
    """French F-F_International_Countries.zip → {파일 이름(Japan · UK · Swtzrlnd …): 달 Mkt(USD · 소수)}. 충실도 대조(보고)만 — 신호에 쓰지 않는다."""
    p = path or registry()["french/intl_countries"]["path"]
    out = {}
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            base = os.path.splitext(os.path.basename(name))[0]
            s = _french_mkt_monthly(z.read(name).decode("latin-1", "replace"))
            if s is not None and len(s):
                out[base] = s[s.index >= pd.Period(BASE_MONTH, "M")]         # 20년 규칙: 창 앞(2005-08 전) 달은 들이지 않는다
    return out


def _french_mkt_monthly(txt, title=("Value-Weight Dollar Returns", "Not Reqd")):
    """첫 «Value-Weight Dollar Returns · All 4 Data Items Not Reqd» 절의 달 행(YYYYMM)에서 Mkt 열(%) — 머리에 날짜 열 이름이 없어 한 칸 민다."""
    lines = txt.replace("\r\n", "\n").split("\n")
    i, n = 0, len(lines)
    while i < n and not all(t in lines[i] for t in title):
        i += 1
    if i >= n:
        return None
    hdr = None
    while i < n and hdr is None:
        if "Mkt" in lines[i].split():
            hdr = lines[i].split()
        i += 1
    if hdr is None:
        return None
    k = hdr.index("Mkt") + 1
    dates, vals = [], []
    while i < n:
        a = lines[i].split()
        if not a:
            if dates:
                break
            i += 1
            continue
        if not (a[0].isdigit() and len(a[0]) == 6):
            break
        try:
            v = float(a[k])
        except (ValueError, IndexError):
            v = np.nan
        dates.append(a[0][:4] + "-" + a[0][4:])
        vals.append(np.nan if v in (-99.99, -999.0) else v / 100.0)
        i += 1
    if not dates:
        return None
    return pd.Series(vals, index=pd.PeriodIndex(dates, freq="M"))


def french_sign_agreement(frames, fr):
    """자료 충실도(보고): 시장별 USD D0 달 수익과 French 국가 Mkt(USD) 부호 일치 {n, n_agree} — 채점 창 안 겹친 달만."""
    hold = pd.period_range(SCORE[0], SCORE[1], freq="M")
    out = {}
    for cc, f in frames.items():
        name = FRENCH_COUNTRY.get(cc)
        if not name or name not in fr:
            out[cc] = {"n": 0, "n_agree": 0, "note": "French 국가 목록에 없음" if not name else "French 파일에 없음"}
            continue
        a = f["usd_d0"].reindex(hold)
        b = fr[name].reindex(hold)
        ok = a.notna() & b.notna()
        out[cc] = {"n": int(ok.sum()), "n_agree": int((np.sign(a[ok]) == np.sign(b[ok])).sum())}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험(망 · 캐시 · 실자료를 읽지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _syn_sessions(first="2005-08-01", last="2026-09-30", holidays=()):
    d = pd.bdate_range(first, last)
    return d[~d.isin(pd.DatetimeIndex(list(holidays)))]


def _st_fx_direction():
    """🚨 I 층 FX 역수 방향 (USD/현지 계열) — 명세 selftest."""
    # (1) 명세 표지 ⇔ FRED 호가 이름 규칙: DEXUSxx = USD per xx(역수) · DEXxxUS = xx per USD(직접)
    for m in MARKETS:
        by_name = m["fx"].startswith("DEXUS")
        assert m["inverse"] == by_name, (m["cc"], m["fx"], m["inverse"])
    assert [m["cc"] for m in MARKETS if m["inverse"]] == ["GB", "DE", "FR", "IT", "AU", "NL", "ES"], "역수 시장 목록"
    assert [(_parse_fx(x["fx"])[1]) for x in SPEC_MARKETS] == [False, True, True, True, True, False, False, False, True, False]
    # (2) 합성: USD 가격 평평 · 현지 통화 10% 약세(현지/USD 1.10배) → 현지 TR = +10% — 직접 · 역수 호가 모두
    ses = _syn_sessions("2005-08-01", "2005-10-31")
    sch = schedule(ses, "2005-08", "2005-09")
    d0, d1 = sch["d"].iloc[0], sch["d"].iloc[1]
    px = pd.Series(50.0, index=ses)
    jpy = pd.Series(np.where(ses <= d0, 100.0, 110.0), index=ses)          # JPY per USD (직접)
    usd_per_gbp = pd.Series(np.where(ses <= d0, 2.0, 2.0 / 1.1), index=ses)  # USD per GBP (역수가 필요)
    for raw, inv in ((jpy, False), (usd_per_gbp, True)):
        X0 = local_per_usd(value_asof(raw, [d0], FX_STALE_DAYS)[0], inv).iloc[0]
        X1 = local_per_usd(value_asof(raw, [d1], FX_STALE_DAYS)[0], inv).iloc[0]
        tr = (50.0 * X1) / (50.0 * X0) - 1.0
        assert abs(tr - 0.10) < 1e-12, (inv, tr)
    # (3) 틀린 방향(역수를 빼먹음)은 −9.09% 로 부호가 뒤집힌다 — 시험이 방향 실수를 잡는다
    wrong = (value_asof(usd_per_gbp, [d1], 7)[0][0] / value_asof(usd_per_gbp, [d0], 7)[0][0]) - 1.0
    assert wrong < 0 and abs(wrong - (1 / 1.1 - 1)) < 1e-12
    # (4) 항등식: 1 + TR_loc = (1 + TR_usd)·X_t/X_{t−1} — market_frame 전 경로(역수 호가)
    ses2 = _syn_sessions("2005-08-01", "2026-09-30")
    sch2 = schedule(ses2)
    rng = np.random.default_rng(1)
    pxu = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, len(ses2)))), index=ses2)
    q = pd.Series(1.3 * np.exp(np.cumsum(rng.normal(0, 0.005, len(ses2)))), index=ses2)           # USD per EUR
    rate = pd.Series(2.0, index=pd.period_range(*RATE_MONTHS, freq="M"))
    rfu = pd.Series(0.001, index=pd.period_range(WARM[0], SCORE[1], freq="M"))
    f_inv = market_frame(pxu, q, True, rate, rfu, sch2)
    f_dir = market_frame(pxu, 1.0 / q, False, rate, rfu, sch2)                                     # 같은 환율을 EUR per USD 로 준 판
    assert np.allclose(f_inv["tr_d0"], f_dir["tr_d0"], atol=1e-12) and np.allclose(f_inv["tr_t1"].dropna(), f_dir["tr_t1"].dropna(), atol=1e-12)
    xd = 1.0 / value_asof(q, sch2["d"], 7)[0]
    ratio = xd[1:] / xd[:-1]
    assert np.allclose(1 + f_inv["tr_d0"].to_numpy(), (1 + f_inv["usd_d0"].to_numpy()) * ratio, atol=1e-12)
    # (5) USD 가 강해지면(q = USD/EUR 하락) 유로 투자자 TR > USD TR
    up = f_inv["tr_d0"] > f_inv["usd_d0"]
    qd = value_asof(q, sch2["d"], 7)[0]
    assert bool((up.to_numpy() == (qd[1:] < qd[:-1])).all())
    # (6) 실자료 방향 띠: 현지/USD 수준 표 — 역수를 빼먹으면 띠를 벗어난다(EUR 1.3 → 띠 0.55~1.20 밖)
    lo, hi = FX_LEVEL_BAND["EUR"]
    assert not (lo <= 1.3 <= hi) and (lo <= 1 / 1.3 <= hi)
    lo, hi = FX_LEVEL_BAND["JPY"]
    assert (lo <= 110 <= hi) and not (lo <= 1 / 110 <= hi)
    return "FX 방향: 명세 표지 = 호가 이름(DEXUS* 역수 7) · 직접/역수 합성 +10% · 누락 역수 −9.09% 탐지 · 항등식 · 수준 띠"


def _st_schedule_t1():
    hol = ["2006-09-04", "2009-12-31"]                                       # 가짜 휴일(달 마지막 날 포함)
    ses = _syn_sessions("2005-08-01", "2026-09-30", hol)
    sch = schedule(ses)
    assert str(sch.index[0]) == BASE_MONTH and str(sch.index[-1]) == SCORE[1] and len(sch) == 253
    assert sch.loc[pd.Period("2009-12", "M"), "d"] == pd.Timestamp("2009-12-30")           # 휴일이면 그 전 거래일
    assert sch.loc[pd.Period("2006-08", "M"), "t1"] == pd.Timestamp("2006-09-01")
    assert sch.loc[pd.Period("2026-08", "M"), "t1"] == pd.Timestamp("2026-09-01")
    for m, r in sch.iterrows():
        assert r["t1"] > r["d"] and r["d"].to_period("M") == m
        k = ses.searchsorted(r["d"], side="right")
        assert ses[k] == r["t1"]
    # T+1 이 FX 휴일이면 직전 영업일 값 · 7일 넘게 비면 없음
    s = pd.Series([1.0, 2.0, np.nan, 4.0], index=pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]))
    v, ex, fi, mi, st = value_asof(s, pd.DatetimeIndex(["2020-01-06", "2020-01-20", "2020-01-07"]), 7)
    assert v[0] == 2.0 and fi[0] and not ex[0] and mi[1] and ex[2] and v[2] == 4.0
    # 달력이 T+1 까지 안 닿으면 멈춘다
    try:
        schedule(_syn_sessions("2005-08-01", "2026-08-31"))
        raise AssertionError("T+1 끝 점검 실패")
    except SystemExit:
        pass
    return "달력: d_m = 마지막 거래일(휴일 앞당김) · T1 = 다음 거래일 · 끝 2026-09-01 · FX 직전 영업일 채움 · 늦음 한도"


def _st_rates_rf():
    months = pd.period_range(*RATE_MONTHS, freq="M")
    s = pd.Series(np.arange(len(months), dtype=float), index=months)
    y, c = rate_fill(s)
    assert c["interior_missing"] == 0 and c["tail_missing"] == 0 and c["present"] == len(months)
    s2 = s.iloc[:-3]
    y2, c2 = rate_fill(s2)
    assert c2["tail_missing"] == 3 and c2["tail_carried"] == 3 and y2.iloc[-1] == s2.iloc[-1] and y2.notna().all()
    s3 = s.iloc[:-4]
    y3, c3 = rate_fill(s3)
    assert c3["tail_missing"] == 4 and c3["tail_carried"] == 4 and y3.notna().all() and y3.iloc[-1] == s3.iloc[-1]   # 명세: 상한 없이 마지막 공표값
    y3b, c3b = rate_fill(s3, tail_max=3)                                         # 수를 주면 그 수까지(함수 인자 · 등록 판은 None)
    assert c3b["tail_carried"] == 3 and y3b.isna().sum() == 1
    s3c = s.iloc[:-7]
    _, c3c = rate_fill(s3c)
    assert c3c["tail_missing"] == 7 and c3c["tail_carried"] == 7 and RATE_TAIL_MAX is None
    s4 = s.drop(months[100])
    _, c4 = rate_fill(s4)
    assert c4["interior_missing"] == 1
    # rf_u = rate(u−1)/1200 — market_frame 정렬
    ses = _syn_sessions()
    sch = schedule(ses)
    px = pd.Series(10.0, index=ses)
    fx = pd.Series(1.0, index=ses)
    rate = pd.Series(np.arange(len(months), dtype=float) + 1.0, index=months)
    rfu = pd.Series(0.0, index=pd.period_range(WARM[0], SCORE[1], freq="M"))
    f = market_frame(px, fx, False, rate, rfu, sch)
    for u in (pd.Period("2005-09", "M"), pd.Period("2016-01", "M"), pd.Period("2026-08", "M")):
        assert abs(f.loc[u, "rf"] - rate[u - 1] / 1200.0) < 1e-15
        assert abs(f.loc[u, "re_d0"] + f.loc[u, "rf"]) < 1e-15              # 가격 평평 → 초과 = −rf
    # USD rf: rf_monthly(월복리) → y/12 → 보유월 u
    tmp = os.path.join(tempfile.gettempdir(), "_x_intl_st_rf.json")
    ym = {str(p): (1 + 0.03 + 0.0001 * i) ** (1 / 12) - 1 for i, p in enumerate(pd.period_range("2005-01", "2026-09", freq="M"))}
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"monthly": ym}, fh)
    try:
        r = rf_us_monthly(tmp)
    finally:
        os.remove(tmp)
    i = list(pd.period_range("2005-01", "2026-09", freq="M")).index(pd.Period("2016-04", "M"))
    assert abs(r[pd.Period("2016-05", "M")] - (0.03 + 0.0001 * i) / 12) < 1e-14
    assert str(r.index.min()) == "2005-09" and str(r.index.max()) == "2026-08"          # 입력 2005-08 ~ 2026-07 만
    return "금리: rf_u = rate(u−1)/1200 · 끝 빈 달 마지막 공표값 유지(상한 없음 · 명세) · 안쪽 빈 달 셈 · USD rf = DGS3MO(u−1)/12(월복리 되돌림)"


def _syn_cov(bad=(), bad_etf=(), pending=()):
    cov = {}
    for m in MARKETS:
        ok = m["cc"] not in bad and m["cc"] not in pending
        e_ok = m["cc"] not in bad_etf
        cov[m["cc"]] = {"ok": ok and e_ok, "etf_cov": {"ok": e_ok}, "fx_cov": {"ok": ok}, "rate_cov": {"ok": ok, "pending_oecd": m["cc"] in pending}}
    return cov


def _st_decide():
    d = decide(_syn_cov())
    assert d["mode"] == "local" and d["markets"] == PRIMARY and not d["substituted"]
    d = decide(_syn_cov(["KR"]))
    assert d["mode"] == "local" and d["substituted"] == {"KR": "NL"} and d["markets"][-1] == "NL" and len(d["markets"]) == 10
    d = decide(_syn_cov(["SE", "KR"]))
    assert d["mode"] == "local" and d["substituted"] == {"SE": "NL", "KR": "ES"}
    d = decide(_syn_cov(["KR", "NL"]))
    assert d["mode"] == "local" and d["substituted"] == {"KR": "ES"}
    d = decide(_syn_cov(["SE", "KR", "NL"]))
    assert d["mode"] == "usd" and "모자람" in d["why"] and d["markets"] == PRIMARY
    d = decide(_syn_cov(["JP", "SE", "KR"]))
    assert d["mode"] == "usd" and d["markets"] == PRIMARY
    d = decide(_syn_cov(["DE", "FR", "IT", "NL", "ES"]))                     # DEXUSEU 가 비면 유로 셋 → USD 판
    assert d["mode"] == "usd"
    try:
        decide(_syn_cov(["JP", "SE", "KR"], bad_etf=["JP"]))
        raise AssertionError("USD 판 ETF 빈 경우 멈춤 실패")
    except SystemExit:
        pass
    d = decide(_syn_cov(pending=["GB"]))                                       # FRED 빔 · OECD 미시도 → 보류(대체하지 않는다)
    assert d["mode"] == "pending" and d["pending_oecd"] == ["GB"] and not d["substituted"]
    return "OECD 미시도 → 보류 · 전환 규칙: 0 → 그대로 · 1~2 → NL · ES 순서 · 셋 이상/대체 모자람 → USD 판 전체 · 유로 FX 빔 → USD · USD 판 ETF 빔 → 멈춤"


def _syn_world(seed=7):
    ses = _syn_sessions()
    rng = np.random.default_rng(seed)
    n = len(ses)
    px = {m["cc"]: pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.012, n))), index=ses) for m in MARKETS}
    lvl = {"DEXJPUS": 110, "DEXUSUK": 1.6, "DEXUSEU": 1.2, "DEXSZUS": 1.0, "DEXSDUS": 8.0, "DEXCAUS": 1.2, "DEXUSAL": 0.75, "DEXKOUS": 1150}
    fx = {f: pd.Series(lvl[f] * np.exp(np.cumsum(rng.normal(0, 0.003, n)) * 0.3), index=ses) for f in FX_IDS}
    months = pd.period_range(*RATE_MONTHS, freq="M")
    rate = {m["cc"]: pd.Series(1.0 + rng.normal(0, 0.2, len(months)).cumsum() * 0.05, index=months) for m in MARKETS}
    rfu = pd.Series(0.001, index=pd.period_range(WARM[0], SCORE[1], freq="M"))
    return ses, px, fx, rate, rfu


def _panel_from(ses, px, fx, rate, rfu, ccs=None):
    sch = schedule(ses)
    return {cc: market_frame(px[cc], fx[MK[cc]["fx"]], MK[cc]["inverse"], rate[cc], rfu, sch) for cc in (ccs or PRIMARY)}


def _st_window_and_lookahead():
    ses, px, fx, rate, rfu = _syn_world()
    P = _panel_from(ses, px, fx, rate, rfu)
    assert_window(P, ses.min())
    for cc, f in P.items():
        assert str(f.index.min()) == WARM[0] and str(f.index.max()) == SCORE[1] and len(f) == 252
        h = f["re_t1"].dropna()
        assert str(h.index.min()) == SCORE[0] and str(h.index.max()) == SCORE[1] and len(h) == N_SCORE
        assert f.loc[pd.period_range(*WARM, freq="M"), "re_t1"].isna().all()           # 워밍업은 채점 행이 없다
        assert f["re_d0"].notna().all() and f["re_usd_d0"].notna().all()
    # 단언: 입력이 2005-08-01 앞이면 멈춘다 · 보유 행이 창 밖이면 멈춘다
    for bad in ((P, "2005-07-29"),):
        try:
            assert_window(bad[0], bad[1])
            raise AssertionError("입력 최소 단언 실패")
        except SystemExit:
            pass
    Q = {k: v.copy() for k, v in P.items()}
    Q["JP"].loc[pd.Period("2006-08", "M"), "re_t1"] = 0.0
    try:
        assert_window(Q)
        raise AssertionError("보유 창 단언 실패")
    except SystemExit:
        pass
    early = pd.Series(1.0, index=pd.DatetimeIndex(["2005-07-29", "2005-08-01"]))
    assert clip_daily(early, "2026-09-01").index.min() == pd.Timestamp(INPUT_MIN)
    # 선견: d_t 뒤 자료(ETF · FX · 금리 t 달 이후)를 흔들어도 re_sig[≤ t] 불변 · T+1 보유 행은 T1(d_t) 뒤를 흔들어도 u ≤ t 불변
    sch = schedule(ses)
    rng = np.random.default_rng(11)
    for t in (pd.Period("2006-08", "M"), pd.Period("2012-03", "M"), pd.Period("2020-02", "M"), pd.Period("2026-07", "M")):
        dt = sch.loc[t, "d"]
        t1 = sch.loc[t, "t1"]
        px2 = {cc: s.where(s.index <= dt, s * np.exp(rng.normal(0, 0.2, len(s)))) for cc, s in px.items()}
        fx2 = {f: s.where(s.index <= dt, s * np.exp(rng.normal(0, 0.2, len(s)))) for f, s in fx.items()}
        rate2 = {cc: s.where(s.index < t, s + rng.normal(0, 3, len(s))) for cc, s in rate.items()}
        P2 = _panel_from(ses, px2, fx2, rate2, rfu)
        for cc in PRIMARY:
            a, b = P[cc].loc[:t, "re_d0"], P2[cc].loc[:t, "re_d0"]
            assert np.allclose(a, b, atol=1e-13, equal_nan=True), (cc, t)
        px3 = {cc: s.where(s.index <= t1, s * 1.5) for cc, s in px.items()}
        fx3 = {f: s.where(s.index <= t1, s * 0.7) for f, s in fx.items()}
        P3 = _panel_from(ses, px3, fx3, rate, rfu)
        for cc in PRIMARY:
            assert np.allclose(P[cc].loc[:t, "re_t1"], P3[cc].loc[:t, "re_t1"], atol=1e-13, equal_nan=True), (cc, t)
    return "창 · 선견: 신호 행 2005-09 ~ 2026-08(252) · 보유 행 2006-09 ~ 2026-08(240) · 워밍업 채점 없음 · 입력 < 2005-08-01 · 창 밖 보유 멈춤 · d_t 뒤 흔들기 불변"


def _st_views_and_labels():
    ses, px, fx, rate, rfu = _syn_world(3)
    P = _panel_from(ses, px, fx, rate, rfu)
    vl, vu = view(P, "local"), view(P, "usd")
    for cc in PRIMARY:
        assert np.allclose(vl[cc]["re_sig"], P[cc]["re_d0"], equal_nan=True) and np.allclose(vu[cc]["re_hold"], P[cc]["re_usd_t1"], equal_nan=True)
        assert np.allclose(P[cc]["re_usd_d0"], P[cc]["usd_d0"] - rfu.reindex(P[cc].index).to_numpy())
        assert bool(((vl[cc]["down"] == 1) == (P[cc]["re_d0"] < 0)).all())
    cl = crash_labels(vl)
    for cc in PRIMARY:
        r = vl[cc]["tr"].reindex(cl[cc].index)
        sd = r.std(ddof=1)
        assert bool((cl[cc]["crash"] == (r <= -sd)).all()) and len(cl[cc]) == N_SCORE and not bool((cl[cc]["crash"] & cl[cc]["surge"]).any())
    fr = {"Japan": P["JP"]["usd_d0"] * 1.01, "Germany": -P["DE"]["usd_d0"]}                 # 키 = French 파일 이름
    sa = french_sign_agreement(P, fr)
    assert sa["JP"]["n"] == N_SCORE and sa["JP"]["n_agree"] == N_SCORE and sa["DE"]["n_agree"] == 0 and sa["KR"]["n"] == 0
    txt = ("\n     Value-Weight Dollar Returns      All 4 Data Items Not Reqd\n                -- BE/ME --   --- E/P ---\n"
           "          Mkt   High    Low   High    Low\n197501    1.00   2.00   3.00   4.00   5.00\n197502  -99.99   1.00   1.00   1.00   1.00\n\n"
           "     Value-Weight Local  Returns      All 4 Data Items Not Reqd\n          Mkt   High    Low   High    Low\n197501    9.00   9.00   9.00   9.00   9.00\n")
    s = _french_mkt_monthly(txt)
    assert len(s) == 2 and abs(s.iloc[0] - 0.01) < 1e-15 and np.isnan(s.iloc[1]) and str(s.index[0]) == "1975-01"
    assert _french_mkt_monthly("no such section\n197501 1 2\n") is None
    try:
        view(P, "eur")
        raise AssertionError("mode 점검 실패")
    except ValueError:
        pass
    return "보기 · 라벨: local/usd 열 대응 · USD 초과 = USD TR − DGS3MO(u−1)/12 · 하락월 = 초과 < 0 · CRASH/SURGE 창 안 SD · French 부호 일치 · French 파서"


def _st_coverage_synthetic():
    ses, px, fx, rate, rfu = _syn_world(5)
    fx_bad = dict(fx)
    s = fx["DEXKOUS"].copy()
    s[(s.index >= "2012-03-01") & (s.index <= "2012-04-30")] = np.nan          # 두 달 빈 FX → KR 빈다
    fx_bad["DEXKOUS"] = s
    rate_bad = dict(rate)
    rate_bad["SE"] = rate["SE"].drop(rate["SE"].index[[60, 61]])                   # 안쪽 두 달 없음 → FRED 빈다 → OECD 없음 → SE 빈다
    rate_tail = dict(rate)
    rate_tail["SE"] = rate["SE"].iloc[:-5]                                       # 끝 5개월 없음 → 마지막 공표값 유지(명세 · 상한 없음) → 빈 시장 아님
    L = {"etf": lambda cc: px[cc], "fx": lambda fid: fx_bad[fid], "rate": lambda cc, src: rate_bad[cc] if src == "fred" else None,
         "etf_capgain_rows": lambda cc: 0}
    cov = coverage(sessions=ses, loaders=L, rf_us=rfu)
    assert cov["markets"]["KR"]["fx_cov"]["ok"] is False and cov["markets"]["KR"]["fx_cov"]["n_need_missing"] >= 1
    assert cov["markets"]["SE"]["rate_cov"]["ok"] is False and cov["markets"]["SE"]["rate_cov"]["by_source"]["fred"]["interior_missing"] == 2
    Lt = dict(L, fx=lambda fid: fx[fid], rate=lambda cc, src: rate_tail[cc] if src == "fred" else None)
    covt = coverage(sessions=ses, loaders=Lt, rf_us=rfu)
    rs = covt["markets"]["SE"]["rate_cov"]
    assert rs["ok"] and rs["source"] == "fred" and rs["by_source"]["fred"]["tail_missing"] == 5 and rs["by_source"]["fred"]["tail_carried"] == 5
    assert covt["decision"]["mode"] == "local" and covt["decision"]["empty"] == [] and covt["decision"]["markets"] == list(PRIMARY)
    assert cov["markets"]["JP"]["ok"] and cov["markets"]["NL"]["ok"] and cov["markets"]["ES"]["ok"]
    d = cov["decision"]
    assert d["mode"] == "local" and d["substituted"] == {"SE": "NL", "KR": "ES"}
    pub = f0_block(cov)
    no_value_series(pub)
    js = json.dumps(pub, ensure_ascii=False)
    assert "re_" not in js and "tr_d0" not in js
    # OECD 대안: FRED 가 비고 OECD 가 덮으면 OECD 로
    L2 = dict(L)
    L2["rate"] = lambda cc, src: (rate_bad[cc] if src == "fred" else rate[cc])
    cov2 = coverage(sessions=ses, loaders=L2, rf_us=rfu)
    assert cov2["markets"]["SE"]["rate_cov"]["source"] == "oecd" and cov2["markets"]["SE"]["ok"]
    # 방향 띠: 역수를 빼먹은 표(USD/EUR 를 그대로)면 띠 밖 → FX 빈다
    bad_mk = dict(MK["DE"])
    MK["DE"] = dict(bad_mk, inverse=False)
    try:
        cov3 = coverage(sessions=ses, loaders=L, rf_us=rfu)
        assert cov3["markets"]["DE"]["fx_cov"]["level_band_ok"] is False and not cov3["markets"]["DE"]["ok"]
    finally:
        MK["DE"] = bad_mk
    return "커버리지(합성): FX 두 달 빔 · 금리 안쪽 두 달 → 빈 시장 · 금리 끝 5개월 → 마지막 공표값(빈 시장 아님) · NL/ES 대체 · OECD 대안 · 역수 누락 띠 탐지 · 공개 블록 값 없음"


def _st_guard():
    fake_root = os.path.join(tempfile.gettempdir(), "_x_intl_fake_repo")
    try:
        cache_guard(os.path.join(fake_root, "cache"), fake_root)
        raise AssertionError("캐시 가드 실패")
    except SystemExit:
        pass
    try:
        guard_write_path(os.path.join(ROOT, "data", "_xb_intl_panel.json"))
        raise AssertionError("저장소 쓰기 가드 실패")
    except SystemExit:
        pass
    try:
        guard_write_path(os.path.join(tempfile.gettempdir(), "elsewhere", "x.json"))
        raise AssertionError("캐시 밖 쓰기 가드 실패")
    except SystemExit:
        pass
    assert guard_write_path(os.path.join(CACHE, "out", "x.json"))
    for bad in ({"a": [0.1, 0.2]}, {"a": [1, 2, 3, 4, 5, 6]}, {"a": {"b": 0.03}}):
        try:
            no_value_series(bad)
            raise AssertionError("값 계열 가드 실패")
        except SystemExit:
            pass
    assert no_value_series({"n": 240, "first": "2006-09", "ok": True, "l": [1, 2]})
    return "가드: 저장소 안 캐시 · 저장소/캐시 밖 쓰기 · 공개 요약 값 계열 · 정수 아닌 수 — 모두 멈춘다"


def _st_spec_table():
    assert PRIMARY == ["JP", "GB", "DE", "FR", "IT", "CH", "SE", "CA", "AU", "KR"] and SUBSTITUTES == ["NL", "ES"]
    assert [MK[c]["etf"] for c in PRIMARY] == ["EWJ", "EWU", "EWG", "EWQ", "EWI", "EWL", "EWD", "EWC", "EWA", "EWY"]
    assert [MK[c]["etf"] for c in SUBSTITUTES] == ["EWN", "EWP"]
    assert all(MK[c]["rate"] == "IR3TIB01%sM156N" % c for c in PRIMARY + SUBSTITUTES)
    assert FX_IDS == sorted(["DEXJPUS", "DEXUSUK", "DEXUSEU", "DEXSZUS", "DEXSDUS", "DEXCAUS", "DEXUSAL", "DEXKOUS"])
    assert (INPUT_MIN, WARM, SCORE) == ("2005-08-01", ("2005-09", "2006-08"), ("2006-09", "2026-08"))
    assert len(pd.period_range(*SCORE, freq="M")) == N_SCORE
    assert all(u.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?id=") and u.endswith("cosd=2005-08-01")
               for u in (fred_url(x) for x in FX_IDS + RATE_IDS))
    return "명세 표: 시장 10 · 대체 NL→ES · ETF · IR3TIB01{cc}M156N · FX 8 · 창 상수 · 받기 시작 2005-08-01"


SELFTESTS = (_st_spec_table, _st_fx_direction, _st_schedule_t1, _st_rates_rf, _st_decide, _st_window_and_lookahead, _st_views_and_labels,
             _st_coverage_synthetic, _st_guard)


def selftest():
    res, bad = [], 0
    for fn in SELFTESTS:
        t0 = time.time()
        try:
            msg = fn()
            res.append("  ✓ %-28s %.2fs  %s" % (fn.__name__, time.time() - t0, msg))
        except Exception:
            bad += 1
            res.append("  ✗ %-28s %s" % (fn.__name__, traceback.format_exc(limit=3).strip().replace("\n", " | ")))
    print("x_intl selftest — 합성만(망 · 캐시 · 실자료 없음)")
    print("\n".join(res))
    print("결과: %d/%d 통과" % (len(SELFTESTS) - bad, len(SELFTESTS)))
    return bad == 0


# ══════════════════════════════════════════════════════════════════════════
#  실자료 눈가린 연기(모양 · 개수 · 시간만)
# ══════════════════════════════════════════════════════════════════════════
def shape_of(x):
    if isinstance(x, pd.DataFrame):
        return {"type": "DataFrame", "rows": int(x.shape[0]), "cols": list(map(str, x.columns)), "first": str(x.index.min()), "last": str(x.index.max()),
                "n_nan": {str(c): int(x[c].isna().sum()) for c in x.columns}}
    if isinstance(x, pd.Series):
        return {"type": "Series", "n": int(len(x)), "n_nan": int(x.isna().sum())}
    if isinstance(x, dict):
        return {"type": "dict", "n": len(x), "keys": sorted(map(str, x))[:12]}
    return {"type": type(x).__name__}


def smoke():
    """실자료로 커버리지 → 패널 → 보기 → 라벨 · 충실도(눈가림). 값은 보지 않는다: 산출은 캐시에 쓰고 읽지 않은 채 지운다."""
    cache_guard()
    T = {}
    t0 = time.time()
    cov = coverage()
    T["coverage_s"] = round(time.time() - t0, 2)
    t0 = time.time()
    frames, meta = build_panel(cov)
    T["panel_s"] = round(time.time() - t0, 2)
    t0 = time.time()
    frames_all, meta_all = build_panel(cov, include_all=True)
    T["panel_all_s"] = round(time.time() - t0, 2)
    v = primary_view(frames, meta)
    vu = view({cc: frames_all[cc] for cc in meta["markets"] if cc in frames_all}, "usd")
    t0 = time.time()
    cl = crash_labels(v)
    T["labels_s"] = round(time.time() - t0, 2)
    fr_shape, sa_shape = None, None
    fp = registry()["french/intl_countries"]["path"]
    if os.path.exists(fp):
        t0 = time.time()
        fr = load_french_intl(fp)
        sa = french_sign_agreement(frames_all, fr)
        T["french_s"] = round(time.time() - t0, 2)
        fr_shape = {"n_countries": len(fr), "countries": sorted(fr)[:14],
                    "spans": {k: [str(s.index.min()), str(s.index.max()), int(len(s))] for k, s in fr.items() if k in FRENCH_COUNTRY.values()}}
        sa_shape = {cc: sorted(d.keys()) for cc, d in sa.items()}
        del fr, sa
    # 눈가림: 값이 든 것은 캐시에 쓰고 읽지 않고 지운다
    blind = os.path.join(CACHE, "out", "_smoke_intl_%d.pkl" % os.getpid())
    guard_write_path(blind)
    os.makedirs(os.path.dirname(blind), exist_ok=True)
    pd.to_pickle({"frames": frames, "v": v, "vu": vu, "labels": cl}, blind)
    nbytes = os.path.getsize(blind)
    os.remove(blind)
    fs = {cc: shape_of(f) for cc, f in frames.items()}
    nan_rng = {c: [min(x["n_nan"][c] for x in fs.values()), max(x["n_nan"][c] for x in fs.values())] for c in COLS}
    shp = {"mode": meta["mode"], "markets": meta["markets"], "substituted": meta["substituted"], "empty": meta["empty"],
           "input_min": meta["input_min"], "t1_last": meta["t1_last"], "calendar_sha256": (meta["calendar_sha256"] or "")[:12],
           "frames": {"n": len(fs), "rows": sorted({x["rows"] for x in fs.values()}), "first": sorted({x["first"] for x in fs.values()}),
                      "last": sorted({x["last"] for x in fs.values()}), "cols": list(COLS), "n_nan_min_max": nan_rng},
           "view_cols": sorted(next(iter(v.values())).columns) if v else [],
           "usd_view_n": len(vu), "labels": {cc: [int(len(x)), sorted(x.columns)] for cc, x in list(cl.items())[:2]},
           "all_markets": sorted(frames_all), "french": fr_shape, "french_sign_keys": sa_shape, "blind_pickle_bytes": int(nbytes), "timings": T}
    del frames, frames_all, v, vu, cl
    return shp


def _print_cov(pub):
    print("I 층 커버리지 (개수 · 날짜 · 참/거짓만)")
    w = pub["window"]
    print("  창: 입력 ≥ %s · 워밍업 %s~%s · 채점 %s~%s · d 첫 %s · T1 끝 %s · 달 %d" % (w["input_min"], w["warm"][0], w["warm"][1], w["score"][0], w["score"][1],
                                                                            w["d_first"], w["t1_last"], w["n_months_sched"]))
    for cc, m in pub["markets"].items():
        rs = m["rate_by_source"].get("fred", {})
        ro = m["rate_by_source"].get("oecd")
        oe = (" · OECD 있음 %s 안빔 %s 끝빔 %s 끝 %s" % (ro.get("present"), ro.get("interior_missing"), ro.get("tail_missing"), ro.get("last_obs"))) if ro else ""
        print("  %-2s %-9s %-3s ETF %s~%s 빈거래일 %s 채움 %s 없음 %s | FX %s%s %s~%s 공백 %s 채움 %s 없음 %s 띠 %s | 금리 %s(%s) FRED 있음 %s 안빔 %s 끝빔 %s 끝 %s%s | %s"
              % (cc, m["role"], m["etf"], m["etf_first"], m["etf_last"], m["etf_n_sessions_missing"], m["etf_n_need_filled"], m["etf_n_need_missing"],
                 m["fx"], "⁻¹" if m["fx_inverse"] else "", m["fx_first"], m["fx_last"], m["fx_n_blank"], m["fx_n_need_filled"], m["fx_n_need_missing"],
                 m["fx_level_band_ok"], m["rate"], m["rate_source"], rs.get("present"), rs.get("interior_missing"), rs.get("tail_missing"),
                 rs.get("last_obs"), oe, "OK" if m["ok"] else "빔"))
    d = pub["decision"]
    print("  US rf(DGS3MO) 덮음: %s" % pub["rf_us_ok"])
    print("  판정: %s · 시장 %s · 빈 %s · 대체 %s — %s" % (d["mode"], ",".join(d["markets"]), d["empty"] or "-", d["substituted"] or "-", d["why"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="배치 X · I 층 국외 패널")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--fetch-oecd", action="store_true", help="FRED 금리가 빈 시장에만 OECD SDMX 를 받는다")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--manifest", action="store_true", help="data/_xb_manifest.json 에 intl 절(값 없음 · x_data.repo_write_json)")
    ap.add_argument("--f0-merge", action="store_true", help="data/_xb_f0.json 에 intl 절(개수 · 날짜 · 판정 · x_run --f0 뒤)")
    ap.add_argument("--check", action="store_true", help="굽기 전 관문: 캐시 SHA == 명세 intl 절 · 판정 같음")
    a = ap.parse_args(argv)
    rc = 0
    if a.selftest:
        rc |= 0 if selftest() else 1
    if a.fetch:
        r = fetch_all(force=a.force)
        print("받기: 새로 %d · 그대로 %d · 실패 %d" % (len(r["fetched"]), len(r["kept"]), len(r["failed"])))
        for k, e in r["failed"].items():
            print("  실패 %s — %s" % (k, e))
        rc |= 1 if r["failed"] else 0
    if a.fetch_oecd:
        cov = coverage()
        need = [cc for cc, c in cov["markets"].items() if not c["rate_cov"]["by_source"]["fred"]["ok"]]
        for cc in need:
            try:
                p, new = fetch_one("oecd/" + cc, force=a.force)
                print("  OECD %s %s" % (cc, "받음" if new else "그대로"))
            except Exception as e:
                write_json_cache(oecd_fail_marker(cc), {"cc": cc, "url": oecd_url(cc), "at": _now(), "error": "%s: %s" % (type(e).__name__, str(e)[:300])})
                print("  OECD %s 실패 — %s: %s (시도 표지를 남긴다 → 그 시장 금리는 빈다)" % (cc, type(e).__name__, str(e)[:160]))
        if not need:
            print("  OECD: FRED 금리가 빈 시장 없음 — 받지 않음")
    if a.coverage:
        cov = coverage()
        write_json_cache(os.path.join(CACHE, "f0", "intl_coverage.json"), cov)
        pub = f0_block(cov)
        write_json_cache(os.path.join(CACHE, "f0", "intl_f0_block.json"), pub)
        _print_cov(pub)
    if a.smoke:
        shp = smoke()
        print(json.dumps(shp, ensure_ascii=False, indent=1))
    if a.manifest:
        p = write_manifest_section()
        print("명세 intl 절 → %s" % os.path.relpath(p, ROOT))
    if a.f0_merge:
        p = merge_f0_block()
        print("F0 intl 절 → %s" % os.path.relpath(p, ROOT))
    if a.check:
        r = check_pins()
        print("intl 고정본 점검: %s · 원천 %s · %s" % ("OK" if r["ok"] else "틀림", r.get("n_sources"), "; ".join(r["bad"][:5]) or "-"))
        rc |= 0 if r["ok"] else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
