#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시점정합 지수 멤버십 로더 — data/index_history.json(위키 과거 리비전) 하나만 읽는다.

무엇을·왜.
  PIT(시점정합) 검정은 '그때 실제로 지수에 있던 명단'이 있어야 성립한다. 그 명단이
  오래 **사내 DB(public.index_constituents)** 에서만 왔고, 그래서 data/pit_members.json 이
  gitignore 였다 — 러너가 스스로 만들 수 없어 생존편향 측정이 PC 한 대에 묶여 있었다.

  build/refresh_index_history.py 가 위키백과 지수 목록 문서의 **과거 리비전**으로 같은
  명단을 만든다(CC BY-SA 라 재배포 가능). 그 산출물 data/index_history.json 은 저장소에
  커밋되므로 러너도 읽을 수 있다. 이 모듈은 그것을 예전 pit_members.json 과 같은 모양
  ({YYYY-MM: [티커…]}) 으로 바꿔 주는 얇은 층이다.

정확도 — 사내DB 와 실측 대조는 refresh_index_history.py 머리말에 있다(2026-08-02).
  '2020-09 멤버 후 편출' 60종 중 위키 스냅샷 적중 53종, 나머지 7종은 개명 6 + 위키가 옳은 1 로
  실질 일치 60/60. ⚠ 그래서 티커가 아니라 CIK 로 조인한다(그쪽 cik_hist).

범위 — 위키본이 오히려 넓다. DB 경로는 SPX 2020-09~ 였는데 이 파일은 2015-01~ 이다.
  ⚠ 그렇다고 호출부의 START 를 마음대로 앞당기지 말 것 — 게시된 수치가 통째로 바뀐다.
    넓히는 것은 '더 길게 재기로 한다'는 별도 결정이다.

결손 — 한 달의 한쪽 지수가 비면 **직전 달을 이월**하고 그 사실을 carried 로 돌려준다.
  멤버십은 월 단위로 거의 안 바뀌므로 이월이 0으로 두는 것보다 참에 가깝다. 다만 조용히
  하지 않는다 — 호출부가 화면·로그에 적을 수 있게 목록으로 준다.
  (실측 2026-08-03: 2020-09 이후 결손은 2024-04 의 ndx 하나뿐이고 앞뒤 달이 모두 101종이다.)
"""
from __future__ import annotations
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data", "index_history.json")


def load(start: str | None = None, path: str | None = None):
    """{YYYY-MM: [티커…]} (SPX ∪ NDX) 와 이월 목록을 돌려준다.

    start 는 'YYYY-MM' 또는 'YYYY-MM-DD'. None 이면 파일 전체.
    """
    p = path or HIST
    if not os.path.exists(p):
        raise SystemExit(
            "%s 가 없다 — `python build/refresh_index_history.py` 를 먼저 돌릴 것.\n"
            "  (위키백과 과거 리비전에서 만든다. 사내 DB 는 더 이상 쓰지 않는다.)" % p)
    d = json.load(io.open(p, encoding="utf-8"))
    months = d.get("months") or {}
    if not months:
        raise SystemExit("%s 에 months 가 비어 있다 — 파서가 조용히 어긋났을 수 있다." % p)

    ym0 = (start or "")[:7]
    out, carried = {}, []
    prev = {"spx": [], "ndx": []}
    for ym in sorted(months):
        cur = months[ym] or {}
        use = {}
        for ix in ("spx", "ndx"):
            v = cur.get(ix) or []
            if not v and prev.get(ix):
                v = prev[ix]
                if not ym0 or ym >= ym0:
                    carried.append((ym, ix, len(v)))
            use[ix] = v
        prev = {k: (v or prev.get(k) or []) for k, v in use.items()}
        if ym0 and ym < ym0:
            continue
        u = sorted(set(use["spx"]) | set(use["ndx"]))
        if u:
            out[ym] = u
    if not out:
        raise SystemExit("멤버십이 0개월이다 — start(%s)가 파일 범위 밖인지 볼 것." % start)
    return out, carried


def source_note() -> str:
    """산출물에 적어 둘 출처 한 줄. 화면·JSON 이 같은 문장을 쓰게 한다."""
    return ("월말 지수 편입 종목(SPX ∪ NDX) — 위키백과 지수 목록 문서의 과거 리비전"
            "(data/index_history.json · build/refresh_index_history.py). CC BY-SA.")


if __name__ == "__main__":
    import sys
    mem, carried = load(sys.argv[1] if len(sys.argv) > 1 else None)
    ks = sorted(mem)
    print("멤버십 %d개월 · %s ~ %s" % (len(mem), ks[0], ks[-1]))
    print("  종목수 min/max: %d / %d" % (min(len(v) for v in mem.values()),
                                         max(len(v) for v in mem.values())))
    print("  이월: %s" % (carried or "없음"))
