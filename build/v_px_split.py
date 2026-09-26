# -*- coding: utf-8 -*-
"""build/v_px_split.py — 배치 V 시총 규칙: V-D1(분할만 조정 종가) 받기 · 핀 · «그날 기준 가격 × 그날 기준 주식수» · 분할/분사 가르기 · 앵커 대조.

설계 원본(구속): vbatch_research.json final.data_plan.market_cap_rule(🚨 비평 1 C3 · SHARES2 결함 ② 재발 방지) · D04.
  ME_t = P_raw(t) × S_filed × Π_{실제 분할 e ∈ (d_s, t]} q_e
    P_raw(t) = V-D1 종가(yfinance auto_adjust=False Close · 분할 · 분사 조정) × Π_{야후 사건 e > t} r_e(분할 · 분사 모두 — 야후는 분사도 과거 가격을 r 로 낮춘다)
    편출 이름: data/_px_raw.json(사내 DB «지수에 있던 날» 원 종가 · 분할만 되맞춤 · 기준 = 그 이름 마지막 재적일)은 그 기준의 분할(basis.splits)만 되돌린 값을
      P_raw 로 쓴다(그 파일에 분할이 있는 키는 CELG 하나 — 나머지는 «그대로»).
    S_filed = v_fund.shares_at(최초 제출 · 가용일 ≤ t) · d_s = 그 기록의 filed(분할이 기간말과 제출 사이면 공시는 분할 뒤 기준 — SAB 4C · 선언).
    분할/분사 판별 = tech_backtest.split_kinds(tech_backtest.py:3210 — splits 의 절반 가까이가 분사) · q = 주식수가 실제로 바뀐 배수(실제 = r · 섞임 = 지정 · 분사형 = 1).
  이중클래스: 회사당 한 줄(pit_panel.union_members) · 그 줄의 시총 = 회사 원장 주식수(두 클래스 합으로 공시) × 그 줄 가격 — 명세의 «GOOGL/GOOG 같은 계열 주식수
    반씩»(SHARES2 §3)은 두 줄이 같은 계열을 들 때의 이중 계상 막기이고, 한 줄뿐인 이 우주에서 반으로 나누면 회사가 반만 들어간다 → 나누지 않는다(🔎 선언 · 오케스트레이터 확인 요청).
    버크셔는 원장이 A주 환산 주식수라 B주 가격에 ×1500(v_fund.SHARE_CLASS_FACTOR · 선언).
  대체(fallback): V-D1 이 이름에 서지 않고 _px_raw 도 없으면 조정 가격(랩 가격 계열) × 오늘(계열 끝) 기준 주식수(배당 수준 선견 · 공개) — 그 이름의 시총 몫을 달마다 보고
    (5% 넘는 달이 있으면 VAL «잠정» · 판정은 v_pit.coverage).
  앵커(F0 · 자료 타당성 · 수익 아님): shares_split.ANCHOR 가운데 명세가 적은 9개(AAPL 2021-11 · NVDA 2024-05 · MSFT 2021-11 · AMZN 2021-06 · TSLA 2021-11 ·
    WMT 2019-06 · JNJ 2017-10 · KO 2019-06 · GE 2017-10) + GE 2022-12 ≈ 91B$ — 각 |ME/알려진 값 − 1| ≤ 0.10 그리고 평균 절대오차 ≤ 0.05. 실패면 굽지 않고 고친다.
    ANCHOR 의 나머지(XOM 2014-12 · GOOGL 2026-04)는 보고만(관문 밖). 🔧 검토 고침(등록 전): 알려진 값은 V 소유 표(anchor_table — ANCHOR 사본 +
    JNJ · GE 2017-10 두 칸을 SEC 10-Q 표지 발행주식수 × NYSE 월말 원 종가로 고침 · ANCHOR_REPAIRS 에 출처) · 공유 표 shares_split.ANCHOR 는 고치지 않는다.

🚨 수익 · 신호-수익 통계를 계산하지 않는다(시총 · 사건 · 커버리지뿐). V-D1 원자료는 저장소 밖 캐시(raw/vd1)에만 · 명세에는 해시 · 행 수 · 기간만.

  python build/v_px_split.py --selftest
  python build/v_px_split.py --fetch-vd1 [--limit N]   현재 이름(stocks.json 518종)의 V-D1 받기(있으면 그대로 · 초당 ≤ 2)
  python build/v_px_split.py --anchors                 앵커 대조(시총 · 조 달러 · 오차만)
"""
from __future__ import annotations

