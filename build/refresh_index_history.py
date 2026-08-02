#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""위키백과 과거 리비전 → 시점정합 지수 편입 이력 (data/index_history.json)

무엇을·왜.
  이 랩이 스스로 최대 약점으로 꼽는 것이 생존편향이다 — "오늘의 518종목을 과거에 그대로
  적용한다. 그 사이 상장폐지·편출된 종목이 없어 모든 수치가 실제보다 좋게 나온다"
  (data/signal_lab.json 의 limits, sources.html, tech_backtest.py 곳곳).
  그걸 재려면 '그때 실제로 지수에 있던 명단'이 필요한데, 지금 그 명단은 라이선스 DB
  (public.index_constituents)에서만 오고 그래서 data/pit_members.json 이 gitignore 다 —
  즉 **러너가 스스로 만들 수 없고**, 그래서 시점정합 검증이 사내망 PC 에 묶여 있다.

  위키백과의 지수 목록 문서는 **과거 리비전이 영구 보존**된다. 월말 시점의 리비전을 받으면
  그 시점의 편입 명단이 그대로 나온다. 라이선스가 CC BY-SA 라 재배포도 가능하다.

정확도 — 사내DB 와 실측 대조했다(2026-08-02).
  사내DB 가 '2020-09 멤버였고 이후 편출'이라 한 60종 중 위키 2020-08-30 스냅샷 적중 53종.
  누락 7종을 파 보니 6종은 **개명이지 결손이 아니었다** — 사내DB 는 오늘 티커로, 위키는
  그때 티커로 적었을 뿐 같은 회사다:
      BBWI←LB · DINO←HFC · FBIN←FBHS · GAP←GPS · LUMN←CTL · FRCB←FRC
  나머지 1종(ETSY)은 위키가 옳다 — 2020-09 편입이라 8-30 스냅샷에 없는 것이 정답이고,
  사내DB 도 first=2020-09 이라 두 소스가 오히려 일치한다. 실질 일치 60/60.
  ⚠ 그래서 **티커가 아니라 CIK 로 조인해야 한다.** 아래 cik_hist 가 그 지도다.

⚠ 경계는 2015년이다. CIK 컬럼이 그때부터 생겼다(실측: 2011-06 · 2013-06 리비전은 CIK 0행,
  2015-03 부터 502/502). 2015 이전은 티커만 있어 개명이 모호해지므로 START 를 2015-01 로 둔다.

⚠ 파서가 이 파일에서 가장 약한 곳이다. 실제로 세 번 틀렸다 —
  ① 표를 안 좁혀 751종(다른 표까지) ② 단일문자 티커(T·F·C·V·K·L·O)를 정규식이 버려 495종
  ③ NDX 표가 `|회사||티커` 인라인이라 줄 단위 분해로는 0종.
  그래서 관문을 아래에 두껍게 깔았다. 파싱이 조용히 어긋나느니 갱신이 멈추는 편이 낫다.

⚠ NDX 표는 시기에 따라 **다른 문서에 있다**(실측):
      2015~2023  Nasdaq-100 문서의 ==Components== 절
      2024~      List of NASDAQ-100 companies 문서의 id=constituents 표
      2015~2016  Nasdaq-100 문서의 ==Components== 절 — **표가 아니라 번호 목록**이다
                 (`#[[Adobe Systems]] (ADBE)`). 표 파서로는 0종이 나온다(49개월이 그렇게 실패했다).
  셋 다 시도한다. 그래도 못 읽으면 그 달의 NDX 는 gaps 에 적고 SPX 만 남긴다 —
  형식이 또 바뀌었다고 SPX 까지 못 쓰게 하지 않는다. 빈칸은 조용히 두지 않고 기록한다.

증분 갱신. 이미 파일에 있는 달은 다시 받지 않는다(과거 리비전은 불변이다).
처음 한 번만 무겁고(약 140개월 × 2문서) 이후에는 새 달 하나씩이다.

사용:
    python3 build/refresh_index_history.py            # 증분
    python3 build/refresh_index_history.py --rebuild  # 처음부터 다시
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "index_history.json")

