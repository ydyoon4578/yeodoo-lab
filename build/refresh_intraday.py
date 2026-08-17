# -*- coding: utf-8 -*-
"""build/refresh_intraday.py — 장중 분봉 수집 → data/intraday.json · data/id/<티커>.json · data/intraday_hist.json

무엇을 왜 이렇게 나눴나.
  야후가 주는 창이 간격마다 다르다(2026-08-17 실측, 야후 오류문구가 직접 말한다 —
  "Only 8 days worth of 1m granularity data are allowed to be fetched per request"):

      1분봉  7 거래일   ← 화면용. 하루치만 보여 준다
      2분봉 23 거래일
      5분봉 60 거래일   ← 측정용. 「1일 전략」을 재려면 이쪽뿐이다

  🚨 그래서 **1분봉으로는 전략을 못 만든다.** 표본이 7일이다. 이 랩은 10년·120개월로도
    「판정 불가」를 적어 왔는데, 7일짜리 수에 전략이라는 이름을 붙일 수 없다.

  🚨 그리고 봉을 브라우저로 보내지 않는다. 518종 × 60일 × 78봉 × (종가·거래량)이면
    500만 값이고 JSON 으로 50MB 를 넘는다. **측정은 여기서 하고 결과만 싣는다** —
    랩의 나머지가 이미 그렇게 돈다.

세 산출물.
  ① data/intraday.json      그 세션의 종목별 요약(시가갭·구간수익·VWAP 대비·거래량). 전 종목.
  ② data/id/<티커>.json     그 세션 1분봉(종가·거래량). **매일 덮어쓴다** —
                            쌓으면 저장소가 하루 5MB 씩 분다(연 1GB 이상).
  ③ data/intraday_hist.json 일자×종목 **요약만** 누적. 하루 30KB 수준이라 부담이 없고,
                            이것이 쌓여야 나중에 60일보다 긴 표본으로 잴 수 있다.
                            🚨 오늘 시작해야 내년에 잴 수 있다 — 야후는 과거를 안 준다.

⚠ 크론이 장 마감 후 1일 1회라 화면은 «어제 장중» 을 보여 준다. 장중에 보려면 장중 크론이
  필요하고 그건 자주 밀린다(check_freshness.py 머리말의 실측). 산출물에 세션 날짜를 박아
  화면이 그것을 그대로 찍게 한다 — 언제 것인지 모르는 채로 보는 일이 없어야 한다.

  python build/refresh_intraday.py              # 전체(요약 + 1분봉 + 이력 append)
  python build/refresh_intraday.py --hist-only  # 이력만(5분봉 60일 재구성 · 최초 1회)
  python build/refresh_intraday.py --limit 40   # 앞 40종만(시험용)
"""
from __future__ import annotations
import io
import json
import os
import sys
import time
import warnings

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_ID = os.path.join(DATA, "id")
OUT = os.path.join(DATA, "intraday.json")
HIST = os.path.join(DATA, "intraday_hist.json")

CHUNK = 60          # 실측 3초/60종. 더 키우면 야후가 조인다
OPEN_MIN = 30       # 「오전 30분」 구간
CLOSE_MIN = 30      # 「마감 30분」 구간
MIN_BARS = 40       # 이보다 적은 봉이면 그날 그 종목은 요약하지 않는다(반쪽 세션)


def _yf(t):
    return t.replace(".", "-")


