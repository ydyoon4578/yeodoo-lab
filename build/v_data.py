# -*- coding: utf-8 -*-
"""build/v_data.py — 배치 V 자료 층의 바탕: 판 고정(French · 랩 파일 · V-D1) · 가용 늦춤 · 선견 점검 틀 · L 층 French 대리 · 한 곳 입구.

설계 원본(구속): 설계 워크플로 산출 vbatch_research.json → final(slate V01~V07 · conditions · data_plan · build_plan · tests) — 저장소 밖 스크래치.
  이 파일은 설계를 다시 짓지 않는다. 옮기는 것은 final.build_plan.modules[v_data](French · 핀 해시 · LAGS 복사 · blind_smoke 제외)와
  자료 층 전체의 입구(`layer()` — v_pit · v_px_split · v_fund · v_ins · v_ear · v_cond 를 함수 안에서 부른다)뿐이다.
  오케스트레이터 변경(결정 8): V08 «NI — 순자사주(주주환원)» 카드를 전방 전용으로 더한다 — 자료 입력은 v_fund.net_issuance 하나(순발행 자체만).

🚨 가져오지 않는 모듈(build_plan.no_import_rule · D22): t_core · t_data · t_signals · u_data · u_core · qfwd_* · eg30plus · qg_lab · qbatch_* · q_switch ·
   eg_q5* · idxeg · eg_best · r_stages · r_r1_flags · r_r2flags. 필요한 함수는 소스째 복사했다(아래 «복사» 표지) — 원본과의 짝맞춤은
   허용 목록의 별도 감사 프로세스(v_audit)에서만 한다. 전이 가드(함수 안 import 포함)는 build/v_guard.py 가 건다.
   French 파서 = t_data.parse_french_text 복사 + 여러 줄 제목(25_ME_BETA · 6_ME_OP 의 월별 BE/ME 절) · 투자(자산 증가) 절은 읽지 않는다(Eg 인접 · 금지).
   가용 · 선견 틀 = u_data AVAIL · lag_rule · horizon · _avail_mask · asof · _poison · lookahead_check 복사(층 이름 L · S).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해서 찍지 않는다.
   --selftest 는 합성 자료만 · --smoke 는 실자료를 끝까지 돌리되 표준출력을 버리고 모양(색인 범위 · 개수 · 참/거짓)만 돌려준다(산출 파일은 열지 않고 지운다).
   --pin · --manifest 는 행 수 · 기간 · 해시 · 판 표식만. 시총 앵커 대조(v_px_split --anchors)는 자료 타당성이다(수익 아님 · 명세 data_plan.market_cap_rule).

D1 — 1926+ 장기(L) 층은 내부 기전 증거로만 · 라이선스 원자료(French · yfinance)는 저장소 밖 캐시에만($VBATCH_CACHE, 없으면 %TEMP%/vbatch_cache —
   저장소 안이면 멈춘다). 저장소에 드는 것은 data/_vb_* 의 공개 안전 명세(URL · 받은 때 · SHA-256 · 행 수 · 처음/끝 · 판정 표)뿐이다. L 층 값은 어떤 저장소 파일에도 쓰지 않는다.

  python build/v_data.py --selftest        합성 자료 시험(망 · 캐시 · 실자료를 읽지 않는다)
  python build/v_data.py --pin             French(CRSP 202608 + 2024-12 FIZ)를 캐시에 고정(설계 · 배치 U · 스카우트 사본을 SHA 로 들이고 없는 것만 받는다)
  python build/v_data.py --manifest        data/_vb_manifest.json(랩 파일 · French · V-D1 · 원 캐시 핀 — 값 없음)
  python build/v_data.py --check           고정본 SHA == 명세 · French 판 섞임 없음(굽기 전 관문 — 틀리면 1)
  python build/v_data.py --smoke           실자료 눈가린 연기 시험(자료 층 전체 · 선견 점검 · 모양만)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import inspect
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MANIFEST = os.path.join(DATA, "_vb_manifest.json")
CACHE = os.environ.get("VBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "vbatch_cache")
CRSP_WANT = "202608"                                   # French 는 CRSP 202608 한 판 — 섞이면 멈춘다(배치 U 판과 같다)
FIZ = "2024-12"                                        # 2024-12 FIZ 판 사본(보고 · 명세 data_plan.french)
SEED = 20260925                                        # 명세 parameters_table SEED · 위약 · 선견 씨앗
LOOKAHEAD_N = 200                                      # 명세 parameters_table LOOKAHEAD_T
MIN_FIRMS = 20
Z_MIN, Z_ROLL, Z_CLIP = 60, 240, 2.0                   # 명세 Z_MIN 60 · rolling240 · ±2
LATE_TOL = 1                                           # 선언 늦춤 + 1개월까지는 그 값 · 더 늦으면 z = 0(stale)
S_WIN = ("2016-09", "2026-08")                         # S 층 보유월 창(명세 tests.S_layer.window)
S_WARM = ("2014-06", "2016-08")                        # 워밍업
SE_FROM = "2010-01"                                    # S-E 추정 전용 연장(D27)
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"


# ══════════════════════════════════════════════════════════════════════════
#  캐시 · 해시
# ══════════════════════════════════════════════════════════════════════════
def _inside(p, root):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(root))
    return a == r or a.startswith(r + os.sep)


def cache_guard():
    """캐시가 저장소 안이면 멈춘다(D1 · 라이선스 원자료는 저장소 밖에만)."""
    if _inside(CACHE, ROOT):
        raise SystemExit("🚨 캐시(%s)가 저장소 안이다 — 라이선스 원자료는 저장소 밖에만 둔다(D1)." % CACHE)
    return os.path.abspath(CACHE)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def sha256_file_lf(p):
    """줄 끝을 LF 로 맞춘 SHA-256 — 추적된 랩 텍스트 자료(JSON)는 core.autocrlf=true 인 새 사본에서 CRLF 로 꺼내질 수 있다(판 점검 예행에서 확인).
    명세는 LF 판(이 저장소 core.autocrlf=false)에서 쟀으므로 LF 파일이면 sha256_file 과 같다. 원자료(French zip · V-D1 · companyfacts)는 바이트 그대로(sha256_file)."""
    with open(p, "rb") as f:
        b = f.read()
    return sha256_bytes(b.replace(b"\r\n", b"\n"))


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_bytes(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)


def read_json(p):
    if p.endswith(".gz"):
        import gzip
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def lab_path(rel):
    return os.path.join(ROOT, *rel.split("/"))


# ══════════════════════════════════════════════════════════════════════════
#  자료 목록 — French(명세 data_plan.french) · 랩 파일(핀만) · V-D1(v_px_split 이 받는다)
# ══════════════════════════════════════════════════════════════════════════
#  fid, 파일, 쓰임. 투자(자산 증가) · NI(순발행) 계열 French 파일은 V01~V07 입력에 없다(V08 은 전방 전용 · L 대리 없음).
V_FRENCH = [
    ("ff3_m", "F-F_Research_Data_Factors_CSV.zip", "Mkt · RF — SLOW · MKT3 · PANICX I_B · 목표 y = P − Mkt · RF"),
    ("ff3_d", "F-F_Research_Data_Factors_daily_CSV.zip", "Mkt-RF 일간 — RVAR(L) · PANICX σ²(L)"),
    ("me_prior12", "6_Portfolios_ME_Prior_12_2_CSV.zip", "V01 L 대리 BIG HiPRIOR"),
    ("prior12_2", "10_Portfolios_Prior_12_2_CSV.zip", "V01 쌍둥이 Hi PRIOR(10분위)"),
    ("me_beta", "25_Portfolios_ME_BETA_5x5_CSV.zip", "V02 L 대리 ME5×β1(BIG LoBETA) · G2own(월별 BE/ME 절 · BIG LoBETA − 시장)"),
    ("beta", "Portfolios_Formed_on_BETA_CSV.zip", "V02 쌍둥이 Lo 20 · BSPRD(U17 사전 베타 절)"),
    ("me_prior10", "6_Portfolios_ME_Prior_1_0_CSV.zip", "V03 L 대리 BIG LoPRIOR"),
    ("me_ep", "6_Portfolios_ME_EP_2x3_CSV.zip", "V06 L 대리 BIG HiEP"),
    ("me_op", "6_Portfolios_ME_OP_2x3_CSV.zip", "V07 L 대리 BIG HiOP · PQ(월별 BE/ME 절 HiOP − LoOP)"),
    ("beme", "Portfolios_Formed_on_BE-ME_CSV.zip", "VSPRD(U16) BE/ME 연 절 Hi 30 · Lo 30"),
    ("beme_xd", "Portfolios_Formed_on_BE-ME_Wout_Div_CSV.zip", "VSPRD(U16) 배당 제외 VW 가격 비"),
    ("ind30", "30_Industry_Portfolios_CSV.zip", "DISP(U08) 30 산업 월 VW 수익 · 기업 수"),
    ("ind49", "49_Industry_Portfolios_CSV.zip", "T-MOM-IND 쌍둥이(L French 49 산업)"),
]
FRENCH_FILES = {f: fn for f, fn, _ in V_FRENCH}
_SCOUT = os.path.join(tempfile.gettempdir(), "claude", "C--Users-Win10", "67afc626-eea1-4c7d-acf2-0ed27516b1fe", "scratchpad", "vbatch",
                      "data_audit", "french")
FRENCH_SEEDS = (  # 들일 사본 후보(차례) — SHA 는 들인 뒤 명세에 적는다(설계 해시가 없는 파일은 이 사본이 고정본)
    os.environ.get("VBATCH_FRENCH_SEED") or "",
    os.path.join(tempfile.gettempdir(), "ubatch_cache", "raw", "french"),
    _SCOUT,
)
FRENCH_SEEDS_FIZ = (os.path.join(tempfile.gettempdir(), "ubatch_cache", "raw", "french@" + FIZ),)

# 랩 파일(저장소 data/ · 이미 추적) — 해시만 적는다. EG 산출(_eg_q5* · _eg30plus · _qfwd · V0 핀)은 여기 없다(G-NoEG (3)(4)).
LAB_FILES = ("data/stocks.json", "data/pit_px.json", "data/_px_raw.json", "data/splits.json", "data/index_history.json",
             "data/index_ledger.json", "data/pit_universe.json", "data/pit_reuse.json", "data/pit_gics_sectors.json",
             "data/earn_dates.json", "data/_ins_pit/cikmonth.json", "data/_ins_pit/routine.json", "data/_ins_pit/manifest.json",
             "data/_tenq_rf.json", "data/_issuer_map.json", "data/_fxv/index.json", "data/_fxv/manifest.json",
             "data/assets.json", "data/rf_monthly.json", "data/shares_yf.json")
LAB_DIRS = ("data/sd", "data/fx", "data/fx_pit", "data/_fxv")
EG_FILE_MARKS = ("_eg_q5", "_eg30plus", "_qfwd", "_eg_best", "_idxeg", "_qbatch", "_qg_", "v0_pin", "_fund_card")   # G-NoEG (3)(4) — 읽지도 싣지도 않는다


def french_path(fid, vintage=None):
    sub = "french" if vintage is None else "french@" + vintage
    return os.path.join(cache_guard(), "raw", sub, FRENCH_FILES[fid])


def french_url(fid, vintage=None):
    fn = FRENCH_FILES[fid]
    return FF + ("ftp/" if vintage is None else "ftp_202412/") + fn


def _http_get(url, ua=UA_BROWSER, timeout=90, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), {"status": r.status, "last_modified": r.headers.get("Last-Modified")}
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 410):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(2.0 * (k + 1))
    raise last


def pin_french(fetch=True):
    """French 13 파일 × (CRSP 202608 · 2024-12 FIZ) 를 캐시 raw/ 에 고정 — 있으면 그대로(판 동결) · 없으면 사본 → 받기.
    돌려주는 것 {키: 상태}. 판 표식(CRSP)이 CRSP_WANT 가 아니면 들이지 않는다."""
    out = {}
    for fid, fn, _ in V_FRENCH:
        for vint, seeds in ((None, FRENCH_SEEDS), (FIZ, FRENCH_SEEDS_FIZ)):
            key = "french%s/%s" % ("" if vint is None else "@" + vint, fid)
            p = french_path(fid, vint)
            if os.path.exists(p):
                out[key] = "고정본 있음"
                continue
            blob, origin = None, None
            for s in seeds:
                if s and os.path.exists(os.path.join(s, fn)):
                    with open(os.path.join(s, fn), "rb") as f:
                        blob = f.read()
                    origin = "copy:" + ("ubatch_cache" if "ubatch_cache" in s else ("scout" if s == _SCOUT else "env"))
                    break
            if blob is None and fetch:
                try:
                    blob, info = _http_get(french_url(fid, vint))
                    origin = "live " + (info.get("last_modified") or "")
                    time.sleep(0.6)
                except Exception as e:
                    out[key] = "🚨 받기 실패 %s" % repr(e)[:120]
                    continue
            if blob is None:
                out[key] = "사본 없음"
                continue
            if blob[:2] != b"PK":
                out[key] = "🚨 zip 아님 — 들이지 않음"
                continue
            f = parse_french_blob(blob)
            want = CRSP_WANT if vint is None else vint.replace("-", "")
            if f["crsp"] != want and vint is None:
                out[key] = "🚨 CRSP %s ≠ %s — 들이지 않음" % (f["crsp"], want)
                continue
            _write_bytes(p, blob)
            meta = {"key": key, "origin": origin, "sha256": sha256_bytes(blob), "bytes": len(blob), "crsp": f["crsp"], "pinned_at": _now(),
                    "url": french_url(fid, vint)}
            mp = os.path.join(cache_guard(), "meta", key.replace("/", "__") + ".json")
            _write_bytes(mp, json.dumps(meta, ensure_ascii=False, indent=1).encode("utf-8"))
            out[key] = "들임(%s · CRSP %s)" % (origin, f["crsp"])
    return out


# ══════════════════════════════════════════════════════════════════════════
#  French 다절 CSV 파서 — 복사: t_data.parse_french_text/_block_kind(여러 줄 제목 · 월별 BE/ME 절 · 투자 절 금지를 더함)
# ══════════════════════════════════════════════════════════════════════════
_DATE_LENS = (4, 6, 8)
MISSING_CODES = (-99.99, -999.0)
RETURN_KINDS = ("m", "d", "a", "vw_m", "ew_m", "vw_a", "ew_a")
FORBIDDEN_BLOCK_RX = re.compile(r"investment|rate of growth of assets|\baverage of ni\b")   # Eg 인접 · 순발행 절 — 파서가 버린다(정규화한 제목에)


def _is_data_line(ln):
    tok = ln.replace(",", " ").split()
    return bool(tok) and tok[0].isdigit() and len(tok[0]) in _DATE_LENS


def _norm_col(c):
    c = re.sub(r"\s+", " ", c.strip())
    m = re.match(r"^(\d)-Dec$", c)
    return "Dec %s" % m.group(1) if m else c


def _block_kind(title, dlen):
    t = title.lower().replace("value-weighted", "value weight").replace("weighted", "weight")
    ann = "annual" in t or dlen == 4
    if FORBIDDEN_BLOCK_RX.search(t):
        return "forbidden"
    if "number of firms" in t:
        return "nfirms"
    if "average firm size" in t or "average market cap" in t:
        return "avgsize"
    if "value weight average of be_fyt-1/me_june" in t:
        return "vwbeme_jun" + ("_a" if dlen == 4 else "")
    if "value weight average of be/me calculated" in t or "value weight average of be / me calculated" in t:
        return "vwbeme_m" if dlen == 6 else "vwbeme_a"
    if "value weight average of prior beta calculated" in t:
        return "vwbeta_m" if dlen == 6 else "vwbeta_a"
    if "value weight average of op" in t:
        return "vwop_m" if dlen == 6 else "vwop_a"
    if "value weight average of" in t:
        return "vwavg" + ("_a" if dlen == 4 else "")
    if t.startswith("sum of"):
        return "sum_ratio"
    if "equal weight" in t and "return" in t:
        return "ew_a" if ann else "ew_m"
    if "value weight" in t and "return" in t:
        return "vw_a" if ann else "vw_m"
    if t == "" or "factors" in t:
        return {4: "a", 6: "m", 8: "d"}[dlen]
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40]


def _num(tok):
    tok = tok.strip()
    if tok == "":
        return np.nan
    v = float(tok)
    for m in MISSING_CODES:
        if abs(v - m) < 1e-9:
            return np.nan
    return v


def _period_index(dates, dlen):
    if dlen == 6:
        return pd.PeriodIndex(["%s-%s" % (d[:4], d[4:6]) for d in dates], freq="M")
    if dlen == 8:
        return pd.DatetimeIndex(pd.to_datetime(dates, format="%Y%m%d"))
    return pd.Index([int(d) for d in dates], name="year")


def parse_french_text(txt):
    """French 자료실 파일 → {"blocks": {kind: DataFrame(원 단위)}, "titles", "cols", "crsp", "n_missing", "forbidden"}.
    절 = 제목 줄들(빈 줄 뒤 · 여러 줄이면 이어 붙인다) + 머리글 줄 + 날짜로 시작하는 줄들. −99.99 · −999 는 NaN.
    «forbidden» 절(투자 · 자산 증가 · NI)은 blocks 에 넣지 않고 제목만 센다."""
    lines = txt.replace("\r", "").split("\n")
    raw, cur = [], None

    def _cols_of(h):
        return [c for c in h.split(",")][1:] if "," in h else h.split()
    for i, ln in enumerate(lines):
        if _is_data_line(ln):
            if cur is None:
                j = i - 1
                hdr = lines[j] if j >= 0 else ""
                if hdr.strip() == "":
                    k = j
                    while k >= 0 and lines[k].strip() == "":
                        k -= 1
                    ntok = len(ln.split(",")) if "," in ln else len(ln.split())
                    if k >= 0 and not _is_data_line(lines[k]) and len(_cols_of(lines[k])) == ntok - 1 and ntok > 1:
                        j, hdr = k, lines[k]
                tl, k = [], j - 1
                while k >= 0 and lines[k].strip() != "" and not _is_data_line(lines[k]) and len(tl) < 8:
                    tl.insert(0, lines[k].strip())
                    k -= 1
                title = " ".join(tl)
                cur = {"title": title, "cols": [_norm_col(c) for c in _cols_of(hdr)], "rows": [], "hdr_line": j}
                raw.append(cur)
            cur["rows"].append([t for t in ln.split(",")] if "," in ln else ln.split())
        else:
            cur = None
    if not raw:
        raise ValueError("French 파일에서 자료 절을 못 찾았다")
    m = re.search(r"(\d{6}) CRSP database", " ".join(lines[:12]))
    out = {"blocks": {}, "titles": {}, "cols": {}, "n_missing": {}, "crsp": m.group(1) if m else None, "forbidden": []}
    for b in raw:
        dlen = len(b["rows"][0][0].strip())
        kind = _block_kind(b["title"], dlen)
        if kind == "forbidden":
            out["forbidden"].append(b["title"][:80])
            continue
        k2, n = kind, 2
        while k2 in out["blocks"]:
            k2, n = "%s_%d" % (kind, n), n + 1
        cols = b["cols"] or ["c%d" % j for j in range(1, len(b["rows"][0]))]
        vals, dates, nmiss = [], [], 0
        for r in b["rows"]:
            d = r[0].strip()
            if len(d) != dlen:
                continue
            row = [_num(x) for x in r[1:1 + len(cols)]]
            row += [np.nan] * (len(cols) - len(row))
            nmiss += sum(1 for x, t in zip(row, r[1:1 + len(cols)]) if x != x and t.strip() != "")
            vals.append(row)
            dates.append(d)
        df = pd.DataFrame(vals, index=_period_index(dates, dlen), columns=cols)
        df = df[~df.index.duplicated(keep="first")].sort_index()
        out["blocks"][k2], out["titles"][k2], out["cols"][k2], out["n_missing"][k2] = df, b["title"], cols, nmiss
    return out


def parse_french_blob(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = [n for n in z.namelist() if not n.endswith("/")]
    out = parse_french_text(z.read(names[0]).decode("latin-1"))
    out["inner"] = names[0].split("/")[-1]
    return out


_FR = {}


def load_french(fid, vintage=None):
    key = (fid, vintage)
    if key not in _FR:
        p = french_path(fid, vintage)
        if not os.path.exists(p):
            raise FileNotFoundError("French 고정본 없음: %s — python build/v_data.py --pin" % fid)
        with open(p, "rb") as f:
            fr = parse_french_blob(f.read())
        want = CRSP_WANT if vintage is None else None
        if want and fr["crsp"] != want:
            raise SystemExit("🚨 %s 판 표식 CRSP %s ≠ %s — French 판이 섞이면 멈춘다" % (fid, fr["crsp"], want))
        _FR[key] = fr
    return _FR[key]


def french(fid, kind=None, vintage=None, pct=True):
    """French 표 한 절 — 수익 절은 pct=True 면 소수(÷100) · 기업 수 · 규모 · 비율 절은 원 단위."""
    f = load_french(fid, vintage)
    B = f["blocks"]
    if kind is None:
        kind = next(k for k in ("vw_m", "m", "d") if k in B)
    if kind not in B:
        raise KeyError("%s 에 절 %s 가 없다(있는 절: %s)" % (fid, kind, ", ".join(B)))
    df = B[kind].copy()
    if pct and re.sub(r"_\d+$", "", kind) in RETURN_KINDS:
        df = df / 100.0
    return df


def ff3(freq="m", vintage=None):
    """F-F 3팩터(소수) · Mkt = Mkt-RF + RF."""
    df = french("ff3_m" if freq == "m" else "ff3_d", "m" if freq == "m" else "d", vintage=vintage)
    df["Mkt"] = df["Mkt-RF"] + df["RF"]
    return df


# ══════════════════════════════════════════════════════════════════════════
#  랩 시장 계열(S 층) — SPY 총수익 일간(data/assets.json) · rf_monthly(DGS3MO 월복리)
# ══════════════════════════════════════════════════════════════════════════
def lab_spy_daily():
    A = read_json(lab_path("data/assets.json"))
    s = pd.Series([np.nan if v is None else float(v) for v in A["px"]["SPY"]], index=pd.DatetimeIndex(pd.to_datetime(A["dates"])))
    return s.dropna().sort_index()


def lab_rf_monthly():
    R = read_json(lab_path("data/rf_monthly.json"))["monthly"]
    ks = sorted(R)
    return pd.Series([float(R[k]) for k in ks], index=pd.PeriodIndex(ks, freq="M"), name="rf")


def daily_rf_from_monthly(rf_m, days):
    """월 무위험 → 그달 거래일마다 같은 일 수익((1 + rf_m)^(1/n) − 1) — 복사: u_data.daily_rf_from_monthly."""
    d = pd.DatetimeIndex(days)
    per = d.to_period("M")
    n = pd.Series(1, index=d).groupby(per).transform("count").to_numpy()
    r = pd.Series(rf_m).reindex(per).to_numpy(float)
    return pd.Series((1.0 + r) ** (1.0 / n) - 1.0, index=d)


def contiguous(s):
    """월 계열을 빈 달 없는 색인으로 — 복사: t_signals.contiguous."""
    s = s.sort_index()
    if len(s) == 0:
        return s
    return s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))


def lagged(s, k):
    """관측 달 s 의 값을 결정 달 s + k 에 — 복사: t_signals.lagged."""
    out = s.copy()
    out.index = out.index + k
    return out


def month_last(daily):
    d = daily.dropna()
    return d.groupby(d.index.to_period("M")).last()


def month_ret_from_daily(px):
    """일 가격 → 월 수익(그달 마지막 값 ÷ 전달 마지막 값 − 1) — 복사: u_data.month_ret_from_daily."""
    m = contiguous(month_last(pd.Series(px, dtype=float)))
    return (m / m.shift(1) - 1.0).dropna()


# ══════════════════════════════════════════════════════════════════════════
#  가용 늦춤 — 복사: u_data AVAIL · lag_rule · horizon · _avail_mask · asof (층 이름 SF → S)
# ══════════════════════════════════════════════════════════════════════════
#  이름 → (L 층, S 층) 달 수 · None = 그 층에서 쓰지 않음. «월말 t 결정에 쓸 수 있는 마지막 관측 달» = t − 규칙.
#  종목 수준(가격 · 8-K · Form 4 · _fxv · 10-Q · 섹터)은 달 규칙이 아니라 기록마다 가용일(날짜)로 건다 — PIT_AVAIL 표(아래).
AVAIL = {
    "french:mkt": (0, 2),       # Mkt · RF 월 — 시장 상태(SLOW · MKT3 · PANICX I_B) · S 는 t−2 까지 + t−1 · t 는 SPY TR · 랩 rf
    "french:mkt_d": (0, 2),     # Mkt-RF 일 — RVAR · PANICX σ²(L) · S 는 SPY 일간
    "french:lag2": (2, 2),      # 포트폴리오 · 산업 · 목표 y · BE/ME 월 절 — 모든 층 t−2(French 실시간 공표 · 명세 Y_LAG 2)
    "french:june": (2, 2),      # 연 비율 절(BE/ME · 사전 베타) — 행 Y 는 Y년 6월 관측, 그 뒤 t−2
    "lab:spy": (None, 0),       # S 만 — SPY TR 월
    "lab:spy_d": (None, 0),     # S 만 — SPY 일간(RVAR · σ²)
    "lab:rf": (None, 0),        # S 만 — rf_monthly
    "v:book_y": (None, 0),      # S 만 — θ = 1 책 능동수익(보유월 s 의 값은 s 월말에 안다 · G1rel S 늦춤 0 선견 점검 · 검토 고침)
}
FORBIDDEN = {"fred:USREC": "경기후퇴 표지(u_data FORBIDDEN)", "fred:USRECM": "경기후퇴 표지", "fred:RECPROUSM156N": "경기후퇴 확률",
             "gz:ebp": "EBP(u_data FORBIDDEN)", "gz:est_prob": "경기후퇴 확률", "wurgler:recess": "경기후퇴 표지",
             "fred:TEDRATE": "지연 TED(명세 conditions.forbidden)", "eg:score": "Eg 점수 — v_cmp 밖 금지", "eg:eg30": "EG30 보유 — v_cmp 밖 금지",
             "eg:qg30": "QG30 — v_cmp 밖 금지", "fund:cfo": "cfo(Cop · Eg 입력) 금지", "fund:investment": "투자 · 자산 증가 신호 금지",
             "fund:accruals": "발생액 신호 금지"}
MODES = ("L", "S")
# 종목 수준 가용일 규칙(날짜) — 모든 PIT 입력은 «가용일 ≤ 결정일 d(월말 거래일 종가)» 만 쓴다
PIT_AVAIL = {
    "px": "그날 종가(결정일 d 까지 · d 종가 포함)",
    "8k": "8-K Item 2.02 EDGAR 접수일 f — CAR 창 끝 f+1 ≤ d(창이 다 관측된 발표만) · 가장 최근 = f+1 ≤ d 인 것 가운데 가장 늦은 것",
    "form4": "_ins_pit 가용월 = FILING_DATE 다음 NYSE 거래일의 달(R1 규칙) — 결정 달 m 에는 가용월 ≤ m",
    "fxv": "_fxv 기록 가용일 = max(기간말 + 90일, filed 다음 NYSE 거래일) ≤ d",
    "wide": "넓힌 원장(원 companyfacts) 같은 가용일 규칙 ≤ d",
    "tenq": "_tenq_rf avail(16:00 ET 뒤 · 휴장 → 다음 거래일 · filingDate 바닥) — 공개월 ≤ m",
    "sector": "pit_gics_sectors 월 m 또는 과거 쪽 가장 가까운 달(미래 달 금지) · 2014-06 앞(S-E 추정 전용)은 첫 달 값(선견 · 공개)",
    "members": "index_history 월말 명단(위키 과거 리비전) · 2014-06 앞(S-E 추정 전용)은 첫 달 명단(선견 · 생존 · 공개)",
    "split": "분할 사건일 ≤ d 만 주식수에 곱한다 · V-D1 가격의 사건 계수는 오늘까지(가격 수준 되돌림 — ME 에서 상쇄 · 선견 점검 대상)",
}


def lag_rule(name, mode="L"):
    if mode not in MODES:
        raise ValueError("mode 는 L · S")
    if name in FORBIDDEN:
        raise PermissionError("🚨 %s — %s" % (name, FORBIDDEN[name]))
    if name not in AVAIL:
        raise KeyError("가용 늦춤이 선언되지 않은 입력: %s — AVAIL 에 먼저 적는다(선언 없이 쓰지 않는다)" % name)
    r = AVAIL[name][MODES.index(mode)]
    if r is None:
        raise KeyError("%s 는 %s 층에서 쓰지 않는다" % (name, mode))
    return r


def horizon(name, t, mode="L", extra=0):
    return pd.Period(t, "M") - int(lag_rule(name, mode)) - extra


def _avail_mask(obj, name, t, mode, extra=0):
    h = horizon(name, t, mode, extra)
    idx = obj.index
    if isinstance(idx, pd.PeriodIndex):
        return np.asarray(idx <= h)
    if isinstance(idx, pd.DatetimeIndex):
        return np.asarray(idx <= h.end_time)
    yrs = pd.Index(idx).astype(int)
    if name == "french:june":
        return np.asarray([pd.Period("%04d-06" % y, "M") <= h for y in yrs])
    last_year = h.year if h.month == 12 else h.year - 1
    return np.asarray(yrs <= last_year)


def asof(obj, name, t, mode="L", extra=0):
    return obj.loc[_avail_mask(obj, name, t, mode, extra)]


# ══════════════════════════════════════════════════════════════════════════
#  선견 점검 틀 — 복사: u_data _row · _same · _poison · lookahead_check · require_no_lookahead
# ══════════════════════════════════════════════════════════════════════════
def _row(x, t):
    try:
        v = x.loc[t]
    except KeyError:
        return None
    return np.atleast_1d(np.asarray(v, dtype=float))


def _same(a, b, atol):
    if a is None or b is None or a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    return bool((na == nb).all() and np.allclose(a[~na], b[~nb], atol=atol, rtol=0))


def _poison(obj, name, t, mode, rng, extra=0):
    bad = ~_avail_mask(obj, name, t, mode, extra)
    if not bad.any():
        return obj
    out = obj.copy()
    if isinstance(out, pd.Series):
        out = out.astype(float)
        out.iloc[np.flatnonzero(bad)] = rng.normal(0.0, 37.0, int(bad.sum()))
        return out
    for c in out.columns:
        if not pd.api.types.is_numeric_dtype(out[c]):
            continue
        col = out[c].astype(float).to_numpy().copy()
        col[bad] = rng.normal(0.0, 37.0, int(bad.sum()))
        out[c] = col
    return out


def lookahead_check(signal_fn, inputs, n=LOOKAHEAD_N, seed=SEED, mode="L", t_min=None, t_max=None, poison=True, atol=1e-10, extra=0):
    """결정 달 t 의 값은 «t 에 쓸 수 있는 자료»로만 — 무작위 t n 개에서 (1) 모든 입력을 가용 지평에서 잘라 다시 계산한 값과
    (2) 지평 뒤 값을 난수로 바꾼 입력으로 다시 계산한 값이 원 값과 같아야 한다.
      signal_fn(**{인자: obj}) → PeriodIndex(결정 달) Series/DataFrame · signal_fn 이 _t 를 받으면 그 달만 부탁한다
      inputs = {인자: (obj, 가용 이름)} — 가용 이름은 AVAIL 에 선언된 것.
    돌려주는 것 {"ok", "n", "n_bad", "bad"(≤ 5 · t · 시험 · 오류 — 값은 싣지 않는다), "mode", "seed"}."""
    takes_t = "_t" in inspect.signature(signal_fn).parameters
    full = signal_fn(**{k: o for k, (o, nm) in inputs.items()})
    fr = full.to_frame() if isinstance(full, pd.Series) else full
    cand = fr.index[fr.notna().any(axis=1).to_numpy()]
    if t_min is not None:
        cand = cand[cand >= pd.Period(t_min, "M")]
    if t_max is not None:
        cand = cand[cand <= pd.Period(t_max, "M")]
    if len(cand) == 0:
        return {"ok": False, "n": 0, "n_bad": 0, "bad": [], "mode": mode, "seed": seed, "err": "유효한 결정 달이 없다"}
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(cand), size=min(n, len(cand)), replace=False))
    prng = np.random.default_rng(seed + 1)
    bad = []
    for i in pick:
        t = cand[i]
        want = _row(fr, t)
        tests = [("자르기", {k: asof(o, nm, t, mode, extra) for k, (o, nm) in inputs.items()})]
        if poison:
            tests.append(("난수", {k: _poison(o, nm, t, mode, prng, extra) for k, (o, nm) in inputs.items()}))
        for how, args in tests:
            try:
                with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                    got = signal_fn(**args, _t=t) if takes_t else signal_fn(**args)
                got = _row(got.to_frame() if isinstance(got, pd.Series) else got, t)
                err = None
            except Exception as e:
                got, err = None, type(e).__name__
            if not _same(want, got, atol):
                bad.append({"t": str(t), "test": how, "err": err})
    return {"ok": not bad, "n": int(len(pick)), "n_bad": len(bad), "bad": bad[:5], "mode": mode, "seed": seed}


def require_no_lookahead(res, label=""):
    if not res.get("ok"):
        raise SystemExit("🚨 선견 점검 실패 %s — %d/%d · 첫 사례 %s · 굽지 않는다." % (label, res.get("n_bad", 0), res.get("n", 0),
                                                                      (res.get("bad") or [{}])[0].get("t")))
    return True


def pit_lookahead(compute, world, months, poison_after, n=24, seed=SEED, atol=1e-10):
    """종목 수준(PIT) 선견 점검 — 결정 달 m(결정일 d) n 개에서 «d 뒤» 자료를 모두 난수로 바꾼 세계로 다시 계산한 값이 같아야 한다.
      compute(world, m) → {이름: 값 | 튜플 | None}(값만 비교 · 순서 무관)
      poison_after(world, d, rng) → 독 넣은 세계(가격 d 뒤 · 8-K d 뒤 접수 · Form 4 가용월 > m · 원장 가용일 > d · 10-Q 가용 > d · 분할 d 뒤)
    돌려주는 것 {"ok", "n", "n_bad", "bad"(≤ 5 · 달 · 다른 이름 수 — 값은 싣지 않는다), "seed"}."""
    months = list(months)
    if not months:
        return {"ok": False, "n": 0, "n_bad": 0, "bad": [], "seed": seed, "err": "달이 없다"}
    rng = np.random.default_rng(seed)
    pick = sorted(rng.choice(len(months), size=min(n, len(months)), replace=False))
    prng = np.random.default_rng(seed + 1)
    bad = []
    for j in pick:
        m = months[j]
        a = compute(world, m)
        W2 = poison_after(world, m, prng)
        try:
            b = compute(W2, m)
            err = None
        except Exception as e:
            b, err = {}, type(e).__name__
        diff = 0
        for k in set(a) | set(b):
            x, y = a.get(k), b.get(k)
            if x is None and y is None:
                continue
            if x is None or y is None:
                diff += 1
                continue
            xa, ya = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float))
            if not _same(xa, ya, atol):
                diff += 1
        if diff or err:
            bad.append({"m": str(m), "n_diff": diff, "err": err})
    return {"ok": not bad, "n": len(pick), "n_bad": len(bad), "bad": bad[:5], "seed": seed}


# ══════════════════════════════════════════════════════════════════════════
#  L 층 French 대리(명세 slate[*].L_proxy) — y_f,t = P_f,t − Mkt_t(소수) · 쌍둥이 · 기업 수 마스크
# ══════════════════════════════════════════════════════════════════════════
#  전략 → (파일, 칸) · 쌍둥이 목록. V04 INS · V05 EAR · V08 NI 는 L 대리가 없다(명세 · V05 OSAP 은 선택 — F0 라이선스 확인 전 없음).
L_PROXIES = {
    "V01": {"main": ("me_prior12", "BIG HiPRIOR"), "twins": {"T-MOM-10": ("prior12_2", "Hi PRIOR")}, "first": "1927-01"},
    "V02": {"main": ("me_beta", "BIG LoBETA"), "twins": {"T-LBS-LO20": ("beta", "Lo 20")}, "first": "1963-07"},   # ME5 × β1 = French «BIG LoBETA»
    "V03": {"main": ("me_prior10", "BIG LoPRIOR"), "twins": {}, "first": "1926-02"},
    "V06": {"main": ("me_ep", "BIG HiEP"), "twins": {}, "first": "1951-07"},
    "V07": {"main": ("me_op", "BIG HiOP"), "twins": {}, "first": "1963-07"},
}


def l_leg(fid, col, vintage=None):
    """French 칸 하나의 VW 월 수익(소수) · 그달 기업 수 < 20 이면 NaN(측정 불가 · t_data.french_firm_mask 와 같은 문턱)."""
    r = french(fid, "vw_m", vintage=vintage)[col]
    n = french(fid, "nfirms", vintage=vintage, pct=False)
    if col in n.columns:
        r = r.where(n[col].reindex(r.index) >= MIN_FIRMS)
    return contiguous(r)


def l_proxy(sid, which="main", vintage=None):
    """전략 sid 의 L 대리 y = P − Mkt(관측 달 색인 · 늦춤 없음 — 목표 y 의 늦춤 2 는 추정기가 건다). 🚨 L 층 값은 저장소에 쓰지 않는다(D1)."""
    spec = L_PROXIES[sid]
    fid, col = spec["main"] if which == "main" else spec["twins"][which]
    leg = l_leg(fid, col, vintage)
    mkt = contiguous(ff3("m", vintage)["Mkt"])
    idx = leg.index.intersection(mkt.index)
    return (leg.reindex(idx) - mkt.reindex(idx)).rename("%s:%s" % (sid, which))


def french_cols(fid, kind="vw_m"):
    return list(load_french(fid)["cols"][kind])


# ══════════════════════════════════════════════════════════════════════════
#  공통 도우미 — NYSE 거래일(가격 격자 = 거래일) · 월말 결정일
# ══════════════════════════════════════════════════════════════════════════
def grid_dates():
    """랩 가격 격자(stocks.json pxd_dates) — NYSE 거래일 목록(2009-01-02~). 결정일 = 그달 격자 마지막 날."""
    S = read_json(lab_path("data/stocks.json"))
    return list(S["pxd_dates"])


def month_ends(dates):
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    return me


def next_session(dates, d):
    """d 다음 NYSE 거래일(격자 안) — 격자 밖이면 d 다음 평일(주말만 건너뜀 · 선언)."""
    import bisect
    j = bisect.bisect_right(dates, d)
    if j < len(dates):
        return dates[j]
    x = _dt.date.fromisoformat(d) + _dt.timedelta(days=1)
    while x.weekday() >= 5:
        x += _dt.timedelta(days=1)
    return x.isoformat()


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def mrange(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


# ══════════════════════════════════════════════════════════════════════════
#  주식 중심 무결성 — 복사: u_data.DERIV_MARKS · assert_no_derivatives(자료 목록에 선물 · 옵션 · 변동성 지수 표식 없음)
# ══════════════════════════════════════════════════════════════════════════
DERIV_MARKS = re.compile(r"(?i)(futur|option|=F\b|\bMES\b|\bES1\b|BXM|\bVIX|cboe|covered|put_|_put|\bPUT\b|margin)")


def data_registry():
    """이 배치가 읽는 자료 한 벌(키 → 파일 · URL · 쓰임) — 선물 · 옵션 계열은 받지도 않는다."""
    R = {}
    for fid, fn, use in V_FRENCH:
        R["french/" + fid] = {"key": "french/" + fid, "fname": fn, "url": FF + "ftp/" + fn, "use": use}
    for rel in LAB_FILES:
        R["lab/" + rel] = {"key": "lab/" + rel, "fname": rel, "url": "repo", "use": "랩 자료(해시만)"}
    R["vd1"] = {"key": "vd1", "fname": "vd1/<ticker>.csv", "url": "yfinance:history(auto_adjust=False, actions=True)", "use": "V-D1 분할 조정 종가"}
    R["companyfacts"] = {"key": "companyfacts", "fname": "companyfacts/CIK##########.json.gz", "url": "SEC EDGAR companyfacts API(원 캐시 핀 사본 · 이 모듈은 SEC 를 부르지 않는다 — SEC 요청은 edgar.py 한 곳)",
                         "use": "넓힌 최초 제출 원장(매출 · 원가 · 판관비 · 이자 · 영업이익 · D&A)"}
    return R


def assert_no_derivatives(R=None):
    R = R or data_registry()
    hits = []
    for key, ds in R.items():
        for fld in ("key", "fname", "url", "use"):
            if DERIV_MARKS.search(str(ds.get(fld) or "")):
                hits.append("%s.%s" % (key, fld))
    if hits:
        raise SystemExit("🚨 선물 · 옵션 표식이 자료 목록에 있다(주식 중심): %s" % ", ".join(hits[:5]))
    return True


def assert_no_eg_files(paths):
    """G-NoEG (3)(4) — 읽는 파일 · 명세 목록에 EG 산출(_eg_q5* · _eg30plus · _qfwd · V0 핀 …)이 없어야 한다."""
    bad = [p for p in paths if any(mk in str(p) for mk in EG_FILE_MARKS)]
    if bad:
        raise SystemExit("🚨 EG 산출 파일을 읽거나 싣는다(G-NoEG): %s" % ", ".join(map(str, bad[:5])))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  명세(data/_vb_manifest.json) — 값 없이 URL · 받은 때 · SHA-256 · 행 수 · 처음/끝 · 판
# ══════════════════════════════════════════════════════════════════════════
def _lab_dir_sha(rel):
    d = lab_path(rel)
    if not os.path.isdir(d):
        return None, 0
    lines = []
    for fn in sorted(os.listdir(d)):
        fp = os.path.join(d, fn)
        if os.path.isfile(fp):
            lines.append("%s\t%s\n" % (fn, sha256_file(fp)))
    return sha256_bytes("".join(lines).encode("utf-8")), len(lines)


def _french_summary(fid, vintage=None):
    p = french_path(fid, vintage)
    if not os.path.exists(p):
        return {"state": "고정본 없음"}
    with open(p, "rb") as f:
        blob = f.read()
    fr = parse_french_blob(blob)
    blocks = []
    for k, df in fr["blocks"].items():
        a, b = (str(df.index.min()), str(df.index.max())) if len(df) else (None, None)
        blocks.append({"kind": k, "rows": int(len(df)), "first": a, "last": b, "n_cols": int(df.shape[1])})
    mp = os.path.join(cache_guard(), "meta", ("french%s/%s" % ("" if vintage is None else "@" + vintage, fid)).replace("/", "__") + ".json")
    meta = read_json(mp) if os.path.exists(mp) else {}
    return {"sha256": sha256_bytes(blob), "bytes": len(blob), "crsp": fr["crsp"], "inner": fr["inner"], "origin": meta.get("origin"),
            "pinned_at": meta.get("pinned_at"), "url": french_url(fid, vintage), "blocks": blocks, "forbidden_blocks_skipped": len(fr["forbidden"])}


def build_manifest(write=True, extra=None):
    """공개 안전 명세 — 값 계열은 싣지 않는다(해시 · 개수 · 기간뿐). extra = 다른 v_ 모듈이 보태는 핀 칸(V-D1 · 원 캐시 · 문헌 열기)."""
    assert_no_eg_files(LAB_FILES)
    lab = {}
    for rel in LAB_FILES:
        p = lab_path(rel)
        lab[rel] = {"sha256": sha256_file(p), "bytes": os.path.getsize(p)} if os.path.exists(p) else {"state": "없음"}
    dirs = {}
    for rel in LAB_DIRS:
        s, n = _lab_dir_sha(rel)
        dirs[rel] = {"digest": s, "files": n, "rule": "sha256(«이름 \\t sha256 \\n» 을 이름 차례로)"}
    fr = {}
    for fid, fn, use in V_FRENCH:
        fr["french/" + fid] = dict(_french_summary(fid), use=use, license="French: 문구 없음 — 출처 표기 · 원자료 재게시 안 함(캐시만 · D1)")
        fr["french@%s/%s" % (FIZ, fid)] = _french_summary(fid, FIZ)
    doc = {"note": ("배치 V 자료 판 동결 — build/v_data.py 가 쓴다. 값은 없다: URL · 받은 때 · SHA-256 · 행 수 · 기간 · 구조만. "
                    "French · yfinance · companyfacts 원자료는 저장소 밖 캐시에만 있다(D1 — L 층은 내부 기전 증거 · 사이트 자료가 아니다)."),
           "generated_at": _now(), "cache_root": "$VBATCH_CACHE 또는 %TEMP%/vbatch_cache (저장소 밖)",
           "design": "vbatch_research.json final(설계 워크플로 2026-09-26) · 오케스트레이터 결정 8 변경(V08 전방 전용)",
           "crsp_vintage": CRSP_WANT, "fiz_vintage": FIZ,
           "availability": {k: {"L": v[0], "S": v[1]} for k, v in AVAIL.items()}, "pit_availability": PIT_AVAIL,
           "forbidden_inputs": FORBIDDEN, "lab_files": lab, "lab_dirs": dirs, "french": fr}
    if extra:
        doc.update(extra)
    if write:
        txt = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        _no_value_series(doc)
        io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(txt)
    return doc


def _no_value_series(doc, path="", max_len=4):
    """공개 명세에 숫자 목록(값 계열)이 들어가지 않았는지 — 숫자 다섯 개 넘는 목록이 있으면 멈춘다(u_data.value_like_lists 문턱)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            _no_value_series(v, path + "/" + str(k), max_len)
    elif isinstance(doc, list):
        nums = [x for x in doc if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) > max_len:
            raise SystemExit("🚨 공개 명세에 값 계열 같은 숫자 목록: %s" % path)
        for x in doc:
            _no_value_series(x, path + "[]", max_len)


