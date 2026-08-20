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

    print("\n열 안내: A=날짜 B=펀드 C=NAV D=좌수(NAV÷기준가×1000) E=기준가")
    # ⚠ 시트는 날짜 **내림차순**이다(1차 실행 실측) — «마지막 행»은 가장 오래된 날이다.
    #   파서는 max(날짜) 를 쓰므로 정렬과 무관하게 옳다. 진단은 날짜로 줄 세워 찍는다.
    for f, rows in rows_by_fund.items():
        ser = sorted((d10(r[0]), float(r[2]), float(r[4])) for r in rows)
        print("\n■ 펀드 %s — 총 %d행 · %s ~ %s" % (f, len(rows), ser[0][0], ser[-1][0]))
        print("   최신 3행:")
        for d, nv, bp in ser[-3:]:
            print("     %s  NAV %.0f  기준가 %.6f" % (d, nv, bp))
        print("   연초 3행:")
        for d, nv, bp in ser[:3]:
            print("     %s  NAV %.0f  기준가 %.6f" % (d, nv, bp))
        # 연초 후 — 기준 후보별. 화면(portfolio_fund)은 첫 행(전년 12-31)을 기준으로 쓴다.
        bp_last = ser[-1][2]
        print("   연초 후 후보:")
        print("     기준 전년말 %s (화면 방식)      → %+7.3f%%"
              % (ser[0][0], (bp_last / ser[0][2] - 1) * 100))
        # 분배락 후보 — 기준가 일수익 하위 5일. 결산 분배가 있으면 여기 걸린다.
        #   (그날 미국 시장이 안 빠졌는데 기준가만 빠졌으면 분배락이다 — 지수는 화면에서 대조.)
        dd5 = sorted((ser[i][2] / ser[i - 1][2] - 1, ser[i - 1][0], ser[i][0], ser[i - 1][2], ser[i][2])
                     for i in range(1, len(ser)))
        print("   기준가 일수익 하위 5일 (분배락 후보):")
        for r5, d0, d1, b0, b1 in dd5[:5]:
            print("     %s → %s  %+.3f%%  (%.4f → %.4f)" % (d0, d1, r5 * 100, b0, b1))
        # 만약 그 하락일이 분배락이면: 그 날 이후 기준으로 다시 잰 연초 후도 같이 찍는다
        worst = dd5[0]
        print("   (참고) 하위 1일을 분배락으로 보고 재투자 가정 → %+7.3f%%"
              % ((bp_last / ser[0][2] / (1 + worst[0]) - 1) * 100))
        # 좌수(D=NAV÷기준가) 급변일 — 분배 재투자·대량 설정/환매의 흔적
        us = sorted((d10(r[0]), float(r[3])) for r in rows)
        uc = sorted(((abs(us[i][1] / us[i - 1][1] - 1), us[i - 1][0], us[i][0])
                     for i in range(1, len(us))), reverse=True)
        print("   좌수 변화 상위 3일:")
        for ch, d0, d1 in uc[:3]:
            print("     %s → %s  %.3f%%" % (d0, d1, ch * 100))
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
