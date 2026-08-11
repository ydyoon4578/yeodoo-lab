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
# 🚨 2026-08-11 — 앵커를 **경기 곡선에 맞췄다**(+0.22, 사용자 지적).
#   종전 배열은 침체 0.00 · 골디락스 0.16 … 이었는데, 화면의 두 곡선은 이렇게 생겼다:
#       증시 곡선  바닥 0.02 · 정점 0.52
#       경기 곡선  바닥 0.22 · 정점 0.72   (증시보다 LEAD=0.20 늦다)
#   즉 첫 칸(침체 0.00)이 **증시 바닥**에 붙어 있었다. 그런데 화면은 이 앵커를 전부
#   **경기 곡선 위**에 그린다(점선·「지금」 점·자취 모두 Ye). 7국면은 성장×물가로 정의된
#   **경제** 상태이므로 경기 곡선에 맞아야 한다.
#   그 어긋남이 그림에서 이렇게 보였다 —
#       골디락스(확장·저물가)가 경기 곡선의 **바닥쪽·하강 중** 자리에 놓였다
#       스태그플레이션(둔화·고물가)이 경기 **상승 중** 자리에 놓였다
#   +0.22 밀면 침체가 경기 **바닥**(0.22)에, 과열(확장·고물가)이 경기 **정점**(0.72)에
#   정확히 얹힌다. 우연이 아니라 이 배열이 원래 그렇게 만들어진 것이고, 그림에 옮길 때
#   기준 곡선을 안 맞춘 것이었다.
#   ⚠ 순서 자체는 여전히 **통념**이다(order_basis 참조). 이 랩의 실측은 실제 이력이 이
#     순서대로 안 돈다는 것이다(앞으로 4 · 뒤로 8). 고친 것은 '통념을 그리기로 했으면
#     기준 곡선이라도 맞추자' 이지 '순서가 옳다' 가 아니다.
#   ⚠ 뒤 둘이 1.0 을 넘어 왼쪽 끝으로 감긴다(후기사이클 1.00→0.00 · 연착륙 1.12→0.12).
#     한 바퀴짜리 그림이라 맞는 표시다 — 왼쪽에서 오른쪽으로 읽으면
#     후기사이클 → 연착륙 → 침체 → 골디락스 → 회복 → 과열 → 스태그플레이션 순환이 된다.
ECO_SHIFT = 0.22            # 경기 곡선 바닥. 여기를 바꾸면 7국면이 통째로 따라 움직인다.
_PHASE0 = [
    ("Recession",   "침체",       0.00, "성장 CONTRACTION"),
    ("Goldilocks",  "골디락스",    0.16, "확장 · 저물가"),
    ("Recovery",    "회복",       0.32, "확장 · 물가 안정"),
    ("Overheating", "과열",       0.50, "확장 · 고물가"),
    ("Stagflation", "스태그플레이션", 0.64, "둔화 · 고물가"),
    ("LateCycle",   "후기사이클",   0.78, "둔화 · 물가 안정"),
    ("SoftLanding", "연착륙",     0.90, "둔화 · 저물가"),
]
PHASE = [(k, ko, round((p + ECO_SHIFT) % 1.0, 4), d) for k, ko, p, d in _PHASE0]
POS = {k: p for k, _ko, p, _d in PHASE}

# 곡선 위 네 구획 — 레퍼런스(침체기·회복기·호황기·후퇴기)와 같은 나눔.
# 같은 축이므로 같이 민다. b 가 1 을 넘으면 왼쪽 끝으로 감긴다(wrap).
# ⚠ 이 필드는 지금 화면이 읽지 않는다. 지우지 않고 축만 맞춰 둔다 — 나중에 그릴 때
#   혼자만 옛 축이면 조용히 어긋난다.
BANDS = [(round(a + ECO_SHIFT, 4), round(b + ECO_SHIFT, 4), ko)
         for a, b, ko in [(0.00, 0.24, "침체·바닥"), (0.24, 0.46, "회복"),
                          (0.46, 0.70, "확장·정점"), (0.70, 1.00, "둔화·후퇴")]]

RECENT = 24

