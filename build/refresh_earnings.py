# -*- coding: utf-8 -*-
"""build/refresh_earnings.py — 실적 발표 일정 → data/earnings.json

무엇을. 앞으로 발표될 실적의 날짜·시간(장전/장후)·컨센서스 EPS를 유니버스(data/stocks.json)에
맞춰 싣는다. 종목 화면에서 '이 종목 언제 발표하나'가 안 보이던 자리를 채운다.

출처. Finnhub `calendar/earnings` — **키 필요**. 저장소 시크릿 FINNHUB_API_KEY로만 읽는다.
  ⚠ 이 저장소는 공개다. 키를 파일·커밋·로그에 남기지 않는다(과거 FRED 키 노출 사고가 있었다).
     로컬 실행:  FINNHUB_API_KEY=... python build/refresh_earnings.py

무료 티어의 실제 한계 — 추측하지 말고 실측한 것만 적는다(2026-07-26 측정).
  · 한 응답이 **1,500건에서 잘린다**. 90일을 한 번에 부르면 정확히 1500건이 와서 뒤가 통째로
    사라지는데, 화면에는 '그날 발표가 없는 것'처럼 보인다. 7일씩 끊어 받으면 5,968건이 된다
    (유니버스 커버리지 184종목 → 481종목).
  · 과거는 **약 30일까지만** 준다. 7일 전 창은 471건이 오지만 90일 전·1년 전·5년 전은 전부 0건.
  · 종목별 stock/earnings는 최근 4분기만 준다.
따라서 과거 서프라이즈 표본(SUE·PEAD)은 이 API로 만들 수 없다.
그래서 발표가 끝난 건은 **여기서 직접 누적**한다(data/earnings_history.json). 오늘부터 쌓아야
언젠가 PEAD 같은 검증이 가능해진다 — 목표주가 이력(target_history.json)과 같은 방식이다.

  python build/refresh_earnings.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "earnings.json")
HIST = os.path.join(DATA, "earnings_history.json")
KEY = (os.getenv("FINNHUB_API_KEY") or "").strip()
BASE = "https://finnhub.io/api/v1/"
AHEAD = 90          # 앞으로 몇 일치를 실을 것인가
BACK = 30           # 과거는 약 30일까지만 응답한다(실측) — 그 창을 매번 통째로 훑어 누적한다


def api(path, **q):
    q["token"] = KEY
    u = BASE + path + "?" + "&".join("%s=%s" % (k, v) for k, v in q.items())
    for attempt in range(4):
        try:
            with urllib.request.urlopen(u, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:          # 분당 호출 제한 — 기다렸다 다시
                time.sleep(8 * (attempt + 1)); continue
            raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3)
    return None


def main() -> int:
    if not KEY:
        print("❌ FINNHUB_API_KEY가 없습니다. 저장소 시크릿에 등록하세요:")
        print("     gh secret set FINNHUB_API_KEY --repo <owner>/<repo>")
        print("   (공개 저장소이므로 키를 파일에 적지 마세요.)")
        return 1

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    uni = {s["t"]: s for s in st["stocks"]}
    # Finnhub는 점 대신 하이픈을 쓴다(BRK.B → BRK-B). 유니버스 대조표를 양방향으로 만든다.
    alias = {}
    for t in uni:
        alias[t] = t
        alias[t.replace(".", "-")] = t

    today = dt.date.today()
    frm = today - dt.timedelta(days=BACK)
    to = today + dt.timedelta(days=AHEAD)
    # ⚠ 응답이 **1,500건에서 잘린다**(실측: 90일 한 번에 = 정확히 1500). 그냥 넓게 부르면
    #   실적 시즌 초반만 담기고 뒤가 통째로 사라지는데, 화면에는 '그날 발표가 없는 것'처럼 보인다.
    #   그래서 7일씩 끊어 받아 합친다(같은 건은 심볼+날짜로 중복 제거).
    rows, seen, capped = [], set(), 0
    cur = frm
    while cur < to:
        nxt_ = min(to, cur + dt.timedelta(days=7))
        r = api("calendar/earnings", **{"from": str(cur), "to": str(nxt_)})
        chunk = (r or {}).get("earningsCalendar") or []
        if len(chunk) >= 1500:
            capped += 1
        for x in chunk:
            k = (x.get("symbol"), x.get("date"))
            if k not in seen:
                seen.add(k); rows.append(x)
        cur = nxt_
        time.sleep(1.1)          # 무료 티어 분당 제한 회피
    print("응답 %d건 (%s ~ %s)%s"
          % (len(rows), frm, to, ("  ⚠ 상한에 닿은 구간 %d개" % capped) if capped else ""))

    HOUR = {"bmo": "장전", "amc": "장후", "dmh": "장중", "": ""}
    up, recent = [], []
    for x in rows:
        sym = (x.get("symbol") or "").strip()
        t = alias.get(sym)
        if not t:
            continue                     # 유니버스 밖은 싣지 않는다
        d = x.get("date")
        if not d:
            continue
        rec = {
            "t": t, "n": uni[t].get("name") or t, "s": uni[t].get("sector") or "",
            "dt": d, "hour": HOUR.get((x.get("hour") or "").lower(), x.get("hour") or ""),
            "q": x.get("quarter"), "y": x.get("year"),
            "est": x.get("epsEstimate"), "act": x.get("epsActual"),
            "rest": x.get("revenueEstimate"), "ract": x.get("revenueActual"),
        }
        (recent if d < str(today) else up).append(rec)
    up.sort(key=lambda z: (z["dt"], z["t"]))
    recent.sort(key=lambda z: (z["dt"], z["t"]), reverse=True)

    # ── 이력 누적 ── 무료 티어는 과거를 안 준다. 지나간 건을 매번 붙여 두어야 표본이 생긴다.
    hist = {}
    if os.path.exists(HIST):
        try:
            hist = json.load(io.open(HIST, encoding="utf-8")).get("rows") or {}
        except Exception:
            hist = {}
    added = 0
    for z in recent:
        if z.get("act") is None:
            continue
        k = "%s|%s" % (z["t"], z["dt"])
        if k not in hist:
            added += 1
        # 실제치가 나중에 정정될 수 있어 항상 최신으로 덮는다
        hist[k] = {"t": z["t"], "dt": z["dt"], "q": z["q"], "y": z["y"],
                   "est": z["est"], "act": z["act"]}
    json.dump({"note": "지나간 실적 발표의 컨센서스·실제 누적. Finnhub 무료 티어가 과거를 주지 않아 "
                       "여기서 직접 쌓는다 — 이 파일이 두꺼워져야 서프라이즈 검증이 가능해진다.",
               "as_of": str(today), "n": len(hist), "rows": hist},
              io.open(HIST, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # 다음 발표일까지 남은 일수 — 화면이 계산하지 않게 여기서 준다
    nxt = {}
    for z in up:
        if z["t"] not in nxt:
            nxt[z["t"]] = z["dt"]
    doc = {
        "note": "실적 발표 일정. 유니버스(data/stocks.json) 종목만 싣는다. "
                "컨센서스 EPS는 발표 전 추정치이며 사후에 바뀔 수 있다.",
        "source": "Finnhub calendar/earnings",
        "as_of": str(today), "window": {"from": str(frm), "to": str(to)},
        "n_upcoming": len(up), "n_recent": len(recent), "n_history": len(hist),
        "limits": [
            "한 번의 응답이 1,500건에서 잘린다(실측). 넓은 구간을 한 번에 부르면 뒤쪽이 통째로 "
            "빠지는데 화면에는 '발표가 없는 날'처럼 보이므로, 7일씩 끊어 받아 합친다.",
            "과거는 약 30일까지만 응답한다(실측: 7일 전 471건 · 90일 전 0건 · 1년 전 0건). "
            "그래서 지나간 건은 이 스크립트가 직접 누적한다(data/earnings_history.json) — "
            "그 파일이 두꺼워져야 서프라이즈 검증(SUE·PEAD)이 언젠가 가능해진다.",
            "발표 일정은 회사가 바꾼다. 여기 날짜는 조회 시점의 예정일이며 확정이 아니다.",
            "컨센서스 EPS는 조정 EPS 기준이 많고 회사·집계기관마다 정의가 다르다 — "
            "GAAP 순이익과 직접 비교하지 말 것.",
        ],
        "upcoming": up, "recent": recent[:120], "next": nxt,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("예정 %d건 · 최근 %d건 · 누적 이력 %d건(신규 %d) · 유니버스 %d종목 중 %d종목"
          % (len(up), len(recent), len(hist), added, len(uni), len(nxt)))
    if up[:3]:
        for z in up[:3]:
            print("   %s %-6s %s %s" % (z["dt"], z["t"], z["hour"], z["n"][:26]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