import bisect
import io
import json
import math
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_data as VD          # noqa: E402

ANCHOR_GATE = [("AAPL", "2021-11"), ("NVDA", "2024-05"), ("MSFT", "2021-11"), ("AMZN", "2021-06"), ("TSLA", "2021-11"),
               ("WMT", "2019-06"), ("JNJ", "2017-10"), ("KO", "2019-06"), ("GE", "2017-10")]
ANCHOR_EXTRA = [("GE", "2022-12", 0.091)]              # split_kinds 주석(GE 2022-12 ≈ 91B$ · 분사 배수 두 개)
ANCHOR_TOL, ANCHOR_MAE = 0.10, 0.05
# 🔧 V 소유 앵커 표(검토 고침 · 등록 전 · 명세 data_plan.anchor_check «실패면 굽지 않고 고친다»): shares_split.ANCHOR(출처 표기 없음)를 그대로 옮기되
#   두 칸만 출처 있는 월말 값으로 고친다 — 공유 표(shares_split.py)는 고치지 않는다. 알려진 값 = 회사가 SEC 에 낸 10-Q 표지 발행주식수(원 숫자) ×
#   NYSE 2017-10-31 공식 종가(분할 · 분사 조정 전 원 종가 — 공개 시세 · V-D1 P_raw 와 같은 값). 옛 값 JNJ 0.44 · GE 0.20 은 그달 말 값이 아니다
#   (JNJ 0.44조$ 는 2017 년에 닿은 적이 없고 · GE 0.20 은 10월 초 주가 약 $23 수준). 🔎 종가가 V-D1 과 같은 원천일 수 있어 완전히 독립은 아니다 — 공개.
ANCHOR_REPAIRS = {
    ("JNJ", "2017-10"): (0.3745, "SEC 10-Q(2017 Q3 · 접수번호 0000200406-17-000052 · 2017-11-02 제출) 표지 발행주식수 2,686,520,050주(2017-10-27 기준) × "
                                 "NYSE 2017-10-31 종가 $139.41 = 374.5B$ · 옛 표 0.44"),
    ("GE", "2017-10"): (0.1748, "SEC 10-Q(2017 Q3 · 접수번호 0000040545-17-000073 · 2017-10-30 제출) 표지 발행주식수 8,672,085,000주(2017-09-30 기준) × "
                                "NYSE 2017-10-31 종가 $20.16(분할 · 분사 조정 전) = 174.8B$ · 옛 표 0.20"),
}


def anchor_table():
    """V 소유 앵커 표 — [(티커, 달, 알려진 조$, 출처 · 고침 표지)] · shares_split.ANCHOR 사본 + ANCHOR_REPAIRS 두 칸."""
    import shares_split as SS                                   # 허용 목록 — ANCHOR 표만 읽는다
    out = []
    for t, m, v in SS.ANCHOR:
        if (t, m) in ANCHOR_REPAIRS:
            nv, why = ANCHOR_REPAIRS[(t, m)]
            out.append((t, m, nv, {"repaired": True, "spec_T": v, "source": why}))
        else:
            out.append((t, m, v, {"repaired": False, "spec_T": v, "source": "shares_split.ANCHOR(명세 값 그대로)"}))
    return out


def vd1_dir():
    return os.path.join(VD.cache_guard(), "raw", "vd1")


