#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC Form 13F 분기 데이터셋 → 거장 포트폴리오 · 공통 보유종목

  guru.html           거장 포트폴리오·매매
  guru.html#overlap   공통 보유종목

── 이 화면이 구조적으로 못 하는 것 ────────────────────────────────────
13F는 '무엇을 얼마나 들고 있었나'를 **분기말 기준**으로, 그것도 **45일 뒤에** 낸다.
그래서 화면을 보는 시점엔 최대 4.5개월 묵은 숫자다. 이건 수집을 자주 해도 안 줄어든다.

더 중요한 것:
* **롱온리 미국 상장주식만 담긴다.** 공매도·현금·채권·해외주식·파생 원본은 13F에 없다.
  "이 사람 포트폴리오"라고 부르면 거짓말이 된다 — 보고 대상만 보이는 것이다.
* **변동은 매매 기록이 아니다.** 분기말 잔고의 차이일 뿐이라, 분기 중에 샀다 판 것은
  아예 안 보이고, 안 팔았는데 주가가 움직여도 평가액은 바뀐다. 그래서 주식 수로 비교한다.
* 우리 유니버스(518종목)와 겹치는 부분만 본다. 그들 포트폴리오의 **일부**다 — 비중을 함께 적는다.

── CUSIP → 티커 ───────────────────────────────────────────────────────
13F는 CUSIP으로만 종목을 적는다. 티커가 없다. FIGI 컬럼이 있지만 실측 채움률이 13.9%라
쓸 수 없어(2026-07-25), SEC의 **공매도 미결제(FTD) 파일**을 쓴다 — CUSIP과 SYMBOL을 같이
싣는 무료 공개 파일이고, 실측 우리 유니버스 커버가 98.1%다.

── 명단은 랩이 골랐다 ─────────────────────────────────────────────────
13F 보고총액 1위는 BlackRock(5.7조$)·Vanguard·State Street다. 그건 액티브 판단이 아니라
인덱스라, 규모를 기준으로 삼으면 '거장'이 아니라 '수탁고 순위'가 된다. 그래서 널리 알려진
액티브 운용사를 **CIK로 명시해** 고른다. 이름을 안다는 뜻이지 잘한다는 뜻이 아니다 —
이 랩은 이들의 성과를 검증한 적이 없다.

사용: python3 build/refresh_13f.py
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru.json")

IDX_13F = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
IDX_FTD = "https://www.sec.gov/data/foiadocsfailsdatahtm"
FTD_FILES = 2        # CUSIP↔티커 커버를 올리려고 최근 몇 개를 합칠지
KEEP_HOLD = 60       # 운용사별로 남길 보유 종목 수(유니버스 교집합 기준, 평가액순)

# ── 명단(CIK 고정) ────────────────────────────────────────────────────
# 이름 부분일치로 찾으면 엉뚱한 법인이 걸린다(실측: 'ARK INVEST'가 GREATMARK를 물어왔다).
# 그래서 CIK를 박아 둔다. 바꾸려면 이 표만 고치면 된다 — 고른 사람이 누군지 숨기지 않는다.
GURUS = {
    1067983: "버크셔 해서웨이 (버핏)",
    1061768: "바우포스트 (클라만)",
    1336528: "퍼싱스퀘어 (애크먼)",
    1656456: "아팔루사 (테퍼)",
    1536411: "듀케인 패밀리오피스 (드러켄밀러)",
    1167483: "타이거 글로벌 (콜먼)",
    1040273: "서드포인트 (롭)",
    1061165: "론파인 캐피털 (맨델)",
    1103804: "바이킹 글로벌 (핼버슨)",
    1135730: "코튜 매니지먼트 (라퐁)",
    1412093: "아이칸 캐피털 (아이칸)",
    1029160: "소로스 펀드 (소로스)",
    1709323: "히말라야 캐피털 (리루)",
    1350694: "브리지워터 (달리오)",
    1697748: "아크 인베스트 (우드)",
    949509: "오크트리 (마크스)",
    1166559: "게이츠 재단 신탁",
    1096343: "마클 그룹",
}


