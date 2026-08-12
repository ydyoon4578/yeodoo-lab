#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC Form 3/4/5 분기 데이터셋 → 회사별 내부자 거래

  co.html#ins  내부자 거래 — 임원·이사·10% 주주의 매매

── 이 화면이 실시간이 될 수 없는 이유(구조적) ──────────────────────────
SEC는 Form 4를 **분기 단위 데이터셋**으로 묶어 내놓는다. 개별 제출은 이틀 안에 올라오지만,
정형화된 표로 묶이는 건 분기가 끝난 뒤다. 그래서 이 경로로 만든 화면에는 **수십 일 지연**이
구조적으로 따라붙는다. 줄일 방법이 이 소스에는 없다(개별 제출을 XML로 긁으면 되지만
그건 회사당 수십 콜이고, 이 랩이 그 부하를 SEC에 걸 이유가 없다).
그래서 만들되 "실시간 내부자 매매"라고 부르지 않는다 — 화면에 실측 지연일을 적는다.

── 이 화면이 지키는 것 ─────────────────────────────────────────────────
* **거래코드를 뭉개지 않는다.** Form 4의 코드는 성격이 전혀 다르다. P(장내매수)·S(장내매도)는
  본인이 고른 거래지만, A(주식보상)·M(옵션행사)·F(세금 대납분 반납)는 보상 제도가 굴러간
  결과다. 이걸 합쳐 "내부자가 샀다/팔았다"로 말하면 그냥 틀린 말이 된다.
  코드를 그대로 두고, '재량 거래(P·S)'만 따로 세어 함께 보여준다.
* **예측하지 않는다.** 내부자 매수가 초과수익으로 이어지는지 이 랩은 검증한 적이 없다.
  점수도 시그널도 만들지 않는다.
* 원문 링크를 항상 함께 준다.

── 실측(2026-07-25) ────────────────────────────────────────────────────
  2026q2 ZIP 28MB · SUBMISSION 56,102건 · 비파생거래 78,328건 · 티커 표기 100%
  ISSUERTRADINGSYMBOL로 티커에 직접 조인된다 — CUSIP 매핑이 필요 없다.
  ⚠ 최신 분기는 /files/datastandardsinnovation/ 아래, 이전 분기는 /files/structureddata/ 아래에
    있다. 경로를 못 박으면 다음 분기에 404가 난다 — 그래서 인덱스 페이지를 훑어 링크를 얻는다.

사용: python3 build/refresh_insider.py
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
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_INS = os.path.join(DATA, "ins")
OUT_SUM = os.path.join(DATA, "insider.json")
OUT_MON = os.path.join(DATA, "ins_monthly.json")   # 종목×월 장내 합계 — 절단 전 원본에서 만든다

INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
QUARTERS = 2          # 최근 몇 분기를 합칠지(2분기 ≈ 6개월)
KEEP_PER_CO = 40      # 회사별 보관 거래 수
FORMS = ("4", "4/A", "5", "5/A")   # 거래가 실린 서식. 3은 최초 보유 신고라 거래가 아니다


