#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/refresh_events.py — 캘린더 '이벤트·주목도' 정본 → data/events.json

── 왜 이 파일이 따로 있나 ──────────────────────────────────────────────
캘린더의 재료는 FRED(지표 발표일)와 Finnhub(실적일)에서 온다. 그런데 두 가지는
**어느 소스도 주지 않는다**.

  ① FOMC 일정 — FRED 는 '데이터 릴리스'만 준다. 통화정책 회의는 릴리스가 아니라서
     calendar.json 에 애초에 들어올 수 없다. 정작 회의에서 가장 먼저 보는 날인데도.
  ② 주목도(★) — 어느 발표가 더 중요한지는 데이터가 아니라 판단이다. FRED 는 말해주지 않는다.

이 둘을 각 화면이 알아서 채우게 두면 같은 목록이 여러 곳에 복제된다. 실제로 그렇게 됐다 —
주간회의 PDF · calendar.html · index.html 세 곳에 FOMC 날짜가 각각 하드코딩돼 있었다.
그래서 **여기 한 곳에만 적고 data/events.json 으로 내보내, 세 소비처가 그것만 읽게** 한다.

── 무엇이 정본이고 무엇이 판단인가 ────────────────────────────────────
  fomc  = 연준이 미리 공표한 사실(federalreserve.gov FOMC calendars). 2027 은 잠정.
  stars = 이 랩이 매긴 **주관적 주목도**이며 검증된 신호가 아니다. 화면에도 그렇게 적는다.

── 갱신 ────────────────────────────────────────────────────────────────
연준이 다음 해 일정을 공표하면 FOMC 에 한 해를 덧붙이고 이 스크립트를 다시 돌린다.
(연 8회·수년 치를 미리 공표하므로 자주 손댈 일은 없다. validate_site.py 가 남은 일정이
 6개월 미만이면 경고한다 — 조용히 바닥나는 것을 막으려는 것.)

  python build/refresh_events.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "events.json")

# ── ① FOMC 결정일(회의 2일차) — 연준 공표 사실 ──────────────────────────
#    sep=True 는 경제전망요약(점도표)이 함께 나오는 회의. 3·6·9·12월.
FOMC_2026 = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
             "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
FOMC_2027 = ["2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09",
             "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08"]   # 잠정
SEP_MONTHS = {3, 6, 9, 12}

# ── ② 주목도 ★1~4 — 주관적 눈금(검증 신호 아님) ─────────────────────────
#    FRED release id 기준. 이름은 화면 표기용으로 함께 내보낸다(세 화면 표기 통일).
RELEASES = {
    "50":  ("고용보고서",            4),
    "10":  ("소비자물가(CPI)",        4),
    "54":  ("개인소득·지출(PCE)",     3),
    "46":  ("생산자물가(PPI)",        3),
    "9":   ("소매판매",              3),
    "192": ("구인·이직(JOLTS)",       2),
    "91":  ("소비자심리(미시간대)",    2),
    "27":  ("주택착공·허가",          2),
    "199": ("주택가격(케이스실러)",    2),
    "13":  ("산업생산",              2),
    "180": ("주간 실업수당 청구",      1),
    "219": ("시카고연준 경기지수",     1),
    "21":  ("통화량 M2",             1),
    "456": ("삼의 법칙(침체 신호)",    1),
}
FOMC_NAME = "FOMC 금리결정"
FOMC_SEP_NAME = "FOMC 금리결정 · 점도표(SEP)"


# ── ③ 휴장 · 조기폐장 ────────────────────────────────────────────────────
# 🚨 왜 여기 있나. 캘린더는 월~금을 다 그리는데 **휴장일이 그냥 빈 칸**이었다. 빈 칸은
#   «그날 아무 일도 없었다» 와 «시장이 안 열렸다» 를 구별하지 못한다. FRED 도 Finnhub 도
#   휴장일을 주지 않으므로 FOMC 와 같은 자리에 둔다.
#
# 🚨 그리고 이것은 **규칙만으로는 못 만든다.** 18년치(2009~2026) 거래일 격자와 맞대 봤고,
#   규칙이 두 군데서 틀렸다:
#     ① 신정이 토요일이면 연방 규칙은 전날 금요일로 당기는데 **NYSE 는 안 당긴다** —
#        2010-12-31·2021-12-31 은 둘 다 정상 개장이었다. 해를 넘겨 당기지 않는다.
#     ② 규칙에 아예 없는 **임시휴장이 4일** 있었다(아래 ADHOC). 허리케인·국장은 예측 대상이
#        아니다. 그래서 **과거는 관측을, 미래는 규칙을** 쓰고 화면이 둘을 구별해 적는다.
#
# ⚠ 조기폐장(13:00 ET)은 거래량으로 확인했다(대형 5종 · 직전 30일 중앙값 대비):
#     2025-12-24 0.32 · 2024-12-24 0.39 · 2023-11-24 0.43 · 2025-11-28 0.54 ·
#     2024-07-03 0.57 · 2025-07-03 0.66  ← 전부 반휴
#     2023-12-22 0.64 · 2026-07-02 1.04                       ← 반휴 아님(규칙도 안 잡는다)
#   독립기념일이 토요일이라 금요일로 당겨 쉬는 해(2026)에는 **조기폐장이 없다.**

