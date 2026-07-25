#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRED 릴리스 일정 → 경제지표 발표 캘린더

  calendar.html#macro  경제지표 일정

── 왜 FRED인가 ────────────────────────────────────────────────────────
이 사이트의 국면 판정(regime.html)은 FRED 시리즈 39개로 만든다. 그 39개가 **각각 어느
릴리스에 실려 언제 나오는지**를 FRED가 알려준다. 그래서 이 캘린더는 임의로 고른 '주요
지표 목록'이 아니라, **이 랩이 실제로 쓰는 지표의 발표 일정**이다. 둘을 같은 정본에서
뽑으므로 어긋날 수 없다.

── 이 화면이 싣지 않는 것 ─────────────────────────────────────────────
* **예상치·컨센서스를 싣지 않는다.** FRED는 주지 않고, 다른 데서 가져오면 라이선스 문제이며,
  무엇보다 이 랩은 컨센서스 대비 서프라이즈가 수익으로 이어지는지 검증한 적이 없다.
  "언제 나오는가"까지만 말한다.
* 발표 시각(한국시간 몇 시)도 싣지 않는다 — FRED는 날짜만 준다.

── 실측(2026-07-25) ───────────────────────────────────────────────────
  releases/dates는 **미래 예정일을 준다**(고용보고서 2026-08-07·CPI 2026-08-12 …).
  호출 수 = 시리즈 39 + 릴리스 약 25 ≈ 64회. FRED 상한은 분당 120회라 여유 있다.

사용: FRED_API_KEY=... python3 build/refresh_calendar.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "calendar.json")

# ⚠ 키를 소스에 적지 않는다(2026-07-25 정리 — 공개 저장소에 폴백으로 박혀 있었다).
KEY = (os.getenv("FRED_API_KEY") or "").strip()
BASE = "https://api.stlouisfed.org/fred/"

BACK_DAYS = 21      # 지난 발표도 이만큼은 보여준다(방금 나온 게 뭔지가 캘린더의 절반이다)
FWD_DAYS = 120      # 앞으로 이만큼
MIN_GAP = 0.55      # 초당 2회 미만 — FRED 상한(분당 120)의 절반 이하로 둔다


def get(ep: str, **kw):
    kw.update(api_key=KEY, file_type="json")
    url = BASE + ep + "?" + urllib.parse.urlencode(kw)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "yeodoo-lab"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def load_series():
    """국면 판정이 쓰는 FRED 시리즈 목록 — regime.json이 정본이다."""
    with io.open(os.path.join(DATA, "regime.json"), encoding="utf-8") as f:
        d = json.load(f)
    return [(x["k"], x.get("label") or x["k"], x.get("group") or "") for x in d.get("indicators", [])]


