# -*- coding: utf-8 -*-
"""build/strategy_charts.py — 랩 전략 상세 차트 묶음 → data/strategy_charts.json

왜 따로 파나. 배포 전략 카드에는 곡선·낙폭·연도별·위기구간이 다 있는데 랩 전략 카드에는
작은 스파크라인 하나뿐이었다. 같은 것을 보여주려면 곡선 자료가 필요한데, 그걸 목록
페이로드(strategy_index.json)에 넣으면 목록만 보려는 사람도 300KB를 더 받는다.

그래서 **목록과 상세를 나눈다** — 목록은 지금대로 두고, 전략을 처음 눌렀을 때 이 파일을
한 번 받는다. 홈이 원본 대신 슬림 묶음을 읽는 것과 같은 규약이다.

수치는 각 백테스트가 **전체 계열에서** 계산해 둔 것을 그대로 옮긴다(curve_pack).
여기서 다시 계산하지 않는다 — 줄인 곡선에서 낙폭을 다시 재면 골짜기가 표본에서 빠져
카드에 적힌 MDD와 그림이 어긋난다.

  python build/strategy_charts.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_charts.json")


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def slim(c):
    """브라우저가 받는 묶음에서 **안 그리는 계열을 뺀다.** 값은 고치지 않는다.

    원본은 지수를 셋 들고 있는데(S&P 500 · NASDAQ 100 · 동일가중 S&P 500) 마지막 것은
    생존편향 눈금 전용이라 화면에 선으로 그리지 않는다(tech_backtest.load_index_tr 머리말).
    안 빼면 안 그리는 계열이 차트마다 실려 브라우저가 그만큼 더 받는다(월별을 넣자
    2.0 → 3.0MB 가 됐다).
    """
    keep = ("S&P 500", "NASDAQ 100")
    m = c.get("monthly")
    if m:
        c = dict(c, monthly=[
            (dict(row, i={k: v for k, v in row["i"].items() if k in keep})
             if row.get("i") else row) for row in m])
    for _k in ("idx", "idx_dd"):
        if isinstance(c.get(_k), dict):
            c = dict(c, **{_k: {k2: v2 for k2, v2 in c[_k].items() if k2 in keep}})
    if c.get("yearly"):
        c = dict(c, yearly=[
            (dict(y, i={k2: v2 for k2, v2 in y["i"].items() if k2 in keep})
             if isinstance(y.get("i"), dict) else y) for y in c["yearly"]])
    return c


def main() -> int:
    out, src = {}, {}

    # sid 접두사는 strategy_index.py가 붙이는 것과 **반드시 같아야** 한다.
    # 어긋나면 화면이 차트를 못 찾고, 그건 '차트가 없는 전략'처럼 보인다.
    for fn, key, pre in (("tech_strategies.json", "strategies", "t-"),
                         ("asset_strategies.json", "strategies", "a-")):
        d = load(fn) or {}
        for r in (d.get(key) or []):
            c = r.get("chart")
            if c:
                c = slim(c)
                out[pre + r["sid"]] = c
                src[pre + r["sid"]] = fn

    # 🚨 2026-08-14 — **시점정확 곡선이 있으면 그것으로 덮는다.**
    #   사용자 지시("소급은 다 없애고 시점정확 pit만"). 종전에는 카드 머리 숫자만 PIT 으로
    #   바뀌고 그 밑 그림은 소급 곡선이 남아, 한 카드 안에서 숫자와 그림이 **다른 유니버스**를
    #   말했다. 편입 종목이 갈리므로 두 곡선은 실제로 다르다(x-amihud 는 CAGR 이 44.82%p).
    # ⚠ 다시 계산하지 않는다. pit_backtest 가 랩과 **같은 curve_pack** 으로 만든 것을 옮긴다.
    _pit = (load("pit_strategies.json") or {}).get("strategies") or []
    _npit = 0
    for r in _pit:
        c = r.get("chart")
        if c and c.get("dates"):
            out["t-" + r["sid"]] = slim(c)
            src["t-" + r["sid"]] = "pit_strategies.json"
            _npit += 1

    # 기각 재검은 배포 원장과 같은 스키마(dates·nav·bench·dd·yearly)를 이미 갖고 있다.
    ab = (load("archive_backtests.json") or {}).get("strategies") or {}
    for sid, b in ab.items():
        if b.get("dates") and b.get("nav"):
            out["r-" + sid] = {"dates": b["dates"], "nav": b["nav"],
                               "bench": b.get("bench") or [],
                               "dd": b.get("dd") or [], "dd_b": b.get("dd_b") or [],
                               "yearly": b.get("yearly") or []}
            src["r-" + sid] = "archive_backtests.json"

    # 🚨 지수(S&P 500·NASDAQ 100) 월별을 **한 벌만** 싣는다. 배포 원장 전략은 자기 레코드에
    #   지수를 안 갖고 있어(대조군이 모전략·동일가중인 것도 있다) 같은 표를 못 그렸다 —
    #   그래서 카드마다 구성이 달랐다. 여기서 공유 계열을 주면 두 렌더러가 같은 블록을 쓴다.
    # ⚠ 새로 계산하지 않는다. 랩 백테스트가 이미 만든 monthly 의 i 칸을 그대로 옮긴다.
    idx_m, best = {}, 0
    for c in out.values():
        m = c.get("monthly") or []
        if len(m) > best and any(r.get("i") for r in m):
            best = len(m)
            idx_m = {}
            for r in m:
                for lab, v in (r.get("i") or {}).items():
                    idx_m.setdefault(lab, {})[r["m"]] = v

    doc = {
        "idx_monthly": idx_m,
        "note": "랩 전략 상세 차트(곡선·낙폭·연도별). 목록 페이로드와 분리해 전략을 처음 "
                "눌렀을 때 한 번만 받는다. 수치는 각 백테스트가 전체 계열에서 계산한 것을 "
                "그대로 옮긴 것이며 여기서 다시 계산하지 않는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 🚨 2026-09-03 — **곡선마다 어느 파일에서 왔는지 싣는다.** 종전에는 src 를 여기서
        #   계산만 하고 안 실었다. 그래서 validate_site 의 끝점 대조가 «차트가 랩과 다르다» 를
        #   잡고도 **원인을 못 갈랐다** — 「strategy_charts 를 안 구웠다」와 「구웠는데 원천
        #   (pit_strategies)이 구조적으로 낡았다」가 같은 오류로 나왔다. 뒤엣것은 다시 구워도
        #   안 낫는데 안내문이 「다시 돌릴 것」이라 사람을 헛돌게 했고, refresh-tech 가
        #   그 오류로 두 번 죽었다(08-29 · 09-02). 출처를 실으면 검사가 둘을 가른다.
        "src": src,
        "src_note": "곡선마다 그 값을 옮겨 온 파일. t-* 중 pit_strategies.json 인 것은 "
                    "시점정확 레그이고, 그 파일은 러너가 못 굽는다(가격 캐시가 커밋 금지) — "
                    "끝점이 랩과 갈리는 것은 대개 그 구조 때문이지 이 스크립트를 안 돌려서가 아니다.",
        "n": len(out), "charts": out,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")

    # 통합 목록에 있는데 차트가 없는 전략을 드러낸다 — 조용히 비면 '원래 없는 것'처럼 보인다.
    ix = load("strategy_index.json") or {}
    miss = [r["sid"] for r in (ix.get("items") or [])
            if r["sid"] not in out and r.get("src") != "배포 원장"]
    print("랩 차트 %d개(그중 시점정확 곡선 %d개) · %.0fKB"
          % (len(out), _npit, os.path.getsize(OUT) / 1024))
    if miss:
        print("  ⚠ 차트 없는 랩 전략 %d건: %s" % (len(miss), ", ".join(miss[:8])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
