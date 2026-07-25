#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기준일 정본 생성기 → data/asof.json

이 사이트의 1순위 원칙은 "모든 데이터의 as-of를 통일하고 메인에 표기한다"이다.
그런데 기준일은 실제로 하나가 아니다 — 가격은 매일, FINRA 공매도잔량은 격주,
지수 편입은 리밸런스 때만 바뀐다. 원칙의 진짜 뜻은 '전부 같은 날짜'가 아니라
**'축이 몇 개이고 각각 언제인지를 숨기지 않는다'** 이다.

그래서 축을 한 파일에 모아 정본으로 두고, 전 페이지 내비 칩·홈 기준일 표·
sources.html이 이 파일 하나만 읽게 한다. 페이지마다 자기 날짜를 따로 적으면
어긋나는 날 어느 쪽이 맞는지 아무도 모른다(그 사고가 이미 있었다).

  primary   = 대표 기준일(가격·테크니컬 — 화면 상단에 크게 뜨는 그 날짜)
  axes[]    = 축별 기준일과 갱신 주기
  lag_days  = primary 대비 뒤처진 영업일 수(0이면 통일)

사용: python3 build/asof_index.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "asof.json")


def load(fn: str):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def bdays(frm: str, to: str) -> int:
    """frm에서 to까지 흐른 영업일(미 휴장은 세지 않는다 — 근사치로 충분하다)."""
    try:
        a = dt.date.fromisoformat(str(frm)[:10])
        b = dt.date.fromisoformat(str(to)[:10])
    except Exception:
        return 0
    if a >= b:
        return 0
    n = 0
    while a < b:
        a += dt.timedelta(days=1)
        if a.weekday() < 5:
            n += 1
    return n


def finra_asof(stocks: dict) -> str | None:
    """공매도잔량 기준일. stocks.json의 factor_defs가 정본이고(sources.html도 여기를 읽는다),
    없으면 종목 상세 sd/의 dtc.dt로 물러선다."""
    fd = (stocks or {}).get("factor_defs") or {}
    for k in ("dtc", "sipct"):
        d = (fd.get(k) or {}).get("as_of")
        if d:
            return d
    sd = os.path.join(DATA, "sd")
    if not os.path.isdir(sd):
        return None
    for fn in sorted(os.listdir(sd))[:40]:
        if not fn.endswith(".json"):
            continue
        try:
            with io.open(os.path.join(sd, fn), encoding="utf-8") as f:
                sig = (json.load(f) or {}).get("sig") or {}
        except Exception:
            continue
        d = (sig.get("dtc") or {}).get("dt") or (sig.get("sipct") or {}).get("dt")
        if d:
            return d
    return None


def main() -> int:
    stocks = load("stocks.json") or {}
    regime = load("regime.json") or {}
    sent = load("sentiment.json") or {}
    members = load("members.json") or {}

    primary = stocks.get("as_of")
    if not primary:
        print("❌ stocks.json as_of 없음 — 정본을 만들 수 없다")
        return 1

    axes = [
        {"key": "price", "label": "가격·테크니컬·EPS", "as_of": primary,
         "cadence": "매 거래일", "note": "대표 기준일"},
        {"key": "regime", "label": "시장 국면(FRED 매크로)", "as_of": regime.get("as_of"),
         "cadence": "매 거래일", "note": "지표별 발표 주기가 달라 최신 공통일 기준"},
        {"key": "sentiment", "label": "시장 심리", "as_of": sent.get("as_of"),
         "cadence": "매 거래일", "note": "상태 요약 — 수익 예측 신호가 아니다"},
        {"key": "short", "label": "공매도잔량(FINRA)", "as_of": finra_asof(stocks),
         "cadence": "격주", "note": "FINRA 공시 주기상 구조적으로 뒤처진다"},
        {"key": "members", "label": "지수 편입(PIT 멤버십)", "as_of": members.get("as_of_members"),
         "cadence": "리밸런스 시", "note": "생존편향 보정에 쓰는 시점별 구성"},
        # 로테이션 풀은 '오늘 10선을 고른 날'과 '풀을 마지막으로 채운 날'이 다르다.
        # 화면에 보이는 선정일은 매일 오늘이라 축이 아니고, 축은 풀의 generated다.
        {"key": "rotation", "label": "전략 탐색 풀", "as_of": (load("rotation_pool.json") or {}).get("generated"),
         "cadence": "수시", "note": "외부 출처 수집분 — 랩이 검증한 것이 아니다"},
        # 공시는 '수집한 날'이 아니라 '가장 최근에 접수된 제출일'이 기준이다. 회사가 안 내면
        # 우리가 매일 돌아도 축은 안 움직인다 — 그 사실을 감추지 않으려고 접수일을 쓴다.
        {"key": "filings", "label": "SEC 공시(8-K)", "as_of": (load("filings.json") or {}).get("as_of"),
         "cadence": "주 1회 수집", "note": "제출 접수일 기준 — 회사가 안 내면 이 날짜는 안 움직인다"},
        # 재무는 '분기 결산 기간말'이라 분기에 한 번 움직인다. 가격과 나란히 놓고 '뒤처졌다'고
        # 읽으면 안 되는 축이라, cadence에 그 성격을 적는다.
        {"key": "facts", "label": "SEC 재무(XBRL)", "as_of": (load("facts.json") or {}).get("as_of"),
         "cadence": "분기(실적 발표 시)", "note": "회사의 최근 보고 기간말 — 구조적으로 분기마다 한 번 움직인다"},
    ]
    axes = [a for a in axes if a.get("as_of")]
    for a in axes:
        a["lag_days"] = bdays(a["as_of"], primary)

    uni = sorted({a["as_of"] for a in axes})
    doc = {
        "note": "기준일 정본. build/asof_index.py가 만들고, 전 페이지 내비 칩·홈·sources.html이 "
                "이 파일만 읽는다. 페이지에 날짜를 직접 적지 말 것.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primary": primary,
        "unified": len(uni) == 1,
        "axes": axes,
        # 화면에 그대로 쓰는 한 줄 — '통일했다'는 주장을 데이터로만 하게 한다
        "summary": ("전 축 %s 통일" % primary) if len(uni) == 1 else
                   ("대표 %s · 축 %d개(%s)" % (primary, len(axes),
                    " · ".join("%s %s" % (a["label"], a["as_of"]) for a in axes if a["as_of"] != primary))),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("기준일 정본: primary %s · 축 %d개 · %s"
          % (primary, len(axes), "통일" if doc["unified"] else "분리"))
    for a in axes:
        print("  %-22s %s%s" % (a["label"], a["as_of"],
                                "" if not a["lag_days"] else "  (−%d영업일)" % a["lag_days"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
