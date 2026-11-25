#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""분기 데이터셋 뒤 구간을 Form 4 원문으로 메운다 (2026-11-25 사용자 «내부자 거래 지연 문제 해결»).

── 왜 ──────────────────────────────────────────────────────────────────
분기 데이터셋(refresh_insider.py)은 **제출일 기준 분기**로 묶여 분기가 끝난 뒤 나온다.
그래서 화면이 54일(2026-11-24 실측: 최근 거래일 2026-09-30) 늦었다. 그 뒤 구간(마지막 분기 끝 다음날 ~ 오늘)을
EDGAR 일별 색인(daily-index/form.YYYYMMDD.idx)에서 우리 유니버스 발행사의 Form 4/5 를 골라 원문 XML 로 읽는다.

── 부하 ────────────────────────────────────────────────────────────────
* 하루 색인 1콜 + 그날 우리 유니버스 Form 4 수(평일 약 50~150건)만큼 원문 1콜씩. edgar.fetch_bytes 가 초당 8회로 묶는다.
* data/ins_live.json 에 이미 읽은 제출(접수번호 → 거래 줄)을 남겨 다음 실행은 새 제출만 읽는다.
  마지막 2일 색인은 다시 읽는다(그날 밤 늦게 올라온 제출).
* 새 분기 데이터셋이 나오면 그 분기 제출은 데이터셋 쪽이 맡고 여기 캐시에서 빠진다(제출일 > 데이터셋 마지막 분기 끝만 남김).

── 줄 모양은 분기 데이터셋과 같다 ────────────────────────────────────
{d, fd, c, ad, sh, px, own, nm, rel, ti, a, k} · rel = 'Director,Officer,TenPercentOwner,Other' 순 · k = 발행사 CIK.
보통주 표(nonDerivativeTable)만 · 거래일 > 제출일 + 3 은 버림(데이터셋과 같은 규칙) · 원문 링크용 a = 접수번호(대시 없음).
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

import edgar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "ins_live.json")
FORMS = ("4", "4/A", "5", "5/A")
IDX = "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR%d/form.%s.idx"
DOC = "https://www.sec.gov/Archives/%s"
_OWN = re.compile(rb"<ownershipDocument>.*?</ownershipDocument>", re.S)


def _q_end(iso_q: str) -> dt.date:
    """'2026Q3' → 2026-09-30."""
    y, q = int(iso_q[:4]), int(iso_q[-1])
    m = q * 3
    return (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1))


def _v(el, path):
    x = el.find(path)
    if x is None:
        return ""
    v = x.find("value")
    return ((v.text if v is not None else x.text) or "").strip()


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _flag(s):
    return str(s).strip().lower() in ("1", "true")


def parse(raw: bytes, filed: str, acc: str):
    """제출 원문(.txt) → (티커 기호, 발행사 CIK, [줄], 버린 오타 수)."""
    m = _OWN.search(raw)
    if not m:
        return None, None, [], 0
    doc = ET.fromstring(m.group(0))
    sym = (doc.findtext("issuer/issuerTradingSymbol") or "").strip().upper()
    cik = (doc.findtext("issuer/issuerCik") or "").strip().lstrip("0")
    ro = doc.find("reportingOwner")
    nm = rel = ti = ""
    if ro is not None:
        nm = (ro.findtext("reportingOwnerId/rptOwnerName") or "").strip()
        r = ro.find("reportingOwnerRelationship")
        if r is not None:
            rel = ",".join(k for k, t in (("Director", "isDirector"), ("Officer", "isOfficer"),
                                          ("TenPercentOwner", "isTenPercentOwner"), ("Other", "isOther"))
                           if _flag(r.findtext(t)))
            ti = (r.findtext("officerTitle") or "").strip()
    out, bad = [], 0
    for tr in doc.findall("nonDerivativeTable/nonDerivativeTransaction"):
        d = _v(tr, "transactionDate")[:10]
        if not d:
            continue
        if filed and d > (dt.date.fromisoformat(filed) + dt.timedelta(days=3)).isoformat():
            bad += 1
            continue
        sh, px = _num(_v(tr, "transactionAmounts/transactionShares")), _num(_v(tr, "transactionAmounts/transactionPricePerShare"))
        out.append({"d": d, "fd": filed, "c": (tr.findtext("transactionCoding/transactionCode") or "").strip(),
                    "ad": _v(tr, "transactionAmounts/transactionAcquiredDisposedCode"),
                    "sh": round(sh, 0) if sh is not None else None, "px": round(px, 4) if px is not None else None,
                    "own": _num(_v(tr, "postTransactionAmounts/sharesOwnedFollowingTransaction")),
                    "nm": nm, "rel": rel, "ti": ti, "a": acc, "k": cik})
    return sym, cik, out, bad


