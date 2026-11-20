#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""모니터링 전략 장부 — 랩 전략 12종을 실제로 들고 간 것처럼 매달 적는다.

왜 따로 두나
- 랩의 성적(tech_strategies.json · pit_strategies.json)은 **지난 자료로 다시 돌린 값**이다.
  이 장부는 그 규칙이 **오늘 이후** 고른 종목을 그대로 들고 간 기록이다. 판정이 아니다 —
  2026-09-27 전방 판정 취소(FORWARD-STOP)는 그대로이고, 여기서는 «통과/기각» 을 내리지 않는다.
  (2026-10-26 사용자 결정: KPI «모니터링 전략 10개 이상 · BM 대비 outperform» 증빙용 장부를 켠다.)

규칙
- 보유 = 랩이 매번 다시 굽는 data/tech_strategies.json 의 holdings(동일가중).
- 새 다리 = 그 전략의 holdings.as_of 가 바뀌었고, 이번 달에 아직 다리를 안 열었을 때.
  → 월말 규칙은 월 1회, 분기·반기 규칙은 자기 주기대로, 매일 바뀌는 이벤트 규칙도 월 1회.
- 진입가 = 다리를 연 날의 종가(장부를 쓴 시점에 이미 나온 가장 최근 종가). 소급하지 않는다.
- 가격 = yfinance 종가(배당 뺀 가격수익, PR) — 대조군 S&P 500(SPY 종가)도 PR 이라 같은 잣대다.
- 비용 = 다리 교체 때 바뀐 비중 × 5bp(랩 기본값).
- 장부는 덧붙이기만 한다. 이미 쓴 다리는 고치지 않는다(--check 가 지문으로 막는다).

사용:
    python build/kpi_monitor.py            # 다리 열기(필요하면) + 성적 다시 계산
    python build/kpi_monitor.py --check    # 이미 쓴 다리가 바뀌지 않았는지만 검사
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "kpi_monitor.json")
TECH = os.path.join(DATA, "tech_strategies.json")
BENCH = "SPY"
COST_BP = 5.0

