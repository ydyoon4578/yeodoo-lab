# -*- coding: utf-8 -*-
"""build/pit_quarantine.py — 편출 가격 **격리 명단**을 읽는 한 곳.

정본은 `data/pit_px.json` 의 `quarantine` 이다(build/pit_px_repair.py 가 2026-09-14 에 넣었다 —
PARA: 편입 기간 계열이 57.80~113,900 로 뛰는 «다른 증권» · COL: 록웰 콜린스가 1달러 미만).
격리 = «편입 기간 값이 믿을 수 없어 지운 이름» 이다. 그 이름은 **어느 경로로 읽든** 쓰면 안 된다.

🚨 왜 따로 떼었나(2026-09-23). 격리는 커밋되는 정리본(pit_px.json)에만 걸려 있었고, 원시 캐시
  `data/_pit_px_cache.json` 을 읽는 경로는 그것을 몰랐다. 그 캐시가 gitignore 였던 동안에는
  pit_px_repair ④ 가 로컬 캐시에서 지워 두면 됐다. 그런데 같은 날 `a2a9c154`(PIT 캐시를 저장소가
  갖는다)가 캐시를 러너에서 새로 받아 커밋하면서 — 받는 쪽(`pit_backtest.py --fetch-cache`)이 격리를
  모르니 — 야후가 지금 «PARA» 로 주는 다른 증권을 다시 받아 넣었다.
  · `pit_backtest.load_prices` 는 크기 검사(멤버 기간 100배)로 PARA 를 따로 걸러 안전했다.
  · `style_pit_panel.prepare` 는 캐시가 **있으면 캐시를 먼저** 쓰고 크기 검사가 없다 — 캐시가 러너에
    올라간 뒤로는 CI 의 스타일 PIT(style_top_pdf·style_pit)가 PARA 를 주입할 자리였다.
  · 기대투자성장 등록(PREREG-2026-09-23-EG)이 원시 캐시를 읽다가 그 오염을 밟았다(위생 상관 0.53).
  그래서 받는 곳·읽는 곳이 모두 이 함수를 부른다. 명단을 여러 벌로 두면 반드시 갈린다.

  import pit_quarantine as PQ ;  PQ.names()  → {'PARA', 'COL'}
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

ROOT =os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLIM = os.path.join(ROOT, "data", "pit_px.json")
_CACHE = None


def names():
    """격리된 티커 집합. 정리본이 없으면 빈 집합(그 경우 정리본 자체가 없다는 것을 부르는 쪽이 따로 막는다)."""
    global _CACHE
    if _CACHE is None:
        try:
            q = (json.load(io.open(SLIM, encoding="utf-8")) or {}).get("quarantine") or {}
            _CACHE = set(q.keys())
        except Exception:
            _CACHE = set()
    return set(_CACHE)


def drop(dct, label="", say=print):
    """사전(티커 → 계열)에서 격리 이름을 지우고 지운 것을 돌려준다. 지웠으면 한 줄 찍는다."""
    gone = sorted(t for t in names() if t in dct)
    for t in gone:
        dct.pop(t, None)
    if gone and say:
        say("  격리 적용%s: %s 제외 (data/pit_px.json quarantine)" % ((" · " + label) if label else "", ", ".join(gone)))
    return gone
