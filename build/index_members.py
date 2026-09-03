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

범위 — 위키본이 오히려 넓다. DB 경로는 SPX 2020-09~ 였는데 이 파일은 **2014-06~** 이다
  (2026-08-11 에 2015-01 에서 내렸다 — CIK 컬럼이 생긴 첫 달이 2014-06 이라는 실측 때문이다.
   그 아래는 조인이 무너진다. 근거는 refresh_index_history.py 머리말).
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


# ── 지도의 «꼬리» 규약 — 한 곳에서 정한다 ─────────────────────────────────
# 🚨 2026-09-03 전면 점검. 이 랩은 주기가 다른 두 자료를 `d[:7]` 월 키로 조인하는 구조가
#   도처에 있다(지수 멤버십 · NDX 편입 · 스타일 패널). 하나같이 「결손 달은 직전 달을
#   이월한다」고 적혀 있는데, **그 이월은 지도의 키 범위 «안»에서만 일어난다.**
#   마지막 키 뒤는 항목 자체가 없어 `mem.get(ym) or set()` 이 **빈 집합을 조용히** 돌려준다.
#
#   그런데 가격 패널은 **매 거래일** 갱신이고 이 지도는 **주 1회**다. 그래서 새 달 첫
#   거래일부터 그 주 토요일까지 **매달 빈다.**
#   ⚠ 정정(2026-09-03 오후) — 이 주석을 처음 쓸 때 「refresh-members 가 주 1회 굽는다」고
#     적었는데 **틀렸다.** 그 잡은 members.json(오늘 스냅샷)만 굽고 index_history.json 은
#     안 건드렸다. 굽는 잡이 **저장소에 하나도 없었고**(grep 0건) 마지막 쓰기가 2026-08-14 라
#     20일 고착이었다. 같은 날 refresh_index_history.py 를 refresh-members.yml 에 배선해서
#     이제 정말로 주 1회(토)가 됐다 — 표준 라이브러리만 쓰고 증분이라 실측 7.7초다.
#     러너가 돌 수 있게 만들어 놓고 배선만 안 한 것이었다(되풀이 결함 1번).
#
#   실제로 세 번 밟았다 —
#     · 2026-09-02 style_pit_panel 이 members_at(마지막날)=∅ 로 스타일 18종 전부를 죽였다.
#       (refresh-assets 두 슬롯 연속 실패 → 자산 패널·시장판·홈 성과가 하루 고착)
#     · 실측 ndx_members('2026-08')=102 인데 ('2026-09')=0 — 2026-09-30 리밸에서
#       NDX 계열 다섯(x-ncapw·ncap10·ncap5·ncap45·ncapndx)이 통째로 무보유가 된다.
#     · pit_backtest 는 같은 파일 안에서 **대조군만 이월하고 전략은 안 한다** —
#       그 비대칭이 그대로 「생존편향」 칸에 적힌다.
#
#   조용한 이유가 세 겹이라 더 나쁘다: ⓐ 예외가 안 난다(`len(mc)<40` 갈래로 빠진다)
#   ⓑ 검사가 못 본다(「CAGR 0 = 전 구간 무보유」만 잡는다) ⓒ 화면의 거짓 초록이 덮는다.
#
# ⚠ 이월은 **선견이 아니다.** 9월 1일에 알 수 있는 최신 명단은 8월 명단이다.
# ⚠ **꼬리만** 이월한다. 창 «안쪽» 결손을 이월로 덮으면 마스크가 풀린 것을 못 보게 되는데,
#   그것이 호출부의 gapless 검사가 막으려는 실패다. 안쪽은 여기서 손대지 않는다.
CARRY_MAX_M = 2      # 주 1회 갱신이라 정상 최대는 1달. 2를 넘으면 수집이 죽은 것이다.

_WARNED: set = set()


def _months_between(a: str, b: str) -> int:
    """월 키 b 가 a 보다 몇 달 뒤인가(같으면 0, 앞이면 음수)."""
    return (int(b[:4]) - int(a[:4])) * 12 + (int(b[5:7]) - int(a[5:7]))


def at(mem: dict, ym: str, label: str = "멤버십", carry_max: int = CARRY_MAX_M,
       say=print) -> set:
    """월 키 조회 — **지도의 마지막 키 뒤는 그 키를 이월한다.**

    mem       {'YYYY-MM': [티커…] 또는 set}
    ym        찾을 월 키('YYYY-MM')
    carry_max 마지막 키에서 몇 달까지 이월할 것인가. 넘으면 SystemExit.
    say       이월했다는 사실을 알리는 함수(조용히 하지 않는다). None 이면 안 알린다.

    ⚠ 지도 «안»의 결손은 이월하지 않는다 — 빈 집합을 그대로 돌려준다(위 머리말).
    """
    v = mem.get(ym)
    if v:
        return set(v)
    keys = [k for k, x in mem.items() if x]
    if not keys:
        return set()
    last = max(keys)
    gap = _months_between(last, ym)
    if gap <= 0:                       # 지도 안쪽(또는 시작 전)의 결손 — 손대지 않는다
        return set()
    if gap > carry_max:
        raise SystemExit(
            "%s 지도가 %s 에서 멈췄는데 %s 을 찾는다(%d달 차) — 이월 한도 %d달을 넘었다. "
            "한 분기 묵은 명단을 시점정합이라 부르며 내보내지 않는다. "
            "`python build/refresh_index_history.py` 가 왜 안 도는지 볼 것"
            % (label, last, ym, gap, carry_max))
    if say and (label, last, ym) not in _WARNED:
        _WARNED.add((label, last, ym))
        say("  ⚠ %s 지도가 %s 까지만 있다 — %s 은 %s 명단을 이월한다(주 1회 갱신이라 정상)"
            % (label, last, ym, last))
    return set(mem.get(last) or [])


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
