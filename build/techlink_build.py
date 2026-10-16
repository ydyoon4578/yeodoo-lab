#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B11 기술 링크 모멘텀 — 특허 → 티커 × 등록연도 × CPC subclass 집계(러너 1회성).

사전등록 build/PREREG-2026-08-12-TECHLINK.md §3 · §4 G0~G3.
  · 원천: Zenodo 15783125 (PatentsView 최종판, 2024-12-31 동결, CC-BY-4.0)
  · g_cpc_at_issue 만 쓴다(G3①) — g_cpc_current 는 받지도 않는다.
  · 출원인은 «등록 시점 출원인»(g_assignee_disambiguated)이라 사후 양도가 섞이지 않는다.
  · 이름 다리: data/fx/*.json · data/fx_pit/*.json 의 SEC 정식명(+ 과거명) 정규화 정확일치
    + 아래 ALIAS(회사 자체 IP 보유 자회사만 — 인수로 얻은 회사는 넣지 않는다, G3③).
산출: data/_techlink_cpc.json  {tk: {연도: {subclass: 건수}}} + 매칭 감사표 + 미매칭 상위 조직
"""
from __future__ import annotations
import collections
import csv
import glob
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
csv.field_size_limit(1 << 30)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_techlink_cpc.json")
TMP = os.environ.get("RUNNER_TEMP", "/tmp")
ZEN = "https://zenodo.org/records/15783125/files/%s?download=1"
F_PAT, F_ASG, F_CPC = "g_patent.tsv.zip", "g_assignee_disambiguated.tsv.zip", "g_cpc_at_issue.tsv.zip"
Y0, Y1 = 2004, 2024
UA = {"User-Agent": "yeodoo-lab globalkbam@gmail.com"}

STOP = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "LLC",
        "LP", "LLP", "PLC", "NV", "SA", "AG", "SE", "HOLDINGS", "HOLDING", "GROUP", "THE", "DE",
        "NY", "MD", "DEL", "CA", "NEW", "COS", "INTL"}
# 회사 자체의 IP 보유 법인(같은 회사의 특허 창구)만. 인수한 별도 회사 이름은 넣지 않는다.
ALIAS = {
    "GOOGL": ["GOOGLE INC", "GOOGLE LLC"],
    "META": ["FACEBOOK INC", "META PLATFORMS INC", "FACEBOOK TECHNOLOGIES LLC", "META PLATFORMS TECHNOLOGIES LLC"],
    "IBM": ["INTERNATIONAL BUSINESS MACHINES CORPORATION"],
    "MSFT": ["MICROSOFT TECHNOLOGY LICENSING LLC", "MICROSOFT CORPORATION"],
    "CSCO": ["CISCO TECHNOLOGY INC"],
    "AMZN": ["AMAZON TECHNOLOGIES INC"],
    "ORCL": ["ORACLE INTERNATIONAL CORPORATION"],
    "VZ": ["VERIZON PATENT AND LICENSING INC"],
    "T": ["AT&T INTELLECTUAL PROPERTY I L P", "AT&T INTELLECTUAL PROPERTY I LP", "AT&T INTELLECTUAL PROPERTY II L P"],
    "GM": ["GM GLOBAL TECHNOLOGY OPERATIONS LLC", "GM GLOBAL TECHNOLOGY OPERATIONS INC"],
    "F": ["FORD GLOBAL TECHNOLOGIES LLC"],
    "MMM": ["3M INNOVATIVE PROPERTIES COMPANY"],
    "DOW": ["DOW GLOBAL TECHNOLOGIES LLC", "DOW GLOBAL TECHNOLOGIES INC"],
    "XOM": ["EXXONMOBIL UPSTREAM RESEARCH COMPANY", "EXXONMOBIL RESEARCH AND ENGINEERING COMPANY",
            "EXXONMOBIL CHEMICAL PATENTS INC", "EXXONMOBIL TECHNOLOGY AND ENGINEERING COMPANY"],
    "CVX": ["CHEVRON U S A INC", "CHEVRON USA INC"],
    "SLB": ["SCHLUMBERGER TECHNOLOGY CORPORATION"],
    "HAL": ["HALLIBURTON ENERGY SERVICES INC"],
    "KMB": ["KIMBERLY-CLARK WORLDWIDE INC"],
    "BSX": ["BOSTON SCIENTIFIC SCIMED INC"],
    "HPQ": ["HEWLETT-PACKARD DEVELOPMENT COMPANY L P", "HP INC", "HEWLETT-PACKARD COMPANY", "HEWLETT-PACKARD COMPANY L P"],
    "HPE": ["HEWLETT PACKARD ENTERPRISE DEVELOPMENT LP"],
    "AMD": ["ADVANCED MICRO DEVICES INC"],
    "QCOM": ["QUALCOMM INCORPORATED"],
    "TXN": ["TEXAS INSTRUMENTS INCORPORATED"],
    "HON": ["HONEYWELL INTERNATIONAL INC"],
    "GE": ["GENERAL ELECTRIC COMPANY"],
    "BA": ["THE BOEING COMPANY", "BOEING COMPANY"],
    "DE": ["DEERE & COMPANY"],
    "PG": ["THE PROCTER & GAMBLE COMPANY", "PROCTER & GAMBLE COMPANY"],
    "AAPL": ["APPLE INC"],
    "NVDA": ["NVIDIA CORPORATION"],
    "INTC": ["INTEL CORPORATION"],
    "ADBE": ["ADOBE INC", "ADOBE SYSTEMS INCORPORATED"],
    "CRM": ["SALESFORCE COM INC", "SALESFORCE INC"],
    "EBAY": ["EBAY INC"],
    "PYPL": ["PAYPAL INC"],
    "MDT": ["MEDTRONIC INC", "MEDTRONIC MINIMED INC", "MEDTRONIC VASCULAR INC", "MEDTRONIC XOMED INC"],
    "RTX": ["UNITED TECHNOLOGIES CORPORATION", "RAYTHEON COMPANY", "RAYTHEON TECHNOLOGIES CORPORATION", "RTX CORPORATION"],
    "MSI": ["MOTOROLA INC", "MOTOROLA SOLUTIONS INC"],          # 같은 CIK(68505) — 2011 분사 뒤 존속법인
    "DELL": ["DELL PRODUCTS L P", "DELL PRODUCTS LP"],
    "LMT": ["LOCKHEED MARTIN CORPORATION"],
    "NOC": ["NORTHROP GRUMMAN SYSTEMS CORPORATION"],
}


def norm(s: str) -> str:
    s = (s or "").upper().replace(" ", " ").replace("&", " AND ")
    s = re.sub(r"/[A-Z]{2,3}/?$", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = s.split()
    while toks and toks[-1] in STOP:
        toks.pop()
    while toks and toks[0] == "THE":
        toks.pop(0)
    return " ".join(toks)


def name_map():
    m, src = {}, {}
    def add(n, tk, how):
        k = norm(n)
        if len(k) < 3:
            return
        if k in m and m[k] != tk:
            m[k] = None                                          # 두 티커가 같은 이름 → 버린다
        elif k not in m:
            m[k] = tk; src[k] = how
    for d, how in ((os.path.join(DATA, "fx"), "sec"), (os.path.join(DATA, "fx_pit"), "sec_pit")):
        for p in glob.glob(os.path.join(d, "*.json")):
            try:
                j = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            tk = j.get("t") or os.path.basename(p)[:-5]
            add(j.get("nm", ""), tk, how)
            for c in j.get("ciks") or []:
                if len(c) >= 5:
                    add(c[4], tk, how)
    for tk, ns in ALIAS.items():
        for n in ns:
            k = norm(n); m[k] = tk; src[k] = "alias"
    return {k: v for k, v in m.items() if v}, src


def fetch(fn):
    dest = os.path.join(TMP, fn)
    if os.path.exists(dest):
        return dest
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(ZEN % fn, headers=UA), timeout=600) as r, open(dest, "wb") as w:
        while True:
            b = r.read(1 << 22)
            if not b:
                break
            w.write(b)
    print(f"  받음 {fn} {os.path.getsize(dest)/1e6:.0f}MB {time.time()-t0:.0f}s", flush=True)
    return dest


def rows(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".tsv")][0]
    with z.open(name) as f:
        rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t")
        hdr = next(rd)
        yield hdr
        for r in rd:
            yield r


def main():
    nm, src = name_map()
    print(f"이름표 {len(nm)}개", flush=True)

    # ① 출원인 → 매칭된 특허만
    it = rows(fetch(F_ASG)); h = next(it)
    io_org = h.index("disambig_assignee_organization")
    pid2tk = {}
    org_hits = collections.Counter(); org_miss = collections.Counter(); org_raw = {}
    for r in it:
        if len(r) <= io_org or not r[io_org]:
            continue
        k = norm(r[io_org])
        tk = nm.get(k)
        if tk:
            pid2tk.setdefault(r[0], set()).add(tk)
            org_hits[(r[io_org], tk)] += 1
        else:
            org_miss[k] += 1
            org_raw.setdefault(k, r[io_org])
    os.remove(os.path.join(TMP, F_ASG))
    print(f"매칭 특허 {len(pid2tk)}건", flush=True)

    # ② 등록일(실용특허만)
    it = rows(fetch(F_PAT)); h = next(it)
    ip_t, ip_d = h.index("patent_type"), h.index("patent_date")
    pdate = {}
    for r in it:
        if r[0] in pid2tk and r[ip_t] == "utility":
            y = int(r[ip_d][:4])
            if Y0 <= y <= Y1:
                pdate[r[0]] = r[ip_d]
    os.remove(os.path.join(TMP, F_PAT))

    # ③ CPC(등록 시점 분류) subclass — 특허 하나 안에서 중복 subclass 는 한 번만
    it = rows(fetch(F_CPC)); h = next(it)
    ic = h.index("cpc_subclass")
    psub = {}
    for r in it:
        if r[0] in pdate:
            psub.setdefault(r[0], set()).add(r[ic])
    os.remove(os.path.join(TMP, F_CPC))

    # 집계: 티커 × 월(YYYY-MM, 등록월) × subclass. 월 해상도로 둬야 월말 PIT(G3②)가 정확하다.
    agg = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for pid, d in pdate.items():
        for tk in pid2tk[pid]:
            for sc in psub.get(pid, ()):
                agg[tk][d[:7]][sc] += 1
    npat = collections.Counter()
    npm = collections.defaultdict(collections.Counter)            # 티커 × 등록월 특허 건수(5년 3건 문턱용)
    for pid, d in pdate.items():
        for tk in pid2tk[pid]:
            npat[tk] += 1
            npm[tk][d[:7]] += 1
    audit = sorted(([o, t, n, src.get(norm(o), "")] for (o, t), n in org_hits.items()), key=lambda x: -x[2])
    miss = [[org_raw[k], n] for k, n in org_miss.most_common(400)]
    out = {
        "note": "B11 기술 링크 — 티커 × 등록월 × CPC subclass(등록 시점 분류) 특허 건수. build/techlink_build.py(러너 1회성). 원천 PatentsView 최종판(Zenodo 15783125, CC-BY-4.0, 2024-12-31 동결).",
        "source": "https://zenodo.org/records/15783125",
        "cpc_file": F_CPC, "years": [Y0, Y1],
        "n_tickers": len(agg), "n_patents": len(pdate),
        "patents_by_ticker": dict(npat.most_common()),
        "npat_month": {tk: dict(sorted(c.items())) for tk, c in npm.items()},
        "cpc": {tk: {m: dict(c) for m, c in sorted(v.items())} for tk, v in agg.items()},
        "match_audit": audit[:3000],
        "top_unmatched": miss,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"산출 {OUT} {os.path.getsize(OUT)/1e6:.1f}MB · 티커 {len(agg)} · 특허 {len(pdate)}")


if __name__ == "__main__":
    main()
