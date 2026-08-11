# -*- coding: utf-8 -*-
"""build/regime_cycle.py — 경기 사이클 곡선 위의 좌표를 굽는다 → data/regime_cycle.json

## 왜 별도 스크립트인가

`refresh_regime.py` 는 FRED_API_KEY 가 있어야 돌고 그 키는 Actions 시크릿에만 있다.
이 파일은 **이미 구워진 data/regime.json 만 읽어** 파생값을 만든다 — 네트워크가 필요 없어
아무 PC 에서나 돌고, 화면을 고칠 때마다 곧바로 다시 구울 수 있다.
⚠ 그래서 refresh-regime 워크플로에서 refresh_regime.py **뒤에** 반드시 같이 돌려야 한다.
  안 그러면 국면은 바뀌었는데 곡선 위 점은 어제 자리에 남는다.

## 곡선 위 위치를 무엇으로 정하나 — 🚨 이건 실측이 아니라 교과서다

성장×물가 3×3 에서 나온 7개 이름을 사이클 한 바퀴에 늘어놓는 순서는 **통념**이다:

    침체(바닥) → 골디락스(확장·저물가) → 회복(확장·물가안정) → 과열(확장·고물가, 정점)
    → 스태그플레이션(둔화·고물가) → 후기사이클(둔화·물가안정) → 연착륙(둔화·저물가) → 다시 바닥

물가가 성장을 뒤따라 오르고 뒤따라 내린다는 전제에서 나온 배열이고, 이 랩이 검정한 것이
아니다. 히어로 카드가 '교과서적 대응'에 이미 같은 딱지를 붙이고 있다(refresh_regime.py MATRIX).

🚨 **이 랩의 212개월은 이 순서대로 돌지 않는다.** 실측:
     · 전이 32건이 순서쌍 14개에 흩어져 있고 가장 많은 쌍이 5건 — 방향을 판정할 표본이 없다
     · 이웃 쌍이 대칭이다: 골디락스↔회복 5:5 · 회복↔후기 4:3
     · 런 33개 중 12개가 1개월, 25개가 6개월 미만
   그래서 이 파일은 곡선을 '경로'로 팔지 않는다. 최근 24개월 점을 **같은 곡선 위에 같이**
   찍어서, 점들이 순서대로 나아가지 않는다는 사실을 그림 안에서 보이게 한다.

## 선호 업종을 곡선에 얹는 방법 — 두 가지 자를 **따로** 낸다

레퍼런스(증권사 도표)는 국면마다 유리한 업종을 곡선에 붙이고, 그것을 '실적 기준'과
'주가 기준' 두 장으로 나눠 그린다. 이 랩 자료로 둘 다 만들 수 있다.

🚨 처음에 '못 한다'고 판단했는데 그건 **추정량이 나빴던 것**이지 자료가 없어서가 아니었다.
  섹터마다 '월평균이 가장 높았던 국면'을 argmax 로 뽑으니 11개 전부가 표본 20개월 미만
  구간(연착륙 13 · 후기사이클 7)에 걸렸다 — 얇은 칸이 우연으로 이긴다. 자를 바꿨다:

  · **주가 기준** = 그 국면의 섹터 월평균 − **같은 국면의 SPY 월평균**.
    레퍼런스 11.png 이 제목에 적어 둔 그대로다("벤치마크 대비 상대성과에 의거").
    국면마다 섹터를 **줄 세우고** 상위만 쓴다. 섹터에 국면을 배정하지 않는다.
  · **실적 기준** = 그 국면에 속한 분기의 **섹터 합산 순이익 YoY 중앙값**.
    data/fx/*.json(SEC XBRL 분기) 494종에서 만든다.
    YoY 는 **같은 종목이 두 분기에 다 있을 때만** 센다(구성 변화가 성장률로 새지 않게).
    기저가 적자인 분기는 버린다(성장률이 뜻을 잃는다). 평균이 아니라 중앙값을 쓴다 —
    에너지 과열 구간처럼 기저효과로 +197% 가 나오는 분기가 평균을 지배한다.

⚠ 이 자료가 못 하는 것을 그대로 적는다:
  · data/fx 는 **오늘의 518종**이다. 과거 섹터 실적을 오늘 멤버로 계산하므로 생존편향이 있다.
    가격 쪽에는 PIT 장치가 있지만 섹터 실적에는 없다.
  · 국면별 분기 수가 얇다(후기사이클은 3분기 미만이라 실적 기준을 아예 안 낸다).
  · 두 자는 서로 다른 것을 잰다. 침체에서 실적 상위는 헬스케어·필수소비인데 주가 상위는
    소재·경기소비·기술이다 — **주가가 실적보다 앞선다**는 레퍼런스의 주장이 이 자료에도 보인다.
    그것이 두 장을 나눠 그리는 이유다.

    python build/regime_cycle.py
"""
import collections
import glob
import io
import json
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "regime.json")
OUT = os.path.join(DATA, "regime_cycle.json")

