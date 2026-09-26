# -*- coding: utf-8 -*-
"""build/v_fund.py — 배치 V 재무 층: _fxv 최초 제출 원장 + 원 companyfacts 핀 사본에서 넓힌 최초 제출 원장 · 99(→ 139) 그룹 잇기 ·
pre_xbrl 금지 · TTM · 신호 입력(E/P · S/P · PROF · LEV · σROA · BE) · V08 순발행 · 커버리지 · 생존편향 표.

설계 원본(구속): vbatch_research.json final.data_plan.fundamentals · survivorship · slate V06 · V07 · 오케스트레이터 결정 8(V08).
  _fxv 는 eq · ni · asset · sh · sho · debt 만 읽는다(🚨 cfo 는 읽지 않는다 — Cop · Eg 입력 · 금지). 넓힘은 원 캐시(%TEMP%/egff/raw · 815 CIK)를
  첫날 sha 핀 사본(캐시 raw/companyfacts)에서 같은 «최초 제출» 규칙으로 뽑는다. 태그 대체 순서(등록문에 고정 — 아래 WIDE_TAGS):
    rev   Revenues → RevenueFromContractWithCustomerExcludingAssessedTax → SalesRevenueNet(명세 순서) → ifrs Revenue
    cogs  CostOfRevenue → CostOfGoodsAndServicesSold → CostOfGoodsSold → ifrs CostOfSales
    sga   SellingGeneralAndAdministrativeExpense
    int   InterestExpense → InterestExpenseDebt
    opinc OperatingIncomeLoss → ifrs ProfitLossFromOperatingActivities
    da    DepreciationDepletionAndAmortization → DepreciationAndAmortization → DepreciationAmortizationAndAccretionNet
  기본 키(_fxv 에 없는 그룹 — issuer_map 이 푼 그룹의 139개 · 원 캐시에 137개)도 원 캐시에서 _fxv 와 같은 태그 후보(index.json candidates)로 짓는다.
  «최초 제출» = 칸(키 · 버킷 · 기간말)마다 태그 후보 차례로 기록이 있는 첫 태그 · 그 태그의 filed 가 가장 이른 기록. 값 = 백만 단위(소수 둘째 · _fxv 와 같다).
  가용일 = max(기간말 + 90일, filed 다음 NYSE 거래일)(_fxv 규칙 · 격자 = 랩 가격 격자). 🚨 pre_xbrl 칸(기간말 < 그룹 첫 XBRL 정기보고 filed)은 어떤 신호에도 쓰지 않는다.
  그룹 CIK 규칙(_fxv 와 같다): 주 CIK 기록 전부 · 선행 CIK 기록은 filed < 주 CIK 첫 정기보고 · 지도 효력 구간 안.
  새 SEC 호출이 필요하면 SEC_UA 환경변수로만(저장소에 쓰지 않는다) — 이 모듈은 SEC 에 접속하지 않는다(원 캐시 사본만 읽는다 · 없는 2 그룹은 «원장 없음»).

TTM = tech_backtest.ttm2 의 갈래 복사(① 인접 간격 ≤ 120일 · 4분기 ≤ 400일 · ② 연간 · 신선 550일 · ③ 연 1회 보고) — 기록은 «가용일 ≤ 결정일» 만.
V08 NI(순발행 · T18 규칙 문구 PREREG-2026-09-26-TBATCH.md §1.12 «t−2 회계연도 말부터 t−1 까지 분할 조정 주식수 로그 변화 · 6월 말 재구성»):
  6월 말 d 에 가용한 마지막 연간 기간말(FY t−1) · 그 앞 연간 기간말(FY t−2 · 320~410일 앞)의 주식수 — sho(기말 발행주식) 두 해 모두 있으면 그것 ·
  아니면 sh 연간(가중평균 희석) 두 해 — 섞지 않는다. 분할 조정 = 앞 해 주식수에 두 기록 기준일(filed) 사이 실제 분할 배수를 곱한다(v_px_split.split_events).
  🔎 이론 인접(공개): 순발행은 투자 CAPM(HXZ 투자 범주)과 이웃이다 — V08 은 순발행 자체만 쓰고 EG30 · Eg · 투자 · cfo 입력은 없다.

🚨 수익 · 신호-수익 통계를 계산하지 않는다. 커버리지 · 개수만.

  python build/v_fund.py --selftest
  python build/v_fund.py --pin-raw         원 companyfacts(%TEMP%/egff/raw)를 캐시 raw/companyfacts 에 sha 핀 사본으로(있으면 그대로)
  python build/v_fund.py --build-wide      핀 사본 → 넓힌 원장(캐시 derived/wide_ledger.json.gz · 수 분)
"""
from __future__ import annotations

import bisect
import datetime as _dt
import gzip
import io
import json
import math
import os
import shutil
import sys
import tempfile
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_data as VD          # noqa: E402