API = "https://en.wikipedia.org/w/api.php"
RAW = "https://en.wikipedia.org/w/index.php?oldid=%d&action=raw"
# 위키미디어는 UA 에 연락처를 요구한다(정책). 익명 UA 는 429/403 을 받는다.
UA = {"User-Agent": "yeouido-lab/1.0 (https://github.com/ydyoon4578/yeodoo-lab) index-history"}

START = "2015-01"          # CIK 컬럼이 생긴 시점. 위 ⚠ 참조.
# 위키미디어는 익명 클라이언트에 429 를 준다. 실측으로 0.35초 간격에 140개월 × 6요청을
# 돌리다 429 를 받았다. 1.2초로 늘리고 429 는 지수 백오프로 재시도한다 —
# 첫 실행은 20분쯤 걸리지만 그 뒤로는 새 달 하나뿐이다.
PAUSE = 1.2

# (인덱스, 후보 문서 제목들). 앞의 것부터 시도해 표가 나오는 쪽을 쓴다.
SRC = {
    "spx": ["List of S&P 500 companies"],
    "ndx": ["List of NASDAQ-100 companies", "Nasdaq-100"],
}
# 관문: 종목 수가 이 범위를 벗어나면 파싱이 깨진 것으로 본다.
LIM = {"spx": (480, 520), "ndx": (95, 115)}

TICK = re.compile(r"[A-Z][A-Z.\-]{0,5}")
CIK = re.compile(r"\d{7,10}")
# 2015~2016 무렵 NDX 는 표가 아니라 **번호 목록**이었다: `#[[Adobe Systems]] (ADBE)`.
# 표 파서로는 0종이 나온다(실제로 그렇게 49개월이 실패했다).
LISTED = re.compile(r"^#\s*\[\[[^\]]*\]\][^(\n]*\(([A-Z][A-Z.\-]{0,5})\)", re.M)


def _get(url: str) -> str:
    for i in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) \
                .read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == 4:
                raise
            time.sleep(5 * (i + 1))       # 429 는 길게 물러선다
        except Exception:
            if i == 4:
                raise
            time.sleep(2 * (i + 1))
    return ""


def rev_at(title: str, iso: str):
    """iso 시각 **이전**의 마지막 리비전. 없으면 (None, None)."""
    u = API + "?" + urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "titles": title, "rvlimit": 1,
        "rvstart": iso, "rvdir": "older", "rvprop": "ids|timestamp",
        "format": "json", "formatversion": "2"})
    p = json.loads(_get(u))["query"]["pages"][0]
    if p.get("missing"):
        return None, None
    r = (p.get("revisions") or [None])[0]
    return (r["revid"], r["timestamp"]) if r else (None, None)


def _clean(c: str) -> str:
    c = re.sub(r"<ref[^>]*>.*?</ref>", "", c, flags=re.S)
    c = re.sub(r"<ref[^>]*/>", "", c)
    c = re.sub(r"\{\{[^}|]*\|([^}]*)\}\}", r"\1", c)      # {{NyseSymbol|MMM}} → MMM
    c = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", c)    # [[3M|3M Company]] → 3M Company
    c = re.sub(r"\[\[([^\]]*)\]\]", r"\1", c)
    c = re.sub(r"\[[^\s\]]+\s[^\]]*\]", "", c)            # 외부링크 [url 라벨] 제거
    c = re.sub(r"<[^>]+>", "", c)
    return c.strip()