def monthly_agg(by_co, latest):
    """{티커: [거래…]} → {티커: {월: 합계}}. 🚨 **보관 상한을 적용하기 전** 원본으로 부를 것.

    ⚠ 함수로 떼어 둔 이유: 이 스크립트 본체는 SEC 를 직접 때리므로 사내 PC 에서 못 돌린다.
      그러면 이 계산은 러너에서 처음 실행되고, 거기서 처음 죽는다(그 잡이 죽으면 그날 수집분이
      통째로 날아간다). 함수로 있으면 손으로 만든 입력으로 로컬에서 먼저 확인할 수 있다.
    ⚠ 중복 제거 키·역할 규칙은 home_insider.py 와 같아야 한다 — (거래일·코드·수량·단가).
    """
    mon = {}
    for t, rows in by_co.items():
        seen = set()
        for r in rows:
            if r.get("c") not in ("P", "S"):
                continue
            d, fd = r.get("d") or "", r.get("fd") or ""
            if not d or d > latest or fd > latest:
                continue
            sh, px = r.get("sh") or 0, r.get("px") or 0
            amt = sh * px
            if amt <= 0:
                continue
            k = (d, r["c"], sh, px)
            if k in seen:
                continue
            seen.add(k)
            m = mon.setdefault(t, {}).setdefault(d[:7], {
                "b": 0.0, "s": 0.0, "nb": 0, "ns": 0, "who": set(), "roles": {}, "days": set()})
            role = _role(r.get("rel"))
            m["roles"][role] = m["roles"].get(role, 0.0) + amt
            m["days"].add(d)
            if r["c"] == "P":
                m["b"] += amt; m["nb"] += 1; m["who"].add(r.get("nm") or "")
            else:
                m["s"] += amt; m["ns"] += 1
    return {t: {mo: {"b": round(v["b"]), "s": round(v["s"]), "nb": v["nb"], "ns": v["ns"],
                     "who": len([x for x in v["who"] if x]),
                     "roles": {k2: round(v2) for k2, v2 in v["roles"].items()},
                     "nd": len(v["days"])}
                for mo, v in ms.items()}
            for t, ms in mon.items()}


def _role(rel: str) -> str:
    """SEC 관계 문자열 → 짧은 역할 태그. 🚨 home_insider.py 의 _role 과 라벨이 같아야 한다 —
    어긋나면 home_insider 가 ins_monthly.json 을 거부하고 죽는다(조용히 틀리지는 않는다).
    겸직은 임원 쪽으로 접는다: 임원·이사를 겸한 10% 주주의 매매는 지분 정리가 아니라
    본인 판단일 수 있어서, '10%주주'로 부르면 틀린 말이 된다."""
    r = rel or ""
    if "Officer" in r:
        return "임원"
    if "Director" in r:
        return "이사"
    if "TenPercentOwner" in r:
        return "10%주주"
    return "기타"

# Form 4 Table I 거래코드. 출처: SEC Form 4 서식 설명(General Instructions).
CODE = {
    "P": "장내매수", "S": "장내매도", "A": "주식보상 수령", "D": "회사에 처분",
    "F": "세금 대납분 반납", "M": "파생 행사·전환", "C": "전환", "X": "옵션 행사",
    "G": "증여", "V": "자발적 조기보고", "J": "기타 취득·처분", "K": "스왑",
    "U": "공개매수 응모", "I": "재량없는 거래", "L": "소액 취득", "W": "상속",
    "Z": "보관신탁 입출",
}
# 본인이 고른 거래. 나머지는 보상 제도·세금 처리·상속 등 '굴러간 결과'다.
DISCRETIONARY = ("P", "S")


def fetch(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": edgar.UA, "Accept-Encoding": "gzip"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw


def latest_zips(n: int):
    """인덱스 페이지에서 최근 n개 분기 ZIP의 절대 URL. 경로가 분기마다 달라 훑어서 얻는다."""
    html = fetch(INDEX_URL, timeout=60).decode("utf-8", "ignore")
    hrefs = re.findall(r'href="([^"]*form345\.zip)"', html)
    out, seen = [], set()
    for h in hrefs:
        m = re.search(r"(\d{4})q(\d)_form345\.zip", h)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        if key in seen:
            continue
        seen.add(key)
        out.append((key, h if h.startswith("http") else "https://www.sec.gov" + h))
    out.sort(reverse=True)
    return [(f"{k[0]}Q{k[1]}", u) for k, u in out[:n]]


def _num(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def _date(x):
    """'29-JUN-2026' → '2026-06-29'. 파싱 실패는 버린다(형식이 바뀌면 조용히 틀리느니 비운다)."""
    s = str(x or "").strip()
    if not s:
        return ""
    try:
        return dt.datetime.strptime(s, "%d-%b-%Y").date().isoformat()
    except ValueError:
        return ""


def _plus_days(iso: str, n: int) -> str:
    try:
        return (dt.date.fromisoformat(iso) + dt.timedelta(days=n)).isoformat()
    except ValueError:
        return iso


def read_tsv(z: zipfile.ZipFile, name: str):
    if name not in z.namelist():
        return []
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="ignore"), delimiter="\t"))


