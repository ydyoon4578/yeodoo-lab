# -*- coding: utf-8 -*-
"""build/wire_refs.py — 빠진 출처를 붙인다. 두 종류이고, **근거의 질이 다르다.**

ⓐ **배선 누락 12건** — 짝(10종판)에는 논문이 있는데 크기 변형(-nNN)에는 없다.
   그 규칙들이 **자기 문장에 «짝이 되는 10종판과 점수 함수가 같다» 고 적어 뒀다.**
   같은 점수를 쓰는 두 규칙이 서로 다른 출처를 갖는 것은 둘 중 하나가 틀린 것이다.
   → 짝의 논문을 그대로 붙인다. **연구 문제가 아니라 배선 문제다.**

ⓑ **새로 찾은 것 2건** — `x-fcfy` · `x-divgrow`. 웹 검색으로 후보를 찾았다.
   🚨 **둘 다 정의가 완전히 같지 않다.** 이 랩의 출처 규약은
   «확실하지 않은 규칙은 비워 둔다 … 없는 것을 지어 채우면 독자가 원문을 못 찾고,
   그 사실도 모른다» 이다. 그래서 붙이되 **어디가 다른지를 `fit` 칸에 함께 적는다.**
   그 칸이 없으면 독자가 «이 규칙 = 이 논문» 으로 읽고, 그것이 규약이 막으려던 일이다.

⚠ `x-residind-n52` 는 짝도 비어 있어 건드리지 않는다 — 배선이 아니라 정말 출처가 없다.

  python build/wire_refs.py            무엇이 바뀌는지만 본다
  python build/wire_refs.py --write    실제로 쓴다
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "build", "strategy_refs.json")

# ⓐ 짝에서 그대로 가져올 것 — {크기변형: 짝}
TWINS = {
    "x-52wh-n155": "x-52wh", "x-agrow-n52": "x-agrow", "x-btp-n155": "x-btp",
    "x-lowvol-n100": "x-lowvol", "x-max5low-n52": "x-max5low",
    "x-maxlow-n52": "x-maxlow", "x-mom12-n52": "x-mom12",
    "x-payout-n50": "x-payout", "x-poacc-n52": "x-poacc",
    "x-residmom-n52": "x-residmom", "x-revdrift-n25": "x-revdrift",
    "x-shiss-n52": "x-shiss",
}

# ⓑ 새로 찾은 것 — fit 에 «어디가 다른가» 를 반드시 적는다
NEW = {
    "x-fcfy": [
        {"a": "Hackel·Livnat·Rai", "y": 1994,
         "t": "The free cash flow/small-cap anomaly",
         "j": "Financial Analysts Journal 50",
         "fit": ("부분 일치. 원문은 **소형주**에서 «잉여현금흐름을 꾸준히 내고 · 부채가 낮고 · "
                 "잉여현금흐름 배수가 낮은» 회사를 함께 고른다. 이 규칙은 그중 «배수가 낮다"
                 "(=수익률이 높다)» 하나만 쓰고 유니버스가 **대형주 S&P 500∪NDX** 다. "
                 "방향의 근거로는 맞고, 성적을 원문과 나란히 놓을 수는 없다.")},
        {"a": "Hackel·Livnat·Rai", "y": 2000,
         "t": "A free cash flow investment anomaly",
         "j": "Journal of Accounting, Auditing & Finance 15",
         "fit": "위 1994 의 후속 검정. 같은 이유로 부분 일치다."},
    ],
    "x-divgrow": [
        {"a": "Grullon·Michaely·Swaminathan", "y": 2002,
         "t": "Are dividend changes a sign of firm maturity?",
         "j": "Journal of Business 75",
         "fit": ("부분 일치. 원문은 배당을 **올린 사건** 뒤 3년 누적 초과수익(FF3 기준 약 8%)을 "
                 "보고하고, 그 원인을 체계적 위험의 하락으로 설명한다. 이 규칙은 «올렸나» 가 "
                 "아니라 **증가율의 크기**로 줄을 세우고 보유가 한 달(이 랩 원판)이다. "
                 "🚨 원문은 오히려 «성숙해져서 위험이 준 것» 이라고 읽으므로, 이 규칙이 "
                 "**원문의 주장을 그대로 구현한 것은 아니다.**")},
    ],
}
# ⚠ 랩의 규칙 본문이 이미 이름을 대던 것 — 형식 출처로 올리지 않는 이유를 남긴다
KEEP_BLANK_NOTE = {
    "x-divgrow-prose": ("규칙 본문이 Michaely·Thaler·Womack(1995)를 첫 줄에 댄다. "
                        "그 논문은 **배당의 개시·중단**에 대한 것이고 이 규칙은 증가율 크기다. "
                        "본문 인용은 그대로 두되 형식 출처로 올리지 않는다 — "
                        "대신 Grullon 외(2002)를 부분 일치로 붙였다."),
}


def main(argv):
    write = "--write" in argv
    d = json.load(io.open(REFS, encoding="utf-8"))
    P = d.setdefault("papers", {})
    n_a = n_b = 0

    print("■ ⓐ 배선 누락 — 짝의 논문을 그대로 붙인다")
    for sid, base in sorted(TWINS.items()):
        if P.get(sid):
            print("   %-16s 이미 있다 — 건너뜀" % sid); continue
        src = P.get(base)
        if not src:
            print("   %-16s ⚠ 짝(%s)에도 없다 — 건너뜀" % (sid, base)); continue
        P[sid] = json.loads(json.dumps(src))
        n_a += 1
        print("   %-16s ← %-14s %s (%s)" % (sid, base, src[0].get("a"), src[0].get("y")))

    print("\n■ ⓑ 새로 찾은 것 — fit 에 «어디가 다른가» 를 적는다")
    for sid, ps in sorted(NEW.items()):
        if P.get(sid):
            print("   %-16s 이미 있다 — 건너뜀" % sid); continue
        P[sid] = ps
        n_b += 1
        for p in ps:
            print("   %-16s %s (%s) %s · %s" % (sid, p["a"], p["y"], p["t"], p["j"]))
            print("      fit: %s" % p["fit"][:90])

    d.setdefault("partial", {})["note"] = (
        "일부 항목의 `fit` 칸은 **원문과 이 랩의 구현이 어디서 갈리는지**를 적은 것이다. "
        "fit 이 있는 항목은 «이 규칙 = 이 논문» 이 아니라 «방향의 근거» 로만 읽어야 한다. "
        "이 랩의 출처 규약이 막으려는 것은 독자가 원문을 찾아가서 다른 것을 보는 일이다.")
    d["partial"].update(KEEP_BLANK_NOTE)

    print("\n붙인 것 — 배선 %d건 · 새로 찾은 것 %d건" % (n_a, n_b))
    if not write:
        print("(안 썼다. --write 로 쓴다)")
        return 0
    io.open(REFS, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print("→ %s" % REFS)
    print("⚠ data/strategy_report.json 과 strategy_index 를 다시 구워야 화면에 나간다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
