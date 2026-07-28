# -*- coding: utf-8 -*-
"""build/refresh_earnings.py — 실적 발표 일정 → data/earnings.json

무엇을. 앞으로 발표될 실적의 날짜·시간(장전/장후)·컨센서스 EPS를 유니버스(data/stocks.json)에
맞춰 싣는다. 종목 화면에서 '이 종목 언제 발표하나'가 안 보이던 자리를 채운다.

출처. Finnhub `calendar/earnings` — **키 필요**. 저장소 시크릿 FINNHUB_API_KEY로만 읽는다.
  ⚠ 이 저장소는 공개다. 키를 파일·커밋·로그에 남기지 않는다(과거 FRED 키 노출 사고가 있었다).
     로컬 실행:  FINNHUB_API_KEY=... python build/refresh_earnings.py
2차 소스. Nasdaq `calendar/earnings`(키 없음) — 날짜 교차검증용. 한쪽만 믿으면 안 되는 이유는
  아래 '실제 한계' 마지막 항목에 적었다.

무료 티어의 실제 한계 — 추측하지 말고 실측한 것만 적는다(2026-07-26 측정).
  · 한 응답이 **1,500건에서 잘린다**. 90일을 한 번에 부르면 정확히 1500건이 와서 뒤가 통째로
    사라지는데, 화면에는 '그날 발표가 없는 것'처럼 보인다. 7일씩 끊어 받으면 5,968건이 된다
    (유니버스 커버리지 184종목 → 481종목).
    ⚠ 7일도 실적 시즌 피크에는 부족하다 — 2026-07-28 실행에서 1개 구간이 상한에 닿았다.
    고정 폭을 더 줄이면 한산한 구간까지 호출만 늘어나므로, **닿은 구간만 반으로 쪼개
    다시 받는다**(fetch_span). 하루로 좁혀도 닿으면 그 날짜를 로그에 찍는다.
  · 과거는 **약 30일까지만** 준다. 7일 전 창은 471건이 오지만 90일 전·1년 전·5년 전은 전부 0건.
  · 종목별 stock/earnings는 최근 4분기만 준다.
  · **회사가 확정하지 않은 종목에 추정 날짜를 넣어 주면서 확정과 구분해 주지 않는다.**
    그 추정은 실제보다 이른 쪽으로 틀린다 — 2026-07-28 실측으로 창 안 451종목 중 55종목이
    Nasdaq과 어긋났고 **55건 전부 Finnhub이 이른 쪽**이었다(반대 방향 0건). 이르게 틀리면
    발표가 없었는데도 지나간 칸에 남아 화면이 '그날 발표했다'고 말한다(EA 7/27 → 실제 8/4).
    그래서 Nasdaq으로 교차검증하고, 어긋나면 늦은 쪽에 놓고 밀어낸 날짜를 alt 에 남긴다.
따라서 과거 서프라이즈 표본(SUE·PEAD)은 이 API로 만들 수 없다.
그래서 발표가 끝난 건은 **여기서 직접 누적**한다(data/earnings_history.json). 오늘부터 쌓아야
언젠가 PEAD 같은 검증이 가능해진다 — 목표주가 이력(target_history.json)과 같은 방식이다.

  python build/refresh_earnings.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys, time, urllib.error, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "earnings.json")
HIST = os.path.join(DATA, "earnings_history.json")
KEY = (os.getenv("FINNHUB_API_KEY") or "").strip()
BASE = "https://finnhub.io/api/v1/"
AHEAD = 90          # 앞으로 몇 일치를 실을 것인가
BACK = 30           # 과거는 약 30일까지만 응답한다(실측) — 그 창을 매번 통째로 훑어 누적한다
CAP = 1500          # 한 응답의 상한(실측). 이 수에 닿으면 잘렸다고 본다
CHUNK = 7           # 기본 청크(일). 닿은 구간만 반씩 쪼갠다 — fetch_span 참조

# ── 2차 소스(Nasdaq) 교차검증 창 ──────────────────────────────────────────
# 홈 캘린더가 그리는 구간(지난 1주+앞으로 3주)과 '다음 발표일'을 덮을 만큼만 본다.
# 90일을 다 훑어도 되지만 하루 한 콜이라 그만큼 느려지고, 먼 미래는 어차피 양쪽 다 추정이다.
XC_BACK, XC_AHEAD = 7, 60
# 2차 소스는 티커마다 '다음 발표' 하나만 준다. Finnhub 행은 분기마다 있으므로 **같은 발표를
# 가리키는 행 하나**에만 대조해야 한다. 이만큼 넘게 떨어져 있으면 다른 분기로 본다 —
# 안 두면 다음 분기 행까지 전부 불일치로 세어 26건이 193건이 된다(실측).
XC_TOL = 21
NAS_URL = "https://api.nasdaq.com/api/calendar/earnings?date=%s"
NAS_UA = "Mozilla/5.0"          # 기본 파이썬 UA로 부르면 403이 온다
NAS_HOUR = {"time-pre-market": "장전", "time-after-hours": "장후"}   # time-not-supplied → 미공개


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


def fetch_span(a, b, rows, seen, st):
    """[a, b] 을 한 번에 받고, 상한에 닿으면 반으로 쪼개 다시 받는다.

    7일 고정으로는 부족하다 — 실적 시즌 피크에서 실제로 닿았다(2026-07-28 실행, 1개 구간).
    닿은 구간은 뒤쪽이 잘려 나가는데 화면에는 '그날 발표가 없는 것'처럼 보인다.
    한산한 구간까지 무조건 잘게 쪼개면 호출만 늘어나므로, **닿은 구간만** 쪼갠다.
    """
    r = api("calendar/earnings", **{"from": str(a), "to": str(b)})
    st["calls"] += 1
    time.sleep(1.1)              # 무료 티어 분당 제한 회피 — 쪼개기 전에 쉰다
    chunk = (r or {}).get("earningsCalendar") or []
    if len(chunk) >= CAP:
        if a < b:
            mid = a + (b - a) // 2
            st["split"] += 1
            fetch_span(a, mid, rows, seen, st)
            fetch_span(mid + dt.timedelta(days=1), b, rows, seen, st)
            return
        st["capped"].append(str(a))   # 하루짜리인데도 상한 — 더 쪼갤 수 없다
    for x in chunk:
        k = (x.get("symbol"), x.get("date"))
        if k not in seen:
            seen.add(k); rows.append(x)


def nasdaq_calendar(frm, to):
    """Nasdaq 일자별 실적 캘린더 → ({심볼: (날짜, 시각)}, 받은 영업일수, 실패일수).

    왜 2차 소스가 필요한가 — Finnhub 무료 티어는 회사가 날짜를 확정하지 않은 종목에
    **추정 날짜**를 넣어 주는데, 확정된 것과 구분할 표시가 없다. 그 추정이 실제보다 이르면
    (실측한 불일치 26건 중 23건이 이른 쪽이었다) 발표가 없었는데도 지나간 칸에 남는다.
    실제로 EA가 그랬다 — Finnhub 7/27(실제치 없음) vs Nasdaq 8/4.

    Nasdaq은 날짜별로 그날 전체를 한 번에 주므로 창 전체가 수십 콜이면 끝난다.
    """
    out, days, fails = {}, 0, 0
    d = frm
    while d <= to:
        if d.weekday() < 5:                      # 주말은 응답이 비어 있다 — 부르지 않는다
            try:
                req = urllib.request.Request(NAS_URL % d,
                                             headers={"User-Agent": NAS_UA,
                                                      "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    rows = ((json.load(r).get("data") or {}).get("rows")) or []
                for x in rows:
                    s = (x.get("symbol") or "").strip().upper()
                    if s and s not in out:       # 창 안에서 **처음 나오는** 날짜가 다음 발표다
                        out[s] = (str(d), NAS_HOUR.get(x.get("time") or "", ""))
                days += 1
            except Exception:
                fails += 1                       # 하루 실패는 넘어간다. 전멸이면 아래에서 판정한다
            time.sleep(0.4)
        d += dt.timedelta(days=1)
    return out, days, fails


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
    #   7일씩 끊어 받되, 상한에 닿은 구간은 반으로 쪼개 다시 받는다(같은 건은 심볼+날짜로 중복 제거).
    rows, seen = [], set()
    st = {"calls": 0, "split": 0, "capped": []}
    cur = frm
    while cur < to:
        nxt_ = min(to, cur + dt.timedelta(days=CHUNK))
        fetch_span(cur, nxt_, rows, seen, st)
        cur = nxt_
    print("응답 %d건 (%s ~ %s) · 호출 %d회%s"
          % (len(rows), frm, to, st["calls"],
             (" · 상한에 닿아 쪼갠 구간 %d개" % st["split"]) if st["split"] else ""))
    if st["capped"]:
        # 하루로 좁혀도 1,500건이면 더 쪼갤 단위가 없다. 그 날은 뒤쪽이 빠진 채로 실린다 —
        # 조용히 넘어가면 '그날 발표가 적은 것'으로 보이므로 날짜를 찍어 둔다.
        print("⚠ 하루 단위인데도 상한에 닿은 날 %d일: %s — 그 날의 일부가 빠졌을 수 있다"
              % (len(st["capped"]), ", ".join(st["capped"][:8])))

    # ── 2차 소스 교차검증 ──────────────────────────────────────────────
    NAS, nas_days, nas_fails = nasdaq_calendar(today - dt.timedelta(days=XC_BACK),
                                               today + dt.timedelta(days=XC_AHEAD))
    if nas_days:
        print("Nasdaq 교차검증 %d영업일 수집(실패 %d일) · 심볼 %d개" % (nas_days, nas_fails, len(NAS)))
    else:
        # 조용히 지나가면 '검증했는데 다 맞았다'로 읽힌다 — 그건 검증이 없는 것보다 나쁘다.
        print("⚠ Nasdaq 교차검증 실패 — Finnhub 단독으로 싣는다(날짜 보정·시각 보강 없음)")

    def nas_of(t):
        return NAS.get(t) or NAS.get(t.replace(".", "-")) or NAS.get(t.replace("-", "."))

    HOUR = {"bmo": "장전", "amc": "장후", "dmh": "장중", "": ""}
    recs = []
    for x in rows:
        sym = (x.get("symbol") or "").strip()
        t = alias.get(sym)
        if not t:
            continue                     # 유니버스 밖은 싣지 않는다
        d = x.get("date")
        if not d:
            continue
        recs.append({
            "t": t, "n": uni[t].get("name") or t, "s": uni[t].get("sector") or "",
            "dt": d, "hour": HOUR.get((x.get("hour") or "").lower(), x.get("hour") or ""),
            "q": x.get("quarter"), "y": x.get("year"),
            "est": x.get("epsEstimate"), "act": x.get("epsActual"),
            "rest": x.get("revenueEstimate"), "ract": x.get("revenueActual"),
        })

    # ── 대조 ── 티커마다 2차 소스의 날짜에 **가장 가까운 행 하나**만 본다.
    xc_lo = str(today - dt.timedelta(days=XC_BACK))
    xc_hi = str(today + dt.timedelta(days=XC_AHEAD))
    n_both = n_moved = n_hour = n_only = 0
    if nas_days:
        by_t = {}
        for i, rec in enumerate(recs):
            if xc_lo <= rec["dt"] <= xc_hi:          # 창 밖은 대조하지 않는다(src를 안 붙인다)
                by_t.setdefault(rec["t"], []).append(i)
        for t, idxs in by_t.items():
            nz = nas_of(t)
            if not nz:
                for i in idxs:
                    recs[i]["src"] = "finnhub"       # 2차 소스에 없다 — 교차검증 안 됨
                continue
            nd, nh = nz
            gap = lambda i: abs((dt.date.fromisoformat(recs[i]["dt"]) -
                                 dt.date.fromisoformat(nd)).days)
            i = min(idxs, key=gap)
            if gap(i) > XC_TOL:                      # 다른 분기다 — 대조 대상이 아니다
                for j in idxs:
                    recs[j]["src"] = "finnhub"
                continue
            rec = recs[i]
            if nh and not rec["hour"]:
                rec["hour"] = nh; n_hour += 1        # Finnhub이 시각을 안 준 것을 채운다
            if nd == rec["dt"]:
                rec["src"] = "both"; n_both += 1
            else:
                # 늦은 쪽에 놓는다. 실제보다 이른 날짜는 '발표가 없었는데 지나간 칸에 남는'
                # 형태로 굳는데(EA가 그랬다), 늦은 쪽은 아직 앞에 있으므로 다음 갱신이 고칠 수
                # 있다. 어느 쪽이 옳은지는 여기서 알 수 없으므로 밀어낸 날짜를 alt 로 남긴다.
                rec["src"] = "conflict"; rec["alt"] = min(rec["dt"], nd)
                rec["dt"] = max(rec["dt"], nd); n_moved += 1

    up, recent = [], []
    for rec in recs:
        (recent if rec["dt"] < str(today) else up).append(rec)

    # ── 2차 소스에만 있는 유니버스 종목 ──────────────────────────────────
    # Finnhub이 통째로 빠뜨린 것이 있다(실측 17종목 — PLTR·MAR·BRK.B 등). 화면에는
    # '그날 발표가 없는 것'으로 보이므로 채운다. 지난 날짜는 넣지 않는다 — 실제치가
    # 없는 과거 행을 만들면 우리가 고치려는 그 문제를 우리 손으로 만드는 셈이다.
    if nas_days:
        have = {z["t"] for z in up} | {z["t"] for z in recent}
        for t in sorted(uni):
            if t in have:
                continue
            nz = nas_of(t)
            if not nz or nz[0] < str(today):
                continue
            up.append({"t": t, "n": uni[t].get("name") or t, "s": uni[t].get("sector") or "",
                       "dt": nz[0], "hour": nz[1], "q": None, "y": None,
                       "est": None, "act": None, "rest": None, "ract": None,
                       "src": "nasdaq"})
            n_only += 1
    print("  일치 %d · 날짜 불일치(늦은 쪽 채택) %d · 시각 보강 %d · 2차 소스에만 있어 추가 %d"
          % (n_both, n_moved, n_hour, n_only))

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
        "source": "Finnhub calendar/earnings + Nasdaq calendar/earnings 교차검증",
        "as_of": str(today), "window": {"from": str(frm), "to": str(to)},
        "n_upcoming": len(up), "n_recent": len(recent), "n_history": len(hist),
        # 행마다 src 가 붙는다 — both(두 소스 일치) · conflict(불일치, 늦은 쪽 채택하고 alt 에
        # 밀어낸 날짜) · finnhub/nasdaq(한쪽에만 있어 교차검증 안 됨). 창 밖은 src 가 없다.
        "xcheck": {"source": "Nasdaq calendar/earnings", "window": {
                       "from": str(today - dt.timedelta(days=XC_BACK)),
                       "to": str(today + dt.timedelta(days=XC_AHEAD))},
                   "ok": bool(nas_days), "days": nas_days, "fail_days": nas_fails,
                   "agree": n_both, "conflict": n_moved, "hour_filled": n_hour,
                   "added": n_only},
        "limits": [
            "한 번의 응답이 1,500건에서 잘린다(실측). 넓은 구간을 한 번에 부르면 뒤쪽이 통째로 "
            "빠지는데 화면에는 '발표가 없는 날'처럼 보이므로, 7일씩 끊어 받아 합친다. "
            "실적 시즌에는 7일도 상한에 닿아, 닿은 구간은 반으로 쪼개 다시 받는다.",
            "과거는 약 30일까지만 응답한다(실측: 7일 전 471건 · 90일 전 0건 · 1년 전 0건). "
            "그래서 지나간 건은 이 스크립트가 직접 누적한다(data/earnings_history.json) — "
            "그 파일이 두꺼워져야 서프라이즈 검증(SUE·PEAD)이 언젠가 가능해진다.",
            "발표 일정은 회사가 바꾼다. 여기 날짜는 조회 시점의 예정일이며 확정이 아니다.",
            "Finnhub은 회사가 날짜를 확정하지 않은 종목에 추정 날짜를 넣어 주면서 확정된 것과 "
            "구분해 주지 않는다. 그 추정이 실제보다 이르면 발표가 없었는데도 지나간 칸에 남는다 "
            "— 실측(2026-07-28) 창 안 417종목 중 26종목이 어긋났고 그중 23종목이 이른 쪽이었다. "
            "그래서 Nasdaq 캘린더로 교차검증하고 어긋나면 늦은 쪽에 놓는다(src=conflict). "
            "두 소스가 함께 틀릴 수 있다는 점은 그대로 남는다 — 확정 여부를 주는 소스가 아니다.",
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
