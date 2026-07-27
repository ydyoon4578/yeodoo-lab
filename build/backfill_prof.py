#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/sd/<티커>.json 에 회사 소개(prof)를 채운다 — 1회성 백필.

왜 있나: prof 수집은 refresh_stocks.py 의 .info 응답에서 키만 더 꺼내는 것이라
추가 API 호출이 0이고, 그 잡이 돌면 sd/ 파일이 통째로 다시 쓰이며 prof 도 함께
들어간다. 하지만 그 잡은 가격 패널 10년치를 다시 받는 무거운 실행이라, 소개
문장 하나 때문에 돌리기엔 과하다. 이 스크립트는 .info 만 받아 prof 만 병합한다.

번역하지 않는다 — 정보원(yfinance longBusinessSummary)이 쓴 영문 원문 그대로다.
요약도 하지 않는다. 둘 다 원문에 없는 뜻을 만들어 넣는 일이고, 어긋나도 알 방법이 없다.
"""
import io, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SD = os.path.join(ROOT, "data", "sd")

sys.path.insert(0, HERE)
from refresh_stocks import _yf_sym          # 클래스주 티커 변환(BRK.B → BRK-B)을 다시 구현하지 않는다

KEYS = (("sum", "longBusinessSummary"), ("ind", "industry"), ("web", "website"),
        ("emp", "fullTimeEmployees"), ("cty", "country"))


def fetch(t, retries=2):
    for a in range(retries):
        try:
            info = yf.Ticker(_yf_sym(t)).info or {}
            p = {k: info.get(src) for k, src in KEYS}
            p = {k: v for k, v in p.items() if v not in (None, "")}
            if p:
                return t, p
        except Exception:
            pass
        if a < retries - 1:
            time.sleep(0.6 * (a + 1))
    return t, None


def main():
    tickers = [s["t"] for s in json.load(io.open(os.path.join(ROOT, "data", "stocks.json"),
                                                encoding="utf-8"))["stocks"]]
    print(f"대상 {len(tickers)}종목 · yfinance .info…")
    got = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for t, p in ex.map(fetch, tickers):
            if p:
                got[t] = p
    print(f"수집 {len(got)}/{len(tickers)}종목 · 소개문 있는 종목 {sum(1 for p in got.values() if p.get('sum'))}")
    # 커버가 절반도 안 되면 쓰지 않는다 — 부분 응답을 병합하면 '왜 이 종목만 없나'가 남는다
    if len(got) < len(tickers) * 0.5:
        raise SystemExit("수집 커버 50% 미만 — 병합 중단(기존 파일 유지)")
    n = 0
    for t, p in got.items():
        fn = os.path.join(SD, t + ".json")
        if not os.path.exists(fn):
            continue
        d = json.load(io.open(fn, encoding="utf-8"))
        d["prof"] = p
        json.dump(d, io.open(fn, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        n += 1
    print(f"→ data/sd/ {n}개 파일에 prof 병합")


if __name__ == "__main__":
    main()
