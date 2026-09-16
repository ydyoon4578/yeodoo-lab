#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC 주식수가 **없거나 비어 있는** 종목을 yfinance 로 메운다 → data/shares_yf.json

**왜 이 파일이 필요한가.** SEC XBRL 로 주식수를 못 만드는 회사가 남는다. 2026-08-04 실측
6종(2026-09-16 현재 7종): ARES · BKR · BRK.B · ERIE · HONA · STZ · V. 사유는 다중클래스다 —
회사가 클래스별로 따로 보고하니 '이 회사의 주식수'라는 단일 태그가 없다(V 는 us-gaap 에
우선주 수만 있고, BRK.B 는 A주 환산 가중평균만 있어 B주 주가와 곱할 수 없다).
그 결과 이 종목들은 시가총액을 만들 수 없어 **모든 펀더멘털 규칙의 후보에서 통째로 빠졌다.**

🚨 2026-09-16 — **대상을 넓혔다.** '아예 없음'만 메우면 더 큰 구멍이 남는다. 실측(data/fx 전수):
  ① 시작이 늦다(2016 이후) 67종 — 알파벳은 희석주식수 태그가 2023 년부터뿐이라 **9년 동안
     시총이 없었고**, BLK(2023~)·XOM(2025~)·DIS·AVB 도 같은 이유로 지수 계산에서 빠져 있었다.
  ② 중간에 400일 넘는 구멍 13종 — MO 2015~2019 · PANW 2013~2021 · SPG 2014~2020.
     asof_fund 에는 낡기 제한이 없어 몇 해 전 값을 현재값처럼 물고 있었다(MO 2019년에 2014년 값).
  ③ 끝이 400일 넘게 멈춤 1종(MCD).
  ④ 분할로 설명 안 되는 **단절**이 있는 종목(tech_backtest.SPLIT_BREAKS) — 그 자리에서
     '아직 소급 안 된 값인지'를 가르는 **중재 증거**로 쓴다(tech_backtest._rebase 참조).
  합쳐서 144종(겹침 제외). 효과: S&P 500 편입 종목 중 주식수가 있는 비율 2014년 90% → 100%.

yfinance 의 get_shares_full 은 **전 클래스 합산**이다(refresh_stocks.fetch_shares 의 주석에
실측 근거가 있다 — GOOGL 12,230M · BRK.B 2,157M 로 직전 빌드 역산값과 10/10 일치).

⚠ 이 자료의 한계를 그대로 적는다. 대신 쓰는 것이지 더 나은 것이 아니다.
  · 2015-10 부터만 있다(SEC 계열은 2008~). 그래서 **SEC 가 있으면 SEC 를 쓴다** — 쓰는 쪽이
    빈 곳만 메우고, 정의 차이로 수준이 5% 넘게 벌어지면 SEC 쪽에 맞춰 넣는다
    (tech_backtest.merge_shares_yf — 실측 SPG 1.145배 · PANW 0.927배 · CVNA 2.21배).
  · 정의가 다르다 — 기말 발행주식수(전 클래스)이지 가중평균 희석주식수가 아니다.
  · 분할조정이 안 돼 있다. 분할일에 계단이 그대로 있다. 여기서는 손대지 않고 날짜별
    원값을 싣는다 — 되맞추기는 쓰는 쪽(tech_backtest)이 splits.json 으로 한다.
    수집기가 값을 고쳐 저장하면 원본이 사라져 나중에 검산할 수 없다.
  · **0.2% 안쪽 변화는 싣지 않는다.** 원계열은 날마다 한 주씩 움직여 파일이 900KB 를 넘는데,
    이 파일은 매일 갱신·커밋된다. 수준을 0.2% 안에서 지키면서 행을 30% 줄인다(값은 안 고친다).

대상은 손으로 적지 않고 **data/fx 와 tech_backtest 의 처리 결과에서 정한다.** 손으로 적으면
다음에 SEC 가 태그를 바꿔 다른 회사가 비어도 아무도 모른다.

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
LATE_START = "2016-01-01"   # SEC 계열이 이보다 늦게 시작하면 앞이 비어 있다
GAP_DAYS = 400              # 중간 구멍·끝 멈춤 판정(분기 공시 주기로 한 해를 넘긴 자리)
GAP_AFTER = "2015-10-01"    # 야후가 덮는 구간의 구멍만 본다 — 그 앞은 메울 자료가 아예 없다
THIN = 0.002                # 0.2% 안쪽 변화는 싣지 않는다(위 주석)
# '아예 없음'이 이보다 많으면 SEC 수집 쪽이 망가진 것이다 — 조용히 yfinance 로 갈아타면 안 된다.
MAX_NONE = 40
MAX_TARGETS = 250           # 넓힌 대상 전체의 상한(2026-09-16 실측 144종)


def _d(s):
    return dt.date.fromisoformat(s[:10])


def _ok(x):
    return isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float)) and x[1] > 0