def _table(wt: str):
    """구성종목 표 하나를 잘라 낸다. id=constituents 를 우선하고, 없으면 첫 wikitable."""
    m = re.search(r'\{\|[^\n]*id\s*=\s*"?constituents"?[^\n]*\n', wt)
    how = "id=constituents"
    if not m:
        # NDX 는 2023년까지 Components 절 안에 있다 — 그 구간만 좁혀 첫 표를 잡는다.
        seg = wt
        i = wt.find("==Components==")
        if i < 0:
            i = wt.find("== Components ==")
        if i >= 0:
            j = wt.find("==", i + 5)
            seg = wt[i:j if j > 0 else len(wt)]
            how = "Components절 첫 표"
        else:
            how = "첫 wikitable"
        m = re.search(r"\{\|[^\n]*wikitable[^\n]*\n", seg)
        if not m:
            return None, how
        off = wt.find(seg) if seg is not wt else 0
        e = wt.find("\n|}", off + m.end())
        return wt[off + m.end():e if e > 0 else len(wt)], how
    e = wt.find("\n|}", m.end())
    return wt[m.end():e if e > 0 else len(wt)], how


def _section(wt: str, name: str):
    """== name == 절의 본문. 헤더 자체를 건너뛰고 다음 헤더 앞까지."""
    m = re.search(r"^==+\s*%s\s*==+\s*$" % re.escape(name), wt, re.M)
    if not m:
        return None
    nxt = re.search(r"^==+[^=\n]+==+\s*$", wt[m.end():], re.M)
    return wt[m.end():m.end() + (nxt.start() if nxt else len(wt))]


def parse(wt: str):
    """(티커→CIK 또는 None) 사전. CIK 는 SPX 표에만 있다."""
    seg, how = _table(wt)
    if seg is None or not re.search(r"\S", seg):
        # 표가 없으면 번호 목록 형식을 본다(초기 NDX).
        comp = _section(wt, "Components")
        if comp:
            # 값 모양을 표 경로와 맞춘다 — (CIK, 회사명). 이 형식엔 CIK 컬럼이 없다.
            tk = {t.upper().replace("-", "."): (None, "") for t in LISTED.findall(comp)}
            if tk:
                return tk, "Components 번호목록"
        return {}, how or "표 없음"
    out = {}
    for row in re.split(r"\n\|-", seg):
        cells = []
        for line in re.split(r"\n\s*\|(?!\|)", row)[1:]:
            cells += line.split("||")          # NDX 는 `|회사||티커` 인라인이다
        cells = [_clean(x) for x in cells]
        t = None
        for c in cells[:2]:                    # 티커는 1열(SPX) 또는 2열(NDX)
            if TICK.fullmatch(c):
                t = c.upper().replace("-", ".")
                break
        if not t:
            continue
        ck = next((x.zfill(10) for x in cells if CIK.fullmatch(x)), None)
        # 회사명도 같이 잡는다. CIK 묶음이 옳은지 검증할 단서가 이것뿐이다 —
        # 실제로 HBI(Hanesbrands)가 AVY(Avery Dennison)의 CIK 로 한 번 붙었는데,
        # 이름을 안 들고 있으면 그 오염을 알아챌 방법이 없다. 잘못된 CIK 묶음은
        # 서로 다른 두 회사를 한 회사로 합쳐 버리므로 이 파일에서 가장 위험한 오류다.
        nm = next((x for x in cells[1:4] if len(x) > 3 and not CIK.fullmatch(x)
                   and not TICK.fullmatch(x)), None)
        out[t] = (ck, (nm or "")[:60])
    return out, how


def month_ends(start: str, end: str):
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    while (y, m) <= (ey, em):
        nx = dt.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        yield "%04d-%02d" % (y, m), (nx - dt.timedelta(days=1)).isoformat() + "T23:59:59Z"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def snapshot(idx: str, iso: str):
    """그 시점의 (티커→CIK, 메타). 후보 문서를 순서대로 시도한다."""
    last = None
    for title in SRC[idx]:
        rid, ts = rev_at(title, iso)
        time.sleep(PAUSE)
        if not rid:
            continue
        tk, how = parse(_get(RAW % rid))
        time.sleep(PAUSE)
        lo, hi = LIM[idx]
        if lo <= len(tk) <= hi:
            return tk, {"title": title, "rev": rid, "ts": (ts or "")[:10], "how": how}
        last = (title, rid, len(tk), how)
    return {}, {"fail": last}


