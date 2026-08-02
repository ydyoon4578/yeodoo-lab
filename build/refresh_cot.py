#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CFTC 미결제약정 보고서(COT) → data/cot.json

무엇을·왜.
  data/sentiment.json 은 VIX 수준·기간구조·MOVE 를 합성한 **가격** 기반 상태 요약이다.
  COT 는 다른 축이다 — 누가 실제로 어느 쪽에 서 있는가(포지션). 이 랩이 반복해서 묻는
  '따라 사면 되는가'를 대형 투기세력에 대해 물을 수 있게 된다.

  받는 계약 셋(코드로 잡는다. 아래 ⚠ 참조):
      13874+  S&P 500 Consolidated
      20974+  NASDAQ-100 Consolidated
      1170E1  VIX FUTURES (CBOE)
  두 보고 체계를 다 받는다 —
      Legacy(6dca-aqww)  상업/비상업 — 오래된 어휘. 이력이 같은 2010-06 부터.
      TFF(gpe5-46if)     딜러/자산운용사/레버리지머니/기타 — 금융선물 전용 분류.

⚠ **발표 지연 3일이 이 파일의 핵심이다.** 화요일 장마감 포지션을 금요일 15:30 ET 에 발표한다.
  화요일 값을 화요일에 쓰면 룩어헤드다. 그래서 report_date(화) 와 함께 release(금)를
  **미리 계산해 싣는다** — 소비하는 쪽이 지연을 잊는 사고를 파일 수준에서 막는다.
  백테스트는 release 이후 첫 거래일부터 그 값을 쓸 수 있다.

⚠ 계약을 **이름이 아니라 cftc_contract_market_code 로 잡는다.** CME 가 이름을 바꾼 전례가
  있다(실측: 같은 13874A 가 'E-MINI S&P 500' 과 'E-MINI S&P 500 STOCK INDEX' 두 이름으로
  나온다). 이름을 키로 쓰면 개명하는 날 조용히 끊긴다.

⚠ 이 데이터를 읽는 법에 함정이 있다. 화면·문서에 반드시 함께 적을 것 —
  주가지수 선물의 '상업(commercial)'과 TFF 의 '딜러'는 현물 헤지 쪽이라 **구조적으로 순숏**이고,
  '자산운용사'는 인덱스 롱 대체 수단이라 **구조적으로 순롱**이다(실측 2026-07-28 S&P500:
  딜러 롱 166,249 / 숏 915,511, 자산운용사 롱 1,160,957 / 숏 214,663).
  원자재 COT 의 '상업=스마트머니' 서사를 그대로 옮기면 정확히 이 랩이 기각하려는 종류의
  오독이 된다. 절대 수준이 아니라 **자기 이력 대비 백분위/z** 로만 읽어야 한다.

⚠ 셧다운 공백은 **이 데이터셋에는 없다**(실측: 2주 이상 간격 0건). 8일 간격이 6번 있는데
  전부 명절 주간이라 기준일이 월요일로 당겨진 다음 주다 — 빠진 주가 아니다.
  그래도 ffill 은 하지 않는다. 없는 주는 없는 채로 두고, 메우는 것은 소비하는 쪽이
  한도를 명시해 할 일이다.

라이선스: 미국 정부 저작물(CFTC Public Reporting Environment, Socrata 공개 API). 인증 없음.

사용:
    python3 build/refresh_cot.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "cot.json")

BASE = "https://publicreporting.cftc.gov/resource/%s.json"
UA = {"User-Agent": "yeouido-lab/1.0 (https://github.com/ydyoon4578/yeodoo-lab) cot"}

CONTRACTS = [
    ("spx", "13874+", "S&P 500 Consolidated"),
    ("ndx", "20974+", "NASDAQ-100 Consolidated"),
    ("vix", "1170E1", "VIX FUTURES"),
]

# (데이터셋, 저장키, 소스필드) — 순포지션은 저장하지 않는다. 롱·숏을 그대로 두고
# 파생은 읽는 쪽에서 만든다(어느 정의로 뺐는지가 화면마다 달라질 수 있다).
LEGACY = "6dca-aqww"
TFF = "gpe5-46if"
LEG_F = [("comm_l", "comm_positions_long_all"), ("comm_s", "comm_positions_short_all"),
         ("ncomm_l", "noncomm_positions_long_all"), ("ncomm_s", "noncomm_positions_short_all"),
         ("ncomm_sp", "noncomm_positions_spread"),
         ("nonrep_l", "nonrept_positions_long_all"), ("nonrep_s", "nonrept_positions_short_all")]
TFF_F = [("deal_l", "dealer_positions_long_all"), ("deal_s", "dealer_positions_short_all"),
         ("am_l", "asset_mgr_positions_long"), ("am_s", "asset_mgr_positions_short"),
         ("lev_l", "lev_money_positions_long"), ("lev_s", "lev_money_positions_short"),
         ("oth_l", "other_rept_positions_long"), ("oth_s", "other_rept_positions_short")]

# 관문 — 주 수가 이보다 적으면 받아오다 만 것으로 본다(계약별 실측 하한).
MIN_WEEKS = {"spx": 700, "ndx": 700, "vix": 800}


