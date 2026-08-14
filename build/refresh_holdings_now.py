# -*- coding: utf-8 -*-
"""build/refresh_holdings_now.py — 랩 전략의 '지금 보유'만 오늘 격자로 다시 뽑는다.

왜 따로 파나.
  성과 기준일은 **전월말**이라 한 달 안에서는 백테스트를 다시 돌려도 수치가 안 바뀐다
  (tech_backtest.asof_cut). 그런데 **보유 명단은 다르다** — 타이밍 22종은 매일, 주간 리밸
  8종은 매주 갈아탄다. 가격이 하루 늘 때마다 그 명단이 낡는데, 랩 본편(tech_backtest)은
  주 1회·월 1회만 돌므로 그 사이 화면이 최대 한 달 묵은 명단을 '지금 보유' 라고 말한다.

  랩 본편을 매일 돌리면 되지 않나 — 20분짜리다. 반면 보유는 **마지막 리밸 시점의 채점
  한 번**이면 나온다(1~2분). 성과는 월 1회, 보유는 매일 — 주기가 다른 두 가지를 한 잡에
  묶어 두었던 것이 문제였다.

무엇을 하나 / 안 하나.
  · data/tech_strategies.json 의 **holdings 칸만** 덮는다. metrics·nav·chart 는 손대지
    않는다 — 그것들은 전월말 기준이고 여기서 바뀌면 안 된다.
  · 다시 뽑기에 실패한 규칙은 **안 덮는다.** 그 카드는 옛 명단과 옛 as_of 를 그대로 들고
    있고, 화면이 as_of 를 같이 찍으므로 스스로 낡았다고 말한다.

  python build/refresh_holdings_now.py            # 덮어쓴다
  python build/refresh_holdings_now.py --dry-run  # 무엇이 바뀌는지만 본다
"""
from __future__ import annotations
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tech_backtest as TB                                        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "tech_strategies.json")


def main() -> int:
    dry = "--dry-run" in sys.argv
    if not os.path.exists(OUT):
        print("❌ data/tech_strategies.json 없음 — build/tech_backtest.py 를 먼저 돌릴 것")
        return 1
    doc = json.load(io.open(OUT, encoding="utf-8"))
    rows = doc.get("strategies") or []
    if not rows:
        print("❌ 전략이 0종 — 산출물이 비었다")
        return 1

    TB.build_strats()
    now = TB.current_holdings(TB.STRATS)
    if not now:
        # 조용히 넘어가지 않는다 — 넘어가면 옛 명단이 '지금' 으로 남는다.
        print("🚨 다시 뽑은 것이 0종 — 덮지 않는다(옛 명단이 그대로 나간다)")
        return 1

    moved, same, missing = [], 0, []
    for r in rows:
        h = now.get(r["sid"])
        if not h:
            missing.append(r["sid"])
            continue
        old = (r.get("holdings") or {}).get("as_of")
        if old != h.get("as_of"):
            moved.append((r["sid"], old, h.get("as_of")))
        else:
            same += 1
        if not dry:
            r["holdings"] = h

    print("\n기준일이 움직인 규칙 %d종 · 그대로 %d종 · 못 뽑은 것 %d종"
          % (len(moved), same, len(missing)))
    for sid, a, b in moved[:12]:
        print("   %-18s %s → %s" % (sid, a, b))
    if len(moved) > 12:
        print("   … 외 %d종" % (len(moved) - 12))
    if missing:
        print("   ⚠ 못 뽑은 규칙(옛 명단 유지): %s" % ", ".join(missing[:8]))

    if dry:
        print("\n--dry-run — 파일을 쓰지 않았다")
        return 0
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("\n→ %s (holdings 칸만 갱신)" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
