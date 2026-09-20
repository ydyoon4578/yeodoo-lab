# -*- coding: utf-8 -*-
"""build/sync_tested.py — 세 번째 목록의 거울을 정본에 맞춘다.

무엇을 고치나
   `validate_site.py` ④ 가 «세 번째 목록 개수 불일치 — 정본 206종 vs 산출 200종»
   으로 막고 있었다. 검증기가 적어 둔 해법은 «build/tech_backtest.py 재실행» 인데,
   **이 클론에서는 그것을 못 돌린다**(`data/_ratings_cache.json` 이 없어서 투자의견
   이력이 0종이 되고, 그대로 돌리면 게시된 산출물이 조용히 나빠진다 — 2026-09-19 에
   같은 사유로 중단했다).

왜 이 스크립트로 고쳐도 되나
   `tech_backtest.py` 가 그 키를 만드는 줄은 **한 줄이고 가공이 없다**:

       "tested": load_tested(),          # tech_backtest.py

   `load_tested()` 는 `build/tested_not_published.json` 의 `items` 를 **그대로** 돌려준다.
   즉 이 키는 정본의 **복사본**이고, 복사는 백테스트와 무관하다.
   그래서 **백테스트가 그 키에 쓸 값과 똑같은 값**을 여기서 쓴다.
   ⚠ 다른 키는 한 개도 건드리지 않는다. 성적·NAV·차트는 백테스트만이 만든다.

같이 맞추는 것 — `limits` 의 다중검정 문장
   그 문장에 규칙 개수가 **글자로 박혀** 있다(«규칙 319개를 돌렸다(등록 125개 +
   내린 194개)»). 백테스트는 이것도 `len(STRATS) + len(load_tested())` 로 찍는다.
   🚨 실측으로 이 문장(194)은 `tested` 키(200)와도 안 맞았다 — 예전에 거울만 일부
   맞추고 문장을 안 고친 자국이다. **숫자가 세 군데에 따로 살면 반드시 갈라진다.**

  python build/sync_tested.py            무엇이 달라지는지만 보여준다
  python build/sync_tested.py --write    실제로 쓴다
"""
from __future__ import annotations
import io, json, os, re, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "build", "tested_not_published.json")
ART = os.path.join(ROOT, "data", "tech_strategies.json")


def main(argv):
    write = "--write" in argv
    led = json.load(io.open(LEDGER, encoding="utf-8"))
    items = led.get("items") or []
    art = json.load(io.open(ART, encoding="utf-8"))
    n_live, n_old = len(art.get("strategies") or []), len(art.get("tested") or [])

    print("정본  build/tested_not_published.json   items %d" % len(items))
    print("산출  data/tech_strategies.json         tested %d · strategies %d"
          % (n_old, n_live))

    if n_old == len(items):
        print("\n이미 맞다 — 고칠 것 없다.")
    else:
        a = {x["sid"] for x in (art.get("tested") or [])}
        b = {x["sid"] for x in items}
        print("\n■ 정본에만 있는 sid %d개" % len(b - a))
        for s in sorted(b - a):
            it = next(x for x in items if x["sid"] == s)
            print("   + %-20s %-36s %s" % (s, (it.get("name") or "")[:36], it.get("when") or "—"))
        if a - b:
            print("\n■ 산출에만 있는 sid %d개 (정본에서 사라진 것 — 손으로 확인할 것)" % len(a - b))
            for s in sorted(a - b):
                print("   - %s" % s)

    # 다중검정 문장의 숫자
    lim = art.get("limits") or []
    tot = n_live + len(items)
    hit = None
    for i, x in enumerate(lim):
        if isinstance(x, str) and x.startswith("다중검정"):
            hit = i
            new = re.sub(r"규칙 \d+개를 돌렸다\(이번 실행에 등록된 \d+개 \+ 돌렸다가 목록에서 내린 \d+개",
                         "규칙 %d개를 돌렸다(이번 실행에 등록된 %d개 + 돌렸다가 목록에서 내린 %d개"
                         % (tot, n_live, len(items)), x)
            print("\n■ 다중검정 문장")
            print("   전  %s" % x[:96])
            print("   후  %s" % new[:96])
            lim[i] = new
    if hit is None:
        print("\n⚠ 다중검정 문장을 못 찾았다 — limits 를 손으로 볼 것.")

    if not write:
        print("\n(쓰지 않았다. 실제로 쓰려면 --write)")
        return 0

    art["tested"] = items
    art["limits"] = lim
    art["tested_synced"] = {
        "by": "build/sync_tested.py",
        "why": ("tech_backtest.py 를 못 돌리는 클론에서 세 번째 목록의 거울만 정본에 맞췄다. "
                "그 키는 load_tested() 의 그대로 복사라 백테스트와 무관하다. "
                "성적·NAV·차트는 건드리지 않았다."),
        "n": len(items),
    }
    io.open(ART, "w", encoding="utf-8").write(json.dumps(art, ensure_ascii=False))
    print("\n→ 썼다. tested %d → %d" % (n_old, len(items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