def fetch(ds: str, code: str, fields) -> dict:
    """계약 하나의 전 이력. Socrata 는 기본 1000행이라 페이지를 넘긴다."""
    sel = ["report_date_as_yyyy_mm_dd", "open_interest_all"] + [f for _, f in fields]
    out, off = {}, 0
    while True:
        u = BASE % ds + "?" + urllib.parse.urlencode({
            "cftc_contract_market_code": code, "$select": ",".join(sel),
            "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": 1000, "$offset": off})
        rows = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=60).read().decode())
        if not rows:
            break
        for r in rows:
            d = (r.get("report_date_as_yyyy_mm_dd") or "")[:10]
            if not d:
                continue
            rec = out.setdefault(d, {})
            oi = r.get("open_interest_all")
            if oi is not None:
                rec["oi"] = int(float(oi))
            for k, f in fields:
                v = r.get(f)
                if v is not None:
                    rec[k] = int(float(v))
        off += len(rows)
        if len(rows) < 1000:
            break
        time.sleep(0.2)
    return out


def release_of(report_date: str) -> str:
    """기준일 → 그 주 금요일 15:30 ET 발표일. 이 값 **이후**에야 쓸 수 있다.

    ⚠ 단순히 +3일로 두면 안 된다. 기준일이 늘 화요일인 것이 아니다 — 실측으로 8주가
      **월요일**이었다(전부 성탄·연말·독립기념일 주간: 2012-12-24 · 2012-12-31 · 2017-07-03 ·
      2018-12-24 · 2018-12-31 · 2020-12-21 · 2023-07-03 · 2025-11-10).
      그 주에 +3 을 하면 목요일이 나오고, 그건 실제 발표(금)보다 **하루 이르다** —
      즉 아직 세상에 없던 값을 알았다고 가정하는 룩어헤드다. 방향이 나쁜 쪽으로 틀린다.

    그래서 +3일을 한 뒤 **금요일까지 앞으로 민다**. 화요일 기준일은 그대로 +3=금요일이고,
    월요일 기준일은 목→금으로 하루 밀린다. 공휴일로 발표가 더 밀리는 날은 하루 이르게
    잡힐 수 있으나, 그 방향의 오차는 소비하는 쪽이 '발표일 이후 **첫 거래일**부터 쓴다'는
    규칙으로 흡수한다.
    """
    d = dt.date.fromisoformat(report_date) + dt.timedelta(days=3)
    while d.weekday() != 4:                       # 4 = 금요일
        d += dt.timedelta(days=1)
    return d.isoformat()


def main() -> int:
    doc = {
        "note": "CFTC 미결제약정 보고서(COT). 화요일 장마감 포지션을 그 주 금요일 15:30 ET 에 "
                "발표한다 — 각 행의 release 가 '이 값을 처음 알 수 있게 된 날'이며, "
                "백테스트는 그 이후 첫 거래일부터만 써야 한다(안 그러면 룩어헤드다).",
        "warn": "주가지수 선물에서 '상업/딜러'는 현물 헤지 쪽이라 구조적 순숏이고 '자산운용사'는 "
                "인덱스 롱 대체라 구조적 순롱이다. 원자재 COT 의 '상업=스마트머니' 해석을 그대로 "
                "옮기면 안 된다 — 절대 수준이 아니라 자기 이력 대비 백분위로 읽을 것. "
                "주 간격은 8일이 되는 주가 6번 있는데(명절 주간, 기준일이 월요일로 당겨진 다음 주) 빠진 주는 아니다 — 실측 결과 이 데이터셋에 2주 이상의 공백은 없다.",
        "source": "CFTC Public Reporting Environment (Socrata) — Legacy %s · TFF %s. "
                  "계약은 이름이 아니라 cftc_contract_market_code 로 잡는다(이름은 바뀐다)."
                  % (LEGACY, TFF),
        "license": "미국 정부 저작물 · 인증 없음",
        "fields": {"legacy": [k for k, _ in LEG_F], "tff": [k for k, _ in TFF_F], "oi": "미결제약정 전체"},
        "contracts": {}, "as_of": None,
    }
    fail = []
    for key, code, name in CONTRACTS:
        leg = fetch(LEGACY, code, LEG_F)
        tff = fetch(TFF, code, TFF_F)
        dates = sorted(set(leg) | set(tff))
        if len(dates) < MIN_WEEKS[key]:
            fail.append("%s(%s) %d주 — 하한 %d 미만. 받다 말았을 가능성"
                        % (key, code, len(dates), MIN_WEEKS[key]))
            continue
        rows = {}
        for d in dates:
            r = {}
            r.update(leg.get(d, {}))
            r.update(tff.get(d, {}))
            r["release"] = release_of(d)
            rows[d] = r
        doc["contracts"][key] = {"code": code, "name": name,
                                 "start": dates[0], "end": dates[-1], "n": len(dates),
                                 "rows": rows}
        print("  %-4s %-8s %s ~ %s · %d주" % (key, code, dates[0], dates[-1], len(dates)))
        time.sleep(0.2)

    if fail:
        print("\n❌ 관문 미통과 — 파일을 건드리지 않는다:")
        for f in fail:
            print("   ·", f)
        return 1

    ends = [c["end"] for c in doc["contracts"].values()]
    doc["as_of"] = min(ends)          # 가장 뒤진 계약 기준 — 앞선 것으로 신선하다고 말하지 않는다
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print("\nCOT — 계약 %d · 기준 %s(발표 %s) · %.0fKB"
          % (len(doc["contracts"]), doc["as_of"], release_of(doc["as_of"]),
             os.path.getsize(OUT) / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