def check_pins():
    """고정본 SHA == 명세 · French 판 섞임 없음 — (ok, 문제 목록)."""
    if not os.path.exists(MANIFEST):
        return False, ["명세 없음 — --manifest"]
    doc = read_json(MANIFEST)
    bad = []
    for rel, rec in doc.get("lab_files", {}).items():
        p = lab_path(rel)
        if "sha256" in rec and (not os.path.exists(p) or sha256_file_lf(p) != rec["sha256"]):
            bad.append("lab %s: SHA 다름" % rel)
    for key, rec in doc.get("french", {}).items():
        if "sha256" not in rec:
            continue
        fid = key.split("/", 1)[1]
        vint = FIZ if key.startswith("french@") else None
        p = french_path(fid, vint)
        if not os.path.exists(p) or sha256_file(p) != rec["sha256"]:
            bad.append("%s: SHA 다름" % key)
        if vint is None and rec.get("crsp") != CRSP_WANT:
            bad.append("%s: CRSP %s" % (key, rec.get("crsp")))
    return not bad, bad


# ══════════════════════════════════════════════════════════════════════════
#  한 곳 입구 — 자료 층 전체(함수 안에서 v_ 모듈을 부른다 · 순환 import 없음)
# ══════════════════════════════════════════════════════════════════════════
class Layer:
    """자료 층 한 벌(입구) — 전략 입력을 결정 달마다 한 곳에서 준다. 🚨 수익 통계를 계산하지 않는다 — 입력만(굽기 v_run 의 몫).
      pit     v_pit.Universe(명단 · w_B · 시총 · 섹터 · 보유월 수익 · 모멘텀 · β̂ · 재무 · V08 NI)
      ear     v_ear.Earnings(V05 CAR · ATTN · V03 IRRX)      tenq  v_ear.TenQ(V05 CH 제외 · R2 규칙)      ins  v_ins.Insider(V04 OB/OS · R1 규칙)
      cond_L · cond_S  v_cond 조건 z(결정 달 × 가닥)      l_proxy  {전략: y = P − Mkt}(L 층 · 저장소에 쓰지 않는다)      strands  v_cond.web(전략)"""

    def __init__(self, U, E=None, T=None, I=None):
        import v_ear as VE
        import v_ins as VI
        self.pit = U
        self.ear = E or VE.Earnings(U)
        self.tenq = T or VE.TenQ()
        self.ins = I or VI.Insider()
        self._cL = self._cS = None

    @classmethod
    def real(cls, with_vd1=True):
        import v_pit as VP
        return cls(VP.Universe.real(with_vd1=with_vd1))

    def cond_L(self):
        import v_cond as VC
        if self._cL is None:
            self._cL = VC.conditions_L()
        return self._cL

    def cond_S(self):
        import v_cond as VC
        if self._cS is None:
            self._cS = VC.conditions_S()
        return self._cS

    def l_proxy(self):
        return {s: l_proxy(s) for s in L_PROXIES}

    def strands(self, sid):
        import v_cond as VC
        return VC.web(sid)

    def inputs(self, m):
        """결정 달 m 의 모든 전략 입력 — {"members", "w_B", "me", "signals", "irrx", "ear", "ch", "ins"} · 선정 · 가중 · θ 는 책(v_books)의 몫."""
        U = self.pit
        return {"members": U.members(m), "w_B": U.w_B(m), "me": U.me(m), "signals": U.signals(m), "irrx": self.ear.irrx_inputs(m),
                "ear": self.ear.ear_inputs(m), "ch": self.tenq.flags(U, m), "ins": self.ins.flags(U, m)}

    def poison_after(self, m, rng):
        """결정 달 m 뒤 자료 전부를 독 넣은 층(선견 점검용)."""
        import v_ear as VE
        E2 = self.ear.poison_after(m, rng)
        d = self.pit.dates[self.pit.me_idx[m]]
        return Layer(E2.U, E=E2, T=self.tenq.poison_after(d, rng), I=self.ins.poison_after(m, rng))