def yahoo_symbol(tk):
    return tk.replace(".", "-")


def vd1_path(tk):
    return os.path.join(vd1_dir(), tk.replace("^", "_") + ".csv")


def current_tickers():
    S = VD.read_json(VD.lab_path("data/stocks.json"))
    return [s["t"] for s in S["stocks"]]


def fetch_vd1(tickers=None, limit=None, sleep=0.5):
    """V-D1 — yfinance history(period='max', auto_adjust=False, actions=True) 의 Close · Dividends · Stock Splits 를 캐시에(있으면 그대로 · 판 동결)."""
    import yfinance as yf
    tickers = tickers or current_tickers()
    got, skip, fail = 0, 0, []
    idx_p = os.path.join(vd1_dir(), "_index.json")
    idx = VD.read_json(idx_p) if os.path.exists(idx_p) else {"files": {}}
    for j, tk in enumerate(tickers):
        if limit is not None and got >= limit:
            break
        p = vd1_path(tk)
        if os.path.exists(p) and tk in idx["files"]:
            skip += 1
            continue
        try:
            df = yf.Ticker(yahoo_symbol(tk)).history(period="max", auto_adjust=False, actions=True)
            if df is None or df.empty:
                raise RuntimeError("빈 응답")
            ix = pd.to_datetime(df.index)
            if ix.tz is not None:
                ix = ix.tz_localize(None)
            df.index = ix.normalize()
            df.index.name = "Date"
            cols = [c for c in ("Close", "Dividends", "Stock Splits") if c in df.columns]
            txt = df[cols].to_csv(date_format="%Y-%m-%d", float_format="%.10g", lineterminator="\n").encode("utf-8")
            VD._write_bytes(p, txt)
            idx["files"][tk] = {"sha256": VD.sha256_bytes(txt), "rows": int(len(df)), "first": str(df.index.min().date()),
                                "last": str(df.index.max().date()), "fetched_at": VD._now(), "yfinance": getattr(yf, "__version__", "?")}
            got += 1
        except Exception as e:
            fail.append((tk, type(e).__name__))
        if (j + 1) % 25 == 0:
            VD._write_bytes(idx_p, json.dumps(idx, ensure_ascii=False, indent=0).encode("utf-8"))
        time.sleep(sleep)
    VD._write_bytes(idx_p, json.dumps(idx, ensure_ascii=False, indent=0).encode("utf-8"))
    return {"got": got, "skip": skip, "fail": fail}


def vd1_manifest():
    """공개 명세 칸 — 받은 이름 수 · 묶음 해시 · 기간 범위(값 없음)."""
    p = os.path.join(vd1_dir(), "_index.json")
    if not os.path.exists(p):
        return {"state": "V-D1 없음 — python build/v_px_split.py --fetch-vd1"}
    idx = VD.read_json(p)
    lines = "".join("%s\t%s\n" % (k, v["sha256"]) for k, v in sorted(idx["files"].items()))
    fe = sorted(v["fetched_at"] for v in idx["files"].values())
    return {"n": len(idx["files"]), "digest": VD.sha256_bytes(lines.encode("utf-8")), "fetched_first": fe[0] if fe else None,
            "fetched_last": fe[-1] if fe else None, "source": "yfinance history(period='max', auto_adjust=False, actions=True) · Close · Dividends · Stock Splits",
            "license": "yfinance: 개인 사용 — 캐시만(D1)", "rule": "sha256(«티커 \\t sha256 \\n» 을 티커 차례로)"}


_VD1 = {}


def load_vd1(tk):
    if tk not in _VD1:
        p = vd1_path(tk)
        if not os.path.exists(p):
            _VD1[tk] = None
        else:
            df = pd.read_csv(p, index_col=0)
            df.index = pd.DatetimeIndex(pd.to_datetime(df.index, format="%Y-%m-%d"))
            _VD1[tk] = df.sort_index()
    return _VD1[tk]


