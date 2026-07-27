# -*- coding: utf-8 -*-
"""build/refresh_estimates.py — 선행(컨센서스) 지표 → data/estimates.json

왜 따로 만드나. 이 저장소는 "애널리스트 전망은 유료라 무료로는 못 구한다"고 적어 두고
EPS 리비전 계열을 재현 불가로 분류해 왔다. **그건 절반만 맞았다** — yfinance가
quoteSummary의 분석 모듈을 그대로 준다:

  · eps_trend        같은 회계연도 EPS 컨센서스를 현재 / 7일 / 30일 / 60일 / 90일 전 시점으로
                     나란히 준다. 이 다섯 숫자의 차이가 곧 **리비전**이다.
  · eps_revisions    최근 7일·30일 상향/하향 애널리스트 수.
  · earnings_estimate  선행 EPS 컨센서스와 성장률, 애널리스트 수.
  · revenue_estimate   선행 매출 컨센서스와 성장률.

여전히 못 하는 것은 **과거**다. 위 값들은 오늘 시점의 스냅샷이라 백테스트를 못 돌린다.
그래서 이 파일은 두 가지를 한다 — 오늘의 목록을 만들고, 스냅샷을 쌓는다(snaps).
쌓이면 그때 검정한다. 지금 검정한 척하지 않는다.

⚠ 비용: 종목당 요청 1회(네 모듈이 한 응답에 온다 — 같은 Ticker 객체에서 꺼내면 캐시된다).
   518종목 약 4분. 새 Ticker를 종목마다 만들되 모듈은 반드시 그 객체에서 다 꺼낼 것.

  python build/refresh_estimates.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys, time
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "estimates.json")
SNAP_KEEP = 90          # 스냅샷 보관 일수 — 쌓여야 리비전을 시계열로 검정할 수 있다
MIN_OK = 0.80           # 이만큼도 못 받으면 기존 파일을 지키고 실패한다


def _f(x):
    try:
        v = float(x)
        return None if v != v else round(v, 6)
    except (TypeError, ValueError):
        return None


def _cell(df, row, col):
    try:
        return _f(df.loc[row, col])
    except Exception:
        return None


def pull(t, yf):
    """한 종목의 선행 지표. 네 모듈을 **같은 Ticker 객체**에서 꺼낸다(요청 1회)."""
    tk = yf.Ticker(t)
    tr = tk.eps_trend
    ee = tk.earnings_estimate
    re_ = tk.revenue_estimate
    rv = tk.eps_revisions

    cur = _cell(tr, "+1y", "current")

    def revpct(days):
        old = _cell(tr, "+1y", days)
        # 분모에 절댓값을 쓴다 — 적자(음수) 전망에서 부호가 뒤집혀 '대폭 상향'으로 둔갑한다.
        # ⚠ 그래도 분모가 0에 가까우면 값이 폭발한다(실측: WBD +8174%). 순위에는 이 값이 아니라
        #   아래 rp(주가 대비 변화)를 쓴다 — 이 %는 읽는 용도로만 싣는다.
        return round((cur / abs(old) - 1) * 100, 3) if (cur is not None and old) else None

    rec = {
        "fe": cur,                                   # 다음 회계연도 EPS 컨센서스
        "e90": _cell(tr, "+1y", "90daysAgo"), "e30": _cell(tr, "+1y", "30daysAgo"),
        "e7": _cell(tr, "+1y", "7daysAgo"),
        "r90": revpct("90daysAgo"), "r30": revpct("30daysAgo"), "r7": revpct("7daysAgo"),
        "up": _cell(rv, "0y", "upLast30days"), "dn": _cell(rv, "0y", "downLast30days"),
        "eg": _cell(ee, "+1y", "growth"),            # 선행 EPS 성장률
        "rg": _cell(re_, "+1y", "growth"),           # 선행 매출 성장률
        "nan": _cell(ee, "0y", "numberOfAnalysts"),
    }
    return rec if any(v is not None for v in rec.values()) else None


def main() -> int:
    import yfinance as yf

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    uni = [s["t"] for s in st["stocks"]]
    names = {s["t"]: s.get("name") or "" for s in st["stocks"]}

    # 최근 종가 — 리비전을 **주가 대비**로 재기 위해. 추정치 대비 변화율은 분모가 0에 가까우면
    # 폭발하는데(WBD +8174%), 주가로 나누면 그 문제가 사라지고 종목 간 비교도 그대로 된다.
    PX = {}
    for t in uni:
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            a = json.load(io.open(p, encoding="utf-8")).get("pxd") or []
        except Exception:
            continue
        last = next((x for x in reversed(a) if x), None)
        if last:
            PX[t] = last

    rows, fail = {}, []
    t0 = time.time()
    for i, t in enumerate(uni, 1):
        try:
            r = pull(t, yf)
        except Exception:
            r = None
        if r:
            # 주가 대비 리비전(%p) — 순위에 쓰는 값
            px = PX.get(t)
            for k, ek in (("rp90", "e90"), ("rp30", "e30"), ("rp7", "e7")):
                old, cur = r.get(ek), r.get("fe")
                r[k] = (round((cur - old) / px * 100, 4)
                        if (px and old is not None and cur is not None) else None)
            rows[t] = r
        else:
            fail.append(t)
        if i % 100 == 0:
            print("  %d/%d · %.0f초 · 실패 %d" % (i, len(uni), time.time() - t0, len(fail)))
        time.sleep(0.05)

    got = len(rows) / max(1, len(uni))
    if got < MIN_OK:
        print("❌ 수집 %.1f%% (< %.0f%%) — 기존 파일을 지키고 중단한다"
              % (got * 100, MIN_OK * 100))
        return 1

    # ── 스냅샷 누적 ── 리비전을 **시계열로** 검정하려면 오늘의 값만으로는 안 된다.
    # eps_trend가 90일 과거를 주지만 그건 같은 회계연도의 재추정이라 백테스트 표본이 아니다.
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(io.open(OUT, encoding="utf-8"))
        except Exception:
            prev = {}
    today = dt.date.today().isoformat()
    snaps = [s for s in (prev.get("snaps") or []) if s.get("d") != today]
    snaps.append({"d": today, "n": len(rows),
                  "fe": {t: r["fe"] for t, r in rows.items() if r.get("fe") is not None}})
    snaps = snaps[-SNAP_KEEP:]

    doc = {
        "note": "선행(컨센서스) 지표. yfinance의 분석 모듈(eps_trend·eps_revisions·"
                "earnings_estimate·revenue_estimate)에서 받는다. 오늘 시점 스냅샷이라 "
                "백테스트는 못 돌린다 — snaps에 매일 쌓아 두고, 표본이 차면 그때 검정한다.",
        "fields": {
            "fe": "다음 회계연도 EPS 컨센서스", "r90": "90일 전 대비 EPS 컨센서스 변화율(%)",
            "r30": "30일 전 대비(%)", "r7": "7일 전 대비(%)",
            "rp90": "90일간 컨센서스 변화 ÷ 주가(%p) — 순위는 이 값으로 매긴다",
            "rp30": "30일간 · 주가 대비(%p)", "rp7": "7일간 · 주가 대비(%p)",
            "up": "최근 30일 상향 애널리스트 수", "dn": "최근 30일 하향 수",
            "eg": "선행 EPS 성장률(다음 회계연도)", "rg": "선행 매출 성장률(다음 회계연도)",
            "nan": "추정에 참여한 애널리스트 수",
        },
        "limits": [
            "오늘 시점 스냅샷이다. 리비전 값(r90·r30·r7)은 '지금까지 이렇게 바뀌었다'는 "
            "기록이지 과거 어느 시점에 그 값이 얼마였는지가 아니다 — 백테스트에 쓸 수 없다.",
            "애널리스트 수가 적은 종목은 한 사람이 바꾸면 리비전이 크게 튄다. nan을 같이 싣는다.",
            "적자 전망(음수) 종목은 변화율의 뜻이 흐려진다 — 분모에 절댓값을 써서 부호가 "
            "뒤집히는 것만 막았고, 해석은 여전히 조심해야 한다.",
        ],
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": today,
        "n": len(rows), "n_uni": len(uni),
        "fail": sorted(fail)[:40],
        "names": {t: names.get(t, "") for t in rows},
        "rows": rows,
        "snaps": snaps,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("선행 지표 %d/%d종목 · 스냅 %d일 · %.0fKB · %.0f초"
          % (len(rows), len(uni), len(snaps), os.path.getsize(OUT) / 1024, time.time() - t0))
    for k, lab in (("rp90", "90일 리비전 상위(주가 대비)"), ("eg", "선행 EPS 성장 상위")):
        top = sorted(((r[k], t) for t, r in rows.items() if r.get(k) is not None), reverse=True)[:8]
        print("  %s: %s" % (lab, " · ".join("%s %+.1f" % (t, v) for v, t in top)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