def layer(with_vd1=True):
    return Layer.real(with_vd1=with_vd1)


SMOKE_MONTHS = ("2010-06", "2014-06", "2016-09", "2020-03", "2023-06", "2026-08")      # 고정 표본(무작위 아님) — 모양만


def _flat_inputs(Lr, m):
    """선견 점검 비교용 — 결정 달 m 의 모든 입력을 {열쇠: 수 튜플}로 편다(값은 비교에만 쓰고 찍지 않는다)."""
    x = Lr.inputs(m)
    out = {}

    def num(v):
        return np.nan if v is None else (float(v) if isinstance(v, (int, float, np.floating)) else float(hash(str(v)) % 1000003))
    for t, (v, how) in x["me"].items():
        out["me:" + t] = (num(v), num(how))
    out["wB"] = tuple(sorted(x["w_B"].values()))
    for t, s in x["signals"].items():
        f = s.get("fund") or {}
        ni = s.get("ni_v08") or {}
        out["sig:" + t] = tuple(num(s.get(c)) for c in ("mom12_2", "beta_fp", "month_ret", "sector")) + \
            tuple(num(f.get(c)) for c in ("ni_ttm", "rev_ttm", "be", "asset", "op_num", "roa_ttm", "lev", "sig_roa")) + (num(ni.get("ni")),)
    for t, s in x["irrx"].items():
        out["irrx:" + t] = tuple(num(s.get(c)) for c in ("r_m", "sec_vw", "car3", "irrx"))
    for t, s in x["ear"].items():
        out["ear:" + t] = tuple(num(s.get(c)) for c in ("eligible", "car", "friday", "sameday_n", "attn_primary", "attn_twin"))
    for t, s in x["ch"].items():
        out["ch:" + t] = (num(s["ch"]), num(s["miss"]), num(s["n"]))
    for t, s in x["ins"].items():
        out["ins:" + t] = (num(s),)
    return out