def main() -> int:
    if not KEY:
        print("❌ FRED_API_KEY가 없습니다. 저장소 시크릿에 등록하세요:")
        print("     gh secret set FRED_API_KEY --repo <owner>/<repo>")
        print("   로컬 실행은  FRED_API_KEY=... python3 build/refresh_calendar.py")
        return 1
    series = load_series()
    if not series:
        print("❌ regime.json에서 시리즈를 읽지 못했다 — 갱신 중단(이전본 유지)")
        return 1
    print("국면 판정이 쓰는 시리즈 %d개" % len(series))

    # ── 시리즈 → 릴리스 ─────────────────────────────────────────────────
    rel = {}            # release_id → {name, series:[(k,label,group)]}
    miss = []
    for k, label, grp in series:
        j = get("series/release", series_id=k)
        time.sleep(MIN_GAP)
        rs = (j or {}).get("releases") or []
        if not rs:
            miss.append(k)
            continue
        r = rs[0]
        e = rel.setdefault(int(r["id"]), {"name": r.get("name") or "", "series": []})
        e["series"].append({"k": k, "label": label, "group": grp})
    if not rel:
        print("❌ 릴리스 매핑 0건 — API 키나 응답 형식을 확인할 것. 갱신 중단")
        return 1
    print("릴리스 %d개로 묶임 (매핑 실패 %d개)" % (len(rel), len(miss)))

    # ── 릴리스 → 발표일 ─────────────────────────────────────────────────
    today = dt.date.today()
    lo = (today - dt.timedelta(days=BACK_DAYS)).isoformat()
    hi = (today + dt.timedelta(days=FWD_DAYS)).isoformat()
    rows = []
    for rid, e in rel.items():
        j = get("release/dates", release_id=rid, realtime_start=lo, realtime_end=hi,
                include_release_dates_with_no_data="true", sort_order="asc", limit=200)
        time.sleep(MIN_GAP)
        for x in ((j or {}).get("release_dates") or []):
            d = str(x.get("date") or "")
            if not (lo <= d <= hi):
                continue
            rows.append({"d": d, "rid": rid})
    if not rows:
        print("❌ 발표일 0건 — 갱신 중단(이전본 유지)")
        return 1

    # 같은 릴리스가 같은 날 두 번 잡히는 일이 있어 (d, rid)로 중복을 없앤다
    seen, dedup = set(), []
    for r in rows:
        key = (r["d"], r["rid"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    dedup.sort(key=lambda r: (r["d"], r["rid"]))

    # ── 릴리스별 발표 간격 실측 ────────────────────────────────────────
    # 이걸 안 재면 매일 나오는 금리·VIX 릴리스가 캘린더를 뒤덮는다(실측: 576건 중 394건).
    # '주요 지표'를 손으로 고르는 대신, 실제 날짜 간격으로 성격을 가른다.
    by_rid = {}
    for r in dedup:
        by_rid.setdefault(r["rid"], []).append(r["d"])
    for rid, ds in by_rid.items():
        ds = sorted(set(ds))
        gaps = []
        for a, b in zip(ds, ds[1:]):
            try:
                gaps.append((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days)
            except ValueError:
                pass
        gaps.sort()
        med = gaps[len(gaps) // 2] if gaps else None
        kind = ("매일" if med is not None and med <= 3 else
                "주간" if med is not None and med <= 9 else
                "격주" if med is not None and med <= 20 else
                "월간" if med is not None and med <= 45 else
                "분기" if med is not None else "부정기")
        rel[rid]["gap_days"] = med
        rel[rid]["kind"] = kind

    fut = [r for r in dedup if r["d"] >= today.isoformat()]
    doc = {
        "note": "FRED 릴리스 일정. 이 랩의 국면 판정이 실제로 쓰는 39개 시리즈가 어느 릴리스에 "
                "실려 언제 나오는지만 싣는다. 예상치·컨센서스는 싣지 않는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": today.isoformat(),
        "window": {"from": lo, "to": hi, "back_days": BACK_DAYS, "fwd_days": FWD_DAYS},
        "n": len(dedup),
        "n_future": len(fut),
        "n_series": len(series),
        "miss_series": miss,
        "releases": {str(k): v for k, v in rel.items()},
        "dates": dedup,
        # 화면 기본값 — 매일 나오는 릴리스는 접어 둔다(이벤트가 아니라 시세 갱신에 가깝다)
        "kinds": sorted({v["kind"] for v in rel.values()}),
        "limits": [
            "발표 간격은 손으로 고른 분류가 아니라 실제 날짜 간격의 중앙값으로 잰 것이다.",
            "예상치·컨센서스를 싣지 않는다 — FRED가 주지 않고, 이 랩은 서프라이즈가 수익으로 "
            "이어지는지 검증한 적도 없다. '언제 나오는가'까지만 말한다.",
            "발표 시각은 없다. FRED는 날짜만 준다.",
            "미래 일정은 FRED가 공지한 예정일이며, 기관 사정으로 바뀔 수 있다.",
            "이 랩이 쓰지 않는 지표는 아무리 유명해도 싣지 않는다 — 국면 판정의 39개 시리즈가 정본이다.",
        ],
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    sz = os.path.getsize(OUT) / 1024
    print("발표일 %d건(앞으로 %d건) · 릴리스 %d개 · %.0fKB" % (len(dedup), len(fut), len(rel), sz))
    nxt = fut[:5]
    for r in nxt:
        print("   %s  %s" % (r["d"], rel[r["rid"]]["name"]))
    if miss:
        print("⚠ 릴리스를 못 찾은 시리즈 %d개: %s" % (len(miss), ", ".join(miss)))
    if not fut:
        print("❌ 미래 일정이 하나도 없다 — 캘린더로 쓸 수 없다. 갱신 중단")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
