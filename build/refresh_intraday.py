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
# 🚨 변동성·효율은 **표본 간격에 민감하다.** 봉이 촘촘할수록 경로가 길어져 효율비는
#   작아지고, 미시구조 잡음 때문에 실현변동성은 커진다. 실측(2026-08-17, 514종 중앙):
#       er   5분/1분 = 2.33 배   ← 같은 이름이 두 배 넘게 다른 값이 된다
#       rvol 5분/1분 = 0.87 배
#   화면은 1분봉, 이력은 5분봉이라 그대로 두면 목록과 이력 카드가 «추세 효율» 을
#   서로 다른 잣대로 말한다. → 입력 간격과 무관하게 **5분 격자로 다시 뽑아** 잰다.
GRID_MIN = 5        # rvol·er 을 재는 고정 격자(분)
CLOSE_MIN = 30      # 「마감 30분」 구간
MIN_BARS = 40       # 이보다 적은 봉이면 그날 그 종목은 요약하지 않는다(반쪽 세션)

# 🚨 이력 행의 «칸 뜻» 정본. 여기 한 곳에서만 정한다.
#   2026-08-18 실패에서 배운 것: fields 를 load_hist() 의 **기본값**에만 적었더니,
#   파일이 이미 있는 경우 옛 fields(7칸)를 그대로 들고 오면서 행만 10칸이 됐다.
#   머리와 몸이 다른 말을 하는 파일이 만들어졌다 — 읽는 쪽은 그걸 알 방법이 없다.
# ⚠ 새 축은 **끝에만** 붙인다. 가운데 넣으면 이미 쌓인 날의 뜻이 통째로 밀린다.
HFIELDS = ["r", "r_open", "r_close", "clv", "vs_vwap", "v", "gap",
           "rvol", "er", "cvol"]

# 🚨 지수 자체의 분봉. 화면이 오래 «동일가중 평균» 만 그렸고, 그 패널이 스스로
#   «지수가 아니라 동일가중이라 대형주 쏠림이 빠진다» 고 경고하고 있었다 —
#   경고를 적어 둘 게 아니라 **지수를 같이 받아 나란히 그리면 되는 일**이다.
#   두 선의 벌어짐이 곧 그날의 «대형주가 끌었나 vs 폭이 넓었나» 다.
# ⚠ 파일명에 ^ 를 쓰지 않는다(URL 인코딩이 필요해지고 정적 호스팅에서 사고가 난다).
#   키(SPX·NDX)는 stocks.json 의 idx 표기와 **같은 글자**를 쓴다 — 화면이 그 값으로
#   종목을 좁히므로, 여기서 다른 글자를 쓰면 두 벌이 된다.
INDEXES = [("SPX", "^GSPC", "S&P 500"), ("NDX", "^NDX", "나스닥 100")]


def _yf(t):
    return t.replace(".", "-")


