#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/fxv_build.py — EGFF 빈티지 원장: companyfacts 원본 → data/_fxv/ (사전등록 PREREG-2026-09-25-EGFF §2 · §9)

무엇을·왜.
  랩의 재무 경로(build/refresh_facts.py pick)는 같은 기간이 여러 번 보고되면 filed 가 가장 늦은 값 하나만 남긴다.
  그래서 과거 형성월이 나중 제출의 재작성 값을 읽는다. companyfacts 는 **제출마다** 값을 남긴다(accn · filed · form) —
  이 파일은 그 제출 기록 전부를 Eg 입력(asset · debt · eq · ni 분기·연간 · cfo 연간 · sh · sho)에 한해 원장으로 남긴다.
  빈티지 패널 P-V / P-FF 는 build/eg_q5_vintage.py 가 이 원장에서 날짜마다 만든다(여기서는 만들지 않는다).

원장 규칙(사전등록 §2 — 하나만).
  · 태그 · 기간 판정 · 제출 서식은 refresh_facts 와 **같은 함수**를 부른다: TAGS/TAGS_IFRS 의 후보 태그 · resolve_unit(단위) ·
    _days 로 80~100일 분기(q) · 350~380일 연간(a) · 시작 없음 = 시점(i) · FORMS_OK · 값 = pick 과 같은 반올림(백만 단위 소수 둘째).
  · 가용일 = max(기간말 + 90일, filed 다음 NYSE 거래일). 휴장 = refresh_events._holidays(규칙) ∪ refresh_events.ADHOC(관측 임시휴장).
  · XBRL 이전 기간(그룹의 첫 XBRL 정기보고 filed 보다 먼저 끝난 기간): 그 칸의 **첫** 제출 기록의 가용일을 기간말 + 90일로 둔다(종이 공시 대리).
  · 발행사 그룹 = 배치 R §A0 지도(data/_issuer_map.json · issuer_map.load_map). 한 그룹의 원장은 data/fx · fx_pit 의 CIK(주 CIK)를
    따른다 — 주 CIK 의 기록은 전부, 선행 CIK 의 기록은 **주 CIK 의 첫 정기보고보다 먼저 · 그 CIK 의 지도 효력 구간 안에서** 낸 것만
    (지주사 재편 뒤 자회사로 계속 내는 옛 법인의 값 — 다른 실체의 값 — 이 섞이지 않게).
  · 기록 = [가용일, 값, accn, form, filed] (+ 여러 CIK 그룹이면 cik) — 한 칸 안에서 filed 오름차순(같은 날은 원본 순서 = pick 의 동점 규칙).

원본 · 고정.
  원 JSON 은 저장소 밖(EGFF_RAW, 기본 %TEMP%/egff/raw · gzip) · sha256(내용 바이트)은 data/_fxv/manifest.json.
  원장 data/_fxv/<그룹>.json.gz(결정적 gzip · mtime 0) · 색인 data/_fxv/index.json(티커 → 그룹 · 파일 해시 · 규칙 · 점검).

SEC 접속 — 모든 요청이 build/edgar.py(gzip · 백오프)를 거친다 · 이 스크립트는 초당 4회로 더 낮춘다.
  🚨 SEC_UA 환경변수가 없으면 어떤 명령도 돌지 않는다(edgar.py 의 기본값을 조용히 쓰지 않는다 · UA 값은 어디에도 적지 않는다).

  SEC_UA="이름 연락처" python build/fxv_build.py check              # 1건 받기 · 구조 확인(저장 안 함)
  SEC_UA=... python build/fxv_build.py fetch [--limit N]             # 원본 받기 · 고정(이미 있으면 해시만 맞춘다)
  SEC_UA=... python build/fxv_build.py build [--fx-root DIR]         # 원본 → 원장 · 색인 · pick 대조
  SEC_UA=... python build/fxv_build.py selftest                      # 합성 자료로 규칙 점검(네트워크 없음)
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 🚨 SEC_UA 가 없으면 거부한다 — edgar.py 는 없을 때 기본값으로 조용히 넘어가므로 import 전에 막는다.
if not (os.environ.get("SEC_UA") or "").strip():
    sys.exit("🚨 SEC_UA 환경변수가 없다 — SEC 요청의 User-Agent(이름 + 연락처)를 명시적으로 정해서 넘길 것. "
             "edgar.py 의 기본값은 쓰지 않는다.")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402

