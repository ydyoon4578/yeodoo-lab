# -*- coding: utf-8 -*-
"""build/portfolio_navcheck.py — NAV 시트 원시 열 진단 (사내 PC 전용 · 일회성 아님)

왜 있나. 2026-08-20 사용자 발견: «2Z30은 펀드 기준가가 잘 맞는데 2A81은 9,597 정도인데
8.67 로 줬어». 두 펀드를 같은 코드(r[2]=NAV · r[4]=기준가)로 읽는데 한쪽만 틀리다는 것은
**시트 쪽 모양이 펀드마다 다르다**는 뜻이다 — 열이 밀렸거나, 같은 날짜 행이 여러 줄이라
나중 줄이 덮어쓰거나. 코드를 고치기 전에 원시 열을 눈으로 봐야 한다. 짐작으로 열 번호를
바꾸면 이번엔 2Z30 이 틀어진다.

무엇을 찍나 — 펀드별 마지막 6행의 A~H 열 원시값 + 파서가 실제로 채택한 (NAV, 기준가).
같은 (펀드, 날짜) 가 여러 행이면 그 사실도 센다(파서는 나중 행이 이긴다).

  python build/portfolio_navcheck.py
"""
from __future__ import annotations
import datetime as dt
import glob
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_CFG = os.path.join(ROOT, "_build", "portfolio_local.json")


def main() -> int:
    cfg = json.load(io.open(LOCAL_CFG, encoding="utf-8"))
    files = sorted((f for g in cfg["xlsm_globs"] for f in glob.glob(g)),
                   key=lambda f: (os.path.getmtime(f), f.replace(chr(92), '/').startswith('//')))
    if not files:
        raise SystemExit("사내 export 없음")
    path = files[-1]
    print("입력:", os.path.basename(path))
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    def d10(v):
        return v.strftime("%Y-%m-%d") if isinstance(v, dt.datetime) else str(v)[:10]

    rows_by_fund, dupes = {}, {}
    for r in wb["NAV"].iter_rows(min_row=11, values_only=True):
        if not r[0]:
            break
        f = str(r[1]).strip()
        rows_by_fund.setdefault(f, []).append(r)
        k = (f, d10(r[0]))
        dupes[k] = dupes.get(k, 0) + 1

    print("\n열 안내: A=날짜 B=펀드 C(r[2])=NAV로 읽음 E(r[4])=기준가로 읽음")
    for f, rows in rows_by_fund.items():
        print("\n■ 펀드 %s — 총 %d행 · 마지막 6행 원시값(A~H):" % (f, len(rows)))
        for r in rows[-6:]:
            print("   " + " | ".join("%s=%r" % (chr(65 + i), r[i]) for i in range(min(8, len(r)))))
        last = rows[-1]
        print("   → 파서 채택: 날짜 %s · NAV(C) %r · 기준가(E) %r"
              % (d10(last[0]), last[2], last[4]))
    dd = {k: n for k, n in dupes.items() if n > 1}
    if dd:
        print("\n🚨 같은 (펀드, 날짜) 중복 행 — 파서는 나중 행이 이긴다:")
        for (f, d), n in sorted(dd.items()):
            print("   %s %s × %d행" % (f, d, n))
    else:
        print("\n(펀드, 날짜) 중복 행 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
