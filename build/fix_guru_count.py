# -*- coding: utf-8 -*-
"""build/fix_guru_count.py — «13F 공시 18인» 이라는 **틀린 문장**을 고친다.

무엇이 틀렸나
   `x-guruacc` 의 규칙 문장이 «13F 공시 **18인**의 합산 보유금액» 이라고 적혀 있다.
   실측(`data/guru_history.json`)으로 매니저 수는 **분기마다 다르고 18인이었던 적이 없다**:

       2013-06  22명 → 2016-06  23명 → 2019-06  24명 → 2020-12 이후  27명
       (최소 22 · 최대 27 · 오늘 기준 27명)

   등록 당시의 수가 굳은 채 자료만 자란 것으로 보인다. 화면에 나가는 규칙 문장이
   자료와 다르면 **그 문장이 거짓말**이고, 이 랩은 «이름이 자료보다 크면 그 자체가
   거짓말이다» 를 바로 그 규칙의 사유에 적어 뒀다.

무엇을 고치나
   ① `build/tech_backtest.py` 의 원문 — 다음에 구우면 맞게 나온다.
   ② `data/tech_strategies.json` · `data/strategy_report.json` 의 **문장만** —
      이 클론에서는 백테스트를 못 돌리므로(투자의견 캐시 부재) 화면에 나가는 글자를
      직접 고친다. **숫자·성적·보유는 한 글자도 안 건드린다.**

  python build/fix_guru_count.py            무엇이 바뀌는지만 본다
  python build/fix_guru_count.py --write    실제로 쓴다
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

OLD_A = "13F 공시 18인의 합산 보유금액이"
NEW_A = "13F 공시 거장 22~27인(분기마다 다르다 · 오늘 27인)의 합산 보유금액이"
OLD_B = "18인은 기관 수급이 아니라 거장 포지셔닝이고, "
NEW_B = "이들은 기관 수급이 아니라 거장 포지셔닝이고, "
OLD_C = "18인뿐이라 서로 다른 값이 얇다"
NEW_C = "스물 몇 명뿐이라 서로 다른 값이 얇다"
PAIRS = ((OLD_A, NEW_A), (OLD_B, NEW_B), (OLD_C, NEW_C))


def counts():
    d = json.load(io.open(os.path.join(DATA, "guru_history.json"), encoding="utf-8"))
    n = [(q, len(d["holdings"][q])) for q in d["quarters"]]
    return d, n


def main(argv):
    write = "--write" in argv
    d, n = counts()
    print("실측 — 분기 %d개 · 매니저 최소 %d · 최대 %d · 오늘 %d"
          % (len(n), min(x[1] for x in n), max(x[1] for x in n), d["n_managers"]))
    print("   " + " · ".join("%s %d명" % (q[:7], c) for q, c in n[::8]))
    print("\n⚠ 27명 **전원이 2026-06-30 까지 제출을 계속한다** — 중간에 사라진 매니저가 0명이다.")
    print("   명단을 오늘 기준으로 골랐다는 뜻이고, **매니저 생존편향**이 그대로 들어 있다.")
    print("   (그 크기는 별도 사전등록에서 잰다 — PREREG-2026-09-20-GURUACC.)")

    tot = 0
    for f in ("tech_strategies.json", "strategy_report.json"):
        p = os.path.join(DATA, f)
        s = io.open(p, encoding="utf-8").read()
        k = sum(s.count(a) for a, _ in PAIRS)
        print("\n%-24s 고칠 곳 %d" % (f, k))
        if not k:
            continue
        for a, b in PAIRS:
            s = s.replace(a, b)
        tot += k
        if write:
            io.open(p, "w", encoding="utf-8").write(s)
    p = os.path.join(ROOT, "build", "tech_backtest.py")
    s = io.open(p, encoding="utf-8").read()
    k = sum(s.count(a) for a, _ in PAIRS)
    print("\n%-24s 고칠 곳 %d" % ("build/tech_backtest.py", k))
    if k:
        for a, b in PAIRS:
            s = s.replace(a, b)
        tot += k
        if write:
            io.open(p, "w", encoding="utf-8").write(s)
    print("\n%s 총 %d곳" % ("썼다 —" if write else "(안 썼다. --write 로 쓴다)", tot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
