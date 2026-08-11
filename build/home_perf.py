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

그리고 섹터 수익률의 정의는 **'기준일 대비 종목별 비율의 평균'** 이다
(home_summary.agg: mean over stocks of px[-1]/px[base] - 1). 일별 리밸런스 지수가 아니다.
그래서 여기서도 **같은 식으로** 경로를 만든다 — 각 구간의 기준일 d0 에 대해
    path[d] = mean_over_stocks( px[d]/px[d0] - 1 )
이렇게 하면 경로의 마지막 점이 표의 그 칸과 글자 그대로 같아진다.

⚠ 구간마다 기준일이 다르므로 **구간마다 경로를 따로 굽는다.** 12개월 경로를 잘라
  다시 기준화하면 안 된다 — 비율의 평균은 곱셈적이지 않아 끝점이 표와 어긋난다.

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

    # ── 섹터: 랩 518종을 GICS 로 묶은 것(표의 섹터 줄과 같은 원자료·같은 정의) ──
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    sdates = S["pxd_dates"]
    spos = {d: i for i, d in enumerate(sdates)}
    sec_of = {x["t"]: x.get("sector") for x in S["stocks"]}
    KO = {"Information Technology": "IT", "Financials": "금융", "Health Care": "헬스케어",
          "Consumer Discretionary": "경기소비", "Communication Services": "커뮤니케이션",
          "Industrials": "산업재", "Consumer Staples": "필수소비", "Energy": "에너지",
          "Utilities": "유틸리티", "Materials": "소재", "Real Estate": "부동산"}
    spx = {}
    for t in sec_of:
        fp = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(fp):
            continue
        a = json.load(io.open(fp, encoding="utf-8")).get("pxd")
        if isinstance(a, list) and len(a) == len(sdates):
            spx[t] = a
    members = {}
    for t, g in sec_of.items():
        if g in KO and t in spx:
            members.setdefault(KO[g], []).append(t)

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
        blk = {"dates": [adates[i] for i in aidx], "ix": {}, "sec": {},
               "sec_dates": [sdates[i] for i in sidx]}
        for t, nm in IX:
            a = apx.get(t)
            if not a or a[ai] in (None, 0):
                continue
            blk["ix"][nm] = [None if a[i] is None else round((a[i] / a[ai] - 1) * 100, 2)
                             for i in aidx]
        for nm, ts in members.items():
            path = []
            for i in sidx:
                vs = []
                for t in ts:
                    a = spx[t]
                    if a[si] and a[i] and a[si] > 0:
                        vs.append(a[i] / a[si] - 1.0)
                path.append(round(sum(vs) / len(vs) * 100, 2) if vs else None)
            blk["sec"][nm] = path
        out["series"][hz] = blk

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    kb = os.path.getsize(OUT) / 1024.0
    print("→ %s (%.0fKB)" % (OUT, kb))
    for hz in HZ:
        s2 = out["series"].get(hz)
        if not s2:
            continue
        print("   %-4s 기준 %s · 점 %d · 지수 %d · 섹터 %d"
              % (hz, out["base_dates"][hz], len(s2["dates"]), len(s2["ix"]), len(s2["sec"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