if edgar.UA != os.environ["SEC_UA"]:
    sys.exit("🚨 edgar.UA 가 SEC_UA 와 다르다 — edgar.py 가 환경변수를 읽지 않았다")
edgar.RATE = 4.0                      # 사전등록은 초당 8회 이하 · 이 빌드는 4회(작업 지시)
edgar._MIN_GAP = 1.0 / edgar.RATE

import refresh_facts as RF            # noqa: E402  TAGS · TAGS_IFRS · FORMS_OK · resolve_unit · _days · pick(대조용)
import refresh_events as REV          # noqa: E402  _holidays · ADHOC (NYSE 휴장)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RAW = os.environ.get("EGFF_RAW") or os.path.join(tempfile.gettempdir(), "egff", "raw")
OUT_DIR = os.path.join(DATA, "_fxv")
MANIFEST = os.path.join(OUT_DIR, "manifest.json")
INDEX = os.path.join(OUT_DIR, "index.json")
ISSUER_MAP = os.path.join(DATA, "_issuer_map.json")
FACTS_URL = RF.FACTS_URL
PREREG = "build/PREREG-2026-09-25-EGFF.md"

EG_KEYS = ("asset", "debt", "eq", "ni", "cfo", "sh", "sho")
# 원장에 싣는 버킷 = eg_q5 가 읽는 것만(Firm: asset · debt · eq 는 i, 없으면 q · ni q · a · cfo a / load_fund: sh 는 i · q, 없으면 a · sho i · q)
EG_BUCKETS = {"asset": ("i", "q"), "debt": ("i", "q"), "eq": ("i", "q"), "ni": ("q", "a"), "cfo": ("a",),
              "sh": ("i", "q", "a"), "sho": ("i", "q")}
LAG_DAYS = 90
SCALE_M = "m"


# ════════════════════════════════════════════════════════════════════════
# 공용
# ════════════════════════════════════════════════════════════════════════
def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rj(p, default=None):
    if not os.path.exists(p):
        return default
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _gz_bytes(b: bytes) -> bytes:
    """결정적 gzip(mtime 0 · 파일 이름 없음) — 같은 내용이면 같은 바이트."""
    bio = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=bio, compresslevel=9, mtime=0) as f:
        f.write(b)
    return bio.getvalue()


def _write(p, b: bytes):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "wb") as f:
        f.write(b)
    os.replace(tmp, p)


def _dumps(obj, indent=None):
    return json.dumps(obj, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))


# ── NYSE 거래일(refresh_events 의 휴장 규칙 + 관측 임시휴장) ─────────────────
_HOL = {}


def _is_closed(d: dt.date) -> bool:
    if d.weekday() >= 5:
        return True
    y = d.year
    if y not in _HOL:
        _HOL[y] = set(REV._holidays(y)) | {x for x in REV.ADHOC if x.startswith("%04d-" % y)}
    return d.isoformat() in _HOL[y]


def next_session(filed: str) -> str:
    """filed(날짜만) 다음 NYSE 거래일 — 접수 시각을 모르므로 늘 다음 세션(보수적 · 사전등록 §2)."""
    d = dt.date.fromisoformat(filed) + dt.timedelta(days=1)
    while _is_closed(d):
        d += dt.timedelta(days=1)
    return d.isoformat()


def pe_plus(pe: str, days=LAG_DAYS) -> str:
    return (dt.date.fromisoformat(pe) + dt.timedelta(days=days)).isoformat()


def avail_of(pe: str, filed: str) -> str:
    """가용일 = max(기간말 + 90일, filed + 1 NYSE 거래일)."""
    a, b = pe_plus(pe), next_session(filed)
    return a if a >= b else b