def fetch(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": edgar.UA, "Accept-Encoding": "gzip"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw


def _abs(href: str) -> str:
    return href if href.startswith("http") else "https://www.sec.gov" + href


def latest_13f(n: int):
    """인덱스 페이지에서 최근 n개 창의 ZIP URL. 파일명이 '01mar2026-31may2026' 꼴이라
    끝 날짜로 정렬한다(경로가 분기마다 달라 하드코딩하면 깨진다)."""
    html = fetch(IDX_13F, timeout=90).decode("utf-8", "ignore")
    out = []
    for h in re.findall(r'href="([^"]*form13f\.zip)"', html):
        m = re.search(r"(\d{2})([a-z]{3})(\d{4})-(\d{2})([a-z]{3})(\d{4})_form13f\.zip", h)
        if not m:
            continue
        mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        try:
            end = dt.date(int(m.group(6)), mon[m.group(5)], int(m.group(4)))
        except (ValueError, KeyError):
            continue
        out.append((end, _abs(h)))
    out.sort(reverse=True)
    seen, res = set(), []
    for end, u in out:
        if u in seen:
            continue
        seen.add(u)
        res.append((end.isoformat(), u))
    return res[:n]


def cusip_map(universe):
    """{CUSIP: 우리 티커}. SEC 공매도 미결제(FTD) 파일에서 만든다 — CUSIP과 SYMBOL이 같이 있다."""
    html = fetch(IDX_FTD, timeout=90).decode("utf-8", "ignore")
    hrefs = [h for h in re.findall(r'href="([^"]*cnsfails\d{6}[ab]\.zip)"', html, re.I)]
    # 파일명의 연월+a/b로 최신순 정렬
    def key(h):
        m = re.search(r"cnsfails(\d{6})([ab])", h, re.I)
        return (m.group(1), m.group(2)) if m else ("", "")
    hrefs = sorted(set(hrefs), key=key, reverse=True)[:FTD_FILES]
    alias = {}
    for t in universe:
        for v in (t, t.replace(".", "-"), t.replace("-", ".")):
            alias[v.upper()] = t
    out = {}
    for h in hrefs:
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(_abs(h), timeout=180)))
        except Exception:
            print("⚠ FTD 파일 실패: %s" % h)
            continue
        for name in z.namelist():
            for line in io.TextIOWrapper(z.open(name), "utf-8", errors="ignore"):
                p = line.split("|")
                if len(p) < 4:
                    continue
                c, s = p[1].strip(), p[2].strip().upper()
                t = alias.get(s)
                if c and t:
                    out.setdefault(c, t)
    return out


def read_tsv(z, name):
    if name not in z.namelist():
        return []
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), "utf-8", errors="ignore"), delimiter="\t"))


