# -*- coding: utf-8 -*-
"""build/pit_px_db2.py — 편출 종목 가격을 사내 DB(public.index_constituents)로 **복구**한다(§F · 배치 R).

  사내 DB 캐시  →  $TEMP/rbatch/pxrec[/nullmeta|/merge]/stage_pit_px.json · stage_px_raw.json · splits.json · report.json
  --merge       →  위 스테이징을 **지금의** data/pit_px.json 위에 병합 + data/_px_raw.json(시총용 원 종가) — 두 파일만 쓴다

🚨 병합은 **다시 돌려 재현한다**(손으로 고치지 않는다). CI 봇이 data/pit_px.json 을 매일(pit_px_refresh · 격자) · data/fx 를
   매주 옮기므로 커밋하는 쪽은 **당겨 온 판 위에서** 이 차례로 다시 만든다(--merge 가 먼저 · --merge-stage 가 뒤):
     1. git checkout -- data/pit_px.json data/_px_raw.json && git pull
     2. python build/pit_px_db2.py --merge              → data/pit_px.json + data/_px_raw.json(사내 DB 캐시 · 빈 날만)
     3. python build/pit_px_db2.py --merge-stage 파일 --src-tags "kaggle:*,yf_successor:*,zenodo:*" --write
                                                        → data/pit_px.json 만(공개 스테이징 · 빈 날만 · 스테이징은 같은 격자에서
                                                          뽑은 판이어야 한다 — 새로 더할 스테이징이 없으면 건너뛴다)
     4. python build/r_stagem.py --ytrunc-scan          → 새 계열 끝에 y 판정 줄이 있나(data/_r_ytrunc.json)
   2026-09-26 — --merge 는 스테이징 병합본 위에서도 돈다(origin 의 pit_px.json 이 이미 스테이징 병합본인 판 · P1 재굽기):
   관문을 모두 통과한 stage_merges 파일이 넣은 날(stage_src 구간 · DB 날 아님)이 낀 인접 변동은 그 병합의 G1 이 확인했다
   (stage_confirmed · 이번 실행에 DB 로 새로 메운 날이 끼면 종전대로 DB 종가 열 증거를 묻는다) · 스테이징이 계열을 이어 붙여
   더는 멈춤이 아닌 DB 멈춤 줄은 남긴다. 그래서 같은 입력이면 같은 바이트가 나오고, 이미 병합된 판(스테이징 병합본 포함) 위에서
   또 돌려도 바뀌지 않는다(메울 빈 곳이 없으면 값은 그대로 · closed · src · basis · stage_* 는 이어받는다 · 스크립트가 바뀌었으면
   db_merge.script_sha256 · _px_raw.json script_sha256 만 바뀐다). 합성 세계 자체 시험: --selftest.

## 왜 pit_px_db.py 를 고치지 않고 새로 두나 (38172fe6d 의 교훈)

  pit_px_db.py 는 DB local_price 를 «원종가» 로 보고 배당조정 계열에 이어 붙였다가 되돌렸다(가짜 계단 · CELG 분할 −49.9%).
  2026-09-25 실측으로 local_price 는 **한 가지 기준이 아니다** —
   ① 2014-06~2014-12 행: 원종가(분할 날 가격이 1/k 로 떨어지고 index_shares 가 k 배).
   ② 2015-01-02 이후 NDX 행 가운데 DB 를 채울 때 아직 상장돼 있던 종목: 블룸버그 기본 조정가(분할 + 분사 등 비정상 분배 조정 ·
      정규 배당은 조정 안 함). 그래서 q = index_market_cap ÷ (local_price × index_shares) 가 조정 전 구간에서 k 다
      (CMCSA 2015-01-02~2017-02-17 q = 2.000 · TSLA 2020-08-28 q = 15 → 08-31 3 · NFLX 2015-07-14 q = 70 → 07-15 10).
      편출 이름(DB 를 채울 때 이미 없던 것)은 q = 1 — 원종가다.
   ③ SPX 는 2025-04-16 부터만 가격이 있다(그 전 2020-09~2025-04 행은 가격·주식수·시총이 모두 NULL). 그 뒤는 원종가.
   ④ 기업 행위 날 앞뒤로 local_price 가 다른 증권을 가리킨 날이 있다(FOXA 2019-03-12~18: 21CF 가 지수에 있는데
      local_price 는 폭스코프 발행일 거래가 · 시총 ÷ 주식수 는 21CF 종가).
  → index_market_cap ÷ index_shares 가 «그날 지수가 쓴 종가» 이다. 원종가 R 은 그것을 기준으로 세우고(build_R)
    local_price × (그 구간의 안정 q) 와 0.2% 안에서 맞아야 쓴다 — 안 맞는 날은 버린다(local_off).

## 분할 (2026-09-25 개정 — 검토 지적 반영)

  후보: R 의 인접일 비 ≈ 1/k(15% 안) · ±5행 안 index_shares 비 ≈ k(3% 안). k ∈ K_STD(2·3·4·5·7·8·10·15·20·25·50 · 1.5 · 1.25 와
  역수). 값 비로 가까운 k 가 둘 이상이면(큰 변동일: TSLA 2020-08-31 은 값 비로 4 가 5 보다 가깝다) 주식수 비가 맞는 k 를 고른다.
  채택은 셋이 다 맞을 때만:
   ① 시총 연속(12% 안) — 또는 주식수 비가 **정확히** k(0.2% 안: 큰 변동일의 진짜 분할 · TSLA 2020-08-31 +12.6%)
   ② **확인** — data/splits.json 에 같은 k 가 ±5일 안에 있거나, DB 종가 열(local_price)이 **그 조정 기준 안에서** 분할을 보인다:
      · 조정 기준(q ≠ 1): 앞뒤 안정 q 의 비가 k(1% 안) — 블룸버그가 그날 k 로 과거를 되맞췄다(NFLX 70 → 10 = 7)
      · 원종가 기준(q ≈ 1 양쪽): local_price 비 ≈ 1/k(15% 안) **이고** 주식수 비가 정확히 k(0.2% 안)
        (SIRI 2023-07-24: 주식수 1.26801배 · −15% 날 = NDX 가중치 조정 → 확인 없음 → 분할 아님)
  확인 없는 후보는 되맞추지 않고 near_miss 로 싣는다. 전체 DB 로 규칙을 재는 모드: --split-audit.

## 공개 규약 (사용자 2026-08-19)

  저장소에 실을 수 있는 것은 «그 종목이 지수에 있던 날의 종가» 뿐이다. 이름·섹터·비중·주식수·시총·ISIN 은 어떤 파일에도
  안 싣는다. 주식수·시총은 메모리와 저장소 밖 캐시($TEMP/rbatch/pxrec)에서만 분할 판별·원종가 복원에 쓴다.
  캐시(db_cache.pkl.gz)에는 가격·주식수·시총·통화·국가·날짜·티커만 담는다(이름·섹터·비중·ISIN 은 조회도 안 한다).
  접속 자격은 db_load._conn_params() 가 저장소 밖에서 읽는다 — 여기서는 찍지도 적지도 않는다.
  🚨 db_load 는 주 접속처가 안 닿으면 접속처 주소를 콘솔에 찍는다 — --fetch 의 콘솔 출력은 파일로 남기지 않는다.

## 무엇을 보태나

  (티커, 날짜) 가운데 ① 랩이 값이 없고(pit_panel._key 와 같은 차례: 날짜 인식 별칭 → 명단 티커 → 점 표기 → cik_spliced)
  ② 그 이름이 랩 PIT 멤버였고(index_history 월말 명단 · 비는 달 이월 · 멤버 달 + 다음 달 = 편출 달의 마지막 가격)
  ③ DB 에 그날 행이 있다(= 그날 지수에 있었다) — 셋이 모두 맞는 칸만. 있는 값은 절대 안 덮는다.
  · 목표 키 = 날짜 인식 별칭(build/pit_alias.py) 이 그날 가리키는 키 · 없으면 명단 티커(점 표기).
    FOXA/FOX 의 21CF 시절 → TFCFA/TFCF · Staples → SPLS@791519 · 옛 SanDisk → SNDK@1000180.
  · 오늘 유니버스 키(sd)는 load_world 가 pit_px 쪽 값을 읽지 않으므로 넣지 않는다(보고만).
  · 격리 이름(pit_quarantine.names())은 넣지 않는다.
  · 기존 키인데 DB 날과 겹침이 0 이고 값이 멀리 떨어져 있으면 **재사용 티커** 로 보고 멈춘다(SPLS 가 그랬다) —
    pit_alias 에 날짜 인식 키를 먼저 적는다.

## 기준(basis)

  · db_scaled — 랩 배당조정 계열과 겹치는 날이 20일 이상: 가장 가까운 겹침일의 비율(랩 ÷ DB 분할조정 원종가)을 곱한다.
  · db_pr     — 겹침이 없다(편출 이름 대부분): 분할만 되맞춘 **가격수익** 계열. 배당 누락은 선언된 편향이다.

## 관문 — 하나라도 어기면 아무것도 쓰지 않는다

  G1 인접 거래일(격자 5일 이내) 변동 > 12% 는 전부 싣고 **DB 종가 열(local_price)** 로 확인한다: 같은 두 날 local_price 의
     변동(그 구간의 안정 q · 되맞춘 분할 배수로 기준을 맞춘 것)이 ±3% 안이면 진짜. DB 시총 변동은 보조로만 싣는다
     (스테이징 가격이 시총 ÷ 주식수 라 시총 일치는 «그날 주식수가 안 바뀌었다» 만 보여 준다 — 순환이다).
     ⚠ build_R 가 이미 매일 값을 local_price × 안정 q 와 0.2% 안으로 맞춰 두므로, 이 관문이 실제로 막는 것은 «두 날 사이에
     되맞추지 않은 기준 계단(분할·분배 계수)» 이다. 값 자체의 정확성 근거로 인용하지 않는다.
  G2 티커 수가 줄지 않는다 · 기존 값은 한 칸도 안 바뀐다(선언된 절단 CUT_AFTER_DB 만 예외 · repairs 에 적는다).
  G3 격리 이름은 추가되지 않는다.
  G4 위생: PIT S&P 500 시총가중 월수익(pit_panel.month_rows) 대 S&P 500(PR) 상관 ≥ 0.98(달력연도 2016..2026 각각).
     스테이징 전에 이미 0.98 아래인 해는 «나빠지지 않음»(≥ 전 − 0.001)으로 판정한다(2017 SPX 0.96 — 편출 가격이 없어
     시총의 ~15% 가 빠진 탓 · 이 완화는 결과를 보고 넣었다: 사전등록에 이탈로 적는다 · 가격 품질 근거로 인용하지 않는다).
  G5 멤버 창: 보탠 값의 날짜는 index_members.load() 로 따로 잰 멤버 창 ± 5 거래일 안.
  G6 멈춤 분류: DB 로 메운 키의 계열이 보유월 끝 전에 멈추는 날은 전부 STOPS(공개 사실)로 규칙이 있어야 한다 —
     missing(계속 거래됨: 지수만 떠남 · 개명 · 재분류) · last_price(인수 · 파산 · 비공개화) · short_cut(DB 월말 행 없음).
  G7 재사용 가드: 위 «기존 키 · 겹침 0 · 멀리 떨어진 값» 이 없다.

  python build/pit_px_db2.py                 # 스테이징만(USD/US 행) · 캐시가 없으면 DB 에서 받는다
  python build/pit_px_db2.py --null-meta     # 스테이징만(crncy/country NULL 행도 · 결과는 pxrec/nullmeta/)
  python build/pit_px_db2.py --merge         # NULL 메타 판으로 스테이징 → 관문 → data/pit_px.json · data/_px_raw.json
  python build/pit_px_db2.py --split-audit   # 분할 규칙을 DB 전체로 재 data/splits.json 과 맞댄다(보고만)
  python build/pit_px_db2.py --fetch         # 캐시를 새로 받는다(DB 가 보이는 PC · 콘솔 출력을 파일로 남기지 말 것)
  python build/pit_px_db2.py --merge-stage 파일 [--src-tags 패턴,…] [--write]   # 공개 데이터셋 스테이징을 빈 날에만 병합
                                             # (기본 = 시험 병합: 보고와 병합본을 저장소 밖에만 쓴다 · --write 일 때만 data/pit_px.json)
  python build/pit_px_db2.py --selftest      # 합성 세계에서 --merge → --merge-stage --write → --merge(같은 바이트) · 대조 둘
                                             # (임시 폴더만 쓴다 · DB · 저장소 자료를 읽지 않는다)

🚨 수익 관계는 계산하지 않는다(사전등록 전 자료 작업). 위생 상관은 세계 전체 시총가중 수익과 지수의 상관뿐이다.
"""
from __future__ import annotations

import bisect
import datetime as _dt
import gzip
import hashlib
import io
import json
import math
import os
import pickle
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

from pit_px_db import sig          # noqa: E402  같은 반올림(유효 6자리)
import pit_quarantine as PQ        # noqa: E402
import pit_alias as PA             # noqa: E402  날짜 인식 별칭 · 명단 고치기(pit_panel 과 같은 표)

IDX = ("SPX Index", "NDX Index")
K_STD = (2.0, 3.0, 4.0, 5.0, 7.0, 8.0, 10.0, 15.0, 20.0, 25.0, 50.0, 1.5, 1.25)   # 25: BKNG 2026-04-06(분할 감사가 찾음)
K_ALL = tuple(sorted(set(K_STD) | {1.0 / k for k in K_STD}))
JUMP_MAX = 0.12            # G1 인접일 변동 문턱
JUMP_GAP = 5               # 격자 몇 거래일 안을 «인접» 으로 보나
MIN_OVL = 20               # 기준 맞춤에 필요한 겹침일
EVID_TOL = math.log(1.03)  # 진짜 변동 = DB 종가 열이 같은 크기(±3%)로 움직였다
EXACT_SR = 0.002           # «정확한» 주식수 비(로그 0.2%) — 진짜 분할은 2.00000 · 7.00000 · 5.00000 로 맞는다
WIN_TOL = 5                # G5 멤버 창 여유(거래일)
REUSE_GAP = 60             # G7 재사용 가드: 기존 키 값과 DB 채움 사이가 이만큼(거래일) 넘게 떨어지면 다른 증권으로 본다
SPX_PRICE_FROM = "2025-04-16"   # 실측: SPX 행에 가격이 서는 첫날
PX_RAW = os.path.join(DATA, "_px_raw.json")
PX_OUT = os.path.join(DATA, "pit_px.json")


def _outdir():
    base = os.environ.get("RBATCH_PXREC") or os.path.join(os.environ.get("TEMP") or tempfile.gettempdir(),
                                                           "rbatch", "pxrec")
    base = os.path.abspath(base)
    if os.path.commonpath([base.lower(), ROOT.lower()]) == ROOT.lower():
        raise SystemExit("🚨 출력 경로 %s 가 저장소 안이다 — 스테이징은 저장소 밖에만 쓴다" % base)
    return base


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _days(a, b):
    return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days


# ══ DB 캐시 ══════════════════════════════════════════════════════════════════════════════════
CACHE_COLS = ["index", "ticker_full", "ticker", "crncy", "country", "dt", "price", "shares", "mcap"]