def smoke_layer(n_lookahead=6):
    """자료 층 전체 눈가린 연기 — 실자료로 끝까지 돌리되 모양 · 참/거짓 · 개수만 돌려준다(값 없음). G-NoEG 실행 · 파일 감사를 함께."""
    import v_guard as VG
    VG.install_open_audit()
    out = {}
    box = {}

    def build():
        box["L"] = Layer.real()
        return box["L"].pit.months
    out["layer.real"] = blind_smoke(build)
    if "L" not in box:
        return out
    Lr = box["L"]
    for m in SMOKE_MONTHS:
        out["inputs " + m] = blind_smoke(lambda _m=m: {k: shape_of(v) for k, v in Lr.inputs(_m).items()})
        out["hold_ret " + m] = blind_smoke(lambda _m=m: Lr.pit.hold_ret(_m))
        out["coverage " + m] = blind_smoke(lambda _m=m: Lr.pit.coverage(_m))
    out["cond_L"] = blind_smoke(Lr.cond_L)
    out["cond_S"] = blind_smoke(Lr.cond_S)
    out["l_proxy"] = blind_smoke(lambda: pd.concat(list(Lr.l_proxy().values()), axis=1))
    out["strands V01..V08"] = blind_smoke(lambda: {s: Lr.strands(s) for s in ("V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08")})
    ms = [m for m in Lr.pit.months if "2010-06" <= m <= "2026-07"]
    la = {}

    def run_la():
        r = pit_lookahead(lambda X, m: _flat_inputs(X, m), Lr, ms, lambda X, m, rg: X.poison_after(m, rg), n=n_lookahead)
        la.update(r)
        return r["ok"]
    out["pit_lookahead(all inputs)"] = blind_smoke(run_la)
    out["pit_lookahead(all inputs)"]["detail"] = {"ok": la.get("ok"), "n": la.get("n"), "n_bad": la.get("n_bad"),
                                                  "bad_months": [b["m"] for b in la.get("bad", [])]}
    out["pit_lookahead(all inputs)"]["ok"] = bool(out["pit_lookahead(all inputs)"]["ok"] and la.get("ok"))
    # V08 NI(6월 재구성) · SW β̂ 쌍둥이 — 6월 달에서 따로(무작위 달 표본이 6월을 놓칠 수 있다)
    june = [m for m in ms if m[5:7] == "06"]
    la2 = {}

    def comp_june(X, m):
        U = X.pit
        spy_m = U.spy_month()
        out2 = {}
        for r in U.members(m):
            ni = U.ni_v08(r, m) or {}
            sw = U.beta_sw(r["k"], m, _spy_m=spy_m)
            out2[r["t"]] = (np.nan if ni.get("ni") is None else ni["ni"], np.nan if sw is None else sw)
        return out2

    def run_la2():
        r = pit_lookahead(comp_june, Lr, june, lambda X, m, rg: X.poison_after(m, rg), n=min(3, len(june)))
        la2.update(r)
        return r["ok"]
    out["pit_lookahead(V08 NI · SW β̂ · 6월)"] = blind_smoke(run_la2)
    out["pit_lookahead(V08 NI · SW β̂ · 6월)"]["detail"] = {"ok": la2.get("ok"), "n": la2.get("n"), "n_bad": la2.get("n_bad"),
                                                          "bad_months": [b["m"] for b in la2.get("bad", [])]}
    out["pit_lookahead(V08 NI · SW β̂ · 6월)"]["ok"] = bool(out["pit_lookahead(V08 NI · SW β̂ · 6월)"]["ok"] and la2.get("ok"))
    out["G-NoEG runtime"] = {"ok": VG.runtime_check()["ok"], "sec": 0, "shape": VG.runtime_check(), "err": None}
    out["G-NoEG open audit"] = {"ok": VG.open_audit_check()["ok"], "sec": 0, "shape": VG.open_audit_check(), "err": None}
    out["G-NoEG static"] = {"ok": VG.noeg_static()["ok"], "sec": 0, "shape": {k: VG.noeg_static()[k] for k in ("n_reached", "hits")}, "err": None}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기 시험 — 표준출력 버림 · 모양만(색인 범위 · 개수 · 참/거짓) · 산출 파일은 열지 않고 지운다