def targets():
    """티커 → 사유. 앞의 넷은 data/fx 를 훑어서, 마지막 하나는 tech_backtest 의 처리 결과에서 정한다.

    계열을 잇는 순서는 tech_backtest.load_fund 와 같다 — sh(분기/시점) → sh 연간 → 그 앞을 sho 로.
    """
    why, today = {}, dt.date.today()
    for fn in sorted(os.listdir(DIR_FX)):
        if not fn.endswith(".json"):
            continue
        try:
            j = json.load(io.open(os.path.join(DIR_FX, fn), encoding="utf-8"))
        except Exception:
            continue
        tg = j.get("tags") or {}
        sh, sho = tg.get("sh") or {}, tg.get("sho") or {}
        prim = [x[0] for x in (sh.get("i") or sh.get("q") or sh.get("a") or []) if _ok(x)]
        first = min(prim) if prim else None
        alt = [x[0] for x in (sho.get("i") or sho.get("q") or []) if _ok(x) and (first is None or x[0] < first)]
        ds = sorted(set(prim) | set(alt))
        t = j.get("t") or fn[:-5]
        if not ds:
            why[t] = "SEC 없음"
        elif ds[0] > LATE_START:
            why[t] = "시작 " + ds[0]
        elif any(ds[i + 1] >= GAP_AFTER and (_d(ds[i + 1]) - _d(ds[i])).days > GAP_DAYS
                 for i in range(len(ds) - 1)):
            why[t] = "중간 구멍"
        elif (today - _d(ds[-1])).days > GAP_DAYS:
            why[t] = "끝 " + ds[-1]
    # 단절 종목 — 되맞춤 후보를 고르는 증거로 쓴다. load_fund 는 data/fx 만 훑으므로 대상 범위가 같다.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tech_backtest as TB
    TB.load_fund()
    for t, br in TB.SPLIT_BREAKS.items():
        why.setdefault(t, "단절 " + br[0])
    return why


def series_of(s):
    """yfinance 계열 → [[날짜, 백만주]]. 같은 날 여러 값이면 마지막 것, 0.2% 안쪽 변화는 버린다."""
    ser, prev, last = [], None, None
    for idx, v in s.items():
        try:
            val = float(v)
        except (TypeError, ValueError):
            continue
        if val <= 0:
            continue
        d, mv = str(idx.date()), round(val / 1e6, 4)
        last = [d, mv]
        if ser and ser[-1][0] == d:
            ser[-1] = last
            prev = mv
            continue
        if prev is not None and abs(mv / prev - 1) <= THIN:
            continue
        ser.append(last)
        prev = mv
    if ser and last and ser[-1][0] != last[0]:
        ser.append(last)            # 마지막 관측은 값이 거의 안 변했어도 남긴다(최신 시점 표시)
    return ser


def main() -> int:
    import yfinance as yf
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from refresh_stocks import _yf_sym

    ts = targets()
    kinds = {}
    for w in ts.values():
        k = w.split(" ")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print("야후로 메울 종목 %d종 %s" % (len(ts), kinds))
    print("  " + ", ".join("%s(%s)" % (t, ts[t]) for t in sorted(ts)))
    if not ts:
        print("대상 없음 — 파일을 건드리지 않는다")
        return 0
    n_none = sum(1 for w in ts.values() if w == "SEC 없음")
    if n_none > MAX_NONE:
        print("❌ SEC 주식수가 아예 없는 종목이 %d종(>%d) — SEC 수집이 깨졌을 가능성이 크다. 중단한다."
              % (n_none, MAX_NONE))
        return 1
    if len(ts) > MAX_TARGETS:
        print("❌ 대상이 %d종(>%d) — 자료나 판정 규칙이 흔들렸다. 중단한다." % (len(ts), MAX_TARGETS))
        return 1

    rows, miss = {}, []
    for t in sorted(ts):
        try:
            s = yf.Ticker(_yf_sym(t)).get_shares_full(start=START)
        except Exception:
            s = None
        if s is None or not len(s):
            miss.append(t)
            continue
        if hasattr(s, "columns"):
            s = s[s.columns[0]]
        ser = series_of(s)
        if ser:
            rows[t] = ser
        else:
            miss.append(t)

    if not rows:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1
    doc = {
        "note": "SEC XBRL 주식수가 없거나(다중클래스) 비어 있는 종목(시작이 늦음·중간 구멍·끝 멈춤·"
                "분할로 설명 안 되는 단절)을 yfinance get_shares_full 로 받은 것. 단위는 백만주, "
                "**전 클래스 합산 · 기말 발행주식수**이며 분할조정은 하지 않았다"
                "(쓰는 쪽이 splits.json 으로 되맞춘다). 0.2% 안쪽 변화는 싣지 않는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start": START,
        "n_co": len(rows),
        "why": {t: ts[t] for t in sorted(rows)},
        "co": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    print("보완 주식수: %d사 · %d행 · %.0fKB"
          % (len(rows), sum(len(v) for v in rows.values()), os.path.getsize(OUT) / 1024))
    for t in sorted(rows):
        v = rows[t]
        print("  %-7s %3d행 %s ~ %s · %.0fM → %.0fM  [%s]"
              % (t, len(v), v[0][0], v[-1][0], v[0][1], v[-1][1], ts[t]))
    if miss:
        print("⚠ yfinance 도 못 준 종목 %d: %s" % (len(miss), ", ".join(miss)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
