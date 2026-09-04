# -*- coding: utf-8 -*-
"""build/pool_triage.py — 탐색 풀 카드가 **왜 아직 안 쟀는지**를 자료가 말하게 한다
                          → data/pool_triage.json

무엇을·왜.
  탐색 풀 116종 중 랩이 실제로 잰 것은 40종(34%)이다. 나머지 76종이 왜 안 쟀는지는
  지금 **아무 데도 안 적혀 있다.** 화면은 그냥 「외부 출처 · 미검증」이라고만 말한다.
  그래서 읽는 사람은 «게을러서 안 쟀나» 와 «잴 수 없어서 못 쟀나» 를 구별할 수 없다.
  둘은 완전히 다른 사실이고, 뒤엣것은 **랩의 한계를 드러내는 결과**다.

  → 카드마다 하나로 판정하고 사유를 적는다.

판정 넷.
  measured   이미 쟀다(lab 칸이 있다).
  ready      원문이 크기·문턱을 구체적으로 적었고 **랩에 입력이 있다** — 구현만 하면 된다.
  no_input   원문은 구체적인데 **랩에 그 자료가 없다**(신평사 등급 · 스핀오프 · 콜 전문 등).
             ⚠ 이건 결함이 아니라 **경계**다. 이 랩이 무엇을 못 재는지가 그대로 목록이 된다.
  underspec  원문이 「상위 분위」·「상위 편입」처럼 **수를 안 적었다.**
             🚨 여기에 기본값을 정하면 안 된다 — PREREG-2026-08-29-ASWRITTEN 이 못박았다:
             「원문에 없는 수를 내가 정하면 방금 없앤 자유도를 옮기는 것이다.」
             `nsel`(성적 보고 N 고르기)을 폐기하면서 없앤 자유도를, 자동 구현기가
             기본값이라는 이름으로 **대량 생산**하게 된다. 그래서 이 갈래는 자동화하지 않는다.

⚠ 이 분류는 **산문 어휘로 판정하는 추정**이다. 판정 자체를 «사실» 이라 부르지 않는다 —
  산출물에 method="heuristic" 을 싣고, 근거가 된 낱말을 hits 로 같이 남긴다.
  사람이 카드를 열어 보면 뒤집힐 수 있고, 뒤집으면 아래 OVERRIDE 에 사유와 함께 적는다.

    python build/pool_triage.py
    python build/pool_triage.py --check    # 커밋본과 다르면 종료코드 1
"""
from __future__ import annotations
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pool_triage.json")

# ── 랩이 **없는** 자료 — 이 낱말이 진입기준에 있으면 못 잰다 ────────────────────
#   ⚠ 실측으로 확인한 것만 적는다(2026-09-04). 있는 자료는 build/refresh_*.py 가 굽고
#     data/ 에 있다: 가격·거래량·고저 · SEC 재무 22태그 · 컨센서스 · 13F · 내부자 ·
#     8-K · 실적일정 · COT · 고객집중도 · 장중분봉 · ETF/FRED · 편입이력 · 분할 · 페어.
#   🚨 낱말은 **신호 수준**이어야 한다. 처음에 「옵션」·「뉴스」·「IV」 같은 넓은 말을 넣었더니
#     거짓 양성이 무더기로 났다(실측) —
#       C3  「**옵션으로** 여름엔 방어자산 대체」  → 선택 변형이지 필수 입력이 아니다
#       C6  「SPY/QQQ **또는** 옵션 미결제약정 상위」 → 앞 갈래로 구현된다
#       E11 「**옵션행사**·증여 제외」            → 내부자 거래 코드 필터다(그 자료는 있다)
#     즉 낱말이 나온다고 그 자료가 **필요한** 것이 아니다. 신호를 만드는 자리에 쓰이는
#     표현만 남긴다. ⚠ 좁히다 놓치는 편이 넓혀서 잘못 막는 편보다 낫다 —
#     못 잡으면 ready 로 남아 사람이 구현하다 알게 되고, 잘못 막으면 영영 안 쟨다.
MISSING = {
    "신평사 등급": ["신평사", "신용등급", "발행자 등급", "negative watch", "등급 하향"],
    "스핀오프 이벤트": ["스핀오프", "스플릿오프", "캐브아웃"],
    "실적 콜 전문": ["트랜스크립트", "콜 전문", "net tone"],
    "옵션 자료": ["내재변동성", "OTM 풋", "ATM 콜", "풋콜 비율", "옵션 IV", "델타 -0."],
    "뉴스·텍스트": ["감성분석", "뉴스 기사", "기사 수", "언론 보도량"],
    "포워드 환율": ["포워드 환율", "1개월 포워드", "포워드 디스카운트"],
    "채권 개별종목": ["회사채 개별", "CDS 스프레드"],
    "PIT 컨센서스": ["과거 컨센서스", "추정치 이력"],
    # 실측 보완(2026-09-04) — 표본으로 카드를 열어 보고 찾은 둘.
    #   · 지배구조: A10 이 E-index(주주권리) 를 쓴다. 랩에 그 자료가 없다.
    #   · 연구개발비: B3 이 R&D 자본을 쓴다. **SEC 재무 태그 22종에 rd 가 없다**
    #     (asset bb ca capex cash cfo cl cogs debt dep dps eps eq gp iss liab ni
    #      opinc re rev sh sho — 실측). 특허는 있는데 분모가 없다.
    "지배구조 자료": ["지배구조", "E-index", "G-index", "이사회 독립성"],
    "연구개발비(R&D)": ["R&D자본", "R&D 자본", "연구개발비", "특허/R&D", "특허인용/R&D"],
    # ⚠ **특허는 «없는 자료» 가 아니다.** .github/workflows/probe-patents.yml 이 받는다.
    #   다만 원천(Zenodo 15783125)이 2024-12-31 에 동결돼 있어 창이 그 앞까지다 —
    #   그 사실은 카드를 구현할 때 등록에 적을 일이지, 못 잰다고 막을 일이 아니다.
}