# ══════════════════════════════════════════════════════════════════════════
def shape_of(x):
    """값을 싣지 않는 모양 — 종류 · 크기 · 색인 처음/끝 · 결측 아닌 칸 수(값 · 통계 없음)."""
    if isinstance(x, pd.DataFrame):
        return {"type": "DataFrame", "shape": list(x.shape), "first": str(x.index.min()) if len(x) else None,
                "last": str(x.index.max()) if len(x) else None, "nonnull": int(x.notna().sum().sum())}
    if isinstance(x, pd.Series):
        return {"type": "Series", "len": int(len(x)), "first": str(x.index.min()) if len(x) else None,
                "last": str(x.index.max()) if len(x) else None, "nonnull": int(x.notna().sum())}
    if isinstance(x, dict):
        return {"type": "dict", "len": len(x), "keys_head": [str(k) for k in list(x)[:3]]}
    if isinstance(x, (list, tuple)):
        return {"type": type(x).__name__, "len": len(x)}
    if isinstance(x, (bool, np.bool_)):
        return {"type": "bool", "value": bool(x)}
    return {"type": type(x).__name__}


def blind_smoke(fn, *a, **k):
    """fn 을 돌리되 표준출력 · 표준오류를 버리고 {ok, sec, shape, err} 만 돌려준다. 산출 파일은 fn 이 만든 임시 폴더째 지운다."""
    import contextlib
    t0 = time.time()
    td = tempfile.mkdtemp(prefix="vb_smoke_", dir=cache_guard())
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            with np.errstate(all="ignore"):
                res = fn(*a, **k)
        out = {"ok": True, "sec": round(time.time() - t0, 1), "shape": shape_of(res), "err": None}
    except Exception as e:
        out = {"ok": False, "sec": round(time.time() - t0, 1), "shape": None, "err": "%s: %s" % (type(e).__name__, str(e)[:200])}
    finally:
        shutil.rmtree(td, ignore_errors=True)                     # 열지 않고 지운다
        del sink
    return out


