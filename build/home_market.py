#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""홈 전용 시장 요약 — data/regime.json + data/sentiment.json → data/home_market.json.

왜 이 파일이 있나
  홈은 국면 카드와 심리 카드를 그리려고 원본 둘을 통째로 받고 있었다. 실측(gzip):
      regime.json     5,205B   → 홈이 실제로 쓰는 부분은 469B
      sentiment.json 16,865B   → 홈이 실제로 쓰는 부분은 1,607B
  즉 홈 JSON 전송량의 53%가 화면을 만들지 않는다. 가장 큰 덩어리는 sentiment.history 로,
  2,765점(2015-08~)이 실려 오는데 스파크라인은 끝 750점(3년)만 그린다. regime.indicators 는
  39개 전부가 미사용이고 홈은 **개수 하나**만 쓴다(히어로 눈썹의 'FRED 39지표').

  이 저장소에는 같은 판례가 둘 있다 — build/home_summary.py(홈이 stocks.json 을 안 받게 한다)와
  data/style_trails.json(style_perf.json 의 발췌). 같은 방식이다.

무엇을 하지 않나
  원본을 줄이지 않는다. regime.json·sentiment.json 은 그대로 둔다 —
  build/asof_index.py 가 축 기준일을 그 둘에서 읽고, regime.html 은 전체 이력을 쓴다.
  이 파일은 **발췌**이지 대체가 아니다.

⚠ 표준 라이브러리만 쓴다. build/ci_push.sh 의 REBAKE_TABLE 에 올라가는 파일이라
  리베이스 뒤 어느 잡에서든 다시 구워져야 하는데, 잡마다 pip 목록이 다르다
  (refresh-regime 에는 scipy 가 없고 refresh-sentiment 에는 있다).

⚠ 라벨 어휘를 손대지 말 것. 홈의 카드는 RGC/RGKO/AXKO/SNTC/SNTE 사전으로 라벨을 찾는데,
  값이 도착했는데 사전에 없으면 '실패'가 아니라 '미도착'으로 판정돼 카드가 영영
  '불러오는 중…'에 고착된다(index.html 의 renderMarket). 원문을 그대로 옮긴다.

사용:
    python3 build/home_market.py