def load_universe():
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        return {s["t"].upper(): s["t"] for s in json.load(f)["stocks"]}


def main() -> int:
    uni = load_universe()
    # SEC 표기는 하이픈(BRK-B), 우리 유니버스는 점(BRK.B)이 섞인다 — 양쪽을 다 키로 둔다
    for k in list(uni):
        uni.setdefault(k.replace(".", "-"), uni[k])
        uni.setdefault(k.replace("-", "."), uni[k])

    zips = latest_zips(QUARTERS)
    if not zips:
        print("❌ 분기 ZIP 링크를 찾지 못했다 — 인덱스 페이지 구조가 바뀌었을 수 있다. 갱신 중단")
        return 1
    print("대상 분기: " + " · ".join(q for q, _ in zips))

    by_co, quarters, bad_date = {}, [], []
    for qname, url in zips:
        blob = fetch(url)
        z = zipfile.ZipFile(io.BytesIO(blob))
        sub = read_tsv(z, "SUBMISSION.tsv")
        # 우리 유니버스 + 거래 서식만 남긴다. 여기서 줄여야 뒤 테이블 조인이 싸진다.
        want = {}
        for s in sub:
            if str(s.get("DOCUMENT_TYPE") or "").strip() not in FORMS:
                continue
            sym = str(s.get("ISSUERTRADINGSYMBOL") or "").strip().upper()
            t = uni.get(sym)
            if not t:
                continue
            want[s["ACCESSION_NUMBER"]] = {"t": t, "filed": _date(s.get("FILING_DATE")),
                                           "cik": str(s.get("ISSUERCIK") or "").lstrip("0")}
        owners = {}
        for o in read_tsv(z, "REPORTINGOWNER.tsv"):
            a = o["ACCESSION_NUMBER"]
            if a not in want or a in owners:
                continue
            owners[a] = {"nm": str(o.get("RPTOWNERNAME") or "").strip(),
                         "rel": str(o.get("RPTOWNER_RELATIONSHIP") or "").strip(),
                         "title": str(o.get("RPTOWNER_TITLE") or "").strip()}
        n_tr = 0
        for r in read_tsv(z, "NONDERIV_TRANS.tsv"):
            a = r["ACCESSION_NUMBER"]
            meta = want.get(a)
            if not meta:
                continue
            code = str(r.get("TRANS_CODE") or "").strip()
            sh, px = _num(r.get("TRANS_SHARES")), _num(r.get("TRANS_PRICEPERSHARE"))
            d = _date(r.get("TRANS_DATE"))
            if not d:
                continue
            # 거래일이 제출일보다 뒤인 건 물리적으로 불가능하다 — Form 4는 거래 후 2영업일
            # 안에 내는 서식이다. 이건 제출자 오타이고, 그대로 두면 '가장 최근 거래일'이
            # 미래로 튄다. 실측(2026-07-25): 18,190건 중 1건(GOOGL, 거래일 2027-01-25 ·
            # 제출 2026-01-27 — 연도 오타). 버리고 세어서 화면에 적는다.
            if meta["filed"] and d > _plus_days(meta["filed"], 3):
                bad_date.append((meta["t"], d, meta["filed"]))
                continue
            ow = owners.get(a) or {}
            by_co.setdefault(meta["t"], []).append({
                "d": d, "fd": meta["filed"], "c": code,
                "ad": str(r.get("TRANS_ACQUIRED_DISP_CD") or "").strip(),   # A=취득 D=처분
                "sh": round(sh, 0) if sh is not None else None,
                "px": round(px, 4) if px is not None else None,
                "own": _num(r.get("SHRS_OWND_FOLWNG_TRANS")),
                "nm": ow.get("nm", ""), "rel": ow.get("rel", ""), "ti": ow.get("title", ""),
                "a": a.replace("-", ""), "k": meta["cik"],
            })
            n_tr += 1
        quarters.append({"q": qname, "n": n_tr})
        print("  %s → 우리 유니버스 거래 %d건 (전체 제출 %d)" % (qname, n_tr, len(sub)))

    if not by_co:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1

    # ── 월별 집계 — 🚨 **절단 전에** 만든다 ──────────────────────────────
    # KEEP_PER_CO 는 회사별 최근 N건만 파일에 남긴다. 거래가 잦은 종목은 그 N건이 최신 달
    # 안에서 끝나 버려, 그 파일만 읽으면 '그 달'이 며칠치가 된다. 실측(2026-06): 21종이
    # 6월 앞부분을 통째로 잃어 6월 금액의 13.2%가 사라졌고, 홈 순매도 4위 AVGO 는 평일
    # 22일 중 10일치(6/17~)만 담긴 채 '2026년 6월 한 달 순금액'으로 표시·정렬됐다.
    # 보정하면 −$261M 이 아니라 −$575M 이고 순위도 4위가 아니라 3위다.
    # 🚨 행을 다 보관하는 것으로는 못 고친다 — 비절단 P·S 만 16,902건이라 저장소가 3배
    #   넘게 부풀고, 그 파일들은 매주 다시 쓰여 git 이력까지 같이 부푼다.
    #   패널이 실제로 쓰는 것은 행이 아니라 **월별 합계**다. 그것만 따로 남긴다(≈수십 KB).
    # ⚠ 중복 제거 키는 home_insider.py 와 같아야 한다 — (거래일·코드·수량·단가).
    #   공동보고(한 거래를 여러 보고자가 각자 제출)를 안 걷어내면 금액이 사람 수만큼 뛴다.
    latest = max((r["d"] for rows in by_co.values() for r in rows), default="")
    mon_doc = monthly_agg(by_co, latest)
    io.open(OUT_MON, "w", encoding="utf-8").write(json.dumps(
        {"note": ("종목×월 장내(P·S) 합계. 🚨 회사별 보관 상한(KEEP_PER_CO) **적용 전** 원본에서 "
                  "만든 것이라, 상한에 걸린 종목도 그 달이 온전하다. data/ins/*.json 을 직접 "
                  "합산하면 안 되는 이유가 이것이다."),
         "as_of": latest, "cap": KEEP_PER_CO, "roles": sorted({r for ms in mon_doc.values()
                                                               for v in ms.values() for r in v["roles"]}),
         "by_t": mon_doc}, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("  월별 합계 → %s (종목 %d)" % (os.path.basename(OUT_MON), len(mon_doc)))

    # ── 회사별 파일 ─────────────────────────────────────────────────────
    os.makedirs(DIR_INS, exist_ok=True)
    n_new = n_upd = 0
    disc_tot, tot = 0, 0
    n_cap = 0
    for t, rows in by_co.items():
        rows.sort(key=lambda r: (r["d"], r["fd"]), reverse=True)
        if len(rows) > KEEP_PER_CO:
            n_cap += 1
        rows = rows[:KEEP_PER_CO]
        doc = {"t": t, "n": len(rows), "codes": {c: CODE[c] for c in {r["c"] for r in rows} if c in CODE},
               "disc": list(DISCRETIONARY), "tr": rows}
        body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        fn = os.path.join(DIR_INS, "%s.json" % t.replace("/", "_"))
        old = io.open(fn, encoding="utf-8").read() if os.path.exists(fn) else None
        if old is None:
            n_new += 1
        elif old == body:
            pass
        else:
            n_upd += 1
        if old != body:
            io.open(fn, "w", encoding="utf-8").write(body)
        for r in rows:
            tot += 1
            if r["c"] in DISCRETIONARY:
                disc_tot += 1
        # ⚠ latest 는 위에서 **비절단 원본**으로 이미 구했다. 여기서 다시 구하지 않는다 —
        #   두 곳에서 같은 값을 만들면 언젠가 갈라진다. (정렬이 최신순이라 값은 어차피 같다.)

    n_del = 0
    for fn in os.listdir(DIR_INS):
        if fn.endswith(".json") and fn[:-5] not in by_co:
            os.remove(os.path.join(DIR_INS, fn))
            n_del += 1

    # 티커별 재량 거래 집계 — 산업 단위 관전 포인트가 이걸 읽는다.
    # 회사별 파일 507개를 화면에서 다 받을 수는 없어, 요약에 압축해 싣는다(≈10KB).
    by_t = {}
    for t, rows in by_co.items():
        nb = ns = 0
        for r in rows:
            if r["c"] == "P":
                nb += 1
            elif r["c"] == "S":
                ns += 1
        if nb or ns:
            by_t[t] = [nb, ns]

    # 지연 실측 — '오늘'과 '가장 최근 거래일'의 거리. 화면에 그대로 적는다.
    lag = (dt.date.today() - dt.date.fromisoformat(latest)).days if latest else None
    summary = {
        "note": "SEC Form 3/4/5 분기 데이터셋 수집분. 거래코드를 뭉개지 않는다 — "
                "P·S(재량 거래)와 A·M·F(보상 제도가 굴러간 결과)는 성격이 전혀 다르다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": latest,
        "lag_days": lag,
        "quarters": quarters,
        "n_co": len(by_co),
        "n_tr": tot,
        "n_disc": disc_tot,
        # 버린 오타 건수를 감추지 않는다 — 0이 아니면 화면이 그 사실을 적는다
        "n_bad_date": len(bad_date),
        # [장내매수 건수, 장내매도 건수] — 보상·세금 처리는 빼고 본인이 고른 거래만 센다
        "by_t": by_t,
        "codes": CODE,
        "disc": list(DISCRETIONARY),
        "limits": [
            "SEC가 Form 4를 분기 단위로 묶어 내놓기 때문에 수십 일 지연이 구조적으로 따라붙는다 — "
            "실시간이 아니다. 화면에 실측 지연일을 적는다.",
            "P(장내매수)·S(장내매도)만 본인이 고른 거래다. A(주식보상)·M(옵션행사)·F(세금 대납분 반납)은 "
            "보상 제도가 굴러간 결과라, 합쳐 세면 '내부자가 샀다/팔았다'가 틀린 말이 된다.",
            "내부자 매수가 초과수익으로 이어지는지 이 랩은 검증한 적이 없다 — 점수도 시그널도 만들지 않는다.",
            "파생상품 거래(옵션·RSU 자체의 취득)는 담지 않는다. 보통주 거래(Table I)만 싣는다.",
            "거래일이 제출일보다 뒤인 건은 제출자 오타로 보고 버린다 — Form 4는 거래 후 2영업일 안에 내는 서식이다.",
        ],
    }
    io.open(OUT_SUM, "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n")

    sz = sum(os.path.getsize(os.path.join(DIR_INS, f)) for f in os.listdir(DIR_INS)) / 1024
    print("내부자 거래: %d사 · %d건(재량 %d건) · %.0fKB — 신규 %d · 변경 %d · 삭제 %d"
          % (len(by_co), tot, disc_tot, sz, n_new, n_upd, n_del))
    # 상한에 걸린 회사 수를 매번 찍는다. 이 수가 0 이 아니면 data/ins 를 직접 합산하는 쪽은
    # 반드시 틀린 답을 낸다 — ins_monthly.json 이 있어야 하는 이유를 눈에 보이게 남긴다.
    print("보관 상한 %d건에 걸린 회사 %d/%d — 합산은 ins_monthly.json 을 쓸 것"
          % (KEEP_PER_CO, n_cap, len(by_co)))
    if bad_date:
        print("⚠ 거래일이 제출일보다 뒤인 오타 %d건 제외: %s"
              % (len(bad_date), ", ".join("%s %s(제출 %s)" % b for b in bad_date[:5])))
    print("최근 거래일 %s · 오늘 기준 %s일 지연" % (latest or "—", lag if lag is not None else "—"))
    cover = len(by_co) / max(1, len({v for v in uni.values()}))
    print("커버 %.1f%% (내부자 거래가 없는 회사는 파일이 없다 — 정상)" % (cover * 100))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "내부자 거래")
