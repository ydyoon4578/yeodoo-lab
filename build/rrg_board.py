# -*- coding: utf-8 -*-
"""build/rrg_board.py — 종목 RRG 판 자료 → data/rrg_board.json

사전등록: build/PREREG-2026-09-23-RRGSTOCK.md (계산 전 커밋 064bdb29)

무엇을. 518종(= explorer 202개 전략 보유의 합집합, 실측 일치)을 S&P 500(PR) 대비 **주간**
  RRG 로 놓는다. 산식은 build/rrg.py 의 rrg_axes() 그대로다 — 되돌아보기 12(여기선 주)·컷 100.
  판은 지난 52주 궤적을 싣고, 화면이 꼬리 길이와 날짜를 고른다.

🚨 **판정은 여기서 내지 않는다.** 검정은 build/rrg_stock.py 가 **한 번** 했고
   (data/_rrg_stock.json), 이 빌더는 그 판정을 옮겨 적기만 한다. 매일 도는 이 스크립트가
   검정까지 다시 하면 판정이 날마다 조용히 바뀔 수 있다 — 그건 사전등록이 아니다.
🚨 **부분 주는 뺀다.** Mom 축이 1주 차분이라 이틀짜리 주를 넣으면 그 한 점만 다른 잣대가
   된다(사전등록 §1). 금요일로 끝났거나 그 뒤에 날짜가 더 있는 주만 «완전한 주» 다.

  python build/rrg_board.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "rrg_board.json")
TEST = os.path.join(DATA, "_rrg_stock.json")

LOOK = 12            # 되돌아보기(주) — 사전등록 고정. build/rrg.py 의 LOOK 과 같은 수
CUT = 100.0          # 4분면 컷 — 사전등록 고정
HIST = 52            # 판에 싣는 지난 주 수(현재 주 포함 53점). 화면용 — 검정과 무관
Q = ["회복", "주도", "약화", "부진"]      # 시계 방향 차례 — rrg.py 와 같은 정의
QEN = {"회복": "Improving", "주도": "Leading", "약화": "Weakening", "부진": "Lagging"}


def load_daily(bench="spx"):
    """랩 일간 격자 → (종목 종가 DataFrame, 벤치 Series, 메타). 새로 받지 않는다.

    bench — bench_px.json 의 계열 키(spx · ndx). ⚠ 기본값을 바꾸지 말 것: 얼린 검정(rrg_stock.py)이
    인자 없이 불러 S&P 500 판을 받는다.
    """
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = pd.to_datetime(S["pxd_dates"])
    cols, meta = {}, {}
    for s in S["stocks"]:
        t = s["t"]
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        px = d.get("pxd") or []
        if len(px) != len(dates):
            raise SystemExit("🚨 %s: pxd %d칸 ≠ pxd_dates %d칸 — 격자가 어긋났다" % (t, len(px), len(dates)))
        cols[t] = [np.nan if v is None else float(v) for v in px]
        meta[t] = {"name": s.get("name") or t, "sector": s.get("sector") or "—",
                   "idx": s.get("idx") or []}
    P = pd.DataFrame(cols, index=dates)
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    b = pd.Series([np.nan if v is None else float(v) for v in B["series"][bench]["px"]],
                  index=pd.to_datetime(B["dates"]))
    # 벤치를 종목 격자에 맞춘다. 벤치에만 없는 날은 앞 값을 잇는다(holes 0 이 정상).
    b = b.reindex(P.index).ffill()
    return P, b, meta, S.get("as_of")


def weekly(P, b):
    """각 주(월~금)의 **마지막 거래일** 행을 뽑는다. 부분 주(마지막 주가 금요일 전에 끝남)는 뺀다."""
    key = P.index.to_period("W-FRI")
    last = pd.Series(P.index, index=P.index).groupby(key).max()
    idx = pd.DatetimeIndex(last.values)
    partial = None
    if len(idx) and idx[-1].weekday() != 4:
        # 데이터가 금요일 전에 끝났다 — 이번 주는 아직 안 끝났다
        partial = idx[-1]
        idx = idx[:-1]
    return P.loc[idx], b.loc[idx], partial


def rrg_np(rs):
    """상대강도 DataFrame(주 × 종목) → (RS-Ratio, RS-Mom). build/rrg.py rrg_axes() 의 numpy 판.

    rrg_axes 와 같은 규칙 — 창이 LOOK 칸 **꽉 찼을 때만** 값을 낸다(결측이 하나라도 있으면 NaN),
    표준편차는 표본(ddof=1), 표준편차가 0 이면 z 는 0.
    """
    m = rs.rolling(LOOK, min_periods=LOOK).mean()
    s = rs.rolling(LOOK, min_periods=LOOK).std(ddof=1)
    z = (rs - m) / s
    z = z.where(~(s <= 0), 0.0).where(m.notna())
    ratio = CUT + z
    d = ratio.diff()
    m2 = d.rolling(LOOK, min_periods=LOOK).mean()
    s2 = d.rolling(LOOK, min_periods=LOOK).std(ddof=1)
    z2 = (d - m2) / s2
    z2 = z2.where(~(s2 <= 0), 0.0).where(m2.notna())
    mom = CUT + z2
    return ratio, mom


def rel_from_returns(r, rb, mask):
    """주간 수익(종목 DataFrame, 벤치 Series) → 상대 NAV. 결측 주는 NAV 를 NaN 으로 둔다.

    rrg.py rel_from() 과 같은 뜻(누적 ÷ 누적). 결측 칸의 수익은 0 으로 잇되 그 칸의 값은 지운다 —
    셔플 귀무(rrg_stock.py)가 같은 함수를 써야 실제와 귀무가 같은 잣대가 된다.
    """
    f = (1.0 + r.fillna(0.0)).cumprod()
    g = (1.0 + rb.fillna(0.0)).cumprod()
    rel = 100.0 * f.div(g, axis=0)
    return rel.where(mask)


def quad_np(ratio, mom):
    """사분면 코드: 0 회복 · 1 주도 · 2 약화 · 3 부진 · -1 없음 (Q 의 순서와 같다)."""
    R, M = ratio.values, mom.values
    out = np.full(R.shape, -1, dtype=np.int8)
    ok = ~(np.isnan(R) | np.isnan(M))
    hi, up = R >= CUT, M >= CUT
    out[ok & hi & up] = 1
    out[ok & hi & ~up] = 2
    out[ok & ~hi & ~up] = 3
    out[ok & ~hi & up] = 0
    return out


def panel(bench="spx"):
    """검정(rrg_stock.py)과 판이 **같은** 주간 패널을 쓰게 한 곳에서 만든다(기본 = S&P 500 — 검정이 쓴 것)."""
    P, b, meta, asof = load_daily(bench)
    W, wb, partial = weekly(P, b)
    r = W.pct_change(fill_method=None)
    rb = wb.pct_change(fill_method=None)
    # 종목이 첫 가격을 갖기 전 칸은 수익이 없다 — 그 칸을 0 으로 이으면 상장 전이 «제자리» 가 된다
    mask = W.notna()
    rel = rel_from_returns(r, rb, mask)
    return {"P": P, "W": W, "wb": wb, "r": r, "rb": rb, "mask": mask, "rel": rel,
            "meta": meta, "asof": asof, "partial": partial}


WIDE = 100          # 이보다 많이 쥔 전략은 필터로 못 쓴다(유니버스 전체를 쥐는 전략이 있다)


def explorer_strategies():
    """explorer 가 싣는 전략 중 종목 명단을 가진 것 — 판의 «전략 보유만 보기» 필터용(보기용).

    ⚠ WIDE 종 넘게 쥔 전략은 뺀다. 518종 전부(동일가중 유니버스 등)를 쥔 것을 골라도 «전체» 와
      같은 그림이라 필터가 아니다. 뺀 수는 화면이 적는다(wide_n).
    """
    ix = json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))
    out, wide = [], 0
    for x in ix.get("items") or []:
        h = x.get("holdings") or {}
        tk = h.get("tickers") or []
        if not tk:
            continue
        if len(tk) > WIDE:
            wide += 1
            continue
        out.append({"sid": x.get("sid"), "name": x.get("name") or x.get("sid"),
                    "grade": x.get("grade"), "as_of": h.get("as_of"), "t": sorted(tk)})
    out.sort(key=lambda s: s["name"])
    return out, wide


# 🚨 2026-09-24 사용자 «rrg sp500이랑 나스닥100 따로 보여줘» — 판을 지수별로 나눈다.
#   각 판은 **그 지수의 구성 종목을 그 지수 대비로** 놓는다(NASDAQ 100 종목을 S&P 500 대비로 그리면
#   «나스닥 안에서 누가 앞서나» 가 아니라 «나스닥이 S&P 를 이기나» 가 섞인다). 산식·주·컷은 같다.
#   ⚠ 판정(_rrg_stock.json)은 518종 × S&P 500 대비 검정 **하나**다. NASDAQ 100 판은 따로 검정하지
#     않은 서술용 — 화면이 그렇게 적는다. 여기서 새로 재지 않는다.
MIN_SEC = 3          # 섹터 중앙값을 싣는 최소 종목 수(보기용)
BOARDS = (("spx", "SPX", "S&P 500", "S&P 500(PR)"),
          ("ndx", "NDX", "NASDAQ 100", "NASDAQ 100(PR)"))


def enc(v):
    # 100 기준 편차 × 100 을 정수로 — 파일을 줄인다(화면이 100 + v/100 으로 되돌린다).
    # 🚨 반올림이 아니라 **내림**이다. 반올림하면 99.996 이 0 이 되어 화면이 «100 이상» 으로
    #   읽는다 — 부진·회복이 약화·주도로 넘어간다. 내림은 부호(= 사분면)를 늘 지킨다.
    return None if (v is None or v != v) else int(math.floor((v - CUT) * 100))


def board(pn, member, sidx, sectors, lo):
    """한 지수 판 — pn 은 그 지수 대비 패널, member 는 구성 종목(오늘 명단)."""
    ratio, mom = rrg_np(pn["rel"])
    q = quad_np(ratio, mom)
    W, meta = pn["W"], pn["meta"]
    n = len(W.index)
    rows, cnt = [], {k: 0 for k in Q}
    for j, t in enumerate(W.columns):
        if t not in member:
            continue
        xs = [enc(v) for v in ratio[t].values[lo:]]
        ys = [enc(v) for v in mom[t].values[lo:]]
        qc = int(q[n - 1, j])
        if qc >= 0:
            cnt[Q[qc]] += 1
        # 지난 1주·4주 절대 수익(참고 표시용 — 판정 무관 · 벤치와 무관해 두 판이 같다)
        w = W[t].values
        r1 = (w[-1] / w[-2] - 1) * 100 if n >= 2 and w[-2] == w[-2] and w[-1] == w[-1] else None
        r4 = (w[-1] / w[-5] - 1) * 100 if n >= 5 and w[-5] == w[-5] and w[-1] == w[-1] else None
        rows.append({"t": t, "n": meta[t]["name"], "s": sidx[meta[t]["sector"]],
                     "ix": meta[t]["idx"], "q": (Q[qc] if qc >= 0 else None),
                     "r1": None if r1 is None else round(r1, 2),
                     "r4": None if r4 is None else round(r4, 2),
                     "x": xs, "y": ys})
    # 섹터 중앙값 궤적(보기용) — 그 판 종목 점의 중앙값이지 섹터 지수의 RRG 가 아니다
    sec = []
    for sname in sectors:
        cols = [t for t in W.columns if t in member and meta[t]["sector"] == sname]
        # ⚠ 종목이 MIN_SEC 보다 적은 섹터는 싣지 않는다 — NASDAQ 100 판의 금융·소재는 1종이라
        #   «섹터 중앙값» 이 그 한 종목 점이 된다(마름모가 섹터를 대표하는 것처럼 읽힌다).
        if len(cols) < MIN_SEC:
            continue
        mx = ratio[cols].iloc[lo:].median(axis=1)
        my = mom[cols].iloc[lo:].median(axis=1)
        sec.append({"s": sidx[sname], "k": len(cols),
                    "x": [enc(v) for v in mx.values], "y": [enc(v) for v in my.values]})
    return rows, cnt, sec


def main() -> int:
    pns = {k: panel(k) for k, *_ in BOARDS}
    base = pns["spx"]
    W, meta = base["W"], base["meta"]
    for k, pn in pns.items():
        # 두 판이 같은 주·같은 종목 격자여야 기준 주 눈금 하나로 둘을 오갈 수 있다
        if list(pn["W"].index) != list(W.index) or list(pn["W"].columns) != list(W.columns):
            raise SystemExit("🚨 %s 판의 주·종목 격자가 S&P 500 판과 다르다" % k)
    n = len(W.index)
    lo = max(0, n - 1 - HIST)
    weeks = [d.strftime("%Y-%m-%d") for d in W.index[lo:]]
    sectors = sorted({m["sector"] for m in meta.values()})
    sidx = {s: i for i, s in enumerate(sectors)}

    boards = {}
    for key, code, label, bench in BOARDS:
        member = {t for t, m in meta.items() if code in (m.get("idx") or [])}
        rows, cnt, sec = board(pns[key], member, sidx, sectors, lo)
        if not rows:
            raise SystemExit("🚨 %s 판에 종목이 없다 — stocks.json 의 idx 표기를 볼 것" % label)
        boards[key] = {"key": key, "label": label, "bench": bench, "n": len(rows),
                       "counts": cnt, "stocks": rows, "sector_med": sec}

    test = None
    if os.path.exists(TEST):
        T = json.load(io.open(TEST, encoding="utf-8"))
        test = {k: T.get(k) for k in ("verdict", "prereg", "commit", "window", "n_obs",
                                      "base_mean", "quadrants", "f1", "f2", "f3", "f4", "f5", "f6")}
    # 섹터 ETF 판(PREREG-2026-09-23-SECRRG) — «이 판을 섹터 로테이션에 쓰면?» 에 대한 답을 판정 상자가 읽는다.
    #   ⚠ 옮겨 적기만 한다. 여기서 다시 재지 않는다(그 파일도 얼린 기록이다).
    sect = None
    sp = os.path.join(DATA, "_secrrg.json")
    if os.path.exists(sp):
        S2 = json.load(io.open(sp, encoding="utf-8"))
        sect = {"verdict": S2.get("verdict"), "commit": S2.get("commit"), "window": S2.get("window"),
                "ann_excess_pp": (S2.get("f1") or {}).get("ann_excess_pp"), "t": (S2.get("f1") or {}).get("t"),
                "net_ann_excess_pp": (S2.get("f5") or {}).get("ann_excess_pp"),
                "turnover": (S2.get("turnover") or {}).get("S1"),
                "lead_lag_t": (S2.get("f3") or {}).get("t_clustered")}
    strats, wide = explorer_strategies()
    both = len({r["t"] for r in boards["spx"]["stocks"]} & {r["t"] for r in boards["ndx"]["stocks"]})
    doc = {
        "note": "종목 RRG 판 — 지수별 두 판. S&P 500 구성 종목 × S&P 500(PR) · NASDAQ 100 구성 종목 × NASDAQ 100(PR), 주간. "
                "산식은 build/rrg.py rrg_axes() 그대로(되돌아보기 12주·컷 100). "
                "판정은 build/rrg_stock.py 가 사전등록 PREREG-2026-09-23-RRGSTOCK 대로 518종 × S&P 500 에서 한 번 냈고 "
                "여기서는 옮겨 적기만 한다 — NASDAQ 100 판은 따로 검정하지 않은 서술용이다.",
        "as_of": weeks[-1], "px_as_of": base["asof"],
        "partial": base["partial"].strftime("%Y-%m-%d") if base["partial"] is not None else None,
        "look": LOOK, "cut": CUT, "freq": "주간",
        "universe_n": len(W.columns), "both_n": both,
        "axis_note": "RS = 종목 누적 ÷ 그 판 지수 누적. RS-Ratio = 100 + (RS − 12주 평균)/12주 표준편차. "
                     "RS-Mom = 같은 정규화를 RS-Ratio 1주 차분에. 두 축 모두 z 점수라 ±3.2 안에 든다.",
        "px_note": "종목 종가는 배당조정(yfinance)이고 벤치는 가격지수라 RS 에 연 약 1~2%p 상향 기울기가 섞인다. "
                   "12주 z 점수가 수준을 대부분 지우지만 0 은 아니다.",
        "member_note": "구성 종목은 오늘 명단이다(stocks.json 의 idx) — 과거 주의 점도 오늘 멤버만 그린다.",
        "enc": "x·y 는 floor((값 − 100) × 100) 정수 — 내림이라 부호(사분면)가 보존된다. "
               "null 은 계산 불가(상장 12+12주 미만 등).",
        "weeks": weeks, "sectors": sectors, "boards": boards, "default": "spx",
        "test": test, "test_sector": sect,
        "strategies": strats, "wide_n": wide, "wide_cut": WIDE,
    }
    s = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(s + "\n")
    print("주 %d(%s ~ %s) · 부분 주 %s 제외" % (len(weeks), weeks[0], weeks[-1], doc["partial"] or "없음"))
    for key, code, label, bench in BOARDS:
        bd = boards[key]
        print("  %-10s %3d종 × %s — 지금 %s" % (label, bd["n"], bench,
                                             " · ".join("%s %d" % (k, bd["counts"][k]) for k in Q)))
    print("  두 판 모두 %d종 · 유니버스 %d종" % (both, len(W.columns)))
    print("판정:", (test or {}).get("verdict") or "— (rrg_stock.py 를 아직 안 돌림)")
    print("→ rrg_board.json %.0f KB" % (len(s.encode("utf-8")) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