# 🚨 창 — 사용자 결정 2026-08-11. 이 파일이 내는 모든 수치가 이 창이다.
#   2015 로 자른 이유는 하나가 아니다:
#     · 섹터 순위를 ETF 로 재면 XLC(2018-06 상장) 때문에 11종이 2018 이후만 완비된다.
#       랩 518종으로 직접 만들면 그 병목이 사라지고 가격이 2009 까지 있다.
#     · 그런데 편출 종목을 되살려 생존편향을 걷는 길은 자료에서 막혔다 — 2015~ PIT 명단의
#       편출 324종 중 가격이 있는 것은 147종뿐이고, 없는 177종이 총 멤버-개월의 52% 다.
#       그리고 그 결손은 무작위가 아니라 **인수·상폐된 쪽**이다(EA·BK·MMC·ATVI…).
#       반만 걷고 PIT 이라 부르면 안 걷힌 절반이 하필 나쁜 결말들이다.
#     → 그래서 걷지 않는다. 대신 **오늘의 518종으로 과거를 잰다는 사실을 화면에 적는다.**
#       창을 2015 로 맞춘 것은 이 랩의 PIT 자료가 시작하는 해와 눈금을 맞추려는 것이다.
WINDOW = "2015-01"

# ── 사전등록 검정 결과(2026-08-11) — **박아 둔다, 다시 재지 않는다** ──────────
# 🚨 매 빌드에 다시 재면 안 된다. 라벨이 바뀌면(최소지속 필터) p 가 따라 움직이고,
#   그러면 화면이 매일 다른 숫자를 말하면서 아무도 어느 것이 등록된 값인지 모르게 된다.
#   여기 값은 PREREG-2026-08-11-REGIME.md 의 주검정을 **필터 전 라벨**로 한 번 돌린 것이다.
#   다시 재려면 새 사전등록이 필요하다.
GROWTH_SPLIT = {
    "prereg": "PREREG-2026-08-11-REGIME.md",
    "when": "2026-08-11",
    "basis": "라벨 필터 적용 전 이력(2009-01~2026-08) · 순환이동 귀무 5000회 · 양측",
    "primary": {"what": "SPY 3개월 선도수익", "not_exp": 7.51, "exp": 3.16,
                "n_not": 39, "n_exp": 170, "gap": 4.34, "p": 0.0112, "pass": True},
    "prior": {"what": "SPY 1개월(사후 발견 — 이것으로 판정하지 않았다)", "p": 0.019},
    "seven": {"what": "7국면 전체가 다음 달을 가르는가", "gap": 2.97, "p": 0.152, "pass": False},
    "family": {"n": 4, "alpha": 0.0125,
               "note": "오늘 국면 축으로 돌린 검정 4건(7국면 · 2분할 1개월 · 2011컷 · 주검정). "
                       "본페로니 0.05/4 = 0.0125 — 주검정 p 0.0112 는 이것도 넘는다."},
    "read": ("7국면 분류는 다음 달 수익을 가르지 못한다(p 0.152). 성장축을 둘로만 쪼개면 "
             "가른다 — 확장이 아닐 때가 확장일 때보다 좋았다. 방향이 히어로 카드의 "
             "교과서적 대응과 반대다."),
}
SURV_NOTE = ("오늘의 518종으로 과거를 잰다 — 그사이 지수에서 빠진 종목은 빠져 있다. "
             "이 랩의 실측으로 그 격차는 유니버스 전체 기준 연 +6.25%p 다.")

# 섹터 월수익을 만들 때 이만큼은 종목이 있어야 그 달 그 섹터를 쓴다.
SEC_MIN_N = 5


