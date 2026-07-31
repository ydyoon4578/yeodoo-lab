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
import statistics
import sys
import urllib.request
import zipfile
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru.json")

IDX_13F = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
IDX_FTD = "https://www.sec.gov/data/foiadocsfailsdatahtm"
FTD_FILES = 2        # CUSIP↔티커 커버를 올리려고 최근 몇 개를 합칠지
KEEP_HOLD = 90       # 운용사별로 남길 보유 종목 수(평가액순).
# 유니버스 밖 종목까지 담게 되면서 60칸으로는 큰 운용사가 상위만 남고 잘린다.

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
    full = {}          # 유니버스 밖까지 포함한 CUSIP→심볼. 거장 포트폴리오에서 쓴다.
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
                if not c or not s:
                    continue
                full.setdefault(c, s)
                t = alias.get(s)
                if t:
                    out.setdefault(c, t)
    cusip_map.full = full          # 부수 산출물 — 반환 계약은 그대로 둔다(호출부가 셋이다)
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


def edgar_quarters(cmap: dict):
    """운용사별 EDGAR 제출에서 최근 두 분기를 읽는다. 반환 계약은 read_quarter와 같다
    — (기준분기, {cik: {name, total_val, total_n, holds:{ticker:{v,sh}}}}).

    벌크 데이터셋과 다른 점 두 가지를 알고 써야 한다.
      · 수정보고 처리: 같은 보고분기에 여러 제출이 있으면 **가장 나중 것**을 쓴다.
        벌크 경로의 RESTATEMENT/NEW HOLDINGS 구분보다 단순하지만, 최신 제출이 완전한
        보고인 경우가 대부분이라 실무상 같은 결과가 된다.
      · total_val/total_n은 표지(primary_doc) 대신 정보표 합으로 낸다.
    """
    import refresh_13f_history as H13
    per_cik = {}
    periods = set()
    for cik in GURUS:
        try:
            fl = H13.filings(cik)
        except Exception:
            continue
        best = {}
        for rd, acc, _form in sorted(fl):
            best[rd] = acc          # 같은 분기면 나중 제출이 덮는다
        if best:
            per_cik[cik] = best
            periods.update(best)
    if not periods:
        return None, None
    want = sorted(periods)[-2:][::-1]      # 최신, 그다음
    out = []
    for per in want:
        got = {}
        for cik, best in per_cik.items():
            if per not in best:
                continue
            try:
                rows = H13.holdings(cik, best[per])
            except Exception:
                rows = []
            if not rows:
                continue
            holds, tot_v, tot_n = {}, 0.0, 0
            full = getattr(cusip_map, "full", {})
            for cu, val, sh, nm in rows:
                tot_v += val; tot_n += 1
                t = cmap.get(cu)
                off = False
                if not t:
                    # 유니버스 밖. 버리지 않고 담되 표시한다 — 버리면 그 운용사 포트폴리오의
                    # 절반이 화면에서 사라지고, 남은 절반의 비중이 실제보다 커 보인다.
                    # 티커는 FTD 전체 지도에서 찾고(없으면 CUSIP), 이름은 13F 원문에서 온다.
                    t = full.get(cu) or ("#" + cu)
                    off = True
                h = holds.setdefault(t, {"v": 0.0, "sh": 0.0, "off": off, "nm": nm})
                h["v"] += val; h["sh"] += sh
                if nm and not h.get("nm"):
                    h["nm"] = nm
            if holds:
                got[cik] = {"name": GURUS[cik], "total_val": tot_v,
                            "total_n": tot_n, "holds": holds}
        out.append((per, got))
    while len(out) < 2:
        out.append((None, {}))
    print("EDGAR 직접 수집 — %s %d곳 · %s %d곳"
          % (out[0][0], len(out[0][1]), out[1][0], len(out[1][1])))
    return out[0], out[1]


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
            # 콜/풋은 보통주 보유가 아니다 — 섞으면 '몇 주 들고 있나'가 틀린다
            if (row.get("PUTCALL") or "").strip():
                continue
            cu = (row.get("CUSIP") or "").strip()
            t = cmap.get(cu)
            off = False
            if not t:
                t = getattr(cusip_map, "full", {}).get(cu) or ("#" + cu)
                off = True
            h = out[cik]["holds"].setdefault(
                t, {"v": 0.0, "sh": 0.0, "off": off,
                    "nm": (row.get("NAMEOFISSUER") or "").strip()})
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

    # ── 공급원 선택 ────────────────────────────────────────────────────
    # SEC 벌크 데이터셋은 '제출일 3개월 창' 단위로, 창이 닫히고도 약 8주 뒤에 공개된다.
    # 그래서 6월말 보유(8/14 제출 마감)는 10월 말에야 들어온다.
    # 운용사별 EDGAR 제출을 직접 읽으면 제출 당일부터 보인다 — 같은 자료를 2개월 반 먼저 본다.
    # 벌크가 더 최신이거나 EDGAR가 실패하면 자동으로 벌크로 내려간다(그쪽이 검증된 경로다).
    edgar_cur = edgar_prev = None
    try:
        edgar_cur, edgar_prev = edgar_quarters(cmap)
    except Exception as e:
        print("⚠ EDGAR 직접 수집 실패(%s) — 벌크 데이터셋으로 진행" % e)

    zips = latest_13f(2)
    if not zips:
        print("❌ 13F ZIP 링크를 찾지 못했다 — 인덱스 페이지 구조가 바뀌었을 수 있다. 갱신 중단")
        return 1
    print("대상 창: " + " · ".join(e for e, _ in zips))

    cur_per, cur = read_quarter(zips[0][1], cmap)
    print("벌크 이번 분기 %s — 명단 중 보고한 곳 %d/%d" % (cur_per, len(cur), len(GURUS)))
    prev_per, prev = (None, {})
    if len(zips) > 1:
        prev_per, prev = read_quarter(zips[1][1], cmap)
        print("벌크 직전 분기 %s — %d곳" % (prev_per, len(prev)))

    # ⚠ 두 경로의 분기 표기가 다르다 — EDGAR는 '2026-03-31', 벌크는 '31-MAR-2026'.
    #   문자열로 비교하면 '2026-06-30' < '31-MAR-2026'이 되어 **Q2가 와도 벌크를 계속 쓴다**
    #   (지금은 우연히 맞는 답이 나오지만, 새 분기가 뜨는 순간 조용히 틀린다).
    _MON = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

    def _iso(p_):
        if not p_:
            return ""
        p_ = str(p_).strip()
        m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", p_)
        if m:
            return "%s-%02d-%02d" % (m.group(3), _MON[m.group(2).upper()], int(m.group(1)))
        return p_          # 이미 ISO

    # EDGAR가 더 최신 분기를 갖고 있으면 그쪽으로 간다. 같은 분기면 검증된 벌크를 쓴다.
    if edgar_cur and edgar_cur[0] and (not cur_per or _iso(edgar_cur[0]) > _iso(cur_per)):
        print("→ EDGAR 직접 수집이 더 최신(%s > %s) — 그쪽을 쓴다" % (edgar_cur[0], cur_per))
        cur_per, cur = edgar_cur
        if edgar_prev and edgar_prev[0]:
            prev_per, prev = edgar_prev
    else:
        print("→ 벌크 데이터셋 사용(EDGAR %s · 벌크 %s → ISO %s vs %s)"
              % (edgar_cur[0] if edgar_cur else "없음", cur_per,
                 _iso(edgar_cur[0]) if edgar_cur else "—", _iso(cur_per)))

    if not cur:
        print("❌ 이번 분기 수집 0곳 — 갱신 중단(이전본 유지)")
        return 1

    # ── 제출 단위 정규화(천$ → 달러) ──────────────────────────────────────
    # 🚨 13F 정보표의 VALUE 는 2023년 규칙 변경 전까지 **천 달러** 단위였고, 지금도 그 눈금으로
    #   내는 운용사가 남아 있다. 정규화 없이 합산하면 total_val·holds[].v 가 운용사마다 단위가
    #   1000배 다른 필드가 된다.
    #   2026-07-31 실측(기준 2026-03-31): 17곳 중 2곳(바우포스트·듀케인)이 천$였고, guru.html 에
    #   "$5M"(실제 $5.1B) · 아마존 주당 $0.21 이 아무 배지 없이 나가고 있었다. 겹침 비율(%)은
    #   스케일 불변이라 정상으로 보여 오래 안 들켰다.
    #   ⚠ 운용사 명단을 하드코딩하면 틀린다 — 시기에 따라 바뀐다(히말라야는 2024-06-30 에 전환했다).
    #   판정 근거는 **우리 가격 패널의 분기말 종가**다. 내재주가(VALUE/SSHPRNAMT)를 종가로 나눈
    #   중앙비가 달러면 ~1, 천$면 ~0.001 이라 세 자릿수가 벌어져 오판 여지가 없다.
    #   (내재주가의 절대 수준만 보는 방식은 쓰지 않는다 — 천$ 로 낸 고가주 위주 제출이 1을 넘겨
    #    달러로 오분류된다.)
    def _closes_at(period, want):
        """보고 기준일 이하 마지막 거래일의 종가. {티커: 종가}. 가격 패널 밖이면 빈 dict."""
        ds = st.get("pxd_dates") or []
        iso_ = _iso(period)
        idx = max((i for i, d_ in enumerate(ds) if d_ <= iso_), default=None)
        if idx is None:
            return {}
        got = {}
        for t in want:
            try:
                with io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8") as fh_:
                    px = json.load(fh_).get("pxd") or []
                if idx < len(px) and px[idx]:
                    got[t] = float(px[idx])
            except Exception:
                pass
        return got

    def _med_ratio(holds, closes):
        """내재주가 ÷ 실제 종가의 중앙값. 표본이 3종목 미만이면 None."""
        rat = []
        for t, h in holds.items():
            if h.get("off") or not h.get("sh") or not h.get("v"):
                continue
            c = closes.get(t)
            if c and c > 0:
                rat.append((h["v"] / h["sh"]) / c)
        return (statistics.median(rat), len(rat)) if len(rat) >= 3 else (None, len(rat))

    def _renorm(book, period, tag):
        want = {t for d_ in book.values() for t, h in d_["holds"].items() if not h.get("off")}
        closes = _closes_at(period, want)
        scaled, unknown, bad = 0, [], []
        for cik, d_ in book.items():
            m_, n_ = _med_ratio(d_["holds"], closes)
            tv = d_.get("total_val") or 0
            if m_ is not None:
                sc, why = (1000.0 if m_ < 0.02 else 1.0), "종가 대조 %d종목 중앙비 %.5f" % (n_, m_)
            else:
                # 가격 대조 표본이 모자란 제출(채권 위주 등)은 **보고 규모**로 가른다.
                #   13F 는 13F증권 1억$ 이상일 때 내는 보고다. 그래서
                #     · 보고총액이 1억$ 미만이면 달러일 수 없다 → 천$
                #     · ×1000 이 5조$ 를 넘으면 천$ 일 수 없다(최대 신고자도 4조$대) → 달러
                #   그 사이는 못 가른다. 그때만 경고하고 원값을 둔다(오판보다 낫다).
                if tv and tv < 1e8:
                    sc, why = 1000.0, "가격 대조 %d종목뿐 · 보고총액 %.1f백만 = 13F 하한 미만" % (n_, tv / 1e6)
                elif tv and tv * 1000 > 5e12:
                    sc, why = 1.0, "가격 대조 %d종목뿐 · ×1000 이면 %.1f조$ — 최대 신고자를 넘는다" % (n_, tv * 1000 / 1e12)
                else:
                    unknown.append("%s(대조 %d종목 · 총액 %.2g)" % (d_.get("name") or cik, n_, tv))
                    continue
            if sc != 1.0:
                d_["total_val"] = tv * sc
                for h in d_["holds"].values():
                    h["v"] *= sc
                scaled += 1
                print("  · %s: 천$ 제출 → ×1000 (%s)" % (d_.get("name") or cik, why))
            # 정규화 뒤에도 종가와 2배 넘게 어긋나면 그건 우리가 모르는 눈금이다.
            if m_ is not None and not (0.5 <= m_ * sc <= 2.0):
                bad.append("%s(중앙비 %.3f · %d종목)" % (d_.get("name") or cik, m_ * sc, n_))
        if unknown:
            print("  ⚠ %s 단위 판정 불가 %d곳(가격 대조도 규모 판정도 못 함): %s"
                  % (tag, len(unknown), ", ".join(unknown[:5])))
        return scaled, bad

    try:
        _sc, _bad = _renorm(cur, cur_per, "이번 분기")
        if prev:
            _renorm(prev, prev_per, "직전 분기")
        # 정규화 뒤에도 종가와 2배 넘게 어긋나는 제출이 있으면 그건 우리가 모르는 눈금이다.
        # 조용히 내보내면 이번과 똑같은 사고가 다른 배수로 반복된다.
        if _bad:
            print("❌ 정규화 뒤에도 종가와 어긋나는 제출: " + " · ".join(_bad))
            print("   갱신 중단(이전본 유지) — 13F VALUE 눈금 규약을 다시 확인할 것")
            return 1
        print("  단위 정규화: %d곳 ×1000 · 나머지 달러" % _sc)
    except Exception as e:
        print("❌ 제출 단위 정규화 실패: %s — 갱신 중단(이전본 유지)" % e)
        return 1

    managers, overlap, OFFNM = [], {}, {}
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
            rows.append({"t": t, "nm": names.get(t) or h.get("nm") or "",
                         "v": round(h["v"], 0),
                         "sh": round(h["sh"], 0), "chg": chg,
                         "off": 1 if h.get("off") else 0,
                         "psh": round(before["sh"], 0) if before else None})
        # 전량 매도 — 직전에 있었는데 이번에 없는 것
        if prev.get(cik):
            for t, h in p.items():
                if t not in d["holds"]:
                    rows.append({"t": t, "nm": names.get(t) or h.get("nm") or "", "v": 0, "sh": 0,
                                 "chg": "전량매도", "off": 1 if h.get("off") else 0,
                                 "psh": round(h["sh"], 0)})
        rows.sort(key=lambda r: -r["v"])
        # ⚠ 겹침은 **자르기 전 전체**로 센다. 예전엔 rows[:KEEP_HOLD] 뒤에 합산했는데,
        #   분자(유니버스 안 보유)만 상위 90개로 잘리고 분모(total_val)는 전체라서
        #   보유 종목이 90개를 넘는 운용사의 겹침이 조용히 과소 표기됐다.
        #   실측 오차: 브리지워터 43.0%→52.4%(+9.4%p) · 소로스 25.6%→32.9% · 마클 67.8%→69.5% ·
        #   듀케인 10.7%→11.9% · 오크트리 10.3%→11.1% · 아크 46.2%→46.7%.
        #   90개 이하인 나머지 11사는 차이 0.0%p라 아무도 눈치채지 못했다.
        uni_val = sum(r["v"] for r in rows if not r.get("off"))
        off_n = sum(1 for r in rows if r.get("off"))
        full = rows                  # 겹침은 이걸로 센다 — 아래 자르기 전 목록이다
        rows = rows[:KEEP_HOLD]      # 화면에 싣는 목록만 자른다(집계는 위에서 끝냈다)
        managers.append({
            "cik": cik, "label": GURUS[cik], "filer": d["name"],
            "total_val": round(d["total_val"], 0), "total_n": d["total_n"],
            "uni_val": round(uni_val, 0),
            "uni_pct": round(uni_val / d["total_val"] * 100, 1) if d["total_val"] else None,
            "n": len(rows), "n_off": off_n, "holds": rows,
        })
        # ⚠ full 을 돈다. 위 주석대로 '자르기 전 전체'로 세야 하는데 이 루프만 rows(잘린 것)를
        #   돌고 있었다 — uni_val·off_n 만 고쳐 두고 정작 겹침은 그대로였다(2026-07-28 발견).
        #   보유가 90개를 넘는 운용사는 상위 90개 밖의 종목이 겹침에 아예 안 잡혔다.
        #   브리지워터는 유니버스 안 보유가 355종목인데 그중 상위 90개(유니버스 밖 포함)만 셌다.
        for r in full:
            if r["chg"] == "전량매도":
                continue
            overlap.setdefault(r["t"], []).append(cik)
            # 유니버스 밖 표시도 여기서 같이 모은다. 예전처럼 managers[].holds(잘린 목록)로
            # 만들면, 겹침에는 들어왔는데 어느 운용사의 상위 90개에도 없는 종목이 off=0 으로
            # 찍혀 **유니버스 안 종목으로 둔갑한다**(브리지워터의 유니버스 밖 830종목이 그렇다).
            if r.get("off") and r.get("nm"):
                OFFNM.setdefault(r["t"], r["nm"])
    ov = [{"t": t, "n": len(v), "ciks": sorted(v),
           "nm": names.get(t) or OFFNM.get(t, ""), "off": 1 if t in OFFNM else 0}
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
        "n_off": sum(m.get("n_off") or 0 for m in managers),
        "off_note": "‘밖’ 표시는 이 랩의 유니버스(S&P 500 ∪ NASDAQ 100, 518종목) 밖 종목이다. "
                    "이름은 13F 원문(nameOfIssuer)에서, 티커는 SEC 공매도 미결제 파일에서 "
                    "찾은 것이라 티커가 없으면 CUSIP을 그대로 적는다. 이 사이트에는 그 종목의 "
                    "가격·재무 화면이 없다 — 무엇을 들고 있는지만 보여준다.",
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
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "13F 보유")