def yahoo_events(df):
    """야후 «Stock Splits» 사건 [(날짜, r)] — r > 0 · r ≠ 1 (분할 · 분사 모두 · 야후가 과거 가격을 r 로 나눈 사건)."""
    if df is None or "Stock Splits" not in df.columns:
        return []
    s = df["Stock Splits"]
    s = s[(s > 0) & (np.abs(s - 1.0) > 1e-12)]
    return [(d.strftime("%Y-%m-%d"), float(r)) for d, r in s.items()]


def p_raw_on_grid(df, grid, events=None):
    """V-D1 종가를 격자(날짜 문자열 목록)에 맞춘 원 가격 — P_raw(t) = Close(t) × Π_{e > t} r_e. 격자 날에 값이 없으면 NaN."""
    if df is None:
        return None
    ev = yahoo_events(df) if events is None else events
    c = df["Close"].reindex(pd.DatetimeIndex(pd.to_datetime(grid))).to_numpy(float)
    f = np.ones(len(grid))
    for d, r in ev:
        j = bisect.bisect_right(grid, d)                         # 사건일 이전(< d) 격자 날짜들 = 0..j−1 에서 사건일 당일은 이미 분할 뒤 가격
        jj = bisect.bisect_left(grid, d)
        f[:jj] *= r
    return c * f


def raw_db_on_grid(key, grid, RAW=None):
    """_px_raw.json(사내 DB 원 종가 · 분할만 되맞춤) → 격자 위 원 가격(basis.splits 를 되돌린다 — 사건일 앞 날에 r 을 곱한다)."""
    R = RAW if RAW is not None else _raw_db()
    obj = (R.get("px") or {}).get(key)
    if not obj:
        return None
    if R.get("dates") != grid:
        raise SystemExit("🚨 _px_raw.json 격자가 가격 격자와 다르다")
    a = np.full(len(grid), np.nan)
    i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
    for j, v in enumerate(arr):
        if v is not None and 0 <= i0 + j < len(grid):
            a[i0 + j] = float(v)
    for d, r in ((R.get("basis") or {}).get(key) or {}).get("splits") or []:
        jj = bisect.bisect_left(grid, d)
        a[:jj] *= float(r)
    return a


_RAWDB = None


def _raw_db():
    global _RAWDB
    if _RAWDB is None:
        _RAWDB = VD.read_json(VD.lab_path("data/_px_raw.json"))
    return _RAWDB


def split_share_events(tk, events, sec):
    """사건 → 주식수 배수 [(날짜, q)] — tech_backtest.split_kinds 로 실제 · 섞임 · 분사형을 가른다(분사형 q = 1 은 싣지 않는다).
    sec = SEC 주식수 계열(날짜 내림차순 [(날짜, 값)] · v_fund.sec_share_series)."""
    if not events:
        return []
    import tech_backtest as TB                                   # 허용 목록(may_import) — 함수 안 · G-NoEG 전이 점검 대상
    out = []
    for k in TB.split_kinds(tk, events, sec):
        if k["kind"] in ("real", "mixed") and k["q"] and abs(float(k["q"]) - 1.0) > 1e-12:
            out.append((k["s"], float(k["q"])))
    return out


def me_value(p_raw, shares, basis, d, share_events):
    """ME = P_raw × S × Π_{e ∈ (basis, d]} q_e — 순수 함수(백만 달러 × 백만 주 단위면 백만 달러). 값이 없으면 None."""
    if p_raw is None or not (p_raw == p_raw) or p_raw <= 0 or not shares or shares <= 0:
        return None
    f = 1.0
    for s, q in share_events:
        if basis < s <= d:
            f *= q
    return float(p_raw) * float(shares) * f


