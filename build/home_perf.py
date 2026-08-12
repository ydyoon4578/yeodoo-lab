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
HZ = ["1M", "3M", "6M", "12M", "YTD"]
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
    STY_ETF = [("MTUM", "모멘텀"), ("QUAL", "퀄리티"), ("IVE", "가치"), ("USMV", "저변동"),
               ("RPG", "성장"), ("SDY", "배당성장"), ("SPHB", "고베타"), ("SIZE", "중소형"),
               ("RSP", "동일가중")]

    out = {"note": ("홈 '기간별 수익률' 위 시계열. 🚨 끝점이 아래 표의 그 칸과 같도록 "
                    "표와 **같은 정의**로 만든다 — 섹터는 기준일 대비 종목별 비율의 평균이다. "
                    "만든 곳 build/home_perf.py."),
           "as_of": mb.get("as_of"), "maxpt": MAXPT,
           "base_dates": {k: bases.get(k) for k in HZ},
           "series": {}}

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
