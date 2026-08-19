# -*- coding: utf-8 -*-
"""build/pit_px_db.py — 편출 종목 가격 기록의 **빈 곳을 사내 DB 로 메운다**.

  public.index_constituents  →  data/pit_px.json (병합)

## 왜 있나 (2026-08-19 · 사용자 지시)

  "종목 없는거는 index_constituents db 참고해서 채우라고 했을텐데.
   적어도 최근 1년치는 100% 데이터가 있어야지 지수 둘다"

  편입 원장(constituents.html)의 최근 12개월 커버리지가 SPX 95.8~99.6% · NDX 94.1~99.0%
  였다. 빠진 것은 멤버십이 아니라 **가격**이고, 그 대부분이 «최근 1년 안에 지수를 떠난»
  종목이다 — BK(2026-05 편출) · FI(2025-11) · MMC(2026-01) · K(2025-12) 처럼.
  랩은 오늘의 유니버스(518종)만 매일 받고, 야후는 이 이름들을 잘 주지 않는다
  (실측: BK·MMC 에 "possibly delisted" 를 돌려준다).
  🚨 DB 에는 그 종목이 **지수에 있던 기간의 종가**가 그대로 있다. 그것이 정확히 필요한 값이다.

## 규약 — 공개 저장소에 사내 DB 자료를 싣는다

  ⚠ build/index_ledger.py 머리말에 «사내 DB 는 쓰지 않는다(공개 저장소)» 가 적혀 있었다.
    2026-08-19 사용자 지시로 **빈 곳을 메우는 용도에 한해** 그 제약을 푼다.
    · 싣는 것은 «그 종목이 지수에 있던 날의 종가» 뿐이다 — 이름·섹터·비중·주식수는 안 싣는다.
    · 어느 값이 DB 에서 왔는지 티커별로 적는다(src). 출처를 지우고 섞지 않는다.
    · 접속 자격은 이 저장소에 없다(build/db_load.py 규약 그대로 · 환경변수/연구 repo).

## 자동인가

  ⚠ DB 는 tailnet 안에 있어 러너가 못 닿는다. 이 스크립트는 **DB 가 보이는 PC 에서** 돈다.
    다만 메울 대상은 «지수를 떠난 종목» 이고 그 값은 떠난 뒤로 바뀌지 않는다 —
    한 번 메우면 그 이름은 끝이다. 새 편출이 생길 때만 늘어난다(분기 몇 종).
    러너 쪽 일상 갱신은 build/pit_px_refresh.py 가 야후로 계속 한다.

    python build/pit_px_db.py            # 메운다
    python build/pit_px_db.py --dry-run  # 무엇이 바뀔지만 본다
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pit_px.json")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

IDX = ("SPX Index", "NDX Index")


def sig(x, n=6):
    if x is None:
        return None
    x = float(x)
    if not x or x != x:
        return None
    return round(x, max(0, n - int(math.floor(math.log10(abs(x)))) - 1))


def main() -> int:
    dry = "--dry-run" in sys.argv
    import db_load
    import psycopg2

    rec = {"dates": [], "px": {}}
    if os.path.exists(OUT):
        rec = json.load(io.open(OUT, encoding="utf-8"))
    dates, px = list(rec.get("dates") or []), dict(rec.get("px") or {})
    flat = {t: {dates[v["i0"] + k]: p for k, p in enumerate(v["p"]) if p is not None}
            for t, v in px.items()}

    # 오늘의 랩 유니버스는 매일 따로 받으므로 여기서 안 건드린다.
    today = set()
    try:
        st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        today = {s["t"] for s in (st.get("stocks") or []) if s.get("t")}
    except Exception:
        pass

    # 🚨 **랩이 실제로 쓰는 이름만** 메운다. DB 의 ticker 에는 블룸버그 표기 잡음이 섞여
    #   있다($ANSS$ · AMTM_z · CMCSK 같은 만료·클래스 표기). 그것을 그대로 실으면 랩의
    #   멤버십과 짝이 안 맞는 유령 티커가 기록에 쌓인다.
    #   → 랩의 지수 이력(data/index_history.json)에 실제로 있는 티커로만 좁힌다.
    need = set()
    try:
        import index_members
        mem, _ = index_members.load()
        for _ym, ts in mem.items():
            need |= set(ts)
    except Exception as e:
        raise SystemExit("지수 이력을 못 읽었다(%s) — 좁힐 근거 없이 DB 를 붓지 않는다"
                         % str(e)[:70])
    print("랩 지수 이력 티커 %d종 — 이 안에 있는 것만 메운다" % len(need))

    conn = psycopg2.connect(**db_load._conn_params())
    cur = conn.cursor()
    cur.execute("""select split_part(ticker,' ',1) as t, dt, local_price
                     from public.index_constituents
                    where index = any(%s) and local_price is not null
                    order by 1, 2""", (list(IDX),))
    rows = cur.fetchall()
    print("DB 조회 %d행 (%s)" % (len(rows), " · ".join(IDX)))

    add_t, add_p, seen = set(), 0, set()
    for t, dt, p in rows:
        seen.add(t)
        if t in today or t not in need:
            continue                      # 랩이 매일 받는 종목·랩이 모르는 이름은 건드리지 않는다
        d = str(dt)[:10]
        v = sig(p)
        if v is None:
            continue
        cur_d = flat.setdefault(t, {})
        if d in cur_d:
            continue                      # 🚨 이미 있는 값은 **안 덮는다** — 원천을 섞지 않는다
        cur_d[d] = v
        add_t.add(t)
        add_p += 1
    print("DB 티커 %d종 · 오늘 유니버스 제외 후 보탤 대상 %d종 · 새 관측 %d건"
          % (len(seen), len(add_t), add_p))
    if not add_p:
        print("보탤 것이 없다 — 그대로 둔다")
        return 0
    if dry:
        print("  (--dry-run) 보탤 티커:", " ".join(sorted(add_t)[:20]))
        return 0

    alld = sorted({d for v in flat.values() for d in v})
    idx = {d: i for i, d in enumerate(alld)}
    out, n_pts = {}, 0
    for t, v in sorted(flat.items()):
        a = [None] * len(alld)
        for d, p in v.items():
            a[idx[d]] = p
        lo = next((i for i, x in enumerate(a) if x is not None), None)
        if lo is None:
            continue
        hi = next(i for i in range(len(a) - 1, -1, -1) if a[i] is not None)
        seg = a[lo:hi + 1]
        n_pts += sum(1 for x in seg if x is not None)
        out[t] = {"i0": lo, "p": seg}
    if len(out) < len(px):
        raise SystemExit("❌ 티커가 %d → %d 로 줄었다 — 병합인데 줄 수 없다. 멈춘다."
                         % (len(px), len(out)))

    src = dict(rec.get("src") or {})
    for t in add_t:
        src[t] = "index_constituents"     # 어느 이름이 DB 에서 왔는지 남긴다
    rec.update({
        "coverage": {"start": alld[0], "end": alld[-1], "n_dates": len(alld),
                     "n_tickers": len(out), "n_points": n_pts},
        "src": src, "n_src_db": len(src),
        "src_note": "src 에 적힌 티커는 사내 DB(public.index_constituents)의 «지수에 있던 "
                    "날의 종가» 로 메운 것이다. 이미 있던 값은 덮지 않았다 — 원천을 섞지 않는다.",
        "dates": alld, "px": out,
    })
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s · 티커 %d(DB 로 보탠 것 %d) · %s ~ %s · 관측 %d · %.1fMB"
          % (os.path.relpath(OUT, ROOT), len(out), len(add_t), alld[0], alld[-1],
             n_pts, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