def _f(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return 0.0


def read_quarter(url: str, cmap: dict):
    """한 창의 ZIP → (기준분기, {cik: {name, total_val, total_n, holds:{ticker:{v,sh}}}}).

    수정보고(13F-HR/A) 처리 — SEC 규약대로 가른다:
      RESTATEMENT  = 원본을 갈아치운다
      NEW HOLDINGS = 원본에 더한다
    안 가르면 애크먼처럼 수정보고를 자주 내는 곳의 보유가 두 배로 잡힌다.
    """
    z = zipfile.ZipFile(io.BytesIO(fetch(url)))
    sub = read_tsv(z, "SUBMISSION.tsv")
    period = {}
    for s in sub:
        period[s["PERIODOFREPORT"]] = period.get(s["PERIODOFREPORT"], 0) + 1
    per = max(period.items(), key=lambda kv: kv[1])[0] if period else None
    if not per:
        return None, {}

    cover = {c["ACCESSION_NUMBER"]: c for c in read_tsv(z, "COVERPAGE.tsv")}
    summ = {s["ACCESSION_NUMBER"]: s for s in read_tsv(z, "SUMMARYPAGE.tsv")}

    # (cik) → 채택할 accession들. 원본 1개 + NEW HOLDINGS 수정보고 n개, RESTATEMENT면 교체.
    base, adds = {}, {}
    for s in sub:
        if s["PERIODOFREPORT"] != per:
            continue
        cik = int(str(s["CIK"]).lstrip("0") or 0)
        if cik not in GURUS:
            continue
        a, typ = s["ACCESSION_NUMBER"], s["SUBMISSIONTYPE"]
        if typ == "13F-HR":
            base[cik] = a
        elif typ == "13F-HR/A":
            at = (cover.get(a) or {}).get("AMENDMENTTYPE", "").upper()
            if "RESTATE" in at:
                base[cik] = a
            else:
                adds.setdefault(cik, []).append(a)

    want = {}
    for cik, a in base.items():
        want[a] = cik
    for cik, arr in adds.items():
        if cik in base:
            for a in arr:
                want[a] = cik

    out = {}
    for cik, a in base.items():
        sm = summ.get(a) or {}
        out[cik] = {"name": (cover.get(a) or {}).get("FILINGMANAGER_NAME", ""),
                    "total_val": _f(sm.get("TABLEVALUETOTAL")),
                    "total_n": int(_f(sm.get("TABLEENTRYTOTAL"))),
                    "holds": {}}

    # INFOTABLE은 압축 해제 350MB가 넘는다 — 리스트로 읽지 않고 흘려보내며 거른다.
    with z.open("INFOTABLE.tsv") as fh:
        for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="ignore"), delimiter="\t"):
            cik = want.get(row.get("ACCESSION_NUMBER"))
            if cik is None:
                continue
            t = cmap.get((row.get("CUSIP") or "").strip())
            if not t:
                continue
            # 콜/풋은 보통주 보유가 아니다 — 섞으면 '몇 주 들고 있나'가 틀린다
            if (row.get("PUTCALL") or "").strip():
                continue
            h = out[cik]["holds"].setdefault(t, {"v": 0.0, "sh": 0.0})
            h["v"] += _f(row.get("VALUE"))
            h["sh"] += _f(row.get("SSHPRNAMT"))
    return per, out


def _iso(p):
    """'31-MAR-2026' → '2026-03-31'."""
    try:
        return dt.datetime.strptime(str(p), "%d-%b-%Y").date().isoformat()
    except ValueError:
        return str(p)