# 규칙으로 못 만드는 임시휴장 — 관측된 사실만 적는다. 새로 생기면 여기 한 줄 는다.
ADHOC = {
    "2012-10-29": "허리케인 샌디",
    "2012-10-30": "허리케인 샌디",
    "2018-12-05": "부시 전 대통령 국장",
    "2025-01-09": "카터 전 대통령 국장",
}
HOL_BACK_DAYS = 400          # 과거는 1년 남짓만 싣는다(캘린더가 그 이상 안 본다)
HOL_FWD_YEARS = 2


def _nth(y, m, wd, n):
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))


def _last(y, m, wd):
    nx = dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)
    return nx - dt.timedelta(days=(nx.weekday() - wd) % 7)


def _easter(y):
    """부활절(그레고리력) — 성금요일을 여기서 뺀다. NYSE 휴장 중 유일하게 계산이 필요하다."""
    a, b, c = y % 19, y // 100, y % 100
    d, e, f = b // 4, b % 4, (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)


def _obs(d, y):
    """주말에 걸린 휴일의 관측일. ⚠ **해를 넘겨 당기지 않는다**(위 ① 참조)."""
    if d.weekday() == 5:
        back = d - dt.timedelta(days=1)
        return None if back.year != y else back
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def _holidays(y):
    out = {}
    for d, n in ((_obs(dt.date(y, 1, 1), y), "신정"),
                 (_nth(y, 1, 0, 3), "마틴 루터 킹의 날"),
                 (_nth(y, 2, 0, 3), "워싱턴 탄생일"),
                 (_easter(y) - dt.timedelta(days=2), "성금요일"),
                 (_last(y, 5, 0), "메모리얼 데이"),
                 (_obs(dt.date(y, 6, 19), y) if y >= 2022 else None, "준틴스"),
                 (_obs(dt.date(y, 7, 4), y), "독립기념일"),
                 (_nth(y, 9, 0, 1), "노동절"),
                 (_nth(y, 11, 3, 4), "추수감사절"),
                 (_obs(dt.date(y, 12, 25), y), "성탄절")):
        if d is not None:
            out[d.isoformat()] = n
    return out


def _half_days(y):
    """13:00 ET 조기폐장. 셋 다 «그 앞날이 거래일일 때만» 생긴다."""
    out = {}
    j4 = dt.date(y, 7, 4)
    if j4.weekday() < 5:                       # 7/4 가 평일일 때만 7/3 이 반휴
        j3 = dt.date(y, 7, 3)
        if j3.weekday() < 5:
            out[j3.isoformat()] = "독립기념일 전날"
    out[(_nth(y, 11, 3, 4) + dt.timedelta(days=1)).isoformat()] = "추수감사절 다음날"
    d24 = dt.date(y, 12, 24)
    if d24.weekday() < 5 and dt.date(y, 12, 25).weekday() < 5:
        out[d24.isoformat()] = "성탄절 전날"
    return out


def _grid():
    """거래일 격자 — 과거의 «관측» 정본. 없으면 규칙만으로 만들고 그 사실을 적는다."""
    try:
        p = os.path.join(ROOT, "data", "stocks.json")
        return set(json.load(io.open(p, encoding="utf-8")).get("pxd_dates") or [])
    except Exception:
        return set()


