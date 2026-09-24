# -*- coding: utf-8 -*-
"""build/pit_panel.py — 지수 강화 틀(idxrev.run/solve/ev)에 먹일 **시점정확 월별 패널** 한 벌.

IDXEG(PREREG-2026-09-23-IDXEG)의 idxeg.py 안에 있던 패널 준비를 떼어냈다(2026-09-23, GURUCMP 가 같이 쓴다).
두 등록이 같은 패널을 쓰지 않으면 «Eg 틸트 대 거장 틸트» 를 나란히 놓을 수 없고, 패널을 두 벌로 두면
반드시 갈린다(이 저장소가 되풀이 밟은 결함).

한 달의 패널 = 그 달 index_history 의 SPX 또는 NDX 명단(비는 달은 직전 달을 잇는다 · 티커 승계 포함)
  · 가격 = 오늘 유니버스 data/sd + 편출 정리본 data/pit_px.json({i0,p} · 격리 반영)
  · 주식수 = tech_backtest.load_fund 의 sh (fx + fx_pit · 90일 공시 지연)
  · 이중클래스는 회사당 하나(GOOGL·FOXA·NWSA, 그 밖은 사전순 첫째) · 재배정 티커의 마지막 멤버월은 뺀다
  · 벤치 비중 = 시총가중 · 보유월 수익 = 다음 달 말 가격(달 중간 상장폐지는 마지막 가격)
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tech_backtest as TB            # noqa: E402  load_fund·asof_all
import pit_quarantine as PQ           # noqa: E402  격리 명단

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
KEEP_DUAL = {"GOOGL", "FOXA", "NWSA"}


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def load_world():
    """패널을 만드는 데 필요한 것 전부를 한 번 읽는다."""
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    D = len(dates)
    sector_now = {s["t"]: s.get("sector") for s in S["stocks"]}
    PX = {}
    for t in sector_now:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        PX[t] = np.array([np.nan if v is None else float(v) for v in d["pxd"]])
    slim = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    if slim.get("dates") != dates:
        raise SystemExit("🚨 pit_px.json 격자가 stocks.json 과 다르다")
    for t, obj in slim["px"].items():          # {i0, p} 압축 배열 — 격리 이름은 정리본에 이미 없다
        if t in PX or t in PQ.names():
            continue
        a = np.full(D, np.nan)
        i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
        for j, v in enumerate(arr):
            if v is not None and 0 <= i0 + j < D:
                a[i0 + j] = float(v)
        PX[t] = a
    PU = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    # 지수별 월말 명단 — 비는 달은 직전 달을 잇는다(NDX 2018-10~12 파싱 공백)
    lists = {"spx": {}, "ndx": {}}
    last = {"spx": [], "ndx": []}
    for m in sorted(H["months"]):
        row = H["months"][m] or {}
        for ix in ("spx", "ndx"):
            if row.get(ix):
                last[ix] = [x.replace(".", "-") for x in row[ix]]
            lists[ix][m] = list(last[ix])
    return {"dates": dates, "D": D, "PX": PX, "sector_now": sector_now, "today": set(sector_now),
            "splice": PU.get("cik_spliced") or {},
            "reassigned": (json.load(io.open(os.path.join(DATA, "pit_reuse.json"), encoding="utf-8"))
                           .get("reassigned") or {}),
            "meta": json.load(io.open(os.path.join(DATA, "index_ledger.json"), encoding="utf-8")).get("meta") or {},
            "cikmap": H.get("cik") or {},
            "FUND": TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")]),
            "me": me, "lists": lists}


def _key(W, t, i=None):
    """명단 티커 → 가격 계열 키.

    🚨 2026-09-24 정정 — 결함 둘(PREREG-2026-09-24-RALLY 결과 §0 에서 찾았다):
      ① 점 표기 — 명단은 `BRK-B`·`BF-B`(load_world 가 '.'→'-' 로 바꾼다)인데 가격 키는 `BRK.B`·`BF.B` 라
         버크셔·브라운포먼이 **전 기간** 빠졌다 → 점 표기도 찾는다.
      ② 티커 재사용 — pit_px.json 의 `FB` 는 2025-06-26 부터의 **다른 증권**(39~46달러 · 같은 날 메타 700달러대)이다.
         키가 그것을 먼저 잡아 `FB → META`(cik_spliced)가 안 걸렸고, 메타가 2014~2022 명단에서 빠졌다
         → 날짜 i 를 주면 **그날 가격이 선 후보**를 고른다(명단 티커 → 점 표기 → cik_spliced 차례).
    i 를 안 주면 있는 첫 후보다(종전과 같은 뜻 — 날짜를 모르는 호출용).
    """
    cands = []
    for c in (t, t.replace("-", "."), W["splice"].get(t)):
        if c and c in W["PX"] and c not in cands:
            cands.append(c)
    if not cands:
        return None
    if i is not None:
        for c in cands:
            v = W["PX"][c][i]
            if v == v and v > 0:
                return c
    return cands[0]


def union_members(W, mm, i):
    """그달 말 명단 S&P 500 ∪ NASDAQ 100 → [(명단 티커, 가격 키)] · 명단 수(이중클래스 하나로 줄인 뒤).

    2026-09-24 추가(TTEMPLATE·STOPLOSS 가 같이 쓴다 — 사본을 두지 않는다). 규칙은 month_rows 와 같다:
    이중클래스 회사당 하나(KEEP_DUAL · 그 밖은 사전순 첫째) · 재배정 티커의 마지막 멤버월 제외 · 날짜 인식 키.
    """
    mem = set(W["lists"]["spx"].get(mm) or []) | set(W["lists"]["ndx"].get(mm) or [])
    by_cik = {}
    for t in mem:
        c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
        by_cik.setdefault(c or ("_" + t), []).append(t)
    keep = []
    for c, ts in by_cik.items():
        if len(ts) == 1 or c.startswith("_"):
            keep.extend(ts)
            continue
        k_ = [t for t in ts if t in KEEP_DUAL]
        keep.append(k_[0] if k_ else sorted(ts)[0])
    out = []
    for t in sorted(keep):
        if t in W["reassigned"] and mm >= W["reassigned"][t].get("last", "9999"):
            continue
        k = _key(W, t, i)
        if k is not None:
            out.append((t, k))
    return out, len(keep)


def _sector(W, t, k):
    s = W["sector_now"].get(k) or W["sector_now"].get(t)
    if s:
        return s
    m = W["meta"].get(t) or W["meta"].get(k)
    return m[1] if (m and len(m) > 1) else "?"


def _shares(W, t, k, d):
    for c in (k, t):
        f = W["FUND"].get(c) or {}
        sh = f.get("sh")
        if sh:
            obs = TB.asof_all(sh, d)
            if obs and obs[0][1]:
                return obs[0][1]
    return None


def month_rows(W, ix, sig_months, end):
    """신호월 목록 → 행 목록. 행 = {m(보유월), names, wb, sec, r, key}. Z·cov 는 부르는 쪽이 붙인다.

    반환 (rows, cover) — cover 는 달마다 «명단 중 가격·주식수가 선 비율».
    """
    PX, dates, me = W["PX"], W["dates"], W["me"]
    rows, cover = [], []
    for mm in sorted(sig_months):
        mm1 = mshift(mm, 1)
        if mm not in me or mm1 not in me or mm1 > end:
            continue
        i, i1 = me[mm], me[mm1]
        mem = W["lists"][ix].get(mm) or []
        by_cik = {}
        for t in mem:
            c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = set()
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                keep.update(ts)
                continue
            k_ = [t for t in ts if t in KEEP_DUAL]
            keep.add(k_[0] if k_ else sorted(ts)[0])
        mc, r, sec, kk = {}, {}, {}, {}
        for t in sorted(keep):
            k = _key(W, t, i)                     # 🚨 날짜를 준다 — 그날 가격이 선 후보(재사용 티커 · 2026-09-24 정정)
            if k is None or not (PX[k][i] == PX[k][i]) or PX[k][i] <= 0:
                continue
            if t in W["reassigned"] and mm >= W["reassigned"][t].get("last", "9999"):
                continue
            sh = _shares(W, t, k, dates[i])
            if not sh or sh <= 0:
                continue
            p = PX[k]
            seg = p[i + 1:i1 + 1]
            ok = np.where(seg == seg)[0]
            mc[t] = p[i] * sh
            r[t] = (seg[ok[-1]] / p[i] - 1) if len(ok) else 0.0
            sec[t] = _sector(W, t, k)
            kk[t] = k
        cover.append(len(mc) / max(1, len(keep)))
        if len(mc) < 40:
            continue
        zsum = sum(mc.values())
        wb = {t: mc[t] / zsum for t in mc}
        rows.append({"m": mm1, "sig": mm, "names": sorted(wb), "wb": wb, "sec": sec, "r": r, "key": kk})
    return rows, cover


def f0_gate(rows, idx_monthly, bench_name, judge):
    """패널 관문 — 패널 시총가중 벤치 대 지수(PR) 월간 상관·평균 차이. IDXEG 와 같은 문턱."""
    bm = idx_monthly.get(bench_name) or {}
    pairs = [(sum(x["wb"][t] * x["r"][t] for t in x["names"]) * 100, bm[x["m"]]) for x in rows
             if x["m"] in bm and judge[0] <= x["m"] <= judge[1]]
    corr = float(np.corrcoef([a for a, b in pairs], [b for a, b in pairs])[0, 1])
    gap = float(np.mean([a - b for a, b in pairs]))
    return bool(corr >= 0.98 and abs(gap) <= 0.30), corr, gap