def sector_ret_lab(root, window):
    """랩 518종을 GICS 섹터로 묶어 월수익(동일가중)을 만든다.

    🚨 ETF(XLK…) 대신 이걸 쓰는 이유: XLC 가 2018-06 에야 상장해 ETF 로는 11개 섹터가
      2018 이후만 완비된다. 랩 가격은 2009 부터 518종 전부 있다.
    ⚠ 대조군도 같은 유니버스로 잡는다 — 그 달 **전체 518종 동일가중**. SPY(시총가중)를
      빼면 '동일가중 대 시총가중' 차이가 섹터 순위에 섞인다. 같은 자로 재야 한다.
    """
    st = json.load(io.open(os.path.join(root, "data", "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    sec = {x["t"]: x.get("sector") for x in st["stocks"]}
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i                      # 그 달의 마지막 거래일 인덱스
    months = sorted(me)

    px = {}
    for t in sec:
        fp = os.path.join(root, "data", "sd", t + ".json")
        if not os.path.exists(fp):
            continue
        a2 = json.load(io.open(fp, encoding="utf-8")).get("pxd")
        if isinstance(a2, list) and len(a2) == len(dates):
            px[t] = a2

    ret = collections.defaultdict(dict)
    allr = {}
    for k in range(1, len(months)):
        m1 = months[k]
        if m1 < window:
            continue
        i0, i1 = me[months[k - 1]], me[m1]
        by, tot = collections.defaultdict(list), []
        for t, a2 in px.items():
            p0, p1 = a2[i0], a2[i1]
            if p0 and p1 and p0 > 0:
                r = (p1 / p0 - 1) * 100
                tot.append(r)
                if sec.get(t):
                    by[sec[t]].append(r)
        if tot:
            allr[m1] = sum(tot) / len(tot)
        for s2, v in by.items():
            if len(v) >= SEC_MIN_N:
                ret[s2][m1] = sum(v) / len(v)
    return ret, allr, len(px)

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


def sector_by_price(reg_json, root):
    """주가 기준 — 그 국면의 섹터 월평균 − 같은 달 전체 518종 동일가중 평균(%p).

    🚨 빼는 이유: 안 빼면 '어느 국면이 통째로 좋았나'가 순위를 지배한다.
      레퍼런스 도표도 제목에 '벤치마크 대비 상대성과에 의거'라고 적어 두었다.
    ⚠ 대조군을 SPY 가 아니라 같은 유니버스의 동일가중으로 잡았다 — 자를 하나로 맞춘다.
    """
    ret, allr, nstk = sector_ret_lab(root, WINDOW)
    reg = {x["dt"][:7]: x["r"] for x in (reg_json.get("history") or [])}
    ko_of = {g: ko for g, ko, _e in SECTORS}
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    nmon = collections.Counter()
    for m in sorted(allr):
        r = reg.get(m)
        if not r:
            continue
        nmon[r] += 1
        for g, series in ret.items():
            if m in series and g in ko_of:
                per[r][g].append(series[m] - allr[m])
    out = {}
    for k, _ko, _p, _d in PHASE:
        rows = [{"ko": ko_of[g], "v": round(statistics.mean(v), 2), "n": len(v)}
                for g, v in (per.get(k) or {}).items() if v]
        rows.sort(key=lambda x: -x["v"])
        out[k] = rows
    return out, {"n_stocks": nstk, "months": dict(nmon), "min_n": SEC_MIN_N,
                 "bench": "같은 달 전체 %d종 동일가중" % nstk}


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
        if _qmon(q) < WINDOW:          # 창 밖 분기는 안 센다(주가 쪽과 같은 창이어야 한다)
            dropped["창 밖"] += 1
            continue
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

    # 🚨 창을 여기서 한 번 자르고 아래 전부가 그 창을 쓴다. 통계마다 따로 자르면
    #   언젠가 한 곳이 빠지고 화면이 두 창을 말한다.
    full_n = len(hist)
    hist = [x for x in hist if x["dt"][:7] >= WINDOW]
    if not hist:
        print("창(%s) 안에 이력이 없다" % WINDOW)
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

    # ── 최근 이동 자취 — 달이 아니라 **런** 단위로 접는다 ────────────────
    # 🚨 pos 는 라벨이 정한다(회복이면 언제나 0.32). 그래서 달마다 점을 찍으면 같은 자리에
    #   15개가 겹쳐 자취가 안 보인다. 라벨이 바뀐 지점만 남기고 머문 개월수를 크기로 준다.
    # ⚠ 런 안에서 위치를 조금씩 흩뿌리지 않는다. 그건 이 랩이 재지 않은 값을 그리는 것이다 —
    #   같은 국면 안에서 '어디쯤인지' 는 이 분류기가 말하지 않는다.
    # ⚠ 마지막 달은 최소지속 필터가 아직 확정 못 한 잠정값이다(regime.json 의 prov).
    _ko1 = {k: ko for k, ko, _p, _dd in PHASE}
    trail = []
    for x in recent:
        if trail and trail[-1]["r"] == x["r"]:
            trail[-1]["months"] += 1
            trail[-1]["to"] = x["dt"]
        else:
            trail.append({"r": x["r"], "ko": _ko1.get(x["r"], x["r"]), "pos": x["pos"],
                          "months": 1, "from": x["dt"], "to": x["dt"]})
    # 앞으로 갔나 뒤로 갔나 — 화살표 색이 이것으로 갈린다. 곡선의 순서는 통념이므로
    # '뒤로' 가 잘못이라는 뜻이 아니다. 실제 이력이 그 순서를 안 따른다는 사실의 표시다.
    for a, b in zip(trail, trail[1:]):
        # 🚨 좌표 크기로 비교하면 안 된다 — 이건 **원**이다. 2026-08-11 에 앵커를 밀면서
        #   후기사이클이 0.78 → 0.00 이 되자 `pos >` 비교가 '뒤로' 를 '앞으로' 로 뒤집었다.
        #   아래 drift 가 쓰는 것과 **같은 원형 규약**(짧은 호 쪽이 앞)으로 맞춘다 —
        #   그래야 앵커를 어디로 밀든 방향 판정이 안 바뀐다(실측: 이동 전후 판정 동일).
        _dp = (b["pos"] - a["pos"]) % 1.0
        b["dir"] = "fwd" if 0 < _dp <= 0.5 else "back"

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

    by_price, pmeta = sector_by_price(d, ROOT)
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
        "window": {"start": WINDOW, "end": hist[-1]["dt"][:7], "months": len(hist),
                   "full_months": full_n,
                   "why": "섹터 순위를 랩 518종으로 직접 만들면서 창을 이 랩 PIT 자료의 "
                          "시작(2015-01)에 맞췄다. 이 화면의 모든 수치가 이 창이다.",
                   "surv": SURV_NOTE},
        "order_basis": ("통념(성장×물가 매트릭스의 관용적 배열) — 실측 아님. "
                        "2026-08-11 에 앵커를 경기 곡선 바닥(%.2f)에 맞췄다 — "
                        "종전에는 증시 곡선 바닥에 붙어 있었다." % ECO_SHIFT),
        # never — 이 창에서 한 번도 없던 칸. "0개월"이 아니라 "없었음"이라고 말하게 한다.
        # 🚨 그 칸을 지우지 않는다. 스태그플레이션이 0인 것은 문턱이 못 닿아서가 아니라
        #   이 창에서 CPI≥4% 인 달이 전부 성장 EXPANSION 이었기 때문이다 — 안 일어난 것이다.
        "phases": [{"k": k, "ko": ko, "pos": p, "desc": ds,
                    "months": months.get(k, 0), "recent": rmonths.get(k, 0),
                    "never": months.get(k, 0) == 0}
                   for k, ko, p, ds in PHASE],
        "growth_split": GROWTH_SPLIT,
        "bands": [{"a": a, "b": b, "ko": ko, **({"wrap": 1} if b > 1 else {})}
                  for a, b, ko in BANDS],
        "now": {"r": cur, "ko": dict((k, ko) for k, ko, _p, _d in PHASE)[cur],
                "pos": POS[cur], "run": run, "dt": hist[-1]["dt"][:7]},
        "recent": recent,
        "recent_n": len(recent),
        # 화면이 그리는 것은 이쪽이다. recent 는 달 단위 원자료로 남긴다.
        "trail": trail,
        "trail_note": ("최근 %d개월의 이동을 국면이 바뀐 지점만 남겨 이은 것. 점 크기는 그 국면에 "
                       "머문 개월수다. 🚨 한 국면 안에서 '어디쯤인지'는 이 분류기가 말하지 않으므로 "
                       "머문 동안 점은 움직이지 않는다. 화살표가 왼쪽으로 가면 교과서 순서와 반대로 "
                       "간 것이다 — 실측으로 그런 이동이 더 많다(아래 drift)." % len(recent)),
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
                    "price_meta": pmeta,
                    "caveat": SURV_NOTE},
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
    print("   창 %s ~ %s · %d개월(전체 %d 중) · 섹터 지수는 랩 %d종 동일가중"
          % (WINDOW, hist[-1]["dt"][:7], len(hist), full_n, pmeta.get("n_stocks", 0)))
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