def market_days():
    """휴장·조기폐장 목록과 **규칙 대 관측 감사 결과**를 함께 돌려준다.

    🚨 감사 결과를 산출물에 싣는 이유: 이 규칙은 이미 두 번 틀렸다(머리주석). 다음에 또
      틀리면 «조용히 하루가 사라지는» 것이 아니라 파일에 숫자로 남아야 한다.
    """
    G = _grid()
    today = dt.date.today()
    lo = (today - dt.timedelta(days=HOL_BACK_DAYS)).isoformat()
    hi = dt.date(today.year + HOL_FWD_YEARS, 12, 31).isoformat()
    gmax = max(G) if G else ""

    closed, half, wrong = [], [], []
    for y in range(int(lo[:4]), int(hi[:4]) + 1):
        for d, n in sorted(_holidays(y).items()):
            if not (lo <= d <= hi):
                continue
            if d in G:                       # 규칙은 닫는다는데 실제로 열었다
                wrong.append({"d": d, "n": n})
                continue
            closed.append({"d": d, "n": n, "src": "관측" if d <= gmax else "규칙"})
        for d, n in sorted(_half_days(y).items()):
            if lo <= d <= hi and (d in G or d > gmax):
                half.append({"d": d, "n": n + " · 13:00 조기폐장",
                             "src": "관측" if d <= gmax else "규칙"})
    # 규칙에 없는 임시휴장 — 관측 구간에서 직접 줍는다(ADHOC 에 이름이 있으면 붙인다)
    adhoc = []
    if G:
        x = dt.date.fromisoformat(max(lo, min(G)))
        end = dt.date.fromisoformat(min(hi, gmax))
        known = set()
        for y in range(x.year, end.year + 1):
            known |= set(_holidays(y))
        while x <= end:
            s = x.isoformat()
            if x.weekday() < 5 and s not in G and s not in known:
                adhoc.append({"d": s, "n": ADHOC.get(s, "임시휴장(사유 미기록)"), "src": "관측"})
            x += dt.timedelta(days=1)
    closed = sorted(closed + adhoc, key=lambda r: r["d"])
    return {
        "note": ("미국 증시 휴장·조기폐장. **과거는 거래일 격자에서 관측**하고 미래는 NYSE "
                 "규칙으로 계산한다(src 가 그 구별이다). 규칙만으로는 못 만든다 — 허리케인·"
                 "국장 같은 임시휴장이 2009년 이후 4일 있었다."),
        "closed": closed, "half": half,
        "audit": {"n_grid": len(G), "grid_max": gmax,
                  "rule_wrong": wrong,
                  "adhoc_in_window": [r["d"] for r in adhoc],
                  "why": ("rule_wrong 가 비어 있지 않으면 규칙이 틀린 것이다 — 실제로 두 번 "
                          "그랬다(신정이 토요일인 해에 전년 12/31 을 당겨 쉰다고 잘못 적었다). "
                          "고치고 이 목록이 다시 비는지 확인할 것.")},
    }


def build() -> dict:
    fomc = []
    for d in FOMC_2026 + FOMC_2027:
        y, m, _ = (int(x) for x in d.split("-"))
        sep = m in SEP_MONTHS
        fomc.append({"d": d, "sep": sep, "name": FOMC_SEP_NAME if sep else FOMC_NAME,
                     "star": 4, "tentative": y >= 2027})
    fomc.sort(key=lambda r: r["d"])

    by_rid = {rid: s for rid, (_, s) in RELEASES.items()}
    name_kr = {rid: n for rid, (n, _) in RELEASES.items()}
    # 이름 기준 조회용(홈은 릴리스 id 없이 한글 이름만 갖는다). 공백 표기가 갈릴 수 있어
    # 소비처는 공백을 지우고 맞춘다 — 여기서는 정본 표기 그대로 싣는다.
    by_name = {n: s for n, s in RELEASES.values()}
    by_name[FOMC_NAME] = 4
    by_name[FOMC_SEP_NAME] = 4

    return {
        "note": ("캘린더에 얹는 이벤트·주목도. FOMC 일정은 FRED가 주지 않아 연준 공표 일정을 "
                 "여기 적는다(2027은 잠정). ★는 이 랩이 매긴 주관적 주목도이며 검증된 신호가 아니다."),
        "source": "FOMC=federalreserve.gov FOMC calendars · ★=여두 전략 랩 자체 판단",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fomc": fomc,
        "stars": {"by_rid": by_rid, "by_name": by_name},
        "macro_kr": name_kr,
        # 휴장·조기폐장 — FRED·Finnhub 어느 쪽도 안 준다. 위 market_days() 주석 참조.
        "market": market_days(),
    }


def main() -> int:
    j = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write("\n")
    last = j["fomc"][-1]["d"]
    mk = j["market"]
    print("data/events.json 생성 — FOMC %d건(마지막 %s) · 주목도 %d종"
          % (len(j["fomc"]), last, len(j["stars"]["by_rid"])))
    print("  휴장 %d일(관측 %d · 규칙 %d) · 조기폐장 %d일"
          % (len(mk["closed"]),
             sum(1 for r in mk["closed"] if r["src"] == "관측"),
             sum(1 for r in mk["closed"] if r["src"] == "규칙"),
             len(mk["half"])))
    if mk["audit"]["adhoc_in_window"]:
        print("  ⚠ 규칙에 없는 임시휴장 %s — 사유는 ADHOC 에 적을 것"
              % ", ".join(mk["audit"]["adhoc_in_window"]))
    if mk["audit"]["rule_wrong"]:
        print("  🚨 규칙이 닫는다고 했으나 실제로 열린 날 %d일: %s — 규칙을 고칠 것"
              % (len(mk["audit"]["rule_wrong"]),
                 ", ".join(r["d"] for r in mk["audit"]["rule_wrong"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
