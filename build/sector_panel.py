# -*- coding: utf-8 -*-
"""build/sector_panel.py — 섹터 11 + GICS 산업그룹 24를 한 표에 → data/sector_panel.json

## 왜 있나 (2026-08-19 사용자 지시)

  "섹터 탭을 추가해서 섹터랑 세부섹터 관련된 정보를 한눈에 볼수있게해줘"

  ⚠ sector.html 은 2026-08-12 에 **메뉴에서 뺐던 칸**이다. 그때 사유는
    «11섹터의 오늘 등락은 홈의 기간별 수익률 표가 이미 보여 준다» 였다 —
    두 화면 사이에 낀 채 어느 쪽도 더 잘 답하지 못했다.
  🚨 그래서 같은 것을 다시 만들지 않는다. 이 화면이 홈과 다른 점은 **세부단**이다:
    섹터를 열면 그 안의 GICS 산업그룹이 펴진다. 홈은 섹터 한 줄로 끝난다.
    (홈은 1일 구간에서만 산업그룹을 만든다 — 여기는 전 기간을 만든다.)

## 두 단의 계산이 다르다 — 그래서 안 합쳐진다

  · 섹터 = **섹터 ETF**(XLK·XLF…)의 가격 수익률. 홈이 쓰는 바로 그 수치를 그대로 쓴다.
    🚨 여기서 따로 계산하면 같은 섹터가 두 화면에서 다른 수가 된다 — 이 저장소가
      되풀이해 겪은 사고다. 홈 산출물(data/home_perf.json)을 **읽어서** 옮긴다.
  · 산업그룹 = 유니버스 종목의 **기준일 시총가중** 수익률(GICS 산업그룹 · data/members.json 의 grp).
    산업그룹에는 ETF 가 없어 달리 만들 방법이 없다.
  ⚠ 그래서 산업그룹들을 시총가중해도 그 섹터 ETF 수익률과 정확히 같아지지 않는다.
    ETF 는 부동주 가중이고 편입 종목도 다르다. 화면이 그 사실을 적는다.

  ⚠ 3종 미만이 담긴 산업그룹은 만들지 않는다(home_perf 와 같은 취급).

    python build/sector_panel.py
"""
from __future__ import annotations
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "sector_panel.json")
HZ = [("1W", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("12M", 252), ("YTD", None)]
MIN_MEMBERS = 3

_SEC_KO = {"Information Technology": "IT", "Financials": "금융", "Health Care": "헬스케어",
           "Consumer Discretionary": "경기소비", "Communication Services": "커뮤니케이션",
           "Industrials": "산업재", "Consumer Staples": "필수소비", "Energy": "에너지",
           "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재"}


def main() -> int:
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts, stocks = st["pxd_dates"], st["stocks"]
    mem = (json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8")) or {}).get("members") or {}
    n = len(dts)

    # 종목 → (산업그룹, 섹터한글, 시총). 하나라도 없으면 뺀다 — 추측으로 채우지 않는다.
    rows = []
    for x in stocks:
        g = ((mem.get(x["t"]) or {}).get("grp") or "").strip()
        ko = _SEC_KO.get(x.get("sector") or "")
        mc = (x.get("fund") or {}).get("mc")
        if g and ko and mc and mc > 0:
            rows.append((x["t"], g, ko, float(mc)))
    print("유니버스 %d종 중 산업그룹·섹터·시총이 다 있는 것 %d종" % (len(stocks), len(rows)))

    px = {}
    for t, _g, _k, _m in rows:
        p = os.path.join(SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        a = (json.load(io.open(p, encoding="utf-8")) or {}).get("pxd") or []
        if a:
            px[t] = a + [None] * (n - len(a))
    print("  종가 계열을 읽은 종목 %d종" % len(px))

    def base_idx(span):
        if span is None:                      # YTD — 직전 해 마지막 거래일
            y = dts[-1][:4]
            for i in range(n - 1, -1, -1):
                if dts[i][:4] < y:
                    return i
            return 0
        return max(0, n - 1 - span)

    grp_sec, out_hz = {}, {}
    for t, g, ko, _m in rows:
        grp_sec[g] = ko
    for label, span in HZ:
        bi = base_idx(span)
        acc, wsum, cnt = {}, {}, {}
        for t, g, _ko, mc in rows:
            a = px.get(t)
            if not a:
                continue
            p0, p1 = a[bi], a[n - 1]
            if not p0 or not p1:
                continue                      # ⚠ 기준일이나 오늘 값이 없으면 그 종목은 뺀다
            acc[g] = acc.get(g, 0.0) + mc * (p1 / p0 - 1) * 100.0
            wsum[g] = wsum.get(g, 0.0) + mc
            cnt[g] = cnt.get(g, 0) + 1
        blk = {}
        for g in acc:
            if cnt[g] < MIN_MEMBERS or wsum[g] <= 0:
                continue                      # 3종 미만 그룹은 만들지 않는다
            blk[g] = {"ret": round(acc[g] / wsum[g], 2), "n": cnt[g],
                      "sec": grp_sec.get(g, "")}
        out_hz[label] = {"base": dts[bi], "grp": blk}
        print("  %-4s 기준 %s · 산업그룹 %d개" % (label, dts[bi], len(blk)))

    # 섹터 줄은 **홈 산출물을 그대로 옮긴다** — 여기서 다시 계산하면 두 화면이 갈린다.
    sec = {}
    hp = os.path.join(DATA, "home_perf.json")
    if os.path.exists(hp):
        H = json.load(io.open(hp, encoding="utf-8"))
        for label, _s in HZ:
            b = ((H.get("series") or {}).get(label) or {}).get("sec") or {}
            sec[label] = {k: (v[-1] if isinstance(v, list) and v else None) for k, v in b.items()}
        print("  섹터 줄은 home_perf.json 에서 옮겼다(구간 %d개)" % len(sec))
    else:
        print("  ⚠ home_perf.json 이 없다 — 섹터 줄 없이 만든다(산업그룹만)")

    doc = {
        "note": "섹터(ETF) + GICS 산업그룹(유니버스 시총가중)을 한 표에. "
                "🚨 두 단의 계산이 다르다 — 섹터는 섹터 ETF 의 가격 수익률(홈이 쓰는 그 수치를 "
                "그대로 옮겼다)이고, 산업그룹은 유니버스 종목의 기준일 시총가중이다. "
                "산업그룹에는 ETF 가 없어 달리 만들 방법이 없다. 그래서 산업그룹을 합쳐도 "
                "그 섹터 ETF 수익률과 정확히 같아지지 않는다(ETF 는 부동주 가중이고 편입도 다르다).",
        "as_of": dts[-1],
        "n_stocks": len(rows), "n_priced": len(px), "min_members": MIN_MEMBERS,
        "sec_ko": _SEC_KO,
        "hz": [h[0] for h in HZ],
        "sec": sec,
        "ind": out_hz,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
