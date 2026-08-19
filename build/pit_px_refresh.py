# -*- coding: utf-8 -*-
"""build/pit_px_refresh.py — 편출 종목 가격 기록(data/pit_px.json)을 **자동으로** 이어 붙인다.

## 왜 있나 (2026-08-19)

  전날 style_pit 을 러너로 들여오면서 data/pit_px.json 을 커밋했다. 그때 나는
  «편출된 종목의 과거 가격은 앞으로 바뀌지 않으니 새 이름이 편출될 때만 손으로 다시
  구우면 된다» 고 적었다. 사용자가 답했다 — "자동이 아니면 내가 일일이 관리할수가 없어."
  맞는 말이었고, 재 보니 **전제부터 틀렸다.**

  🚨 기록에 든 154종 중 **143종의 가격이 같은 날(2026-08-10)에 끝난다.** 죽은 종목이
    아니라 «지수에서 빠졌을 뿐 지금도 거래되는» 회사들이다(AA 알코아 · AAL 아메리칸항공 ·
    ALK 알래스카항공 …). 즉 이 파일은 «변하지 않는 기록» 이 아니라 **매일 낡는 자료**다.
    손으로 관리할 대상이 애초에 아니었다.

  ⚠ 그리고 이 154종은 랩의 어느 일간 피드에도 없다 — stocks.json(518종) · assets.json(65계열) ·
    data/sd/(518파일) 어디에도 0종이다. 여기서 안 받으면 아무도 안 받는다.

## 무엇을 하나 / 안 하나

  · 필요한 티커 = 기록에 이미 있는 것 ∪ (지수 이력에 있었는데 오늘 유니버스엔 없는 것).
    뒤쪽이 «새로 편출된 이름» 을 자동으로 데려온다 — 사람이 알아챌 필요가 없다.
  · 이미 있는 티커는 **마지막 날짜 다음부터만** 받는다. 새 티커는 전체를 받는다.
  · 🚨 **병합만 한다. 절대 줄이지 않는다.** yfinance 가 상장폐지된 이름을 더는 안 주는 날이
    와도(실제로 온다) 저장소에 있는 기록은 그대로 남는다. 이름 하나가 조용히 사라지면
    PIT 후보가 생존자 쪽으로 기울고, 그러면 «생존편향을 재는 표» 가 스스로 생존편향을 갖는다.
  · 🚨 한 종목도 못 받으면 **쓰지 않고 죽는다.** 병합 구조라 산출물은 겉보기에 멀쩡하다 —
    여기서 안 막으면 «잡은 초록인데 자료는 안 움직인다» 가 그대로 숨는다(2026-08-19 에
    고객 집중도에서 정확히 그 사고를 냈다).

    python build/pit_px_refresh.py
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

START = "2009-01-01"          # 기록의 시작 — pit_backtest.CACHE_START 과 같다


def sig(x, n=6):
    """유효숫자 n자리. 🚨 소수 자리로 자르면 안 된다 — 이 바구니의 가격은 $0.015 부터다."""
    if not x or x != x:
        return None
    return round(float(x), max(0, n - int(math.floor(math.log10(abs(float(x))))) - 1))


# 🚨 «영영 못 받는 이름» 을 기억한다(2026-08-19 실측). 첫 실행에서 334종을 물었더니
#   187종이 실패했다 — YHOO·UTX·WFM·ANTM 처럼 오래 전에 합병·상장폐지돼 yfinance 가
#   더는 주지 않는 이름들이다. 매일 다시 묻는 것은 낭비이고, 매일 «못 받았다» 를 찍는 것은
#   **더 나쁘다** — 고칠 수 없는 경고가 매일 뜨면 사람이 경고 전체를 안 믿게 된다.
#   그래서 포기한 날을 적어 두고 RETRY_DAYS 마다 한 번만 다시 물어본다.
RETRY_DAYS = 30
# 🚨 한 번 실패를 «영영» 으로 적지 않는다(2026-08-19 실측). 334종을 한 번에 훑은 직후
#   BK·MMC·FI 같은 **세계 최대 대형주**에도 야후가 "possibly delisted" 를 돌려줬다 —
#   상장폐지가 아니라 **쓰로틀**이다. 그것을 «영영 못 받는 이름» 으로 적으면 멀쩡한
#   종목이 30일간 기록에서 빠지고, 그 사이 PIT 후보가 조용히 좁아진다.
#   → 연속 FAIL_STREAK 번 실패해야 «영영» 으로 본다. 한 번이라도 받아지면 0 으로 되돌린다.
FAIL_STREAK = 3


def wanted():
    """받아야 할 티커 — 기록에 있는 것 ∪ (지수 이력에 있었는데 오늘 유니버스엔 없는 것).

    ⚠ «영영 못 받는» 목록에 있고 아직 RETRY_DAYS 가 안 지난 이름은 뺀다.
    """
    have, never = set(), {}
    if os.path.exists(OUT):
        _o = json.load(io.open(OUT, encoding="utf-8"))
        have = set(_o.get("px") or {})
        # never[t] = {"since": 포기한 날, "n": 연속 실패 횟수}. 옛 판(문자열)도 읽는다.
        for t, v in (_o.get("never") or {}).items():
            never[t] = v if isinstance(v, dict) else {"since": str(v), "n": FAIL_STREAK}
    today = set()
    try:
        st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        today = {s["t"] for s in (st.get("stocks") or []) if s.get("t")}
    except Exception:
        pass
    gone = set()
    try:
        import index_members
        mem, _ = index_members.load()
        for _ym, ts in mem.items():
            gone |= set(ts)
        gone -= today
    except Exception as e:
        print("  ⚠ 지수 이력을 못 읽었다(%s) — 기록에 있는 것만 갱신한다" % str(e)[:60])
    want = have | gone
    import datetime as _dt
    today = _dt.date.today()
    skip = set()
    for t, d in never.items():
        if t in have:
            continue                       # 기록이 있으면 계속 받아 본다(오늘 값이 필요하다)
        if (d.get("n") or 0) < FAIL_STREAK:
            continue                       # 아직 «영영» 이라 부를 근거가 모자란다 — 또 물어본다
        try:
            if (today - _dt.date.fromisoformat(str(d.get("since"))[:10])).days < RETRY_DAYS:
                skip.add(t)
        except Exception:
            pass
    return sorted(want - skip), len(have), len(gone - have - skip), skip, never


def main() -> int:
    import pandas as pd                                   # noqa: F401
    import yfinance as yf

    tick, n_have, n_new, skipped, never = wanted()
    if not tick:
        print("❌ 받을 티커가 없다")
        return 1
    rec = {"dates": [], "px": {}}
    if os.path.exists(OUT):
        rec = json.load(io.open(OUT, encoding="utf-8"))
    dates, px = list(rec.get("dates") or []), dict(rec.get("px") or {})
    # 기존 기록을 {티커: {날짜: 값}} 으로 편다(병합하기 쉬운 모양).
    flat = {t: {dates[v["i0"] + k]: p for k, p in enumerate(v["p"]) if p is not None}
            for t, v in px.items()}
    last = max(dates) if dates else None
    print("기록 %d종(마지막 %s) · 새로 데려올 이름 %d종 · 받을 대상 %d종"
          % (n_have, last, n_new, len(tick)))
    if skipped:
        print("  (영영 못 받는 %d종은 %d일마다 한 번만 다시 묻는다 — 오늘은 건너뜀)"
              % (len(skipped), RETRY_DAYS))

    # ⚠ 이미 있는 이름은 마지막 날짜부터만 받는다(하루 겹치게 — 경계에서 빠지지 않게).
    frm = last if last else START
    got, miss = 0, []
    for i in range(0, len(tick), 60):                     # yfinance 는 묶음이 클수록 잘 흘린다
        batch = tick[i:i + 60]
        try:
            df = yf.download(batch, start=frm, progress=False, auto_adjust=True,
                             threads=False, group_by="column")
        except Exception as e:
            print("  ⚠ 묶음 %d 실패: %s" % (i // 60 + 1, str(e)[:70]))
            continue
        if df is None or df.empty:
            continue
        cl = df["Close"] if "Close" in df else df
        for t in batch:
            try:
                s = cl[t] if t in getattr(cl, "columns", []) else (cl if len(batch) == 1 else None)
            except Exception:
                s = None
            if s is None:
                miss.append(t); continue
            d = {str(k)[:10]: sig(v) for k, v in s.items() if v == v}
            d = {k: v for k, v in d.items() if v is not None}
            if not d:
                miss.append(t); continue
            flat.setdefault(t, {}).update(d)              # 🚨 병합만 — 기존 값을 지우지 않는다
            got += 1
        print("  … %d/%d종 · 받은 종목 %d" % (min(i + 60, len(tick)), len(tick), got), flush=True)

    if got == 0:
        raise SystemExit("❌ 한 종목도 받지 못했다 — 기록을 쓰지 않고 멈춘다. "
                         "병합 구조라 그냥 쓰면 «잡은 초록인데 자료는 그대로» 가 숨는다.")

    import datetime as _dt2
    _stamp = _dt2.date.today().isoformat()
    for t in miss:
        e = never.get(t) or {"since": _stamp, "n": 0}
        e["n"] = (e.get("n") or 0) + 1
        e["since"] = _stamp
        never[t] = e
    for t in flat:
        never.pop(t, None)                 # 한 번이라도 받아졌으면 «영영» 목록에서 뺀다
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

    doc = {
        "note": "편출·상장폐지 종목의 일별 종가 기록. build/pit_px_refresh.py 가 매일 이어 "
                "붙인다. 🚨 이 154여 종은 랩의 어느 일간 피드에도 없다 — 여기서 안 받으면 "
                "아무도 안 받는다. 병합만 하고 절대 줄이지 않는다: 벤더가 상장폐지된 이름을 "
                "더는 안 주는 날이 와도 기록은 남아야 «생존편향을 재는 표» 가 스스로 "
                "생존편향을 갖지 않는다.",
        "source": "yfinance (auto_adjust=True) · 최초 기록은 data/_pit_px_cache.json 에서 옮겼다",
        "coverage": {"start": alld[0], "end": alld[-1], "n_dates": len(alld),
                     "n_tickers": len(out), "n_points": n_pts},
        # 🚨 이 목록이 있어야 매일 187종을 헛되이 묻고 «못 받았다» 를 찍지 않는다.
        #   고칠 수 없는 경고를 매일 띄우면 사람이 경고 전체를 안 믿게 된다.
        "never": never,
        "n_never": len(never),
        "dates": alld,
        "px": out,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s · 티커 %d(이번에 받은 것 %d · 못 받은 것 %d) · %s ~ %s · %.1fMB"
          % (os.path.relpath(OUT, ROOT), len(out), got, len(miss), alld[0], alld[-1],
             os.path.getsize(OUT) / 1e6))
    # 못 받은 이름을 둘로 가른다 — 다른 뜻이라 같이 찍으면 둘 다 안 읽힌다.
    #   ① 기록이 있는데 오늘 못 받았다 → 벤더가 오늘 안 줬다. 값어치 있는 경고다.
    #   ② 기록도 없고 못 받는다 → 오래 전에 사라진 이름. 세어서 한 줄, 그리고 기억한다.
    warn = [t for t in miss if t in out]
    lost = [t for t in miss if t not in out]
    if warn:
        print("  ⚠ 기록이 있는데 오늘 못 받은 이름 %d종(기록은 유지): %s"
              % (len(warn), " ".join(sorted(warn)[:12])))
    if lost:
        firm = [t for t in lost if (never.get(t, {}).get("n") or 0) >= FAIL_STREAK]
        print("  · 못 받은 옛 이름 %d종(그중 %d종은 %d회 연속 실패 — %d일 뒤 다시 묻는다). "
              "나머지는 쓰로틀일 수 있어 내일 또 물어본다"
              % (len(lost), len(firm), FAIL_STREAK, RETRY_DAYS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