# 사이클 한 바퀴에서의 자리(0=바닥, 0.5=정점, 1=다시 바닥).
# ⚠ 이 숫자는 통념이다. 바꾸려면 위 독스트링의 근거부터 바꿀 것.
PHASE = [
    ("Recession",   "침체",       0.00, "성장 CONTRACTION"),
    ("Goldilocks",  "골디락스",    0.16, "확장 · 저물가"),
    ("Recovery",    "회복",       0.32, "확장 · 물가 안정"),
    ("Overheating", "과열",       0.50, "확장 · 고물가"),
    ("Stagflation", "스태그플레이션", 0.64, "둔화 · 고물가"),
    ("LateCycle",   "후기사이클",   0.78, "둔화 · 물가 안정"),
    ("SoftLanding", "연착륙",     0.90, "둔화 · 저물가"),
]
POS = {k: p for k, _ko, p, _d in PHASE}

# 곡선 위 네 구획 — 레퍼런스(침체기·회복기·호황기·후퇴기)와 같은 나눔.
BANDS = [(0.00, 0.24, "침체·바닥"), (0.24, 0.46, "회복"),
         (0.46, 0.70, "확장·정점"), (0.70, 1.00, "둔화·후퇴")]

RECENT = 24

# GICS 섹터 → (한글, SPDR ETF). sector_perf 는 ETF 키, fx 는 GICS 이름을 쓴다 — 둘을 잇는다.
SECTORS = [
    ("Information Technology", "기술",       "XLK"),
    ("Financials",             "금융",       "XLF"),
    ("Health Care",            "헬스케어",    "XLV"),
    ("Consumer Discretionary", "경기소비",    "XLY"),
    ("Communication Services", "커뮤니케이션", "XLC"),
    ("Industrials",            "산업재",      "XLI"),
    ("Consumer Staples",       "필수소비",    "XLP"),
    ("Energy",                 "에너지",      "XLE"),
    ("Utilities",              "유틸리티",    "XLU"),
    ("Materials",              "소재",       "XLB"),
    ("Real Estate",            "부동산",      "XLRE"),
]
TOPN = 3            # 국면마다 곡선에 얹을 업종 수

# ── 레퍼런스 도표(Sector Rotation) 원문 ─────────────────────────────────────
# 🚨 이 블록은 **교과서다.** 이 랩이 잰 것이 아니라 널리 쓰이는 섹터 로테이션 도표의
#   내용을 그대로 옮겨 적은 것이다. 화면이 그 사실을 말하고, 아래 cmp 가 이 랩의
#   실측과 얼마나 겹치는지를 같이 낸다 — 겹치지 않으면 겹치지 않는 대로 보인다.
# 곡선 위 자리(pos)는 증시 곡선 기준이다. 원 도표의 좌우 배열을 그대로 따랐다.
REF_TITLE = "Sector Rotation (교과서 도표)"
# 🚨 자리(pos)는 x축 0~1 위의 값이다. 증시 곡선은 0.02 에서 바닥, 0.52 에서 정점이고
#   경기 곡선은 그것을 REF_LEAD 만큼 오른쪽으로 민 것이다 — 그래서 증시가 앞선다.
#   박스 다섯은 원 도표의 좌우 배열을 그대로 따라 고르게 벌려 둔다.
REF_BOXES = [
    (0.02, "증시 바닥",  ["금융", "기술", "경기소비"],       "Finance · Technology · Cyclicals"),
    (0.27, "강세장",     ["기술", "산업재", "소재"],          "Technology · Industrials · Basic Materials"),
    (0.52, "증시 정점",  ["소재", "에너지", "필수소비"],       "Basic Materials · Energy · Staples"),
    (0.77, "약세장",     ["에너지", "필수소비", "헬스케어"],    "Energy · Staples · Healthcare"),
    (0.96, "약세장 후반", ["헬스케어", "유틸리티", "금융"],     "Healthcare · Utilities · Finance"),
]
# 증시 곡선의 단계(원 도표의 분홍 알약)
REF_MKT = [(0.02, "증시 바닥"), (0.27, "강세장"), (0.52, "증시 정점"),
           (0.77, "약세장"), (0.96, "약세장 후반")]
