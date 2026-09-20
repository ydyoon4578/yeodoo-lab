# -*- coding: utf-8 -*-
"""build/audit_buyback.py — 분할이 자사주 매입 신호를 얼마나 오염시키나.

`AUDIT-2026-09-20-SHARES2` §9 가 «크기를 안 쟀다» 고 적은 것을 잰다.

랩의 여러 스크립트가 주식수의 **1년 변화율**을 자사주 매입 신호로 쓴다
(`tech_backtest.py` · `pure*.py` · `style_score.py` …).
주식수가 분할 기준으로 어긋나 있으면 **20:1 분할이 「주식수 1,900% 증자」**로,
**1:8 역분할이 「87.5% 자사주 소각」**으로 보인다.

여기서는 고치기 전 계열과 고친 계열로 각각 1년 변화율을 만들고,
**얼마나 많은 관측이 가짜로 큰 값을 갖는지** 센다. 고치지는 않는다 —
게시 산출물을 다시 굽지 않는다는 규약 때문이다. **크기만 적어 둔다.**
"""
from __future__ import annotations
import os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shares_clean import clean_shares                      # noqa: E402
from shares_split import clean_shares2                     # noqa: E402

BIG = 0.30          # 1년에 30% 넘게 변했으면 「큰 값」으로 본다


def yoy(ser):
    """{날짜: 값} → [(날짜, 1년 변화율)] · 가장 가까운 12개월 전과 견준다."""
    ks = sorted(ser)
    out = []
    for i, k in enumerate(ks):
        y, m = int(k[:4]), int(k[5:7])
        tgt = "%04d-%02d" % (y - 1, m)
        prev = [x for x in ks[:i] if x[:7] <= tgt]
        if not prev:
            continue
        a, b = ser[prev[-1]], ser[k]
        if a > 0 and b > 0:
            out.append((k, b / a - 1.0))
    return out


def main():
    old, new = clean_shares(), clean_shares2()
    no, nn, tk = 0, 0, set()
    rows = []
    for t in sorted(set(old) & set(new)):
        o, n = dict(yoy(old[t])), dict(yoy(new[t]))
        for k, vo in o.items():
            vn = n.get(k)
            if vn is None:
                continue
            if abs(vo) > BIG:
                no += 1
            if abs(vn) > BIG:
                nn += 1
            # 고치기 전엔 컸는데 고친 뒤 작아진 것 = 분할이 만든 가짜
            if abs(vo) > BIG and abs(vn) <= BIG:
                tk.add(t)
                rows.append((t, k, vo, vn))
    print("■ 주식수 1년 변화율 — |변화| > %d%% 인 관측" % (BIG * 100))
    print("   고치기 전 %5d건" % no)
    print("   고친 뒤   %5d건" % nn)
    print("   → **분할이 만든 가짜 %d건 · %d종**" % (len(rows), len(tk)))
    print("\n■ 가장 큰 가짜 12건 (고치기 전 → 고친 뒤)")
    for t, k, vo, vn in sorted(rows, key=lambda x: -abs(x[2]))[:12]:
        print("   %-6s %s   %+9.1f%%  →  %+7.1f%%" % (t, k[:7], vo * 100, vn * 100))
    print("""
   ⚠ 이 가짜는 **한 방향이 아니다** — 분할은 «대규모 증자»로, 역분할은
      «대규모 소각»으로 보인다. 자사주 매입 신호에서 **부호가 뒤집힌 관측**이 섞인다.
      그리고 분할은 **주가가 많이 오른 회사**가 하므로, 가짜가 들어가는 자리가
      무작위가 아니라 **승자 쪽으로 치우친다.**""")
    print("\n   고친 뒤에도 남은 %d건은 실제 증자·합병·소각일 수 있다. 여기서 판정하지 않는다." % nn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