def smoke():
    """실자료 연기 시험(모양만) — French 절 · L 대리 · 선견 틀(French 조건은 v_cond.smoke) · 자료 목록 무결성."""
    tests = {
        "french 13 파일 판 표식": (lambda: {fid: load_french(fid)["crsp"] == CRSP_WANT for fid, _, _ in V_FRENCH}, ()),
        "french 금지 절(투자) 건너뜀": (lambda: {fid: len(load_french(fid)["forbidden"]) for fid in ("me_beta", "me_op")}, ()),
        "l_proxy 다섯 + 쌍둥이": (lambda: pd.concat([l_proxy(s) for s in L_PROXIES] + [l_proxy("V01", "T-MOM-10"), l_proxy("V02", "T-LBS-LO20")], axis=1), ()),
        "lab SPY · rf": (lambda: (lab_spy_daily(), lab_rf_monthly()), ()),
        "assert_no_derivatives": (assert_no_derivatives, ()),
    }
    out = {nm: blind_smoke(fn, *a) for nm, (fn, a) in tests.items()}
    # 목표 y 의 결정 달 판(늦춤 2 · 명세 Y_LAG) 선견 점검 — 대리 다섯 + 쌍둥이 둘
    la = {}

    def run():
        for s in L_PROXIES:
            for w in ["main"] + list(L_PROXIES[s]["twins"]):
                y = l_proxy(s, w)
                r = lookahead_check(lambda y: lagged(contiguous(y), 2).rolling(60, min_periods=36).std(), {"y": (y, "french:lag2")}, n=LOOKAHEAD_N)
                la["%s:%s" % (s, w)] = {"ok": r["ok"], "n": r["n"], "n_bad": r["n_bad"]}
        return all(v["ok"] for v in la.values())
    out["lookahead l_proxy(늦춤 2)"] = blind_smoke(run)
    out["lookahead l_proxy(늦춤 2)"]["shape"] = la
    return out


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험
# ══════════════════════════════════════════════════════════════════════════
def _zip_text(name, txt):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, txt.encode("latin-1"))
    return b.getvalue()