def collect(uni: dict, ciks: set, after: dt.date, log=print):
    """after 다음날 ~ 오늘 제출분. → ({티커: [줄]}, 메타). uni = {기호: 우리 티커}, ciks = 우리 유니버스 발행사 CIK(str)."""
    try:
        cache = json.load(io.open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    acc = {a: v for a, v in (cache.get("acc") or {}).items() if v.get("fd", "") > after.isoformat()}
    done = set(d for d in (cache.get("days") or []) if d > after.isoformat())
    today = dt.date.today() - dt.timedelta(days=1)       # 그날 색인은 미 동부 밤에 올라온다 → 어제까지
    day, n_idx, n_new, n_bad, miss = after + dt.timedelta(days=1), 0, 0, 0, 0
    while day <= today:
        ds = day.strftime("%Y%m%d")
        if day.weekday() < 5 and (ds not in done or (today - day).days <= 2):
            url = IDX % (day.year, (day.month - 1) // 3 + 1, ds)
            try:
                # 아직 안 올라온 날(오늘 · 공휴일)은 SEC 가 404 가 아니라 403 을 준다 → 오래 기다리지 않는다
                txt = edgar.fetch_bytes(url, timeout=60, max_wait=40).decode("latin-1")
            except Exception as e:                        # 공휴일·아직 안 올라온 오늘 = 404
                if "404" not in str(e) and "403" not in str(e):
                    log("  ⚠ 색인 %s 실패: %s" % (ds, e))
                txt = None
            if txt is not None:
                n_idx += 1
                paths = set()
                for ln in txt.splitlines():
                    f = ln[:17].strip()
                    if f not in FORMS:
                        continue
                    parts = ln.split()
                    if len(parts) < 4 or not parts[-1].startswith("edgar/"):
                        continue
                    if parts[-3] in ciks:                 # 발행사 CIK 줄 (같은 제출이 보고자 CIK 로도 한 줄 더 있다)
                        paths.add(parts[-1])
                for p in sorted(paths):
                    a = os.path.basename(p)[:-4].replace("-", "")
                    if a in acc:
                        continue
                    filed = day.isoformat()
                    try:
                        sym, cik, rows, bad = parse(edgar.fetch_bytes(DOC % p, timeout=60), filed, a)
                    except Exception as e:
                        miss += 1
                        log("  ⚠ 원문 %s 실패: %s" % (p, e))
                        continue
                    n_bad += bad
                    acc[a] = {"fd": filed, "sym": sym or "", "rows": rows}
                    n_new += 1
                if (today - day).days > 2:
                    done.add(ds)
        day += dt.timedelta(days=1)
    by_co = {}
    for a, v in acc.items():
        t = uni.get(v["sym"]) or uni.get(v["sym"].replace(".", "-")) or uni.get(v["sym"].replace("-", "."))
        if not t:
            continue
        by_co.setdefault(t, []).extend(v["rows"])
    io.open(CACHE, "w", encoding="utf-8").write(json.dumps(
        {"note": "Form 4 원문으로 메운 분기 데이터셋 뒤 구간 캐시 (build/insider_live.py). 접수번호 → 거래 줄.",
         "after": after.isoformat(), "days": sorted(done), "acc": acc}, ensure_ascii=False, separators=(",", ":")) + "\n")
    meta = {"from": (after + dt.timedelta(days=1)).isoformat(), "n_filings": len(acc), "n_new": n_new, "n_idx": n_idx,
            "n_bad_date": n_bad, "n_miss": miss}
    log("  원문 보충 %s~: 제출 %d건(새로 읽음 %d · 색인 %d일 · 실패 %d)" % (meta["from"], len(acc), n_new, n_idx, miss))
    return by_co, meta