RAW_SRC = os.environ.get("EGFF_RAW") or os.path.join(tempfile.gettempdir(), "egff", "raw")
FORMS_OK = ("10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A")
LAG_DAYS = 90
TTM_STALE_DAYS = 550                     # tech_backtest.TTM_STALE_DAYS 와 같은 상수(r_stagem 이 같음을 시험한다)
BASE_KEYS = ("asset", "debt", "eq", "ni", "sh", "sho")          # 🚨 cfo 없음
FORBIDDEN_KEYS = ("cfo",)
BASE_TAGS = {  # _fxv/index.json candidates 와 같다(cfo 제외) — 원 캐시에서 기본 키를 지을 때
    "ni": {"us-gaap": ["NetIncomeLoss", "ProfitLoss"], "ifrs-full": ["ProfitLoss"]},
    "asset": {"us-gaap": ["Assets"], "ifrs-full": ["Assets"]},
    "eq": {"us-gaap": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "ifrs-full": ["Equity"]},
    "sh": {"us-gaap": ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
           "ifrs-full": ["AdjustedWeightedAverageShares", "WeightedAverageShares"]},
    "sho": {"us-gaap": ["CommonStockSharesOutstanding"]},
    "debt": {"us-gaap": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"]},
}
WIDE_TAGS = {
    "rev": {"us-gaap": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"], "ifrs-full": ["Revenue"]},
    "cogs": {"us-gaap": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"], "ifrs-full": ["CostOfSales"]},
    "sga": {"us-gaap": ["SellingGeneralAndAdministrativeExpense"]},
    "int": {"us-gaap": ["InterestExpense", "InterestExpenseDebt"]},
    "opinc": {"us-gaap": ["OperatingIncomeLoss"], "ifrs-full": ["ProfitLossFromOperatingActivities"]},
    "da": {"us-gaap": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet"]},
    # 주식수 대체(선언 · _fxv 주식수가 없는 그룹-날짜만): 기본 · 희석 합친 가중평균 태그 · 표지 발행주식(dei — 기준일 = 표지 날짜 · 가용 = 제출 다음 거래일)
    "sh2": {"us-gaap": ["WeightedAverageNumberOfShareOutstandingBasicAndDiluted"]},
    "shc": {"dei": ["EntityCommonStockSharesOutstanding"]},
}
BUCKETS = {"asset": ("i",), "debt": ("i",), "eq": ("i",), "sho": ("i",), "sh": ("q", "a", "i"), "ni": ("q", "a"),
           "rev": ("q", "a"), "cogs": ("q", "a"), "sga": ("q", "a"), "int": ("q", "a"), "opinc": ("q", "a"), "da": ("q", "a"),
           "sh2": ("q", "a"), "shc": ("i",)}
UNIT_OF = {"sh": "shares", "sho": "shares", "sh2": "shares", "shc": "shares"}
AVAIL_FILED = ("shc",)                   # 표지 주식수 — 기준일이 제출 직전이라 «기간말 + 90일» 이 아니라 max(기준일, 제출 다음 거래일)
SHARE_CLASS_FACTOR = {"g1067983": 1500.0}   # 버크셔 — 원장 주식수는 A주 환산(1.64M) · 가격은 BRK.B(= A 의 1/1500) → B주 환산(선언)


def _ord(d):
    return _dt.date.fromisoformat(d[:10]).toordinal()


def _days(a, b):
    return _ord(a) - _ord(b)


def pe_plus(pe, days=LAG_DAYS):
    return (_dt.date.fromisoformat(pe) + _dt.timedelta(days=days)).isoformat()


def avail_of(pe, filed, grid):
    """가용일 = max(기간말 + 90일, filed 다음 NYSE 거래일) — 복사: fxv_build.avail_of(휴장 = 랩 가격 격자 밖 날)."""
    a, b = pe_plus(pe), VD.next_session(grid, filed)
    return a if a >= b else b


def bucket_of(start, end):
    """80~100일 q · 350~380일 a · 시작 없음 i — refresh_facts.pick 과 같은 기간 판정."""
    if not start:
        return "i"
    n = _days(end, start) + 1
    if 80 <= n <= 100:
        return "q"
    if 350 <= n <= 380:
        return "a"
    return None


# ══════════════════════════════════════════════════════════════════════════
#  원 캐시 핀 사본
# ══════════════════════════════════════════════════════════════════════════
def raw_dir():
    return os.path.join(VD.cache_guard(), "raw", "companyfacts")


def pin_raw():
    """%TEMP%/egff/raw 의 CIK##########.json.gz 를 캐시 raw/companyfacts 로 복사(있으면 그대로) · 내용 sha256(gzip 을 푼 바이트) 표를 쓴다.
    _fxv/manifest.json 의 sha 와 같은 CIK 는 대조한다(다르면 들이지 않는다 — 원본이 바뀌었다)."""
    dst = raw_dir()
    os.makedirs(dst, exist_ok=True)
    man = VD.read_json(VD.lab_path("data/_fxv/manifest.json")).get("files", {})
    idx_p = os.path.join(dst, "_pin_index.json")
    idx = VD.read_json(idx_p) if os.path.exists(idx_p) else {"files": {}}
    n_new = n_same = n_bad = 0
    for fn in sorted(os.listdir(RAW_SRC)):
        if not fn.endswith(".json.gz"):
            continue
        key = fn.split(".")[0]
        b = os.path.join(dst, fn)
        if os.path.exists(b) and key in idx["files"]:
            n_same += 1
            continue
        with open(os.path.join(RAW_SRC, fn), "rb") as f:
            gz = f.read()
        sha = VD.sha256_bytes(gzip.decompress(gz))
        want = (man.get(key) or {}).get("sha256")
        if want and want != sha:
            n_bad += 1
            idx["files"][key] = {"state": "🚨 _fxv 명세와 다름 — 들이지 않음"}
            continue
        VD._write_bytes(b, gz)
        idx["files"][key] = {"sha256": sha, "gz_bytes": len(gz), "fxv_manifest": "일치" if want else "명세에 없음(_fxv 밖 그룹)"}
        n_new += 1
    idx["pinned_at"] = idx.get("pinned_at") or VD._now()
    idx["source"] = "egff/raw(EGFF 빌드가 받은 companyfacts · 2026-09-25)"
    VD._write_bytes(idx_p, json.dumps(idx, ensure_ascii=False, indent=0).encode("utf-8"))
    return {"new": n_new, "same": n_same, "bad": n_bad, "files": len(idx["files"])}


def raw_pin_manifest():
    """공개 명세 칸 — 파일 수 · 묶음 해시(이름 · sha 줄들의 sha256) · 대조 결과 개수(값 없음)."""
    p = os.path.join(raw_dir(), "_pin_index.json")
    if not os.path.exists(p):
        return {"state": "핀 없음 — python build/v_fund.py --pin-raw"}
    idx = VD.read_json(p)
    lines = "".join("%s\t%s\n" % (k, v.get("sha256")) for k, v in sorted(idx["files"].items()))
    n_match = sum(1 for v in idx["files"].values() if v.get("fxv_manifest") == "일치")
    return {"files": len(idx["files"]), "digest": VD.sha256_bytes(lines.encode("utf-8")), "fxv_manifest_match": n_match,
            "pinned_at": idx.get("pinned_at"), "rule": "sha256(«CIK \\t 내용 sha256 \\n» 을 CIK 차례로)"}


# ══════════════════════════════════════════════════════════════════════════
#  원 companyfacts → 칸별 기록(최초 제출 규칙)
# ══════════════════════════════════════════════════════════════════════════
def cik_cells(facts, tagmap, grid):
    """companyfacts 한 CIK → {키: {버킷: {기간말: [[가용일, 값(백만), filed, form, accn, 태그 순위]]}}}(filed 오름차순).
    태그 순위는 칸마다 «기록이 있는 첫 태그» 를 고르는 데 쓴다(cells_first)."""
    out = {}
    F = facts.get("facts") or {}
    for key, bytx in tagmap.items():
        want_unit = UNIT_OF.get(key, "USD")
        for tx, tags in bytx.items():
            T = F.get(tx) or {}
            for rank, tag in enumerate(tags):
                node = T.get(tag)
                if not node:
                    continue
                for unit, recs in (node.get("units") or {}).items():
                    if unit != want_unit:
                        continue
                    for r in recs:
                        form = str(r.get("form") or "")
                        if form not in FORMS_OK or r.get("val") is None or not r.get("end") or not r.get("filed"):
                            continue
                        b = bucket_of(r.get("start"), r["end"])
                        if b is None or b not in BUCKETS.get(key, ()):
                            continue
                        v = round(float(r["val"]) / 1e6, 2)
                        cell = out.setdefault(key, {}).setdefault(b, {}).setdefault(r["end"], [])
                        if key in AVAIL_FILED:
                            ns = VD.next_session(grid, r["filed"])
                            av = ns if ns >= r["end"] else r["end"]
                        else:
                            av = avail_of(r["end"], r["filed"], grid)
                        cell.append([av, v, r["filed"], form, r.get("accn"), rank, tx])
    for key in out:
        for b in out[key]:
            for pe in out[key][b]:
                out[key][b][pe].sort(key=lambda z: (z[5], z[2], z[4] or ""))
    return out


def first_xbrl(facts):
    """그 CIK 의 첫 XBRL 정기보고 filed — 기록 가운데 FORMS_OK 의 가장 이른 filed(없으면 None)."""
    best = None
    for tx in (facts.get("facts") or {}).values():
        for node in tx.values():
            for recs in (node.get("units") or {}).values():
                for r in recs:
                    if str(r.get("form") or "") in FORMS_OK and r.get("filed"):
                        f = r["filed"]
                        if best is None or f < best:
                            best = f
    return best


def merge_group(cells_by_cik, ciks, first_own):
    """그룹 CIK 규칙 — 주 CIK 기록 전부 · 선행 CIK 기록은 filed < 주 CIK 첫 정기보고(first_own) · 효력 구간 [시작, 끝] 안(복사: fxv_build 규칙).
    ciks = [(cik, 시작, 끝, 역할)] · 역할 'primary' 가 하나. 돌려주는 것 칸 사전(같은 꼴)."""
    out = {}
    for cik, s, e, role in ciks:
        C = cells_by_cik.get(cik) or {}
        for key, bk in C.items():
            for b, cells in bk.items():
                for pe, recs in cells.items():
                    for r in recs:
                        if role != "primary":
                            if first_own and r[2] >= first_own:
                                continue
                            if (s and r[2] < s) or (e and r[2] > e):
                                continue
                        out.setdefault(key, {}).setdefault(b, {}).setdefault(pe, []).append(r)
    for key in out:
        for b in out[key]:
            for pe in out[key][b]:
                out[key][b][pe].sort(key=lambda z: (z[5], z[2], z[4] or ""))
    return out


def cells_first(cells, key, bucket, pre_xbrl_before=None):
    """칸마다 최초 제출 한 기록 → [(기간말, 가용일, 값, filed)] 기간말 오름차순. 칸의 첫 기록 = 태그 순위가 가장 앞 · 그 안에서 filed 가 가장 이른 것.
    pre_xbrl_before(첫 XBRL filed) 보다 먼저 끝난 기간은 뺀다(🚨 pre_xbrl 금지)."""
    if key in FORBIDDEN_KEYS:
        raise PermissionError("🚨 %s 는 V 입력 금지(Cop · Eg 입력)" % key)
    B = ((cells or {}).get(key) or {}).get(bucket) or {}
    out = []
    for pe in sorted(B):
        if pre_xbrl_before and pe < pre_xbrl_before:
            continue
        recs = B[pe]
        if not recs:
            continue
        r = recs[0]
        out.append((pe, r[0], float(r[1]), r[2]))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  원장 한 벌 — 그룹 → 칸(기본 키 _fxv · 넓힌 키 원 캐시 · _fxv 밖 그룹은 원 캐시 전부)
# ══════════════════════════════════════════════════════════════════════════
class Ledger:
    """그룹(gid) 단위 최초 제출 원장. fxv = _fxv 그룹 파일 · wide = 원 캐시에서 지은 칸(derived/wide_ledger.json.gz)."""

    def __init__(self, wide=None, fxv_index=None, fxv_dir=None, grid=None):
        self.fxv_dir = fxv_dir or VD.lab_path("data/_fxv")
        self.ix = fxv_index if fxv_index is not None else VD.read_json(os.path.join(self.fxv_dir, "index.json"))
        self.wide = wide if wide is not None else load_wide()
        self._g = {}
        self.grid = grid

    def fxv_group(self, gid):
        g = (self.ix.get("groups") or {}).get(gid)
        if not g:
            return None
        p = os.path.join(self.fxv_dir, g["file"])
        if not os.path.exists(p):
            return None
        d = VD.read_json(p)
        cells = {}
        cand = self.ix.get("candidates") or BASE_TAGS
        for k, v in (d.get("keys") or {}).items():
            key, tx, tag = k.split(":", 2)
            if key in FORBIDDEN_KEYS or key not in BASE_KEYS:
                continue                                       # 🚨 cfo 는 읽지 않는다
            rank = (cand.get(key, {}).get(tx) or []).index(tag) if tag in (cand.get(key, {}).get(tx) or []) else 99
            for b, byp in v.items():
                if b == "u":
                    continue
                for pe, recs in byp.items():
                    for r in recs:
                        cells.setdefault(key, {}).setdefault(b, {}).setdefault(pe, []).append([r[0], r[1], r[4], r[3], r[2], rank, tx])
        for key in cells:
            for b in cells[key]:
                for pe in cells[key][b]:
                    cells[key][b][pe].sort(key=lambda z: (z[5], z[2], z[4] or ""))
        return {"cells": cells, "first_xbrl": d.get("first_xbrl"), "src": "fxv"}

    def group(self, gid):
        if gid in self._g:
            return self._g[gid]
        fx = self.fxv_group(gid)
        w = (self.wide.get("groups") or {}).get(gid) if self.wide else None
        if fx is None and w is None:
            self._g[gid] = None
            return None
        cells = {}
        if fx is not None:
            cells.update(fx["cells"])
        if w is not None:
            for key, bk in w["cells"].items():
                if key in BASE_KEYS and fx is not None:
                    continue                                   # 기본 키는 _fxv(등록된 원장)가 먼저
                cells[key] = bk
        fxb = (fx or {}).get("first_xbrl") or (w or {}).get("first_xbrl")
        rec = {"cells": cells, "first_xbrl": fxb, "src": "fxv+wide" if (fx and w) else ("fxv" if fx else "wide")}
        self._g[gid] = rec
        return rec

    def series(self, gid, key, bucket):
        g = self.group(gid)
        if not g:
            return []
        return cells_first(g["cells"], key, bucket, g["first_xbrl"])


# ── 넓힌 원장 짓기(원 캐시 핀 사본 → derived/wide_ledger.json.gz) ─────────
def wide_path():
    return os.path.join(VD.cache_guard(), "derived", "wide_ledger.json.gz")


def group_ciks_map():
    """그룹 → [(cik, 시작, 끝, 역할)] · 첫 정기보고. _fxv 색인이 있으면 그것 · 없으면 _issuer_map groups(최근 tm 행의 주 CIK 가 primary)."""
    ix = VD.read_json(VD.lab_path("data/_fxv/index.json"))
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    out = {}
    for gid, g in (ix.get("groups") or {}).items():
        out[gid] = {"ciks": [(int(c[0]), c[1], c[2], "primary" if c[4] == "primary" else "pred") for c in g["ciks"]],
                    "first_own": g.get("first_own"), "src": "fxv"}
    last_prim = {}
    for t, rows in (im.get("tm") or {}).items():
        for r in rows:
            if r[2]:
                if r[2] not in last_prim or r[1] > last_prim[r[2]][0]:
                    last_prim[r[2]] = (r[1], int(r[3]) if r[3] else None)
    for gid, g in (im.get("groups") or {}).items():
        if gid in out:
            continue
        prim = (last_prim.get(gid) or (None, None))[1] or int(gid[1:])
        cl = []
        for c in g.get("ciks") or []:
            cl.append((int(c[0]), c[1], c[2], "primary" if int(c[0]) == prim else "pred"))
        if not any(x[3] == "primary" for x in cl):
            cl.append((prim, None, None, "primary"))
        out[gid] = {"ciks": cl, "first_own": None, "src": "issuer_map"}
    return out


def build_wide(groups=None):
    """핀 사본 → 넓힌 원장. 모든 그룹의 넓힌 키 + _fxv 밖 그룹의 기본 키. 돌려주는 것 {"groups": {gid: {cells, first_xbrl}}, "stats"}."""
    grid = VD.grid_dates()
    G = group_ciks_map()
    if groups:
        G = {g: G[g] for g in groups if g in G}
    rd = raw_dir()
    have = set(f.split(".")[0] for f in os.listdir(rd) if f.endswith(".json.gz"))
    out, st = {}, {"groups": 0, "no_raw": [], "from_fxv_base": 0, "from_raw_base": 0}
    tag_all = dict(WIDE_TAGS)
    tag_base = dict(BASE_TAGS)
    for gid, g in sorted(G.items()):
        per_cik, fx_first, first_own = {}, None, g["first_own"]
        for cik, s, e, role in g["ciks"]:
            key = "CIK%010d" % cik
            if key not in have:
                continue
            facts = VD.read_json(os.path.join(rd, key + ".json.gz"))
            tm = dict(tag_all)
            if g["src"] != "fxv":
                tm.update(tag_base)
            per_cik[cik] = cik_cells(facts, tm, grid)
            if role == "primary":
                fx_first = first_xbrl(facts)
                first_own = first_own or fx_first
        if not per_cik:
            st["no_raw"].append(gid)
            continue
        cells = merge_group(per_cik, g["ciks"], first_own)
        out[gid] = {"cells": cells, "first_xbrl": fx_first, "base_from": "fxv" if g["src"] == "fxv" else "raw"}
        st["groups"] += 1
        st["from_fxv_base" if g["src"] == "fxv" else "from_raw_base"] += 1
    return {"groups": out, "stats": st, "built_at": VD._now(), "tags": {"wide": WIDE_TAGS, "base_raw": BASE_TAGS}}


def save_wide(doc):
    b = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    VD._write_bytes(wide_path(), gzip.compress(b, mtime=0))
    return wide_path()


_WIDE = None


def load_wide():
    global _WIDE
    if _WIDE is None:
        p = wide_path()
        _WIDE = VD.read_json(p) if os.path.exists(p) else {"groups": {}}
    return _WIDE


# ══════════════════════════════════════════════════════════════════════════
#  결정일 d 의 값 — «가용일 ≤ d» 기록만
# ══════════════════════════════════════════════════════════════════════════
def avail_upto(ser, d):
    """[(기간말, 가용일, 값, filed)] → 가용일 ≤ d 인 것(기간말 내림차순)."""
    return sorted([x for x in ser if x[1] <= d], key=lambda z: z[0], reverse=True)


def latest(ser, d, stale=TTM_STALE_DAYS + LAG_DAYS):
    """가용한 마지막 값(기간말 기준 신선도 ≤ 640일 = 90일 지연 + 550일) — (값, 기간말, filed) | None."""
    got = avail_upto(ser, d)
    if not got:
        return None
    pe, av, v, fd = got[0]
    if _days(d, pe) > stale:
        return None
    return (v, pe, fd)


def clean_share_units(ser):
    """주식수 단위 사고 정리 — 복사: tech_backtest._clean_units(규칙 그대로 · 입력 꼴만 [(기간말, 가용일, 값, filed)] 기간말 오름차순).
    중앙값의 500~2000배 → ÷1000 · 1/2000~1/500 → ×1000(되돌린 값이 가장 가까운 정상 관측과 5% 안일 때만) · 그 밖 100배 밖은 버림 ·
    앞뒤와 30% 넘게 벌어지고 앞뒤끼리 15% 안인 외톨이도 버림. 백만 배(원 단위 · 천 단위 표기) 사고도 같은 식으로(1e6 근처 → ÷1e6).
    🚨 PIT: 부르는 쪽이 «가용일 ≤ d» 기록만 넘긴다(미래 기록으로 중앙값을 정하지 않는다)."""
    xs = [x for x in ser if x[2] and x[2] > 0]
    if len(xs) < 3:
        return xs
    vs = sorted(x[2] for x in xs)
    med = vs[len(vs) // 2]
    tmp = []
    for x in xs:
        r = x[2] / med
        if 5e5 < r < 2e6:
            tmp.append((x, x[2] / 1e6, True))
        elif 500 < r < 2000:
            tmp.append((x, x[2] / 1000.0, True))
        elif 1 / 2000 < r < 1 / 500:
            tmp.append((x, x[2] * 1000.0, True))
        elif 1 / 2e6 < r < 1 / 5e5:
            tmp.append((x, x[2] * 1e6, True))
        elif 0.01 < r < 100:
            tmp.append((x, x[2], False))
    mid = []
    for i, (x, v, resc) in enumerate(tmp):
        if resc:
            nb = [w for (_x, w, rr) in reversed(tmp[:i]) if not rr][:1] + [w for (_x, w, rr) in tmp[i + 1:] if not rr][:1]
            if nb and not any(abs(math.log(v / w)) < math.log(1.05) for w in nb):
                continue
        mid.append((x[0], x[1], v, x[3]))
    ok = []
    for i, x in enumerate(mid):
        if 0 < i < len(mid) - 1:
            a, b, v = mid[i - 1][2], mid[i + 1][2], x[2]
            if max(v / a, a / v) > 1.3 and max(v / b, b / v) > 1.3 and max(a / b, b / a) < 1.15:
                continue
        ok.append(x)
    return ok


def latest_shares(ser, d):
    """주식수 계열의 «가용일 ≤ d» 기록만 단위 정리(clean_share_units) 뒤 마지막 값 — (값, 기간말, filed) | None."""
    got = sorted([x for x in ser if x[1] <= d], key=lambda z: z[0])
    return latest(clean_share_units(got), d)


def ttm(q, a, d):
    """TTM — 복사: tech_backtest.ttm2 의 세 갈래(① 분기 4개 · 400일 · 인접 ≤ 120일 ② 연간 · 신선 ③ 연 1회) · 기록은 가용일 ≤ d(기간말 컷 대신).
    신선도 = 결정일 − 90일 − 기간말 ≤ 550일(ttm2 의 cut 과 같은 뜻)."""
    got = [(pe, v) for pe, av, v, fd in avail_upto(q, d)]
    if (len(got) >= 4 and _days(got[0][0], got[3][0]) <= 400
            and all(_days(got[k][0], got[k + 1][0]) <= 120 for k in range(3))):
        return sum(v for _p, v in got[:4]), got[0][0]
    cut = (_dt.date.fromisoformat(d) - _dt.timedelta(days=LAG_DAYS)).isoformat()
    ann = [(pe, v) for pe, av, v, fd in avail_upto(a, d)]
    if ann and _days(cut, ann[0][0]) <= TTM_STALE_DAYS:
        return ann[0][1], ann[0][0]
    if len(got) >= 2 and _days(got[0][0], got[1][0]) >= 300 and _days(cut, got[0][0]) <= TTM_STALE_DAYS:
        return got[0][1], got[0][0]
    return None


def ttm_key(L, gid, key, d):
    return ttm(L.series(gid, key, "q"), L.series(gid, key, "a"), d)


SHARE_ORDER = (("sho", "i"), ("sh", "q"), ("sh", "i"), ("sh", "a"))       # _fxv 최초 제출(명세 S_filed)
SHARE_ORDER_FALLBACK1 = (("sh2", "q"), ("sh2", "a"))                       # 대체 1 — 기본 · 희석 합친 태그(원 캐시 · 같은 최초 제출 규칙)
SHARE_ORDER_FALLBACK2 = (("shc", "i"),)                                   # 대체 2 — 표지 발행주식(dei · 클래스별 공시 회사는 없다)


def shares_at(L, gid, d):
    """그날 기준 주식수(최초 제출 · 가용일 ≤ d) — (값, 기준일 = filed, 출처, 기간말) | None.
    규칙(선언): 후보 = sho(CommonStockSharesOutstanding · 기말 발행주식 · 시점) · sh 분기 · sh 시점 · sh 연간(가중평균 희석) 가운데 가용한 마지막 값 —
      기간말이 가장 새 것 · 같으면 이 차례(sho 먼저). 가중평균 희석은 전환사채 · 옵션이 큰 회사에서 발행주식보다 크다(TSLA 2021 약 +13%) → 발행주식이 있으면 그것.
      이 넷이 모두 없거나 낡으면(640일) 대체 1(sh2 · BasicAndDiluted 태그) → 대체 2(shc · 표지 발행주식) → 없음(v_pit 이 랩 원장 대체로 내려간다).
    기준일을 filed 로 두는 까닭: 분할이 기간말과 제출 사이에 있으면 공시는 분할 뒤 기준으로 다시 적는다(SAB Topic 4C · ASC 260 소급)."""
    f = SHARE_CLASS_FACTOR.get(gid, 1.0)
    for order in (SHARE_ORDER, SHARE_ORDER_FALLBACK1, SHARE_ORDER_FALLBACK2):
        best = None
        for rank, (key, b) in enumerate(order):
            x = latest_shares(L.series(gid, key, b), d)
            if x is not None and x[0] and x[0] > 0:
                cand = (x[1], -rank, x[0], x[2], "%s:%s" % (key, b))
                if best is None or cand[:2] > best[:2]:
                    best = cand
        if best is not None:
            pe, _r, v, fd, src = best
            return (v * f, fd, src, pe)
    return None


def sec_share_series(L, gid):
    """split_kinds 판정용 SEC 주식수 계열(날짜 내림차순 [(filed, 값)]) — sh 분기 · sho(최초 제출)."""
    out = {}
    for key, b in (("sh", "q"), ("sho", "i")):
        for pe, av, v, fd in L.series(gid, key, b):
            out.setdefault(fd, v)
    return sorted(out.items(), reverse=True)


def fund_signals(L, gid, d):
    """결정일 d 의 재무 원값(최초 제출 · 가용일 ≤ d) — {ni_ttm, rev_ttm, be, asset, op_num(매출 − 원가 − 판관비 − 이자), roa_ttm, lev, sig_roa, n_sig}.
    ROE 수준 · 성장(dRoe) · 배당 · cfo 는 없다(명세 V07). 🚨 수익과 무관한 원값이다."""
    out = {}
    ni = ttm_key(L, gid, "ni", d)
    rev = ttm_key(L, gid, "rev", d)
    out["ni_ttm"] = ni[0] if ni else None
    out["rev_ttm"] = rev[0] if rev else None
    be = latest(L.series(gid, "eq", "i"), d)
    at = latest(L.series(gid, "asset", "i"), d)
    out["be"] = be[0] if be else None
    out["asset"] = at[0] if at else None
    cg, sg, it = ttm_key(L, gid, "cogs", d), ttm_key(L, gid, "sga", d), ttm_key(L, gid, "int", d)
    if rev and cg and sg and it and rev[1] == cg[1] == sg[1] == it[1]:
        out["op_num"] = rev[0] - cg[0] - sg[0] - it[0]                  # FF OP 분자(같은 12개월일 때만 · 기간말 대조)
    else:
        out["op_num"] = None
    out["op"] = (out["op_num"] / out["be"]) if (out["op_num"] is not None and out["be"] and out["be"] > 0) else None
    out["roa_ttm"] = (out["ni_ttm"] / out["asset"]) if (out["ni_ttm"] is not None and out["asset"] and out["asset"] > 0) else None
    out["lev"] = (1.0 - out["be"] / out["asset"]) if (out["be"] is not None and out["asset"] and out["asset"] > 0) else None
    s, n = sigma_roa(L, gid, d)
    out["sig_roa"], out["n_sig"] = s, n
    return out


def sigma_roa(L, gid, d, lo=12, hi=20):
    """σROA — 분기 NI/자산(같은 기간말 · 최초 제출 · 10-Q 분기만 · pre_xbrl 금지)의 최근 hi 개(최소 lo 개) 표준편차(ddof 1).
    창 = 가장 최근 분기 기간말부터 5년(20분기) 안 · Q4 는 연간에서 빼서 만들지 않는다(선언)."""
    q = avail_upto(L.series(gid, "ni", "q"), d)
    A = {pe: v for pe, av, v, fd in L.series(gid, "asset", "i") if av <= d}
    if not q:
        return None, 0
    last = q[0][0]
    vals = []
    for pe, av, v, fd in q:
        if _days(last, pe) > 5 * 366:
            break
        a = A.get(pe)
        if a and a > 0:
            vals.append(v / a)
        if len(vals) >= hi:
            break
    if len(vals) < lo:
        return None, len(vals)
    return float(np.std(np.asarray(vals), ddof=1)), len(vals)


def net_issuance(L, gid, d, splits=()):
    """V08 NI — T18 규칙(6월 말 재구성 · FY t−2 말 → FY t−1 말 분할 조정 주식수 로그 변화). splits = [(사건일, 주식수 배수 q)](실제 · 섞임 분할).
    🔧 검토 고침(등록 전): 결정일 d 의 해를 t 라 하면 pe1 = 달력 해 t−1 에 끝난 회계연도(가용 ≤ d 가운데 가장 늦은 것) · pe0 = 달력 해 t−2 에 끝난
    회계연도(pe1 과 320~410 일) — French «Portfolios Formed on NI» 의 FY t−2 → t−1 와 같다(옛 판은 1~5월 결산 기업에서 달력 해 t 의 회계연도를 썼다).
    돌려주는 것 {"ni", "pe1", "pe0", "src"} | None. 🚨 순발행 자체만 — 투자 · cfo · Eg 입력 없음."""
    ann = [pe for pe, av, v, fd in avail_upto(L.series(gid, "ni", "a"), d)]
    if not ann:
        return None
    t = int(str(d)[:4])
    pe1 = next((p for p in ann if int(str(p)[:4]) == t - 1), None)
    if pe1 is None:
        return None
    pe0 = next((p for p in ann if int(str(p)[:4]) == t - 2 and 320 <= _days(pe1, p) <= 410), None)
    if pe0 is None:
        return None
    for key, b in (("sho", "i"), ("sh", "a")):
        ser = {pe: (v, fd) for pe, av, v, fd in clean_share_units(sorted([x for x in L.series(gid, key, b) if x[1] <= d], key=lambda z: z[0]))}
        if pe1 in ser and pe0 in ser and ser[pe1][0] > 0 and ser[pe0][0] > 0:
            (s1, f1), (s0, f0) = ser[pe1], ser[pe0]
            adj = 1.0
            for sd, qf in splits:
                if f0 < sd <= f1:
                    adj *= qf
            return {"ni": math.log(s1 / (s0 * adj)), "pe1": pe1, "pe0": pe0, "src": key + ":" + b}
    return None


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
def _fake_facts(cik=1, with_rev=True):
    def q(start, end, val, filed, form="10-Q"):
        return {"start": start, "end": end, "val": val, "accn": "a-%s-%s" % (end, filed), "form": form, "filed": filed}
    ni, rev, sh, eq, at, sho = [], [], [], [], [], []
    ends = ["2014-03-31", "2014-06-30", "2014-09-30", "2014-12-31", "2015-03-31", "2015-06-30", "2015-09-30", "2015-12-31"]
    starts = ["2014-01-01", "2014-04-01", "2014-07-01", "2014-10-01", "2015-01-01", "2015-04-01", "2015-07-01", "2015-10-01"]
    for j, (s, e) in enumerate(zip(starts, ends)):
        filed = (_dt.date.fromisoformat(e) + _dt.timedelta(days=35)).isoformat()
        if e.endswith("12-31"):
            ni.append(q(e[:4] + "-01-01", e, 4.0e8 + j, filed, "10-K"))
        else:
            ni.append(q(s, e, 1.0e8 + j * 1e6, filed))
            ni.append(q(s, e, 9.9e8, (_dt.date.fromisoformat(filed) + _dt.timedelta(days=365)).isoformat()))  # 뒤 재작성 — 쓰면 안 된다
        rev.append(q(s, e, 1.0e9, filed))
        sh.append(q(s, e, 5.0e8 * (2 if e >= "2015-06-30" else 1), filed))
        eq.append({"end": e, "val": 2.0e9, "accn": "x", "form": "10-Q", "filed": filed})
        if e.endswith("12-31"):
            sho.append({"end": e, "val": 5.0e8 * (2 if e >= "2015-06-30" else 1), "accn": "s", "form": "10-K", "filed": filed})
        at.append({"end": e, "val": 5.0e9, "accn": "x", "form": "10-Q", "filed": filed})
    eq.append({"end": "2012-12-31", "val": 1.0e9, "accn": "old", "form": "10-K", "filed": "2014-05-05"})   # pre_xbrl 칸(기간말 < 첫 filed)
    ug = {"NetIncomeLoss": {"units": {"USD": ni}}, "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": sh}},
          "StockholdersEquity": {"units": {"USD": eq}}, "Assets": {"units": {"USD": at}}, "CommonStockSharesOutstanding": {"units": {"shares": sho}},
          "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [q("2014-01-01", "2014-12-31", 7e8, "2015-02-05", "10-K")]}}}
    if with_rev:
        ug["Revenues"] = {"units": {"USD": rev[:4]}}
        ug["SalesRevenueNet"] = {"units": {"USD": rev}}
    return {"cik": cik, "facts": {"us-gaap": ug}}


def _st_ledger():
    grid = [d.strftime("%Y-%m-%d") for d in __import__("pandas").bdate_range("2013-01-01", "2017-12-31")]
    fx = _fake_facts()
    tm = dict(BASE_TAGS)
    tm.update(WIDE_TAGS)
    cells = cik_cells(fx, tm, grid)
    assert "cfo" not in cells and set(cells) >= {"ni", "rev", "sh", "eq", "asset"}
    fxb = first_xbrl(fx)
    assert fxb == "2014-05-05"
    niq = cells_first(cells, "ni", "q", fxb)
    # 첫 XBRL filed = 2014-05-05 → 기간말이 그 앞인 칸(2012-12-31 · 첫 보고 자신의 2014-03-31)은 pre_xbrl(_fxv 규칙 그대로 — 20,056칸의 정의)
    assert len(niq) == 5 and all(v < 5e2 for _, _, v, _ in niq)                    # 재작성(990) 이 아니라 최초 제출
    assert niq[0][0] == "2014-06-30" and niq[0][1] == pe_plus("2014-06-30")       # 가용 = 기간말 + 90(> filed + 1)
    assert [pe for pe, *_ in cells_first(cells, "eq", "i", fxb)][0] == "2014-06-30"   # pre_xbrl 칸 제외
    assert [pe for pe, *_ in cells_first(cells, "eq", "i", None)][0] == "2012-12-31"
    rv = cells_first(cells, "rev", "q", fxb)
    assert len(rv) == 7                                                            # 앞 3 은 Revenues · 뒤 4 는 SalesRevenueNet(칸마다 첫 태그)
    try:
        cells_first(cells, "cfo", "a")
        raise AssertionError("cfo 가 통과했다")
    except PermissionError:
        pass
    # 그룹 CIK 규칙 — 선행 CIK 는 주 CIK 첫 제출 전 · 효력 구간 안
    pred = cik_cells(_fake_facts(2), {"ni": BASE_TAGS["ni"]}, grid)
    merged = merge_group({1: cells, 2: pred}, [(1, None, None, "primary"), (2, "2014-01-01", "2014-06-30", "pred")], "2014-06-01")
    n_all = sum(len(v) for v in merged["ni"]["q"].values())
    n_prim = sum(len(v) for v in cells["ni"]["q"].values())
    assert n_all == n_prim + 1, (n_all, n_prim)                                   # 선행 기록 중 filed ∈ [01-01, 06-01) 인 한 건만
    return "최초 제출(재작성 무시) · 가용 = max(기간말 + 90, filed + 1) · pre_xbrl 칸 금지 · 칸마다 첫 태그 · cfo 금지 · 선행 CIK 규칙"


def _st_values():
    import pandas as pd
    grid = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2013-01-01", "2017-12-31")]
    fx = _fake_facts()
    tm = dict(BASE_TAGS)
    tm.update(WIDE_TAGS)
    cells = cik_cells(fx, tm, grid)
    L = Ledger(wide={"groups": {"g1": {"cells": cells, "first_xbrl": first_xbrl(fx)}}}, fxv_index={"groups": {}, "candidates": BASE_TAGS},
               fxv_dir=VD.cache_guard())
    d = "2015-12-31"
    t = ttm_key(L, "g1", "ni", d)
    # 가용한 분기(가용 ≤ d): 2015-09-30 까지 · Q4(12-31)는 10-K 라 a 버킷 → 분기 4개가 인접하지 않다 → 연간(2014-12-31 · 신선) 갈래
    assert t is not None and t[1] == "2014-12-31" and abs(t[0] - 400.0) < 1e-9, t
    s = shares_at(L, "g1", "2015-12-31")
    assert s is not None and s[2] == "sh:q" and s[0] == 1000.0 and s[3] == "2015-09-30"      # sho(2014-12-31)보다 새 분기
    s_jun = shares_at(L, "g1", "2015-04-15")
    assert s_jun is not None and s_jun[2] == "sho:i" and s_jun[3] == "2014-12-31"             # 같은 기간말이면 sho 먼저
    ni_v8 = net_issuance(L, "g1", "2016-06-30", splits=[("2015-06-15", 2.0)])
    assert ni_v8 is not None and abs(ni_v8["ni"]) < 1e-12 and ni_v8["pe1"] == "2015-12-31" and ni_v8["pe0"] == "2014-12-31", ni_v8
    assert net_issuance(L, "g1", "2016-06-30") is not None and abs(net_issuance(L, "g1", "2016-06-30")["ni"] - math.log(2.0)) < 1e-12

    class _FY:                                                                          # 1월 결산 — 6월 t 에는 달력 해 t−1 · t−2 에 끝난 회계연도(검토 고침)
        def series(self, gid, key, b):
            pes = ["2014-01-31", "2015-01-31", "2016-01-31"]
            if key == "ni":
                return [(pe, pe[:4] + "-04-15", 1.0, pe[:4] + "-03-20") for pe in pes]
            if key == "sho":
                return [(pe, pe[:4] + "-04-15", v, pe[:4] + "-03-20") for pe, v in zip(pes, (100.0, 110.0, 90.0))]
            return []
    nj = net_issuance(_FY(), "gx", "2016-06-30")
    assert nj["pe1"] == "2015-01-31" and nj["pe0"] == "2014-01-31" and abs(nj["ni"] - math.log(1.1)) < 1e-12, nj
    f = fund_signals(L, "g1", "2015-12-31")
    assert f["be"] == 2000.0 and f["asset"] == 5000.0 and abs(f["lev"] - 0.6) < 1e-12 and f["op_num"] is None
    assert f["sig_roa"] is None and f["n_sig"] < 12
    assert SHARE_CLASS_FACTOR["g1067983"] == 1500.0
    # 단위 사고 — 원 단위(백만 배) · 천 배 · 외톨이
    ser = [("2014-%02d-28" % k, "2014-%02d-28" % k, v, "f") for k, v in
           zip(range(1, 9), [100.0, 101.0, 100.5e6, 102.0, 101.5e3, 51.0, 102.5, 103.0])]
    cl = clean_share_units(ser)
    assert [round(x[2], 3) for x in cl] == [100.0, 101.0, 100.5, 102.0, 101.5, 102.5, 103.0], cl
    # 대체 차례 — _fxv 주식수가 없는 그룹은 sh2 → shc(표지 · 가용 = max(기준일, 제출 다음 거래일))
    dei = {"cik": 3, "facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"end": "2015-10-20", "val": 7.0e8, "accn": "c", "form": "10-Q", "filed": "2015-10-28"}]}}}}}
    c3 = cik_cells(dei, {"shc": WIDE_TAGS["shc"]}, grid)
    assert c3["shc"]["i"]["2015-10-20"][0][0] == VD.next_session(grid, "2015-10-28")
    L3 = Ledger(wide={"groups": {"g3": {"cells": c3, "first_xbrl": "2014-01-01"}}}, fxv_index={"groups": {}, "candidates": BASE_TAGS},
                fxv_dir=VD.cache_guard())
    s3 = shares_at(L3, "g3", "2015-12-31")
    assert s3 is not None and s3[2] == "shc:i" and s3[0] == 700.0 and shares_at(L3, "g3", "2015-10-28") is None
    # 선견 — 가용일이 d 뒤인 기록을 바꿔도 값이 같다
    cells2 = json.loads(json.dumps(cells))
    for key in cells2:
        for b in cells2[key]:
            for pe in cells2[key][b]:
                for r in cells2[key][b][pe]:
                    if r[0] > d:
                        r[1] = r[1] * 13.0 + 7.0
    L2 = Ledger(wide={"groups": {"g1": {"cells": cells2, "first_xbrl": first_xbrl(fx)}}}, fxv_index={"groups": {}, "candidates": BASE_TAGS},
                fxv_dir=VD.cache_guard())
    assert fund_signals(L2, "g1", d) == f and shares_at(L2, "g1", d) == s and ttm_key(L2, "g1", "ni", d) == t
    return "TTM(ttm2 갈래 · 가용일 ≤ d) · 주식수 차례 · V08 NI(분할 조정 · 두 해 같은 계열) · LEV · OP 기간말 대조 · σROA 최소 12 · 가용 뒤 기록 독 넣기 불변"


def selftest():
    res, ok = [], True
    for fn in (_st_ledger, _st_values):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-12s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_fund selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--pin-raw" in sys.argv:
        print(json.dumps(pin_raw(), ensure_ascii=False))
    if "--build-wide" in sys.argv:
        t0 = time.time()
        doc = build_wide()
        p = save_wide(doc)
        print("넓힌 원장 → 캐시 derived/%s · 그룹 %d · 원 캐시 없음 %d · %.0fs" % (os.path.basename(p), doc["stats"]["groups"],
                                                                  len(doc["stats"]["no_raw"]), time.time() - t0))
    if len(sys.argv) <= 1:
        print(__doc__)