def _st_french():
    hdr = ",SMALL LoBETA,ME5 BETA1\n"
    txt = ("This file was created using the 202608 CRSP database.\n\n\n"
           "  Average Value Weighted Returns -- Monthly\n" + hdr + "196307,   1.00,   2.00\n196308,  -99.99,  -1.00\n\n"
           "  Number of Firms in Portfolios\n" + hdr + "196307,    10,    25\n196308,    30,    19\n\n"
           "  Average Market Cap\n" + hdr + "196307,   5.0,  100.0\n196308,   5.5,  110.0\n\n"
           "  For portfolios formed in June of year t\n  Value Weight Average of BE/ME Calculated for June of t to June of t+1 as: \n"
           "  Sum[ME(Mth) * BE(Fiscal Year t-1) / ME(Dec t-1)] / Sum[ME(Mth)]\n  Where Mth is a month from June of t to June of t+1\n"
           "  and BE(Fiscal Year t-1) is adjusted for net stock issuance to Dec t-1\n" + hdr + "196307,   1.10,   0.50\n196308,   1.20,   0.55\n\n"
           "  For portfolios formed in June of year t\n  Value Weight Average of investment (rate of growth of assets) Calculated as: \n"
           "  Sum[ME(Mth) * Log(ASSET(t-1) / ASSET(t-2) / Sum[ME(Mth)] \n  Where Mth is a month from June of t to June of t+1\n" + hdr +
           "196307,   0.10,   0.20\n\nCopyright 2026 Eugene F. Fama and Kenneth R. French\n")
    f = parse_french_blob(_zip_text("25_Portfolios_ME_BETA_5x5.csv", txt))
    B = f["blocks"]
    assert f["crsp"] == "202608" and set(B) == {"vw_m", "nfirms", "avgsize", "vwbeme_m"}, sorted(B)
    assert len(f["forbidden"]) == 1 and "investment" in f["forbidden"][0]
    assert np.isnan(B["vw_m"].iloc[1, 0]) and B["vwbeme_m"].loc[pd.Period("1963-08", "M"), "ME5 BETA1"] == 0.55
    ff = ("This file was created using the 202608 CRSP database.\n\n,Mkt-RF,SMB,HML,RF\n192607,   2.89,  -2.42,  -2.75,   0.22\n"
          "192608,   2.64,  -1.44,   4.13,   0.25\n\n Annual Factors: January-December \n,Mkt-RF,SMB,HML,RF\n1927,  29.47,  -2.04,  -3.49,   3.12\n")
    g = parse_french_blob(_zip_text("F-F_Research_Data_Factors.csv", ff))
    assert set(g["blocks"]) == {"m", "a"} and g["blocks"]["a"].index[0] == 1927
    beme = (",Lo 30,Hi 30\n")
    tb = ("This file was created using the 202608 CRSP database.\n\n  Value Weight Returns -- Monthly\n" + beme + "192607,  1.0,  2.0\n\n"
          "  Sum of BE / Sum of ME\n" + beme + "1926,   0.5,   1.5\n\n  Value Weight Average of BE / ME\n" + beme + "1926,   0.4,   1.6\n")
    h = parse_french_blob(_zip_text("Portfolios_Formed_on_BE-ME.csv", tb))
    assert set(h["blocks"]) == {"vw_m", "sum_ratio", "vwavg_a"}, sorted(h["blocks"])
    ni = ("This file was created using the 202608 CRSP database.\n\n  Value-Weighted Average of NI\n,< 0,Hi 20\n1963,  -0.1,  0.3\n")
    q = parse_french_blob(_zip_text("Portfolios_Formed_on_NI.csv", ni))
    assert q["blocks"] == {} and len(q["forbidden"]) == 1
    return "French 여러 줄 제목 · 월별 BE/ME 절 · 투자 · NI 절 금지 · 결측 부호 · FF3"


def _st_avail():
    s = pd.Series(np.arange(24.0), index=pd.period_range("2000-01", periods=24, freq="M"))
    assert str(asof(s, "french:mkt", "2000-12").index.max()) == "2000-12"
    assert str(asof(s, "french:mkt", "2000-12", mode="S").index.max()) == "2000-10"
    assert str(asof(s, "french:lag2", "2000-12").index.max()) == "2000-10"
    an = pd.Series([1.0, 2.0, 3.0], index=pd.Index([1998, 1999, 2000]))
    assert asof(an, "french:june", "2000-07").index.max() == 1999 and asof(an, "french:june", "2000-08").index.max() == 2000
    dd = pd.Series(1.0, index=pd.date_range("2000-01-01", "2000-03-31", freq="D"))
    assert asof(dd, "lab:spy_d", "2000-02", mode="S").index.max() == pd.Timestamp("2000-02-29")
    for bad, exc in (("fred:USREC", PermissionError), ("eg:score", PermissionError), ("fund:cfo", PermissionError),
                     ("fund:investment", PermissionError), ("fred:BAA", KeyError)):
        try:
            lag_rule(bad)
            raise AssertionError("%s 가 통과했다" % bad)
        except exc:
            pass
    try:
        lag_rule("lab:spy", "L")
        raise AssertionError("lab:spy 가 L 층에서 통과했다")
    except KeyError:
        pass
    return "늦춤 표(L · S) · 월/일/연(6월 행) 자르기 · 금지(경기후퇴 · Eg · cfo · 투자) · 미선언 거부"


def _st_lookahead():
    rng = np.random.default_rng(7)
    idx = pd.period_range("1960-01", "2005-12", freq="M")
    r = pd.Series(rng.normal(0.005, 0.045, len(idx)), index=idx)

    def clean(mkt):
        return mkt.rolling(12).sum() - mkt.expanding(36).mean()

    ok = lookahead_check(clean, {"mkt": (r, "french:mkt")}, n=60)
    assert ok["ok"] and ok["n"] == 60, ok
    leaks = (lambda mkt: mkt.shift(-1), lambda mkt: mkt.rolling(12).sum() - mkt.median(),
             lambda mkt: pd.Series(np.roll(mkt.to_numpy(), -1), index=mkt.index))
    for fn in leaks:
        assert not lookahead_check(fn, {"mkt": (r, "french:mkt")}, n=40)["ok"]
    lag_ok = lookahead_check(lambda y: lagged(contiguous(y), 2).rolling(12).mean(), {"y": (r, "french:lag2")}, n=40)
    assert lag_ok["ok"], lag_ok
    lag_bad = lookahead_check(lambda y: lagged(contiguous(y), 1).rolling(12).mean(), {"y": (r, "french:lag2")}, n=40)
    assert not lag_bad["ok"]
    try:
        require_no_lookahead(lag_bad, "합성")
        raise AssertionError("멈추지 않았다")
    except SystemExit:
        pass
    # PIT 틀 — 결정일 뒤 가격을 쓰는 신호를 잡는다
    days = pd.bdate_range("2015-01-01", "2016-12-31")
    dates = [d.strftime("%Y-%m-%d") for d in days]
    me = month_ends(dates)
    px = {"A": np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))), "B": np.exp(np.cumsum(rng.normal(0, 0.01, len(dates))))}
    W = {"dates": dates, "me": me, "PX": px}

    def comp_ok(Wx, m):
        i = Wx["me"][m]
        return {k: float(p[i] / p[max(0, i - 21)] - 1) for k, p in Wx["PX"].items()}

    def comp_bad(Wx, m):
        i = min(Wx["me"][m] + 3, len(Wx["dates"]) - 1)
        return {k: float(p[i]) for k, p in Wx["PX"].items()}

    def pois(Wx, m, rg):
        i = Wx["me"][m]
        P2 = {k: np.r_[p[:i + 1], p[i + 1:] * rg.uniform(0.3, 3.0, len(p) - i - 1)] for k, p in Wx["PX"].items()}
        return dict(Wx, PX=P2)
    ms = sorted(me)[1:-1]
    assert pit_lookahead(comp_ok, W, ms, pois, n=10)["ok"]
    assert not pit_lookahead(comp_bad, W, ms, pois, n=10)["ok"]
    return "선견 틀: 깨끗 통과 · 미래 shift · 전 표본 적률 · 위치 색인 · 늦춤 위반 잡음 · 실패 시 멈춤 · PIT 틀(결정일 뒤 가격)"


