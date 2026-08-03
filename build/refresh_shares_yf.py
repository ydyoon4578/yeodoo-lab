#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC 에 주식수가 없는 종목만 yfinance 로 메운다 → data/shares_yf.json

**왜 이 파일이 필요한가.** SEC XBRL 로 주식수를 못 만드는 회사가 남는다. 2026-08-04 실측
6종: ARES · BKR · BRK.B · ERIE · STZ · V. 사유는 다중클래스다 — 회사가 클래스별로 따로
보고하니 '이 회사의 주식수'라는 단일 태그가 없다(V 는 us-gaap 에 우선주 수만 있고,
BRK.B 는 A주 환산 가중평균만 있어 B주 주가와 곱할 수 없다).
그 결과 이 6종은 시가총액을 만들 수 없어 **모든 펀더멘털 규칙의 후보에서 통째로 빠졌다.**

yfinance 의 get_shares_full 은 **전 클래스 합산**이다(refresh_stocks.fetch_shares 의 주석에
실측 근거가 있다 — GOOGL 12,230M · BRK.B 2,157M 로 직전 빌드 역산값과 10/10 일치).

⚠ 이 자료의 한계를 그대로 적는다. 대신 쓰는 것이지 더 나은 것이 아니다.
  · 2015-10 부터만 있다(SEC 계열은 2008~). 그래서 **SEC 가 있으면 SEC 를 쓴다.**
  · 정의가 다르다 — 기말 발행주식수(전 클래스)이지 가중평균 희석주식수가 아니다.
  · 분할조정이 안 돼 있다. 분할일에 계단이 그대로 있다. 여기서는 손대지 않고 날짜별
    원값을 싣는다 — 되맞추기는 쓰는 쪽(tech_backtest)이 splits.json 으로 한다.
    수집기가 값을 고쳐 저장하면 원본이 사라져 나중에 검산할 수 없다.

대상은 손으로 적지 않고 **data/fx 를 훑어 정한다.** 손으로 적으면 다음에 SEC 가 태그를
바꿔 다른 회사가 비어도 아무도 모른다.

사용: python3 build/refresh_shares_yf.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_FX = os.path.join(DATA, "fx")
OUT = os.path.join(DATA, "shares_yf.json")

START = "2015-01-01"
# 대상이 이보다 많으면 SEC 수집 쪽이 망가진 것이다 — 조용히 yfinance 로 갈아타면 안 된다.
MAX_TARGETS = 40


def targets():
    """SEC 주식수가 없는 종목. tech_backtest.load_fund 의 순서(sh → sh 연간 → sho)와 같다."""
    out = []
    for fn in sorted(os.listdir(DIR_FX)):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(io.open(os.path.join(DIR_FX, fn), encoding="utf-8"))
        except Exception:
            continue
        tg = d.get("tags") or {}
        sh, sho = tg.get("sh") or {}, tg.get("sho") or {}
        if sh.get("i") or sh.get("q") or sh.get("a") or sho.get("i") or sho.get("q"):
            continue
        out.append(d.get("t") or fn[:-5])
    return out


def main() -> int:
    import yfinance as yf
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from refresh_stocks import _yf_sym

    ts = targets()
    print("SEC 주식수가 없는 종목 %d종: %s" % (len(ts), ", ".join(ts)))
    if not ts:
        print("대상 없음 — 파일을 건드리지 않는다")
        return 0
    if len(ts) > MAX_TARGETS:
        print("❌ 대상이 %d종(>%d) — SEC 수집이 깨졌을 가능성이 크다. 중단한다."
              % (len(ts), MAX_TARGETS))
        return 1

    rows, miss = {}, []
    for t in ts:
        try:
            s = yf.Ticker(_yf_sym(t)).get_shares_full(start=START)
        except Exception:
            s = None
        if s is None or not len(s):
            miss.append(t)
            continue
        if hasattr(s, "columns"):
            s = s[s.columns[0]]
        # 같은 날 여러 값이 오면 마지막 것만. 그리고 **값이 바뀐 날만** 남긴다 —
        # 원계열은 날마다 같은 값을 되풀이해 파일이 10배가 된다(실측 BRK.B 1,527행).
        ser, prev = [], None
        for idx, v in s.items():
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue
            if val <= 0:
                continue
            d = str(idx.date())
            if ser and ser[-1][0] == d:
                ser[-1] = [d, round(val / 1e6, 4)]
                continue
            mv = round(val / 1e6, 4)
            if prev is not None and mv == prev:
                continue
            ser.append([d, mv])
            prev = mv
        if ser:
            rows[t] = ser
        else:
            miss.append(t)

    if not rows:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1
    doc = {
        "note": "SEC XBRL 로 주식수를 만들 수 없는 종목만 yfinance get_shares_full 로 받은 것. "
                "단위는 백만주, **전 클래스 합산 · 기말 발행주식수**이며 분할조정은 하지 않았다"
                "(쓰는 쪽이 splits.json 으로 되맞춘다). 값이 바뀐 날만 싣는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start": START,
        "n_co": len(rows),
        "co": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    print("보완 주식수: %d사 · %d행 · %.0fKB"
          % (len(rows), sum(len(v) for v in rows.values()), os.path.getsize(OUT) / 1024))
    for t in sorted(rows):
        v = rows[t]
        print("  %-7s %3d행 %s ~ %s · %.0fM → %.0fM"
              % (t, len(v), v[0][0], v[-1][0], v[0][1], v[-1][1]))
    if miss:
        print("⚠ yfinance 도 못 준 종목 %d: %s" % (len(miss), ", ".join(miss)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