# ══════════════════════════════════════════════════════════════════════════
#  앵커 대조(F0 · 자료 타당성)
# ══════════════════════════════════════════════════════════════════════════
def anchors(U=None):
    """앵커 대조 — {rows: [(티커, 달, 알려진 조$, 계산 조$, 오차, 방법)], gate_ok, mae, repairs} · U = v_pit.Universe(없으면 실자료로 짓는다).
    알려진 값은 V 소유 표(anchor_table — shares_split.ANCHOR 사본 + 출처 있는 두 칸 고침)."""
    if U is None:
        import v_pit as VP
        U = VP.Universe.real()
    tab = anchor_table()
    known = {(t, m): v for t, m, v, _ in tab}
    meta = {(t, m): mt for t, m, _, mt in tab}
    rows = []
    for t, m in ANCHOR_GATE:
        rows.append((t, m, known[(t, m)], "gate"))
    for t, m, v in ANCHOR_EXTRA:
        rows.append((t, m, v, "gate"))
    for t, m, v, _ in tab:
        if (t, m) not in ANCHOR_GATE:
            rows.append((t, m, v, "report"))
    out, errs, errs_sec = [], [], []
    for t, m, v, kind in rows:
        me, how = U.me_of_ticker(t, m)
        val = me / 1e6 if me else None
        e = (val / v - 1.0) if val else None
        ref = sec_reference(U, t, m)
        es = (val / ref["T"] - 1.0) if (val and ref and ref.get("T")) else None
        mt = meta.get((t, m)) or {"repaired": False, "spec_T": v}
        out.append({"t": t, "m": m, "known_T": v, "calc_T": None if val is None else round(val, 4), "err": None if e is None else round(e, 4),
                    "how": how, "kind": kind, "sec_ref_T": None if not ref else round(ref["T"], 4), "sec_ref_asof": None if not ref else ref["asof"],
                    "err_vs_sec": None if es is None else round(es, 4), "repaired": bool(mt.get("repaired")), "spec_T": mt.get("spec_T")})
        if kind == "gate":
            errs.append(e)
            errs_sec.append(es)
    ok = all(e is not None and abs(e) <= ANCHOR_TOL for e in errs)
    mae = float(np.mean([abs(e) for e in errs])) if all(e is not None for e in errs) else None
    ok_s = all(e is not None and abs(e) <= ANCHOR_TOL for e in errs_sec)
    mae_s = float(np.mean([abs(e) for e in errs_sec])) if all(e is not None for e in errs_sec) else None
    return {"rows": out, "gate_ok": bool(ok and mae is not None and mae <= ANCHOR_MAE), "mae": None if mae is None else round(mae, 4),
            "sec_ref_ok": bool(ok_s and mae_s is not None and mae_s <= ANCHOR_MAE), "sec_ref_mae": None if mae_s is None else round(mae_s, 4),
            "repairs": [{"t": t, "m": m, "known_T": v, "spec_T": mt["spec_T"], "source": mt["source"]} for t, m, v, mt in tab if mt["repaired"]],
            "table": "v_px_split.anchor_table(shares_split.ANCHOR 사본 + ANCHOR_REPAIRS)"}


