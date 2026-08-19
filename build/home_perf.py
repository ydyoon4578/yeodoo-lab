# -*- coding: utf-8 -*-
"""build/home_perf.py — 홈 '기간별 수익률' 위에 그릴 **시계열** → data/home_perf.json

## 왜 별도 파일인가

홈은 이미 여러 묶음을 받는다. 원본(data/assets.json 4.3MB · data/sd/*.json 518개)을
그대로 받게 하면 홈이 무거워진다 — build/home_flow.py 가 같은 이유로 만들어졌다.
여기서는 **그릴 만큼만** 잘라 담는다(구간마다 최대 %d점).

## 🚨 끝점이 아래 표와 **같아야 한다**

표(index.html #sttbl)가 쓰는 값은 두 곳에서 온다:
  · 지수 4줄 = data/market_board.json (build/market_board.py, 원자료 assets.json)
  · 섹터 11줄 = data/home_reco.json.industry (build/home_summary.py, 원자료 data/sd)

🚨 2026-08-11 — 섹터 정의가 바뀌었다(사용자 결정). 종전에는 '기준일 대비 종목별 비율의
평균'(동일가중)이었고 이 파일도 그 식으로 경로를 만들었다. 지금 표의 섹터 줄은
**섹터 ETF 그 자체**다(home_summary 가 data/assets.json 에서 옮긴다).
그래서 여기서도 ETF 가격 경로를 그대로 쓴다 — 같은 원천이라 끝점이 표와 어긋날 자리가 없다.
⚠ 산업그룹 줄은 유니버스 종목의 기준일 시총가중이라 섹터 줄과 정확히 합쳐지지 않는다.
  ETF 가 분산요건 상한이 걸린 지수이고 구성종목도 다르기 때문이다. 화면이 그것을 적는다.

⚠ 구간마다 기준일이 다르므로 **구간마다 경로를 따로 굽는다.**

⚠ 1일·1주는 점이 1~5개라 선으로 그릴 것이 없다. 굽지 않는다(화면도 그 두 칸을 안 낸다).

    python build/home_perf.py
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "home_perf.json")

MAXPT = 90          # 구간당 점 수 상한 — 이보다 많으면 고르게 솎는다
# ⚠ 홈의 두 블록(기간별 수익률 · 전략별 성과)이 **같은 구간 목록**을 쓴다
#   (사용자 요청 2026-08-13 — "1주, 1개월, 3개월, 6개월, 1년, 올해로 통일").
#   여기만 고치면 반쪽이다 — strategy_index.TR_HOR 도 같이 봐야 한다.
HZ = ["1W", "1M", "3M", "6M", "12M", "YTD"]
IX = [("SPY", "S&P 500"), ("QQQ", "나스닥 100"), ("DIA", "다우존스 30"), ("IWM", "러셀 2000")]

__doc__ = __doc__ % MAXPT


def thin(idx, n):
    """구간 인덱스를 n점으로 고르게 솎는다. 마지막 점은 반드시 남긴다(끝점이 표와 같아야 한다)."""
    if len(idx) <= n:
        return idx
    step = (len(idx) - 1) / float(n - 1)
    out = [idx[int(round(i * step))] for i in range(n)]
    out[-1] = idx[-1]
    return sorted(set(out))


def _idbars(key, stock=False):
    """분봉 파일. ⚠ 지수·ETF 는 «_SPY.json» 이고 **종목은 접두사가 없다**(«AAPL.json»).
    한 함수로 둘 다 읽되 어느 쪽인지 부르는 곳이 말한다 — 접두사를 섞으면 조용히 다 빈다."""
    p = os.path.join(DATA, "id", ("%s.json" if stock else "_%s.json") % key)
    if not os.path.exists(p):
        return None
    try:
        j = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None
    return j if (j.get("c") and j.get("pc")) else None


# 홈 섹터 판과 같은 한글 이름 — home_summary.SEC_ETF 와 짝이다(다르면 색이 안 맞는다).
_SEC_KO = {"Information Technology": "IT", "Financials": "금융", "Health Care": "헬스케어",
           "Consumer Discretionary": "경기소비", "Communication Services": "커뮤니케이션",
           "Industrials": "산업재", "Consumer Staples": "필수소비", "Energy": "에너지",
           "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재"}


def _intraday_ind(idx):
    """(그룹→경로, 그룹→부모섹터한글). 재료가 없으면 ({}, {})."""
    mp = os.path.join(DATA, "members.json")
    sp = os.path.join(DATA, "stocks.json")
    if not (os.path.exists(mp) and os.path.exists(sp)):
        return {}, {}
    try:
        mem = (json.load(io.open(mp, encoding="utf-8")) or {}).get("members") or {}
        st = json.load(io.open(sp, encoding="utf-8"))["stocks"]
    except Exception:
        return {}, {}
    grp, gsec = {}, {}
    for x in st:
        t = x["t"]
        g = ((mem.get(t) or {}).get("grp") or "").strip()
        ko = _SEC_KO.get(x.get("sector") or "")
        mc = (x.get("fund") or {}).get("mc")
        if not g or not ko or not mc or mc <= 0:
            continue          # ⚠ 추측으로 채우지 않는다 — 못 넣는 종목은 그냥 빠진다
        grp.setdefault(g, []).append((t, float(mc)))
        gsec[g] = ko
    out, secs = {}, {}
    for g, mem_l in grp.items():
        num = [0.0] * len(idx)
        wsum = 0.0
        for t, mc in mem_l:
            b = _idbars(t, stock=True)
            if not b or not b.get("pc") or len(b["c"]) < 30:
                continue
            pc, c = float(b["pc"]), b["c"]
            for k, i in enumerate(idx):
                num[k] += mc * (c[min(i, len(c) - 1)] / pc - 1) * 100.0
            wsum += mc
        # 3종 미만이 담긴 그룹은 만들지 않는다 — 일간 판과 같은 취급이다
        if wsum <= 0 or sum(1 for t, _m in mem_l if _idbars(t, stock=True)) < 3:
            continue
        out[g] = [round(v / wsum, 3) for v in num]
        secs[g] = gsec[g]
    return out, secs


def _intraday_block(as_of, adates, apx, sec_etf, sty_etf):
    """그 세션의 분당 경로(전일 종가 대비 %). 못 만들면 None — 0 으로 채우지 않는다."""
    probe = _idbars("SPY")
    if not probe:
        print("   1D: data/id/_SPY.json 없음 — 1일 칸을 만들지 않는다")
        return None
    if probe.get("d") != as_of:
        print("   1D: 분봉 세션 %s ≠ 일간 기준일 %s — 1일 칸을 만들지 않는다"
              % (probe.get("d"), as_of))
        return None
    n = len(probe["c"])
    t0 = probe.get("t0") or "09:30"
    h0, m0 = int(t0[:2]), int(t0[3:5])
    idx = thin(list(range(n)), MAXPT)
    def hhmm(i):
        mm = h0 * 60 + m0 + i
        return "%02d:%02d" % (mm // 60, mm % 60)
    # ⚠ 화면은 지수 판에 dates 를, 섹터·스타일 판에 **sec_dates** 를 쓴다. 1일은 셋이
    #   같은 격자(같은 분봉)라 같은 배열을 둘 다 넣는다 — 없으면 그 두 판이 터진다(실측).
    _t = [hhmm(i) for i in idx]
    blk = {"dates": _t, "sec_dates": _t, "ix": {}, "sec": {}, "sty": {}, "intraday": True}
    # 표의 1일 칸과 얼마나 어긋나는지 잰다 — 일간 종가로 만든 진짜 1일 수익과 견준다.
    apos = {d: i for i, d in enumerate(adates)}
    ai = apos.get(as_of)
    gaps = []
    def put(bucket, key, nm):
        b = _idbars(key)
        if not b or len(b["c"]) < 30 or not b.get("pc"):
            return
        pc = float(b["pc"])
        c = b["c"]
        v = [round((c[min(i, len(c) - 1)] / pc - 1) * 100, 3) for i in idx]
        bucket[nm] = v
        a = apx.get(key)
        if ai and a and ai > 0 and a[ai] and a[ai - 1]:
            gaps.append(abs(v[-1] - (a[ai] / a[ai - 1] - 1) * 100))
    for t, nm in (("SPY", "S&P 500"), ("QQQ", "나스닥 100"),
                  ("DIA", "다우존스 30"), ("IWM", "러셀 2000")):
        put(blk["ix"], t, nm)
    for t, nm in sec_etf.items():
        put(blk["sec"], t, nm)
    for t, nm in sty_etf:
        put(blk["sty"], t, nm)
    if not blk["ix"]:
        print("   1D: 지수 계열을 하나도 못 만들었다 — 1일 칸을 만들지 않는다")
        return None
    # 산업그룹 — 종목 분봉을 **산업그룹 시총가중**으로 합친다(2026-08-19 사용자 요청).
    # 🚨 일간 판(build/home_summary._industry)과 **같은 식**이다: 기준일 시총가중,
    #   가중치는 기준일에 고정. 다른 식으로 만들면 같은 이름의 선이 구간마다 다른 뜻이 된다.
    # ⚠ 분류는 GICS 산업그룹(data/members.json 의 grp) — 그 판이 쓰는 바로 그 값이다.
    blk["ind"], blk["ind_sec"] = _intraday_ind(idx)
    if blk["ind"]:
        print("   1D: 산업그룹 %d줄(종목 분봉 시총가중)" % len(blk["ind"]))
    mx = max(gaps) if gaps else 0.0
    print("   1D: 점 %d · 지수 %d · 섹터 %d · 스타일 %d · 표와의 최대 차 %.3f%%p"
          % (len(idx), len(blk["ix"]), len(blk["sec"]), len(blk["sty"]), mx))
    if mx > 0.15:
        print("   🚨 1D: 표와 %.3f%%p 어긋난다 — 싣지 않는다(조용히 어긋나게 두지 않는다)" % mx)
        return None
    blk["gap_max"] = round(mx, 3)
    return blk


def main():
    mbp = os.path.join(DATA, "market_board.json")
    for p in (mbp, os.path.join(DATA, "assets.json"), os.path.join(DATA, "stocks.json")):
        if not os.path.exists(p):
            print("없음:", p)
            return 1
    mb = json.load(io.open(mbp, encoding="utf-8"))
    bases = ((mb.get("basis") or {}).get("base_dates") or {})

    # ── 지수: assets.json 의 일별 패널(표의 지수 줄과 같은 원자료) ──────────
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    adates, apx = A["dates"], A["px"]
    apos = {d: i for i, d in enumerate(adates)}

    # ── 섹터: **섹터 ETF 그 자체**(표의 섹터 줄과 같은 원자료·같은 정의) ──
    SEC_ETF = {"XLK": "IT", "XLF": "금융", "XLV": "헬스케어", "XLY": "경기소비",
               "XLC": "커뮤니케이션", "XLI": "산업재", "XLP": "필수소비", "XLE": "에너지",
               "XLU": "유틸리티", "XLRE": "부동산", "XLB": "소재"}
    sdates, spos = adates, apos          # ETF 도 assets.json 격자다 — 지수 줄과 같은 날짜

    # ── 스타일: 표의 '스타일 ETF' 묶음과 **같은 목록**이어야 한다 ────────────
    # 🚨 최근에 스타일 ETF 를 7종 더 받았지만(SPMO·IVW·RPV·SPLV·SCHD·VYM·PKW) 여기 안 넣는다.
    #   이 파일의 계약은 "각 선의 끝값이 아래 표의 그 칸과 같다" 이고, 그 표에 없는 줄을
    #   그리면 곧바로 깨진다. 표(build/market_board.py 의 STYLE)에 들어가는 날 같이 넣을 것.
    # ⚠ SPY·IWM 은 뺀다 — 화면(index.html 의 ST_SKIP)이 그 둘을 스타일 묶음에서 빼고
    #   지수 줄로 올린다. 여기서만 넣으면 그림에 있는 선이 표에 없다.
    STY_ETF = [("SPMO", "모멘텀"), ("IVW", "성장"), ("IVE", "가치"), ("QUAL", "퀄리티"),
               ("SPLV", "저변동"), ("SCHD", "고배당"), ("SDY", "배당성장"), ("RSP", "동일가중")]

    out = {"note": ("홈 '기간별 수익률' 위 시계열. 🚨 끝점이 아래 표의 그 칸과 같도록 "
                    "표와 **같은 정의**로 만든다 — 섹터는 기준일 대비 종목별 비율의 평균이다. "
                    "만든 곳 build/home_perf.py."),
           "as_of": mb.get("as_of"), "maxpt": MAXPT,
           "base_dates": {k: bases.get(k) for k in HZ},
           "series": {}}

    # ── 🚨 1일 — 여기만 원천이 다르다(2026-08-19 사용자 요청) ──────────────
    #   일간 종가로 「1일」을 그리면 **점이 둘**이라 선이 아니라 직선 한 도막이다.
    #   하루를 그리려면 분봉뿐이다 → build/refresh_intraday.py 가 받아 둔
    #   data/id/_SPY.json 같은 계열을 쓴다(전일 종가 대비 %).
    # ⚠ 그래서 이 칸의 끝점은 표의 1일 칸과 **정확히 같지 않다.** 분봉의 마지막 봉은
    #   15:59 이고 공식 종가는 그 뒤 단일가로 정해지기 때문이다. 아래에서 그 차이를
    #   재서 찍고, 크면(0.15%p 초과) 아예 안 싣는다 — 조용히 어긋나게 두지 않는다.
    # ⚠ 세션 날짜가 일간 기준일과 다르면(장중 잡이 아직 안 돈 아침) **1일 칸을 안 만든다.**
    #   탭이 잠깐 사라지는 편이, 어제 것을 오늘이라 말하는 것보다 낫다.
    d1 = _intraday_block(out["as_of"], adates, apx, SEC_ETF, STY_ETF)
    if d1:
        out["series"]["1D"] = d1            # 🚨 먼저 넣는다 — 화면 탭 순서가 이 순서다
        out["base_dates"]["1D"] = d1["dates"][0]

    for hz in HZ:
        b = bases.get(hz)
        if not b:
            continue
        # 지수
        ai = apos.get(b)
        si = spos.get(b)
        if ai is None or si is None:
            print("  ⚠ %s 기준일 %s 가 패널에 없다 — 이 구간은 건너뛴다" % (hz, b))
            continue
        aidx = thin(list(range(ai, len(adates))), MAXPT)
        sidx = thin(list(range(si, len(sdates))), MAXPT)
        blk = {"dates": [adates[i] for i in aidx], "ix": {}, "sec": {}, "sty": {},
               "sec_dates": [sdates[i] for i in sidx]}
        for t, nm in IX:
            a = apx.get(t)
            if not a or a[ai] in (None, 0):
                continue
            blk["ix"][nm] = [None if a[i] is None else round((a[i] / a[ai] - 1) * 100, 2)
                             for i in aidx]
        for _t, nm in SEC_ETF.items():
            a = apx.get(_t)
            if not a or a[si] in (None, 0):
                continue
            blk["sec"][nm] = [None if a[i] is None else round((a[i] / a[si] - 1) * 100, 2)
                              for i in sidx]
        # 스타일 — 섹터와 같은 격자·같은 기준일. 자료가 기준일에 없으면 그 줄만 뺀다
        # (0 으로 채우지 않는다 — 상장 전 구간을 '수익 0' 으로 그리게 된다).
        for _t, nm in STY_ETF:
            a = apx.get(_t)
            if not a or a[si] in (None, 0):
                continue
            blk["sty"][nm] = [None if a[i] is None else round((a[i] / a[si] - 1) * 100, 2)
                              for i in sidx]
        out["series"][hz] = blk

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    kb = os.path.getsize(OUT) / 1024.0
    print("→ %s (%.0fKB)" % (OUT, kb))
    for hz in HZ:
        s2 = out["series"].get(hz)
        if not s2:
            continue
        print("   %-4s 기준 %s · 점 %d · 지수 %d · 섹터 %d · 스타일 %d"
              % (hz, out["base_dates"][hz], len(s2["dates"]), len(s2["ix"]),
                 len(s2["sec"]), len(s2["sty"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