# 경기 곡선의 단계(원 도표의 파란 알약) — 증시보다 REF_LEAD 만큼 뒤에 온다
REF_ECO = [(0.22, "완전 침체"), (0.47, "회복 초기"), (0.72, "완전 회복"), (0.97, "침체 초기")]
# 원 도표의 단계 ↔ 이 랩의 국면. 실측 비교를 붙이려면 이 다리가 있어야 한다.
REF_MAP = [("증시 바닥", "Recession"), ("강세장", "Recovery"), ("증시 정점", "Overheating"),
           ("약세장", "LateCycle"), ("약세장 후반", "SoftLanding")]
REF_LEAD = 0.20     # 증시 곡선을 경기 곡선보다 이만큼 앞세워 그린다(원 도표의 시차)
MIN_MATCH = 8       # 섹터 합산 YoY 를 세려면 두 분기에 다 있는 종목이 이만큼은 있어야 한다
MIN_QTR = 3         # 그 국면에 분기가 이만큼도 없으면 실적 기준을 내지 않는다


def _cq(dt):
    """분기말 날짜 → 달력분기. 회계연도가 회사마다 달라 달력분기로 묶어야 합산이 된다."""
    y, m = int(dt[:4]), int(dt[5:7])
    return "%dQ%d" % (y, (m - 1) // 3 + 1)


def _prevq(q):
    return "%dQ%d" % (int(q[:4]) - 1, int(q[5]))


def _qmon(q):
    """분기 → 그 분기 마지막 달(국면 이력과 맞추는 열쇠)."""
    return "%04d-%02d" % (int(q[:4]), int(q[5]) * 3)


def sector_by_price(reg_json):
    """주가 기준 — 그 국면의 섹터 월평균 − 같은 국면의 SPY 월평균(%p).

    🚨 SPY 를 빼는 이유: 빼지 않으면 '어느 국면이 통째로 좋았나'가 순위를 지배한다.
      연착륙(13개월)은 SPY 자체가 +2.86%/월이라 모든 섹터가 좋아 보인다.
      레퍼런스 11.png 도 제목에 '벤치마크 대비 상대성과에 의거'라고 적어 두었다.
    """
    sp = reg_json.get("sector_perf") or {}
    spy = (reg_json.get("asset_perf") or {}).get("SPY") or {}
    out = {}
    for k, _ko, _p, _d in PHASE:
        rows = []
        for _g, ko, etf in SECTORS:
            v = (sp.get(etf) or {}).get(k)
            b = spy.get(k)
            if v is None or b is None:
                continue
            rows.append({"ko": ko, "v": round(v - b, 2)})
        rows.sort(key=lambda x: -x["v"])
        out[k] = rows
    return out


def sector_by_earnings(reg_json, root):
    """실적 기준 — 그 국면에 속한 분기의 섹터 합산 순이익 YoY 중앙값(%).

    YoY 는 **같은 종목이 두 분기에 다 있을 때만** 센다. 안 그러면 커버리지 변화가
    성장률로 새어 든다(2009년에 없던 회사가 2010년에 생기면 그게 '성장'이 된다).
    기저가 적자인 분기는 버린다 — 적자 대비 성장률은 부호도 크기도 뜻이 없다.
    """
    stk = os.path.join(root, "data", "stocks.json")
    if not os.path.exists(stk):
        return {}, {"reason": "stocks.json 없음"}
    sec = {s["t"]: s.get("sector")
           for s in json.load(io.open(stk, encoding="utf-8"))["stocks"]}
    reg = {x["dt"][:7]: x["r"] for x in (reg_json.get("history") or [])}

    ni = collections.defaultdict(dict)      # (섹터, 분기) → {티커: 순이익}
    nfile = 0
    for f in glob.glob(os.path.join(root, "data", "fx", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        t, s = d.get("t"), sec.get(d.get("t"))
        if not s:
            continue
        q = ((d.get("tags") or {}).get("ni") or {}).get("q") or []
        if q:
            nfile += 1
        for dt, v in q:
            if v is not None:
                ni[(s, _cq(dt))][t] = float(v)
    if not ni:
        return {}, {"reason": "data/fx 에 순이익 분기 계열이 없다"}

    per = collections.defaultdict(lambda: collections.defaultdict(list))   # 섹터→국면→[yoy]
    dropped = collections.Counter()
    for (s, q), cur in ni.items():
        prv = ni.get((s, _prevq(q)))
        r = reg.get(_qmon(q))
        if not prv or not r:
            dropped["국면·직전분기 없음"] += 1
            continue
        both = [t for t in cur if t in prv]
        if len(both) < MIN_MATCH:
            dropped["짝지어진 종목 %d 미만" % MIN_MATCH] += 1
            continue
        a = sum(cur[t] for t in both)
        b = sum(prv[t] for t in both)
        if b <= 0:
            dropped["기저 적자"] += 1
            continue
        per[s][r].append((a / b - 1) * 100)

    ko_of = {g: ko for g, ko, _e in SECTORS}
    out = {}
    for k, _ko, _p, _d in PHASE:
        rows = []
        for g, vv in per.items():
            xs = vv.get(k) or []
            if len(xs) < MIN_QTR or g not in ko_of:
                continue
            rows.append({"ko": ko_of[g], "v": round(statistics.median(xs), 1), "n": len(xs)})
        rows.sort(key=lambda x: -x["v"])
        out[k] = rows
    return out, {"files": nfile, "dropped": dict(dropped), "min_match": MIN_MATCH, "min_qtr": MIN_QTR}


def main():
    if not os.path.exists(SRC):
        print("없음:", SRC)
        return 1
    d = json.load(io.open(SRC, encoding="utf-8"))
    hist = d.get("history") or []
    if not hist:
        print("history 가 비어 있다 — 굽지 않는다")
        return 1

    seq = [x["r"] for x in hist]

    # ── 지금 ────────────────────────────────────────────────────────────
    cur = (d.get("regime") or {}).get("label")
    if cur != seq[-1]:
        # 🚨 히어로와 이력 마지막이 다르면 곡선이 어느 쪽을 가리켜야 할지 알 수 없다.
        #   조용히 한쪽을 고르지 않는다 — 굽기를 멈춘다.
        print("불일치: regime.label=%s 인데 history 마지막=%s — 굽지 않는다" % (cur, seq[-1]))
        return 2
    if cur not in POS:
        print("모르는 국면 이름: %s — PHASE 에 추가할 것" % cur)
        return 2

    # ── 지금 국면이 몇 달째인가 ──────────────────────────────────────────
    run = 1
    for x in reversed(seq[:-1]):
        if x == cur:
            run += 1
        else:
            break

    # ── 최근 N개월의 자리 ────────────────────────────────────────────────
    recent = []
    for i, x in enumerate(hist[-RECENT:]):
        r = x["r"]
        if r not in POS:
            continue
        recent.append({"dt": x["dt"][:7], "r": r, "pos": POS[r],
                       "age": len(hist[-RECENT:]) - 1 - i})   # 0 = 가장 최근

    # ── 이 곡선을 '경로'로 읽으면 안 되는 근거를 같이 굽는다 ──────────────
    trans = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    pairs = {}
    for a, b in zip(seq, seq[1:]):
        if a != b:
            pairs["%s→%s" % (a, b)] = pairs.get("%s→%s" % (a, b), 0) + 1
    runs, c, n = [], seq[0], 1
    for x in seq[1:]:
        if x == c:
            n += 1
        else:
            runs.append(n); c = x; n = 1
    runs.append(n)
    rec = [x["r"] for x in hist[-RECENT:]]
    # 곡선 순서대로 '앞으로' 간 전이가 몇 건인가 — 통념이 맞다면 이 값이 커야 한다.
    fwd = back = 0
    for a, b in zip(seq, seq[1:]):
        if a == b or a not in POS or b not in POS:
            continue
        dp = (POS[b] - POS[a]) % 1.0
        if 0 < dp <= 0.5:
            fwd += 1
        else:
            back += 1

    months = {}
    for x in seq:
        months[x] = months.get(x, 0) + 1

    # 최근 N개월이 각 자리에 몇 번 있었나 — 곡선 위에 겹쳐 찍는 대신 이 수를 뱃지로 낸다.
    # 🚨 점을 겹쳐 찍으면 12개가 한 점으로 보여 '한 자리에 계속 있었다'로 읽힌다.
    #   실제로는 최근 24개월이 여섯 자리에 흩어져 있다 — 그 사실이 이 그림의 요점이다.
    rmonths = {}
    for x in rec:
        rmonths[x] = rmonths.get(x, 0) + 1

    by_price = sector_by_price(d)
    by_earn, emeta = sector_by_earnings(d, ROOT)

    # 교과서 도표 ↔ 이 랩 실측 — 겹치는 업종을 센다. 겹침이 적으면 적은 대로 낸다.
    _koN = {k: ko for k, ko, _p, _dd in PHASE}
    cmp_rows = []
    for stage, rk in REF_MAP:
        ref = next((b[2] for b in REF_BOXES if b[1] == stage), [])
        mine = [r["ko"] for r in (by_price.get(rk) or [])[:TOPN]]
        mine_e = [r["ko"] for r in (by_earn.get(rk) or [])[:TOPN]]
        cmp_rows.append({
            "stage": stage, "regime": rk, "ko": _koN.get(rk, rk),
            "months": months.get(rk, 0),
            "ref": ref, "price": mine, "earn": mine_e,
            "hit_price": [x for x in ref if x in mine],
            "hit_earn": [x for x in ref if x in mine_e],
        })

    out = {
        "note": ("경기 사이클 곡선 위의 자리. 🚨 곡선의 순서는 통념이고 이 랩이 검정한 것이 아니다 — "
                 "실제 이력은 이 순서대로 돌지 않는다(아래 drift 참조). "
                 "만든 곳 build/regime_cycle.py, 원자료 data/regime.json."),
        "as_of": d.get("as_of"),
        "src_generated": d.get("as_of"),
        "order_basis": "통념(성장×물가 매트릭스의 관용적 배열) — 실측 아님",
        "phases": [{"k": k, "ko": ko, "pos": p, "desc": ds,
                    "months": months.get(k, 0), "recent": rmonths.get(k, 0)}
                   for k, ko, p, ds in PHASE],
        "bands": [{"a": a, "b": b, "ko": ko} for a, b, ko in BANDS],
        "now": {"r": cur, "ko": dict((k, ko) for k, ko, _p, _d in PHASE)[cur],
                "pos": POS[cur], "run": run, "dt": hist[-1]["dt"][:7]},
        "recent": recent,
        "recent_n": len(recent),
        # 레퍼런스 도표 원문 — 화면이 그대로 그린다(교과서라고 화면이 말한다).
        "ref": {"title": REF_TITLE, "lead": REF_LEAD,
                "boxes": [{"pos": p2, "stage": st, "ko": ko3, "en": en}
                          for p2, st, ko3, en in REF_BOXES],
                "mkt": [{"pos": p2, "ko": ko3} for p2, ko3 in REF_MKT],
                "eco": [{"pos": p2, "ko": ko3} for p2, ko3 in REF_ECO],
                "cmp": cmp_rows},
        # 선호 업종 두 자 — 화면은 이 순위를 그대로 얹기만 한다.
        "sectors": {"price": by_price, "earn": by_earn, "topn": TOPN, "earn_meta": emeta,
                    "price_basis": "그 국면의 섹터 월평균 − 같은 국면의 SPY 월평균(%p)",
                    "earn_basis": "그 국면에 속한 분기의 섹터 합산 순이익 YoY 중앙값(%) · "
                                  "짝지어진 종목만 · 기저 적자 분기 제외",
                    "caveat": "🚨 실적 쪽은 오늘의 518종으로 과거를 계산한다 — 생존편향이 있다. "
                              "가격 쪽 PIT 장치가 여기에는 없다."},
        "drift": {
            "trans": trans, "n_months": len(seq),
            "pairs": len(pairs), "pairs_max": max(pairs.values()) if pairs else 0,
            "runs": len(runs), "runs_one": sum(1 for x in runs if x == 1),
            "runs_lt6": sum(1 for x in runs if x < 6),
            "fwd": fwd, "back": back,
            "recent_changes": sum(1 for a, b in zip(rec, rec[1:]) if a != b),
            "recent_labels": len(set(rec)),
        },
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    dr = out["drift"]
    print("→ %s" % OUT)
    print("   지금 %s(%s) · 곡선 위 %.2f · %d개월째" % (cur, out["now"]["ko"], POS[cur], run))
    print("   최근 %d개월 %d개 자리 · 이름 %d종 · 그 사이 전환 %d회"
          % (RECENT, len(recent), dr["recent_labels"], dr["recent_changes"]))
    print("   ⚠ 곡선 순서대로 나아간 전이 %d건 · 거꾸로 간 전이 %d건 — 통념이 이력을 못 설명한다"
          % (dr["fwd"], dr["back"]))
    for k, ko, _p, _dsc in PHASE:
        pr = (by_price.get(k) or [])[:TOPN]
        er = (by_earn.get(k) or [])[:TOPN]
        print("   %-7s 주가 %-34s 실적 %s"
              % (ko,
                 " ".join("%s%+.2f" % (x["ko"], x["v"]) for x in pr) or "—",
                 " ".join("%s%+.0f%%(n%d)" % (x["ko"], x["v"], x["n"]) for x in er) or "표본 부족"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