def load_universe(limit=None):
    """(티커 목록, 티커→회사명). 이름을 여기서 같이 꺼내는 이유는 화면이 티커만으로는
    무슨 회사인지 못 말하기 때문이다 — 목록 화면은 이름이 있어야 쓸모가 있다."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    ts = [s["t"] for s in st["stocks"]]
    # 이름·지수·섹터를 여기서 같이 꺼낸다 — 화면이 티커만으로는 무슨 회사인지 못 말하고,
    # 지수·섹터가 없으면 목록을 좁힐 수가 없다(정렬만 되고 필터가 안 된다).
    # ⚠ 새로 만들지 않는다. stocks.json 이 정본이고 여기서는 옮기기만 한다.
    nm = {s["t"]: {"nm": s.get("name") or "",
                   "idx": s.get("idx") or [],
                   "sec": s.get("sector") or ""} for s in st["stocks"]}
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
    # 🚨 2026-08-18 — **여기 버그가 있었다.** OPEN_MIN/CLOSE_MIN 을 «분» 이라 이름 붙여
    #   놓고 **봉 개수**로 썼다(c[30]). 1분봉에서는 우연히 맞았지만(30봉=30분),
    #   이력을 만드는 **5분봉에서는 30봉 = 150분**이었다. 즉 지금까지 이력의
    #   `r_open` 은 「개장 30분」이 아니라 **「개장 150분」** 이었고, `r_close` 도
    #   마감 150분이었다. 화면(1분봉)과 이력(5분봉)이 같은 이름으로 다른 것을 재고
    #   있었다 — 이 랩이 늘 경계하는 «경로가 둘» 이다.
    # → 봉 간격을 지표에서 **재서** 분을 봉으로 환산한다. 간격이 바뀌어도 뜻이 안 변한다.
    step = _step_min(sub)
    k_o = max(1, min(int(round(OPEN_MIN / step)), n - 1))
    k_c = max(1, min(int(round(CLOSE_MIN / step)), n - 1))
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
        # 🚨 vs_vwap 은 **화면 정렬 축에서 뺐다**(2026-08-18). 자료에는 남긴다 —
        #   사전등록 INTRADAY6 ⑤가 이 값을 쓰므로 지우면 그 등록을 재현할 수 없다.
        #   왜 뺐나: 그날 안에서 나머지 6축으로 회귀하면 **R² 0.893**(60일 평균)이다.
        #   즉 이 축으로 정렬해도 clv·r_close 로 정렬한 것과 거의 같은 줄이 나온다.
        "vs_vwap": None if not vwap else round((cl / vwap - 1) * 100, 3),
        # ── 아래 셋은 그 빈자리를 메우려고 **잰 뒤에** 고른 것들이다 ──────────
        # 후보 넷을 오늘 세션 517종으로 시험해 기존 7축에 대한 R² 를 재고, 낮은 셋만 남겼다:
        #   rvol 0.146 · er 0.235 · cvol 0.283 · (mdd 0.559 — 탈락, r 과 0.69 로 닮았다)
        # ⚠ «좋은 지표» 라서가 아니라 **다른 것을 재기 때문에** 고른 것이다. 수익을
        #   예측한다는 말이 아니다 — 그건 사전등록해서 따로 재야 한다.
        #
        # 일중 실현변동성 — 봉간 로그수익의 표준편차를 세션 전체로 환산(%).
        # 「얼마나 흔들렸나」. 방향과 무관해서 r 계열 어디와도 안 닮는다.
        "rvol": round(_rvol(_grid(c, step)) * 100, 3) if len(c) > 2 else None,
        # 효율비(0~1) — |종가−시가| ÷ Σ|봉간 변화|. 1 에 가까우면 한 방향으로 갔고,
        # 0 에 가까우면 같은 폭을 톱니로 오갔다. 「추세였나 톱니였나」.
        "er": _eff(_grid(c, step)),
        # 마감 30분 거래량 비중(%) — 「거래가 마감에 몰렸나」. 가격이 아니라 참여를 잰다.
        "cvol": (round(sum(v[n - 1 - k_c:]) / tv * 100, 3) if tv > 0 else None),
        "n": n,
    }


def _step_min(sub):
    """봉 간격(분). 지표에서 중앙값으로 잰다 — 결측 한두 개에 흔들리지 않게.

    ⚠ 못 재면 1 을 돌려준다. 그러면 «분» 이 «봉» 과 같아져 옛 동작이 되는데,
      그건 조용한 오답이므로 그 사실을 부르는 쪽이 아니라 여기서 찍는다.
    """
    try:
        idx = sub.index
        if len(idx) < 3:
            return 1.0
        d = [(idx[i] - idx[i - 1]).total_seconds() / 60.0 for i in range(1, min(len(idx), 40))]
        d = sorted(x for x in d if x > 0)
        return float(d[len(d) // 2]) if d else 1.0
    except Exception:
        print("  ⚠ 봉 간격을 못 쟀다 — 1분으로 본다(구간 길이가 틀어질 수 있다)")
        return 1.0


def _grid(c, step):
    """입력 봉을 GRID_MIN 격자로 성글게 한다 — 간격이 달라도 같은 수가 나오게.

    ⚠ 마지막 봉은 반드시 남긴다. 그냥 k 간격으로 자르면 세션 끝이 잘려
      「종가」가 종가가 아니게 된다(효율비의 분자가 |끝−처음| 이라 바로 틀어진다).
    """
    k = max(1, int(round(GRID_MIN / max(step, 0.001))))
    if k <= 1 or len(c) <= 2:
        return c
    out = c[::k]
    if out[-1] != c[-1]:
        out = out + [c[-1]]
    return out


def _rvol(c):
    """봉간 로그수익 표준편차 × √봉수 — 그 세션의 실현변동성(비율)."""
    import math
    lr = [math.log(c[i] / c[i - 1]) for i in range(1, len(c)) if c[i] > 0 and c[i - 1] > 0]
    if len(lr) < 2:
        return 0.0
    m = sum(lr) / len(lr)
    var = sum((x - m) ** 2 for x in lr) / (len(lr) - 1)
    return (var ** 0.5) * (len(lr) ** 0.5)


def _eff(c):
    """효율비 — |끝−처음| ÷ 경로길이. 경로가 0이면 잴 수 없다(None)."""
    path = sum(abs(c[i] - c[i - 1]) for i in range(1, len(c)))
    return round(abs(c[-1] - c[0]) / path, 4) if path > 0 else None


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
            H = json.load(io.open(HIST, encoding="utf-8"))
            old = list(H.get("fields") or [])
            if old != HFIELDS:
                # 🚨 앞부분이 정본과 같을 때만 «끝에 붙은 것» 으로 보고 늘린다.
                #   어긋나면 자리 뜻이 밀린 것이므로 **고치지 않고 멈춘다** —
                #   조용히 맞춰 버리면 쌓인 60일이 통째로 잘못 읽힌다.
                if HFIELDS[:len(old)] != old:
                    raise SystemExit(
                        "🚨 intraday_hist 의 fields 가 정본과 어긋난다. "
                        "파일=%s · 정본=%s · "
                        "끝에 붙이는 것만 허용한다 — 손으로 확인할 것."
                        % (old, HFIELDS))
                print("  [이력] fields %d칸 → %d칸으로 늘림(%s)"
                      % (len(old), len(HFIELDS), ", ".join(HFIELDS[len(old):])))
                H["fields"] = list(HFIELDS)
            return H
        except SystemExit:
            raise
        except Exception:
            pass
    return {"note": "일자×종목 장중 요약 누적. 봉은 안 쌓는다(크기) — 요약만 쌓아야 "
                    "야후의 60일 창보다 긴 표본을 언젠가 갖는다.",
            # ⚠ 2026-08-18 에 gap 을 끝에 더했다. **끝에 붙인다** — 가운데 넣으면 이미
            #   쌓인 날의 자리 뜻이 통째로 밀린다(옛 행은 6칸이라 읽는 쪽이 길이로 가른다).
            "fields": list(HFIELDS),
            "days": {}}


def main() -> int:
    a = sys.argv[1:]
    lim = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    hist_only = "--hist-only" in a
    os.makedirs(DIR_ID, exist_ok=True)
    ts, NM = load_universe(lim)
    print("유니버스 %d종" % len(ts))

    # 일봉 종가 지도 — 각 세션의 «전일 종가» 를 찾는 데 쓴다(갭 계산).
    # ⚠ 새로 받지 않는다. data/sd(랩 일봉)가 정본이고 여기서는 읽기만 한다.
    DGRID, DCLOSE = [], {}
    try:
        _st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        DGRID = _st["pxd_dates"]
        for _t in ts:
            _p = os.path.join(DATA, "sd", "%s.json" % _t)
            if os.path.exists(_p):
                DCLOSE[_t] = (json.load(io.open(_p, encoding="utf-8")) or {}).get("pxd") or []
        print("  [일봉] 격자 %d일 · 종가 %d종" % (len(DGRID), len(DCLOSE)))
    except Exception as _e:
        print("  ⚠ 일봉 준비 실패: %s — 갭이 전부 빈다" % str(_e)[:60])

    def prev_close(t, day):
        """day 직전 거래일의 종가. 없으면 None — 갭 칸만 빈다."""
        if not DGRID or t not in DCLOSE:
            return None
        i = max((k for k, d in enumerate(DGRID) if d < day), default=None)
        if i is None:
            return None
        a = DCLOSE[t]
        return a[i] if i < len(a) and a[i] else None

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
            # 🚨 갭을 이력에 같이 쌓는다. 없으면 «갭 뒤 장중» 을 60일로 못 재는데,
            #   그건 이 자료로만 답할 수 있는 질문이다(일봉에는 시가가 조정돼 들어온다).
            _pc = prev_close(t, day)
            _gap = round((f["o"] / _pc - 1) * 100, 3) if (_pc and f.get("o")) else None
            H["days"].setdefault(day, {})[t] = [f["r"], f["r_open"], f["r_close"],
                                                f["clv"], f["vs_vwap"], f["v"], _gap,
                                                f.get("rvol"), f.get("er"), f.get("cvol")]
            day_seen.add(day)
            added += 1
    H["generated"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    H["as_of"] = max(H["days"]) if H["days"] else None
    H["n_days"] = len(H["days"])
    # ── 🚨 분해 검산 — 밤샘 × 장중 = 일간 이어야 한다 ───────────────────
    # 2026-08-18 에 이것이 **안 맞는 것을 뒤늦게 찾았다**(연 21%p 가 샜다). 원인은
    # 일봉이 배당·분할로 소급 조정되는데 분봉은 그날 실제가라 두 계열의 수준이 종목마다
    # 상수배로 어긋나는 것이다. 그 상수가 gap 에 매일 들어간다.
    # ⚠ 자료를 고칠 방법이 지금은 없다(미조정 일봉이 없다). 그래서 **막지 않고 잰다** —
    #   대신 그 크기를 산출물에 실어, 이 수를 쓰는 쪽이 오차를 알고 쓰게 한다.
    #   조용히 지나가는 것만은 막는다.
    try:
        _pairs = []
        for _d, _rows in H["days"].items():
            _i = next((k for k, x in enumerate(DGRID) if x == _d), None)
            if _i is None or _i == 0:
                continue
            for _t, _v in _rows.items():
                if len(_v) < 7 or _v[6] is None or _v[0] is None:
                    continue
                _a = DCLOSE.get(_t) or []
                if _i >= len(_a) or not _a[_i] or not _a[_i - 1]:
                    continue
                _pairs.append(((1 + _v[6] / 100.0) * (1 + _v[0] / 100.0) - 1) * 100.0
                              - (_a[_i] / _a[_i - 1] - 1) * 100.0)
        if _pairs:
            _n = len(_pairs)
            _mean = sum(_pairs) / _n
            _srt = sorted(_pairs)
            _med = _srt[_n // 2]
            H["reconcile"] = {"n": _n, "mean_pp": round(_mean, 4),
                              "median_pp": round(_med, 4),
                              "ann_pp": round(_mean * 252, 1),
                              "note": "밤샘×장중 − 일간(%p/일). 0 이어야 한다. 0 이 아닌 것은 "
                                      "일봉(조정가)과 분봉(실제가)의 기준이 달라서다 — "
                                      "PREREG-2026-08-18-OVN5-RESULT.md §1."}
            print("  [분해검산] 밤샘×장중 − 일간 = %+.4f%%p/일 (중앙 %+.4f · 연 %+.1f%%p · 짝 %d)"
                  % (_mean, _med, _mean * 252, _n))
            if abs(_mean) > 0.02:
                print("  🚨 분해가 %.4f%%p/일 어긋난다 — 밤샘을 «수익» 으로 쓰면 안 된다"
                      % _mean)
    except Exception as _e:
        print("  ⚠ 분해 검산 실패: %s" % str(_e)[:60])

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
    # 🚨 2026-08-18 — 프로파일을 **묶음별로** 낸다(사용자 요청: S&P 500·나스닥 100 각각).
    #   전에는 518종 하나뿐이라 「오늘 시장」이 한 덩어리였다. 두 지수는 구성이 크게 달라
    #   (나스닥 100 은 기술주 쏠림) 한 곡선으로 덮으면 갈리는 날을 못 본다.
    # ⚠ 겹치는 종목이 있다(양쪽에 다 든 종목). 묶음을 배타적으로 자르지 않는다 —
    #   «S&P 500 의 하루» 는 그 지수 편입 종목 전부이지, 나스닥과 안 겹치는 것만이 아니다.
    _ser_all, _vol_all, _idx_all = {}, {}, None
    try:
        import pandas as _pd
        for t, sub in d1.items():
            g = dict(sessions_of(sub)).get(last)
            if g is None or len(g) < MIN_BARS:
                continue
            c = g["Close"].dropna()
            if len(c) < MIN_BARS or not c.iloc[0]:
                continue
            _ser_all[t] = (c / float(c.iloc[0]) - 1.0) * 100.0
            _vol_all[t] = g["Volume"]
            _idx_all = c.index if _idx_all is None else _idx_all.union(c.index)
    except Exception as _e:
        print("  ⚠ 프로파일 계열 준비 실패: %s" % str(_e)[:70])

    def _profile(keep):
        """keep(티커 집합)에 대한 분당 프로파일. 비면 빈 칸을 돌려준다."""
        if _idx_all is None or not keep:
            return {"t0": None, "n_min": 0, "ret": [], "breadth": [], "vol": [], "n_stock": []}
        import pandas as _pd
        M = _pd.DataFrame({t: _ser_all[t].reindex(_idx_all) for t in keep})
        V = _pd.DataFrame({t: _vol_all[t].reindex(_idx_all) for t in keep})
        _cnt = M.notna().sum(axis=1)
        return {
            "t0": str(_idx_all.min())[11:16],
            "n_min": len(_idx_all),
            "ret": [None if x != x else round(float(x), 4) for x in M.mean(axis=1)],
            # ⚠ 분모는 «그 분에 봉이 있는 종목» 이다. 전체 종목 수로 나누면 지연상장·
            #   거래정지가 상승비율을 조용히 끌어내린다.
            "breadth": [None if x != x else round(float(x), 2)
                        for x in (M.gt(0).sum(axis=1) / _cnt.replace(0, float("nan")) * 100.0)],
            "vol": [int(x) if x == x else 0 for x in V.sum(axis=1)],
            "n_stock": [int(x) for x in _cnt],
        }

    _in = lambda t, k: k in ((NM.get(t) or {}).get("idx") or [])
    profiles = {
        "ALL": _profile(sorted(_ser_all)),
        "SPX": _profile(sorted(t for t in _ser_all if _in(t, "SPX"))),
        "NDX": _profile(sorted(t for t in _ser_all if _in(t, "NDX"))),
    }
    for _k, _p in profiles.items():
        print("  [프로파일:%s] 분 %d · 종목 최대 %d · 마지막 평균 %+.3f%% · 상승비율 %.1f%%"
              % (_k, _p["n_min"], max(_p["n_stock"] or [0]),
                 (_p["ret"] or [0])[-1] or 0, (_p["breadth"] or [0])[-1] or 0))

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
        # 🚨 갭 = 시가 ÷ 전일 종가 − 1. 전일 종가를 이미 싣게 됐으니(pc) 여기서 같이 낸다.
        #   갭은 «장중 이전에 이미 일어난 일» 이라 장중 지표와 성격이 다르다 — 그래서
        #   따로 적고, 화면도 축을 따로 둔다.
        _pc = PREV.get(t)
        _gap = None
        if _pc and f.get("o"):
            _gap = round((f["o"] / _pc - 1) * 100, 3)
        _m = NM.get(t) or {}
        rows.append(dict(f, t=t, nm=_m.get("nm") or "", idx=_m.get("idx") or [],
                         sec=_m.get("sec") or "", pc=_pc, gap=_gap))
    # ── 지수 자체의 분봉 ────────────────────────────────────────────────
    # 종목과 같은 모양(t·d·t0·pc·c·v)으로 써서 화면이 **같은 그리기 함수**를 쓰게 한다.
    # 두 벌을 만들면 한쪽만 고쳐지는 일이 생긴다(이 랩이 여러 번 겪었다).
    index_meta = {}
    try:
        _iraw = fetch([x[1] for x in INDEXES], "5d", "1m")
        # 전일 종가는 **일봉에서** 꺼낸다. 분봉 마지막 값으로 대신하면 그 봉이
        # 공식 종가와 미세하게 다르고, 갭이 그 차이만큼 틀어진다.
        _iprev = {}
        try:
            import yfinance as _yf2
            _dd = _yf2.download([x[1] for x in INDEXES], period="10d", interval="1d",
                                auto_adjust=False, progress=False, group_by="ticker")
            for _k, _src, _nm in INDEXES:
                _col = _dd[_src]["Close"].dropna() if (_src, "Close") in _dd.columns else None
                if _col is None or _col.empty:
                    continue
                _before = _col[[str(i)[:10] < last for i in _col.index]]
                if len(_before):
                    _iprev[_src] = round(float(_before.iloc[-1]), 4)
        except Exception as _e:
            print("  ⚠ 지수 전일종가 실패: %s — 갭 없이 시가 대비로만 그린다" % str(_e)[:60])
        for _k, _src, _nm in INDEXES:
            _g = dict(sessions_of(_iraw[_src])).get(last) if _src in _iraw else None
            if _g is None or len(_g) < MIN_BARS:
                print("  ⚠ 지수 %s(%s) 세션 %s 봉 부족 — 이번 회차에서 빠진다" % (_nm, _src, last))
                continue
            _c = [round(float(x), 4) for x in _g["Close"].tolist()]
            _v = [int(x) if x == x else 0 for x in _g["Volume"].fillna(0).tolist()]
            io.open(os.path.join(DIR_ID, "_%s.json" % _k), "w", encoding="utf-8").write(
                json.dumps({"t": _src, "d": last, "t0": str(_g.index[0])[11:16],
                            "pc": _iprev.get(_src), "c": _c, "v": _v},
                           separators=(",", ":")) + "\n")
            _pc = _iprev.get(_src)
            index_meta[_k] = {
                "src": _src, "nm": _nm, "file": "_%s" % _k, "n_min": len(_c),
                "t0": str(_g.index[0])[11:16], "pc": _pc,
                # 시가 대비 · 전일 대비를 둘 다 싣는다. 화면이 계산하면 어느 쪽인지
                # 화면마다 달라진다(«전일대비» 라 적고 시가대비를 그린 사고가 있었다).
                "r_open": round((_c[-1] / _c[0] - 1) * 100, 4) if _c[0] else None,
                "r_prev": (round((_c[-1] / _pc - 1) * 100, 4) if _pc else None),
            }
            print("  [지수] %s(%s) 봉 %d · 시가대비 %+.3f%%"
                  % (_nm, _src, len(_c), index_meta[_k]["r_open"] or 0))
    except Exception as _e:
        print("  ⚠ 지수 분봉 수집 실패: %s — 그 패널만 빈다" % str(_e)[:80])

    doc = {
        "note": "그 세션의 종목별 장중 요약. 봉은 data/id/<티커>.json 에 따로 있고 "
                "화면이 종목을 고를 때 받는다. 지수 자체 분봉은 data/id/_SPX·_NDX.json 이다.",
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
        # 분당 프로파일 — 묶음(ALL·SPX·NDX)별 동일가중 평균수익 · 상승 종목 비율 · 거래량.
        # ⚠ 여기 수는 전부 **동일가중**이다. 시총가중 지수는 index 쪽(실제 ^GSPC·^NDX)이고
        #   둘은 다른 값이다 — 화면이 둘을 겹쳐 그려 차이를 보이게 한다.
        "profiles": profiles,
        "index": index_meta,
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
