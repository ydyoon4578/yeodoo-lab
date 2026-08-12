# -*- coding: utf-8 -*-
"""build/pit_backtest.py — 시점정확(PIT) 멤버십으로 다시 돌린 종목선택 백테스트.

무엇을 푸는가.
  랩 본편(tech_backtest.py)은 **오늘의 유니버스를 과거에 소급**한다. 그 사이 지수에서 빠진
  회사가 하나도 없어 모든 수치가 실제보다 좋게 나온다. 여기서는 매월말 **그때 실제로 지수에
  있던 종목만** 후보로 두고 같은 규칙을 다시 돌린다. 두 결과의 차이가 생존편향의 크기다.

데이터 출처가 둘인 이유.
  · 멤버십 — **위키백과 지수 목록 문서의 과거 리비전**(data/index_history.json,
             build/refresh_index_history.py 산출 · CC BY-SA). SPX∪NDX 합집합을 쓴다.
             ⚠ 2026-08-03 이전엔 사내 DB(public.index_constituents)였고 그 산출물이
             gitignore 라 이 검정이 PC 한 대에 묶여 있었다. 대조 실측은 실질 일치 60/60.
  · 가격  — **yfinance**. 오늘의 유니버스는 랩이 이미 받아 둔 data/sd/*.json 을 그대로 쓰고,
             그 사이 지수에서 빠진 종목만 따로 받아 data/_pit_px_cache.json 에 캐시한다.

  편출 종목의 가격이 왜 대체로 있나. 지수에서 빠지는 사유의 대부분은 '작아져서'이고 그 회사들은
  **여전히 상장돼 거래된다.** yfinance 가 못 주는 것은 인수·합병·상장폐지·심볼 인계된 경우다.
  ⚠ 그 결손이 '방향이 반대라 안전하다'고 생각하기 쉬운데 실측은 반대다 — 받아 온 종목은 전부
  오늘까지 살아 있고, 누락분을 되돌리면 초과수익은 줄어든다. 이 표도 편향을 다 걷어내지 못한다.

  python build/pit_backtest.py
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tech_backtest as TB          # noqa: E402  지표·통계를 다시 구현하지 않는다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "_pit_px_cache.json")
# 🚨 고가·저가 캐시는 **별 파일**이다(2026-08-05). 기존 종가 캐시(147종)를 깨지 않으려는 것이다 —
#   형식을 바꾸면 전량 재수집이 필요하고, 그 사이 PIT 이 통째로 못 돈다. 없으면 없는 대로
#   돌아가고(고가가 필요한 규칙만 빠진다) 받아 두면 그때부터 그 규칙들이 살아난다.
HLCACHE = os.path.join(DATA, "_pit_hl_cache.json")
SHCACHE = os.path.join(DATA, "_pit_sh_cache.json")   # 편출 종목의 시점별 주식수(yfinance)
REUSE = os.path.join(DATA, "pit_reuse.json")         # 티커가 다른 법인에 넘어갔는지(SEC 대조)
OUT = os.path.join(DATA, "pit_strategies.json")

START = "2021-07-01"
# 🚨 이 날짜는 **자료의 한계가 아니라 자료의 품질**로 정했다(2026-08-11, 사용자 결정).
#   자료 한계는 2014-06 이다 — 위키 표에 CIK 컬럼이 생긴 첫 달이고, 그 아래는 티커로만
#   조인하게 되어 개명·재사용을 구별할 수 없다(근거는 fetch_members 주석과
#   build/refresh_index_history.py 머리말). data/index_history.json 은 그대로 2014-06 부터
#   모은다 — 원자료를 좁히지 않는다. 좁히는 것은 **채점 창**뿐이다.
#
#   왜 2021-07 인가. 커버리지에 무릎이 없다 — 2014-06 의 72% 에서 2026 의 100% 까지
#   매끄럽게 오른다. 그래서 어디서 자르든 문턱이 자유도가 되고, 자유도를 결과를 보고
#   고르면 이 랩이 전략에 금지한 사후 맞춤이 된다. 그래서 문턱을 **먼저** 정했다:
#
#       세 커버리지(보유율 · 252일 룩백 채점가능 · 재무)가 모두 90% 이상이고,
#       그 뒤로 다시 90% 아래로 내려가지 않는 첫 달.
#
#   실측으로 그 달이 2021-07 이다(보유율 최저 90.3 · 채점 90.1 · 재무 91.3).
#   ⚠ 대가를 같이 적는다. 관측이 3046 → 1262거래일(−59%)이라 같은 효과크기에서 t 가
#     0.64배로 준다. 그리고 이 창의 월평균 편출 멤버가 58.6종(전 구간 120.3종)이라
#     **PIT 이 잴 대상 자체가 절반**이다 — 창을 깨끗하게 만드는 값이 곧 편향을 재기
#     어렵게 만드는 값이다. 이 맞바꿈은 없앨 수 없고, 여기서는 깨끗한 쪽을 골랐다.
#   ⚠ 문턱을 90 에서 85 나 95 로 바꿔 보지 않는다. 그게 자유도다.
# 🚨 캐시를 받는 시작일은 START 와 **다르다.** 종전에는 같았고, 그래서 편출 종목은 창 첫날
#   이전 가격이 아예 없었다 — 12-1 모멘텀은 12개월, 장기반전은 60개월을 뒤로 본다. 룩백이
#   없으면 그 종목은 점수가 None 이 되어 후보에서 빠지고, **초기 월의 후보가 조용히
#   생존자(랩 518종)로 좁혀진다.** 이 파일이 없애려는 바로 그 편향이 창 앞머리에 남는다.
#   실측으로 그 자국이 보였다 — 멤버 대비 가격 보유율 최저 72.5% / 중앙 88.6% 이고
#   "보유율이 시간에 따라 100% 로" 라고 limits 에 적혀 있었다. 그건 편출이 줄어서가 아니라
#   캐시가 창 시작에 잘려 있어서였다.
#   → 랩 일별 격자(data/stocks.json pxd_dates)와 같은 2009-01-01 부터 받는다. 랩 종목은
#     이미 그 격자를 갖고 있으므로, 이렇게 해야 두 출처가 같은 길이의 이력을 준다.
CACHE_START = "2009-01-01"
TOPN = TB.TOPN

# 가격·거래량만으로 정의되는 규칙. 펀더멘털 규칙은 시점별 재무·주식수가 없어 제외한다 —
# 반쪽만 PIT 로 바꾸면 비교가 성립하지 않는다.
PRICE_SIDS = [
             # 2026-08-12 3차 배치 — PREREG-2026-08-12-MOMENTS.md §4. 결과를 보고 넣으면
             #   사후 선택이므로 **등록과 함께 미리** 넣는다. 둘 다 종가만 쓰므로
             #   편출 종목 종가 캐시로 그대로 돈다(x-amihud 가 막힌 거래량 벽이 없다).
             "x-mommvol", "x-rskew",
             "x-mom12", "x-lowvol", "x-rev1m", "x-52wh", "x-dist200",
              "x-mom-trend", "x-rev1w", "x-minvar", "x-riskbudget", "x-lowbeta",
              "x-snapback", "x-maxlow", "x-max5low", "x-recency", "x-ivol",
              "x-small",   # 시가총액 = 시점별 주식수 × 종가 (아래 SH 참조)
              # 2026-07-30 웹 리서치로 추가. 🚨 여기 안 넣으면 새 규칙이 **소급 t 로만** 판정돼
              # '통과 후보' 가 된다 — 이 파일이 막으려는 바로 그 일이다(소급 t 3.2~3.7 이 나왔다).
              "x-echo", "x-season", "x-coskew",
              # 2026-07-31 추가(가격만 쓰는 것)
              "x-ltrev", "x-lowcorr", "x-cntd",
              # 🚨 2026-08-11 바스켓 크기 6종(PREREG-2026-08-11-BASKET.md). 여기 안 넣으면
              #   짝이 되는 10종판에는 PIT 레그가 있는데 이쪽만 없어서, 같은 점수 함수의
              #   두 규칙이 **서로 다른 잣대로** 판정된다. 위 x-echo 주석과 같은 사유다.
              "x-lowvol-n100", "x-maxlow-n52", "x-max5low-n52",
              # 🚨 2026-08-11 — 랩에 등록돼 소급 t 로 판정되면서 PIT 만 안 받고 있던 것들.
              #   '자료가 없어서' 가 아니라 이 파일에 갈래·배선이 없어서였다(저가 미배선).
              "x-lshock", "x-ongapd", "x-updown",
              # 🚨 2026-08-11 개편 — 채점기를 한 벌로 합치자 '횡단면 사전패스가 필요해서'
              #   못 돌던 것들이 전부 돌게 됐다. 사본을 손으로 옮길 때는 2단 구조를
              #   표현할 수 없었지만, 랩 함수를 그대로 부르면 사전패스도 같이 따라온다.
              "x-hlspread", "x-clv", "x-volvol", "x-fip", "x-residmom", "x-indmom"]

# 펀더멘털 규칙 — 2026-07-30 추가. 편출 종목 재무를 data/fx_pit 로 받고 나서 가능해졌다
# (build/pit_facts.py, 러너에서 SEC 수집). 그 전에는 "시점별 재무가 없어 제외" 였다.
#   ⚠ 재무 커버리지가 가격보다 낮다 — 편출 종목 중 몇 종이 실제로 채점되는지 매 실행에 찍고
#     limits 에 싣는다. 커버리지가 낮으면 그 규칙의 PIT 는 '후보가 생존자로 좁혀진' 쪽이다.
FUND_SIDS = ["x-ep", "x-sp", "x-btp", "x-roe", "x-npm", "x-rgrow", "x-lowde",
             "x-dy", "x-fcfy", "x-sue", "x-epsacc",
             "x-agrow", "x-shiss", "x-cash",      # 2026-07-30 추가
             # 2026-07-31 추가 — 전부 흐름 항목이라 ttm2(q, a) 로 읽어야 한다.
             "x-poacc", "x-gpa", "x-ocfp", "x-aci", "x-payout",
             # 2026-08-04 사전등록. 편출 종목 집중도도 같이 모아 뒀다
             # (build/refresh_custconc.py --pit) — 안 그러면 후보가 생존자로만 좁혀져
             # 생존편향을 재려는 표가 오히려 그 편향을 갖는다(x-volsurge 를 뺀 것과 같은 사유).
             "x-custconc",
             # 2026-08-11 바스켓 크기 3종 — 위 PRICE_SIDS 의 같은 주석 참조.
             "x-btp-n155", "x-payout-n50", "x-agrow-n52",
             # 2026-08-11 — 위 PRICE_SIDS 의 같은 사유. 옮기다 랩 본편의 선견을 찾았다.
             "x-debtiss",
             # 2026-08-11 개편으로 풀린 것들(위 PRICE_SIDS 의 같은 사유).
             "x-valcomp", "x-valcomp-sn", "x-fscore",
             # 🚨 2026-08-12 1차 배치(PREREG-…-INCOME-LINES) 3종. 등록할 때 이 목록에
             #   넣는 것을 빠뜨렸고, 아래 완전성 가드가 그것을 잡았다 — 가드가 없었으면
             #   세 규칙이 소급 t 로만 판정된 채 조용히 지나갔다.
             #   편출 종목 재무 실측: rev 133/145(92%) · rev∩cogs 94/145(65%) 로
             #   랩 유니버스(97%·58%)와 비슷하다 — 제외 사유가 없다.
             "x-sur", "x-sugp", "x-cdisc",
             # 2026-08-12 4차 배치 — PREREG-2026-08-12-POLICY.md §4. 등록과 함께 미리 넣는다.
             #   ⚠ x-divgrow 의 PIT 은 반쪽이다 — 편출 145종 중 dps 가 71종(49%)뿐이라
             #     무배당으로 빠지는 것과 자료가 없어 빠지는 것을 구별할 수 없다.
             #     제외하지는 않는다(레그는 돌아간다). 결과를 참고로만 읽으라고 적었다.
             "x-divgrow", "x-earnvol",
             # 2026-08-12 5차 — PREREG-2026-08-12-BALANCE.md. 커버가 랩 84/97% ·
             #   편출 84/93% 로 거의 같아 두 레그 비교가 성립한다.
             "x-currat", "x-reta"]
# x-volsurge 는 뺐다. 거래량이 랩 파일(오늘의 유니버스)에만 있어 편출 85종의 채점률이 정확히
# 0%다 — 후보가 100% 생존자인 채로 편출종목을 포함한 대조군과 겨루게 되어, 이 파일이 없애려는
# 바로 그 선견이 규칙 하나에만 남는다. 거래량을 편출종목까지 받으면 되살릴 수 있다.
EXCLUDED_SIDS = {
    # 🚨 2026-08-11 — 여기 13종이 더 있었다. 사유는 둘이었고 **둘 다 사라졌다**:
    #   · '횡단면 사전패스 필요' 7종 — 이 파일이 채점기 사본을 갖고 있어서 2단 규칙을
    #     표현하지 못한 것이었다. 사본을 지우고 랩 함수를 부르니 그대로 돈다.
    #   · '편출 종목 섹터 부재' 3종 — data/pit_sector.json 으로 메웠다(72/72).
    #   남는 것은 **자료 원천이 생존자만 주는** 넷뿐이다. 이쪽은 코드로 못 푼다.
    "x-volsurge": "편출 종목 거래량 부재 — 랩 파일(오늘의 유니버스)에만 있어 후보가 100% "
                  "생존자로 좁혀지는데 대조군에는 편출 종목이 들어가 비교가 성립하지 않는다. "
                  "편출 종목 거래량을 받아 오면 풀린다.",
    # 🚨 2026-08-12 — 사전등록 PREREG-2026-08-12-LIQ-CAL.md 의 두 규칙. x-volsurge 와
    #   **정확히 같은 사유**다(거래량이 오늘의 유니버스에만 있다). 등록할 때 이 제약을
    #   못 봤다 — 후보 밀도는 월별로 쟀는데 PIT 가능 여부를 안 쟀다.
    #   x-amihud 는 소급 표본에서 t 6.84 로 문턱을 크게 넘는데, 1순위 이웃 x-small 의
    #   실측 생존편향이 초과수익 +49.67%p(소급 t 6.97 → PIT t 0.52)다. 즉 이 규칙의 t 를
    #   검증할 유일한 수단이 바로 여기서 막혀 있다.
    "x-amihud": "편출 종목 거래량 부재 — 분모가 거래대금이라 x-volsurge 와 같은 벽에 걸린다. "
                "🚨 소급 t 6.84 를 이 레그로 검증할 수 없다. 1순위 이웃 x-small 의 실측 "
                "생존편향이 초과수익 +49.67%p 이므로 소급 수치를 그대로 믿으면 안 된다. "
                "편출 종목 거래량을 받아 오면 풀린다(x-volsurge 와 같이 풀린다).",
    "x-turn": "편출 종목 거래량·주식수 부재 — 분자가 거래량이라 x-volsurge 와 같은 벽이고, "
              "분모의 발행주식수도 편출 종목은 시점별로 없다. 편출 종목 거래량을 받아 오면 "
              "거래량 쪽은 풀리지만 주식수는 별도로 채워야 한다.",
    "x-revdrift": "편출 종목 투자의견 이력 부재 — yfinance 의 upgrades_downgrades 는 지금 "
                  "상장돼 있는 종목만 준다. 나중에 받아 채울 수 있는 종류가 아니다(보완 불가).",
    "x-revdrift-q": "편출 종목 투자의견 이력 부재 — 자료 원천이 생존자만 준다(보완 불가)",
    "x-revdrift-sn": "편출 종목 투자의견 이력 부재 — 자료 원천이 생존자만 준다(보완 불가)",
}
# 고가·저가 캐시를 받아 두면 그 사유가 사라진다. 손으로 지우게 두지 않고 **파일 유무로 정한다** —
# 사람이 지우는 것을 잊으면 규칙이 영영 검정을 안 받고, 그건 오늘 하루 내내 잡은 사고 유형이다.
if os.path.exists(HLCACHE):
    try:
        _hl = json.load(io.open(HLCACHE, encoding="utf-8"))
    except Exception:
        _hl = {}
    if len(_hl) >= 100:            # 편출 종목 대부분이 있어야 후보가 생존자로 좁혀지지 않는다
        EXCLUDED_SIDS.pop("x-52wh", None)


def _lab_meta():
    """랩 유니버스의 종목 메타(섹터·이름).

    🚨 종전에는 `TB.load()[3]` 이었다. load() 가 고가·저가를 함께 돌려주기 시작하면서
      3번이 meta 가 아니게 됐는데, 이런 어긋남은 예외를 안 내고 조용히 지나간다 —
      섹터가 전부 None 이 되고 x-gpa·x-ocfp·x-aci 의 금융 제외가 사라져 PIT 표만
      달라진다. 위치가 아니라 **이름으로** 집는다.
    """
    _dates, _px, _vlm, _hi, _lo, meta, _rf = TB.load()
    return meta


def fetch_members():
    """월말 멤버십 — data/index_history.json(위키 과거 리비전) 하나만 읽는다.

    ⚠ 2026-08-03 에 **사내 DB 경로를 걷어냈다**(사용자 결정). 전에는 public.index_constituents
      를 질의해 data/pit_members.json 에 캐시했고, 그 파일이 라이선스 원천이라 gitignore 였다 —
      러너가 스스로 만들 수 없어, 이 랩이 스스로 최대 약점으로 꼽는 **생존편향 측정이 PC 한
      대에 묶여 있었다.** 위키 산출물은 저장소에 커밋되므로 CI 에서도 돈다.
      대조 실측은 build/refresh_index_history.py 머리말에 있다(실질 일치 60/60 · 티커가 아니라
      CIK 로 조인해야 한다는 것도 그 대조에서 나왔다).
    ⚠ 범위는 위키본이 넓다(2015-01~ vs DB 2020-09~).
      🚨 2026-08-04 — 그 '별도 결정'을 했다(사용자 요청). START 를 2015-01-01 로 앞당긴다.
      이유: 재무 보관 깊이를 18년으로 늘리자 원시 t 가 본페로니를 넘는 규칙이 여럿 생겼고,
      그 전부를 생존편향 보정이 다시 눌렀다(강등 5종 → 13종). 즉 병목이 '표본이 짧다'에서
      '생존편향 측정 창이 짧다'로 옮겨갔다. 그때 PIT 창 5.8년으로 17년짜리 규칙을 판정하는
      것은 짧은 쪽이 결론을 지배한다는 뜻이다. 게시 수치가 바뀐다 — 그게 목적이다.
      🚨 2026-08-11 — "2015-01 이 한계다(위키 리비전 보존 범위)" 라고 적어 뒀는데 **틀렸다.**
        리비전은 훨씬 깊다. 실측으로 SPX 명단은 2007-04, NDX 는 2008-03 부터 파싱된다.
        진짜 한계는 **CIK 컬럼**이고 그것은 2014-06(리비전 2014-05-22)에 생긴다 — 종전
        주석이 "2015-03 부터"라 한 것은 성긴 표본을 안 좁힌 탓이었다. START 를 2014-06 으로
        내린다(+7개월, 140 → 147개월).
        ⚠ 그 아래로는 안 내린다. 명단이 없어서가 아니라 **가격이 없어서**다 — 2009-01 SPX
          498종 중 2015 이후 한 번도 안 나오는 109종에서 30종을 표본으로 받아 보니 19종
          (63%)은 가격이 아예 없고(BNI·EK·WFMI·ERTS·APOL…), 남은 11종은 하나도 빠짐없이
          오늘까지 이어진다(아직 상장 중이거나 티커 재사용: S→SentinelOne · WB→Weibo).
          거기서는 후보가 다시 생존자로만 채워져, 생존편향을 재려는 이 파일이 그 편향을
          도로 갖는다. 더 내려가려면 관측창이 아니라 **원천**을 바꿔야 한다(상폐 포함 DB).
    """
    import index_members                            # noqa: E402  같은 build/ 안
    mem, carried = index_members.load(START)
    print("  멤버십 %d개월 (위키 과거 리비전 · data/index_history.json)" % len(mem))
    for ym, ix, n in carried:
        print("  ⚠ %s %s 결손 — 직전 달 %d종 이월" % (ym, ix.upper(), n))
    return mem


def _next_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return "%04d-%02d" % (y + (m == 12), 1 if m == 12 else m + 1)


def load_reuse():
    """티커가 다른 법인에 넘어갔는지 — data/pit_reuse.json(없으면 빈 판정).

    만드는 곳은 fetch_cache() 다(SEC company_tickers.json 이 필요해 온라인이라야 한다).
    여기서는 읽기만 한다 — 백테스트가 네트워크에 매달리면 CI 에서 조용히 다른 결과가 난다.

    🚨 이 파일은 **START 시점의 편출 명단으로만** 만들어진다. START 를 다시 넓히고
      --fetch-cache 를 안 돌리면, 새로 들어온 티커가 판정 대상에 아예 없어서 조용히
      '재배정 아님' 으로 통과한다 — 3492de0c 가 고친 AA·BBBY·BBT 류 오채점이 소리 없이
      되돌아오는 경로다. 그래서 산출 당시 START 를 파일에 적고, 지금 START 와 다르면 죽는다.
      (조용히 넘어가는 것보다 멈추는 것이 낫다는 이 파일의 다른 관문들과 같은 태도다.)
    """
    if not os.path.exists(REUSE):
        return {}
    try:
        d = json.load(io.open(REUSE, encoding="utf-8")) or {}
    except Exception:
        return {}
    st = d.get("start")
    # 더 넓은 창에서 만든 파일은 **상위집합**이라 안전하다(필요한 것보다 더 많이 판정돼 있다).
    # 위험한 것은 그 반대뿐이므로 그때만 죽는다.
    if st and st > START:
        sys.exit("data/pit_reuse.json 이 START %s 로 만들어졌는데 지금 START 는 %s 로 더 넓다 — "
                 "`python build/pit_backtest.py --fetch-cache` 로 다시 만들 것. "
                 "그대로 쓰면 새로 들어온 편출 티커가 판정을 안 받고 재사용 오염이 되돌아온다."
                 % (st, START))
    return d.get("reassigned") or {}


def cutoff_month(t, MEMBER_SPAN, reassigned):
    """이 티커의 가격을 어느 달까지 쓸 것인가.

    🚨 왜 자르는가. 월말 리밸런스라 마지막 멤버월 M 에 뽑힌 종목은 M+1 까지 들고 있다.
      그 뒤 가격은 PIT 이 **쓸 일이 없는데**, 티커가 다른 회사에 넘어갔으면 그 구간이
      통째로 남의 회사다. 종전 방어(계열 기간이 멤버 기간과 '안 겹치면' 제외)는 이걸
      못 잡는다 — 실측 3종이 그렇게 통과하고 있었다:
          AA   위키 0000004281(구 Alcoa) → SEC 현행 0001675149(Alcoa Corp) · 멤버 ~2016-10
          BBBY 위키 0000886158           → SEC 현행 0001130713            · 멤버 ~2017-06
          BBT  위키 0000092230(BB&T)     → SEC 현행 0001108134            · 멤버 ~2019-11
      셋 다 계열이 2005~2026 로 이어져 멤버 기간과 겹치므로 겹침 판정을 그냥 통과한다.
      (BBT 가 후속 법인 스플라이스도 아니라는 것은 실측했다 — 2026-08-10 종가가 BBT 31.54,
       TFC 51.86 으로 다르다. 즉 승계가 아니라 재배정이다.)
    ⚠ 재배정이 확인된 티커는 **M+1 도 주지 않는다.** 그 한 달이 이미 남의 회사이기 때문이다
      (AA 는 2016-11-01 에 신 Alcoa 로 넘어갔고 멤버 마지막 달이 2016-10 이다).
      실제로는 존속법인(ARNC)으로 전환돼 이어졌겠지만 그 경로를 이 자료로는 못 따라간다 —
      마지막 멤버월 종가로 청산한 것으로 둔다. 근사이고, 근사라고 적는다.
    """
    lo, hi = MEMBER_SPAN.get(t, (None, None))
    if not hi:
        return None
    return hi if t in reassigned else _next_month(hi)


def load_prices(need, MEMBER_SPAN):
    """티커→{날짜:종가}. 오늘의 유니버스는 랩 파일, 편출 종목은 캐시에서."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    pdates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        t = s["t"]
        if t not in need:
            continue
        p = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(p):
            continue
        a = json.load(io.open(p, encoding="utf-8")).get("pxd") or []
        if len(a) == len(pdates):
            px[t] = {d: v for d, v in zip(pdates, a) if v is not None}
    n_lab = len(px)
    if not os.path.exists(CACHE):
        # ⚠ 조용히 넘어가면 안 된다. 캐시가 없으면 후보가 '오늘 살아남은 종목'만 남아
        #   생존자 전용 백테스트가 되는데, 파일 이름과 문구는 그대로 'PIT' 라 더 나쁘다.
        sys.exit("편출 종목 가격 캐시가 없다(%s) — `python build/pit_backtest.py --fetch-cache` 로 "
                 "먼저 받을 것. 없이 돌리면 생존자 전용 결과에 PIT 라벨이 붙는다." % CACHE)
    cache = json.load(io.open(CACHE, encoding="utf-8"))
    reassigned = load_reuse()
    bad_reuse, cut = [], []
    for t, ser in cache.items():
        if t not in need or t in px or not ser:
            continue
        # ① 겹침 판정 — 계열이 '그 티커가 멤버였던 기간'과 아예 안 겹치면 다른 회사다.
        # 실측 사례: FB 캐시는 ProShares ETF(2025-06~), 멤버십의 FB 는 2020~2022 의 메타.
        ks = sorted(ser)
        lo, hi = MEMBER_SPAN.get(t, ("9999-99", "0000-00"))
        if ks[-1][:7] < lo or ks[0][:7] > hi:
            bad_reuse.append(t); continue
        # ② 꼬리 절단 — 위 cutoff_month() 주석 참조. ①만으로는 AA·BBBY·BBT 를 못 잡는다.
        cm = cutoff_month(t, MEMBER_SPAN, reassigned)
        if cm and ks[-1][:7] > cm:
            n0 = len(ser)
            ser = {d: v for d, v in ser.items() if d[:7] <= cm}
            cut.append((t, n0 - len(ser), cm, t in reassigned))
            if not ser:
                continue
        px[t] = ser
    if bad_reuse:
        print("  ⚠ 티커 재사용 의심 %d종 제외(계열 기간이 멤버 기간과 안 겹침): %s"
              % (len(bad_reuse), ", ".join(sorted(bad_reuse))))
    if cut:
        _re = [c for c in cut if c[3]]
        print("  ✂ 편출 계열 꼬리 절단 %d종(멤버 종료 뒤 구간 %d거래일) · 그중 SEC 대조로 "
              "재배정 확인 %d종: %s"
              % (len(cut), sum(c[1] for c in cut), len(_re),
                 ", ".join("%s→%s" % (c[0], c[2]) for c in sorted(_re)) or "없음"))
    print("  가격 %d종 (랩 %d + 편출캐시 %d)" % (len(px), n_lab, len(px) - n_lab))
    return px, {"n_cut": len(cut), "n_reassigned": sum(1 for c in cut if c[3]),
                "reassigned": sorted(c[0] for c in cut if c[3]),
                "n_dropped": len(bad_reuse), "dropped": sorted(bad_reuse)}