def load_universe(limit=None):
    """(티커 목록, 티커→회사명). 이름을 여기서 같이 꺼내는 이유는 화면이 티커만으로는
    무슨 회사인지 못 말하기 때문이다 — 목록 화면은 이름이 있어야 쓸모가 있다."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    ts = [s["t"] for s in st["stocks"]]
    nm = {s["t"]: (s.get("name") or "") for s in st["stocks"]}
    return (ts[:limit] if limit else ts), nm


def fetch(tickers, period, interval):
    """(티커 → DataFrame) — 청크로 나눠 받고 실패 청크는 한 번 더 시도한다."""
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), CHUNK):
        ch = tickers[i:i + CHUNK]
        d = None
        for k in range(3):
            try:
                d = yf.download([_yf(t) for t in ch], period=period, interval=interval,
                                auto_adjust=True, progress=False, group_by="ticker",
                                threads=True)
                if d is not None and len(d):
                    break
            except Exception:
                d = None
            time.sleep(2 * (k + 1))
        if d is None or not len(d):
            print("  ⚠ 청크 %d~%d 실패(%s %s) — 그 종목들은 이번 회차에서 빠진다"
                  % (i, i + len(ch), period, interval))
            continue
        for t in ch:
            y = _yf(t)
            try:
                sub = d[y] if (y, "Close") in d.columns else None
            except Exception:
                sub = None
            if sub is None:
                continue
            sub = sub.dropna(subset=["Close"])
            if len(sub):
                out[t] = sub
        print("    %s %s · %d/%d종" % (period, interval, len(out), min(i + CHUNK, len(tickers))))
    return out


def day_feats(sub):
    """하루치 봉 → 요약. 값이 모자라면 None.

    ⚠ VWAP 은 **그날 봉으로만** 만든다. 전일을 섞으면 «오늘 싸게 샀나» 라는 질문이
      «어제보다 싼가» 로 바뀐다 — 다른 질문이다.
    """
    if sub is None or len(sub) < MIN_BARS:
        return None
    c = sub["Close"].tolist()
    v = sub["Volume"].fillna(0).tolist() if "Volume" in sub else [0] * len(c)
    o, cl = c[0], c[-1]
    hi, lo = max(c), min(c)
    if not o or o <= 0:
        return None
    tv = sum(v)
    vwap = (sum(x * y for x, y in zip(c, v)) / tv) if tv > 0 else None
    n = len(c)
    k_o = min(OPEN_MIN, n - 1)
    k_c = min(CLOSE_MIN, n - 1)
    return {
        "o": round(o, 4), "c": round(cl, 4), "h": round(hi, 4), "l": round(lo, 4),
        "v": int(tv),
        # 세션 수익 — 시가 대비 종가. 갭은 전일 종가가 있어야 하므로 여기서 안 낸다.
        "r": round((cl / o - 1) * 100, 3),
        # 오전 N분 · 마감 N분 구간 수익
        "r_open": round((c[k_o] / o - 1) * 100, 3),
        "r_close": round((cl / c[n - 1 - k_c] - 1) * 100, 3) if c[n - 1 - k_c] else None,
        # 종가가 그날 범위 어디에 놓였나(0=저가, 1=고가). 마감 압력의 표준 지표.
        "clv": round((cl - lo) / (hi - lo), 4) if hi > lo else None,
        "vwap": None if vwap is None else round(vwap, 4),
        # 종가가 VWAP 위인가 — 그날 평균 체결가보다 세게 끝났나
        "vs_vwap": None if not vwap else round((cl / vwap - 1) * 100, 3),
        "n": n,
    }


def sessions_of(sub):
    """DataFrame 을 날짜별로 쪼갠다 → [(YYYY-MM-DD, 그날 부분)]."""
    out = []
    try:
        for d, g in sub.groupby(sub.index.date):
            out.append((str(d), g))
    except Exception:
        pass
    return out


def load_hist():
    if os.path.exists(HIST):
        try:
            return json.load(io.open(HIST, encoding="utf-8"))
        except Exception:
            pass
    return {"note": "일자×종목 장중 요약 누적. 봉은 안 쌓는다(크기) — 요약만 쌓아야 "
                    "야후의 60일 창보다 긴 표본을 언젠가 갖는다.",
            "fields": ["r", "r_open", "r_close", "clv", "vs_vwap", "v"],
            "days": {}}


def main() -> int:
    a = sys.argv[1:]
    lim = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    hist_only = "--hist-only" in a
    os.makedirs(DIR_ID, exist_ok=True)
    ts, NM = load_universe(lim)
    print("유니버스 %d종" % len(ts))

    H = load_hist()
    # ── ① 5분봉 60일 → 일자별 요약 누적 ────────────────────────────────
    print("  5분봉 60거래일 받는 중(측정·이력용)…")
    d5 = fetch(ts, "60d", "5m")
    added, day_seen = 0, set()
    for t, sub in d5.items():
        for day, g in sessions_of(sub):
            f = day_feats(g)
            if not f:
                continue
            H["days"].setdefault(day, {})[t] = [f["r"], f["r_open"], f["r_close"],
                                                f["clv"], f["vs_vwap"], f["v"]]
            day_seen.add(day)
            added += 1
    H["generated"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    H["as_of"] = max(H["days"]) if H["days"] else None
    H["n_days"] = len(H["days"])
    io.open(HIST, "w", encoding="utf-8").write(
        json.dumps(H, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("  → intraday_hist.json · 일자 %d(이번 회차 %d일) · 관측 %d · %.0fKB"
          % (H["n_days"], len(day_seen), added, os.path.getsize(HIST) / 1024))
    if hist_only:
        return 0

    # ── ② 1분봉 — 마지막 세션만. 화면용이라 덮어쓴다 ────────────────────
    print("  1분봉 7거래일 받는 중(화면용 — 마지막 세션만 싣는다)…")
    d1 = fetch(ts, "7d", "1m")
    if not d1:
        print("🚨 1분봉을 한 종목도 못 받았다 — 요약만 갱신하고 끝낸다")
        return 1
    last = max((s for sub in d1.values() for s, _g in sessions_of(sub)), default=None)
    if not last:
        print("🚨 세션 날짜를 못 정했다")
        return 1
    # ── 🚨 시장 전체의 «하루 모양» ──────────────────────────────────────
    # 518종 분봉을 갖고도 화면은 한 종목씩만 보여 주고 있었다. 그런데 «오늘 시장이 어떤
    # 모양이었나»(개장에 몰렸나 · 되밀렸나 · 마감에 랠리했나)는 **분봉이 있어야만 답하는
    # 질문**이고, 그것을 못 보면 이 자료를 절반만 쓰는 것이다.
    # 🚨 봉을 브라우저로 보내서 브라우저가 평균 내게 하면 안 된다 — 518파일 3.7MB 다.
    #   여기서 계산해 **배열 셋**(각 390)만 싣는다. 5KB 다.
    # ⚠ 시각으로 맞춘다(인덱스 아님). 거래정지·지연상장 종목은 봉 수가 달라서, 자리로
    #   맞추면 서로 다른 시각이 같은 칸에 겹친다.
    prof_r, prof_b, prof_v, prof_n, prof_t0 = [], [], [], [], None
    try:
        import pandas as _pd
        _idx = None
        _ser = {}
        for t, sub in d1.items():
            g = dict(sessions_of(sub)).get(last)
            if g is None or len(g) < MIN_BARS:
                continue
            c = g["Close"].dropna()
            if len(c) < MIN_BARS or not c.iloc[0]:
                continue
            _ser[t] = (c / float(c.iloc[0]) - 1.0) * 100.0
            _idx = c.index if _idx is None else _idx.union(c.index)
        if _idx is not None and _ser:
            M = _pd.DataFrame({t: v.reindex(_idx) for t, v in _ser.items()})
            V = _pd.DataFrame({t: (dict(sessions_of(d1[t])).get(last)["Volume"]
                                   .reindex(_idx)) for t in _ser})
            prof_r = [None if x != x else round(float(x), 4) for x in M.mean(axis=1)]
            prof_b = [None if x != x else round(float(x), 2)
                      for x in (M.gt(0).sum(axis=1) / M.notna().sum(axis=1) * 100.0)]
            prof_v = [int(x) if x == x else 0 for x in V.sum(axis=1)]
            prof_n = [int(x) for x in M.notna().sum(axis=1)]
            prof_t0 = str(_idx.min())[11:16]
            print("  [프로파일] 분 %d · 종목 최대 %d · 마지막 평균 %+.3f%% · 상승비율 %.1f%%"
                  % (len(prof_r), max(prof_n or [0]),
                     prof_r[-1] if prof_r else 0, prof_b[-1] if prof_b else 0))
    except Exception as _e:
        print("  ⚠ 시장 프로파일 계산 실패: %s — 그 칸만 빈다" % str(_e)[:70])

    # 전일 종가 — 랩 일봉 격자에서 «세션 날짜 직전 거래일» 의 종가를 꺼낸다.
    PREV = {}
    try:
        _st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        _dt_all = _st["pxd_dates"]
        _pi = max((i for i, d in enumerate(_dt_all) if d < last), default=None)
        if _pi is not None:
            for _t in ts:
                _p = os.path.join(DATA, "sd", "%s.json" % _t)
                if not os.path.exists(_p):
                    continue
                _a = (json.load(io.open(_p, encoding="utf-8")) or {}).get("pxd") or []
                if _pi < len(_a) and _a[_pi]:
                    PREV[_t] = round(float(_a[_pi]), 4)
            print("  [전일종가] %s 기준 %d종" % (_dt_all[_pi], len(PREV)))
    except Exception as _e:
        print("  ⚠ 전일 종가 준비 실패: %s — 차트의 갭 선만 빠진다" % str(_e)[:60])

    rows, n_id = [], 0
    for t, sub in d1.items():
        ses = dict(sessions_of(sub))
        g = ses.get(last)
        f = day_feats(g)
        if not f:
            continue
        c = [round(x, 4) for x in g["Close"].tolist()]
        v = [int(x) for x in g["Volume"].fillna(0).tolist()] if "Volume" in g else [0] * len(c)
        io.open(os.path.join(DIR_ID, "%s.json" % t), "w", encoding="utf-8").write(
            # 🚨 전일 종가(pc)를 같이 싣는다. 없으면 화면이 **갭을 못 그린다** —
            #   「오늘 어디서 시작했나」는 시가 자체가 아니라 «어제 대비 어디서 열었나» 이고
            #   그게 그날 성격을 절반 정한다.
            # ⚠ 새로 받지 않는다. data/sd(랩 일봉)에서 꺼낸다 — 두 벌이 되면 어느 쪽이
            #   맞는지 다투게 된다.
            json.dumps({"t": t, "d": last, "t0": str(g.index[0])[11:16],
                        "pc": PREV.get(t), "c": c, "v": v}, separators=(",", ":")) + "\n")
        n_id += 1
        rows.append(dict(f, t=t, nm=NM.get(t) or ""))
    doc = {
        "note": "그 세션의 종목별 장중 요약. 봉은 data/id/<티커>.json 에 따로 있고 "
                "화면이 종목을 고를 때 받는다.",
        "as_of": last,
        "generated": H["generated"],
        "interval": "1m",
        "limits": [
            "🚨 «지금» 이 아니다. 이 표는 **%s 세션**이고, 갱신 잡이 장 마감 뒤 하루 한 번 "
            "돌기 때문에 장중에 보면 어제 것이다. 화면이 세션 날짜를 그대로 찍는다." % last,
            "⚠ 야후 분봉은 다수 거래소에서 지연분이고, 사전·시간외 체결이 섞이는 종목이 있다. "
            "정규장 봉만 걸러 쓰지만 원천이 그렇게 준 것을 다시 검증하지는 않는다.",
            "⚠ 1분봉은 야후가 **7거래일**만 준다. 그래서 이 화면은 하루치이고, 여러 날을 "
            "재는 일은 5분봉(60거래일) 쪽 요약 이력이 맡는다.",
            "⚠ 봉 %d개 미만인 종목은 반쪽 세션으로 보고 싣지 않는다." % MIN_BARS,
        ],
        # 시장 전체 분당 프로파일 — 동일가중 평균수익 · 상승 종목 비율 · 거래량
        "profile": {"t0": (prof_t0 if prof_r else None), "n_min": len(prof_r), "ret": prof_r,
                    "breadth": prof_b, "vol": prof_v, "n_stock": prof_n},
        "n": len(rows),
        "rows": sorted(rows, key=lambda r: -(r["v"] or 0)),
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("  → intraday.json · 세션 %s · %d종 · %.0fKB · 분봉 파일 %d개"
          % (last, len(rows), os.path.getsize(OUT) / 1024, n_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
