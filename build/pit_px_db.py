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


def _daydiff(a, b):
    import datetime as _d
    return abs((_d.date.fromisoformat(a) - _d.date.fromisoformat(b)).days)


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
    # 🚨 통화·국가로 거른다. 전체 106만행 중 6.5만행이 crncy/country 가 NULL 인데
    #   (2014~2018 옛 행들), 그것을 그대로 실으면 어느 통화인지 모르는 값을 섞게 된다.
    #   USD/US 만 쓴다 — 이 랩의 가격은 전부 USD 다.
    cur.execute("""select split_part(ticker,' ',1) as t, dt, local_price
                     from public.index_constituents
                    where index = any(%s) and local_price is not null
                      and crncy = 'USD' and country = 'US'
                    order by 1, 2""", (list(IDX),))
    rows = cur.fetchall()
    print("DB 조회 %d행 (%s)" % (len(rows), " · ".join(IDX)))

    # 🚨 기준을 맞춘다(2026-08-19). DB 의 local_price 는 **원종가**이고 이 기록의 값은
    #   yfinance auto_adjust(배당조정)다. 그대로 이어 붙이면 이어진 자리에 계단이 생긴다 —
    #   실측 CAG 5.74% · CPB 5.05% · ZS 7.95%. 배당수익률이 높을수록, 과거로 갈수록 커진다.
    #   → 두 원천이 **같은 날 값을 가진 날**로 비율 r = 기록/DB 를 만들고, 채울 날짜에서
    #     가장 가까운 겹침일의 r 을 곱한다. 조정계수는 배당 사이에 상수라 최근접이 맞다.
    #   ⚠ 겹치는 날이 MIN_OVL 미만이면 그 티커는 **건너뛴다** — 기준을 못 맞추면 안 넣는다.
    MIN_OVL = 20
    by_t = {}
    seen = set()
    for t, dt, p in rows:
        seen.add(t)
        if t in today or t not in need:
            continue
        v = sig(p)
        if v is not None:
            by_t.setdefault(t, {})[str(dt)[:10]] = v

    add_t, add_p, skip_ovl, raw_t = set(), 0, [], set()
    for t, db in by_t.items():
        cur_d = flat.setdefault(t, {})
        ovl = sorted(d for d in db if d in cur_d)
        if cur_d and len(ovl) < MIN_OVL:
            skip_ovl.append(t)             # 기존 값이 있는데 기준을 맞출 겹침이 모자란다
            continue
        if not cur_d:
            raw_t.add(t)                   # 기존 값이 없다 → DB 단독 계열(원종가 기준)
        ratios = [(d, cur_d[d] / db[d]) for d in ovl if db[d]]
        for d, v in sorted(db.items()):
            if d in cur_d:
                continue                   # 이미 있는 값은 안 덮는다
            if ratios:
                # 가장 가까운 겹침일의 비율
                r = min(ratios, key=lambda x: abs((x[0] > d) - 0.5) if False else _daydiff(x[0], d))[1]
                v = sig(v * r)
            cur_d[d] = v
            add_t.add(t)
            add_p += 1
    print("DB 티커 %d종(USD/US) · 보탤 대상 %d종 · 새 관측 %d건 "
          "· 기준 못 맞춰 건너뛴 %d종 · DB 단독(원종가) %d종"
          % (len(seen), len(add_t), add_p, len(skip_ovl), len(raw_t)))
    if skip_ovl:
        print("  · 겹침 %d일 미만이라 건너뜀: %s" % (MIN_OVL, " ".join(sorted(skip_ovl)[:12])))
    if not add_p:
        print("보탤 것이 없다 — 그대로 둔다")
        return 0
    if dry:
        print("  (--dry-run) 보탤 티커:", " ".join(sorted(add_t)[:20]))
        return 0

    # 🚨 관문 — 이어 붙인 자리에 계단이 생겼나(2026-08-19). 첫 판에서 이 검사가 없어
    #   원종가를 배당조정 계열에 그대로 붙였고, CAG 5.7% · ZS 8.0% 짜리 가짜 하루 변동이
    #   기록에 들어갔다. 산출물은 겉보기에 멀쩡했다 — 검사가 없으면 아무도 모른다.
    # ⚠ **인접 거래일**만 본다. 계열이 몇 년 비어 있다가 이어지는 것은 계단이 아니라 공백이다
    #   (첫 판에서 그것을 494% 계단으로 잘못 읽었다 — SPLS 2015 → 2026).
    JUMP_MAX, JUMP_GAP = 12.0, 5          # %  ·  며칠 이내를 «인접» 으로 볼 것인가
    bad = []
    for t in sorted(add_t):
        ds = sorted(flat[t])
        for i in range(1, len(ds)):
            if _daydiff(ds[i - 1], ds[i]) > JUMP_GAP:
                continue
            p0, p1 = flat[t][ds[i - 1]], flat[t][ds[i]]
            if not p0:
                continue
            mv = abs(p1 / p0 - 1) * 100
            if mv > JUMP_MAX:
                bad.append((mv, t, ds[i - 1], ds[i]))
    bad.sort(reverse=True)
    if bad:
        for mv, t, d0, d1 in bad[:10]:
            print("  🚨 %-6s %s → %s  %.1f%%" % (t, d0, d1, mv))
        raise SystemExit("❌ 인접 거래일 %.0f%% 초과 변동 %d건 — 기준이 안 맞은 것이다. "
                         "기록을 쓰지 않고 멈춘다." % (JUMP_MAX, len(bad)))

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