def sec_reference(U, t, m, max_days=75):
    """앵커 참고값(관문 밖 · 보고만) — 표지 주식수(dei:EntityCommonStockSharesOutstanding · 원 companyfacts 핀 사본 · 기준일이 그달 말에 가장 가까운 것 ·
    ±75일) × 그달 말 원 가격(P_raw) · 조 달러. 클래스별 공시(알파벳 등)는 합이 아니라 첫 값이라 참고가 되지 않는다(표시만)."""
    import v_fund as VF
    row = next((r for r in U.members(m) if r["t"] == t or r["k"] == t), None)
    if row is None or not row["gid"]:
        return None
    G = VF.group_ciks_map().get(row["gid"]) if not hasattr(U, "_gcm") else U._gcm.get(row["gid"])
    if not G:
        return None
    prim = next((c for c, s, e, role in G["ciks"] if role == "primary"), None)
    p = os.path.join(VF.raw_dir(), "CIK%010d.json.gz" % prim) if prim else None
    if not p or not os.path.exists(p):
        return None
    facts = VD.read_json(p)
    recs = ((((facts.get("facts") or {}).get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}).get("units") or {}).get("shares") or []
    i = U.me_idx[m]
    d = U.dates[i]
    best = None
    for r in recs:
        if not r.get("end"):
            continue
        gap = abs((pd.Timestamp(r["end"]) - pd.Timestamp(d)).days)
        if gap <= max_days and (best is None or gap < best[0] or (gap == best[0] and r["filed"] < best[1]["filed"])):
            best = (gap, r)
    if best is None:
        return None
    k = row["k"]
    pr = U.vd1[k][i] if k in U.vd1 else (U.rawdb[k][i] if k in U.rawdb else None)
    if pr is None or not (pr == pr):
        return None
    f = VF.SHARE_CLASS_FACTOR.get(row["gid"], 1.0)
    return {"T": float(pr) * float(best[1]["val"]) * f / 1e12, "asof": best[1]["end"]}


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
def _st_rule():
    grid = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2020-01-01", "2020-12-31")]
    raw = np.linspace(100.0, 200.0, len(grid))
    ev = [("2020-06-01", 4.0), ("2020-09-01", 1.25)]             # 4:1 분할 · 분사형(r 1.25)
    f = np.ones(len(grid))
    for d, r in ev:
        f[:bisect.bisect_left(grid, d)] /= r
    df = pd.DataFrame({"Close": raw * f, "Dividends": 0.0, "Stock Splits": 0.0}, index=pd.DatetimeIndex(pd.to_datetime(grid)))
    for d, r in ev:
        df.loc[pd.Timestamp(d), "Stock Splits"] = r
    pr = p_raw_on_grid(df, grid)
    assert np.allclose(pr, raw, rtol=1e-12), "P_raw 가 원 가격을 되살리지 못한다"
    # 주식수: 분할만(분사형은 q = 1) — 기준일 뒤 · d 까지의 분할만 곱한다
    se = [("2020-06-01", 4.0)]
    i = grid.index("2020-07-01")
    me = me_value(pr[i], 10.0, "2020-05-10", grid[i], se)
    assert abs(me - raw[i] * 40.0) < 1e-9
    assert abs(me_value(pr[i], 40.0, "2020-06-15", grid[i], se) - raw[i] * 40.0) < 1e-9          # 제출이 분할 뒤면 곱하지 않는다
    j = grid.index("2020-03-02")
    assert abs(me_value(pr[j], 10.0, "2020-02-10", grid[j], se) - raw[j] * 10.0) < 1e-9          # d 뒤 분할은 곱하지 않는다(선견 없음)
    # 선견 — d 뒤 사건을 흔들고 종가를 그에 맞춰 다시 지어도(야후 방식) ME_d 는 같다
    ev2 = [("2020-06-01", 4.0), ("2020-09-01", 3.7)]
    f2 = np.ones(len(grid))
    for d, r in ev2:
        f2[:bisect.bisect_left(grid, d)] /= r
    df2 = df.copy()
    df2["Close"] = raw * f2
    df2.loc[pd.Timestamp("2020-09-01"), "Stock Splits"] = 3.7
    k = grid.index("2020-08-03")
    assert abs(p_raw_on_grid(df2, grid)[k] - pr[k]) < 1e-9
    df3 = df.copy()
    df3["Dividends"] = np.random.default_rng(1).uniform(0, 2, len(df3))                            # 배당 계수를 난수로 — ME 불변
    assert np.allclose(p_raw_on_grid(df3, grid), pr)
    assert yahoo_events(df) == [("2020-06-01", 4.0), ("2020-09-01", 1.25)]
    return "P_raw = Close × Π(뒤 사건 r) 가 원 가격 복원 · 분할만 주식수(분사형 제외) · 기준일 뒤 · d 까지 · 뒤 사건 흔들기 · 배당 난수 불변"


