#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC EDGAR submissions → 공시 피드 · 산업 분류 · 회사별 제출 이력

메뉴 정본에서 이 소스 하나에 막혀 있던 세 칸을 연다:
  filings.html      8-K 공시 피드      (Item 코드로 분류, 해설 없음)
  co.html#ir        IR자료실           (EDGAR 원문 링크 목록)
  industry.html     산업 탐색          (SIC 4자리 — yfinance 11섹터보다 훨씬 잘다)

── 이 화면들이 지키는 것 ───────────────────────────────────────────────
* **해설을 붙이지 않는다.** 8-K의 분류는 랩이 읽고 판단한 게 아니라 회사가 스스로
  단 Item 번호다. 우리는 그 번호에 한국어 이름만 붙인다.
* **예측하지 않는다.** 어떤 Item이 주가에 어떻게 작용하는지 이 랩은 검증한 적이 없다.
  피드는 '무엇이 제출됐는가'까지만 말한다.
* 원문 링크를 항상 함께 준다 — 우리 요약을 못 믿으면 원문으로 가면 된다.

── 구조적 한계(화면에도 그대로 적는다) ─────────────────────────────────
* submissions의 recent에는 **최근 1,000건 또는 1년치**만 온다. 그보다 오래된 제출은
  별도 파일에 있고 따라가지 않는다(회사당 호출 2배 — 이 화면들엔 그 깊이가 불필요).
* 회사 IR 사이트 주소는 못 만든다. website·investorWebsite 필드가 스키마에는 있지만
  실측 12/12 전부 빈 문자열이었다(2026-07-25). 그래서 EDGAR 원문 링크만 싣는다.
* 8-K는 '보고 의무가 생긴 사건'만 담는다. 회사에 일어난 모든 일이 아니다.

사용: python3 build/refresh_filings.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT_FEED = os.path.join(DATA, "filings.json")
OUT_IND = os.path.join(DATA, "industry.json")
DIR_CO = os.path.join(DATA, "fil")

FEED_DAYS = 90           # 8-K 피드 창(일). 넓히면 파일만 커지고 화면은 안 좋아진다.
CO_FORMS_MAX = 30        # 회사별로 남길 제출 건수 상한
# IR자료실에 담을 서식. Form 3/4/5·144는 건수가 압도적인데 IR 자료가 아니라 뺀다
# (내부자 거래는 co.html#ins 칸이 따로 있고 소스도 분기 ZIP으로 다르다).
CO_FORMS = ("10-K", "10-Q", "8-K", "DEF 14A", "DEFA14A", "20-F", "40-F", "6-K",
            "11-K", "S-1", "S-3", "S-4", "S-8", "ARS", "SD", "25", "15-12B")
# 서식 한국어 이름. 없는 서식은 원문 코드를 그대로 쓴다(모르는 걸 아는 척하지 않는다).
MIN_IR_FORMS = 6        # 이보다 적으면 '등록 법인이 바뀐 것 아닌가'를 의심한다(아래 참조)

# ── 티커가 새 등록 법인으로 넘어간 경우의 전신 CIK ──────────────────────
# 회사가 지주회사로 전환하면 SEC상 **새 CIK**가 만들어지고, company_tickers.json은
# 그 새 법인만 가리킨다. 옛 법인의 10-K·10-Q·DEF 14A는 그대로 남아 있지만 티커로는
# 더 이상 닿지 않는다 — SEC가 둘을 잇는 포인터를 주지 않기 때문이다.
#
# 실측(2026-07-25): XOM → CIK 2115436 'ExxonMobil Holdings Corp'. 최초 제출 2026-07-01,
#   전체 26건, IR 서식은 8-K 한 건뿐. 전신 CIK 34088 'EXXON MOBIL CORP'에 10-Q(05-04)·
#   DEF 14A(04-08)를 포함해 1,001건이 있다. 둘 다 자기 메타데이터에 티커 XOM을 적지만
#   company_tickers.json에는 중복 항목이 없어(10,429개 전수 확인) 자동으로는 못 찾는다.
#
# 그래서 손으로 적는다. 대신 **빠뜨리면 조용히 넘어가지 않게** 아래 MIN_IR_FORMS 검사가
# 이력이 빈약한 종목을 잡아 경고한다 — 다음에 같은 일이 생기면 잡 로그에 뜬다.
PREDECESSOR = {
    "XOM": [34088],
}