# 명단 — 경제적 근거가 서로 다른 축에서 고른다(같은 베팅 여러 번 금지).
# 축: KPI 문구(기업 이벤트 · 지수 변동 · 수급 · 팩터 · 섹터 군집)를 따랐다.
STRATS = [
    ("x-pead-sue",     "기업 이벤트", "실적 서프라이즈 드리프트"),
    ("x-divgrow",      "기업 이벤트", "배당 증액률 상위 10"),
    ("x-cgate-mom",    "지수 변동",   "지수 집중도 게이트"),
    ("x-guruacc",      "수급",        "거장(13F) 순매집 상위 10"),
    ("x-residind-n52", "섹터 군집",   "산업잔차 모멘텀 상위 52"),
    ("x-bmrot",        "섹터 군집",   "B/M 금리 국면 로테이션"),
    ("x-residmom",     "팩터",        "잔차 모멘텀 상위 10"),
    ("x-dalpha",       "팩터",        "알파 개선 상위 10"),
    ("x-sp",           "팩터",        "저PSR(매출수익률) 상위 10"),
    ("x-fcfy",         "팩터",        "잉여현금흐름 수익률 상위 10"),
    ("x-poacc-n52",    "팩터",        "영업발생액 회피 최저 52"),
    ("x-cdisc",        "팩터",        "비용규율 상위 10"),
]


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _leg_fp(leg: dict) -> str:
    key = json.dumps({k: leg[k] for k in ("sid", "open", "src_as_of", "tickers", "px0")},
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def check(book: dict) -> int:
    bad = [l for l in book.get("legs", []) if l.get("fp") != _leg_fp(l)]
    for l in bad:
        print(f"::error::다리가 쓴 뒤에 바뀌었다 — {l['sid']} {l['open']}")
    print(f"다리 {len(book.get('legs', []))}개 · 바뀐 것 {len(bad)}개")
    return 1 if bad else 0


def fetch_close(tickers, start):
    import pandas as pd
    import yfinance as yf
    yt = sorted({t.replace(".", "-") for t in tickers})
    df = yf.download(yt, start=start, auto_adjust=False, progress=False, threads=True)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(yt[0])
    df.columns = [c.replace("-", ".") for c in df.columns]
    df.index = [d.strftime("%Y-%m-%d") for d in df.index]
    return df.sort_index()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    book = _load(OUT, None) or {"legs": []}
    if a.check:
        return check(book)
    if check(book):
        return 1

    tech = {s["sid"]: s for s in _load(TECH)["strategies"]}
    missing = [sid for sid, _, _ in STRATS if sid not in tech]
    if missing:
        print(f"::error::랩에 없는 전략 — {missing}")
        return 1

    legs = book["legs"]
    # 🆕 2026-11-20 — 같은 자료를 두 번 받지 않는다. 이 잡은 종목 잡이 끝날 때마다(백업 슬롯 포함) 뜬다.
    #   장부 기준일이 이미 저장소 가격 기준일과 같고 새로 열 다리도 없으면 yfinance 를 부르지 않고 끝낸다.
    try:
        repo_asof = _load(os.path.join(DATA, "stocks.json"))["pxd_dates"][-1]   # 이 잡을 띄운 종목 잡이 방금 쓴 가격 기준일
    except Exception:
        repo_asof = None
    if repo_asof and book.get("as_of") and book["as_of"] >= repo_asof:
        need = []
        for sid, _, _ in STRATS:
            mine = [l for l in legs if l["sid"] == sid]
            prev = mine[-1] if mine else None
            if not (prev and (prev["src_as_of"] == tech[sid]["holdings"]["as_of"] or prev["open"][:7] == book["as_of"][:7])):
                need.append(sid)
        if not need:
            print(f"장부 기준일 {book['as_of']} = 저장소 가격 기준일 {repo_asof}, 새 다리 없음 — 다시 받지 않음")
            return 0
    first = min([l["open"] for l in legs], default=None)
    want = {BENCH}
    for sid, _, _ in STRATS:
        want |= set(tech[sid]["holdings"]["tickers"])
    for l in legs:
        want |= set(l["tickers"])
    start = (dt.date.fromisoformat(first) - dt.timedelta(days=7)).isoformat() if first \
        else (dt.date.today() - dt.timedelta(days=14)).isoformat()
    px = fetch_close(want, start)
    last_day = px[BENCH].dropna().index[-1]
    month = last_day[:7]

    # ── 다리 열기 ──
    opened = []
    for sid, axis, ko in STRATS:
        h = tech[sid]["holdings"]
        mine = [l for l in legs if l["sid"] == sid]
        prev = mine[-1] if mine else None
        if prev and (prev["src_as_of"] == h["as_of"] or prev["open"][:7] == month):
            continue
        tick = [t for t in h["tickers"] if t in px.columns and px[t].notna().any()
                and not px[t].loc[:last_day].dropna().empty]
        drop = sorted(set(h["tickers"]) - set(tick))
        p0 = {t: round(float(px[t].loc[:last_day].dropna().iloc[-1]), 4) for t in tick}
        leg = {"sid": sid, "open": last_day, "src_as_of": h["as_of"], "tickers": sorted(p0),
               "px0": p0, "no_price": drop}
        leg["fp"] = _leg_fp(leg)
        legs.append(leg)
        opened.append(sid)

    # ── 성적 ──
    days = [d for d in px.index if d >= min(l["open"] for l in legs)]
    b = px[BENCH].ffill()
    rows = []
    for sid, axis, ko in STRATS:
        mine = sorted([l for l in legs if l["sid"] == sid], key=lambda l: l["open"])
        t0 = mine[0]["open"]
        nav, w_prev, series = 1.0, {}, []
        for i, l in enumerate(mine):
            end = mine[i + 1]["open"] if i + 1 < len(mine) else last_day
            n = len(l["tickers"])
            w = {t: 1.0 / n for t in l["tickers"]}
            turn = sum(abs(w.get(t, 0) - w_prev.get(t, 0)) for t in set(w) | set(w_prev))
            nav *= 1 - turn * COST_BP / 1e4
            seg = [d for d in days if l["open"] <= d <= end]
            for d in seg:
                v = 0.0
                for t in l["tickers"]:
                    s = px[t].loc[:d].dropna()
                    v += w[t] * (float(s.iloc[-1]) / l["px0"][t] if len(s) else 1.0)
                if d == l["open"] and series:
                    continue
                series.append((d, nav * v))
            nav = series[-1][1]
            # 다리 끝 비중(가격 따라 흘러간 것)이 다음 교체의 출발점
            tot = sum(w[t] * (float(px[t].loc[:end].dropna().iloc[-1]) / l["px0"][t]) for t in l["tickers"])
            w_prev = {t: w[t] * float(px[t].loc[:end].dropna().iloc[-1]) / l["px0"][t] / tot for t in l["tickers"]}
        b0 = float(b.loc[t0])
        bser = [(d, float(b.loc[d]) / b0) for d, _ in series]
        r, rb = series[-1][1] - 1, bser[-1][1] - 1
        rows.append({
            "sid": sid, "name": tech[sid]["name"], "ko": ko, "axis": axis, "start": t0,
            "n_legs": len(mine), "n_hold": len(mine[-1]["tickers"]),
            "ret": round(r * 100, 2), "bench_ret": round(rb * 100, 2),
            "excess": round((r - rb) * 100, 2), "beat": r > rb,
            "bt": {"excess_cagr": tech[sid].get("excess_cagr"), "t": tech[sid].get("t")},
            "series": {"d": [d for d, _ in series], "s": [round(v, 5) for _, v in series],
                       "b": [round(v, 5) for _, v in bser]},
            "hold": mine[-1]["tickers"],
        })

    book.update({
        "note": ("모니터링 장부 — 랩 전략 12종이 고른 종목을 장부를 연 날부터 그대로 들고 간 기록. "
                 "판정이 아니다(통과·기각 없음). 가격수익(PR) · 대조군 S&P 500(SPY 종가) · 교체 비용 5bp. "
                 "만든 곳 build/kpi_monitor.py."),
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": last_day, "bench": "S&P 500 (SPY 종가 · PR)",
        "n": len(rows), "n_beat": sum(r["beat"] for r in rows),
        "rows": rows, "legs": legs,
    })
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(book, f, ensure_ascii=False, separators=(",", ":"))
    print(f"기준일 {last_day} · 새 다리 {len(opened)}개 {opened} · 대조군 이긴 전략 {book['n_beat']}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