def main() -> int:
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        st = json.load(f)
    uni = [s["t"] for s in st["stocks"]]
    names = {s["t"]: s.get("name") or "" for s in st["stocks"]}

    print("CUSIP→티커 매핑(FTD) 수집…")
    cmap = cusip_map(uni)
    covered = len(set(cmap.values()))
    print("  CUSIP %d개 · 유니버스 커버 %d/%d (%.1f%%)" % (len(cmap), covered, len(uni), covered / len(uni) * 100))
    if covered / len(uni) < 0.9:
        print("❌ CUSIP 매핑 커버가 90%% 미만 — 갱신 중단(이전본 유지)")
        return 1

    zips = latest_13f(2)
    if not zips:
        print("❌ 13F ZIP 링크를 찾지 못했다 — 인덱스 페이지 구조가 바뀌었을 수 있다. 갱신 중단")
        return 1
    print("대상 창: " + " · ".join(e for e, _ in zips))

    cur_per, cur = read_quarter(zips[0][1], cmap)
    print("이번 분기 %s — 명단 중 보고한 곳 %d/%d" % (cur_per, len(cur), len(GURUS)))
    prev_per, prev = (None, {})
    if len(zips) > 1:
        prev_per, prev = read_quarter(zips[1][1], cmap)
        print("직전 분기 %s — %d곳" % (prev_per, len(prev)))

    if not cur:
        print("❌ 이번 분기 수집 0곳 — 갱신 중단(이전본 유지)")
        return 1

    managers, overlap = [], {}
    for cik, d in sorted(cur.items(), key=lambda kv: -sum(h["v"] for h in kv[1]["holds"].values())):
        p = (prev.get(cik) or {}).get("holds") or {}
        rows = []
        for t, h in d["holds"].items():
            before = p.get(t)
            if before is None:
                chg = "신규" if prev_per and prev.get(cik) else ""
            else:
                # 주식 수로 비교한다 — 평가액은 안 팔아도 주가로 움직인다
                d_sh = h["sh"] - before["sh"]
                base_sh = before["sh"] or 1
                chg = ("증가" if d_sh / base_sh > 0.02 else
                       "감소" if d_sh / base_sh < -0.02 else "유지")
            rows.append({"t": t, "nm": names.get(t, ""), "v": round(h["v"], 0),
                         "sh": round(h["sh"], 0), "chg": chg,
                         "psh": round(before["sh"], 0) if before else None})
        # 전량 매도 — 직전에 있었는데 이번에 없는 것
        if prev.get(cik):
            for t, h in p.items():
                if t not in d["holds"]:
                    rows.append({"t": t, "nm": names.get(t, ""), "v": 0, "sh": 0,
                                 "chg": "전량매도", "psh": round(h["sh"], 0)})
        rows.sort(key=lambda r: -r["v"])
        rows = rows[:KEEP_HOLD]
        uni_val = sum(r["v"] for r in rows)
        managers.append({
            "cik": cik, "label": GURUS[cik], "filer": d["name"],
            "total_val": round(d["total_val"], 0), "total_n": d["total_n"],
            "uni_val": round(uni_val, 0),
            "uni_pct": round(uni_val / d["total_val"] * 100, 1) if d["total_val"] else None,
            "n": len(rows), "holds": rows,
        })
        for r in rows:
            if r["chg"] == "전량매도":
                continue
            overlap.setdefault(r["t"], []).append(cik)

    ov = [{"t": t, "n": len(v), "ciks": sorted(v), "nm": names.get(t, "")}
          for t, v in overlap.items()]
    ov.sort(key=lambda x: (-x["n"], x["t"]))

    doc = {
        "note": "SEC Form 13F 분기 데이터셋. 롱온리 미국 상장주식만, 분기말 기준, 45일 뒤 제출. "
                "변동은 분기말 잔고의 차이지 매매 기록이 아니다. 명단은 랩이 CIK로 고른 것이다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": _iso(cur_per),
        "prev_as_of": _iso(prev_per) if prev_per else None,
        "n_managers": len(managers),
        "n_listed": len(GURUS),
        "cusip_cover": round(covered / len(uni) * 100, 1),
        "managers": managers,
        "overlap": ov,
        "limits": [
            "13F는 롱온리 미국 상장주식만 담는다 — 공매도·현금·채권·해외주식이 빠져 있어 "
            "'이 사람의 포트폴리오'가 아니라 '보고 대상만 본 것'이다.",
            "분기말 기준으로 45일 뒤에 낸다. 화면을 보는 시점엔 최대 4.5개월 묵은 숫자이고, "
            "수집을 자주 해도 줄지 않는다.",
            "변동은 분기말 잔고의 차이다 — 분기 중에 샀다 판 것은 아예 안 보인다. "
            "평가액은 안 팔아도 주가로 움직이므로 주식 수로 비교한다.",
            "이 랩의 유니버스(518종목)와 겹치는 부분만 본다. 각 운용사의 보고 총액 대비 비중을 함께 적는다.",
            "명단은 랩이 골랐다. 널리 알려졌다는 뜻이지 잘한다는 뜻이 아니며, 이 랩은 이들의 성과를 "
            "검증한 적이 없다. 13F 보고총액 1위는 BlackRock·Vanguard 같은 인덱스·수탁사다.",
            "CUSIP→티커는 SEC 공매도 미결제(FTD) 파일로 잇는다. 거기 없는 종목은 빠진다.",
        ],
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    sz = os.path.getsize(OUT) / 1024
    print("거장 %d곳 · 유니버스 보유 %d건 · 공통보유 %d종목 · %.0fKB"
          % (len(managers), sum(m["n"] for m in managers), len(ov), sz))
    for m in managers[:5]:
        print("   %-26s 보고 %6.0f억$ · 유니버스 %5.1f%% · %d종목"
              % (m["label"], m["total_val"] / 1e8, m["uni_pct"] or 0, m["n"]))
    top = ov[:5]
    if top:
        print("   공통 보유 상위: " + " · ".join("%s(%d곳)" % (x["t"], x["n"]) for x in top))
    miss = [GURUS[c] for c in GURUS if c not in cur]
    if miss:
        print("⚠ 이번 분기 보고 없음 %d곳: %s" % (len(miss), ", ".join(miss)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