# ════════════════════════════════════════════════════════════════════════
# 대상 CIK · 그룹
# ════════════════════════════════════════════════════════════════════════
def fx_tickers(fx_root):
    """data/fx ∪ data/fx_pit → {티커: (디렉터리, cik, std)}. eg_q5 의 FIRMS 와 같은 순서(fx 먼저 · 같은 티커면 fx 가 이긴다)."""
    out = {}
    for sub in ("fx", "fx_pit"):
        d = os.path.join(fx_root, "data", sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            tk = fn[:-5]
            if tk in out:
                continue
            j = _rj(os.path.join(d, fn))
            out[tk] = (sub, int(j["cik"]), j.get("std") or "us-gaap")
    return out


def fx_digest(fx_root):
    lines = []
    for sub in ("fx", "fx_pit"):
        d = os.path.join(fx_root, "data", sub)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                lines.append("%s/%s %s" % (sub, fn, _sha_file(os.path.join(d, fn))))
    return _sha("\n".join(lines).encode("utf-8"))


def load_groups():
    """issuer_map.load_map() 의 그룹 → {gid: [[cik, from, to, src, name], …]}. 지도 파일 해시도 돌려준다."""
    import issuer_map as IMAP                  # SEC_UA 가드가 이미 통과했다(그 모듈도 같은 가드를 건다)
    M = IMAP.load_map(ISSUER_MAP)
    return {g: v["ciks"] for g, v in M["groups"].items()}, _sha_file(ISSUER_MAP)


def all_ciks(fx_roots):
    groups, _h = load_groups()
    cs = {int(c[0]) for v in groups.values() for c in v}
    for r in fx_roots:
        cs |= {c for _s, c, _t in fx_tickers(r).values()}
    return sorted(cs)


# ════════════════════════════════════════════════════════════════════════
# 원본 고정표
# ════════════════════════════════════════════════════════════════════════
def load_manifest():
    return _rj(MANIFEST) or {
        "note": "EGFF companyfacts 원본 고정표 — sha256 은 내용 바이트(gzip 전송을 푼 JSON). 원본은 저장소 밖(EGFF_RAW · 기본 "
                "%TEMP%/egff/raw 의 CIK##########.json.gz). 다시 받아 해시가 다르면 원장을 다시 짓기 전에 멈춘다.",
        "prereg": PREREG, "url_fmt": "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json", "files": {}}


def save_manifest(man):
    man["updated"] = _now()
    ent = dict(sorted(man["files"].items()))
    head = {k: v for k, v in man.items() if k != "files"}
    lines = ["{"]
    for k, v in head.items():
        lines.append(" %s: %s," % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False)))
    lines.append(' "files": {')
    items = list(ent.items())
    for i, (k, v) in enumerate(items):
        lines.append("  %s: %s%s" % (json.dumps(k), json.dumps(v, ensure_ascii=False, separators=(",", ":")),
                                     "," if i < len(items) - 1 else ""))
    lines.append(" }")
    lines.append("}")
    _write(MANIFEST, ("\n".join(lines) + "\n").encode("utf-8"))


def raw_path(cik):
    return os.path.join(RAW, "CIK%010d.json.gz" % int(cik))


def read_raw(cik, man):
    """고정된 원본 1건(dict) — 해시를 manifest 와 맞춘다. 없거나 404 면 None."""
    m = man["files"].get("CIK%010d" % int(cik))
    if not m or m.get("status") == 404:
        return None
    p = raw_path(cik)
    b = gzip.open(p, "rb").read()
    if _sha(b) != m["sha256"]:
        raise SystemExit("🚨 원본이 manifest 해시와 다르다 — CIK %d (%s)" % (cik, p))
    return json.loads(b.decode("utf-8"))


def cmd_check():
    url = FACTS_URL % 320193
    b = edgar.fetch_bytes(url, timeout=120)
    j = json.loads(b.decode("utf-8"))
    n = j["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    print("companyfacts 1건: %d바이트 · 이름 %s · 택소노미 %s · NetIncomeLoss 관측 %d · 첫 관측 %s"
          % (len(b), j.get("entityName"), sorted(j["facts"]), len(n), sorted(n[0].items())))
    return 0