"""
from __future__ import annotations

import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "home_market.json")

# 국면 이력 띠는 최근 36개월, 심리 스파크라인은 최근 3년(거래일 750)만 그린다.
# 두 숫자는 index.html 의 렌더와 짝이다 — 한쪽만 바꾸면 화면이 조용히 달라진다.
RG_HIST = 36
SN_HIST = 750

# 홈이 읽는 국면 필드. 여기 없는 키는 화면에 나가지 않는다.
RG_FIELDS = ("label", "emoji", "growth", "inflation", "financial", "desc", "strategy")


# 심리 점수 → 구간 키. regime.html 의 BANDS 와 **같은 문턱**이다(0/20/40/60/80).
# 🚨 문턱을 화면에 두지 않는 이유: 홈과 regime.html 두 곳에 같은 표를 적으면 한쪽만
#   고쳤을 때 같은 점수가 두 화면에서 다른 색·다른 이름이 된다. 여기가 정본이다.
# ⚠ 색이 '좋다/나쁘다'가 아니라 '차갑다(공포)/뜨겁다(탐욕)' 축이라는 것도 그쪽 규약 그대로다.
SN_BANDS = ((20, "xfear"), (40, "fear"), (60, "neut"), (80, "greed"))


def _band(score):
    """0~100 → xfear|fear|neut|greed|xgreed. 점수가 없으면 None(화면이 회색으로 낸다)."""
    if score is None or not isinstance(score, (int, float)):
        return None
    for hi, key in SN_BANDS:
        if score < hi:
            return key
    return "xgreed"


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        print("  ⚠ %s 파싱 실패: %s" % (name, e))
        return None


def main() -> int:
    rg = load("regime.json")
    sn = load("sentiment.json")
    if not rg and not sn:
        print("❌ regime.json·sentiment.json 둘 다 없다 — 쓰지 않는다")
        return 1

    doc = {
        "note": "홈 전용 발췌. 원본은 data/regime.json · data/sentiment.json 이고 "
                "이 파일은 홈 카드가 실제로 그리는 필드만 담는다(build/home_market.py). "
                "전체 이력·지표 원문이 필요하면 원본을 읽을 것.",
        "as_of": None,
    }

    if rg:
        r = rg.get("regime") or {}
        hist = rg.get("history") or []
        doc["regime"] = {
            "as_of": rg.get("as_of"),
            # 원문 그대로 옮긴다(위 ⚠). 없는 키는 넣지 않아 화면이 '—'로 떨어지게 둔다.
            "regime": {k: r[k] for k in RG_FIELDS if k in r},
            "history": [{"dt": h.get("dt"), "r": h.get("r")} for h in hist[-RG_HIST:]],
            # 배열 대신 개수. 홈은 '.length' 만 쓰는데 그 정수 하나 때문에 gzip 3.1KB 를 받고 있었다.
            "n_indicators": len(rg.get("indicators") or []),
            # 🚨 2026-08-06 — 지표 종합(요약 문장 + 축별 한 단어)을 싣는다(사용자 요청으로
            #   홈에 시장 국면 구획을 되살렸다). indicators 39개 전문은 여전히 안 싣는다 —
            #   홈이 쓰는 것은 **요약**이지 지표 하나하나가 아니다. 그 39개는 regime.html 이 편다.
            #   chips 는 축 7개(소비·고용·생산·주택·물가·금융여건·금리) × 한 단어라 가볍다.
            "summary": ({"text": (rg.get("summary") or {}).get("text"),
                         "mode": (rg.get("summary") or {}).get("mode"),
                         "chips": [{k: c.get(k) for k in ("name", "word", "kind", "n", "skip")}
                                   for c in ((rg.get("summary") or {}).get("chips") or [])]}
                        if rg.get("summary") else None),
        }

    if sn:
        h = sn.get("history") or []
        tail = h[-SN_HIST:]
        doc["sentiment"] = {
            "as_of": sn.get("as_of"),
            "score": sn.get("score"),
            "label": sn.get("label"),
            "score_pctl": sn.get("score_pctl"),
            "weight_available": sn.get("weight_available"),
            "prev": {k: v for k, v in (sn.get("prev") or {}).items() if k in ("d1", "w1", "m1")},
            # 스파크라인은 x 를 등간격 인덱스로 그리므로 점마다 날짜가 필요 없다. 시작 날짜
            # 하나(라벨용)와 점수 배열이면 된다 — {dt,score} 객체 배열로 두면 같은 750점이
            # raw 24.9KB, 평면 배열이면 3.9KB 다.
            "hist_start": (tail[0] or {}).get("dt") if tail else None,
            "scores": [x.get("score") for x in tail],
            # 🚨 2026-08-12 — 구간 키를 **여기서** 정한다. 홈이 점수만 받고 스스로
            #   0/20/40/60/80 을 나누면 그 문턱표가 regime.html 의 BANDS 와 두 벌이 되고,
            #   한쪽만 고치면 같은 점수가 두 화면에서 다른 이름으로 불린다.
            #   ⚠ 이름(label)은 원본 sentiment.json 이 이미 준다 — 여기서 다시 짓지 않는다.
            #     이건 **색을 고르는 키**일 뿐이다(index.html 의 --sn-* 토큰).
            "band": _band(sn.get("score")),
        }

    # 대표 기준일 — 둘 중 뒤진 쪽. 홈의 지연 경고는 각 카드가 자기 as_of 로 따로 내지만,
    # 이 파일 자체의 신선도를 물으면(check_freshness) 더 낡은 쪽이 답이어야 한다.
    axes = [d.get("as_of") for d in (doc.get("regime"), doc.get("sentiment")) if d and d.get("as_of")]
    doc["as_of"] = min(axes) if axes else None

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

    n = os.path.getsize(OUT)
    src = sum(os.path.getsize(os.path.join(DATA, x))
              for x in ("regime.json", "sentiment.json")
              if os.path.exists(os.path.join(DATA, x)))
    print("홈 시장 요약 — 국면 %s · 심리 %s · 기준 %s · %.1fKB (원본 %.1fKB)"
          % ((doc.get("regime") or {}).get("as_of") or "—",
             (doc.get("sentiment") or {}).get("as_of") or "—",
             doc["as_of"] or "—", n / 1024.0, src / 1024.0))
    if not doc.get("regime"): print("  ⚠ 국면 없음 — 홈 국면 카드가 뜨지 않는다")
    if not doc.get("sentiment"): print("  ⚠ 심리 없음 — 홈 심리 카드가 뜨지 않는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