# ── 원문이 수를 안 적었다는 신호 ──────────────────────────────────────────────
VAGUE = ["상위 분위", "하위 분위", "상위 편입", "상위 그룹", "적정 수준", "일부 편입",
         "분위로 나눠", "상하위 분위"]
# 크기·문턱을 구체적으로 적었다는 신호
CONCRETE = [r"상위\s*\d+", r"\d+\s*종목", r"\d+\s*개\s*종목", r"N\s*=\s*\d+",
            r"\d+\s*[-~]\s*\d+\s*종목", r"[><≥≤]\s*-?\d", r"\d+\s*%\s*(초과|이상|미만|이하)",
            r"상위\s*\d+\s*%", r"[0-9]+\s*분위"]

# 사람이 카드를 열어 보고 뒤집은 것. **사유를 반드시 적는다.**
OVERRIDE: dict = {}


def classify(card: dict) -> dict:
    e = " ".join(str(card.get(k) or "") for k in ("entry", "target"))
    hits_missing = []
    for label, words in MISSING.items():
        for w in words:
            if w.lower() in e.lower():
                hits_missing.append((label, w))
                break
    concrete = [p for p in CONCRETE if re.search(p, e)]
    vague = [v for v in VAGUE if v in e]

    if card.get("lab"):
        return {"verdict": "measured", "why": "이미 쟀다 — lab 칸 참조", "hits": []}
    if hits_missing:
        return {"verdict": "no_input",
                "why": "랩에 없는 자료를 쓴다: " + " · ".join(l for l, _ in hits_missing),
                "hits": [w for _, w in hits_missing]}
    if concrete and not vague:
        return {"verdict": "ready",
                "why": "원문이 크기·문턱을 구체적으로 적었고 랩에 입력이 있다 — 구현만 하면 된다",
                "hits": concrete[:4]}
    return {"verdict": "underspec",
            "why": ("원문이 크기·문턱의 수를 안 적었다"
                    + ((" (" + " · ".join(vague) + ")") if vague else "")
                    + ". 여기에 기본값을 정하면 폐기한 자유도를 되살리는 것이라 자동 구현하지 않는다"
                      "(PREREG-2026-08-29-ASWRITTEN)"),
            "hits": vague}


def main(argv) -> int:
    pool = json.load(io.open(os.path.join(DATA, "rotation_pool.json"), encoding="utf-8"))
    cards = [c for c in (pool.get("strategies") or []) if c.get("id")]
    out, cnt = {}, {}
    for c in cards:
        r = OVERRIDE.get(c["id"]) or classify(c)
        out[c["id"]] = dict(r, name=str(c.get("name") or ""), cat=c.get("cat"))
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1

    doc = {"note": ("탐색 풀 카드가 «왜 아직 안 쟀나» 를 말한다. 판정 넷 — measured(이미 쟀다) · "
                    "ready(구현만 하면 된다) · no_input(랩에 그 자료가 없다) · "
                    "underspec(원문이 수를 안 적었다). "
                    "🚨 underspec 에 기본값을 정하지 않는다 — 폐기한 자유도를 되살리는 것이다"
                    "(PREREG-2026-08-29-ASWRITTEN)."),
           "method": "heuristic",
           "method_note": ("진입기준 산문의 낱말로 판정하는 **추정**이다. 근거 낱말을 hits 로 "
                           "남긴다. 카드를 열어 보고 뒤집으면 build/pool_triage.py 의 "
                           "OVERRIDE 에 사유와 함께 적을 것 — 코드에 적어야 다음 실행에도 남는다."),
           "n": len(cards), "counts": cnt, "cards": out}

    if "--check" in argv:
        cur = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else None
        ok = cur == doc
        print("일치" if ok else "불일치 — python build/pool_triage.py 로 다시 구울 것")
        return 0 if ok else 1

    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("탐색 풀 %d종 판정" % len(cards))
    for k, lab in (("measured", "이미 쟀다"), ("ready", "구현만 하면 된다"),
                   ("no_input", "랩에 자료가 없다"), ("underspec", "원문이 수를 안 적었다")):
        print("  %-10s %-16s %3d종" % (k, lab, cnt.get(k, 0)))
    rd = [i for i, v in out.items() if v["verdict"] == "ready"]
    print("\n구현 대기(ready) %d종: %s" % (len(rd), ", ".join(sorted(rd))))
    ni = {}
    for i, v in out.items():
        if v["verdict"] == "no_input":
            ni.setdefault(v["why"].split(": ", 1)[-1], []).append(i)
    if ni:
        print("\n랩이 못 재는 것 — 이것이 이 랩의 경계다")
        for k, v in sorted(ni.items(), key=lambda x: -len(x[1])):
            print("  %-24s %2d종  %s" % (k[:24], len(v), ", ".join(sorted(v)[:8])))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