def cmd_fetch(limit=None):
    ciks = all_ciks([ROOT])
    if limit:
        ciks = ciks[:limit]
    man = load_manifest()
    t0, n_new, n_have, n_404 = time.time(), 0, 0, 0
    for i, cik in enumerate(ciks, 1):
        key = "CIK%010d" % cik
        p = raw_path(cik)
        m = man["files"].get(key)
        if m and (m.get("status") == 404 or (os.path.exists(p) and _sha(gzip.open(p, "rb").read()) == m["sha256"])):
            n_have += 1
            continue
        if m and m.get("status") != 404 and not os.path.exists(p):
            raise SystemExit("🚨 manifest 에는 있는데 원본이 없다 — %s (RAW=%s). 다시 받으면 해시가 바뀐다 · 먼저 원본을 찾을 것." % (key, RAW))
        try:
            b = edgar.fetch_bytes(FACTS_URL % cik, timeout=120, max_wait=900)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                man["files"][key] = {"sha256": None, "bytes": 0, "fetched": _now(), "status": 404}
                n_404 += 1
                continue
            raise
        json.loads(b.decode("utf-8"))              # 깨진 응답이면 여기서 죽는다(고정 전에)
        _write(p, _gz_bytes(b))
        man["files"][key] = {"sha256": _sha(b), "bytes": len(b), "fetched": _now()}
        n_new += 1
        if n_new % 50 == 0:
            save_manifest(man)
            print("  … %d/%d · 새로 %d · %.0f초" % (i, len(ciks), n_new, time.time() - t0), flush=True)
    save_manifest(man)
    print("companyfacts: 대상 %d · 새로 받음 %d · 이미 있음 %d · 404 %d · %.0f초" % (len(ciks), n_new, n_have, n_404, time.time() - t0))
    return 0


# ════════════════════════════════════════════════════════════════════════
# 원본 → 기록
# ════════════════════════════════════════════════════════════════════════
def eg_specs():
    """(택소노미, Eg 키, 태그, 단위, 스케일) — refresh_facts 의 후보 태그 그대로(Eg 입력 키만)."""
    out = []
    for tx, tags in (("us-gaap", RF.TAGS), ("ifrs-full", RF.TAGS_IFRS)):
        for spec in tags:
            if spec[0] in EG_KEYS:
                for tag in spec[1]:
                    out.append((tx, spec[0], tag, spec[2], spec[3]))
    return out


def candidates():
    """{Eg 키: {택소노미: [후보 태그 — refresh_facts 순서]}} — 빈티지 공급자가 태그 갈아타기 칸을 채울 때 쓰는 순서."""
    out = {}
    for tx, ekey, tag, _u, _s in eg_specs():
        out.setdefault(ekey, {}).setdefault(tx, []).append(tag)
    return out


def taxonomy_of(facts):
    """refresh_facts.extract 와 같은 선택 — us-gaap 이 없고 ifrs-full 이 있을 때만 IFRS."""
    allf = (facts or {}).get("facts") or {}
    if not allf.get("us-gaap") and allf.get("ifrs-full"):
        return "ifrs-full"
    return "us-gaap"