def main() -> int:
    rebuild = "--rebuild" in sys.argv
    doc = {}
    if os.path.exists(OUT) and not rebuild:
        try:
            doc = json.load(io.open(OUT, encoding="utf-8"))
        except Exception:
            doc = {}
    months = doc.get("months") or {}
    cik = doc.get("cik") or {}
    cik_hist = doc.get("cik_hist") or {}

    today = dt.date.today()
    end = "%04d-%02d" % (today.year, today.month)
    want = list(month_ends(START, end))
    todo = [(mk, iso) for mk, iso in want if mk not in months]
    # 이번 달은 아직 안 끝났으므로 매번 다시 받는다(리비전이 늘어난다).
    cur = "%04d-%02d" % (today.year, today.month)
    if cur in months and (cur, None) not in todo:
        todo += [(mk, iso) for mk, iso in want if mk == cur]

    print("지수 편입 이력 — 보유 %d개월 · 받을 %d개월 (%s ~ %s)"
          % (len(months), len(todo), START, end))
    if not todo:
        print("  받을 것 없음")

    fail, gaps = [], list(doc.get("gaps") or [])
    names = {}          # CIK → {티커: 회사명} — 아래 묶음 검증에 쓴다
    for n, (mk, iso) in enumerate(todo, 1):
        rec = {}
        for idx in ("spx", "ndx"):
            tk, meta = snapshot(idx, iso)
            if not tk:
                # SPX 는 이 파일의 본체다 — 못 읽으면 그 달은 쓸 수 없다.
                # NDX 는 문서·형식이 시기마다 바뀌어(표 → 번호목록 → 다른 문서) 새 형식이
                # 나오면 또 막힌다. 그때 SPX 까지 못 쓰게 하는 것은 과하다.
                # 대신 **빠뜨린 사실을 파일에 적는다**(gaps). 조용히 없는 것과 없다고 적힌 것은 다르다.
                if idx == "spx":
                    fail.append("%s spx 파싱 실패 %s" % (mk, meta.get("fail")))
                else:
                    gaps.append({"month": mk, "index": idx, "why": str(meta.get("fail"))})
                continue
            rec[idx] = sorted(tk)
            rec[idx + "_rev"] = meta["rev"]
            for t, (c, nm) in tk.items():
                if not c:
                    continue
                cik[t] = c
                names.setdefault(c, {})[t] = nm
        if rec.get("spx"):
            months[mk] = rec
        if n % 12 == 0 or n == len(todo):
            print("  … %d/%d (%s)" % (n, len(todo), mk))

    if fail:
        # 조용히 빠뜨리지 않는다. 한 달이라도 못 읽으면 그 달은 '없음'이 아니라 '모름'이다.
        print("\n❌ %d건 실패 — 파일을 건드리지 않는다:" % len(fail))
        for f in fail[:10]:
            print("   ·", f)
        return 1
    if not months:
        print("❌ 결과 없음")
        return 1

    # ── CIK 묶음 검증 ──────────────────────────────────────────────
    # 같은 CIK 에 여러 티커가 붙는 경우는 셋인데, 둘은 정상이고 하나는 사고다.
    #   ① 개명(CTL→LUMN) — 두 티커가 **같은 달에 함께 나타나지 않는다**. 옛것이 끝나고 새것이 시작한다.
    #      회사 이름도 대개 함께 바뀌므로(그래서 티커를 바꾼 것이다) 이름으로는 못 가른다.
    #   ② 복수 클래스(GOOGL/GOOG) — **늘 함께 나타나고** 이름이 같다.
    #   ③ 파싱 사고 — 함께 나타나는데 이름이 무관하다. 실제로 HBI(Hanesbrands)가
    #      AVY(Avery Dennison)의 CIK 로 붙은 적이 있다. 서로 다른 두 회사를 한 회사로 합치는
    #      오류라 이 파일에서 가장 위험하다.
    # 그래서 **공존 여부 + 이름**을 함께 본다. 이름만 보면 ①을 사고로 오판하고,
    # 공존만 보면 ②와 ③을 못 가른다.
    def _stem(x):
        x = re.sub(r"[^A-Za-z ]", " ", (x or "").lower())
        # 홑글자도 지운다 — "(Class A)" 의 A 가 남으면 GOOGL/GOOG 의 어간이 갈린다(실측).
        x = re.sub(r"\b(inc|corp|corporation|co|company|the|plc|ltd|group|holdings|class|new|[a-z])\b", " ", x)
        return " ".join(x.split())[:18]

    where = {}                       # 티커 → 등장한 달 집합
    for mk, rec in months.items():
        for t in (rec.get("spx") or []) + (rec.get("ndx") or []):
            where.setdefault(t, set()).add(mk)

    cik_hist, conflicts = {}, []
    for c, tn in names.items():
        if len(tn) < 2:
            continue
        ts = sorted(tn)
        co = any(where.get(a, set()) & where.get(b, set())
                 for i, a in enumerate(ts) for b in ts[i + 1:])
        if not co:
            cik_hist[c] = ts                      # ① 개명 — 겹치는 달이 없다
            continue
        stems = {_stem(v) for v in tn.values() if v}
        base = sorted(stems, key=len)[0] if stems else ""
        if stems and all(base in x or x in base for x in stems):
            cik_hist[c] = ts                      # ② 복수 클래스 — 함께 나오고 이름이 같다
        else:
            conflicts.append({"cik": c, "tickers": tn,
                              "why": "같은 달에 함께 나오는데 회사 이름이 무관하다 — 파싱 사고로 본다"})

    ks = sorted(months)
    doc = {
        "note": "위키백과 지수 목록 문서의 **과거 리비전**에서 뽑은 월말 시점 편입 명단. "
                "라이선스 DB 없이 시점정합 유니버스를 만들려는 것이다(생존편향 계측용). "
                "티커는 그 시점 표기이므로 오늘 티커와 다를 수 있다 — 조인은 cik_hist 로 할 것.",
        "source": "en.wikipedia.org (CC BY-SA) — 문서·리비전 번호를 월마다 함께 싣는다",
        "limit": "위키 편집 지연이 있다. 문서 자체가 '현재 기준' 날짜를 본문에 적는 경우도 있어 "
                 "월말 리비전이 며칠 전 상태일 수 있다. 발효일 정본이 아니라 근사다. "
                 "CIK 컬럼은 2015년경부터 생겨 그 이전은 다루지 않는다.",
        "start": ks[0], "as_of": ks[-1], "n_months": len(ks),
        # 못 읽은 (달, 지수) — 빈칸을 조용히 두지 않는다. 이 목록이 비어 있지 않으면
        # 그 달의 그 지수는 '멤버가 없었다'가 아니라 '모른다'는 뜻이다.
        "gaps": gaps,
        "months": months,
        "cik": cik,
        # CIK → 그동안 관측된 티커들. 개명 추적용이며 이 파일의 핵심이다
        # (BBWI←LB, DINO←HFC 처럼 같은 회사가 다른 티커로 적혀 있다).
        "cik_hist": dict(sorted(cik_hist.items())),
        # 이름이 안 맞아 채택하지 않은 묶음. 비어 있어야 정상이고, 있으면 그 CIK 는
        # 정체성 조인에 쓰면 안 된다(파싱이 어긋난 자리다).
        "cik_conflicts": conflicts,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    n_ren = len(doc["cik_hist"])
    if conflicts:
        print("  ⚠ 이름이 안 맞는 CIK 묶음 %d건 — cik_conflicts 에 적었다(조인에 쓰지 말 것):" % len(conflicts))
        for x in conflicts[:5]:
            print("     %s %s" % (x["cik"], x["tickers"]))
    uni = set()
    for r in months.values():
        uni |= set(r.get("spx") or []) | set(r.get("ndx") or [])
    print("\n%d개월 · %s ~ %s · 합집합 %d종 · 개명 감지 %d건 · %.0fKB"
          % (len(ks), ks[0], ks[-1], len(uni), n_ren, os.path.getsize(OUT) / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
