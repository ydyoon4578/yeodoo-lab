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
    }


def main() -> int:
    j = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write("\n")
    last = j["fomc"][-1]["d"]
    print("data/events.json 생성 — FOMC %d건(마지막 %s) · 주목도 %d종"
          % (len(j["fomc"]), last, len(j["stars"]["by_rid"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