def fetch_cache(path):
    """SPX·NDX 의 가격 있는 행만 받는다 — 이름·섹터·비중·ISIN 은 조회하지 않는다."""
    import db_load
    import psycopg2
    conn = psycopg2.connect(**db_load._conn_params())
    try:
        cur = conn.cursor()
        cur.execute("""select index, ticker, split_part(ticker,' ',1), crncy, country, dt,
                              local_price, index_shares, index_market_cap
                         from public.index_constituents
                        where index = any(%s) and local_price is not null
                        order by 3, 6, 1""", (list(IDX),))
        rows = cur.fetchall()
    finally:
        conn.close()
    out = [(ix, tf, t, cr, co, str(d)[:10], float(p), None if sh is None else float(sh),
            None if mc is None else float(mc)) for ix, tf, t, cr, co, d, p, sh, mc in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        pickle.dump({"cols": CACHE_COLS, "rows": out,
                     "fetched": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, fh)
    print("DB 캐시 %d행 → %s" % (len(out), path))


def load_cache(path, null_meta):
    C = pickle.load(gzip.open(path, "rb"))
    if C.get("cols") != CACHE_COLS:
        raise SystemExit("🚨 캐시 열이 다르다(%s) — --fetch 로 다시 받을 것" % C.get("cols"))
    by = defaultdict(lambda: defaultdict(list))      # db 티커 → 지수 → [(d, p, sh, mc, null_meta)]
    n_keep = n_drop = 0
    for ix, tf, t, cr, co, d, p, sh, mc in C["rows"]:
        ok = (cr == "USD" and co == "US") or (null_meta and cr is None and co is None)
        if not ok:
            n_drop += 1
            continue
        n_keep += 1
        by[t][ix[:3]].append((d, p, sh, mc, cr is None))
    for t in by:
        for ix in by[t]:
            by[t][ix].sort()
    return by, {"fetched": C.get("fetched"), "n_rows": len(C["rows"]), "n_keep": n_keep, "n_drop_filter": n_drop}


def load_splits():
    """data/splits.json co — {티커: [[날짜, k], …]}(분할 확인의 첫째 근거)."""
    return (json.load(io.open(os.path.join(DATA, "splits.json"), encoding="utf-8")) or {}).get("co") or {}


# ══ 랩 세계(가벼운 판 — FUND 없이) ═══════════════════════════════════════════════════════════
def load_lab():
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    D = len(dates)
    today = [s["t"] for s in S["stocks"]]
    PX = {}
    for t in today:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        PX[t] = np.array([np.nan if v is None else float(v) for v in d["pxd"]])
    rec = json.load(io.open(PX_OUT, encoding="utf-8"))
    if rec.get("dates") != dates:
        raise SystemExit("🚨 pit_px.json 격자(%d일)가 stocks.json pxd_dates(%d일)와 다르다 — 스테이징을 만들 기준이 없다. "
                         "두 격자가 같은 판(CI 가 둘 다 갱신한 뒤)에서 다시 돌릴 것" % (len(rec.get("dates") or []), D))
    Q = PQ.names()
    for t, o in rec["px"].items():
        if t in PX or t in Q:
            continue
        a = np.full(D, np.nan)
        i0 = int(o.get("i0") or 0)
        for j, v in enumerate(o.get("p") or []):
            if v is not None:
                a[i0 + j] = float(v)
        PX[t] = a
    PU = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    orig = {}
    lists = {"spx": {}, "ndx": {}}
    last = {"spx": [], "ndx": []}
    for m in sorted(H["months"]):
        row = H["months"][m] or {}
        for ix in ("spx", "ndx"):
            if row.get(ix):
                for x in row[ix]:
                    orig[x.replace(".", "-")] = x
                last[ix] = [x.replace(".", "-") for x in row[ix]]
            lists[ix][m] = list(last[ix])
    n_fix = PA.fix_lists(lists)                   # pit_panel.load_world 와 같은 명단(NXP → NXPI)
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    cik = H.get("cik") or {}
    return {"dates": dates, "D": D, "di": {d: i for i, d in enumerate(dates)}, "today": set(today), "PX": PX,
            "rec": rec, "Q": Q, "splice": PU.get("cik_spliced") or {}, "lists": lists, "orig": orig, "me": me,
            "months": sorted(H["months"]), "cik": cik, "n_list_fix": n_fix}


def lab_val(L, t, i, PX=None):
    """pit_panel._key 와 같은 차례(날짜 인식 별칭 → 명단 티커 → 점 표기 → cik_spliced '-'·'.') — (키, 값) 또는 (None, None).
    2026-09-26 — 별칭 창 안이면 별칭 키만 본다(계열이 아직 없어도 명단 티커 키로 떨어지지 않는다 · pit_panel._key 와 같다)."""
    PX = PX or L["PX"]
    a = PA.key_at(t, L["dates"][i])
    if a is not None:
        if a not in PX:
            return None, None
        v = PX[a][i]
        return (a, float(v)) if (v == v and v > 0) else (None, None)
    for c in (t, t.replace("-", "."), L["splice"].get(t), L["splice"].get(t.replace("-", "."))):
        if c and c in PX:
            v = PX[c][i]
            if v == v and v > 0:
                return c, float(v)
    return None, None


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def membership(L):
    """티커 → {멤버 달} · 지수별 · 창(격자 색인 집합 = 멤버 달 + 다음 달)."""
    mon = defaultdict(set)
    mon_ix = {"spx": defaultdict(set), "ndx": defaultdict(set)}
    for m in L["months"]:
        for ix in ("spx", "ndx"):
            for t in L["lists"][ix].get(m) or []:
                mon[t].add(m)
                mon_ix[ix][t].add(m)
    days_of = defaultdict(list)
    for i, d in enumerate(L["dates"]):
        days_of[d[:7]].append(i)
    win = {}
    for t, ms in mon.items():
        s = set()
        for m in ms:
            s.update(days_of.get(m, ()))
            s.update(days_of.get(mshift(m, 1), ()))
        win[t] = s
    return mon, mon_ix, win, days_of


# ══ 원종가 R · 분할 · 분할조정 S ════════════════════════════════════════════════════════════
def build_R(rows, sysd=frozenset()):
    """한 지수 계열 [(d, p, sh, mc, nul)] → R(그날 지수 종가) 목록과 줄마다 판정.

    q = mc / (p·sh). 0.2% 안에서 같은 q 가 3행 이상 이어지면 안정 구간. 짧은 구간은 앞뒤 안정 q 가 같으면 그 값.
    P = mc/sh(지수가 쓴 종가) · L = p × 안정 q. |P/L−1| ≤ 0.2% → P(agree) · 주식수 갱신 시점 어긋남 → L(sh_timing)
    · 시총이 전날 가격으로 멈춤 → L(mc_stale) · 그 지수의 거의 모든 종목이 같은 날 어긋남(sysd · 2026 의 시총 수집 날짜 문제)
    → L(sys_mc_off) · 그 밖 → 그날은 **쓰지 않는다**(local_off: 두 가격 필드가 설명 없이 갈린 날 · 실측 ANSS 2025-07-17
    local 374.30 그대로 · 시총 ÷ 주식수 400.11 = 인수 대가 — 종가라 부를 수 없어 뺀다 · FOXA 2019-03-12~18 도 여기).
    """
    n = len(rows)
    q = []
    for d, p, sh, mc, _ in rows:
        q.append(mc / (p * sh) if (p and sh and mc) else None)
    runs = []                                   # [기준 q, j0, j1]
    for j, x in enumerate(q):
        if runs and x is not None and runs[-1][0] is not None and abs(x / runs[-1][0] - 1) <= 0.002:
            runs[-1][2] = j
        elif runs and x is None and runs[-1][0] is None:
            runs[-1][2] = j
        else:
            runs.append([x, j, j])
    stable = [(r[0] is not None and (r[2] - r[1] + 1) >= 3) for r in runs]
    qs = [None] * n
    for a, r in enumerate(runs):
        if stable[a]:
            val = r[0]
        else:
            prev = next((runs[b][0] for b in range(a - 1, -1, -1) if stable[b]), None)
            nxt = next((runs[b][0] for b in range(a + 1, len(runs)) if stable[b]), None)
            if prev is not None and nxt is not None:
                val = prev if abs(prev / nxt - 1) <= 0.002 else None
            else:
                val = prev if prev is not None else nxt
        for j in range(r[1], r[2] + 1):
            qs[j] = val
    R, cls = [None] * n, [None] * n
    for j, (d, p, sh, mc, _) in enumerate(rows):
        P = (mc / sh) if (sh and mc) else None
        Lv = (p * qs[j]) if qs[j] else None
        if P is None:
            R[j], cls[j] = p, "no_sh"
        elif Lv is None:
            R[j], cls[j] = P, "amb"
        elif abs(P / Lv - 1) <= 0.002:
            R[j], cls[j] = P, "agree"
        else:
            ratio = P / Lv
            tim = False
            for jj in (j - 1, j + 1):
                if 0 <= jj < n and rows[jj][2] and sh:
                    if abs(math.log(ratio / (rows[jj][2] / sh))) < 0.003:
                        tim = True
            stale = False
            if j > 0 and qs[j - 1] and rows[j - 1][1]:
                if abs(math.log(P / (rows[j - 1][1] * qs[j - 1]))) < 0.002 and abs(math.log(ratio)) > 0.002:
                    stale = True
            if d in sysd:
                R[j], cls[j] = Lv, "sys_mc_off"
            elif tim:
                R[j], cls[j] = Lv, "sh_timing"
            elif stale:
                R[j], cls[j] = Lv, "mc_stale"
            else:
                R[j], cls[j] = None, "local_off"
    # 안정 구간 사이의 q 변화 = 블룸버그가 local_price 에 넣은 조정(분할 · 분사 · 특별배당). 2014-12-31→2015-01-02 는 판 교체라 뺀다.
    steps = []
    st = [r for a, r in enumerate(runs) if stable[a]]
    for a, b in zip(st, st[1:]):
        if abs(math.log(a[0] / b[0])) > 0.005:
            d_end, d_new = rows[a[2]][0], rows[b[1]][0]
            if d_end <= "2014-12-31" and d_new >= "2015-01-02":
                continue
            steps.append({"d": d_new, "d_prev": d_end, "factor": round(a[0] / b[0], 4)})
    return R, cls, qs, steps


def _q_near(qs, j, step, lim=10):
    """j 에서 step(−1 앞 · +1 뒤) 방향으로 가장 가까운 안정 q(lim 행 안)."""
    c = j
    for _ in range(lim + 1):
        if 0 <= c < len(qs) and qs[c]:
            return qs[c]
        c += step
    return None


def split_confirm(rows, qs, jp, j, k, known, sr):
    """분할 후보(jp → j, 배수 k) 확인 — 'splits_json' · 'close_adj_step' · 'close_raw' 또는 None.

    ① data/splits.json 에 같은 k(1% 안)가 ±5일 안에 있다.
    ② DB 종가 열(local_price)이 그 조정 기준 안에서 분할을 보인다 —
       조정 기준(앞 안정 q ≠ 1): 앞뒤 안정 q 의 비가 k(1% 안) = 블룸버그가 그날 과거를 k 로 되맞췄다.
       원종가 기준(앞뒤 q ≈ 1): local_price 비 ≈ 1/k(15% 안) 이고 주식수 비가 정확히 k(EXACT_SR 안).
    """
    d = rows[j][0]
    for kd, kk in known or []:
        try:
            if abs(_days(kd, d)) <= 5 and abs(math.log(float(kk) / k)) < 0.01:
                return "splits_json"
        except Exception:
            pass
    q0, q1 = _q_near(qs, jp, -1), _q_near(qs, j, +1)
    p0, p1 = rows[jp][1], rows[j][1]
    if q0 and q1 and abs(math.log(q0 / q1 / k)) < math.log(1.01):
        return "close_adj_step"
    if (q0 and q1 and p0 and p1 and abs(math.log(q0)) < 0.005 and abs(math.log(q1)) < 0.005
            and abs(math.log(p1 / p0 * k)) < math.log(1.15) and sr is not None and abs(math.log(sr / k)) < EXACT_SR):
        return "close_raw"
    return None


def detect_splits(rows, R, gi, qs, known=()):
    """R 위에서 분할 찾기. rows 는 한 지수 계열. gi[j] = 격자 색인(격자 밖 날은 미리 뺀다). known = splits.json 줄."""
    ev, near, gapsus = [], [], []
    n = len(rows)
    prev = None
    for j in range(n):
        if R[j] is None:
            continue
        if prev is None or not R[prev]:
            prev = j
            continue
        jp, prev = prev, j
        pr = R[j] / R[jp]
        kb = min(K_ALL, key=lambda k: abs(math.log(pr * k)))
        e, e0 = abs(math.log(pr * kb)), abs(math.log(pr))
        gap = gi[j] - gi[jp]
        # 값 비로 15% 안인 k 후보들(가까운 차례) — 주식수 증거가 서는 첫 k 를 쓴다
        ks = [k for k in sorted(K_ALL, key=lambda k: abs(math.log(pr * k)))
              if abs(math.log(pr * k)) < math.log(1.15) and e0 - abs(math.log(pr * k)) > math.log(1.10)]
        sh0, sh1 = rows[jp][2], rows[j][2]
        if gap > JUMP_GAP:
            if sh0 and sh1:
                sr = sh1 / sh0
                ks = min(K_ALL, key=lambda k: abs(math.log(sr / k)))
                if abs(math.log(sr / ks)) < math.log(1.03) and abs(math.log(pr * ks)) < math.log(1.5):
                    gapsus.append({"d0": rows[jp][0], "d1": rows[j][0], "k": ks, "pr": round(pr, 4),
                                   "_sr": round(sr, 4)})
            continue
        if not ks:
            continue
        cs = []
        for k_ in ks:
            cs = [c for c in range(max(1, j - 5), min(n, j + 6))
                  if rows[c][2] and rows[c - 1][2] and abs(math.log(rows[c][2] / rows[c - 1][2] / k_)) < math.log(1.03)]
            if cs:
                kb = k_
                break
        rec = {"d": rows[j][0], "d0": rows[jp][0], "k": kb, "pr": round(pr, 4)}
        if cs:
            c = min(cs, key=lambda c: abs(c - j))
            lo, hi = min(jp, c - 1), max(j, c)
            mc0, mc1 = rows[lo][3], rows[hi][3]
            mcr = (mc1 / mc0) if (mc0 and mc1) else None
            sr = rows[c][2] / rows[c - 1][2]
            exact = abs(math.log(sr / kb)) < EXACT_SR
            cont = mcr is not None and abs(math.log(mcr)) < math.log(1.12)
            conf = split_confirm(rows, qs, jp, j, kb, known, sr)
            rec.update({"_sr": round(sr, 5), "_sh_lag": c - j, "_mcr": None if mcr is None else round(mcr, 4),
                        "exact_share_ratio": exact, "confirm": conf})
            if (cont or exact) and conf:
                if not cont:
                    rec["large_move_day"] = True       # 시총은 끊겼지만 주식수 비가 정확히 k 이고 확인이 있다(TSLA 2020-08-31)
                ev.append(rec)
                continue
            rec["why"] = ("확인 없음(splits.json · 종가 열)" if (cont or exact) else "시총 불연속 · 주식수 비 부정확")
        else:
            rec["why"] = "주식수 증거 없음(±5행)"
        near.append(rec)
    return ev, near, gapsus


def merge_events(evs_by_ix, di):
    """지수별 분할 → 하나로(같은 k · 격자 2일 안)."""
    allev = []
    for ix, evs in evs_by_ix.items():
        for e in evs:
            allev.append((di[e["d"]], e["k"], ix, e))
    allev.sort(key=lambda x: (x[0], x[1], x[2]))
    out = []
    for g, k, ix, e in allev:
        if out and abs(out[-1]["gi"] - g) <= 2 and abs(math.log(out[-1]["k"] / k)) < 0.01:
            out[-1]["ix"].append(ix)
            out[-1]["ev"].append(e)
            continue
        out.append({"gi": g, "d": e["d"], "k": k, "ix": [ix], "ev": [e]})
    return out


def split_audit(by_db, di, SPL, out):
    """분할 규칙을 DB 전체(두 지수 · 필터 통과 행)로 재 data/splits.json 과 맞댄다 — 보고만(저장소 밖)."""
    found, nears = [], []
    span, daysof = {}, defaultdict(set)
    for t, d_ in sorted(by_db.items()):
        for ix, rows in sorted(d_.items()):
            rows = [r for r in rows if r[0] in di]
            if len(rows) < 2:
                continue
            R, cls, qs, steps = build_R(rows)
            gi = [di[r[0]] for r in rows]
            known = SPL.get(t) or SPL.get(t.replace("/", ".")) or []
            ev, near, _g = detect_splits(rows, R, gi, qs, known)
            for e in ev:
                found.append(dict(e, t=t, ix=ix))
            for x in near:
                nears.append(dict(x, t=t, ix=ix))
            s0, s1 = span.get(t, (rows[0][0], rows[-1][0]))
            span[t] = (min(s0, rows[0][0]), max(s1, rows[-1][0]))
            daysof[t].update(gi)
    # 하나로(같은 티커 · 같은 k · 5일 안 · 두 지수)
    uniq = {}
    for e in sorted(found, key=lambda x: (x["t"], x["d"])):
        key = next((k for k in uniq if k[0] == e["t"] and abs(_days(k[1], e["d"])) <= 5
                    and abs(math.log(k[2] / e["k"])) < 0.01), None)
        if key:
            uniq[key]["ix"].add(e["ix"])
            continue
        uniq[(e["t"], e["d"], e["k"])] = {"t": e["t"], "d": e["d"], "k": e["k"], "ix": {e["ix"]},
                                          "confirm": e.get("confirm"), "large_move_day": bool(e.get("large_move_day"))}
    rows_found = sorted(uniq.values(), key=lambda x: (x["t"], x["d"]))
    matched, unknown = [], []
    for r in rows_found:
        kn = SPL.get(r["t"]) or []
        hit = any(abs(_days(kd, r["d"])) <= 5 and abs(math.log(float(kk) / r["k"])) < 0.01 for kd, kk in kn)
        (matched if hit else unknown).append(r)
    missed = []
    for t, kn in SPL.items():
        if t not in span:
            continue
        for kd, kk in kn:
            # 분할 배수(K_ALL 의 1% 안)만 — 분사 조정 계수(EBAY 2.376 · DD 2.39 · BDX 1.272 …)는 지수 주식수가 안 바뀌어 후보가 아니다
            if not any(abs(math.log(float(kk) / k)) < 0.01 for k in K_ALL):
                continue
            g = di.get(kd)
            if g is None:
                continue
            around = [gg for gg in daysof.get(t, ()) if g - 5 <= gg <= g + 5]
            if not (any(gg < g for gg in around) and any(gg >= g for gg in around)):
                continue                                   # 그 날 앞뒤로 DB 행이 없다(지수 밖 공백) — 이 규칙이 볼 수 없는 분할
            if not any(r["t"] == t and abs(_days(kd, r["d"])) <= 5 for r in rows_found):
                missed.append({"t": t, "d": kd, "k": kk,
                               "near": [{k: v for k, v in x.items() if not k.startswith("_")} for x in nears
                                        if x["t"] == t and abs(_days(kd, x["d"])) <= 5][:2]})
    rep = {"n_found": len(rows_found), "n_matched_splits_json": len(matched), "n_not_in_splits_json": len(unknown),
           "not_in_splits_json": [dict(r, ix=sorted(r["ix"])) for r in unknown],
           "n_missed_vs_splits_json": len(missed), "missed": missed,
           "matched": [dict(r, ix=sorted(r["ix"])) for r in matched],
           "note": "splits.json 가운데 분할 배수(K_ALL 1% 안)이고 그 날 앞뒤 5거래일 안에 DB 행이 있는 줄만 «놓침» 으로 센다 "
                   "(분사 조정 계수 · 지수 밖 공백의 분할은 이 규칙이 볼 수 없다). "
                   "not_in_splits_json 은 splits.json 에 없는 티커(편출 이름)이거나 거짓 분할 후보다 — 이름마다 본다."}
    p = os.path.join(out, "split_audit.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1, default=list))
    print("분할 감사: 찾음 %d · splits.json 과 일치 %d · splits.json 에 없음 %d · 놓침 %d → %s"
          % (len(rows_found), len(matched), len(unknown), len(missed), p))
    for r in unknown:
        print("   splits.json 에 없음: %s %s k=%s %s %s" % (r["t"], r["d"], r["k"], sorted(r["ix"]), r["confirm"]))
    for r in missed:
        print("   놓침: %s %s k=%s  근처 후보 %s" % (r["t"], r["d"], r["k"], r["near"]))
    return rep


# ══ 알려진 사실(내 지식 · 확인 못 한 것은 uncertain) — 남은 결손의 퇴출 사유 분류 ═════════════
# 분류: acquired · cap_drop · taken_private · bankrupt · other(개명·분사·재편·티커 재사용·목록 시차 등)
EXIT = {
    "HOLX": ("taken_private", "Blackstone·TPG 인수(2026)", True), "K": ("acquired", "Mars 인수(2025-12)", False),
    "IPG": ("acquired", "Omnicom 인수(2025-11)", False), "WBA": ("taken_private", "Sycamore 인수(2025-08)", False),
    "JNPR": ("acquired", "HPE 인수(2025-07)", False), "HES": ("acquired", "Chevron 인수(2025-07)", False),
    "DFS": ("acquired", "Capital One 인수(2025-05)", False), "MRO": ("acquired", "ConocoPhillips 인수(2024-11)", False),
    "WRK": ("acquired", "Smurfit Kappa 와 합병 → SW(2024-07)", False), "CMA": ("cap_drop", "S&P 500 편출(2024) · 뒤에 Fifth Third 인수", True),
    "ANSS": ("acquired", "Synopsys 인수(2025-07)", False), "PXD": ("acquired", "ExxonMobil 인수(2024-05)", False),
    "SEE": ("cap_drop", "S&P 500 → MidCap 400(2023-12)", True), "ATVI": ("acquired", "Microsoft 인수(2023-10)", False),
    "DISH": ("cap_drop", "S&P 500 편출(2023) · 뒤에 EchoStar 합병", True), "FBHS": ("other", "FBIN 으로 개명(2022-12 · MasterBrand 분사) 뒤 S&P 500 밖", True),
    "NLSN": ("taken_private", "Elliott·Brookfield 컨소시엄(2022-10)", False), "CTXS": ("taken_private", "Vista·Elliott(2022-09)", False),
    "CERN": ("acquired", "Oracle 인수(2022-06)", False), "PBCT": ("acquired", "M&T 인수(2022-04)", False),
    "DISCA": ("other", "WarnerMedia 와 합병 → WBD(2022-04)", False), "DISCK": ("other", "WarnerMedia 와 합병 → WBD(2022-04)", False),
    "GPS": ("cap_drop", "S&P 500 편출(2022)", True), "XLNX": ("acquired", "AMD 인수(2022-02)", False),
    "KSU": ("acquired", "Canadian Pacific 인수(2021-12)", False), "HBI": ("cap_drop", "S&P 500 편출(2021)", True),
    "DRE": ("acquired", "Prologis 인수(2022-10)", False), "COG": ("other", "Cimarex 합병 → Coterra CTRA 로 개명(2021-10)", False),
    "MXIM": ("acquired", "ADI 인수(2021-08)", False), "SIVB": ("bankrupt", "은행 파산(2023-03)", False),
    "ALXN": ("acquired", "AstraZeneca 인수(2021-07)", False), "FLIR": ("acquired", "Teledyne 인수(2021-05)", False),
    "INFO": ("acquired", "S&P Global 합병(2022-02)", False), "VAR": ("acquired", "Siemens Healthineers 인수(2021-04)", False),
    "ABMD": ("acquired", "J&J 인수(2022-12)", False), "CTRA": ("acquired", "Devon 인수(2026-05 · DB 주식수 점프로 추정)", True),
    "TIF": ("acquired", "LVMH 인수(2021-01)", False), "CXO": ("acquired", "ConocoPhillips 인수(2021-01)", False),
    "TWTR": ("taken_private", "머스크 인수(2022-10)", False), "FRC": ("bankrupt", "은행 파산(2023-05)", False),
    "MYL": ("other", "Upjohn 과 합병 → Viatris(2020-11)", False), "ETFC": ("acquired", "Morgan Stanley 인수(2020-10)", False),
    "NBL": ("acquired", "Chevron 인수(2020-10)", False), "CTLT": ("taken_private", "Novo Holdings 인수(2024-12)", False),
    "SGEN": ("acquired", "Pfizer 인수(2023-12)", False), "ADS": ("cap_drop", "S&P 500 편출(2020)", True),
    "JWN": ("cap_drop", "S&P 500 편출(2020)", True), "AGN": ("acquired", "AbbVie 인수(2020-05)", False),
    "RTN": ("acquired", "UTC 와 합병 → RTX(2020-04)", False), "XEC": ("cap_drop", "S&P 500 편출(2020) · 뒤에 Coterra 합병", True),
    "PARA": ("other", "격리(pit_quarantine) — 랩 계열을 못 믿어 지운 이름 · 2025-08 Skydance 합병", False),
    "STI": ("acquired", "BB&T 와 합병 → Truist(2019-12) · 티커 재사용", False), "CBS": ("other", "Viacom 과 합병 → VIAC(2019-12)", False),
    "VIAB": ("acquired", "CBS 에 합병(2019-12)", False), "CTRP": ("other", "Trip.com(TCOM)으로 개명(2019-11)", False),
    "CELG": ("acquired", "BMS 인수(2019-11)", False), "SPLK": ("acquired", "Cisco 인수(2024-03)", False),
    "TSS": ("acquired", "Global Payments 인수(2019-09)", False), "FL": ("cap_drop", "S&P 500 편출(2019)", True),
    "APC": ("acquired", "Occidental 인수(2019-08)", False), "HFC": ("cap_drop", "S&P 500 편출(2021)", True),
    "RHT": ("acquired", "IBM 인수(2019-07)", False), "LLL": ("acquired", "Harris 와 합병 → L3Harris(2019-06)", False),
    "FOXA": ("acquired", "21CF → Disney 인수(2019-03) · 티커는 Fox Corp 가 이어받음", False),
    "FOX": ("acquired", "21CF → Disney 인수(2019-03) · 티커는 Fox Corp 가 이어받음", False),
    "NFX": ("acquired", "Encana 인수(2019-02)", False), "CA": ("acquired", "Broadcom 인수(2018-11)", False),
    "CDAY": ("other", "Dayforce(DAY)로 개명(2024-02)", False), "COL": ("acquired", "UTC 인수(2018-11) · 격리 이름", False),
    "SRCL": ("cap_drop", "S&P 500 편출(2018)", True), "PX": ("acquired", "Linde 와 합병(2018-10)", False),
    "VIAC": ("other", "Paramount Global(PARA)로 개명(2022-02) · PARA 격리", False), "XL": ("acquired", "AXA 인수(2018-09)", False),
    "GGP": ("acquired", "Brookfield Property 인수(2018-08)", False), "DAY": ("taken_private", "Thoma Bravo 인수(2026-02)", True),
    "MON": ("acquired", "Bayer 인수(2018-06)", False), "WYN": ("other", "Wyndham Hotels 분사 · WYND 개명 뒤 편출(2018)", True),
    "QVCA": ("other", "Qurate(QRTEA)로 개명(2018)", False), "LVNTA": ("other", "GCI Liberty 로 분리(2018-03)", False),
    "PCLN": ("other", "Booking(BKNG)으로 개명(2018-02)", False), "SNI": ("acquired", "Discovery 인수(2018-03)", False),
    "CHK": ("cap_drop", "S&P 500 편출(2018) · 뒤에 파산(2020)", True), "PDCO": ("cap_drop", "S&P 500 편출(2018)", True),
    "BCR": ("acquired", "BD 인수(2017-12)", False), "ANSYS": ("other", "위키 NDX 명단의 ANSS 별표기", True),
    "WCG": ("acquired", "Centene 인수(2020-01)", False), "SBNY": ("bankrupt", "은행 파산(2023-03)", False),
    "LVLT": ("acquired", "CenturyLink 인수(2017-11)", False), "DOW": ("other", "DuPont 과 합병 → DWDP(2017-09) · 티커는 2019 Dow Inc 가 재사용", False),
    "SPLS": ("taken_private", "Sycamore 인수(2017-09)", False), "TSO": ("other", "Andeavor(ANDV)로 개명(2017-08)", False),
    "WFM": ("acquired", "Amazon 인수(2017-08)", False), "RAI": ("acquired", "BAT 인수(2017-07)", False),
    "BHI": ("acquired", "GE Oil & Gas 와 합병 → BHGE(2017-07)", False), "MNK": ("cap_drop", "S&P 500 편출(2017)", True),
    "YHOO": ("other", "본업 Verizon 매각 뒤 Altaba 로 개명(2017-06)", False), "MJN": ("acquired", "Reckitt 인수(2017-06)", False),
    "TGNA": ("cap_drop", "S&P 500 편출(2017)", True), "IR": ("other", "옛 Ingersoll-Rand plc — 티커 IR 을 2017 상장 Gardner Denver 가 쓰는 오늘 키와 충돌", True),
    "QRTEA": ("cap_drop", "NDX 편출(2018-12)", True), "SWN": ("cap_drop", "S&P 500 편출(2017)", True),
    "DNB": ("cap_drop", "S&P 500 편출(2017) · 뒤에 비공개화(2019)", True), "LLTC": ("acquired", "ADI 인수(2017-03)", False),
    "ENDP": ("cap_drop", "S&P 500 편출(2017)", True), "HAR": ("acquired", "Samsung 인수(2017-03)", False),
    "FTR": ("cap_drop", "S&P 500 편출(2017) · 뒤에 파산(2020)", True), "SE": ("acquired", "Enbridge 인수(2017-02) · 티커 재사용(Sea Ltd)", False),
    "STJ": ("acquired", "Abbott 인수(2017-01)", False), "KLA": ("other", "위키 NDX 명단의 KLAC 별표기", True),
    "LM": ("cap_drop", "S&P 500 편출(2016) · 뒤에 Franklin 인수(2020)", True), "UA-C": ("other", "랩 키 표기(UA-C ↔ cik_spliced 의 UA.C) 불일치", False),
    "LMCK": ("other", "Liberty Media 트래킹 주식 재편(2016-04) · 명단 시차", True), "LMCA": ("other", "Liberty Media 트래킹 주식 재편(2016-04) · 명단 시차", True),
    "Q": ("other", "Quintiles IMS → IQVIA 개명(2017-11) · 티커 Q 는 오늘 다른 증권", False),
    "EMC": ("acquired", "Dell 인수(2016-09)", False), "DO": ("cap_drop", "S&P 500 편출(2016)", True),
    "TYC": ("acquired", "Johnson Controls 와 합병(2016-09)", False), "AET": ("acquired", "CVS 인수(2018-11-28) · 월말 전 상장폐지", False),
    "ESRX": ("acquired", "Cigna 인수(2018-12-20) · 월말 전 상장폐지(NDX 2018-10~12 명단 이월)", False),
    "TFCF": ("acquired", "Disney 인수(2019-03-20) · 월말 전 상장폐지", False), "TFCFA": ("acquired", "Disney 인수(2019-03-20) · 월말 전 상장폐지", False),
    "AVB": ("other", "EQR 과 합병(2026-08) · 2026-07 월말 값 결손", True), "EA": ("taken_private", "PIF 컨소시엄 인수(2026) · 오늘 키(sd) 결손", True),
}


# 내 지식으로 아는 분배(분사·주식배당·재편) — DB 시총도 같이 움직여 «진짜 변동» 으로 통과하지만 가격수익 계열에는 분배 가치가 빠진다.
# 적용하지 않고(배당과 같은 선언 편향) 표시만 한다. 계수는 확인 못 해 싣지 않는다.
KNOWN_DIST = {
    ("CTXS", "2017-02-01"): "GetGo 분사 → LogMeIn 합병 주식 분배(2017-01-31 완료)",
    ("LMCA", "2014-07-24"): "LMCK(C주) 주식배당 1주당 2주(2014-07)",
    ("LMCA", "2014-11-05"): "Liberty Broadband 분사(2014-11)",
    ("LMCK", "2014-11-05"): "Liberty Broadband 분사(2014-11)",
    ("LMCA", "2016-04-18"): "트래킹 주식 재편(LSXM·BATR·FWON · 2016-04-15)",
    ("LMCK", "2016-04-18"): "트래킹 주식 재편(LSXM·BATR·FWON · 2016-04-15)",
}


# ══ 멈춤 분류(G6) — DB 로 메운 계열이 보유월 끝 전에 멈추는 날의 규칙(공개 사실 · 확인 못 한 것은 uncertain) ══════════
# y: missing(회사는 계속 거래됐다 — 지수만 떠남 · 개명 · 재분류 → 그 달 수익 결측) · last_price(인수 · 파산 · 비공개화로
#    거래가 끝났다 → 마지막 가격) · short_cut(아래 DB_GAP — DB 에 월말 행이 없다 → 1~3일 짧은 수익 · 선언된 절단).
# 멈춘 날 = 그 날 뒤로 그달(또는 그 날이 월말이면 다음 달) 끝까지 값이 없는 마지막 값의 날. pit_panel.y_stop 이 읽는다.
_M, _LP = "missing", "last_price"
STOPS = {
    "ALTR": {"2015-10-06": (_M, "NDX 편출(2015-10) · Intel 인수 완료(2015-12-28)까지 거래", False)},
    "ALXN": {"2021-07-20": (_LP, "AstraZeneca 인수 완료(2021-07-21)", False)},
    "ANSS": {"2025-07-17": (_LP, "Synopsys 인수 완료(2025-07-17) · 지수 행 값 = 인수 대가", False)},
    "ATVI": {"2023-07-14": (_M, "NDX 편출(2023-07) · S&P 500 에 남아 Microsoft 인수 완료(2023-10-13)까지 거래", False)},
    "AVB": {"2026-08-17": (_LP, "Equity Residential 과 합병 → Vivmark(VMRK) 2026-08-17 · DB 마지막 값 = 전환 대가(1주 → 2.793주)", False)},
    "BRCM": {"2015-11-10": (_M, "NDX 편출(2015-11) · Avago 인수 완료(2016-02-01)까지 거래", True)},
    "CA": {"2018-11-02": (_LP, "Broadcom 인수 완료(2018-11-05 · 마지막 거래일 11-02)", False)},
    "CELG": {"2019-11-20": (_LP, "Bristol-Myers Squibb 인수 완료(2019-11-20)", False)},
    "CERN": {"2021-12-17": (_M, "NDX 연말 편출(2021-12) · Oracle 인수 완료(2022-06-08)까지 거래", False)},
    "CMCSK": {"2015-11-30": (_M, "Comcast 클래스 A 특별주 → CMCSA 1:1 재분류(2015-12) — 같은 회사가 계속 거래", False)},
    "CTRA": {"2026-05-06": (_LP, "Devon Energy 와 합병(2026)으로 보임 — 날짜 · 형태 미확인", True)},
    "CTRP": {"2019-11-04": (_M, "Trip.com Group(TCOM)으로 티커 변경(2019-11) — 계속 거래(ADR · FPI)", False)},
    "CTRX": {"2015-07-23": (_LP, "UnitedHealth(OptumRx) 인수 완료(2015-07-23)", False)},
    "CTXS": {"2020-12-18": (_M, "NDX 연말 편출(2020-12) · S&P 500 에 남아 비공개화(2022-09-30)까지 거래", False)},
    "DAY": {"2026-02-06": (_LP, "Thoma Bravo 비공개화(2026-02 로 보임)", True)},
    "DFS": {"2025-05-16": (_LP, "Capital One 인수 완료(2025-05-18 · 마지막 거래일 05-16)", False)},
    "DISH": {"2018-07-20": (_M, "NDX 편출(2018-07) · S&P 500 에 남아 계속 거래", True)},
    "DTV": {"2015-07-24": (_LP, "AT&T 인수 완료(2015-07-24)", False)},
    "EA": {"2026-08-04": (_LP, "PIF · Silver Lake · Affinity 비공개화 — DB 지수 마지막 날(209.7) · 랩 계열은 뒤로 같은 값을 되풀이했다", True)},
    "ENDP": {"2016-07-15": (_M, "NDX 편출(2016-07) · 계속 거래", True)},
    # 🚨 2026-09-26 — 랩(야후) 키의 멈춤도 여기 적으면 closed 에 실린다(아래 G6 · LAB_STOP_SRC). DB 로 메운 키가 아니다.
    "EQR": {"2026-07-17": (_M, "Equity Residential — 랩 야후 계열이 07-17 뒤 끊겼다(08-11 한 값 · 08-17..21 같은 값) · 회사는 "
                               "계속 거래했고 2026-08-17 AvalonBay 합병과 함께 Vivmark Residential(VMRK)로 개명 — 2026-07 보유월은 "
                               "결측(data/_r_ytrunc.json EQR 2026-07-17 kept_trading 과 같은 판정)", False)},
    "ESRX": {"2018-12-21": (_LP, "Cigna 인수 완료(2018-12-20)", False)},
    # 2026-09-26 — 스테이징 키(yf_successor:FRCB). 은행 파산 = 상장폐지(data/_r_ytrunc.json note 의 단서 · 보유월 0% 는 선언된 편향).
    #   내보내기(스테이징 멈춤 판정)가 이 표를 먼저 읽는다 — 다음 스테이징 판부터 closed[FRC].stops 가 last_price 가 된다.
    "FRC": {"2023-04-28": (_LP, "First Republic Bank — 2023-05-01 캘리포니아 당국 폐쇄 · FDIC 관리(JPMorgan Chase 가 예금 · 자산 "
                                "대부분 인수) · NYSE 상장폐지(마지막 거래 04-28) · 보통주 가치 소멸 — 마지막 가격 규칙이 2023-05 "
                                "보유월을 0% 로 적는다(실제 약 −100% · 선언된 편향)", False)},
    "GMCR": {"2015-12-18": (_M, "NDX 연말 편출(2015-12) · JAB 비공개화(2016-03-03)까지 거래", False)},
    "HES": {"2025-07-22": (_LP, "Chevron 인수 완료(2025-07-18) · 지수 행은 07-22 까지(인수 대가)", False)},
    "HOLX": {"2018-12-21": (_M, "NDX 연말 편출(2018-12) · S&P 500 에 남아 계속 거래", False),
             "2026-04-08": (_LP, "Blackstone · TPG 비공개화(2026-04 로 보임)", True)},
    "IPG": {"2025-11-26": (_LP, "Omnicom 인수 완료(2025-11-26)", False)},
    "JNPR": {"2025-07-08": (_LP, "HPE 인수 완료(2025-07-02) · 지수 행은 07-08 까지(인수 대가)", False)},
    "K": {"2025-12-10": (_LP, "Mars 인수 완료(2025-12-11)", False)},
    "KRFT": {"2015-07-02": (_LP, "Heinz 와 합병 → KHC(2015-07-02) · 1주 → KHC 1주 + 16.50달러 — 가격수익 계열은 분배를 뺀다", False)},
    "LINTA": {"2014-10-06": (_M, "Liberty Interactive 재편 → QVC 그룹 트래킹 주식 QVCA(2014-10) — 계속 거래", False)},
    "LLTC": {"2016-10-18": (_M, "NDX 편출(2016-10) · Analog Devices 인수 완료(2017-03-10)까지 거래", True)},
    "LMCA": {"2016-06-17": (_M, "Liberty Media 트래킹 주식 재편(2016-04) 뒤 NDX 편출 — 계속 거래", True)},
    "LMCK": {"2016-06-17": (_M, "Liberty Media 트래킹 주식 재편(2016-04) 뒤 NDX 편출 — 계속 거래", True)},
    "LVNTA": {"2018-03-09": (_M, "GCI Liberty 분리(2018-03-09) — GLIBA 로 계속 거래", False)},
    "MXIM": {"2014-12-19": (_M, "NDX 연말 편출(2014-12) · 2015-12 재편입 — 계속 거래", False),
             "2021-08-25": (_LP, "Analog Devices 인수 완료(2021-08-26)", False)},
    "MYL": {"2019-12-20": (_M, "NDX 연말 편출(2019-12) · S&P 500 에 남아 Viatris(2020-11)까지 거래", False)},
    "QRTEA": {"2018-12-21": (_M, "NDX 연말 편출(2018-12) · 계속 거래", False)},
    "QVCA": {"2018-03-09": (_M, "Qurate Retail(QRTEA)로 개명(2018-03) — 계속 거래", False)},
    "SGEN": {"2023-12-14": (_LP, "Pfizer 인수 완료(2023-12-14)", False)},
    "SHPG": {"2019-01-08": (_LP, "Takeda 인수 완료(2019-01-08)", False)},
    "SIAL": {"2015-07-31": (_M, "NDX 편출(2015-07) · S&P 500 에 남아 Merck KGaA 인수 완료(2015-11-18)까지 거래", True)},
    "SNDK@1000180": {"2016-03-15": (_M, "NDX 편출(2016-03) · S&P 500 에 남아 WDC 인수 완료(2016-05-12)까지 거래", True)},
    "SPLK": {"2022-12-16": (_M, "NDX 연말 편출(2022-12) · 2023-12 재편입 — 계속 거래", False),
             "2024-03-15": (_LP, "Cisco 인수 완료(2024-03-18 · 마지막 거래일 03-15)", False)},
    "SPLS@791519": {"2015-12-18": (_M, "NDX 연말 편출(2015-12) · S&P 500 에 남아 비공개화(2017-09)까지 거래", False)},
    "SRCL": {"2016-12-16": (_M, "NDX 연말 편출(2016-12) · S&P 500 에 남아 계속 거래", False)},
    "TFCF": {"2019-03-19": (_LP, "Disney 인수 완료(2019-03-20) · Fox Corp 분배는 가격수익 계열에서 빠진다(선언)", False)},
    "TFCFA": {"2019-03-19": (_LP, "Disney 인수 완료(2019-03-20) · Fox Corp 분배는 가격수익 계열에서 빠진다(선언)", False)},
    "VIAB": {"2017-12-15": (_M, "NDX 연말 편출(2017-12) · S&P 500 에 남아 CBS 합병(2019-12)까지 거래", False)},
    "WBA": {"2024-07-19": (_M, "NDX 편출(2024-07) · S&P 500 에 남아 계속 거래", False),
            "2025-08-27": (_LP, "Sycamore 비공개화 완료(2025-08-28)", False)},
    "WFM": {"2016-12-16": (_M, "NDX 연말 편출(2016-12) · Amazon 인수 완료(2017-08-28)까지 거래", False)},
    "XLNX": {"2022-02-11": (_LP, "AMD 인수 완료(2022-02-14 · 마지막 거래일 02-11)", False)},
    "YHOO": {"2017-06-16": (_M, "본업 Verizon 매각(2017-06-13) 뒤 Altaba(AABA)로 개명 — 계속 거래", False)},
}
# STOPS 에 적힌 랩(야후) 키의 closed[키].src — DB 로 메운 키(index_constituents)와 가른다. closed 에 오르면
# pit_px_refresh 가 그 키를 더 묻지 않는다(EQR: 티커가 VMRK 로 바뀌어 야후 EQR 은 멈춘 값만 준다).
LAB_STOP_SRC = "yfinance"
# DB 에 월말 행이 없는 날 — 멈춘 날 → 다시 서는 날(그 사이가 월말). 지수에 계속 있었으니 결측이 아니라 짧은 수익(선언).
DB_GAP = {"2018-05-30": ("2018-06-01", "NDX 2018-05-31 행이 DB 에 없다 — 2018-05 보유월이 1거래일 짧다"),
          "2025-06-25": ("2025-07-01", "SPX 2025-06-26 · 27 · 30 행이 DB 에 없다 — 2025-06 보유월이 3거래일 짧다")}

# 선언된 절단 — DB 마지막 날 뒤의 랩 값이 멈춘 값(같은 수 반복)이라 자른다. repairs 에 적는다(G2 예외는 이것뿐).
CUT_AFTER_DB = {
    "AVB": "2026-08-18..20 의 184.06 은 DB 2026-08-14 종가를 되풀이한 값이다(08-17 합병 전환 대가 177.802 뒤) — "
           "2026-07 신호월 보유 수익이 그 값으로 끝나지 않게 DB 마지막 날(08-17) 뒤를 자른다.",
    "EA": "2026-08-05..10 은 08-04 의 209.7 을 되풀이한 값이다(상장폐지 뒤 멈춘 값) — DB 마지막 지수 날(08-04) 뒤를 자른다.",
}


def find_stops(arr, dates):
    """계열 arr(격자 길이 · NaN = 없음)의 멈춤 — [(멈춘 격자 색인, 다시 서는 격자 색인 또는 None)].

    멈춤 = 그 뒤로 그달 끝까지 값이 없는 마지막 값(그 날이 월말이 아닐 때) · 또는 그 날이 월말이고 다음 달 끝까지 값이 없을 때."""
    D = len(dates)
    mend = {}
    for i, d in enumerate(dates):
        mend[d[:7]] = i
    nz = np.where(arr == arr)[0]
    out = []
    for a, b in zip(nz, list(nz[1:]) + [None]):
        m = dates[a][:7]
        ie = mend[m]
        if a < ie:
            if b is None or b > ie:
                out.append((int(a), None if b is None else int(b)))
        else:
            ie2 = mend.get(mshift(m, 1))
            if ie2 is not None and (b is None or b > ie2):
                out.append((int(a), None if b is None else int(b)))
    return out


def classify_stop(k, d, d_next):
    s = (STOPS.get(k) or {}).get(d)
    if s:
        return {"d": d, "y": s[0], "why": s[1], "uncertain": bool(s[2]), "resume": d_next}
    g = DB_GAP.get(d)
    if g and d_next == g[0]:
        return {"d": d, "y": "short_cut", "why": g[1], "uncertain": False, "resume": d_next}
    return None


# ══ 본 작업 ══════════════════════════════════════════════════════════════════════════════════
def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    merge = "--merge" in argv
    audit = "--split-audit" in argv
    null_meta = ("--null-meta" in argv) or merge              # 병합은 NULL 메타 판(결정 2026-09-25)
    base = _outdir()
    out = os.path.join(base, "merge" if merge else ("nullmeta" if null_meta else ""))
    out = out.rstrip("\\/")
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(base, "db_cache.pkl.gz")
    if "--fetch" in argv or not os.path.exists(cache):
        fetch_cache(cache)
    by_db, cinfo = load_cache(cache, null_meta)
    print("DB 캐시 %s · %d행 중 필터 통과 %d (%s)" % (cinfo["fetched"], cinfo["n_rows"], cinfo["n_keep"],
                                              "USD/US + NULL 메타" if null_meta else "USD/US"))
    SPL = load_splits()

    L = load_lab()
    dates, D, di, PX = L["dates"], L["D"], L["di"], L["PX"]
    if audit:
        split_audit(by_db, di, SPL, out)
        return 0
    mon, mon_ix, win, days_of = membership(L)
    rec = L["rec"]
    prev_src = set((rec.get("src") or {}).keys())
    rep = {"variant": "null_meta" if null_meta else "usd_us", "mode": "merge" if merge else "stage", "cache": cinfo,
           "n_list_fix": L["n_list_fix"]}

    # 체계적 불일치 날 — 그 지수의 20% 이상 종목에서 시총 ÷ 주식수 가 local_price × 안정 q 와 갈린 날(실측 2026 NDX 24일 · SPX 3일)
    tot_d, off_d = Counter(), Counter()
    for t_, d_ in by_db.items():
        for ix, rows in d_.items():
            R_, cls_, _, _ = build_R(rows)
            for j, r in enumerate(rows):
                tot_d[(ix, r[0])] += 1
                if cls_[j] == "local_off":
                    off_d[(ix, r[0])] += 1
    sysd = defaultdict(set)
    for (ix, d_), n_ in off_d.items():
        if n_ >= 5 and n_ / tot_d[(ix, d_)] >= 0.20:
            sysd[ix].add(d_)
    rep["systematic_mcap_off_days"] = {ix: sorted(v) for ix, v in sysd.items()}

    # 같은 CIK 티커(별칭 판정용)
    cik = L["cik"]
    by_cik = defaultdict(set)
    for t in mon:
        c = cik.get(t) or cik.get(t.replace("-", "."))
        if c:
            by_cik[c].add(t)

    def alias_val(t, i):
        """그날 멤버가 아닌 같은 CIK 티커가 랩 값을 가지면 (티커, 값) — pit_alias 에 없는 별칭 후보(보고용)."""
        c = cik.get(t) or cik.get(t.replace("-", "."))
        if not c:
            return None
        ym = dates[i][:7]
        for u in sorted(by_cik[c]):
            if u == t:
                continue
            if any(t in (L["lists"][ix].get(ym) or []) and u in (L["lists"][ix].get(ym) or []) for ix in ("spx", "ndx")):
                continue
            k, v = lab_val(L, u, i)
            if k is not None:
                return (u, k)
        return None

    def tgt_of(t, i):
        """그날 값을 둘 가격 키 — 날짜 인식 별칭이 먼저 · 없으면 명단 티커(랩에 있는 표기)."""
        a = PA.key_at(t, dates[i])
        if a:
            return a
        k0 = next((c for c in (t, t.replace("-", ".")) if c in L["today"] or c in rec["px"]), None)
        return k0 or L["orig"].get(t, t)

    # ── 대상: 멤버 창 안에 DB 행이 있는 이름 ─────────────────────────────────────────────────
    stage_add, stage_src = defaultdict(dict), defaultdict(dict)   # 키 → {격자: 값} · {격자: 명단 티커}
    place = defaultdict(dict)                                      # 키 → {격자: 분할조정 원종가 S}(창 안 DB 날 전부)
    place_all = defaultdict(dict)                                  # 키 → {격자: S}(창 밖 포함 · 기준 맞춤용)
    ev_ctx = {}                                                    # (키, 격자) → {ix: (S, sh, mc, nul, p, 종가 기준 S)}
    basis_t = defaultdict(set)
    unplace, alias_rep, skipped = {}, defaultdict(Counter), {}
    split_log, split_local, near_log, gap_log = [], [], [], []
    rcls_tot = Counter()
    qsteps = defaultdict(dict)
    split_of = defaultdict(list)
    outside_db = Counter()
    conflicts_of, key_conf = Counter(), Counter()
    for t in sorted(mon):
        dbt = next((c for c in (t, t.replace("-", "."), t.replace("-", "/")) if c in by_db), None)
        if dbt is None:
            continue
        w = win[t]
        series, evs_by_ix, cls_cnt = {}, {}, Counter()
        known = SPL.get(t) or SPL.get(t.replace("-", ".")) or SPL.get(dbt) or []
        for ix, rows in by_db[dbt].items():
            rows = [r for r in rows if r[0] in di]          # 격자 밖 날(휴일 행 등) 제외
            if not rows:
                continue
            R, cls, qs, steps = build_R(rows, frozenset(sysd.get(ix, ())))
            cls_cnt.update(cls)
            qsteps[t][ix] = steps
            gi = [di[r[0]] for r in rows]
            ev, near, gapsus = detect_splits(rows, R, gi, qs, known)
            evs_by_ix[ix] = ev
            for x in near:
                near_log.append(dict(x, t=t, ix=ix))
            for x in gapsus:
                gap_log.append(dict(x, t=t, ix=ix))
            series[ix] = (rows, R, gi, cls, qs)
        rcls_tot.update(cls_cnt)
        events = merge_events(evs_by_ix, di)
        for e in events:
            split_log.append({"t": t, "db": dbt, "d": e["d"], "k": e["k"], "ix": sorted(set(e["ix"])),
                              "confirm": sorted({x.get("confirm") for x in e["ev"] if x.get("confirm")}),
                              "large_move_day": any(x.get("large_move_day") for x in e["ev"])})
            split_local.append({"t": t, "d": e["d"], "k": e["k"], "ev": e["ev"]})
        # S = R ÷ (그 뒤 분할 배수의 곱) · 종가 기준 S = local_price × 안정 q ÷ 같은 배수(G1 증거)
        S_by = {}
        for ix, (rows, R, gi, cls, qs) in series.items():
            for j, g in enumerate(gi):
                if R[j] is None:
                    continue
                f = 1.0
                for e in events:
                    if e["gi"] > g:
                        f *= e["k"]
                cS = (rows[j][1] * qs[j] / f) if qs[j] else None
                S_by.setdefault(g, {})[ix] = (R[j] / f, rows[j][2], rows[j][3], rows[j][4], rows[j][1], cS)
        S = {}
        for g, dd in S_by.items():
            if "NDX" in dd and "SPX" in dd:
                if abs(dd["NDX"][0] / dd["SPX"][0] - 1) > 0.005:
                    conflicts_of[t] += 1
                S[g] = dd["NDX"][0]
            else:
                S[g] = next(iter(dd.values()))[0]
        db_days = set(S)
        outside_db[t] = len([g for g in db_days if g not in w])
        # 목표 키별로 나눈다(FOXA: ~2019-03-12 → TFCFA · 그 뒤 → FOXA(오늘 키) …)
        for g in db_days:
            tg = tgt_of(t, g)
            place_all[tg].setdefault(g, S[g])
            if g in w:
                if g in place[tg] and abs(place[tg][g] / S[g] - 1) > 0.005:
                    key_conf[tg] += 1                      # 두 명단 티커가 같은 키 · 같은 날에 다른 값(없어야 한다)
                place[tg].setdefault(g, S[g])
                basis_t[tg].add(t)
                ev_ctx.setdefault((tg, g), S_by[g])
        for e in events:
            split_of[tgt_of(t, e["gi"])].append([e["d"], e["k"]])
        # 채울 날 = 창 안 · 랩 값 없음(pit_panel._key 차례) · DB 행 있음
        for i in sorted(w):
            if i not in db_days or lab_val(L, t, i)[0] is not None:
                continue
            a = alias_val(t, i)
            if a:
                alias_rep[t][a[0]] += 1
                continue
            tg = tgt_of(t, i)
            if tg in L["Q"] or t in L["Q"]:
                skipped.setdefault(t, {"why": "quarantine", "n_days": 0})["n_days"] += 1
                continue
            if tg in L["today"]:
                unplace.setdefault(t, {"key": tg, "why": "오늘 유니버스 키(sd) — load_world 가 pit_px 쪽 값을 읽지 않는다",
                                       "days": {}})["days"][i] = S[i]
                continue
            if i in stage_add[tg]:
                continue                                    # 같은 키 · 같은 날을 다른 명단 티커가 이미 채웠다
            stage_add[tg][i] = S[i]                         # 기준 맞춤 전 값(아래에서 db_scaled 면 배율을 곱한다)
            stage_src[tg][i] = t
    stage_add = {k: v for k, v in stage_add.items() if v}

    # ── 기준 맞춤(키별) · G7 재사용 가드 ─────────────────────────────────────────────────────
    basis, reuse_bad = {}, []
    prev_basis = rec.get("basis") or {}
    db_keys = sorted(set(stage_add) | (prev_src & set(place)))      # 이번에 채웠거나 이미 DB 로 채운 키
    for k in db_keys:
        vals0 = stage_add.get(k) or {}
        lab = PX.get(k)
        pb = prev_basis.get(k) or {}
        is_new = k not in rec["px"]
        new_key = bool(pb.get("new_key", is_new))
        # 겹침 = 랩(야후) 자신의 값이 선 DB 날 — 앞선 병합이 메운 날(filled_days)은 뺀다(다시 돌려도 같은 겹침)
        filled_prev = {di[d] for d in (pb.get("filled_days") or []) if d in di}
        ovl = []
        if lab is not None and not new_key:
            for g in sorted(place_all[k]):
                v = lab[g]
                if v == v and v > 0 and g not in vals0 and g not in filled_prev:
                    ovl.append((g, float(v) / place_all[k][g]))
        if vals0 and not is_new and k not in prev_src and not ovl:
            nz = np.where(lab == lab)[0] if lab is not None else []
            if len(nz):
                a0, a1, b0, b1 = int(nz[0]), int(nz[-1]), min(vals0), max(vals0)
                gap = max(0, b0 - a1, a0 - b1)              # 두 구간 사이 거리(겹치면 0)
                if gap > REUSE_GAP:
                    reuse_bad.append({"key": k, "lab_range": [dates[nz[0]], dates[nz[-1]]],
                                      "db_range": [dates[min(vals0)], dates[max(vals0)]], "gap_days": gap})
        mode = pb.get("basis") or ("db_scaled" if len(ovl) >= MIN_OVL else "db_pr")
        og = [o[0] for o in ovl]
        vals = {}
        for i, s in vals0.items():
            if mode == "db_scaled" and og:
                p = bisect.bisect_left(og, i)
                c2 = [x for x in (p - 1, p) if 0 <= x < len(og)]
                x = min(c2, key=lambda x: (abs(og[x] - i), og[x]))
                vals[i] = sig(s * ovl[x][1])
            else:
                vals[i] = sig(s)
        if vals0:
            stage_add[k] = vals
        b = dict(pb) if pb else {}
        if not new_key:
            fd = sorted({dates[g] for g in filled_prev} | {dates[g] for g in vals0})
            if fd:
                b["filled_days"] = fd               # 기존 키에서 DB 로 메운 날(겹침 계산에서 뺀다)
        b.update({"tickers": sorted(basis_t[k]), "basis": mode, "new_key": new_key,
                  "db_index": "+".join(sorted({ix for g in place[k] for ix in (ev_ctx.get((k, g)) or {})})),
                  "db_first": dates[min(place[k])], "db_last": dates[max(place[k])], "n_db_days": len(place[k]),
                  "splits": sorted({tuple(x) for x in split_of.get(k, [])}) and
                            [list(x) for x in sorted({tuple(x) for x in split_of.get(k, [])})]})
        if vals:
            b["n_added_last_merge"] = len(vals)
        if mode == "db_scaled" and ovl:
            rs = [o[1] for o in ovl]
            b["ratio_range"] = [round(min(rs), 4), round(max(rs), 4)]
            b["n_overlap"] = len(ovl)
        dist = []
        for t in basis_t[k]:
            for ix, steps in qsteps[t].items():
                for s_ in steps:
                    g_ = di.get(s_["d"])
                    if g_ is None or g_ not in place[k]:
                        continue
                    if any(abs(g_ - di[x[0]]) <= 2 for x in split_of.get(k, [])):
                        continue        # 조정 판의 분할 — 이미 되맞췄다
                    if not any(x["d"] == s_["d"] for x in dist):
                        dist.append({"d": s_["d"], "ix": ix})
        if dist:
            b["distributions_not_applied"] = sorted(dist, key=lambda x: x["d"])   # 날짜만(계수는 저장소에 안 싣는다)
        nconf = sum(conflicts_of.get(t, 0) for t in basis_t[k])
        if nconf:
            b["spx_ndx_conflict_days"] = nconf
        if key_conf.get(k):
            b["key_day_conflicts"] = key_conf[k]
        basis[k] = b

    # ── 스테이징 조립 · 선언된 절단 ───────────────────────────────────────────────────────────
    px0 = rec["px"]
    newpx = {k: {"i0": o["i0"], "p": list(o["p"])} for k, o in px0.items()}

    def arr_of(obj):
        a = np.full(D, np.nan)
        for j, v in enumerate(obj["p"]):
            if v is not None:
                a[obj["i0"] + j] = float(v)
        return a

    def pack(arr):
        idx = [i for i, x in enumerate(arr) if x is not None]
        lo, hi = idx[0], idx[-1]
        return {"i0": lo, "p": arr[lo:hi + 1]}

    for k, vals in stage_add.items():
        arr = [None] * D
        if k in newpx:
            o = newpx[k]
            for j, v in enumerate(o["p"]):
                arr[o["i0"] + j] = v
        for i, v in vals.items():
            if arr[i] is not None:
                raise SystemExit("🚨 내부 오류: %s %s 에 이미 값이 있다(덮지 않는다)" % (k, dates[i]))
            arr[i] = v
        newpx[k] = pack(arr)
    cuts = {}
    for k, why in CUT_AFTER_DB.items():
        if k not in newpx or not place.get(k):
            continue
        last_db = max(place[k])
        o = newpx[k]
        arr = [None] * D
        for j, v in enumerate(o["p"]):
            arr[o["i0"] + j] = v
        gone = [(dates[i], arr[i]) for i in range(last_db + 1, D) if arr[i] is not None]
        if gone:
            for i in range(last_db + 1, D):
                arr[i] = None
            newpx[k] = pack(arr)
            cuts[k] = {"after": dates[last_db], "n_cut": len(gone), "cut": [d for d, _ in gone],
                       "values": sorted({v for _, v in gone}), "why": why}

    # ── G1 인접일 12% — 증거는 DB 종가 열(local_price) ─────────────────────────────────────────
    #    스테이징 병합본 위에서 다시 돌 때(2026-09-26): 스테이징 병합(--merge-stage)이 넣은 날(stage_src 구간 · 관문을 모두
    #    통과한 stage_merges 파일 · DB 날이 아닌 날)이 낀 변동은 그 병합의 G1 이 같은 두 날로 이미 확인했다 → stage_confirmed.
    #    이번 실행에 DB 로 새로 메운 날이 한쪽이라도 끼면 스테이징이 본 적 없는 짝이다 — 종전대로 DB 종가 열 증거가 있어야 한다.
    stage_days, stage_file_of = stage_gated_days(rec, dates, place)
    moves, bad, junctions = [], [], []
    n_stage_ok = 0
    for k in db_keys:
        a = arr_of(newpx[k])
        dbd = set(place[k])
        fresh = set(stage_add.get(k) or {})
        sgd = stage_days.get(k) or {}
        nz = np.where(a == a)[0]
        # DB 에서 온 값의 날 — 새 키는 전부 · 기존 키는 이번에 메운 날 + 앞선 병합이 메운 날(filled_days)
        if basis[k].get("new_key"):
            addset = {int(x) for x in nz}
        else:
            addset = set(stage_add.get(k) or {}) | {di[d] for d in (basis[k].get("filled_days") or []) if d in di}
        for x, y in zip(nz, nz[1:]):
            x, y = int(x), int(y)
            if y - x > JUMP_GAP or (x not in addset and y not in addset):
                continue
            s = a[y] / a[x] - 1
            kind = "junction" if ((x in addset) != (y in addset)) else "db"
            if kind == "junction":
                junctions.append({"key": k, "d0": dates[x], "d1": dates[y], "move": round(float(s), 4),
                                  "lab_side": dates[x] if x not in addset else dates[y]})
            if abs(math.log(1 + s)) <= math.log(1 + JUMP_MAX):
                continue
            c0, c1 = ev_ctx.get((k, x)), ev_ctx.get((k, y))
            verdict, cm, mm, lm = "unexplained", None, None, None
            if c0 and c1:
                for ix in ("NDX", "SPX"):
                    if ix in c0 and ix in c1:
                        if c0[ix][5] and c1[ix][5]:
                            cm = c1[ix][5] / c0[ix][5] - 1
                        if c0[ix][4] and c1[ix][4]:
                            lm = c1[ix][4] / c0[ix][4] - 1
                        if c0[ix][2] and c1[ix][2]:
                            mm = c1[ix][2] / c0[ix][2] - 1
                        if cm is not None and abs(math.log((1 + s) / (1 + cm))) <= EVID_TOL:
                            verdict = "close_agrees"
                        break
            sfile = None
            if verdict != "close_agrees" and x not in fresh and y not in fresh and (x in sgd or y in sgd):
                verdict = "stage_confirmed"
                sfile = sgd.get(y) or sgd.get(x)
                n_stage_ok += 1
            rec_m = {"key": k, "d0": dates[x], "d1": dates[y], "move": round(float(s), 4), "kind": kind,
                     "verdict": verdict, "close_move": None if cm is None else round(cm, 4),
                     "local_price_move_raw": None if lm is None else round(lm, 4),
                     "mcap_agrees_secondary": None if mm is None else bool(abs(math.log((1 + s) / (1 + mm))) <= EVID_TOL)}
            if sfile:
                rec_m["stage_file"] = sfile
            tks = basis.get(k, {}).get("tickers") or []
            kd = next((KNOWN_DIST.get((t_, dates[y])) for t_ in tks if KNOWN_DIST.get((t_, dates[y]))), None)
            if kd:
                rec_m["known_distribution"] = kd
                basis[k].setdefault("known_distribution_moves", [])
                if not any(z["d"] == dates[y] for z in basis[k]["known_distribution_moves"]):
                    basis[k]["known_distribution_moves"].append({"d": dates[y], "move": round(float(s), 4), "what": kd})
            moves.append(rec_m)
            if verdict not in ("close_agrees", "stage_confirmed"):
                bad.append(rec_m)

    # ── G2 · G3 · G7 ──────────────────────────────────────────────────────────────────────────
    g2 = len(newpx) >= len(px0) and all(k in newpx for k in px0)
    changed = []
    for k, o in px0.items():
        a0, a1 = arr_of(o), arr_of(newpx[k])
        m0 = a0 == a0
        if k in cuts:
            keep = np.ones(D, bool)
            keep[di[cuts[k]["after"]] + 1:] = False
            m0 = m0 & keep
        if not np.array_equal(a0[m0], a1[m0]):
            changed.append(k)
    g2 = g2 and not changed
    g3 = not any(k in L["Q"] for k in stage_add) and not any(k in newpx for k in L["Q"])
    g7 = not reuse_bad

    # ── G5 멤버 창(index_members.load 로 따로) ───────────────────────────────────────────────
    import index_members as IM
    mem2, _car = IM.load()
    mon2 = defaultdict(set)
    for ym, ts in mem2.items():
        for x in ts:
            mon2[x].add(ym)
    ok_cache = {}
    g5_bad = []
    for k, vals in stage_add.items():
        for i in vals:
            t = stage_src[k][i]
            if t not in ok_cache:
                t_orig = L["orig"].get(t, t)
                ms = set(mon2.get(t_orig) or mon2.get(t) or set())
                for f in PA.LIST_FIX:          # 명단 고치기로 들어온 티커는 원 명단의 오타 티커 달도 멤버 달이다
                    if f["good"] == t:
                        ms |= {m for m in (mon2.get(f["bad"]) or set()) if f["frm"] <= m <= f["to"]}
                okd = set()
                for m in ms:
                    for mm in (m, mshift(m, 1)):
                        okd.update(days_of.get(mm, ()))
                ok_cache[t] = sorted(okd)
            okx = ok_cache[t]
            p = bisect.bisect_left(okx, i)
            dist = min([abs(okx[x] - i) for x in (p - 1, p) if 0 <= x < len(okx)] or [10 ** 9])
            if dist > WIN_TOL:
                g5_bad.append((k, t, dates[i]))
    g5 = not g5_bad

    # ── G6 멈춤 분류 · closed ────────────────────────────────────────────────────────────────
    prev_closed = rec.get("closed") or {}
    closed, unclassified, stop_rows = {}, [], []
    # 랩(야후) 키 가운데 STOPS 에 멈춤이 적힌 것(EQR) — 적힌 날만 싣는다(나머지 랩 쪽 멈춤은 종전 규칙 그대로)
    # 스테이징 키(closed src = stage · FRC)는 뺀다 — 그 멈춤은 --merge-stage 가 STOPS 를 먼저 보고 적는다(여기서 다시 지으면
    # src 가 바뀌고 스테이징 줄을 잃는다 · 재실행 같은 바이트).
    lab_stop_keys = sorted(k for k in STOPS if k not in set(db_keys) and k in newpx and k not in L["today"]
                           and k not in L["Q"] and (prev_closed.get(k) or {}).get("src") != "stage")
    for k in list(db_keys) + lab_stop_keys:
        a = arr_of(newpx[k])
        dbd = set(place.get(k) or {})
        nz = np.where(a == a)[0]
        last_i = int(nz[-1])
        st_ = []
        for L_, nxt in find_stops(a, dates):
            lab_side = L_ not in dbd and not (k in cuts and L_ == last_i)
            c = classify_stop(k, dates[L_], None if nxt is None else dates[nxt])
            if lab_side and not ((STOPS.get(k) or {}).get(dates[L_])):
                continue                                # 랩(야후) 쪽 멈춤 · 표에 없음 — 종전 규칙 그대로(분류하지 않는다)
            if c is None:
                unclassified.append({"key": k, "d": dates[L_], "resume": None if nxt is None else dates[nxt],
                                     "tickers": basis.get(k, {}).get("tickers")})
                continue
            st_.append(c)
            stop_rows.append(dict(c, key=k))
        pc = prev_closed.get(k) or {}
        # 스테이징 병합본 위에서 다시 돌 때: 앞선 --merge 가 적은 DB 쪽 멈춤 가운데 바로 다음 값이 관문을 통과한 스테이징 날이라
        # 더는 멈춤이 아닌 줄은 그대로 남긴다(스테이징이 계열을 이어 붙였을 뿐 — y_stop 은 실제로 멈춘 날만 묻는다 · 같은 바이트).
        sgd = stage_days.get(k) or {}
        if sgd and pc.get("stops"):
            have = {s["d"] for s in st_}
            for s in pc["stops"]:
                if s.get("by") == "stage" or s.get("d") in have or s.get("d") not in di:
                    continue
                j = di[s["d"]]
                nxt = next((int(x) for x in nz if x > j), None)
                if a[j] == a[j] and nxt is not None and nxt in sgd:
                    st_.append(dict(s))
                    stop_rows.append(dict(s, key=k, kept="stage_continues"))
            st_.sort(key=lambda s: s["d"])
        last_stop = next((s for s in reversed(st_) if s["resume"] is None), None)
        if k in lab_stop_keys:
            if not st_:
                continue                                # 적힌 날이 계열에 없다(값이 바뀌었다) — 싣지 않는다
            last_stop = last_stop or st_[-1]
        closed[k] = {"since": dates[last_i], "src": LAB_STOP_SRC if k in lab_stop_keys else "index_constituents",
                     "exit": (last_stop or {}).get("why") or pc.get("exit") or "",
                     "uncertain": bool((last_stop or {}).get("uncertain")),
                     "stops": st_}
    for k, c in prev_closed.items():
        closed.setdefault(k, c)                         # 이미 닫힌 키는 잃지 않는다(재실행)
    _keep_stage_stops(closed, prev_closed)          # 스테이징 병합(--merge-stage)이 적은 멈춤은 잃지 않는다
    g6 = not unclassified

    # ── 커버리지(월말 가격 · 개수 기준) ────────────────────────────────────────────────────────
    PXs = {t: a for t, a in PX.items() if t in L["today"]}
    for k, o in newpx.items():
        if k in L["today"] or k in L["Q"]:
            continue
        PXs[k] = arr_of(o)

    def priced(PXx, t, i):
        return lab_val(L, t, i, PXx)[0] is not None

    ym_all = [m for m in sorted(L["me"]) if "2014-06" <= m <= "2026-07"]
    new_by_y, new_by_ix, miss_by_y, miss_by_t = Counter(), Counter(), Counter(), Counter()
    cov_m, remain, newly = {}, [], []
    for ym in ym_all:
        i = L["me"][ym]
        sp = set(L["lists"]["spx"].get(ym) or [])
        nd = set(L["lists"]["ndx"].get(ym) or [])
        memb = sp | nd
        n_ok = 0
        for t in memb:
            b0 = priced(PX, t, i)
            b1 = priced(PXs, t, i)
            if b1:
                n_ok += 1
            if not b0 and b1:
                newly.append((t, ym))
                if "2016-08" <= ym <= "2026-07":
                    new_by_y[ym[:4]] += 1
                    new_by_ix[("NDX" if t in nd else "") + ("+" if (t in nd and t in sp) else "") + ("SPX" if t in sp else "")] += 1
            if not b1 and "2016-08" <= ym <= "2026-07":
                miss_by_y[ym[:4]] += 1
                miss_by_t[t] += 1
                remain.append((t, ym, t in sp, t in nd))
        cov_m[ym] = (n_ok, len(memb))
    win_m = [m for m in ym_all if "2016-08" <= m <= "2026-07"]
    t_pass = sum(1 for m in win_m if cov_m[m][0] / cov_m[m][1] >= 0.90)

    null_rows = defaultdict(set)
    if not null_meta:
        C = pickle.load(gzip.open(cache, "rb"))
        for ix, tf, t, cr, co, d, p, sh, mc in C["rows"]:
            if cr is None and co is None and d in di:
                null_rows[t].add(di[d])
        del C
    why_db, why_t, spx_only_pre = Counter(), defaultdict(Counter), Counter()
    for t, ym, isp, ind in remain:
        i = L["me"][ym]
        dbt = next((c for c in (t, t.replace("-", "."), t.replace("-", "/")) if c in by_db or c in null_rows), None)
        a = alias_val(t, i)
        if t in L["Q"]:
            w_ = "quarantine"
        elif a:
            w_ = "alias_recoverable(%s)" % a[0]
            alias_rep[t][a[0]] += 1
        elif t in unplace and i in unplace[t]["days"]:
            w_ = "today_key_unplaceable"
        elif dbt and i in null_rows.get(dbt, ()):
            w_ = "db_null_meta_filtered"
        elif isp and not ind and ym < SPX_PRICE_FROM[:7]:
            w_ = "spx_only_db_has_no_price(<2025-04)"
        elif dbt is None:
            w_ = "not_in_db"
        else:
            w_ = "no_db_row_at_month_end"
        if isp and not ind and ym <= "2020-08":
            spx_only_pre[ym] += 1
        why_db[w_] += 1
        why_t[t][w_] += 1

    # ── G4 위생(시총가중 PIT 멤버 대 지수 PR) ─────────────────────────────────────────────────
    import pit_panel as PP
    W = PP.load_world()
    IDXM = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))["idx_monthly"]
    sigm = [m for m in sorted(W["me"]) if "2015-12" <= m <= "2026-07"]

    def hyg(Wx, ix, lab):
        rows, cover = PP.month_rows(Wx, ix, sigm, "2026-08")
        bm = IDXM.get(lab) or {}
        by = defaultdict(list)
        for x in rows:
            if x["m"] in bm:
                by[x["m"][:4]].append((sum(x["wb"][t] * x["r"][t] for t in x["names"]) * 100, bm[x["m"]]))
        res = {}
        for y, pr in sorted(by.items()):
            if len(pr) >= 3:
                c = float(np.corrcoef([p for p, _ in pr], [b for _, b in pr])[0, 1])
                res[y] = {"n": len(pr), "corr": round(c, 4),
                          "gap_mean_pp": round(float(np.mean([p - b for p, b in pr])), 3)}
        return res, rows

    base_spx, _ = hyg(W, "spx", "S&P 500")
    base_ndx, _ = hyg(W, "ndx", "NASDAQ 100")
    PX_base, ST_base = W["PX"], W.get("stops")
    W["PX"] = dict(PXs)
    W["stops"] = {k: {s["d"]: s for s in (c.get("stops") or [])} for k, c in closed.items()}
    stg_spx, rows_spx = hyg(W, "spx", "S&P 500")
    stg_ndx, rows_ndx = hyg(W, "ndx", "NASDAQ 100")
    W["PX"], W["stops"] = PX_base, ST_base
    in_panel = {"spx": Counter(), "ndx": Counter()}
    for nm, rows_ in (("spx", rows_spx), ("ndx", rows_ndx)):
        for x in rows_:
            for t in x["names"]:
                if x["key"][t] in set(db_keys):
                    in_panel[nm][x["m"][:4]] += 1
    g4_detail, g4 = {}, True
    for y in [str(y) for y in range(2016, 2027)]:
        b_, s_ = base_spx.get(y, {}).get("corr"), stg_spx.get(y, {}).get("corr")
        if s_ is None:
            g4_detail[y] = "no_data"
            g4 = False
            continue
        if s_ >= 0.98:
            g4_detail[y] = "pass"
        elif b_ is not None and b_ < 0.98 and s_ >= b_ - 0.001:
            g4_detail[y] = "literal_fail_preexisting(base %.4f → stage %.4f)" % (b_, s_)
        else:
            g4_detail[y] = "FAIL(base %s → stage %.4f)" % (b_, s_)
            g4 = False

    # 메운 이름에 랩 주식수(fx · fx_pit)가 있나
    sh_av = {k: bool((W["FUND"].get(k) or {}).get("sh") or any((W["FUND"].get(t) or {}).get("sh")
                                                              for t in basis.get(k, {}).get("tickers") or []))
             for k in db_keys}

    # ── 보유월 결측 규칙이 닿는 신호월(보고 · 등록 문서용) ─────────────────────────────────────
    ycut = []
    for k in db_keys:
        a = arr_of(newpx[k])
        stp = {s["d"]: s for s in closed[k]["stops"]}
        for m in sorted(L["me"]):
            m1 = mshift(m, 1)
            if m1 not in L["me"]:
                continue
            i, i1 = L["me"][m], L["me"][m1]
            if not (a[i] == a[i]):
                continue
            seg = a[i + 1:i1 + 1]
            okx = np.where(seg == seg)[0]
            if len(okx) and okx[-1] == len(seg) - 1:
                continue
            Lx = (i + 1 + int(okx[-1])) if len(okx) else i
            s = stp.get(dates[Lx])
            ycut.append({"key": k, "signal_month": m, "stop": dates[Lx], "y": s["y"] if s else "last_price(규칙 없음)",
                         "in_window": "2016-08" <= m <= "2026-07",
                         "tickers": basis.get(k, {}).get("tickers")})

    gates = {"G1_moves_confirmed_by_db_close": not bad, "G2_no_decrease_no_overwrite": g2, "G3_no_quarantine": g3,
             "G4_hygiene_spx_ge_0.98_or_not_worse": g4, "G5_member_window": g5, "G6_stops_classified": g6,
             "G7_no_reused_ticker_mixing": g7}
    ok = all(gates.values())

    for s in split_log:
        kn = SPL.get(s["t"]) or SPL.get(s["t"].replace("-", "."))
        hit = None
        if kn:
            for d, kk in kn:
                if abs(_days(d, s["d"])) <= 5:
                    hit = [d, kk]
        s["splits_json"] = hit if hit else ("다른 날만 있음" if kn else "티커 없음")
        s["agree"] = bool(hit and abs(math.log(hit[1] / s["k"])) < 0.01)

    rep.update({
        "gates": gates, "ok": ok,
        "g1_rule": "G1 — 인접 거래일(격자 5일 안) 변동 > 12% 는 같은 두 날 DB 종가 열(local_price × 그 구간의 안정 q ÷ 되맞춘 분할 "
                   "배수)의 변동과 ±3% 안에서 맞아야 한다(주 증거). DB 시총 변동 일치는 보조로만 싣는다 — 스테이징 가격 자체가 "
                   "시총 ÷ 주식수 라 시총 일치는 «그날 주식수가 안 바뀌었다» 만 보여 준다. build_R 가 매일 값을 종가 열과 0.2% 안으로 "
                   "맞춰 두므로 이 관문이 실제로 막는 것은 두 날 사이의 되맞추지 않은 기준 계단이다. 스테이징 병합본 위에서는 "
                   "관문을 통과한 스테이징 병합(stage_merges)이 넣은 날(stage_src 구간 · DB 날 아님)이 낀 짝을 그 병합의 G1 이 "
                   "확인했다(stage_confirmed) — 이번 실행에 DB 로 새로 메운 날이 끼면 종전 규칙 그대로다.",
        "g1_stage_confirmed": n_stage_ok,
        "g1_stage_files": sorted(stage_file_of),
        "g4_note": "G4 는 세계 커버리지 점검이지 가격 품질 근거가 아니다. 2017 의 «나빠지지 않음» 완화는 결과를 본 뒤 넣었다 — "
                   "사전등록에 이탈로 적을 것(시총의 ~15% 가 빠져 대형주가 과대 가중된 탓 · CELG 2017-10 −30.8% 는 진짜).",
        "filled_keys": {k: b for k, b in sorted(basis.items())},
        "n_db_keys": len(db_keys), "n_filled_keys_this_run": len(stage_add),
        "n_added_points": sum(len(v) for v in stage_add.values()),
        "newly_priced_mm_by_year": dict(sorted(new_by_y.items())), "newly_priced_mm_by_index": dict(new_by_ix),
        "newly_priced_mm_2014_07_16": sum(1 for t, ym in newly if ym < "2016-08"),
        "newly_priced_mm_total_window": sum(new_by_y.values()),
        "remaining_mm_by_year": dict(sorted(miss_by_y.items())), "remaining_mm_total": sum(miss_by_y.values()),
        "remaining_by_name": {t: {"n": n, "why_db": dict(why_t[t]), "exit": list(EXIT.get(t, ("?", "", True)))}
                              for t, n in miss_by_t.most_common()},
        "remaining_why_db": dict(why_db),
        "spx_only_unpriced_2016_08_2020_08": dict(sorted(spx_only_pre.items())),
        "coverage_count_by_month": {m: [cov_m[m][0], cov_m[m][1], round(cov_m[m][0] / cov_m[m][1], 4)] for m in win_m},
        "months_count_cov_ge_0.90": t_pass,
        "filled_has_lab_shares": sh_av, "g4_detail": g4_detail,
        "splits": split_log, "splits_near_miss": [{k: v for k, v in x.items() if not k.startswith("_")} for x in near_log],
        "gap_split_suspects": [{k: v for k, v in x.items() if not k.startswith("_")} for x in gap_log],
        "moves_gt_12pct": moves, "moves_unconfirmed": bad, "junctions": junctions,
        "cuts": cuts, "stops": stop_rows, "stops_unclassified": unclassified, "ycut_signal_months": ycut,
        "reuse_suspects": reuse_bad,
        "unplaceable": {t: {"key": u["key"], "why": u["why"], "n_days": len(u["days"]),
                            "first": dates[min(u["days"])], "last": dates[max(u["days"])]} for t, u in unplace.items()},
        "skipped": skipped,
        "alias_proposals_not_in_pit_alias": {t: dict(c) for t, c in alias_rep.items()},
        "db_days_outside_lab_window": {t: n for t, n in outside_db.items() if n},
        "R_class_counts": dict(rcls_tot),
        "hygiene": {"spx_base": base_spx, "spx_stage": stg_spx, "ndx_base": base_ndx, "ndx_stage": stg_ndx,
                    "filled_names_in_panel_by_year": {k: dict(sorted(v.items())) for k, v in in_panel.items()}},
        "g2_changed_keys": changed, "g5_violations": g5_bad[:50],
    })

    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    prov = {"repo_head": head, "script_sha256": _sha(os.path.abspath(__file__)),
            "pit_alias_sha256": _sha(os.path.join(HERE, "pit_alias.py")),
            "pit_px_sha256_before": _sha(PX_OUT),
            "stocks_sha256": _sha(os.path.join(DATA, "stocks.json")),
            "index_history_sha256": _sha(os.path.join(DATA, "index_history.json")),
            "db_cache_fetched": cinfo["fetched"], "variant": rep["variant"]}
    rep["provenance"] = prov

    names_out = ["stage_pit_px.json", "stage_px_raw.json", "splits.json", "stage_unplaceable.json"]
    if not ok:
        for f in names_out:
            p = os.path.join(out, f)
            if os.path.exists(p):
                os.remove(p)
        io.open(os.path.join(out, "gate_fail.json"), "w", encoding="utf-8").write(
            json.dumps(rep, ensure_ascii=False, indent=1, default=str))
        print("❌ 관문 실패 %s — 아무것도 쓰지 않는다(이전 스테이징도 지웠다) · %s" %
              ([k for k, v in gates.items() if not v], os.path.join(out, "gate_fail.json")))
        for x in (bad[:10] + unclassified[:40] + reuse_bad[:10] + [{"g2": changed[:10]}] + [{"g5": g5_bad[:10]}]):
            print("   ", x)
        return 1
    if os.path.exists(os.path.join(out, "gate_fail.json")):
        os.remove(os.path.join(out, "gate_fail.json"))

    # ── 문서 조립(스테이징 = 병합 결과와 같은 바이트) ─────────────────────────────────────────
    src = dict(rec.get("src") or {})
    for k in db_keys:
        src[k] = "index_constituents"
    never = dict(rec.get("never") or {})
    never_removed = sorted(k for k in list(never) if k in closed)
    for k in never_removed:
        never.pop(k, None)
    repairs = dict(rec.get("repairs") or {})
    for k, c in cuts.items():
        r0 = dict(repairs.get(k) or {})
        r0["db_merge_cut"] = {"after": c["after"], "n_cut": c["n_cut"], "cut": c["cut"], "why": c["why"],
                              "by": "build/pit_px_db2.py --merge"}
        repairs[k] = r0
    n_pts = sum(sum(1 for x in o["p"] if x is not None) for o in newpx.values())
    managed = {
        "coverage": {"start": dates[0], "end": dates[-1], "n_dates": D, "n_tickers": len(newpx), "n_points": n_pts},
        "never": never, "n_never": len(never), "repairs": repairs,
        "src": dict(sorted(src.items())), "n_src_db": len(src),
        "src_note": "src 에 적힌 키는 사내 DB(public.index_constituents)의 «지수에 있던 날의 종가» 로 빈 날만 메운 것이다"
                    "(build/pit_px_db2.py --merge). 이미 있던 값은 덮지 않았다(선언된 절단은 repairs 의 db_merge_cut). "
                    "기준은 basis 에 키별로 적었다(db_pr = 분할만 되맞춘 가격수익 · 배당 없음 · db_scaled = 랩 배당조정 계열에 비율로 맞춤).",
        "basis": {k: b for k, b in sorted(basis.items())},
        "closed": dict(sorted(closed.items())), "n_closed": len(closed),
        "closed_note": "닫힌 키 — build/pit_px_refresh.py 가 묻지도 잇지도 않는다(상장폐지 · 티커 재사용 · 옛 증권 전용 키). "
                       "stops = 계열이 보유월 끝 전에 멈추는 날과 그 달 수익 규칙(pit_panel.y_stop): missing = 회사가 계속 "
                       "거래됐다(지수만 떠남 · 개명 · 재분류) → 결측 · last_price = 인수 · 파산 · 비공개화 → 마지막 가격 · "
                       "short_cut = DB 에 월말 행이 없다 → 짧은 수익(선언). 분류는 공개 사실(uncertain = 날짜 · 형태 미확인).",
        "db_merge": {"script": "build/pit_px_db2.py --merge", "script_sha256": prov["script_sha256"],
                     "pit_alias_sha256": prov["pit_alias_sha256"], "db_cache_fetched": cinfo["fetched"],
                     "variant": rep["variant"], "gates": gates,
                     "note": "사내 DB 캐시는 저장소 밖에 있다 — 같은 캐시 · 같은 입력이면 같은 바이트가 나온다. "
                             "G4 는 커버리지 점검이지 가격 품질 근거가 아니다(2017 완화는 사전등록 이탈)."},
        "dates": dates, "px": dict(sorted(newpx.items())),
    }
    # 키 차례를 고정한다 — 병합 위에서 또 돌려도 같은 바이트(내용이 같으면)
    ORDER = ("note", "source", "coverage", "never", "n_never", "quarantine", "n_quarantine", "repairs", "breaks",
             "quarantine_note", "src", "n_src_db", "src_note", "basis", "closed", "n_closed", "closed_note", "db_merge",
             "dates", "px")
    doc = {}
    for k in ORDER:
        if k in managed:
            doc[k] = managed[k]
        elif k in rec:
            doc[k] = rec[k]
    for k, v in rec.items():
        if k not in doc:
            doc[k] = v
    raw_keys = [k for k in db_keys if k not in L["today"] and k not in L["Q"]]
    rpx = {}
    for k in raw_keys:
        vals = {g: sig(v) for g, v in place[k].items()}
        if k in cuts:
            pass                                          # 원 종가는 DB 날만 — 절단과 무관
        lo, hi = min(vals), max(vals)
        rpx[k] = {"i0": lo, "p": [vals.get(i) for i in range(lo, hi + 1)]}
    raw_doc = {
        "note": "시총용 원 종가 — 사내 DB «지수에 있던 날» 의 종가(지수 시총 ÷ 지수 주식수 = 그날 지수가 쓴 종가, DB 종가 열로 "
                "0.2% 안 교차 확인) · 분할만 되맞춤(배당 · 분사 조정 없음 · 기준은 각 이름의 DB 마지막 재적일). DB 로 메운 키만 — "
                "나머지 이름은 r_stagem 이 배당조정 pxd 로 내려간다(adj_fallback). build/pit_px_db2.py --merge 가 data/pit_px.json 과 "
                "같은 격자로 쓴다(🚨 격자가 stocks.json pxd_dates 와 같아야 r_stagem 이 읽는다 — 같은 커밋 판에서 쓸 것).",
        "src": "build/pit_px_db2.py --merge", "script_sha256": prov["script_sha256"], "db_cache_fetched": cinfo["fetched"],
        "dates": dates, "px": dict(sorted(rpx.items())),
        "basis": {k: {"tickers": basis[k]["tickers"], "splits": basis[k].get("splits") or [], "n": len(place[k])}
                  for k in sorted(rpx)},
    }
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    raw_body = json.dumps(raw_doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    io.open(os.path.join(out, "stage_pit_px.json"), "w", encoding="utf-8", newline="").write(body)
    io.open(os.path.join(out, "stage_px_raw.json"), "w", encoding="utf-8", newline="").write(raw_body)
    io.open(os.path.join(out, "splits.json"), "w", encoding="utf-8").write(json.dumps({
        "note": "DB 에서 찾은 분할(가격 비 ≈ 1/k · 주식수 비 ≈ k · 시총 연속 또는 정확한 주식수 비 · splits.json 또는 DB 종가 열 확인).",
        "splits": split_log,
        "near_miss": rep["splits_near_miss"], "gap_suspects": rep["gap_split_suspects"]}, ensure_ascii=False, indent=1))
    io.open(os.path.join(out, "splits_evidence_local.json"), "w", encoding="utf-8").write(json.dumps({
        "note": "🚨 저장소에 넣지 않는다 — DB 주식수·시총 비율이 들어 있다.",
        "splits": split_local, "near": near_log, "gap": gap_log}, ensure_ascii=False, indent=1, default=str))
    if unplace:
        up = {}
        for t, u in unplace.items():
            lo, hi = min(u["days"]), max(u["days"])
            up[t] = {"key": u["key"], "why": u["why"], "i0": lo,
                     "p": [sig(u["days"][i]) if i in u["days"] else None for i in range(lo, hi + 1)]}
        io.open(os.path.join(out, "stage_unplaceable.json"), "w", encoding="utf-8").write(json.dumps({
            "note": "넣을 수 없는 값(오늘 유니버스 키) — 분할조정 원종가(db_pr).",
            "dates_ref": "stocks.json pxd_dates", "px": up}, ensure_ascii=False, separators=(",", ":")))
    rep["never_removed"] = never_removed
    rep["out_sha256"] = {"pit_px.json": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                         "_px_raw.json": hashlib.sha256(raw_body.encode("utf-8")).hexdigest()}
    if merge:
        io.open(PX_OUT, "w", encoding="utf-8", newline="").write(body)
        io.open(PX_RAW, "w", encoding="utf-8", newline="").write(raw_body)
        rep["merged_into"] = [os.path.relpath(PX_OUT, ROOT), os.path.relpath(PX_RAW, ROOT)]
    io.open(os.path.join(out, "report.json"), "w", encoding="utf-8").write(
        json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    print("✅ 관문 통과 · DB 키 %d(이번에 채운 키 %d · 보탠 관측 %d) · 절단 %s · 닫힌 키 %d · never 에서 뺀 키 %d · "
          "새로 값이 선 멤버-월(2016-08..2026-07) %d · 남은 결손 %d · 커버리지 ≥ 0.90 인 달 %d/120%s"
          % (len(db_keys), len(stage_add), rep["n_added_points"], {k: c["n_cut"] for k, c in cuts.items()} or "없음",
             len(closed), len(never_removed), sum(new_by_y.values()), sum(miss_by_y.values()), t_pass,
             (" → 병합: %s" % ", ".join(rep["merged_into"])) if merge else (" → 스테이징 %s" % out)))
    print("   pit_px.json sha256 %s · _px_raw.json sha256 %s" % (rep["out_sha256"]["pit_px.json"][:16],
                                                            rep["out_sha256"]["_px_raw.json"][:16]))
    return 0


# ══ 스테이징 파일 병합(--merge-stage) — 공개 데이터셋 종가를 빈 날에만 넣는다(2026-09-26 제안) ═══════════════════
#
#  입력 = pit_px 모양 스테이징 파일(임의 경로): {format: "pit_px_stage/1", visibility, dates, px: {키: {i0, p}}, keys, stops, moves,
#    provenance}. keys[키].segments = [{from, to, src, basis, n}] — src 는 공개 데이터셋 태그(«데이터셋:이름» · kaggle:dgawlik/nyse ·
#    yf_successor:FBIN · zenodo:12557888). 태그가 없는 맨 스테이징({dates, px} 만)은 --src-tag 태그 하나를 모든 키에 준다.
#  --src-tags 는 허용 목록이다(쉼표로 가른 fnmatch 패턴 · 기본 *): 목록 밖 태그의 날은 넣지 않는다(예: U7 을 거두면 kaggle:camnugent/* 빼기).
#  넣는 칸 = --merge 와 같은 뜻: ① 그 키에 값이 없고 ② 명단 티커가 lab_val 차례로 다른 키의 값을 읽지 않고 ③ 멤버 창(멤버 달 + 다음 달) 안.
#    있는 값은 절대 안 덮는다. 오늘 유니버스 키(sd)는 넣지 않는다(보고만) · 격리 이름(pit_quarantine)은 넣지 않는다.
#  관문 — 하나라도 어기면 --write 는 아무것도 쓰지 않는다:
#    G1 인접 거래일(JUMP_GAP 안) 변동 > JUMP_MAX 인데 한쪽이라도 넣은 날이면, 스테이징 moves 에 같은 두 날 · 같은 크기(0.5%p 안)로
#       확인 판정(explained · explained_monthly · known_distribution)이 있거나 KNOWN_DIST 에 있어야 한다.
#    G2 티커 수가 줄지 않는다 · 기존 값은 한 칸도 안 바뀐다.   G3 격리 이름에 값이 들어가지 않는다.
#    G4 위생(--merge 와 같은 규칙 · pit_panel.month_rows · SPX 연도별 ≥ 0.98 또는 이미 아래인 해는 나빠지지 않음).
#    G5 넣은 값의 날은 index_members.load() 로 따로 잰 멤버 창 ± WIN_TOL 안.
#    G6 넣은 날 쪽 멈춤(find_stops)은 전부 규칙이 있다 — STOPS · DB_GAP, 또는 스테이징 stops 의 같은 날 판정(missing · last_price · short_cut).
#    G7 기존 키에 넣을 때 기존 값과 REUSE_GAP 넘게 떨어져 있으면, 스테이징 keys[키].reuse_check 가 같은 발행사(same_issuer)여야 한다.
#  쓰는 것(--write): data/pit_px.json 한 파일 — px(빈 날만) · closed[키](since · stops 에 by = "stage" 로 판정을 더한다 · 없으면 새로) ·
#    never(메운 키는 뺀다) · stage_src(키마다 넣은 구간 · 태그 · 기준) · stage_merges(파일 sha256 · provenance · 관문 — 같은 파일은 한 번만)
#    · coverage. src · basis · db_merge(이 파일의 사내 DB 병합 기록)는 건드리지 않는다. _px_raw.json 도 안 쓴다(스테이징 값은 원 종가가
#    아니다 — r_stagem 은 그 키를 배당조정 pxd 로 내려간다 · adj_fallback).
#  같은 입력이면 같은 바이트다 · 이미 병합된 판 위에서 다시 돌려도 바뀌지 않는다(보고의 idempotent 가 그것을 잰다).
#  --merge 를 다시 돌려도 by = "stage" 멈춤은 남는다(_keep_stage_stops) — 그 밖의 스테이징 값은 --merge 에게 랩 값이다.
#    다만 그 값이 낀 인접 변동은 --merge 의 G1 이 DB 종가 열로 다시 묻지 않는다(stage_gated_days · 관문을 모두 통과한 병합만 ·
#    이번 실행에 DB 로 새로 메운 날이 끼면 묻는다) · 스테이징이 이어 붙인 DB 멈춤 줄은 남긴다 — 병합본 위 재실행 = 같은 바이트.
STAGE_FORMAT = "pit_px_stage/1"
STAGE_TAG_RX = r"^[a-z][a-z0-9_]*:[A-Za-z0-9_.@/\-]+$"
STAGE_Y = ("missing", "last_price", "short_cut")
STAGE_OK_VERDICTS = ("explained", "explained_monthly", "known_distribution")
STAGE_NOTE = ("stage_src 의 키 · 날은 공개 데이터셋 스테이징(build/pit_px_db2.py --merge-stage)으로 빈 날만 메운 것이다. src 는 데이터셋 "
              "태그(kaggle:… · yf_successor:… · zenodo:…) · basis tr = 분할 + 배당 조정(랩 규약) · tr_derived = 원 종가 × 공개 데이터셋에서 "
              "뽑은 배당 계수 · pr = 가격수익(배당 누락은 선언된 편향). 이미 있던 값은 덮지 않았다. 계열 멈춤 판정은 closed[키].stops 의 "
              "by = stage 줄이다. 출처 · 판 · 관문은 stage_merges 에 파일마다 적는다.")


def _keep_stage_stops(closed, prev_closed):
    """--merge 가 closed[키] 를 다시 지을 때 스테이징 병합이 적은 멈춤(by = "stage")을 잃지 않게 한다 — 같은 날 규칙이 이미 있으면 둔다."""
    for k, pc in (prev_closed or {}).items():
        keep = [s for s in ((pc or {}).get("stops") or []) if s.get("by") == "stage"]
        if not keep or k not in closed:
            continue
        have = {s["d"] for s in (closed[k].get("stops") or [])}
        add = [s for s in keep if s["d"] not in have]
        if add:
            closed[k]["stops"] = sorted(list(closed[k].get("stops") or []) + add, key=lambda s: s["d"])


def stage_gated_days(rec, dates, place=None):
    """문서 rec(pit_px.json)에서 스테이징 병합이 관문으로 확인한 날 — ({키: {격자 색인: 파일 sha 앞 16자}}, {파일 sha 앞 16자}).

    날 = stage_src[키] 구간(from..to) 안이고 · 그 구간의 file 이 관문을 **모두** 통과한 stage_merges 줄(sha256 앞 16자)이고 ·
    rec 의 그 키에 그날 값이 있고 · place[키](이번 실행의 DB 날)가 아닌 날. 그 병합의 G1 은 넣은 날이 낀 인접 짝을 전부 스테이징
    moves 로 확인했으므로(stage_merge) --merge 의 G1 은 이 날이 낀 짝을 다시 DB 종가 열로 묻지 않는다(DB 날끼리의 짝은 그대로 묻는다)."""
    ok = set()
    for m in rec.get("stage_merges") or []:
        g = m.get("gates") or {}
        if g and g.get("G1_moves_confirmed_by_stage") is True and all(v is True for v in g.values()) and m.get("sha256"):
            ok.add(str(m["sha256"])[:16])
    out = {}
    if not ok:
        return out, ok
    D = len(dates)
    for k, segs in (rec.get("stage_src") or {}).items():
        o = (rec.get("px") or {}).get(k)
        if not o:
            continue
        a = _stage_arr(o, D)
        pk = (place or {}).get(k) or {}
        got = {}
        for sg in segs or []:
            f = str(sg.get("file") or "")[:16]
            if f not in ok or not sg.get("from") or not sg.get("to"):
                continue
            lo, hi = bisect.bisect_left(dates, sg["from"]), bisect.bisect_right(dates, sg["to"])
            for i in range(lo, hi):
                if a[i] == a[i] and i not in pk:
                    got.setdefault(i, f)
        if got:
            out[k] = got
    return out, ok


def _stage_arr(obj, D):
    a = np.full(D, np.nan)
    for j, v in enumerate(obj.get("p") or []):
        if v is not None and 0 <= obj["i0"] + j < D:
            a[obj["i0"] + j] = float(v)
    return a


def stage_merge(L, rec, S, allow=("*",), src_tag=None, hygiene=True, sha=None, name=None):
    """스테이징 S 를 문서 rec(pit_px.json) 위에 빈 날만 병합한 (새 문서, 보고). 파일은 쓰지 않는다.
    L = load_lab()(오늘 유니버스 · 명단 · 격자) · 기존 값은 rec 에서 읽는다(병합본 위에서 다시 돌리는 재현 시험을 위해)."""
    import fnmatch
    import re
    dates, D, di = L["dates"], L["D"], L["di"]
    if list(S.get("dates") or []) != list(dates):
        raise SystemExit("🚨 스테이징 격자가 stocks.json pxd_dates 와 다르다 — 같은 판에서 다시 만들 것")
    if S.get("format") not in (STAGE_FORMAT, None):
        raise SystemExit("🚨 스테이징 형식 %r 를 모른다(%s)" % (S.get("format"), STAGE_FORMAT))
    mon, mon_ix, win, days_of = membership(L)
    Q, today = L["Q"], L["today"]
    PX = {t: a for t, a in L["PX"].items() if t in today}
    for k, o in rec["px"].items():
        if k not in PX and k not in Q:
            PX[k] = _stage_arr(o, D)
    Lx = dict(L, PX=PX)
    keys_meta = S.get("keys") or {}
    decl_stops = S.get("stops") or {}
    decl_moves = S.get("moves") or {}
    cnt = Counter()
    bad_tags, add, add_seg, unreach = set(), defaultdict(dict), defaultdict(dict), Counter()
    for k in sorted(S.get("px") or {}):
        o = S["px"][k]
        meta = keys_meta.get(k) or {}
        segs = meta.get("segments") or ([{"from": dates[0], "to": dates[-1], "src": src_tag, "basis": "?"}] if src_tag else [])
        if not segs:
            raise SystemExit("🚨 %s 에 src 태그가 없다 — 스테이징 keys[키].segments 또는 --src-tag 를 줄 것" % k)
        for sg in segs:
            if not re.match(STAGE_TAG_RX, sg.get("src") or ""):
                raise SystemExit("🚨 %s 의 src 태그 %r 는 «데이터셋:이름» 모양이 아니다" % (k, sg.get("src")))
        segs = sorted(segs, key=lambda s: s["from"])
        for a_, b_ in zip(segs, segs[1:]):
            if b_["from"] <= a_["to"]:
                raise SystemExit("🚨 %s 의 구간이 겹친다(%s..%s · %s..%s)" % (k, a_["from"], a_["to"], b_["from"], b_["to"]))
        tickers = list(meta.get("tickers") or [k])
        for j, v in enumerate(o.get("p") or []):
            if v is None:
                continue
            i = o["i0"] + j
            d = dates[i]
            sg = next((s for s in segs if s["from"] <= d <= s["to"]), None)
            if sg is None:
                cnt["no_segment"] += 1
                continue
            if not any(fnmatch.fnmatchcase(sg["src"], p) for p in allow):
                cnt["tag_not_allowed"] += 1
                bad_tags.add(sg["src"])
                continue
            if not (v > 0):
                raise SystemExit("🚨 %s %s 값 %r — 양수가 아니다" % (k, d, v))
            if k in today:
                cnt["unplaceable_today_key"] += 1
                continue
            if k in Q:
                cnt["quarantined_key"] += 1
                continue
            a = PX.get(k)
            if a is not None and a[i] == a[i]:
                cnt["skipped_existing"] += 1
                continue
            if any(lab_val(Lx, t, i)[0] is not None for t in tickers):
                cnt["skipped_priced_under_other_key"] += 1
                continue
            if not any(i in win.get(t, ()) for t in tickers):
                cnt["outside_member_window"] += 1
                continue
            add[k][i] = float(v)
            add_seg[k][i] = sg
            if not any((PA.key_at(t, d) or t) == k or (PA.key_at(t, d) is None and k in (t, t.replace("-", "."),
                       L["splice"].get(t), L["splice"].get(t.replace("-", ".")))) for t in tickers):
                unreach[k] += 1                           # 넣지만 지금 pit_alias 로는 안 읽힌다(날짜 인식 키 줄이 먼저 필요)
    add = {k: v for k, v in add.items() if v}
    merged = {}
    for k, vals in add.items():
        a = PX[k].copy() if k in PX else np.full(D, np.nan)
        for i, v in vals.items():
            a[i] = v
        merged[k] = a
    # G1 — 넣은 날이 낀 큰 변동은 스테이징이 같은 두 날 · 같은 크기로 확인해 두었어야 한다
    g1_bad, g1_n = [], 0
    for k, a in merged.items():
        dm = {(m["d0"], m["d1"]): m for m in (decl_moves.get(k) or [])}
        nz = np.where(a == a)[0]
        for x, y in zip(nz, nz[1:]):
            x, y = int(x), int(y)
            if y - x > JUMP_GAP or (x not in add[k] and y not in add[k]):
                continue
            s = a[y] / a[x] - 1
            if abs(math.log(1 + s)) <= math.log(1 + JUMP_MAX):
                continue
            g1_n += 1
            m = dm.get((dates[x], dates[y]))
            tks = (keys_meta.get(k) or {}).get("tickers") or [k]
            kd = next((KNOWN_DIST.get((t, dates[y])) for t in tks if KNOWN_DIST.get((t, dates[y]))), None)
            ok = bool(kd) or bool(m and m.get("verdict") in STAGE_OK_VERDICTS
                                  and abs(math.log(1 + s) - math.log(1 + float(m["move"]))) <= 0.005)
            if not ok:
                g1_bad.append({"key": k, "d0": dates[x], "d1": dates[y], "move": round(float(s), 4),
                               "declared": m and m.get("verdict")})
    # G2 · G3
    g2 = all(np.array_equal(PX[k][PX[k] == PX[k]], merged[k][PX[k] == PX[k]]) for k in merged if k in PX)
    g3 = not any(k in Q for k in merged)
    # G5 — index_members 로 따로 잰 멤버 창
    import index_members as IM
    mem2, _car = IM.load()
    mon2 = defaultdict(set)
    for ym, ts in mem2.items():
        for x in ts:
            mon2[x].add(ym)
    ok_cache, g5_bad = {}, []
    for k, vals in add.items():
        tks = (keys_meta.get(k) or {}).get("tickers") or [k]
        for i in vals:
            dist = 10 ** 9
            for t in tks:
                if t not in ok_cache:
                    ms = set(mon2.get(L["orig"].get(t, t)) or mon2.get(t) or set())
                    for f in PA.LIST_FIX:
                        if f["good"] == t:
                            ms |= {m for m in (mon2.get(f["bad"]) or set()) if f["frm"] <= m <= f["to"]}
                    okd = set()
                    for m in ms:
                        for mm in (m, mshift(m, 1)):
                            okd.update(days_of.get(mm, ()))
                    ok_cache[t] = sorted(okd)
                okx = ok_cache[t]
                p = bisect.bisect_left(okx, i)
                dist = min([dist] + [abs(okx[x] - i) for x in (p - 1, p) if 0 <= x < len(okx)])
            if dist > WIN_TOL:
                g5_bad.append((k, dates[i]))
    # G6 — 넣은 날 쪽 멈춤의 규칙
    stops_new, g6_bad = defaultdict(list), []
    for k, a in merged.items():
        dd = {s["d"]: s for s in (decl_stops.get(k) or [])}
        for L_, nxt in find_stops(a, dates):
            if L_ not in add[k]:
                continue
            d, dn = dates[L_], (None if nxt is None else dates[nxt])
            s = classify_stop(k, d, dn) or dd.get(d)      # STOPS · DB_GAP(공개 사실 표)가 먼저 · 없으면 스테이징의 판정
            if not s or s.get("y") not in STAGE_Y:
                g6_bad.append({"key": k, "d": d, "resume": dn})
                continue
            sg = add_seg[k][L_]
            stops_new[k].append({"d": d, "y": s["y"], "why": s.get("why") or "", "uncertain": bool(s.get("uncertain")),
                                 "resume": dn, "by": "stage", "src": sg["src"]})
    # G7 — 멀리 떨어진 기존 키(재사용 티커)는 같은 발행사 판정이 있어야 한다
    g7_bad = []
    for k, vals in add.items():
        if k not in rec["px"]:
            continue
        nz = np.where(PX[k] == PX[k])[0]
        if not len(nz):
            continue
        a0, a1, b0, b1 = int(nz[0]), int(nz[-1]), min(vals), max(vals)
        gap = max(0, b0 - a1, a0 - b1)
        rc = ((keys_meta.get(k) or {}).get("reuse_check") or {}).get("verdict")
        if gap > REUSE_GAP and rc != "same_issuer":
            g7_bad.append({"key": k, "gap_days": gap, "reuse_check": rc})
    # G4 — 위생(--merge 와 같은 규칙)
    g4, g4_detail, hyg = True, {}, {}
    if hygiene:
        import pit_panel as PP
        W = PP.load_world()
        IDXM = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))["idx_monthly"]
        sigm = [m for m in sorted(W["me"]) if "2015-12" <= m <= "2026-07"]

        def corr_y(Wx, ix, labn):
            rows, _ = PP.month_rows(Wx, ix, sigm, "2026-08")
            bm = IDXM.get(labn) or {}
            by = defaultdict(list)
            for x in rows:
                if x["m"] in bm:
                    by[x["m"][:4]].append((sum(x["wb"][t] * x["r"][t] for t in x["names"]) * 100, bm[x["m"]]))
            return {y: round(float(np.corrcoef([p for p, _ in v], [b for _, b in v])[0, 1]), 4)
                    for y, v in sorted(by.items()) if len(v) >= 3}

        base = {"spx": corr_y(W, "spx", "S&P 500"), "ndx": corr_y(W, "ndx", "NASDAQ 100")}
        PX0, ST0 = W["PX"], W.get("stops")
        W["PX"] = dict(PX0)
        W["PX"].update({k: a for k, a in merged.items() if k not in today})
        W["stops"] = {k: dict(v) for k, v in (ST0 or {}).items()}
        for k, ss in stops_new.items():
            for s in ss:
                W["stops"].setdefault(k, {}).setdefault(s["d"], s)
        after = {"spx": corr_y(W, "spx", "S&P 500"), "ndx": corr_y(W, "ndx", "NASDAQ 100")}
        W["PX"], W["stops"] = PX0, ST0
        for y in [str(y) for y in range(2016, 2027)]:
            b_, s_ = base["spx"].get(y), after["spx"].get(y)
            if s_ is None:
                g4_detail[y], g4 = "no_data", False
            elif s_ >= 0.98:
                g4_detail[y] = "pass"
            elif b_ is not None and b_ < 0.98 and s_ >= b_ - 0.001:
                g4_detail[y] = "literal_fail_preexisting(base %.4f → stage %.4f)" % (b_, s_)
            else:
                g4_detail[y], g4 = "FAIL(base %s → stage %.4f)" % (b_, s_), False
        hyg = {"base": base, "stage": after}
    gates = {"G1_moves_confirmed_by_stage": not g1_bad, "G2_no_decrease_no_overwrite": g2, "G3_no_quarantine": g3,
             "G4_hygiene_spx_ge_0.98_or_not_worse": g4 if hygiene else None, "G5_member_window": not g5_bad,
             "G6_stops_classified": not g6_bad, "G7_no_reused_ticker_mixing": not g7_bad}
    ok = bool(hygiene) and all(v for v in gates.values() if v is not None)

    # 커버리지(월말 가격 · 개수 기준 · --merge 와 같은 규칙)
    PXa = dict(PX)
    PXa.update(merged)
    cov = {}
    for ym in [m for m in sorted(L["me"]) if "2014-06" <= m <= "2026-07"]:
        i = L["me"][ym]
        memb = set(L["lists"]["spx"].get(ym) or []) | set(L["lists"]["ndx"].get(ym) or [])
        n0 = sum(1 for t in memb if lab_val(Lx, t, i)[0] is not None)
        n1 = sum(1 for t in memb if lab_val(dict(L, PX=PXa), t, i)[0] is not None)
        cov[ym] = [n0, n1, len(memb)]

    # 문서 조립 — rec 의 키 차례를 지키고 새 칸은 끝에 붙인다
    newpx = {k: {"i0": o["i0"], "p": list(o["p"])} for k, o in rec["px"].items()}
    for k, vals in add.items():
        arr = [None] * D
        if k in newpx:
            for j, v in enumerate(newpx[k]["p"]):
                arr[newpx[k]["i0"] + j] = v
        for i, v in vals.items():
            if arr[i] is not None:
                raise SystemExit("🚨 내부 오류: %s %s 에 이미 값이 있다(덮지 않는다)" % (k, dates[i]))
            arr[i] = v
        idx = [i for i, x in enumerate(arr) if x is not None]
        newpx[k] = {"i0": idx[0], "p": arr[idx[0]:idx[-1] + 1]}
    closed = {k: dict(v) for k, v in (rec.get("closed") or {}).items()}
    for k, vals in add.items():
        c = dict(closed.get(k) or {})
        st = list(c.get("stops") or [])
        have = {s["d"] for s in st}
        st += [s for s in stops_new.get(k, []) if s["d"] not in have]
        last = dates[max(i for i, x in enumerate(_stage_arr(newpx[k], D)) if x == x)]
        c["since"] = max(c.get("since") or "", last)
        c.setdefault("src", "stage")
        c.setdefault("exit", "")
        c.setdefault("uncertain", False)
        c["stops"] = sorted(st, key=lambda s: s["d"])
        closed[k] = c
    never = {k: v for k, v in (rec.get("never") or {}).items() if k not in add}
    ssrc = {k: list(v) for k, v in (rec.get("stage_src") or {}).items()}
    for k in sorted(add):
        by_sg = defaultdict(list)
        for i in sorted(add[k]):
            sg = add_seg[k][i]
            by_sg[(sg["from"], sg["src"], sg.get("basis"))].append(i)
        for (_f, tag, basis), ix in sorted(by_sg.items()):
            e = {"from": dates[ix[0]], "to": dates[ix[-1]], "src": tag, "basis": basis, "n": len(ix), "file": (sha or "")[:16]}
            if e not in ssrc.setdefault(k, []):
                ssrc[k].append(e)
    merges = list(rec.get("stage_merges") or [])
    n_pts_add = sum(len(v) for v in add.values())
    if sha and not any(m.get("sha256") == sha for m in merges) and n_pts_add:
        merges.append({"file": name, "sha256": sha, "format": S.get("format"), "visibility": S.get("visibility"),
                       "made": S.get("made"), "provenance": S.get("provenance"), "gates": gates,
                       "n_keys": len(add), "n_points": n_pts_add,
                       "tags": sorted({add_seg[k][i]["src"] for k in add for i in add[k]}), "allow": list(allow)})
    covb = dict(rec.get("coverage") or {})
    covb.update({"n_tickers": len(newpx), "n_points": sum(sum(1 for x in o["p"] if x is not None) for o in newpx.values())})
    upd = {"px": dict(sorted(newpx.items())), "closed": dict(sorted(closed.items())), "n_closed": len(closed),
           "never": never, "n_never": len(never), "coverage": covb}
    doc = {}
    for k, v in rec.items():
        doc[k] = upd.get(k, v)
    for k, v in (("stage_note", STAGE_NOTE), ("stage_src", dict(sorted(ssrc.items()))), ("stage_merges", merges)):
        if v:
            doc[k] = v
    rep = {"stage_file": name, "stage_sha256": sha, "visibility": S.get("visibility"), "allow": list(allow),
           "gates": gates, "ok": ok, "counts": dict(cnt), "keys_new": sorted(k for k in add if k not in rec["px"]),
           "keys_filled": sorted(k for k in add if k in rec["px"]), "n_points_added": n_pts_add,
           "unreachable_until_alias": dict(unreach), "tags_not_allowed": sorted(bad_tags),
           "g1_moves_checked": g1_n, "g1_unconfirmed": g1_bad[:50], "g5_violations": g5_bad[:50], "g6_unclassified": g6_bad[:50],
           "g7_suspects": g7_bad, "g4_detail": g4_detail, "hygiene": hyg,
           "coverage_count_by_month": cov,
           "newly_priced_mm": {"2016-08..2026-07": sum(c[1] - c[0] for m, c in cov.items() if m >= "2016-08"),
                               "2014-06..2016-07": sum(c[1] - c[0] for m, c in cov.items() if m < "2016-08")},
           "stops_added": sum(len(v) for v in stops_new.values())}
    return doc, rep


def merge_stage_cli(argv):
    """python build/pit_px_db2.py --merge-stage 파일 [--src-tags 패턴,…] [--src-tag 태그] [--out-dir 경로] [--write]"""
    def opt(name):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
    path = opt("--merge-stage")
    if not path or not os.path.exists(path):
        raise SystemExit("🚨 --merge-stage 파일 경로가 필요하다")
    allow = tuple(x.strip() for x in (opt("--src-tags") or "*").split(",") if x.strip())
    write = "--write" in argv
    out = os.path.abspath(opt("--out-dir") or os.path.join(_outdir(), "stage_merge"))
    if os.path.commonpath([out.lower(), ROOT.lower()]) == ROOT.lower():
        raise SystemExit("🚨 --out-dir %s 가 저장소 안이다 — 보고와 병합본은 저장소 밖에만 쓴다" % out)
    os.makedirs(out, exist_ok=True)
    L = load_lab()
    rec = L["rec"]
    S = json.load(io.open(path, encoding="utf-8"))
    sha = _sha(path)
    before = _sha(PX_OUT)
    doc, rep = stage_merge(L, rec, S, allow=allow, src_tag=opt("--src-tag"), hygiene=True, sha=sha,
                           name=os.path.basename(path))
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    doc2, _ = stage_merge(L, doc, S, allow=allow, src_tag=opt("--src-tag"), hygiene=False, sha=sha,
                          name=os.path.basename(path))
    rep["idempotent"] = json.dumps(doc2, ensure_ascii=False, separators=(",", ":")) + "\n" == body
    rep["pit_px_sha256_before"] = before
    rep["out_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    rep["script_sha256"] = _sha(os.path.abspath(__file__))
    io.open(os.path.join(out, "stage_pit_px.json"), "w", encoding="utf-8", newline="").write(body)
    rep["written"] = []
    if write:
        if not rep["ok"]:
            raise SystemExit("❌ 관문 실패 %s — data/pit_px.json 을 쓰지 않는다 · 보고 %s" % (
                [k for k, v in rep["gates"].items() if v is False], os.path.join(out, "stage_merge_report.json")))
        if S.get("visibility") != "public":
            raise SystemExit("🚨 visibility = %r — 공개(public) 스테이징만 저장소에 쓴다" % S.get("visibility"))
        if _sha(PX_OUT) != before:
            raise SystemExit("🚨 data/pit_px.json 이 도는 사이에 바뀌었다 — 당겨 온 판에서 다시 돌릴 것")
        io.open(PX_OUT, "w", encoding="utf-8", newline="").write(body)
        rep["written"] = [os.path.relpath(PX_OUT, ROOT)]
    io.open(os.path.join(out, "stage_merge_report.json"), "w", encoding="utf-8").write(
        json.dumps(rep, ensure_ascii=False, indent=1, sort_keys=True, default=str))
    print("%s 스테이징 병합(%s) · 관문 %s · 새 키 %d · 메운 키 %d · 보탠 값 %d · 새로 값이 선 멤버-월 %s · 재현 %s · %s" % (
        "✅" if rep["ok"] else "❌", "쓰기" if write else "시험", {k: v for k, v in rep["gates"].items()},
        len(rep["keys_new"]), len(rep["keys_filled"]), rep["n_points_added"], rep["newly_priced_mm"], rep["idempotent"],
        (" → " + ", ".join(rep["written"])) if rep["written"] else ("보고 " + out)))
    return 0 if rep["ok"] else 1


# ══ 자체 시험(--selftest) — 합성 세계에서 «--merge → --merge-stage --write → --merge» ══════════════════════════════
def selftest():
    """합성 세계(임시 폴더 · 사내 DB · 저장소 자료를 읽지도 쓰지도 않는다)에서 병합 차례를 끝까지 돌린다.

    ① --merge            DB 캐시(합성)로 편출 이름 OLDX 의 1–2월을 메운다 · 02-29 멈춤(STOPS)
    ② --merge-stage      공개 스테이징(합성)이 3–4월을 메운다 — 02-29→03-01 +20% · 03-15→03-16 −18% 는 스테이징 moves 가 확인
    ③ --merge(다시)      스테이징 병합본 위에서 관문 통과 · 두 변동 = stage_confirmed · **같은 바이트**(02-29 DB 멈춤 줄도 남는다)
    ④ 대조 A             stage_merges 의 G1 을 False 로 바꾸면 --merge 가 G1 에서 멈춘다(고치기 전의 동작) · 아무것도 안 쓴다
    ⑤ 대조 B             이번 실행에 DB 로 새로 메운 날(05-02 +30%)이 스테이징 날 옆에 오면 stage_confirmed 가 아니다 → G1 실패
    pit_panel(위생 G4) · index_members(G5) · pit_quarantine 은 합성 판으로 바꿔 끼운다 — 이 시험은 G1 · G6 · 재현을 잰다."""
    import shutil
    import types
    g = globals()
    saved = {k: g[k] for k in ("DATA", "PX_OUT", "PX_RAW", "ROOT", "STOPS", "fetch_cache")}
    saved_mod = {m: sys.modules.get(m) for m in ("pit_panel", "index_members")}
    saved_q, saved_env = PQ.names, os.environ.get("RBATCH_PXREC")
    tmp = tempfile.mkdtemp(prefix="pit_px_db2_selftest_")
    fails = []

    def check(cond, what):
        print("  %s %s" % ("✅" if cond else "❌", what))
        if not cond:
            fails.append(what)

    def wj(path, obj):
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))

    try:
        root = os.path.join(tmp, "repo")
        data = os.path.join(root, "data")
        pxrec = os.path.join(tmp, "pxrec")
        os.makedirs(os.path.join(data, "sd"))
        os.makedirs(pxrec)
        days, d = [], _dt.date(2016, 1, 4)
        while d <= _dt.date(2016, 7, 29):
            if d.weekday() < 5:
                days.append(d.isoformat())
            d += _dt.timedelta(days=1)
        D = len(days)
        di = {x: i for i, x in enumerate(days)}
        months = sorted({x[:7] for x in days})
        wj(os.path.join(data, "stocks.json"), {"pxd_dates": days, "stocks": [{"t": "AAA"}]})
        wj(os.path.join(data, "sd", "AAA.json"), {"pxd": [round(100 * (1 + 0.001 * i), 4) for i in range(D)]})
        H = {"months": {m: {"spx": ["AAA"], "ndx": ["AAA"] + (["OLDX"] if m <= "2016-04" else [])} for m in months},
             "cik": {}}
        wj(os.path.join(data, "index_history.json"), H)
        wj(os.path.join(data, "pit_universe.json"), {"cik_spliced": {}})
        wj(os.path.join(data, "splits.json"), {"co": {}})
        allm = []
        m = "2015-12"
        while m <= "2026-08":
            allm.append(m)
            m = mshift(m, 1)

        def rr(m):
            return ((int(m[5:7]) * 37 + int(m[:4]) * 11) % 17 - 8) / 100.0
        wj(os.path.join(data, "strategy_charts.json"),
           {"idx_monthly": {lab: {m: rr(m) * 100 for m in allm} for lab in ("S&P 500", "NASDAQ 100")}})
        wj(os.path.join(data, "pit_px.json"), {"note": "selftest", "dates": days, "px": {}})

        # 합성 DB 캐시 — OLDX · NDX · 2016-01-04..02-29 · 원종가(q = 1)
        db_days = [x for x in days if x <= "2016-02-29"]
        rows = []
        for j, x in enumerate(db_days):
            p = round(50 * (1 + 0.002 * j), 4)
            rows.append(("NDX Index", "OLDX UW Equity", "OLDX", "USD", "US", x, p, 1e6, p * 1e6))

        def put_cache(rows_):
            with gzip.open(os.path.join(pxrec, "db_cache.pkl.gz"), "wb") as fh:
                pickle.dump({"cols": CACHE_COLS, "rows": rows_, "fetched": "selftest"}, fh)
        put_cache(rows)

        # 합성 판으로 바꿔 끼우기
        def no_fetch(path):
            raise SystemExit("🚨 selftest 는 DB 에 접속하지 않는다(%s)" % path)
        g.update({"DATA": data, "PX_OUT": os.path.join(data, "pit_px.json"), "PX_RAW": os.path.join(data, "_px_raw.json"),
                  "ROOT": root, "fetch_cache": no_fetch,
                  "STOPS": {"OLDX": {"2016-02-29": ("missing", "selftest — DB 행이 끝났다(계속 거래)", False)}}})
        os.environ["RBATCH_PXREC"] = pxrec
        PQ.names = lambda: set()
        im = types.ModuleType("index_members")

        def im_load(start=None, path=None):
            return {m: sorted(set(r["spx"]) | set(r["ndx"])) for m, r in H["months"].items()}, []
        im.load = im_load
        pp = types.ModuleType("pit_panel")
        pp.load_world = lambda: {"me": {m: 0 for m in allm}, "PX": {}, "stops": {}, "FUND": {}, "dates": days}

        def pp_rows(W, ix, sig_months, end):
            out = []
            for mm in sorted(sig_months):
                m1 = mshift(mm, 1)
                if m1 <= end:
                    out.append({"m": m1, "names": ["AAA"], "wb": {"AAA": 1.0}, "r": {"AAA": rr(m1)}, "key": {"AAA": "AAA"}})
            return out, []
        pp.month_rows = pp_rows
        sys.modules["index_members"], sys.modules["pit_panel"] = im, pp

        def body():
            return io.open(g["PX_OUT"], "rb").read()

        def report(name):
            return json.load(io.open(os.path.join(pxrec, "merge", name), encoding="utf-8"))

        print("① --merge(스테이징 전 판)")
        rc = main(["--merge"])
        check(rc == 0, "첫 병합 관문 통과(exit %s)" % rc)
        P1 = json.loads(body())
        check(sum(1 for v in P1["px"]["OLDX"]["p"] if v is not None) == len(db_days), "OLDX DB 날 %d 개" % len(db_days))

        print("② --merge-stage --write(합성 공개 스테이징)")
        s_days = [x for x in days if "2016-03-01" <= x <= "2016-04-29"]
        last_db = P1["px"]["OLDX"]["p"][-1]
        vals, v = [], last_db * 1.20
        for x in s_days:
            if x == "2016-03-16":
                v = v * 0.82
            vals.append(round(v, 4))
            v = v * 1.001
        mv1 = vals[0] / last_db - 1
        mv2 = vals[s_days.index("2016-03-16")] / vals[s_days.index("2016-03-15")] - 1
        S = {"format": STAGE_FORMAT, "visibility": "public", "made": "selftest", "dates": days,
             "px": {"OLDX": {"i0": di[s_days[0]], "p": vals}},
             "keys": {"OLDX": {"tickers": ["OLDX"], "segments": [{"from": s_days[0], "to": s_days[-1],
                                                                   "src": "zenodo:selftest", "basis": "pr",
                                                                   "n": len(s_days)}]}},
             "moves": {"OLDX": [{"d0": "2016-02-29", "d1": "2016-03-01", "move": round(mv1, 6), "verdict": "explained"},
                                {"d0": "2016-03-15", "d1": "2016-03-16", "move": round(mv2, 6), "verdict": "explained"}]},
             "stops": {"OLDX": [{"d": "2016-04-29", "y": "missing", "why": "selftest — 데이터셋 끝(계속 거래)"}]},
             "provenance": {"selftest": True}}
        spath = os.path.join(tmp, "stage_selftest.json")
        wj(spath, S)
        rc = merge_stage_cli(["--merge-stage", spath, "--src-tags", "zenodo:*", "--write",
                              "--out-dir", os.path.join(tmp, "stage_out")])
        check(rc == 0, "스테이징 병합 관문 통과 · 쓰기(exit %s)" % rc)
        B = body()
        PB = json.loads(B)
        check(bool(PB.get("stage_src", {}).get("OLDX")) and bool(PB.get("stage_merges")), "stage_src · stage_merges 가 실렸다")

        print("③ --merge(스테이징 병합본 위에서 다시)")
        rc = main(["--merge"])
        R3 = report("report.json") if rc == 0 else report("gate_fail.json")
        check(rc == 0, "관문 통과(exit %s · 고치기 전에는 G1 이 두 변동에서 멈췄다)" % rc)
        vd = sorted((x["d0"], x["verdict"]) for x in R3.get("moves_gt_12pct") or [])
        check(vd == [("2016-02-29", "stage_confirmed"), ("2016-03-15", "stage_confirmed")],
              "두 변동 = stage_confirmed(%s)" % vd)
        check(body() == B, "같은 바이트(재실행이 스테이징 병합본을 바꾸지 않는다)")
        st = [(s["d"], s.get("by")) for s in (json.loads(body())["closed"]["OLDX"]["stops"])]
        check(st == [("2016-02-29", None), ("2016-04-29", "stage")], "멈춤 줄 = DB 02-29 + 스테이징 04-29(%s)" % st)

        print("④ 대조 A — 관문을 통과하지 못한 스테이징 병합은 확인이 아니다")
        PA_ = json.loads(B)
        PA_["stage_merges"][0]["gates"]["G1_moves_confirmed_by_stage"] = False
        with io.open(g["PX_OUT"], "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(PA_, ensure_ascii=False, separators=(",", ":")) + "\n")
        before = body()
        rc = main(["--merge"])
        RA = report("gate_fail.json") if rc else {}
        check(rc == 1 and RA.get("gates", {}).get("G1_moves_confirmed_by_db_close") is False
              and len(RA.get("moves_unconfirmed") or []) == 2, "G1 실패 · 확인 못 한 변동 2(exit %s)" % rc)
        check(body() == before, "관문 실패 — 아무것도 쓰지 않았다")

        print("⑤ 대조 B — 이번 실행에 DB 로 새로 메운 날이 스테이징 날 옆이면 DB 증거가 있어야 한다")
        with io.open(g["PX_OUT"], "wb") as fh:
            fh.write(B)
        p5 = round(vals[-1] * 1.30, 4)
        put_cache(rows + [("NDX Index", "OLDX UW Equity", "OLDX", "USD", "US", "2016-05-02", p5, 1e6, p5 * 1e6)])
        g["STOPS"] = {"OLDX": dict(g["STOPS"]["OLDX"], **{"2016-05-02": ("missing", "selftest", False)})}
        rc = main(["--merge"])
        RB = report("gate_fail.json") if rc else {}
        bad = [(x["d0"], x["d1"], x["verdict"]) for x in RB.get("moves_unconfirmed") or []]
        fg = sorted(k for k, v in (RB.get("gates") or {}).items() if not v)
        check(rc == 1 and bad == [("2016-04-29", "2016-05-02", "unexplained")] and fg == ["G1_moves_confirmed_by_db_close"],
              "G1 만 실패 · 04-29→05-02 unexplained(%s · %s)" % (bad, fg))
        check(body() == B, "관문 실패 — 아무것도 쓰지 않았다")
    finally:
        g.update(saved)
        PQ.names = saved_q
        for m, mod in saved_mod.items():
            if mod is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = mod
        if saved_env is None:
            os.environ.pop("RBATCH_PXREC", None)
        else:
            os.environ["RBATCH_PXREC"] = saved_env
        shutil.rmtree(tmp, ignore_errors=True)
    print("✅ selftest 통과" if not fails else "❌ selftest 실패 %d: %s" % (len(fails), fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--merge-stage" in sys.argv:
        raise SystemExit(merge_stage_cli(sys.argv[1:]))
    raise SystemExit(main())