def scaled(val, scale):
    """pick.out 과 같은 반올림. 숫자가 아니면 None(pick 도 그 관측을 내보내지 않는다)."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    return round(v / 1e6, 2) if scale == SCALE_M else round(v, 4)


def bucket_of(o):
    """pick 과 같은 기간 판정 → 'q' · 'a' · 'i' · None(버림)."""
    if not o.get("end") or o.get("val") is None:
        return None
    start = o.get("start")
    if not start:
        return "i"
    n = RF._days(start, o["end"])
    if n is None:
        return None
    if 80 <= n <= 100:
        return "q"
    if 350 <= n <= 380:
        return "a"
    return None


def first_periodic(facts, lo=None, hi=None, before=None):
    """그 CIK 의 첫 XBRL 정기보고 filed(FORMS_OK 서식 · 모든 개념). lo·hi·before 를 주면 그 창 안의 제출만(선행 CIK 용)."""
    best = None
    for tx in ((facts or {}).get("facts") or {}).values():
        for node in tx.values():
            for arr in (node.get("units") or {}).values():
                for o in arr:
                    if str(o.get("form") or "") in RF.FORMS_OK and o.get("filed"):
                        f = str(o["filed"])
                        if (lo and f < lo) or (hi and f > hi) or (before and not (f < before)):
                            continue
                        if best is None or f < best:
                            best = f
    return best


def cik_records(facts, tx):
    """한 CIK 의 companyfacts → {키: {'u': 단위, 'q'|'a'|'i': {기간말: [(filed, 순서, 값, accn, form)]}}}."""
    out = {}
    fx = ((facts or {}).get("facts") or {}).get(tx) or {}
    order = 0
    for tx_, ekey, tag, unit, scale in eg_specs():
        if tx_ != tx:
            continue
        node = fx.get(tag)
        if not node:
            continue
        u, vals = RF.resolve_unit(node.get("units") or {}, unit)
        if not vals:
            continue
        key = "%s:%s:%s" % (ekey, tx, tag)
        rec = out.setdefault(key, {"u": u})
        for o in vals:
            if str(o.get("form") or "") not in RF.FORMS_OK:
                continue
            b = bucket_of(o)
            if b is None or b not in EG_BUCKETS[ekey]:
                continue
            v = scaled(o["val"], scale)
            if v is None:
                continue
            order += 1
            rec.setdefault(b, {}).setdefault(o["end"], []).append(
                (str(o.get("filed") or ""), order, v, str(o.get("accn") or ""), str(o.get("form") or "")))
    return out


def group_ledger(gid, members, primary, facts_by_cik):
    """그룹 원장 1벌. members = [[cik, from, to, src, name]] (지도) · primary = fx 의 CIK.

    선행 CIK 의 기록은 주 CIK 의 첫 정기보고보다 먼저 · 그 CIK 의 효력 구간 [from, to] 안에서 낸 것만 받는다."""
    pf = facts_by_cik.get(primary)
    first_own = first_periodic(pf) if pf else None
    tx = taxonomy_of(pf) if pf else "us-gaap"
    cells = {}
    admitted = []
    firsts = []
    multi = len([m for m in members if int(m[0]) != primary and facts_by_cik.get(int(m[0]))]) > 0
    for m in [[primary, None, None, "fx", None]] + [m for m in members if int(m[0]) != primary]:
        cik, lo, hi = int(m[0]), m[1], m[2]
        f = facts_by_cik.get(cik)
        if not f:
            admitted.append([cik, lo, hi, 0, "no-facts"])
            continue
        own = cik == primary
        recs = cik_records(f, tx)
        n_in = 0
        for key, rec in recs.items():
            dst = cells.setdefault(key, {"u": rec["u"]})
            for b in ("q", "a", "i"):
                for pe, rows in (rec.get(b) or {}).items():
                    for filed, order, v, accn, form in rows:
                        if not own:
                            if first_own and not (filed < first_own):
                                continue
                            if lo and filed < lo:
                                continue
                            if hi and filed > hi:
                                continue
                        dst.setdefault(b, {}).setdefault(pe, []).append((filed, (0 if own else 1, order), v, accn, form, cik))
                        n_in += 1
        fp = first_own if own else first_periodic(f, lo, hi, first_own)
        if fp:
            firsts.append(fp)
        admitted.append([cik, lo, hi, n_in, "primary" if own else "predecessor"])
    first_xbrl = min(firsts) if firsts else None
    keys = {}
    n_cells = n_rec = n_pre = 0
    for key in sorted(cells):
        rec = cells[key]
        kout = {"u": rec["u"]}
        for b in ("q", "a", "i"):
            bk = rec.get(b)
            if not bk:
                continue
            bout = {}
            for pe in sorted(bk):
                rows = sorted(bk[pe], key=lambda r: (r[0], 1 if r[1][0] == 0 else 0, r[1][1]))
                # 같은 제출(accn)의 같은 값은 한 번만(여러 CIK 가 같은 합동 제출을 싣는 경우 · 원본 중복).
                #   뒤의 것을 남긴다 — pick 의 동점 규칙(같은 filed 면 원본 순서의 뒤가 이긴다)과 «최신» 이 어긋나지 않게.
                seen, uniq = set(), []
                for r in reversed(rows):
                    k2 = (r[3], r[2])
                    if k2 in seen:
                        continue
                    seen.add(k2)
                    uniq.append(r)
                uniq.reverse()
                lst = []
                for j, (filed, _o, v, accn, form, cik) in enumerate(uniq):
                    a = avail_of(pe, filed)
                    if j == 0 and first_xbrl and pe < first_xbrl:
                        a = pe_plus(pe)                   # XBRL 이전 기간 — 첫 XBRL 보고값 = 종이 공시 대리(기간말 + 90일)
                        n_pre += 1
                    row = [a, v, accn, form, filed]
                    if multi:
                        row.append(cik)
                    lst.append(row)
                bout[pe] = lst
                n_cells += 1
                n_rec += len(lst)
            kout[b] = bout
        keys[key] = kout
    doc = {"gid": gid, "primary": primary, "taxonomy": tx, "first_own": first_own, "first_xbrl": first_xbrl,
           "ciks": admitted, "multi": multi, "keys": keys}
    return doc, {"cells": n_cells, "records": n_rec, "pre_xbrl_cells": n_pre}


def pick_check(facts, tx, doc):
    """원장의 «주 CIK 기록 중 filed 가 가장 늦은 값» 이 refresh_facts.pick 의 결과와 같은가(보관 깊이 안) — 같아야 한다."""
    fx = ((facts or {}).get("facts") or {}).get(tx) or {}
    eq = ne = 0
    bad = []
    for tx_, ekey, tag, unit, scale in eg_specs():
        if tx_ != tx or not fx.get(tag):
            continue
        u, vals = RF.resolve_unit(fx[tag].get("units") or {}, unit)
        if not vals:
            continue
        q, a, i = RF.pick(vals, scale)
        key = "%s:%s:%s" % (ekey, tx, tag)
        for b, ser in (("q", q), ("a", a), ("i", i)):
            if b not in EG_BUCKETS[ekey]:
                continue
            cell = ((doc["keys"].get(key) or {}).get(b)) or {}
            for pe, v in ser:
                rows = [r for r in cell.get(pe) or [] if (len(r) < 6 or r[5] == doc["primary"])]
                lv = rows[-1][1] if rows else None
                if lv == v:
                    eq += 1
                else:
                    ne += 1
                    if len(bad) < 20:
                        bad.append([key, b, pe, v, lv])
    return eq, ne, bad


def cmd_build(fx_root):
    man = load_manifest()
    groups, im_sha = load_groups()
    c2g = {}
    for g, ms in groups.items():
        for m in ms:
            c2g[int(m[0])] = g
    TK = fx_tickers(fx_root)
    by_group = {}
    for t, (sub, cik, std) in TK.items():
        g = c2g.get(cik) or ("g%d" % cik)
        by_group.setdefault(g, {}).setdefault(cik, []).append(t)
    for g, v in by_group.items():
        if len(v) > 1:
            raise SystemExit("🚨 그룹 %s 에 fx CIK 가 둘 이상이다 %s — 원장 한 벌로 못 묶는다" % (g, v))
    os.makedirs(OUT_DIR, exist_ok=True)
    idx_groups, tick = {}, {}
    tot = {"groups": 0, "cells": 0, "records": 0, "pre_xbrl_cells": 0, "pick_eq": 0, "pick_ne": 0, "no_facts": []}
    pick_bad = []
    t0 = time.time()
    keep = set()
    for g in sorted(by_group):
        (primary, tks), = by_group[g].items()
        members = groups.get(g) or [[primary, None, None, "fx-only", None]]
        facts = {}
        for m in members + [[primary]]:
            c = int(m[0])
            if c not in facts:
                facts[c] = read_raw(c, man)
        if not facts.get(primary):
            tot["no_facts"].append([g, primary, tks])
        doc, st = group_ledger(g, members, primary, facts)
        if facts.get(primary):
            e, n, bad = pick_check(facts[primary], doc["taxonomy"], doc)
            tot["pick_eq"] += e
            tot["pick_ne"] += n
            pick_bad += [[g] + b for b in bad][:max(0, 50 - len(pick_bad))]
        b = _gz_bytes(_dumps(doc).encode("utf-8"))
        fn = "%s.json.gz" % g
        keep.add(fn)
        p = os.path.join(OUT_DIR, fn)
        if not (os.path.exists(p) and open(p, "rb").read() == b):
            _write(p, b)
        idx_groups[g] = {"file": fn, "sha256": _sha(b), "primary": primary, "tickers": sorted(tks),
                         "ciks": doc["ciks"], "first_own": doc["first_own"], "first_xbrl": doc["first_xbrl"],
                         "taxonomy": doc["taxonomy"], **st}
        for t in tks:
            tick[t] = {"gid": g, "cik": primary, "src": TK[t][0]}
        tot["groups"] += 1
        for k in ("cells", "records", "pre_xbrl_cells"):
            tot[k] += st[k]
        del facts
    for fn in os.listdir(OUT_DIR):                 # 이 빌드가 쓰지 않은 옛 원장은 지운다(색인과 파일이 늘 같은 벌)
        if fn.endswith(".json.gz") and fn not in keep:
            os.remove(os.path.join(OUT_DIR, fn))
    index = {
        "note": "EGFF 빈티지 원장 색인. 원장 파일 = 그룹마다 {gid, primary, taxonomy, first_own, first_xbrl, ciks, keys: {«Eg키:택소노미:태그»: "
                "{u, q|a|i: {기간말: [[가용일, 값, accn, form, filed(, cik)], …]}}}} (filed 오름차순). 빈티지 패널은 이 원장에서 "
                "build/eg_q5_vintage.py 가 날짜마다 짓는다. 규칙은 rule 에 — 사전등록 " + PREREG + " §2.",
        "prereg": PREREG,
        "rule": {"avail": "max(기간말 + 90일, filed 다음 NYSE 거래일)",
                 "calendar": "refresh_events._holidays ∪ refresh_events.ADHOC",
                 "pre_xbrl": "기간말 < first_xbrl 이면 그 칸 첫 기록의 가용일 = 기간말 + 90일",
                 "predecessor": "주 CIK = data/fx·fx_pit 의 cik · 선행 CIK 기록은 filed < 주 CIK 첫 정기보고 · 지도 효력 구간 안",
                 "tags": "refresh_facts.TAGS / TAGS_IFRS 의 Eg 키(asset · debt · eq · ni · cfo · sh · sho) 후보 태그 전부",
                 "buckets": {k: list(v) for k, v in EG_BUCKETS.items()},
                 "period": "refresh_facts.pick 과 같다(80~100일 q · 350~380일 a · 시작 없음 i · FORMS_OK · 값 백만 단위 소수 둘째)",
                 "forms_ok": list(RF.FORMS_OK)},
        "candidates": candidates(),
        "inputs": {"issuer_map_sha256": im_sha, "manifest_sha256": _sha_file(MANIFEST),
                   "fx_digest": fx_digest(fx_root),
                   "fx_digest_rule": "sha256(«디렉터리/파일 sha256» 줄들 · 정렬) — data/fx · data/fx_pit"},
        "stats": {**tot, "pick_check": "원장의 주 CIK 최신 제출값 == refresh_facts.pick(같은 원본)",
                  "pick_bad": pick_bad},                       # 시간은 싣지 않는다 — 같은 원본이면 색인도 바이트 동일
        "tickers": dict(sorted(tick.items())),
        "groups": idx_groups,
    }
    _write(INDEX, (_dumps(index, indent=1) + "\n").encode("utf-8"))
    sz = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in keep)
    print("원장: 그룹 %d · 칸 %d · 기록 %d · XBRL 이전 대리 %d · pick 대조 같음 %d / 다름 %d · 원장 %.1fMB · %.0f초"
          % (tot["groups"], tot["cells"], tot["records"], tot["pre_xbrl_cells"], tot["pick_eq"], tot["pick_ne"],
             sz / 1e6, time.time() - t0))
    if tot["no_facts"]:
        print("  ⚠ 주 CIK 원본 없음 %d: %s" % (len(tot["no_facts"]), tot["no_facts"][:10]))
    if tot["pick_ne"]:
        print("  🚨 pick 대조 불일치 — 원장의 «최신» 이 랩 경로와 다르다: %s" % pick_bad[:5])
        return 1
    return 0


# ════════════════════════════════════════════════════════════════════════
# 자체 점검(합성)
# ════════════════════════════════════════════════════════════════════════
def cmd_selftest():
    ok = []

    def chk(name, cond):
        ok.append((name, bool(cond)))
        print("  %s %s" % ("통과" if cond else "실패", name))

    # 거래일: 2024-07-03(수) 다음은 07-05(금, 07-04 휴장) · 2012-10-26(금) 다음은 10-31(샌디 29·30 임시휴장) · 금요일 → 월요일
    chk("다음 거래일 · 독립기념일", next_session("2024-07-03") == "2024-07-05")
    chk("다음 거래일 · 임시휴장(샌디)", next_session("2012-10-26") == "2012-10-31")
    chk("다음 거래일 · 주말", next_session("2026-09-25") == "2026-09-28")
    chk("다음 거래일 · 성금요일", next_session("2026-04-02") == "2026-04-06")
    chk("가용일 = 기간말+90 이 지배", avail_of("2020-03-31", "2020-04-30") == "2020-06-29")
    chk("가용일 = 늦은 제출이 지배", avail_of("2020-03-31", "2020-07-10") == "2020-07-13")

    def fact(start, end, val, filed, form="10-Q", accn=None):
        o = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn or ("A-" + filed)}
        if start:
            o["start"] = start
        return o
    prim = {"facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": [
            fact("2008-10-01", "2008-12-31", 10e6, "2010-02-20", "10-K", "K10"),       # XBRL 이전 기간 · 첫 보고
            fact("2008-10-01", "2008-12-31", 11e6, "2011-02-20", "10-K", "K11"),       # 재작성
            fact("2010-01-01", "2010-03-31", 5e6, "2010-05-01"),
            fact("2010-01-01", "2010-03-31", 6e6, "2011-05-01"),                       # 다음 해 10-Q 비교기간 재작성
            fact("2010-01-01", "2010-06-30", 99e6, "2010-08-01"),                      # 6개월 누적 — 버린다
            fact("2010-01-01", "2010-03-31", 7e6, "2011-05-01", "8-K", "X8"),          # 서식 밖 — 버린다
            fact("2009-01-01", "2009-12-31", 40e6, "2010-02-20", "10-K", "K10"),
        ]}},
        "Assets": {"units": {"USD": [fact(None, "2009-12-31", 100e6, "2010-02-20", "10-K", "K10"),
                                     fact(None, "2009-12-31", 100e6, "2010-02-20", "10-K", "K10")]}},  # 원본 중복
    }}}
    pred = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        fact("2009-01-01", "2009-12-31", 39e6, "2010-01-15", "10-K", "P10"),          # 주 CIK 첫 보고 전 — 받는다
        fact("2009-01-01", "2009-12-31", 38e6, "2012-03-01", "10-K", "P12")]}}}}}      # 주 CIK 첫 보고 뒤 — 버린다
    members = [[1, None, None, "t", "PRIMARY"], [2, None, "2011-01-01", "t", "PRED"]]
    doc, st = group_ledger("gT", members, 1, {1: prim, 2: pred})
    ni = doc["keys"]["ni:us-gaap:NetIncomeLoss"]
    chk("첫 XBRL = 선행 CIK 의 첫 보고", doc["first_xbrl"] == "2010-01-15" and doc["first_own"] == "2010-02-20")
    q08 = ni["q"]["2008-12-31"]
    chk("XBRL 이전 칸 첫 기록 = 기간말+90", q08[0][0] == "2009-03-31" and q08[1][0] == avail_of("2008-12-31", "2011-02-20"))
    chk("누적·서식 밖 버림", set(ni["q"]) == {"2008-12-31", "2010-03-31"} and len(ni["q"]["2010-03-31"]) == 2)
    a09 = ni["a"]["2009-12-31"]
    chk("선행 CIK 기록은 주 CIK 첫 보고 전만 · filed 순", [r[1] for r in a09] == [39.0, 40.0] and a09[0][5] == 2)
    chk("원본 중복은 한 번", len(doc["keys"]["asset:us-gaap:Assets"]["i"]["2009-12-31"]) == 1)
    e, n, _b = pick_check(prim, "us-gaap", doc)
    chk("원장 최신 == pick", n == 0 and e > 0)
    chk("가용일은 filed 순으로 줄지 않는다", all(r1[0] <= r2[0] for key in doc["keys"].values() for b in ("q", "a", "i")
                                            for rows in (key.get(b) or {}).values() for r1, r2 in zip(rows, rows[1:])))
    bad = [x for x, c in ok if not c]
    print("selftest: %d/%d 통과" % (len(ok) - len(bad), len(ok)))
    return 1 if bad else 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "check":
        return cmd_check()
    if cmd == "fetch":
        lim = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
        return cmd_fetch(lim)
    if cmd == "build":
        fx_root = argv[argv.index("--fx-root") + 1] if "--fx-root" in argv else ROOT
        return cmd_build(os.path.abspath(fx_root))
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