def _st_proxy():
    idx = pd.period_range("1963-07", periods=6, freq="M")
    leg = pd.Series([0.01, 0.02, np.nan, 0.03, 0.0, 0.01], index=idx)
    nf = pd.Series([25, 19, 30, 30, 30, 30], index=idx)
    r = leg.where(nf >= MIN_FIRMS)
    assert np.isnan(r.iloc[1]) and np.isnan(r.iloc[2]) and r.iloc[3] == 0.03
    assert set(L_PROXIES) == {"V01", "V02", "V03", "V06", "V07"}
    for sid, sp in L_PROXIES.items():
        assert sp["main"][0] in FRENCH_FILES
    return "L 대리 표(V01 · V02 · V03 · V06 · V07 · 기업 수 < 20 = NaN) · V04 · V05 · V08 대리 없음"


def _st_registry():
    assert assert_no_derivatives()
    try:
        assert_no_derivatives({"x": {"key": "cboe/VIX", "fname": "VIX_History.csv", "url": "", "use": ""}})
        raise AssertionError("VIX 가 통과했다")
    except SystemExit:
        pass
    assert assert_no_eg_files(LAB_FILES)
    try:
        assert_no_eg_files(["data/_eg_q5_scores.json"])
        raise AssertionError("EG 파일이 통과했다")
    except SystemExit:
        pass
    try:
        _no_value_series({"a": {"b": [1, 2, 3, 4, 5]}})
        raise AssertionError("값 계열이 통과했다")
    except SystemExit:
        pass
    _no_value_series({"a": [1, 2, 3, 4], "b": {"c": "x"}})
    global CACHE
    old = CACHE
    try:
        CACHE = os.path.join(ROOT, "data", "_x_cache")
        try:
            cache_guard()
            raise AssertionError("저장소 안 캐시가 통과했다")
        except SystemExit:
            pass
    finally:
        CACHE = old
    assert shape_of(pd.Series([1.0, np.nan], index=[0, 1]))["nonnull"] == 1
    bs = blind_smoke(lambda: print("값") or pd.Series([1.0]))
    assert bs["ok"] and bs["shape"]["len"] == 1 and "값" not in json.dumps(bs, ensure_ascii=False)
    return "자료 목록(선물 · 옵션 · VIX 없음) · EG 파일 거부 · 공개 명세 값 계열 거부 · 저장소 안 캐시 거부 · 눈가린 연기(출력 버림)"


def _st_static():
    import ast
    bad = []
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("v_") and fn.endswith(".py")):
            continue
        src = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
        for nd in ast.walk(ast.parse(src)):
            if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "open":
                if any(kw.arg == "encoding" for kw in nd.keywords):
                    continue
                mode = nd.args[1].value if len(nd.args) > 1 and isinstance(nd.args[1], ast.Constant) else ""
                if "b" not in str(mode):
                    bad.append("%s:%d" % (fn, nd.lineno))
    assert not bad, "open() encoding 없음: %s" % bad
    return "v_*.py 의 open() encoding(텍스트 모드) 정적 점검"


def selftest():
    res, ok = [], True
    for fn in (_st_french, _st_avail, _st_lookahead, _st_proxy, _st_registry, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1200:]))
    for st, nm, msg in res:
        print("  %s %-16s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_data selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


DATA_LAYER = ("v_data", "v_cond", "v_fund", "v_px_split", "v_pit", "v_ins", "v_ear", "v_guard")
ENGINE = ("v_core", "v_cards", "v_alloc", "v_tests", "v_cmp", "v_run")  # 엔진 단계(v_cmp 는 별도 프로세스 — 자식 프로세스라 경계와 맞는다) · v_run = 러너


def selftest_all():
    """자료 층 모듈 selftest 를 각각 자식 프로세스로(합성 자료만 · 망 · 실자료 없음) — 끝에 G-NoEG 정적 점검."""
    import subprocess
    rows, ok = [], True
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for m in DATA_LAYER + tuple(x for x in ENGINE if os.path.exists(os.path.join(HERE, x + ".py"))):
        p = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, m + ".py"), "--selftest"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=1800)
        last = [ln for ln in (p.stdout or "").splitlines() if "selftest" in ln]
        rows.append((m, p.returncode, last[-1].strip() if last else (p.stderr or "")[-300:]))
        ok = ok and p.returncode == 0
    import v_guard as VG
    g = VG.noeg_static()
    for m, rc, msg in rows:
        print("  %s %-12s %s" % ("✓" if rc == 0 else "✗", m, msg))
    print("  %s G-NoEG 정적 전이 — 닿은 로컬 모듈 %d · 금지 적중 %d · 별도 프로세스 위반 %d" % ("✓" if g["ok"] else "✗", g["n_reached"], len(g["hits"]),
                                                                          len(g["separate_violations"])))
    return 0 if (ok and g["ok"]) else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--selftest-all" in argv:
        return selftest_all()
    if "--pin" in argv:
        for k, v in pin_french(fetch="--no-fetch" not in argv).items():
            print("  %-34s %s" % (k, v))
    if "--manifest" in argv:
        extra = {}
        try:
            import v_px_split as VX
            extra["vd1"] = VX.vd1_manifest()
        except Exception as e:
            extra["vd1"] = {"state": "없음 · %s" % type(e).__name__}
        try:
            import v_fund as VF
            extra["companyfacts_pin"] = VF.raw_pin_manifest()
        except Exception as e:
            extra["companyfacts_pin"] = {"state": "없음 · %s" % type(e).__name__}
        p = os.path.join(DATA, "_vb_lit_open.json")
        if os.path.exists(p):
            extra["lit_open"] = {"file": "data/_vb_lit_open.json", "sha256": sha256_file(p)}
        # 캐시 표지(v_run — 등록한 캐시 뿌리에서만 굽는다 · 표지 파일 자체는 저장소에 없다) · ^GSPC 핀(L 사건 지그재그) · 넓힌 원장(원 캐시 핀에서 지은 파생)
        cid = os.path.join(cache_guard(), "meta", "cache_id.txt")
        if os.path.exists(cid):
            extra["cache_identity"] = {"file": "<캐시>/meta/cache_id.txt", "sha256": sha256_file(cid),
                                       "rule": "v_run.frozen_check — 캐시 표지 SHA 가 이 값이어야 굽는다(새 캐시로 돌려 다시 굽는 길을 막는다)"}
        gp, gm = os.path.join(cache_guard(), "raw", "yf", "_GSPC.csv"), os.path.join(cache_guard(), "meta", "yf___GSPC.json")
        if os.path.exists(gp):
            meta = read_json(gm) if os.path.exists(gm) else {}
            extra["gspc_pin"] = {"file": "<캐시>/raw/yf/_GSPC.csv", "sha256": sha256_file(gp), "origin": meta.get("origin"),
                                 "meta_sha_same": meta.get("sha256") == sha256_file(gp), "use": "L 층 사건(급락 다리 · 반등 지그재그 · v_tests.events_L)"}
        wl = os.path.join(cache_guard(), "derived", "wide_ledger.json.gz")
        if os.path.exists(wl):
            extra["wide_ledger"] = {"file": "<캐시>/derived/wide_ledger.json.gz", "sha256": sha256_file(wl),
                                    "rule": "v_fund.build_wide 가 원 companyfacts 핀 사본에서 지은 파생(최초 제출 규칙) — 굽기는 같은 파일로"}
        if "--with-anchors" in argv:
            try:
                import v_px_split as VX
                a = VX.anchors()
                extra["market_cap_anchor"] = {
                    "rule": "명세 data_plan.market_cap_rule.anchor_check — 각 |ME/알려진 값 − 1| ≤ 0.10 · 평균 절대오차 ≤ 0.05(자료 타당성 · 수익 아님)",
                    "gate_ok": a["gate_ok"], "mae": a["mae"], "sec_cover_reference_ok": a["sec_ref_ok"], "sec_cover_reference_mae": a["sec_ref_mae"],
                    "rows": [{k: r.get(k) for k in ("t", "m", "known_T", "spec_T", "repaired", "calc_T", "err", "how", "kind", "sec_ref_T", "sec_ref_asof",
                                                    "err_vs_sec")} for r in a["rows"]],
                    "table": a.get("table"), "repairs": a.get("repairs"),
                    "note": ("알려진 값 = V 소유 앵커 표(v_px_split.anchor_table — shares_split.ANCHOR 사본 · 출처 표기 없음 · AUDIT-2026-09-20-SHARES2 §4 — 에서 "
                             "JNJ · GE 2017-10 두 칸만 SEC 10-Q 표지 발행주식수 × NYSE 월말 원 종가로 고쳤다 · repairs 에 출처 · 검토 고침). SEC 참고 = 원 companyfacts "
                             "핀 사본의 표지 발행주식(dei:EntityCommonStockSharesOutstanding · 그달 말에 가장 가까운 기준일) × 그달 말 원 가격(V-D1) — 관문 밖 대조용.")}
            except Exception as e:
                extra["market_cap_anchor"] = {"state": "계산 못 함 · %s" % type(e).__name__}
        build_manifest(extra=extra)
        print("→ %s" % os.path.relpath(MANIFEST, ROOT))
    if "--check" in argv:
        ok, bad = check_pins()
        print("고정본 점검: %s" % ("통과" if ok else "실패 %d" % len(bad)))
        for b in bad:
            print("  " + b)
        if not ok:
            return 1
    if "--smoke" in argv:
        for k, v in smoke().items():
            print("  %s %-34s %6ss %s" % ("✓" if v["ok"] else "✗", k, v["sec"], json.dumps(v["shape"], ensure_ascii=False) if v["ok"] else v["err"]))
    if "--smoke-layer" in argv:
        n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 6
        res = smoke_layer(n_lookahead=n)
        for k, v in res.items():
            sh = json.dumps(v.get("shape"), ensure_ascii=False, default=str)
            print("  %s %-30s %6ss %s" % ("✓" if v["ok"] else "✗", k, v["sec"], (sh[:300] if v["ok"] else v["err"])))
            if "detail" in v:
                print("      선견: %s" % json.dumps(v["detail"], ensure_ascii=False))
        print("연기 %d/%d 참" % (sum(1 for v in res.values() if v["ok"]), len(res)))
    if len(argv) <= 1:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