def load_hilo(need, dates, MEMBER_SPAN=None, which=0):
    """티커 → 고가(which=0) 또는 저가(which=1) 배열(dates 와 같은 길이).

    🚨 2026-08-11 — 종전 이름은 load_highs 였고 고가만 냈다. 저가를 안 내니
      x-lshock·x-ongapd(코윈-슐츠 스프레드·야간 갭)의 PIT 갈래를 애초에 못 만들었고,
      그 셋은 '자료가 없어서' 가 아니라 **여기서 안 실어서** PIT 을 못 돌고 있었다.
      HL 캐시는 [고가, 저가] 를 둘 다 갖고 있었다 — 배선이 없었을 뿐이다.
    """
    # 랩 종목은 data/sd, 편출 종목은 HL 캐시.
    # 🚨 두 출처를 섞는 것이 이 함수의 전부이고, 섞이지 **않으면** 후보가 생존자로만 좁혀진다 —
    #   그러면 생존편향을 재려는 표가 오히려 그 편향을 갖는다(x-volsurge 를 뺀 것과 같은 사유).
    #   그래서 편출 종목 커버리지를 함께 돌려주고, 낮으면 부르는 쪽이 규칙을 뺀다.
    hi = {}
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    pd_ = st["pxd_dates"]
    pos = {d: i for i, d in enumerate(dates)}
    for s_ in st["stocks"]:
        t = s_["t"]
        if t not in need:
            continue
        fp = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(fp):
            continue
        a = json.load(io.open(fp, encoding="utf-8")).get("hd" if which == 0 else "ld") or []
        if len(a) != len(pd_):
            continue
        arr = [None] * len(dates)
        for k, d in enumerate(pd_):
            j = pos.get(d)
            if j is not None:
                arr[j] = a[k]
        hi[t] = arr
    n_lab = len(hi)
    if os.path.exists(HLCACHE):
        try:
            hl = json.load(io.open(HLCACHE, encoding="utf-8"))
        except Exception:
            hl = {}
        # 종가와 **같은 자리에서** 자른다. 한쪽만 자르면 같은 종목이 규칙마다 다른 이력을
        # 갖게 되고, 그 어긋남은 예외를 안 내고 지나간다(이 파일이 세 번 겪은 유형이다).
        reassigned = load_reuse()
        for t, ser in hl.items():
            if t not in need or t in hi or not ser:
                continue
            cm = cutoff_month(t, MEMBER_SPAN or {}, reassigned)
            arr = [None] * len(dates)
            for d, v in ser.items():
                if cm and d[:7] > cm:
                    continue
                j = pos.get(d)
                if j is not None and isinstance(v, list) and len(v) > which:
                    arr[j] = v[which]
            hi[t] = arr
    return hi, n_lab, len(hi) - n_lab