def _st_rawdb():
    grid = ["2014-06-24", "2014-06-25", "2014-06-26", "2014-06-27"]
    R = {"dates": grid, "px": {"X": {"i0": 1, "p": [50.0, 51.0, 52.0]}}, "basis": {"X": {"splits": [["2014-06-26", 2.0]]}}}
    a = raw_db_on_grid("X", grid, R)
    assert np.isnan(a[0]) and a[1] == 100.0 and a[2] == 51.0 and a[3] == 52.0
    try:
        raw_db_on_grid("X", grid[:3], R)
        raise AssertionError("격자 불일치가 통과했다")
    except SystemExit:
        pass
    return "_px_raw 원 종가(기준 분할 되돌림) · 격자 불일치 멈춤"


def _st_anchor_table():
    import shares_split as SS
    tab = anchor_table()
    rep = [(t, m) for t, m, v, mt in tab if mt["repaired"]]
    assert rep == [("GE", "2017-10"), ("JNJ", "2017-10")] or sorted(rep) == [("GE", "2017-10"), ("JNJ", "2017-10")]
    sp = {(t, m): v for t, m, v in SS.ANCHOR}
    assert all(v == sp[(t, m)] for t, m, v, mt in tab if not mt["repaired"]) and len(tab) == len(SS.ANCHOR)
    assert abs(ANCHOR_REPAIRS[("JNJ", "2017-10")][0] - 2686520050 * 139.41 / 1e12) < 5e-5 and abs(ANCHOR_REPAIRS[("GE", "2017-10")][0] - 8672085000 * 20.16 / 1e12) < 5e-5
    return "V 소유 앵커 표: shares_split.ANCHOR 사본 + 출처 있는 두 칸(JNJ · GE 2017-10 · 표지 주식수 × 원 종가 손 계산) · 나머지는 명세 값 그대로"


def _st_kinds():
    ev = [("2021-01-04", 4.0), ("2022-01-03", 1.281)]
    sec = [("2021-06-01", 400.0), ("2020-12-01", 100.0), ("2021-12-01", 400.0), ("2022-06-01", 400.0)]
    sec = sorted(sec, reverse=True)
    se = split_share_events("ZZZ", ev, sec)
    assert se == [("2021-01-04", 4.0)], se
    return "split_kinds: 정확한 비율 = 실제 분할(q = r) · 비정수 비율(주식수 불변) = 분사형 → 주식수에 곱하지 않는다"


def selftest():
    res, ok = [], True
    for fn in (_st_rule, _st_rawdb, _st_kinds, _st_anchor_table):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_px_split selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--fetch-vd1" in sys.argv:
        lim = None
        if "--limit" in sys.argv:
            lim = int(sys.argv[sys.argv.index("--limit") + 1])
        r = fetch_vd1(limit=lim)
        print("V-D1 받음 %d · 있음 %d · 실패 %d %s" % (r["got"], r["skip"], len(r["fail"]), r["fail"][:10]))
    if "--anchors" in sys.argv:
        a = anchors()
        for r in a["rows"]:
            print("  %-6s %s 알려진 %.3f · 계산 %s · 오차 %s · %s · %s · SEC 표지 참고 %s(%s) · 참고 대비 %s" % (
                r["t"], r["m"], r["known_T"], r["calc_T"], r["err"], r["how"], r["kind"], r["sec_ref_T"], r["sec_ref_asof"], r["err_vs_sec"]))
        print("앵커 관문(V 소유 표 · shares_split.ANCHOR + 두 칸 고침): %s · 평균 절대오차 %s" % ("통과" if a["gate_ok"] else "실패", a["mae"]))
        print("참고(SEC 표지 주식수 × 원 가격 · 관문 밖): %s · 평균 절대오차 %s" % ("통과" if a["sec_ref_ok"] else "실패", a["sec_ref_mae"]))
    if len(sys.argv) <= 1:
        print(__doc__)
