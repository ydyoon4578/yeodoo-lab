# -*- coding: utf-8 -*-
"""build/px_repair_db.py — **야후가 깨진 개별 종목만** 사내 DB 종가로 메운다.

## 왜 있나 (2026-08-19 · 사용자 결정)

  EQR(에퀴티 레지덴셜)의 data/sd/EQR.json 이 2026-07-17 이후 **22거래일째 비어 있었다.**
  합병이 아니다 — 사내 DB 에 2026-08-18 까지 S&P 500 구성종목으로 멀쩡히 있고,
  yfinance 쪽이 깨졌다(1개월치를 요청해도 2행만 준다).
  🚨 즉 **현역 편입 종목 하나가 한 달간 빠진 채** 이 랩의 전 횡단면 전략이 돌았다.
  그런데 아무 검사도 안 걸렸다 — 격자 구멍 검사는 «하루에 몇 종이 비었나» 만 보고
  «한 종목이 며칠째 비었나» 는 안 본다.

## 왜 «개별 종목만» 인가

  DB 를 통째로 부어 봤다가 되돌렸다(2026-08-19). DB 의 local_price 는 **원종가**이고
  랩의 값은 배당·분할조정이라, 이어 붙이면 계단이 생긴다(CAG 5.7% · ZS 8.0%).
  분할은 더 크다(CELG 2:1 → 하루 −49.9%). data/splits.json 은 7종뿐이라 보정할 수 없다.
  ⚠ 그래서 범위를 좁힌다 — **최근에 끊긴 구간만** 메운다. 구간이 짧으면 그 사이에
    분할·배당이 끼어 있을 확률이 낮고, 끼어 있으면 아래 «비율 안정성» 검사가 막는다.

## 무엇을 하나 / 안 하나

  · pxd(종가)만 메운다. **vd·hd·ld 는 안 건드린다** — DB 에 없다.
    ⚠ 그래서 메운 날은 «종가는 있고 고가·저가·거래량은 없는» 날이 된다. 그 날짜를
      파일의 px_repair 에 적어 두므로, 그것을 쓰는 쪽이 사실을 알 수 있다.
  · 🚨 기준을 맞춘다. 끊기기 **직전** 겹침 구간에서 비율 r = 랩/DB 를 내고 그것을 곱한다.
    그 구간의 비율이 흔들리면(분할·배당) **메우지 않는다** — 기준을 못 맞추면 안 넣는다.
  · 🚨 이어 붙인 자리의 인접일 변동이 JUMP_MAX 를 넘으면 그 종목을 통째로 버린다.
  · 이미 값이 있는 칸은 절대 안 덮는다.

    python build/px_repair_db.py --dry-run
    python build/px_repair_db.py
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
SD = os.path.join(DATA, "sd")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DARK_MIN = 1          # 이만큼 연속으로 비면 메울 대상으로 본다(거래일)
# ⚠ 1일 구멍까지 보되 **최근 구간만** 본다(2026-08-19). 17.6년 격자 전체를 대상으로 하면
#   수백 칸을 건드리게 되고, 과거로 갈수록 분할·배당이 끼어 기준 맞춤이 위태롭다.
#   최근이면 DB 커버가 있고(SPX 2020-09~ · NDX 2014-06~) 그 사이 분할 확률도 낮다.
SINCE = "2025-01-01"
# 🚨 창을 짧게 잡는다(2026-08-19). 처음에 30거래일을 봤더니 EQR(리츠)의 비율이 2.9%
#   흔들려 관문에 걸렸다 — 그 창에 **배당락**이 끼었기 때문이다. auto_adjust 의 조정계수는
#   배당 사이에는 상수이고 배당락마다 계단으로 바뀐다. 그래서 «끊기기 직전 며칠» 만 본다.
OVL_MIN = 5           # 비율을 확정하는 데 필요한 «서로 맞는» 겹침 일수
OVL_LOOK = 12         # 그 겹침을 찾으러 거슬러 올라갈 최대 거래일
# ⚠ 이상치를 뺄 여유를 두려면 OVL_MIN 보다 **더 모아야** 한다. 처음엔 딱 5개만 모으고
#   멈춰서, 그중 하나가 이상치면 4개가 되어 늘 거절됐다.
#   ⚠ 그렇다고 멀리 가면 안 된다 — 배당락을 넘으면 그 앞은 다른 기준이라 절반이
#     이상치가 되고, 그때는 «흔들린다» 로 거절되는 것이 맞다(그게 이 검사의 일이다).
OVL_TAKE = 8
OVL_SPREAD = 0.004    # 중앙값에서 이보다 벗어난 날은 이상치로 뺀다
OVL_OUTLIER = 2       # 뺄 수 있는 이상치의 최대 개수
# 🚨 왜 중앙값이고 왜 이상치를 빼나(2026-08-19). 처음엔 «구간 비율의 최대/최소» 로 판정해
#   EQR 을 «분할·배당이 꼈다» 며 거절했다. 실제로 보니 06-29 배당락 뒤로 비율이 정확히
#   1.0000 인데 **07-16 하루만** 1.0186 이었다 — 랩 70.00 vs DB 68.72.
#   즉 흔든 것은 배당이 아니라 **랩 쪽의 잘못된 값 한 칸**이었다.
#   한 칸의 오타가 수리를 막으면, 정작 고쳐야 할 것이 안 고쳐진다.
JUMP_MAX = 12.0       # 이어 붙인 자리의 인접일 변동 상한(%)
IDX = ("SPX Index", "NDX Index")


def gaps(pxd, n):
    """(시작색인, 길이) — 상장 후 생긴 연속 결측 구간 중 DARK_MIN 이상."""
    out, seen, run = [], False, None
    for i in range(min(n, len(pxd))):
        if pxd[i] is not None:
            seen = True
            if run is not None:
                if i - run >= DARK_MIN:
                    out.append((run, i - run))
                run = None
        elif seen and run is None:
            run = i
    if run is not None and min(n, len(pxd)) - run >= DARK_MIN:
        out.append((run, min(n, len(pxd)) - run))
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    import db_load
    import psycopg2

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts = st["pxd_dates"]
    n = len(dts)
    di = {d: i for i, d in enumerate(dts)}
    uni = {s["t"] for s in (st.get("stocks") or []) if s.get("t")}

    broken = {}
    for t in sorted(uni):
        p = os.path.join(SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        pxd = (json.load(io.open(p, encoding="utf-8")) or {}).get("pxd") or []
        g = [(i, k) for i, k in gaps(pxd, n) if dts[i + k - 1] >= SINCE]
        if g:
            broken[t] = g
    print("메울 대상 %d종목 (유니버스 %d · %d거래일 이상 연속 결측 · %s 이후)"
          % (len(broken), len(uni), DARK_MIN, SINCE))
    for t, g in broken.items():
        print("   %-6s %s" % (t, " · ".join("%s~%s(%d일)" % (dts[i], dts[i + k - 1], k)
                                            for i, k in g)))
    if not broken:
        print("메울 것이 없다")
        return 0

    conn = psycopg2.connect(**db_load._conn_params())
    cur = conn.cursor()
    cur.execute("""select split_part(ticker,' ',1) as t, dt, local_price
                     from public.index_constituents
                    where index = any(%s) and local_price is not null
                      and crncy = 'USD' and country = 'US'
                      and split_part(ticker,' ',1) = any(%s)
                    order by 1, 2""", (list(IDX), sorted(broken)))
    db = {}
    for t, dt, p in cur.fetchall():
        db.setdefault(t, {})[str(dt)[:10]] = float(p)
    print("DB 에서 받은 종목 %d개" % len(db))

    fixed, refused = {}, []
    for t, g in broken.items():
        d = db.get(t)
        if not d:
            refused.append((t, "DB 에 없다")); continue
        p = os.path.join(SD, "%s.json" % t)
        obj = json.load(io.open(p, encoding="utf-8"))
        pxd = list(obj.get("pxd") or [])
        pxd += [None] * (n - len(pxd))
        got = []
        for i0, k in g:
            # 끊기기 **직전** 구간에서 비율을 만든다 — 조정계수는 배당 사이에 상수다.
            rs = []
            j, look = i0 - 1, 0
            while j >= 0 and len(rs) < OVL_TAKE and look < OVL_LOOK:
                if pxd[j] is not None and dts[j] in d and d[dts[j]]:
                    rs.append(pxd[j] / d[dts[j]])
                j -= 1
                look += 1
            if len(rs) < OVL_MIN:
                refused.append((t, "겹침 %d일 < %d" % (len(rs), OVL_MIN))); break
            med = sorted(rs)[len(rs) // 2]
            keep = [x for x in rs if med > 0 and abs(x / med - 1) <= OVL_SPREAD]
            drop = len(rs) - len(keep)
            if len(keep) < OVL_MIN or drop > OVL_OUTLIER:
                refused.append((t, "비율이 흔들린다(맞는 날 %d · 벗어난 날 %d) — 분할·배당"
                                % (len(keep), drop)))
                break
            if drop:
                # ⚠ 이상치를 조용히 버리지 않는다 — 몇 칸을 왜 뺐는지 적는다.
                print("  · %-6s 비율 이상치 %d칸 제외(중앙 %.4f)" % (t, drop, med))
            r = sorted(keep)[len(keep) // 2]
            for i in range(i0, i0 + k):
                dd = dts[i]
                if pxd[i] is None and dd in d and d[dd]:
                    pxd[i] = round(d[dd] * r, 4)
                    got.append(dd)
        else:
            if not got:
                refused.append((t, "DB 에도 그 날짜가 없다")); continue
            # 관문 — 이어 붙인 자리에 계단이 생겼나
            bad = None
            for i in range(1, n):
                a, b = pxd[i - 1], pxd[i]
                if a and b and abs(b / a - 1) * 100 > JUMP_MAX:
                    if dts[i] in got or dts[i - 1] in got:
                        bad = (dts[i - 1], dts[i], abs(b / a - 1) * 100)
                        break
            if bad:
                refused.append((t, "계단 %s→%s %.1f%%" % bad)); continue
            fixed[t] = (obj, pxd, got, r)

    print()
    for t, why in refused:
        print("  ✗ %-6s 메우지 않음 — %s" % (t, why))
    for t, (obj, pxd, got, r) in fixed.items():
        print("  ✓ %-6s %d일 메움 (%s ~ %s) · 기준배율 %.4f"
              % (t, len(got), got[0], got[-1], r))
    if dry or not fixed:
        if dry:
            print("\n(--dry-run) 쓰지 않았다")
        return 0

    for t, (obj, pxd, got, r) in fixed.items():
        obj["pxd"] = pxd
        rep = dict(obj.get("px_repair") or {})
        for dd in got:
            rep[dd] = "db"
        obj["px_repair"] = rep
        obj["px_repair_note"] = (
            "이 날짜의 종가는 사내 DB(public.index_constituents)의 원종가를 끊기기 직전 "
            "구간의 비율(랩/DB)로 이 계열의 기준에 맞춰 넣은 것이다. yfinance 가 이 종목을 "
            "주지 않아 생긴 공백을 메운 것이며, **고가·저가·거래량은 그대로 비어 있다** — "
            "DB 에 없기 때문이다. "
            "⚠ 남는 오차: 공백 구간 안에 배당락이 있었다면 그 배당만큼(분기 배당 1회 ≈ 1%) "
            "수준이 어긋난다. 공백 뒤에 실제 값이 없어 그것을 확인할 방법이 없다 — "
            "«없는 것보다 낫다» 를 택한 것이고, 그 사실을 여기 적어 둔다. "
            "build/px_repair_db.py")
        io.open(os.path.join(SD, "%s.json" % t), "w", encoding="utf-8", newline="").write(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    print("\n→ %d종목 수리 · data/sd/ 에 기록(px_repair)" % len(fixed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