def dump_universe(mem, span, px_map):
    """편출 종목 명단을 data/pit_universe.json 으로 — **러너가 읽는 유일한 경로**.

    build/pit_facts.py 가 이 명단으로 SEC 재무를 받아 data/fx_pit 에 넣고, 그것이 있어야
    펀더멘털 규칙(저PER·고ROE 등)을 PIT 로 잴 수 있다. 멤버십 원천(pit_members.json)은
    사내 DB 라이선스라 gitignore — 러너가 스스로 계산할 수 없으므로 이 파일을 커밋한다.

    ⚠ 티커별 멤버 기간(first/last)을 같이 싣는다. 재사용 티커를 걸러내려면 러너가
      'SEC 가 준 법인의 최초 보고기간이 이 티커의 마지막 멤버월보다 늦은가' 를 볼 수 있어야
      한다(FB → ProShares ETF 선례). 명단만 주면 그 판정을 못 한다.
    ⚠ 가격이 없는 편출 종목은 애초에 보유할 수 없으니 재무를 받을 이유도 없다 — 뺀다.
    """
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    today = {s["t"] for s in st["stocks"]}
    union = set()
    for v in mem.values():
        union |= set(v)
    gone = sorted(t for t in (union - today) if px_map.get(t))
    doc = {
        "note": ("PIT 창에서 지수에 있었다가 오늘 유니버스에 없는 종목. build/pit_facts.py 가 "
                 "이 명단으로 SEC 재무를 받는다(data/fx_pit). 가격이 없는 종목은 보유 자체가 "
                 "불가하므로 제외했다. first/last 는 멤버였던 월이고 티커 재사용 판정에 쓴다."),
        "start": START, "n_today": len(today), "n_union": len(union), "n_gone": len(gone),
        "tickers": {t: {"first": span[t][0], "last": span[t][1]} for t in gone},
    }
    p = os.path.join(DATA, "pit_universe.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("→ %s · 편출 %d종(가격 있는 것만)" % (p, len(gone)))


def main():
    print("PIT 백테스트 — 매월말 실제 편입 종목만 후보 (SPX ∪ NDX, %s~)" % START)
    mem = fetch_members()
    need = set()
    for v in mem.values():
        need |= set(v)
    # 티커별 '멤버였던 기간' — 재사용 티커를 걸러내는 데 쓴다
    span = {}
    for ym, lst in mem.items():
        for t in lst:
            a, b = span.get(t, (ym, ym))
            span[t] = (min(a, ym), max(b, ym))
    px_map, reuse_rep = load_prices(need, span)
    dump_universe(mem, span, px_map)
    if "--universe-only" in sys.argv:
        return 0

    # 거래일 격자 — 랩과 같은 격자를 쓴다(랩이 이미 yfinance 거래일로 만들어 둔 것).
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = [d for d in st["pxd_dates"]]
    n = len(dates)
    tickers = sorted(px_map)
    px = {t: [px_map[t].get(d) for d in dates] for t in tickers}
    vlm = {}
    for t in tickers:                              # 거래량은 랩 파일에만 있다(편출분은 없음)
        p = os.path.join(DATA, "sd", t + ".json")
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("vd")
            vlm[t] = v if isinstance(v, list) and len(v) == n else None
        else:
            vlm[t] = None

    # ── 시점별 주식수(x-small 용) ──────────────────────────────────────
    # 오늘의 유니버스는 랩이 SEC XBRL 로 이미 갖고 있고(data/fx), 편출 종목만 yfinance 캐시에서.
    # ⚠ 두 출처는 정의가 미세하게 다르다(실측: yfinance 가 0.3~2.3% 낮다). 시총이 자릿수로
    #   벌어지는 횡단면이라 순위 영향은 거의 없지만, 민감도를 재서 limits 에 싣는다.
    SH = {}
    # 재무는 오늘의 유니버스(data/fx)와 편출 종목(data/fx_pit)을 함께 훑는다 — 후자가 있어야
    # 펀더멘털 규칙을 PIT 로 잴 수 있다. 없으면 그 규칙들은 후보가 생존자로만 좁혀진다.
    _FXP = os.path.join(DATA, "fx_pit")
    _fu = TB.load_fund(extra_dirs=[_FXP] if os.path.isdir(_FXP) else [])
    for t in tickers:
        a = (_fu.get(t) or {}).get("sh")
        if a:
            SH[t] = a
    _nsec = len(SH)
    if os.path.exists(SHCACHE):
        # 🚨 단위를 맞춘다. 랩의 SEC 계열(data/fx)은 **백만주**로 저장돼 있고(AOS 139.17),
        #    yfinance get_shares_full 은 **원주**를 준다(94,896,231). 그대로 섞으면 편출 종목
        #    시총이 10^6 배로 부풀어 '가장 작은 10'에 영영 못 들어간다 — 실제로 그렇게 나왔고
        #    (700자리 중 편출 0건) 하마터면 '소형주는 PIT 를 통과했다'는 거짓 결론이 될 뻔했다.
        for t, a in json.load(io.open(SHCACHE, encoding="utf-8")).items():
            if t in tickers and t not in SH:
                SH[t] = [[d, v / 1e6] for d, v in a]
    print("  주식수 %d종 (SEC %d + yfinance %d)" % (len(SH), _nsec, len(SH) - _nsec))
    C_SH = SH

    R = TB.daily_rets(px)
    me = set(TB.month_ends(dates))
    # ⚠ i0 를 START 직후 아무 날로 잡으면 안 된다. 전략은 첫 월말 리밸까지 보유가 없어 수익 0인데
    #   대조군은 그날부터 만기 투자다 — 그 20거래일에 대조군이 −2.77% 빠지면서 16종 전부가
    #   공짜 초과수익을 얻는다(대조군 CAGR 도 0.76%p 낮게 잡힌다). 첫 월말에서 같이 출발시킨다.
    _s0 = next(i for i in range(n) if dates[i] >= START)
    i0 = min(i for i in me if i >= _s0)

    def members_at(i):
        return set(mem.get(dates[i][:7]) or [])

    # 대조군도 PIT 여야 한다 — 전략만 PIT 이고 벤치가 소급이면 초과수익이 엉뚱해진다.
    ixr = [None] * n
    cur = members_at(i0) & set(tickers)
    for i in range(1, n):
        if (i - 1) in me:
            m = members_at(i - 1) & set(tickers)
            if m:
                cur = m
        rs = [R[t][i] for t in cur if R[t][i] is not None]
        ixr[i] = sum(rs) / len(rs) if rs else 0.0
    ixvol = [TB.vol(ixr, i, 20) for i in range(n)]

    rf = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8")).get("monthly") or {}
    rf = {k: v for k, v in rf.items() if k >= dates[i0][:7]}

    TB.build_strats()
    BY = {s["sid"]: s for s in TB.STRATS}
    # 🚨 완결성 관문 — 랩의 **모든 횡단면 규칙**은 셋 중 하나여야 한다:
    #     ① PRICE_SIDS 나 FUND_SIDS 에 있어 PIT 을 돈다
    #     ② EXCLUDED_SIDS 에 **사유와 함께** 있다
    #     ③ 여기서 죽는다
    #   2026-08-11 이전에는 넷째 길이 있었다 — 아무 데도 없어서 조용히 안 도는 것.
    #   그렇게 13종이 생존편향 검사를 한 번도 안 받은 채 소급 t 로만 판정되고 있었다
    #   (그중 x-hlspread 는 소급 t 5.00 이었다). 목록에 없다는 것은 아무 신호도 안 낸다 —
    #   그래서 사람이 알아챌 방법이 없었고, 그것이 이 관문이 막는 것이다.
    _listed = set(PRICE_SIDS) | set(FUND_SIDS) | set(EXCLUDED_SIDS)
    _orphan = sorted(s["sid"] for s in TB.STRATS
                     if s.get("kind") == "xsec" and TB._BASE_SID(s["sid"]) not in _listed
                     and s["sid"] not in _listed)
    if _orphan:
        sys.exit(
            "PIT 목록에 없는 횡단면 규칙 %d종: %s\n"
            "  랩에 등록된 횡단면 규칙은 PIT 을 돌거나, EXCLUDED_SIDS 에 **사유를 적어** "
            "빠지거나 둘 중 하나여야 한다. 목록에 없으면 생존편향 검사를 안 받은 채 소급 t 로만 "
            "판정되는데, 그 사실이 아무 데도 안 남는다.\n"
            "  → build/pit_backtest.py 의 PRICE_SIDS/FUND_SIDS 에 넣고 score() 갈래를 만들거나, "
            "EXCLUDED_SIDS 에 사유와 함께 적을 것." % (len(_orphan), ", ".join(_orphan)))
    # 🚨 랩 본편의 xsec_score_at() 이 받는 것과 **같은 모양**이어야 한다(키 하나라도 빠지면
    #   KeyError 로 죽는다 — 조용히 다른 값이 나오는 것보다 낫다).
    _meta = {t: dict(m or {}) for t, m in (_lab_meta() or {}).items()}
    # 편출 종목 섹터 — 랩 메타는 오늘의 518종만 갖는다. 이것을 안 메우면 섹터로 묶거나
    # 금융업을 빼는 규칙에서 편출 종목이 통째로 빠져 후보가 생존자로 좁혀진다.
    _ps = os.path.join(DATA, "pit_sector.json")
    _nsec2 = 0
    if os.path.exists(_ps):
        for t, sg in ((json.load(io.open(_ps, encoding="utf-8")) or {}).get("sector") or {}).items():
            if t not in _meta and sg:
                _meta[t] = {"sector": sg}
                _nsec2 += 1
    print("  섹터 %d종 (랩 %d + 편출 %d)" % (len(_meta), len(_meta) - _nsec2, _nsec2))
    X = {"FACP": TB.load_factor_proxies(dates), "FU": _fu, "R": R, "dates": dates,
         "hid": {}, "lod": {}, "ixr": ixr, "ixvol": ixvol, "me": me,
         "me_list": sorted(me), "meta": _meta, "px": px, "vlm": vlm,
         "tickers": tickers}
    # 고가·저가 — x-52wh(고가) · x-lshock·x-ongapd(둘 다) 가 쓴다. 편출 종목분은 HLCACHE 에서
    # 온다. 🚨 종전에는 조건이 `x-52wh 가 제외 목록에 없으면` 이었다. HL 캐시가 있어도
    #   x-52wh 하나의 사정으로 저가·고가 전체가 안 실릴 수 있는 배선이었고, 그 탓에 고저가를
    #   쓰는 다른 규칙은 아예 후보에 오르지도 못했다. 파일이 있으면 싣는다 — 쓰는 쪽이 정한다.
    if os.path.exists(HLCACHE):
        X["hid"], _nl, _nx = load_hilo(set(px), dates, span, 0)
        X["lod"], _nl2, _nx2 = load_hilo(set(px), dates, span, 1)
        print("  고가 %d종 (랩 %d + 편출캐시 %d) · 저가 %d종 (랩 %d + 편출캐시 %d)"
              % (len(X["hid"]), _nl, _nx, len(X["lod"]), _nl2, _nx2))

    # 편출 종목의 재무 커버리지 — 펀더멘털 규칙의 PIT 가 얼마나 성립하는지의 눈금.
    # 낮으면 그 규칙은 '후보가 생존자로 좁혀진' 쪽이므로 숫자와 함께 적어 둔다.
    _st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    _today = {s["t"] for s in _st["stocks"]}
    _gone = [t for t in tickers if t not in _today]
    # 🚨 _gone 은 '가격이 있는' 편출뿐이다(tickers = px_map 의 키). 결손 규모를 말하려면
    #   가격이 없어서 애초에 후보가 못 된 것까지 세야 한다 — 그게 _gone_all 이다.
    #   종전에는 이 수를 문장에 "334종 중 180종" 으로 박아 뒀고, 창을 바꾸자 거짓이 됐다.
    _gone_all = sorted(need - _today)
    _fx_gone = [t for t in _gone if (_fu.get(t) or {}).get("eq") or (_fu.get(t) or {}).get("eps")]
    fx_cov = (len(_fx_gone) / len(_gone)) if _gone else 0.0
    print("  편출 %d종 중 재무 있는 것 %d종(%.0f%%) — 펀더멘털 규칙의 PIT 커버리지"
          % (len(_gone), len(_fx_gone), 100 * fx_cov))

    # 커버리지 — 매월말 '멤버인데 가격이 없는' 비율. 남은 편향의 크기를 정직하게 싣는다.
    cov = []
    for i in sorted(me):
        if i < i0:
            continue
        m = members_at(i)
        if m:
            cov.append(len(m & set(tickers)) / len(m))
    cov_min, cov_med = (min(cov), sorted(cov)[len(cov) // 2]) if cov else (0, 0)
    print("  멤버 대비 가격 보유율: 최저 %.1f%% · 중앙 %.1f%%" % (100 * cov_min, 100 * cov_med))

    # 창 첫달의 **채점 가능성** — 보유율(그날 가격이 있나)과 다른 것이다. 12개월 룩백을
    # 요구하는 규칙이 이 달에 몇 종을 실제로 채점할 수 있나. 캐시가 창 시작에 잘려 있으면
    # 여기가 무너지고, 그러면 창 앞머리의 후보가 조용히 생존자로 좁혀진다.
    # 🚨 숫자를 문장에 박지 않고 여기서 만든다 — 창을 바꿀 때마다 문장이 거짓이 되지 않게.
    # ⚠ 분모는 **그달 멤버 전부**다. 가격이 있는 종목만으로 나누면 보유율과 비교가 안 되고
    #   (가격 없는 종목이 통째로 빠져) 값이 늘 좋아 보인다 — 실측 99.8% 대 90.1%.
    _p0 = max(0, i0 - 252)
    _m0all = members_at(i0)
    _mset = set(tickers)
    cov0_look = ((sum(1 for t in _m0all
                      if t in _mset and px[t][i0] is not None and px[t][_p0] is not None)
                  / len(_m0all)) if _m0all else 0.0)
    print("  창 첫달(%s) 12개월 룩백까지 채점 가능: %.1f%%" % (dates[i0], 100 * cov0_look))

    # ── 같은 창의 소급 레그 ────────────────────────────────────────────────
    # 🚨 편향은 **같은 창**에서 재야 한다. 랩 본편은 더 긴 창이라 두 수치를
    #   빼면 편향이 아니라 '편향 + 구간 차이' 가 나온다(스타일 측정에서 같은 함정을 겪었다).
    #   그래서 이 창에서 소급 유니버스(오늘 518종)로 한 번 더 돌린다.
    #   · 채점은 종목별로 독립이라(z 표준화가 없다) 후보집합이 점수를 바꾸지 않는다 —
    #     스타일 쪽에서 필요했던 '채점 모집단 좁히기' 가 여기서는 불필요하다.
    #   · 다만 대조군과 ixr(동일가중 지수)은 유니버스에 딸린 값이라 레그별로 따로 만든다.
    #     x-ivol·x-lowbeta·x-minvar 가 ixr 을 쓰므로 이것을 공유하면 반쪽만 소급이 된다.
    lab_uni = sorted(set(tickers) & _today)
    ixr_lab = [None] * n
    for i in range(1, n):
        rs = [R[t][i] for t in lab_uni if R[t][i] is not None]
        ixr_lab[i] = sum(rs) / len(rs) if rs else 0.0
    ixvol_lab = [TB.vol(ixr_lab, i, 20) for i in range(n)]

    def run(S, pool_at, IXR, IXVOL):
        """한 전략을 한 유니버스로 돌린다. pool_at 이 None 이면 제한 없음(소급)."""
        # 🚨 2026-08-11 — 이 파일이 갖고 있던 **두 번째 채점기**(score())를 지웠다.
        #   랩 본편의 xsec_score_at()/xsec_pick_at() 을 그대로 부른다. 두 레그의 차이가
        #   '생존편향' 이려면 채점도 선택도 같은 코드여야 한다. 사본이 있는 한 어긋난다 —
        #   하루에 넷을 그렇게 잡았다(x-52wh · ttm2 · 편향 문장 · x-debtiss 선견).
        #   그리고 사본으로 옮기기 어려운 2단 규칙 7종이 아예 PIT 을 못 돌고 있었다.
        XX = dict(X, ixr=IXR, ixvol=IXVOL)
        hold, hw, nav, srets, turns = [], None, [100.0], [], 0
        first = None                       # 실제로 무언가를 보유하기 시작한 시점
        for i in range(i0 + 1, n):
            if (i - 1) in me:
                # 소급 레그도 **명단으로** 준다 — 종전에는 pool=None 으로 두고 채점 루프
                # 안에서 오늘 유니버스를 걸렀는데, 그러면 사전패스(모멘텀 5분위·변동성
                # 회귀·섹터 정렬)는 전 종목을 보게 되어 두 레그가 다른 모집단을 쓴다.
                pool = pool_at(i - 1) if pool_at else _today
                sc, ind_raw, _cr = TB.xsec_score_at(S, i, XX, pool)
                if len(sc) < TB.XSEC_MIN_POOL:                  # 소급 레그와 같은 커버리지 게이트
                    hold, hw = [], None
                else:
                    new, new_w = TB.xsec_pick_at(S, i, XX, sc, ind_raw)
                    if new:
                        # 분모도 바스켓 크기로 일반화한다(랩 본편 2026-08-08 과 같은 식).
                        turns += (len(set(new) ^ set(hold)) / (len(new) + len(hold))) if hold else 1.0
                        hold, hw = new, new_w
            if hold and first is None:
                first = i
            if hw:
                # 가중 바스켓(섹터 중립·산업 모멘텀). 랩 본편과 같은 되정규화 —
                # 결측 종목을 0 으로 두면 그날 현금을 든 것이 되어 중립이 조용히 깨진다.
                _pairs = [(hw[t], R[t][i]) for t in hold if R[t][i] is not None and t in hw]
                _sw = sum(w for w, _x in _pairs)
                srets.append((sum(w * x for w, x in _pairs) / _sw) if _sw > 0 else 0.0)
            else:
                rs = [R[t][i] for t in hold if R[t][i] is not None]
                srets.append(sum(rs) / len(rs) if rs else 0.0)
            nav.append(nav[-1] * (1 + srets[-1]))
        bnav = [100.0]
        for i in range(i0 + 1, n):
            bnav.append(bnav[-1] * (1 + (IXR[i] or 0.0)))
        # 재기준은 여기서 하지 않는다 — 두 레그의 보유시작이 갈릴 수 있고, 각자 자기 시점에
        # 맞추면 창이 달라져 이 파일이 없애려는 '구간 차이가 편향으로 위장' 이 되살아난다.
        # 원재료만 돌려주고 fin() 이 **공통 k** 로 마감한다.
        return {"nav": nav, "bnav": bnav, "srets": srets, "turns": turns,
                "first": first, "hold": sorted(hold), "IXR": IXR}

    def fin(raw, k):
        """🚨 보유시작 재기준 — 소급 레그(tech_backtest)에는 있는데 여기엔 없었다.

        적대감사 실측(**2015-01 창 시절** · 지금 값이 아니다): x-season 은 same_month_avg 가
        월말 61개를 요구해 PIT 창 시작보다 231거래일 늦게 첫 보유가 생겼다. 그 231일간 전략
        NAV 는 100 에 고정인데 대조군은 복리로 올라 PIT 초과수익이 음(−) 쪽으로 5.27%p 과대,
        |t| 가 1.8배 과대, 화면에 적히는 생존편향 크기는 4.5%p 과소로 나왔다. 이 파일이 스스로
        주석에 적어 둔 i0 이음매 함정과 같은 것으로, i0 조정이 20일은 막았지만 231일은 못 막았다.

        ⚠ 지금 창(2021-07~)에서는 40종 전부 지연 0일이라 이 분기가 아무것도 하지 않는다.
          그렇다고 **지우지 않는다** — 창을 넓히거나 룩백이 긴 규칙을 더하면 곧바로 되살아나는
          방어이고, 없앴다가 다시 겪은 사고다. 창 길이가 전략마다 갈릴 수 있으므로 start·n_days
          는 전역 라벨이 아니라 전략별로 돌려준다."""
        nav, bnav = raw["nav"], raw["bnav"]
        srets, d2 = raw["srets"], dates[i0:]
        if k:
            nav = [x / nav[k] * 100 for x in nav[k:]]
            bnav = [x / bnav[k] * 100 for x in bnav[k:]]
            srets, d2 = srets[k:], d2[k:]
        stt, bs = TB.ann_stats(nav, d2, rf), TB.ann_stats(bnav, d2, rf)
        return {
            "metrics": stt, "bench": bs,
            "excess_cagr": round(stt.get("cagr", 0) - bs.get("cagr", 0), 2),
            "d_sharpe": round((stt.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
            "t": TB.tstat(srets, raw["IXR"][i0 + 1 + k:]),
            "turnover": round(raw["turns"] / max(1, (n - i0 - k) / 252), 2),
            "start": d2[0], "n_days": len(d2),
            "hold": raw["hold"],
        }

    out = []
    # 🚨 EXCLUDED_SIDS 를 **여기서 실제로 읽는다.** 종전에는 정의만 있고 저장소 어디에서도
    #   참조되지 않는 죽은 변수였다(적대감사 실측: 참조 1건 = 정의 그 자체). 사유까지 적어 둔
    #   딕셔너리인데 아무 코드도 안 봐서, 목록에 도로 넣어도 막는 것이 없었다.
    _PRICE_SET = set(PRICE_SIDS)
    _retired = []
    for sid in [s for s in PRICE_SIDS + FUND_SIDS if s not in EXCLUDED_SIDS]:
        S = BY.get(sid)
        if not S:
            # 🚨 조용히 넘어가지 않는다. 랩 본편에서 은퇴한 규칙은 BY 에 없어 여기서 빠지는데,
            #   그동안 limits 는 PRICE_SIDS+FUND_SIDS 를 세어 '48종' 이라 적고 있었다.
            #   목록에 이름이 남아 있는 한 아무도 안 돈 줄 모른다.
            _retired.append(sid)
            continue
        _p = run(S, members_at, ixr, ixvol)          # PIT
        _b = run(S, None, ixr_lab, ixvol_lab)        # 같은 창·소급 유니버스
        # 두 레그를 **늦은 쪽** 보유시작에 함께 맞춘다. 각자 맞추면 창이 갈려 편향에 구간 차이가
        # 섞인다(x-season 은 두 레그가 같지만 커버리지 게이트 탓에 갈릴 수 있다).
        _k = max(max(0, (_p["first"] or (i0 + 1)) - 1 - i0),
                 max(0, (_b["first"] or (i0 + 1)) - 1 - i0))
        P_, B_ = fin(_p, _k), fin(_b, _k)
        out.append({
            "sid": sid, "name": S["name"],
            "metrics": P_["metrics"], "bench": P_["bench"],
            "excess_cagr": P_["excess_cagr"], "d_sharpe": P_["d_sharpe"],
            "t": P_["t"], "turnover": P_["turnover"],
            # 전략별 실효 창 — 전역 라벨과 다를 수 있다(보유시작 재기준·커버리지 게이트)
            "start": P_["start"], "n_days": P_["n_days"],
            # 같은 창의 소급 레그와 그 차이 = 유니버스 편향(구간 차이가 섞이지 않는다)
            "retro": {"metrics": B_["metrics"], "bench": B_["bench"],
                      "excess_cagr": B_["excess_cagr"], "t": B_["t"]},
            # 🚨 두 지표를 같이 낸다(적대감사가 잡은 결함).
            #   bias_cagr   = 전략 자체가 얼마나 부풀었나. **이것이 편향의 본체다.**
            #   bias_excess = 초과수익 기준. 두 레그의 대조군이 각자의 동일가중 지수라
            #     벤치에 실린 편향(bench_bias_cagr)이 **상쇄된다** — 그래서 이 값은 항상
            #     bias_cagr 에서 그만큼 깎이고 하한이 그 음수다. 즉 '편향 0' 과 'PIT 가 유리' 를
            #     구별하지 못한다. 실제로 그 탓에 "고배당은 PIT 로 오히려 좋아진다"고
            #     잘못 읽었다 — 전략 CAGR 은 33.42 → 32.68 로 **나빠졌는데** 벤치가 더
            #     내려가 −4.51 로 찍혔다. 화면은 bias_cagr 를 먼저 적어야 한다.
            "bias_cagr": round((B_["metrics"].get("cagr") or 0)
                               - (P_["metrics"].get("cagr") or 0), 2),
            "bench_bias_cagr": round((B_["bench"].get("cagr") or 0)
                                     - (P_["bench"].get("cagr") or 0), 2),
            "bias_excess": round(B_["excess_cagr"] - P_["excess_cagr"], 2),
            "bias_sharpe": round((B_["metrics"].get("sharpe") or 0)
                                 - (P_["metrics"].get("sharpe") or 0), 3),
            "holdings": {"kind": "xsec", "as_of": dates[-1],
                         "n": len(P_["hold"]), "tickers": P_["hold"]},
        })
        print("  %-24s CAGR 소급 %+7.2f → PIT %+7.2f (편향 %+6.2f) · 초과 %+7.2f → %+7.2f "
              "(t %5.2f → %5.2f)"
              % (S["name"][:24], B_["metrics"].get("cagr") or 0,
                 P_["metrics"].get("cagr") or 0, out[-1]["bias_cagr"],
                 B_["excess_cagr"], P_["excess_cagr"], B_["t"] or 0, P_["t"] or 0))

    # 다중검정 문턱 — 이 표(재측정한 규칙 수)와 랩 족(탐색한 가설 수) 둘 다 도출한다.
    # 랩 족은 TB.STRATS 레지스트리 길이로, tech_backtest 의 N = len(out) 과 같은 수다.
    _NP = len(out)
    _NLAB = len(TB.STRATS)
    _TC, _TCLAB = TB.z_crit(_NP), TB.z_crit(_NLAB)
    _TMAX = round(max((abs(r.get("t") or 0) for r in out), default=0), 2)

    doc = {
        "t_crit": _TC, "t_crit_lab": _TCLAB, "n_family_lab": _NLAB, "t_max": _TMAX,
        "note": "매월말 실제 지수 편입 종목만 후보로 두고 다시 돌린 결과. 같은 창에서 소급 "
                "유니버스(오늘 518종)로도 한 번 더 돌려 retro 에 담았고, 그 차이(bias_excess)가 "
                "유니버스 편향의 크기다 — 랩 본편(더 긴 창)과 직접 빼면 구간 차이가 섞여 편향이 "
                "아니게 된다. 채점은 종목별로 독립이라(z 표준화 없음) 후보집합이 점수를 바꾸지 "
                "않으므로, 스타일 측정에서 필요했던 '채점 모집단 좁히기' 가 여기서는 불필요하다.",
        "start": dates[i0], "as_of": dates[-1], "n_days": n - i0,
        "span_years": round((n - i0) / 252.0, 1),
        "universe": "SPX ∪ NDX · 매월말 실제 편입(위키백과 과거 리비전 · data/index_history.json) · 가격은 yfinance",
        "coverage": {"min": round(cov_min, 4), "median": round(cov_med, 4)},
        # 티커 재사용 방어가 실제로 무엇을 했는지 — 숫자로 남긴다. 방어를 넣고 아무것도
        # 안 걸리는 것과 16종을 잘라 낸 것은 다른 이야기이고, 화면이 그것을 인용할 수 있어야 한다.
        "reuse_guard": reuse_rep,
        # 🚨 PIT 을 **안 도는** 규칙과 그 사유. 화면이 빈칸 대신 사유를 말할 수 있어야 한다 —
        #   빈칸은 '해당 없음' 과 '아직 안 쟀다' 와 '못 잰다' 를 구별하지 못하고, 그 셋을
        #   구별 못 한 탓에 13종이 검사를 안 받은 채 소급 t 로만 판정되고 있었다(2026-08-11).
        "excluded": dict(EXCLUDED_SIDS),
        "na_timing": ("타이밍·오버레이 규칙은 지수·ETF 를 매매하므로 '그때 지수에 있던 종목' "
                      "이라는 개념 자체가 없다. 생존편향이 걸리는 자리가 아니라서 안 재는 것이고, "
                      "못 재는 것이 아니다."),
        "limits": [
            "구간이 %s부터다. 🚨 이건 **자료의 한계가 아니라 품질 문턱**이다 — 세 커버리지"
            "(보유율·252일 룩백 채점가능·재무)가 모두 90%% 이상이고 그 뒤로 다시 안 내려가는 "
            "첫 달로 정했고, 문턱은 결과를 보기 전에 확정했다. 커버리지에 무릎이 없어"
            "(2014-06 의 72%% → 2026 의 100%% 로 매끄럽게 오른다) 어디서 자르든 자유도가 "
            "되기 때문이다. ⚠ 대가: 관측이 3046 → 1262거래일(−59%%)이고 이 창의 월평균 편출 "
            "멤버가 58.6종(전 구간 120.3종)이라 PIT 이 잴 대상 자체가 절반이다. "
            "창을 깨끗하게 만드는 값이 곧 편향을 재기 어렵게 만드는 값이다." % START,
            "자료의 한계는 따로 있고 그건 **2014-06** 이다 — 위키 표에 CIK 컬럼이 생긴 첫 달"
            "(리비전 2014-05-22)이고, 그 아래는 티커로만 조인하게 되어 개명(BBWI←LB 등)과 "
            "티커 재사용을 구별할 수 없다. 명단 자체는 더 깊다(실측: SPX 2007-04 · NDX 2008-03). "
            "가격은 더 일찍 끊긴다 — 2009-01 SPX 498종 중 2015 이후 한 번도 안 나오는 109종에서 "
            "30종을 받아 보니 19종(63%)은 가격이 아예 없고 남은 11종은 전부 오늘까지 이어진다"
            "(아직 상장 중이거나 재사용). data/index_history.json 은 2014-06 부터 그대로 모은다 "
            "— 원자료는 안 좁혔다. ⚠ 다만 START 는 채점 창만 정하는 것이 아니다: 러너가 받는 "
            "편출 명단(data/pit_universe.json)과 그것을 따르는 가격 캐시 수집·재사용 판정도 "
            "START 를 따라 좁아진다. 되돌리려면 START 를 되돌리고 --fetch-cache 를 다시 돌려야 한다.",
            "편출 종목의 가격 계열은 **마지막 멤버월에서 자른다**(재배정이 확인되지 않은 종목은 "
            "월말 리밸런스를 감안해 +1개월). yfinance 는 티커를 '오늘 그 심볼을 가진 주체'로 "
            "해석하므로, 안 자르면 사라진 회사의 티커에 남의 시계열이 조용히 이어 붙는다. "
            "SEC 현행 티커→CIK 대조(data/pit_reuse.json)로 실제 재배정을 확인한다.",
            "🚨 위의 start·n_days 는 **전역 라벨**이고 규칙마다 실효 창이 갈릴 수 있다 — 각 "
            "규칙의 start·n_days 를 볼 것(이 창에서는 %d종 중 %d종이 전역 창과 같다). 신호가 "
            "늦게 채워지는 규칙은 무보유 구간을 잘라내고 시작한다 — 2015-01 창에서는 동월 "
            "계절성이 월말 61개를 요구해 231거래일 늦었다. 재기준이 없던 동안 그 구간에서 "
            "전략 NAV 는 100 에 고정인데 대조군만 복리로 올라, PIT 초과수익이 5.27%%p 과대 음수·"
            "|t| 1.8배 과대·화면의 편향 크기가 4.5%%p 과소로 나갔다(적대감사가 잡았다). "
            "두 레그는 늦은 쪽에 함께 맞춘다 — 각자 맞추면 창이 갈려 구간 차이가 편향으로 위장한다."
            % (len(out), sum(1 for _r in out if _r.get("start") == dates[i0])),
            "채점 후보가 %d종 미만인 월말은 무보유로 둔다(소급 레그와 같은 게이트). 후보 전량이 "
            "바스켓을 통과하면 '선택'이 아니라 '있는 것 전부'이고, 그 구간 성과는 규칙이 아니라 "
            "데이터 커버리지가 만든 것이다." % TB.XSEC_MIN_POOL,
            # ⚠ 예전엔 "누락은 프리미엄 받고 사라진 쪽이라 방향이 반대"라고 적었다. 실측으로 반증됐다 —
            #   캐시 종목은 전부 오늘까지 살아 있고 보유율은 2020-09 91.8%→최근 100%로 단조 상승한다.
            #   즉 결손은 '오늘까지 못 살아남음' 그 자체이고, 누락분을 되돌리면 초과수익은 **줄어든다**
            #   (누락 기전 재현 실험: 대조군 +2.28%p, 전략 초과 중앙 +1.27%p, 모멘텀·반전 계열 전부 +).
            "월말 멤버 중 가격을 못 구한 종목이 있다(보유율 최저 %.1f%% · 중앙 %.1f%%). 이 결손은 "
            "중립이 아니다 — 남은 종목은 전부 오늘까지 살아 있고 보유율이 시간에 따라 100%%로 오른다. "
            "누락분을 되돌리면 여기 초과수익은 더 줄어든다(재현 실험상 중앙 1.3%%p). 즉 이 표조차 "
            "생존편향을 완전히 걷어내지 못했고, 남은 방향은 여전히 낙관 쪽이다. "
            "⚠ 이 결손은 편출 종목이 인수·상폐돼 yfinance 가 아예 안 주는 것이고(이 창의 편출 "
            "%d종 중 %d종), 캐시를 더 받아서 메울 수 있는 종류가 아니다."
            % (100 * cov_min, 100 * cov_med, len(_gone_all), len(_gone_all) - len(_gone)),
            "🚨 보유율(그날 가격이 있나)과 **채점 가능성**(룩백이 있나)은 다른 것이다. 창 첫달"
            "(%s)에 12개월 룩백까지 갖춰 채점 가능한 멤버는 %.1f%%다. 2026-08-11 에 편출 가격 "
            "캐시를 창 시작이 아니라 2009-01 부터 받도록 고쳐서 이 값이 보유율과 거의 같아졌다 "
            "— 고치기 전 2014-06 창에서는 첫달 채점가능이 58.8%%뿐인데 보유율은 72.0%%여서, "
            "그 차이만큼 창 앞머리의 후보가 조용히 오늘의 518종으로 좁혀져 있었다."
            % (dates[i0], 100 * cov0_look),
            "'거래량 급증' 규칙은 아예 뺐다 — 거래량이 오늘의 유니버스에만 있어 후보가 100% "
            "생존자로 좁혀지는데, 대조군에는 편출 종목이 들어가 비교가 성립하지 않는다.",
            "🚨 **편향은 bias_cagr(전략 CAGR 기준)로 읽을 것.** bias_excess 는 초과수익 기준인데, "
            "두 레그의 대조군이 각자의 동일가중 지수라 벤치에 실린 편향(실측 %.2f%%p)이 "
            "**상쇄된다** — 그래서 bias_excess 는 항상 bias_cagr 에서 그만큼 깎이고 하한이 "
            "음수가 된다. 즉 '편향 없음' 과 'PIT 가 유리' 를 구별하지 못한다. 실제로 그 탓에 "
            "고배당을 'PIT 로 오히려 좋아진다' 고 잘못 읽었다(bias_excess −4.51 이었지만 "
            "bias_cagr 는 +1.18 로 소급이 부풀려진 쪽이었다)."
            % (round((bench_bias := (out[0]["retro"]["bench"]["cagr"]
                                     - out[0]["bench"]["cagr"])) , 2) if out else 0),
            # ⚠ 문턱과 '넘는 규칙 수'를 손으로 적지 않는다 — 27종 시절 값 3.11 과 랩 51종 족
            #   3.30 이 그대로 남아 실제(33종·57종)와 어긋났던 자리다. 둘 다 도출한다.
            "t 는 이 표본(%d거래일·규칙 %d종)에서 계산한 값이다. **규칙 %d종을 한 표에서 재므로 "
            "다중검정이다** — 본페로니 5%%면 |t|≥%.2f 가 필요하다(랩 본편 %d종 족으로 보면 "
            "|t|≥%.2f). 검정족은 재측정한 수가 아니라 탐색한 가설 수여야 하므로 후자가 맞고, "
            "이 표에서 그 문턱을 넘는 규칙은 **%d종**이다(최대 |t| = %.2f). 문턱을 넘고 말고보다 "
            "'소급 대비 t 가 얼마나 무너지는가'로 읽는 것이 안전하다."
            % (n - i0, _NP, _NP, _TC, _NLAB, _TCLAB,
               sum(1 for r in out if abs(r.get("t") or 0) >= _TCLAB), _TMAX),
            "🚨 주당지표 분할 기준 — 주가는 분할조정본인데 SEC 주당지표(eps·dps)와 주식수는 "
            "당시 보고치라 한 계열에 분할 전·후 기준이 섞인다(실측: CMG sh 1387.37 옆에 27.79). "
            "그대로 두면 나중에 분할한 종목의 이익수익률·배당수익률이 분할비만큼 부풀어 **선견**이 "
            "된다 — tech_backtest.split_trim() 이 기준 불일치 관측을 잘라낸다(89종). "
            "자르기 전에는 저PER t 2.63·저PSR 2.49·고배당 2.94 로 문턱을 넘는 것처럼 보였다.",
            "규칙 %d종(가격·거래량 %d + 펀더멘털 %d). 소형주(시가총액)는 시점별 주식수를 랩의 "
            "SEC XBRL 과 yfinance(편출분)로 합쳐 재현했다 — 두 출처가 0.3~2.3%% 차이 나지만 시총이 "
            "자릿수로 벌어지는 횡단면이라 순위 영향은 미미하다. "
            "펀더멘털 규칙은 2026-07-30 에 추가했다 — 편출 종목 재무를 SEC 에서 받아(build/pit_facts.py, "
            "러너) data/fx_pit 에 넣은 뒤 가능해졌다. 편출 %d종 중 재무가 있는 것은 %d종(%.0f%%)이고, "
            "없는 %d종(폐지·개명 티커라 SEC 현행 목록에 없다)만큼 그 규칙들의 후보는 여전히 "
            "생존자 쪽으로 좁혀져 있다."
            # 🚨 '적어 둔 수' 가 아니라 **돌아간 수**를 센다. 종전에는
            #   len(PRICE_SIDS)+len(FUND_SIDS) = 48 을 적었는데 실제로 돈 것은 40종이었다 —
            #   BY 에 없는 은퇴 규칙 8종이 아래 `if not S: continue` 에서 조용히 빠지기 때문이다.
            #   목록에 적어 두면 도는 줄 알게 되는 것이 이 랩이 반복해서 겪은 사고다.
            % (len(out), sum(1 for _r in out if TB._BASE_SID(_r["sid"]) in _PRICE_SET),
               sum(1 for _r in out if TB._BASE_SID(_r["sid"]) not in _PRICE_SET),
               len(_gone), len(_fx_gone), 100 * fx_cov, len(_gone) - len(_fx_gone)),
            "비용 0(gross) · 신호는 당일 종가로 계산해 다음 거래일부터 적용(선견 없음).",
        ] + ([
            "이 파일의 PRICE_SIDS·FUND_SIDS 에 이름은 있는데 **안 돈 규칙** %d종: %s. "
            "랩 본편(tech_backtest)에서 은퇴해 BY 에 없기 때문이고, 지우지 않고 여기 적는다 — "
            "목록에 남은 이름은 도는 것처럼 보이기 때문이다."
            % (len(_retired), ", ".join(_retired)),
        ] if _retired else []) + [
        ],
        "strategies": out,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("\n→ %s · %d종 · %s ~ %s (%s년)"
          % (OUT, len(out), doc["start"], doc["as_of"], doc["span_years"]))
    return 0


# 🚨 여기 있던 score() 를 2026-08-11 에 지웠다 — 랩 본편 채점기의 **두 번째 사본**이었다.
#   sid 마다 손으로 옮긴 갈래가 700줄 있었고, 옮기기 어려운 2단 규칙(횡단면 중립화·합성·
#   섹터 정렬) 7종은 아예 옮기지 못해 PIT 을 못 돌고 있었다. 그 7종은 랩에 등록돼 소급 t 로
#   판정되면서 생존편향 검사만 안 받는 상태였다(x-hlspread 소급 t 5.00).
#   지금은 tech_backtest.xsec_score_at(S, i, X, pool) 하나를 두 레그가 같이 부른다.
#   되살리지 말 것 — 사본이 생기는 순간 어긋나기 시작한다.


def write_reuse(want, span):
    """SEC 현행 티커→CIK 와 위키 당시 CIK 를 맞대 '그 사이 티커가 다른 법인에 넘어갔는지'
    를 판정해 data/pit_reuse.json 에 적는다.

    🚨 왜 필요한가. yfinance 는 티커를 **오늘 그 심볼을 가진 주체**로 해석한다. 그래서
      사라진 회사의 티커를 요청하면 남의 시계열이 조용히 이어 붙는다. 종전 방어(계열 기간이
      멤버 기간과 겹치는가)는 계열이 2005~2026 로 통으로 이어질 때 그냥 통과한다.
      실측(2026-08-11) 편출 132종: 일치 91 · 불일치 3(AA·BBBY·BBT) · 판정불가 38.
    ⚠ 판정불가 38종은 두 갈래이고 **성격이 다르다.**
      · 위키 CIK 없음 — NDX 표에는 CIK 컬럼이 아예 없다(AZN·BIDU·JD·CHKP 같은 것).
      · SEC 현행 없음 — 아무도 그 티커를 안 갖고 있다. 이쪽은 오히려 **안전하다**
        (재배정될 수 없으니 yfinance 가 주는 것은 그 회사의 진짜 이력이거나 아무것도 없다).
      그래서 판정불가를 '재배정 아님'으로 취급하지 않고 사유별로 나눠 적는다.
    ⚠ 이 판정은 온라인이라야 한다. 그래서 백테스트가 아니라 수집 단계에 둔다 — 채점이
      네트워크에 매달리면 CI 와 로컬이 조용히 다른 결과를 낸다.
    """
    import urllib.request
    ua = {"User-Agent": "yeouido-lab/1.0 (globalkbam@gmail.com) pit-reuse-check"}
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            "https://www.sec.gov/files/company_tickers.json", headers=ua), timeout=60).read()
        sec = json.loads(raw)
    except Exception as e:
        print("  ⚠ SEC 티커지도 실패(%s) — pit_reuse.json 을 갱신하지 않는다" % str(e)[:50])
        return
    now = {}
    for v in sec.values():
        now[str(v["ticker"]).upper().replace("-", ".")] = str(v["cik_str"]).zfill(10)
    ih = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hist = ih.get("cik") or {}
    bad, unknown, ok = {}, {}, 0
    for t in want:
        h, c = hist.get(t), now.get(t)
        if not h:
            unknown[t] = "위키 CIK 없음(NDX 표에는 CIK 컬럼이 없다)"
        elif not c:
            unknown[t] = "SEC 현행 매핑 없음 — 아무도 이 티커를 안 갖고 있다(재배정 불가)"
        elif str(h).zfill(10) != c:
            bad[t] = {"wiki_cik": str(h).zfill(10), "sec_cik": c,
                      "first": span.get(t, (None, None))[0], "last": span.get(t, (None, None))[1]}
        else:
            ok += 1
    doc = {"note": ("티커가 그 뒤 다른 법인에 넘어갔는지. SEC company_tickers.json(현행)과 "
                    "data/index_history.json 의 당시 CIK 를 맞댄 것. build/pit_backtest.py 가 "
                    "읽어 그 종목의 가격 계열을 마지막 멤버월에서 자른다(--fetch-cache 가 만든다)."),
           "as_of": ih.get("as_of"), "start": START, "n_checked": len(want), "n_match": ok,
           "n_reassigned": len(bad), "n_unknown": len(unknown),
           "reassigned": bad, "unknown": unknown}
    json.dump(doc, io.open(REUSE, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("→ %s · 대조 %d종: 일치 %d · **재배정 %d** · 판정불가 %d"
          % (REUSE, len(want), ok, len(bad), len(unknown)))
    for t, v in sorted(bad.items()):
        print("   🚨 %-6s 위키 %s → SEC %s · 멤버 %s~%s" % (t, v["wiki_cik"], v["sec_cik"],
                                                          v["first"], v["last"]))


def fetch_cache():
    """편출 종목 가격을 yfinance 로 받아 캐시한다 — 저장소에 만드는 코드가 있어야 재현이 된다.

    오늘의 랩 유니버스에 없는 과거 멤버만 받는다. 지수에서 '작아져서' 빠진 회사는 대개
    아직 상장돼 있어 대부분 받아진다. 인수·상폐분은 못 받고, 그 결손의 방향은 limits 에 적는다.
    """
    import time
    import yfinance as yf
    mem = fetch_members()
    need = set()
    for v in mem.values():
        need |= set(v)
    lab = {s["t"] for s in json.load(io.open(os.path.join(DATA, "stocks.json"),
                                             encoding="utf-8"))["stocks"]}
    want = sorted(t for t in need - lab if t.isalpha() or "." in t)
    print("편출 종목 %d종 가격 수집 (yfinance)" % len(want))
    span = {}
    for ym, lst in mem.items():
        for t in lst:
            a, b = span.get(t, (ym, ym))
            span[t] = (min(a, ym), max(b, ym))
    write_reuse(want, span)
    out = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    hlout = json.load(io.open(HLCACHE, encoding="utf-8")) if os.path.exists(HLCACHE) else {}
    # 🚨 --rebuild 가 필요한 이유. 아래 루프는 '이미 있는 티커는 건너뛴다'가 기본이고
    #   저장도 setdefault 다 — 재수집 시점이 달라 값이 미세하게 흔들리면 그 위에서 잰 PIT
    #   수치가 조용히 바뀌기 때문이다. 그런데 그 보호가 **창을 앞으로 늘릴 때는 정반대로
    #   작동한다** — 캐시가 2015-01 에서 시작하는 채로 영원히 굳는다. 창을 바꾸는 실행에서만
    #   깃발로 푼다. 값이 바뀐다는 것을 알고 하는 것과 모르고 굳는 것은 다르다.
    rebuild = "--rebuild" in sys.argv
    if rebuild:
        print("  --rebuild: 기존 %d종을 %s 부터 다시 받는다(값이 바뀐다)" % (len(out), CACHE_START))
    got = 0
    for i in range(0, len(want), 25):
        # 🚨 2026-08-05 — 종전에는 `t not in out`(종가 캐시)만 봤다. 그래서 고가·저가를
        #   같은 배치에 얹었더니 **이미 종가가 있는 147종은 아예 안 받아** HL 캐시가 0종으로
        #   남았다(실행은 성공으로 끝났다 — 전형적인 '조용한 미수집'이다).
        #   둘 중 하나라도 없으면 받는다.
        ch = want[i:i + 25] if rebuild else [t for t in want[i:i + 25]
                                             if t not in out or t not in hlout]
        if not ch:
            continue
        try:
            _raw = yf.download(ch, start=CACHE_START, auto_adjust=True, progress=False,
                               threads=False)
            d = _raw["Close"]
            _hi, _lo = _raw.get("High"), _raw.get("Low")
        except Exception as e:
            print("  [yf] 배치 실패:", str(e)[:60]); continue
        for t in ch:
            if t in d:
                ser = d[t].dropna()
                if len(ser) > 200:
                    # 이미 있는 종가는 덮어쓰지 않는다 — 재수집 시점이 달라 값이 미세하게
                    # 흔들리면 그 위에서 잰 PIT 수치가 조용히 바뀐다. (--rebuild 때만 덮는다.)
                    _new = {str(k.date()): round(float(v), 4) for k, v in ser.items()}
                    if rebuild:
                        out[t] = _new
                    else:
                        out.setdefault(t, _new)
                    # 고가·저가도 같은 배치에서 받는다 — 따로 받으면 두 번 요청하고
                    # 그 사이 조정계수가 바뀌면 종가와 기준이 어긋난다.
                    if _hi is not None and _lo is not None and t in _hi and t in _lo:
                        _h, _l = _hi[t].dropna(), _lo[t].dropna()
                        hlout[t] = {str(k.date()): [round(float(_h[k]), 4), round(float(_l[k]), 4)]
                                    for k in ser.index if k in _h.index and k in _l.index}
                    got += 1
        time.sleep(2)
    json.dump(out, io.open(CACHE, "w", encoding="utf-8"), separators=(",", ":"))
    print("→ %s · %d종 (이번에 %d종 추가) · 못 받은 %d종은 인수·상폐로 보인다"
          % (CACHE, len(out), got, sum(1 for t in want if t not in out)))
    if hlout:
        json.dump(hlout, io.open(HLCACHE, "w", encoding="utf-8"), separators=(",", ":"))
        print("→ %s · %d종 — 이 파일이 있어야 고가·저가 규칙(x-52wh 등)의 PIT 레그가 돈다"
              % (HLCACHE, len(hlout)))

    # 시점별 주식수 — x-small(시가총액) 을 PIT 로 재려면 필요하다.
    # 오늘의 유니버스는 랩이 SEC XBRL 로 이미 갖고 있고(data/fx), 편출 종목만 여기서 받는다.
    # ⚠ 두 출처는 정의가 미세하게 다르다(실측 yfinance 가 0.3~2.3% 낮다). 시총이 자릿수로
    #   벌어지는 횡단면에서는 순위에 거의 영향이 없지만, limits 에 적고 민감도도 재 둔다.
    sh = json.load(io.open(SHCACHE, encoding="utf-8")) if os.path.exists(SHCACHE) else {}
    tgt = sorted(out) if rebuild else [t for t in sorted(out) if t not in sh]
    print("주식수 수집 %d종 (이미 %d종)" % (len(tgt), len(sh)))
    for k, t in enumerate(tgt):
        try:
            ser = yf.Ticker(t).get_shares_full(start=CACHE_START)
            if ser is not None and len(ser):
                # 날짜 내림차순 [(날짜, 주식수)] — 랩의 asof_fund 와 같은 모양
                sh[t] = [[str(d.date()), float(v)] for d, v in ser.items()][::-1]
        except Exception as e:
            print("  [sh] %s 실패: %s" % (t, str(e)[:50]))
        if k % 10 == 9:
            json.dump(sh, io.open(SHCACHE, "w", encoding="utf-8"), separators=(",", ":"))
        time.sleep(1.5)
    json.dump(sh, io.open(SHCACHE, "w", encoding="utf-8"), separators=(",", ":"))
    print("→ %s · %d종" % (SHCACHE, len(sh)))
    return 0


if __name__ == "__main__":
    sys.exit(fetch_cache() if "--fetch-cache" in sys.argv else main())