FORM_KO = {
    "10-K": "연차보고서", "10-Q": "분기보고서", "8-K": "수시공시",
    "DEF 14A": "주주총회 위임장", "DEFA14A": "위임장 추가자료",
    "20-F": "외국기업 연차보고서", "40-F": "캐나다기업 연차보고서", "6-K": "외국기업 수시보고",
    "11-K": "종업원지주 연차보고서", "S-1": "증권신고서", "S-3": "일괄신고서",
    "S-4": "합병·교환 신고서", "S-8": "주식보상 등록", "ARS": "주주용 연차보고서",
    "SD": "분쟁광물 공시", "25": "상장폐지 신고", "15-12B": "등록말소 신고",
}


def load_universe():
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        d = json.load(f)
    return [(s["t"], s.get("name") or "", s.get("sector") or "") for s in d["stocks"]], d.get("as_of")


def main() -> int:
    uni, px_asof = load_universe()
    cmap = edgar.ticker_cik_map()
    if not cmap:
        print("❌ ticker→CIK 매핑 실패 — 갱신 중단(이전본 유지)")
        return 1

    today = dt.date.today()
    cutoff = (today - dt.timedelta(days=FEED_DAYS)).isoformat()

    feed, ind_rows, co_docs = [], [], {}
    miss_cik, miss_sub, thin = [], [], []
    n_pred = 0

    for i, (t, name, sector) in enumerate(uni, 1):
        cik = cmap.get(t.upper())
        if not cik:
            miss_cik.append(t)
            continue
        # 현행 법인 + (있으면) 전신 법인. 제출은 각자의 CIK 아래에 있으므로 행마다
        # 출처 CIK를 달고 다녀야 원문 링크를 되짓을 수 있다.
        sub = edgar.submissions(cik)
        if not sub:
            miss_sub.append(t)
            continue
        rs = [dict(r, _cik=cik) for r in edgar.rows(sub)]
        for pcik in PREDECESSOR.get(t.upper(), []):
            psub = edgar.submissions(pcik)
            if not psub:
                print("⚠ %s 전신 CIK %d 조회 실패 — 현행 법인분만 쓴다" % (t, pcik))
                continue
            rs += [dict(r, _cik=pcik) for r in edgar.rows(psub)]
            n_pred += 1
        # 같은 제출이 양쪽에 잡히는 일은 없어야 하지만, 겹치면 최신 것 하나만 남긴다
        seen_acc, ded = set(), []
        for r in rs:
            acc = str(r.get("accessionNumber") or "")
            if acc and acc in seen_acc:
                continue
            seen_acc.add(acc)
            ded.append(r)
        rs = sorted(ded, key=lambda r: str(r.get("filingDate") or ""), reverse=True)
        sic = str(sub.get("sic") or "").strip()
        sic_desc = str(sub.get("sicDescription") or "").strip()
        ind_rows.append({"t": t, "sic": sic, "sd": sic_desc, "sec": sector,
                         "cik": cik, "nm": sub.get("name") or name})

        # 원문 링크는 통째로 저장하지 않고 조각(accession·주문서명)만 남긴다.
        # 완성된 URL을 넣으면 같은 접두사 60여 글자가 건마다 반복돼 피드가 두 배가 된다
        # (실측 295KB → 조각 저장 시 절반). 링크는 규칙이 고정돼 있어 화면에서 되짓는다.
        keep = []
        for r in rs:
            form = str(r.get("form") or "").strip()
            fdate = str(r.get("filingDate") or "")
            acc = str(r.get("accessionNumber") or "").replace("-", "")
            pdoc = str(r.get("primaryDocument") or "")
            # 출처 CIK가 대표와 다를 때만 행에 적는다(전신 법인분). 같으면 생략해 파일을 줄인다.
            rcik = r.get("_cik")
            extra = {} if rcik == cik else {"c": rcik}
            if form == "8-K" and fdate >= cutoff:
                feed.append(dict({"t": t, "d": fdate, "rd": str(r.get("reportDate") or ""),
                                  "it": edgar.parse_items(r.get("items")), "a": acc, "p": pdoc}, **extra))
            if form in CO_FORMS and len(keep) < CO_FORMS_MAX:
                keep.append(dict({"f": form, "d": fdate, "rd": str(r.get("reportDate") or ""),
                                  "a": acc, "p": pdoc,
                                  "it": edgar.parse_items(r.get("items")) if form == "8-K" else []}, **extra))
        co_docs[t] = {
            "t": t, "cik": cik, "nm": sub.get("name") or name,
            "sic": sic, "sd": sic_desc,
            "fy": str(sub.get("fiscalYearEnd") or ""),
            "st": str(sub.get("stateOfIncorporationDescription") or ""),
            "ex": sub.get("exchanges") or [],
            "n_recent": len(rs),
            "filings": keep,
        }
        # S&P 대형주가 IR 서식 몇 건뿐일 리 없다 — 그런 종목은 등록 법인이 바뀐 것이고
        # PREDECESSOR에 전신 CIK가 빠져 있다는 뜻이다. 화면에도 그 사실을 적는다.
        if len(keep) < MIN_IR_FORMS:
            co_docs[t]["thin"] = 1
            thin.append((t, len(keep), sub.get("name") or ""))
        if i % 100 == 0:
            print("  … %d/%d" % (i, len(uni)))

    if not ind_rows:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1

    feed.sort(key=lambda x: (x["d"], x["t"]), reverse=True)
    as_of = feed[0]["d"] if feed else today.isoformat()

    # ── 8-K 피드 ────────────────────────────────────────────────────────
    doc = {
        "note": "SEC EDGAR submissions API 수집분. 8-K 원문 피드 — 해설을 붙이지 않는다. "
                "분류는 랩의 판단이 아니라 회사가 스스로 단 Item 번호다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": as_of,
        "window_days": FEED_DAYS,
        "n_co": len(ind_rows),
        "n": len(feed),
        "items": edgar.ITEM8K,
        "major": list(edgar.ITEM8K_MAJOR),
        # 링크 복원 규칙과 재료. 화면은 doc_base + cik + '/' + a + '/' + p 로 원문에 간다.
        # p가 비면 SEC가 주 문서를 안 준 제출이므로 제출 인덱스(idx_base)로 보낸다.
        "doc_base": "https://www.sec.gov/Archives/edgar/data/",
        "cik": {r["t"]: r["cik"] for r in ind_rows},
        "limits": [
            "recent 창은 최근 1,000건 또는 1년치다. 그보다 오래된 제출은 따라가지 않는다.",
            "8-K는 보고 의무가 생긴 사건만 담는다 — 회사에 일어난 모든 일이 아니다.",
            "Item이 주가에 어떻게 작용하는지 이 랩은 검증한 적이 없다. 피드는 무엇이 제출됐는지까지만 말한다.",
        ],
        "feed": feed,
    }
    io.open(OUT_FEED, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ── 산업(SIC) ───────────────────────────────────────────────────────
    groups = {}
    for r in ind_rows:
        if not r["sic"]:
            continue
        g = groups.setdefault(r["sic"], {"sic": r["sic"], "sd": r["sd"], "ts": []})
        g["ts"].append(r["t"])
    ind = {
        "note": "SEC가 회사에 부여한 SIC 4자리 산업분류. yfinance의 11섹터보다 잘아, "
                "'같은 섹터인데 하는 일이 다른' 회사를 갈라 본다. 랩의 분류가 아니라 SEC 부여값이다.",
        "generated": doc["generated"],
        "as_of": as_of,
        "n_co": len(ind_rows),
        "n_sic": len(groups),
        "no_sic": [r["t"] for r in ind_rows if not r["sic"]],
        "groups": sorted(groups.values(), key=lambda g: (-len(g["ts"]), g["sic"])),
        "co": {r["t"]: [r["sic"], r["sd"], r["cik"]] for r in ind_rows},
    }
    io.open(OUT_IND, "w", encoding="utf-8").write(
        json.dumps(ind, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ── 회사별 제출 이력 ────────────────────────────────────────────────
    # ⚠ 이 파일들에는 실행 타임스탬프를 넣지 않는다. 주 1회 갱신인데 대부분의 회사는
    #   그 주에 제출이 없다 — 타임스탬프를 박으면 내용이 같아도 518파일이 매주 전부
    #   '변경'으로 잡혀 커밋이 무의미하게 부풀고, 무엇이 실제로 바뀌었는지 안 보인다.
    #   내용이 같으면 아예 쓰지 않아 mtime도 건드리지 않는다.
    os.makedirs(DIR_CO, exist_ok=True)
    n_new = n_upd = 0
    for t, d in co_docs.items():
        d["forms_ko"] = {k: v for k, v in FORM_KO.items() if any(f["f"] == k for f in d["filings"])}
        fn = os.path.join(DIR_CO, "%s.json" % t.replace("/", "_"))
        body = json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n"
        old = None
        if os.path.exists(fn):
            try:
                old = io.open(fn, encoding="utf-8").read()
            except Exception:
                old = None
        if old is None:
            n_new += 1
        elif old == body:
            continue
        else:
            n_upd += 1
        io.open(fn, "w", encoding="utf-8").write(body)

    # 유니버스에서 빠진 종목의 파일은 지운다 — 남겨두면 폐지 종목이 영원히 남는다
    # (data/sd/ 가 쓰는 규칙과 같다).
    n_del = 0
    for fn in os.listdir(DIR_CO):
        if fn.endswith(".json") and fn[:-5] not in co_docs:
            os.remove(os.path.join(DIR_CO, fn))
            n_del += 1

    sz_feed = os.path.getsize(OUT_FEED) / 1024
    sz_ind = os.path.getsize(OUT_IND) / 1024
    sz_co = sum(os.path.getsize(os.path.join(DIR_CO, f)) for f in os.listdir(DIR_CO)) / 1024
    print("8-K 피드: %d건 · %d사 · 최근 %d일 · 기준일 %s · %.0fKB"
          % (len(feed), len(ind_rows), FEED_DAYS, as_of, sz_feed))
    print("산업(SIC): %d개 분류 · %.0fKB · SIC 없음 %d사" % (ind["n_sic"], sz_ind, len(ind["no_sic"])))
    print("회사별 제출: %d파일 · %.0fKB (평균 %.1fKB) — 신규 %d · 변경 %d · 삭제 %d"
          % (len(co_docs), sz_co, sz_co / max(1, len(co_docs)), n_new, n_upd, n_del))
    if n_pred:
        print("전신 법인 병합: %d종목 (%s)" % (n_pred, ", ".join(sorted(PREDECESSOR))))
    if miss_cik:
        print("⚠ CIK 미매칭 %d종목: %s" % (len(miss_cik), ", ".join(miss_cik[:10])))
    if miss_sub:
        print("⚠ submissions 실패 %d종목: %s" % (len(miss_sub), ", ".join(miss_sub[:10])))
    if thin:
        # 실패시키지는 않는다 — 데이터는 맞고(그 법인의 전부다) 화면도 사유를 적는다.
        # 다만 로그에 남겨서, 다음에 같은 일이 생기면 PREDECESSOR에 추가하게 만든다.
        print("⚠ 제출 이력이 빈약한 %d종목 — 등록 법인이 바뀌었는지 확인하고 PREDECESSOR에 전신 CIK를 추가할 것:"
              % len(thin))
        for t, n, nm in thin:
            print("    %-6s IR서식 %d건 · %s" % (t, n, nm))

    # 유니버스의 큰 몫이 빠지면 배포하지 않는다 — 반쪽 피드는 '조용히 틀린' 화면이 된다.
    cover = len(ind_rows) / max(1, len(uni))
    if cover < 0.95:
        print("❌ 커버 %.1f%% (<95%%) — 수집 실패로 보고 중단" % (cover * 100))
        return 1
    print("커버 %.1f%% · 가격 기준일 %s" % (cover * 100, px_asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
