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
# 🚨 거래량 캐시(2026-08-14). 고가·저가와 **같은 사유로 별 파일**이다.
#   왜 이제야 만드나: yf.download 응답에 Volume 이 처음부터 같이 왔는데 코드가 Close·High·Low
#   세 열만 꺼내 쓰고 거래량을 버리고 있었다. 그 한 줄 때문에 거래량 규칙 7종이
#   (x-volsurge · x-amihud · x-turn · x-turnchg · x-mfi · x-adslope · x-volconc)
#   "편출 종목 거래량 부재"로 시점정확 검증을 못 받았다 — 새 데이터 소스가 아니라
#   이미 받아 놓고 안 쓰던 열이다.
# ⚠ auto_adjust=True 라 분할 조정이 종가와 같은 기준으로 걸린다(거래량도 함께 조정된다).
#   랩의 vd 규약과 같은 축이다.
VOLCACHE = os.path.join(DATA, "_pit_vol_cache.json")
SHCACHE = os.path.join(DATA, "_pit_sh_cache.json")   # 편출 종목의 시점별 주식수(yfinance)
REUSE = os.path.join(DATA, "pit_reuse.json")         # 티커가 다른 법인에 넘어갔는지(SEC 대조)
OUT = os.path.join(DATA, "pit_strategies.json")
# CIK 승계로 가격을 해석한 티커(load_prices 가 채운다) — dump_universe 가 명단에 표시한다.
# 전역으로 두는 이유는 하나뿐이다: 산출물 두 개가 **같은 사실**을 말해야 하는데 함수 인자를
# 늘리면 이 파일을 사본으로 돌리는 감사 하네스들이 조용히 깨진다.
CIK_SPLICE_MAP = {}

START = "2016-08-01"
# 🚨 2026-08-14 사용자 결정 — **랩 10년 창(MAX_YEARS)에 맞춰 2021-07 에서 내렸다.**
#   요청은 "같은 창 소급·랩 본편 소급을 다 없애고 PIT 만 쓰고, 기간은 10년으로 통일" 이다.
#   그 둘은 지금 자료로 **동시에 성립하지 않는다** — 실측 커버리지가 이렇다:
#       2016 76.9%   2018 83.1%   2020 88.4%   2021 90.3%   2024 97.0%   2026 99.7%
#   ⚠ 그래서 앞구간(2016~2020)은 후보의 12~23%가 빠진 채로 고른다. **편향을 없애려는
#     레그가 그만큼 편향을 갖는다.** 그 사실을 감추지 않고 산출물에 구간별 커버리지로
#     실어 화면이 말하게 한다(cov_by_year). 사용자가 그 대가를 알고 택한 갈래다.
#   ⚠ 근본 해결은 **편출 종목 가격을 더 받는 것**이다(결손의 대부분이 그것이다).
#     EODHD EOD 플랜이 그 자리이고, 그러면 이 문턱을 도로 올릴 수 있다.
#
# 아래는 2021-07 을 골랐던 당시의 근거다 — 지웠다가 다시 필요해질 값이라 남긴다.
# 🚨 그 날짜는 **자료의 한계가 아니라 자료의 품질**로 정했다(2026-08-11, 사용자 결정).
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
# 🚨 이 파일을 굽는 워크플로가 없다(.github/workflows 전수 — pit_backtest.py 를 부르는 잡 0건).
#   그래서 소스를 고쳐도 data/pit_strategies.json 은 손으로 다시 돌리기 전까지 옛 코드로 잰
#   값이다. 산출물에 코드 판을 새겨 두고, tech_backtest 가 그것을 보고 화면에 적는다.
#   ⚠ 채점·수집에 영향을 주는 수정을 하면 이 날짜를 올릴 것(그래야 캐비엇이 다시 뜬다).
CODE_REV = "2026-09-02c"   # tech_backtest.PIT_CODE_REV 와 **같아야 한다**(validate 가 대조)
TOPN = TB.TOPN

# 가격·거래량만으로 정의되는 규칙. 펀더멘털 규칙은 시점별 재무·주식수가 없어 제외한다 —
# 반쪽만 PIT 로 바꾸면 비교가 성립하지 않는다.
PRICE_SIDS = [
             # 2026-08-12 3차 배치 — PREREG-2026-08-12-MOMENTS.md §4. 결과를 보고 넣으면
             #   사후 선택이므로 **등록과 함께 미리** 넣는다. 둘 다 종가만 쓰므로
             #   편출 종목 종가 캐시로 그대로 돈다(x-amihud 가 막힌 거래량 벽이 없다).
             "x-mommvol", "x-rskew",
             # 2026-08-15 통계 배치 — PREREG-2026-08-15-STATS.md §3. 등록과 함께 미리 넣는다.
             #   여섯 다 **종가만** 쓰므로 편출 종목 종가 캐시로 그대로 돈다.
             #   ⚠ x-pcaresid 는 횡단면 통계라 그 레그의 **후보 집합**으로 분해한다 —
             #     PIT 레그는 그달 편입 종목만으로, 소급 레그는 오늘 명단으로. 그게 맞다:
             #     주성분은 '그때 시장이 무엇이었나' 이므로 유니버스가 다르면 축도 달라야 한다.
             "x-drift-t", "x-varratio", "x-pcaresid", "x-permen", "x-cusum", "x-ecm",
             # 2026-08-16 ML6 — PREREG-2026-08-16-ML6.md §5. **등록과 함께 미리** 넣는다
             #   (결과를 보고 넣으면 사후 선택이다). 특징 12개가 전부 가격·거래량이라
             #   편출 종목 캐시로 그대로 돈다 — 일부러 그런 특징만 골랐다.
             # 🚨 여섯은 학습 행도 그달 풀로 거른다(ml_strats._train_rows). 그러지 않으면
             #   과거 학습이 «오늘까지 살아남은 종목» 만 보게 되어, 재려던 생존편향이
             #   모형 안으로 숨어 들어간다 — 이 레그가 그 숨은 편향까지 잡으라고 있는 것이다.
             "m-ridge", "m-ridge-w", "m-logit", "m-erc", "m-clust", "m-tree",
             # 2026-08-12 6차 — PREREG-2026-08-12-MACROBETA.md §4. 거시 계열은 전 종목이
             #   공유하는 하나의 계열이라 편출 종목에도 그대로 쓴다(종가만 더 있으면 된다).
             "x-ratebeta", "x-fxbeta",
             # 2026-08-14 수급 축(PREREG-2026-08-14-FLOW). 같은 배치의 거래량 4종은
             #   편출 종목 거래량이 없어 EXCLUDED_SIDS 로 갔는데 **이것만 돈다** —
             #   점수가 13F 보유금액 변화라 가격·거래량을 아예 안 쓰고, guru_history 는
             #   매니저가 그때 들고 있던 종목을 그대로 담고 있어 편출 종목도 들어 있다.
             #   ⚠ 결과를 보고 넣은 것이 아니다. 등록과 함께 넣는다.
             "x-guruacc",
             # 2026-08-14 오후 — 거래량 벽이 풀려(멤버-월 커버 96.91%, 가격과 동일)
             #   같은 배치의 셋도 여기로 온다. x-volsurge 도 EXCLUDED 에서 나갔다.
             "x-volsurge",
             # ── 밴드 변형 12종 — 2026-08-25 ──────────────────────────────────
             # 🚨 이것들은 그동안 **관문을 이름으로 통과하고 실제로는 안 돌았다.**
             #   완결성 관문이 _BASE_SID 로도 봐 줬는데, 밑동이 목록에 있으면 변형까지
             #   통과시킨다 — 그런데 PIT 루프는 목록의 sid 만 도므로 변형은 레그가 안
             #   생겼다. 관문은 «통과» 라 적고 화면은 소급 수를 머리 숫자로 썼다.
             #   전형적인 **공허 통과**다(조건이 늘 참이라 아무것도 안 막는다).
             #   → 아래에서 관문의 _BASE_SID 봐주기를 걷었다. 그래서 여기에 다 적는다.
             # ⚠ 밴드는 이력현상이라 **직전 보유가 있어야** 뜻이 있다. 위 run() 이
             #   held 를 넘기도록 같이 고쳤다 — 둘 중 하나만 하면 조용히 상위 N 이 된다.
             "x-ecm-band", "x-lshock-band", "x-max5low-band", "x-max5low-n52-band",
             "x-maxlow-band", "x-maxlow-n52-band", "x-rev1m-band", "x-rev1w-band",
             "x-snapback-band", "x-volsurge-band",
             # 🚨 2026-08-14 감사(AUDIT-2026-08-14-VOLUME) — 이 둘은 **게시 중인데 PIT 을
             #   한 번도 안 받은 상태**였다. 제외 사유가 "편출 종목 거래량 부재" 였고
             #   그 항목에 "받아 오면 풀린다"고 적혀 있었는데, 오늘 그 거래량을 받았다.
             #   x-turn 은 분모의 시점별 주식수도 필요한데 그쪽은 이미 605종이 있다.
             # ⚠ x-amihud 의 **자료 타당성 우려는 그대로 남는다**(거래대금은 미국 상장분인데
             #   가격은 회사 전체를 따라 움직인다 — 고른 것이 「거래가 어려운 회사」가 아니라
             #   「미국에서 일부만 거래되는 회사」다). 그것은 PIT 이 답하는 질문이 아니고,
             #   재는 것과 그 수가 무엇을 뜻하는지는 다른 축이다. 둘 다 적는다.
             "x-amihud", "x-turn",
             "x-mom12", "x-lowvol", "x-rev1m", "x-52wh", "x-dist200",
             # 2026-09-02 QUANTILE4 — 짝과 같은 갈래를 탄다(_BASE_SID). 크기만 다르다.
             "x-mom12-n52", "x-52wh-n155",
              "x-mom-trend", "x-rev1w", "x-minvar", "x-riskbudget", "x-lowbeta",
              "x-snapback", "x-maxlow", "x-max5low", "x-recency", "x-ivol",
              "x-small",   # 시가총액 = 시점별 주식수 × 종가 (아래 SH 참조)
              # 2026-07-30 웹 리서치로 추가. 🚨 여기 안 넣으면 새 규칙이 **소급 t 로만** 판정돼
              # '통과 후보' 가 된다 — 이 파일이 막으려는 바로 그 일이다(소급 t 3.2~3.7 이 나왔다).
              "x-echo", "x-season", "x-coskew",
              # 2026-07-31 추가(가격만 쓰는 것)
              "x-ltrev", "x-lowcorr",
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
              "x-hlspread", "x-clv", "x-volvol", "x-residmom", "x-indmom",
              "x-residmom-n52",        # 2026-09-02 QUANTILE4
              # 🚨 2026-08-12 재검증에서 이 파일의 완전성 가드가 잡았다 — 7차 배치
              #   (PREREG-2026-08-12-PATH.md)의 둘이 랩에는 등록됐는데 여기 없었다.
              #   그 상태에서는 PIT 을 못 재고 소급 t 로만 판정되며, 화면에 아무 표시도 안 난다
              #   (x-volratio 는 실제로 소급 t 2.86 으로 '통과 후보'에 올라 있었다).
              #   둘 다 일간 수익률만 쓰므로 편출 종목 종가 캐시로 그대로 돈다.
              "x-acorr", "x-volratio",
              # 시가총액 하한 변형 3종 — PREREG-2026-08-12-MCAPFLOOR.md §4.
              #   결과를 보고 넣으면 사후 선택이므로 **등록과 함께 미리** 넣는다.
              #   가격과 시점별 주식수만 쓰므로 편출 종목 캐시(_pit_px_cache·_pit_sh_cache)로
              #   그대로 돈다. 하한은 랩 함수 xsec_score_at 안에서 걸리므로 이쪽에 배선은 없다.
              # 2026-08-25 — -mcf 변형 등록을 그만뒀다(시총 하한이 기본이 됐다).
              #   PREREG-2026-08-25-DEFAULT-PIT.md 참조.
              # 확률·통계 축 5종 — PREREG-2026-08-13-STAT5.md §4.
              #   🚨 **등록과 동시에** 넣는다(결과를 보고 넣으면 사후 선택이다). 다섯 다 종가만
              #   쓰므로 편출 종목 캐시로 그대로 돈다 — 일부러 그런 규칙으로 골랐다.
              "x-kurt", "x-jump", "x-hurst", "x-runs", "x-entropy",
              # 2차 배치 — PREREG-2026-08-13-STAT2.md §4. 등록과 동시에 넣는다.
              #   다섯 다 종가만 쓰므로 편출 종목 캐시로 그대로 돈다.
              #   ⚠ x-distshape 는 횡단면 z 합성이라 2단이지만, 랩 함수를 그대로 부르는
              #     구조라(2026-08-11 개편) 사전패스가 같이 따라온다.
              "x-distshape", "x-hill", "x-lbq", "x-archlm"]

# 펀더멘털 규칙 — 2026-07-30 추가. 편출 종목 재무를 data/fx_pit 로 받고 나서 가능해졌다
# (build/pit_facts.py, 러너에서 SEC 수집). 그 전에는 "시점별 재무가 없어 제외" 였다.
#   ⚠ 재무 커버리지가 가격보다 낮다 — 편출 종목 중 몇 종이 실제로 채점되는지 매 실행에 찍고
#     limits 에 싣는다. 커버리지가 낮으면 그 규칙의 PIT 는 '후보가 생존자로 좁혀진' 쪽이다.
FUND_SIDS = [
             # 산업잔차 모멘텀 — PREREG-2026-08-29-RESIDIND. 가격만이 아니라 발행주식수가
             #   필요하다(산업그룹 수익을 시총가중으로 낸다). 그래서 PRICE_SIDS 가 아니라
             #   여기다.
             # 🚨 한계를 여기 적어 둔다 — 산업 분류(members.json 의 grp)는 **현재 명단**만
             #   갖고 있다. PIT 후보에 든 편출 종목은 grp 가 없어 채점에서 통째로 빠진다.
             #   즉 이 규칙의 PIT 레그는 «가격은 시점정확인데 분류는 생존자만» 인 반쪽이고,
             #   등록 §5 가 예고한 그 편향이다. 후보 수가 다른 규칙보다 얇게 나오면 그 탓이다.
             "x-residind",
             "x-ep", "x-sp", "x-btp", "x-roe", "x-npm", "x-rgrow", "x-lowde",
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
             # 2026-08-30 BASKET2 — 짝 x-poacc 와 같은 갈래를 탄다(_BASE_SID).
             "x-poacc-n52",
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
             "x-currat",
             # 🚨 2026-08-12 재검증 — 위 PRICE_SIDS 의 같은 사유(가드가 잡았다).
             #   x-reta 는 이익잉여금 ÷ 총자산이라 re 와 asset 이 둘 다 있어야 채점된다.
             #   실측 커버리지: 편출 71/75(95%) · 랩 502/519(97%) 로 거의 같다 —
             #   후보가 생존자로 좁혀지지 않으므로 두 레그 비교가 성립한다(x-currat 과 같은 기준).
             "x-reta",
             # 2026-09-02 A1 — PREREG-2026-09-02-A1PAYOUT.md. 자격필터형이라 후보 수
             #   관문을 안 탄다(TB.min_pool → SCREEN_SIDS). PIT 레그도 같은 함수를
             #   쓰므로 그쪽 관문도 같이 풀린다 — 안 그러면 편출 후보가 붙어도 22종짜리
             #   바스켓이 30 문턱에 걸려 통째로 무보유가 된다.
             # ⚠ 짝 x-divgrow 와 같은 반쪽 한계를 그대로 물려받는다 — 편출 145종 중
             #   dps 가 71종(49%)뿐이라 무배당과 자료없음을 못 가른다. 게다가 이 규칙은
             #   bb·debt·cash·opinc·dep 까지 요구하므로 편출 쪽 커버가 더 얇아진다.
             #   PIT 후보가 랩보다 크게 얇으면 그 사실을 결과 문서에 적는다.
             "x-a1payout",
             # 2026-09-02 QUANTILE4 — 짝 x-shiss 와 같은 갈래를 탄다(_BASE_SID).
             "x-shiss-n52",
             # 2026-09-02 BMROT — 자기자본/시총. 선택은 TB.xsec_pick_at 의 갈래를 그대로 탄다
             #   (그 함수가 가중 바스켓을 돌려주므로 두 레그가 안 갈린다 — 등록 §0-1).
             "x-bmrot", "x-bmrot-flat"]

# ── 타이밍·오버레이 22종 ────────────────────────────────────────────────────
# 🚨 2026-08-14 — **이제 잰다.** 종전에는 산출물의 na_timing 이 "타이밍 규칙은 지수·ETF 를
#   매매하므로 생존편향이 걸리는 자리가 아니다" 라고 적고 이 표에서 통째로 빠져 있었다.
#   그 문장이 사실이 아니다 — 타이밍이 매매하는 것은 ixr, 곧 **동일가중 바스켓**이고
#   (tech_backtest 가 그 자리에 "타이밍 전략이 실제로 매매하는 대상" 이라고 적어 두었다)
#   랩 유니버스로 만든 그 바스켓은 실제 동일가중 S&P 500 보다 연 +6.58%p 앞선다. 즉
#   생존편향이 정면으로 걸리고, 평균 노출만큼 그대로 실린다.
# ⚠ 이 규칙들은 종목을 안 고르므로 후보 커버리지 게이트(XSEC_MIN_POOL)와 무관하다.
#   대신 **계열이 유니버스에 딸린다** — disp·mclv·brd·ixr 을 그때 명단으로 만들어야 하고,
#   그것을 TB.timing_ctx 가 members_at 을 받아 처리한다.
# 이벤트 규칙 6종(kind="event") — 2026-08-24. 관문(_orphan)이 이제 이쪽도 본다.
# ⚠ 이 여섯은 «상위 N 바스켓» 이 아니라 종목마다 진입·청산일이 다르다. run() 의
#   이벤트 갈래가 랩 본편 event_weights 를 그대로 불러 두 레그를 만든다.
# 🚨 실적 3종은 발표일(8-K 접수 도장)이 그 자체로 시점정확이라 **완전 PIT** 이 된다 —
#   편출 종목의 발표일도 CIK 로 남아 있다. FIP 3종은 가격만 쓰므로 역시 완전 PIT 이다.
EVENT_SIDS = ["x-pead", "x-pead-sue", "x-earngap",
              "x-fip-base", "x-fip-cont", "x-fip-disc",
              # 프로그인더팬 롱숏 4종 — PREREG-2026-08-26-FIPSN.md.
              # 🚨 x-subls·x-subom 이 PIT 에서 빠진 사유는 **서브산업** 부재였다(편출 336종 중
              #   0종). 이 넷은 서브산업을 안 쓰고 **섹터**만 쓰는데, 편출 종목의 섹터는
              #   data/pit_sector.json 으로 이미 메워져 있다(72/72). 그래서 완전 PIT 이 된다.
              # ⚠ 업종중립 둘은 섹터가 없으면 후보에서 스스로 빠진다(fip_baskets) — 편출
              #   종목의 섹터가 비면 그 종목이 조용히 사라지므로, 결과에 섹터 커버를 싣는다.
              "x-fipq-cont", "x-fipq-disc", "x-fipq-cont-sn", "x-fipq-disc-sn",
]
# ⚠ 2026-08-25 — FIP 의 -mcf 3종은 등록을 그만뒀다(시총 하한이 기본이 됐다).
#   PREREG-2026-08-25-DEFAULT-PIT.md 참조. 측정 기록은 FIPMCF-RESULT.md 에 남는다.

# 2026-08-24 신규 횡단면 — 관문(_orphan)이 잡아서 배선했다.
#   가격·거시만 쓰는 둘은 편출 종목에도 그대로 적용된다(거시 계열은 전 종목 공유).
NEW_PRICE_SIDS = ["x-ratehot", "x-fxweak"]
#   재무를 쓰는 일곱. 편출분은 data/fx_pit(재무)·_pit_sh_cache(주식수)로 덮인다.
NEW_FUND_SIDS = ["x-realsw",
                 "x-capw", "x-cap10", "x-cap5", "x-cap45", "x-cap3", "x-capndx",
                 # NDX 전용 5종 — PREREG-2026-08-25-NDXONLY. 유니버스만 좁혔을 뿐
                 #   자료 요구는 같으므로 PIT 이 그대로 돈다.
                 "x-ncapw", "x-ncap10", "x-ncap5", "x-ncap45", "x-ncapndx"]

TIMING_SIDS = ["t-sma200", "t-cross", "t-chan", "t-macd", "t-gapcap", "t-mhvote",
               "t-donch", "t-ddgate", "t-chand", "t-voltgt", "t-clvgate",
               "t-breadth", "t-breadthc", "t-tom", "t-mavote", "t-volreg",
               "t-kama", "t-tsmom", "t-tsmom6", "t-kelly", "t-semivol", "t-disp"]

# x-volsurge 는 뺐다. 거래량이 랩 파일(오늘의 유니버스)에만 있어 편출 85종의 채점률이 정확히
# 0%다 — 후보가 100% 생존자인 채로 편출종목을 포함한 대조군과 겨루게 되어, 이 파일이 없애려는
# 바로 그 선견이 규칙 하나에만 남는다. 거래량을 편출종목까지 받으면 되살릴 수 있다.
EXCLUDED_SIDS = {
    # ── 밴드 변형 둘 — 밑동과 **같은 사유**로 빠진다(2026-08-25) ──────────────
    #   밑동(x-revdrift · x-revdrift-sn)이 아래에서 제외된 그 사유가 변형에도 그대로
    #   적용된다. 변형만 돌리면 밑동과 다른 유니버스를 보게 되어 둘을 못 나란히 놓는다.
    "x-revdrift-band": "밑동 x-revdrift 와 같은 사유 — 아래 항목 참조",
    # 2026-08-30 BASKET2 — 크기만 다른 변형이라 밑동의 자료 제약을 그대로 물려받는다.
    "x-revdrift-n25": "밑동 x-revdrift 와 같은 사유 — 아래 항목 참조",
    "x-revdrift-sn-band": "밑동 x-revdrift-sn 과 같은 사유 — 아래 항목 참조",
    # ── 2026-08-24 GICS 서브산업 기반 3종 — **자료가 없어 완전 PIT 이 불가능하다** ────
    # 🚨 실측: 창 안 편출 종목 336종 중 GICS 서브산업(members.json 의 sub)이 있는 것이
    #   **0종**이다. members.json 은 오늘 명단만 담고, 편출 종목의 산업 분류는 랩 어디에도
    #   없다(가격은 pit_px, 재무는 fx_pit 로 덮었지만 분류는 원천이 다르다).
    #   그래서 이 셋을 PIT 로 돌리면 편출분이 후보에서 통째로 빠져 **«PIT» 이라 적힌
    #   생존자 백테스트**가 된다 — 그것이 이 파일이 막아야 할 실패다.
    # ⚠ 「자료가 없어 PIT 을 못 잰다」는 대개 절반만 맞다(선견은 자료 없이 보정된다).
    #   그런데 이 셋은 **선택 단위가 서브산업**이라, 편출 종목이 빠지면 서브산업의 구성
    #   자체가 달라진다 — 선견만 보정하는 부분 PIT 도 뜻이 없다.
    #   → 분류 이력을 모으면(그때는 새 수집기가 필요하다) 그때 여기서 뺀다.
    "x-subls": "편출 종목의 GICS 서브산업이 랩에 없다(336종 중 0종) — 선택 단위가 "
               "서브산업이라 편출분이 빠지면 구성 자체가 달라져 부분 PIT 도 뜻이 없다",
    "x-subom": "위와 같다(x-subls 참조)",
    "x-curvebank": "은행·보험 서브산업으로 후보를 좁히는데 편출 종목의 서브산업이 없다 — "
                   "그 창의 편출 은행이 통째로 빠진다",

    # 🚨 2026-08-14 오후 — **거래량 벽이 풀렸다.** yf.download 응답의 Volume 열을 안 꺼내
    #   쓰고 있었을 뿐이고, 꺼내 _pit_vol_cache.json 으로 저장하니 PIT 창 멤버-월 커버가
    #   가격·고저가와 **정확히 같은 96.91%** 가 됐다(36226/37382 · 셋이 같은 수다).
    #   그래서 x-volsurge 를 여기서 뺀다 — 제외 사유("편출 종목 거래량 부재")가
    #   사실이 아니게 됐기 때문이다. 남은 3.09% 는 최근 상폐로 yfinance 가 더는 주지
    #   않는 41종이고, 그 결손은 **가격 규칙도 똑같이** 안고 있다.
    # ⚠ x-amihud · x-turn 은 여기서 되살리지 않는다. 그 둘이 걷힌 사유는 거래량 부재가
    #   아니라 **자료 타당성**이었다(거래대금은 미국 상장분인데 가격은 회사 전체를 따라
    #   움직인다 — 고른 것이 「거래가 어려운 회사」가 아니라 「미국에서 일부만 거래되는
    #   회사」였다). 벽이 하나 풀렸다고 다른 사유까지 풀린 것처럼 쓰지 않는다.
    # 🚨 2026-08-11 — 여기 13종이 더 있었다. 사유는 둘이었고 **둘 다 사라졌다**:
    #   · '횡단면 사전패스 필요' 7종 — 이 파일이 채점기 사본을 갖고 있어서 2단 규칙을
    #     표현하지 못한 것이었다. 사본을 지우고 랩 함수를 부르니 그대로 돈다.
    #   · '편출 종목 섹터 부재' 3종 — data/pit_sector.json 으로 메웠다(72/72).
    #   남는 것은 **자료 원천이 생존자만 주는** 것들이었는데, 2026-08-14 에 거래량이
    #   풀리면서 x-volsurge 도 나갔다(아래 블록). '코드로 못 푼다'가 셋 중 하나는
    #   틀렸던 셈이다 — 못 푸는 것과 안 푼 것은 다르다.
    # 🚨 2026-08-12 — 사전등록 PREREG-2026-08-12-LIQ-CAL.md 의 두 규칙. x-volsurge 와
    #   **정확히 같은 사유**다(거래량이 오늘의 유니버스에만 있다). 등록할 때 이 제약을
    #   못 봤다 — 후보 밀도는 월별로 쟀는데 PIT 가능 여부를 안 쟀다.
    #   x-amihud 는 소급 표본에서 t 6.84 로 문턱을 크게 넘는데, 1순위 이웃 x-small 의
    #   실측 생존편향이 초과수익 +49.67%p(소급 t 6.97 → PIT t 0.52)다. 즉 이 규칙의 t 를
    #   검증할 유일한 수단이 바로 여기서 막혀 있다.
    # ⚠ 2026-08-12 저녁 — x-amihud·x-turn 은 라이브 목록에서 **걷혔다**(자료 타당성 기각 ·
    #   build/tested_not_published.json). 아래 사유는 그때의 기록으로 남긴다.
    # ⚠ 아래 세 줄은 2026-08-19 부터 **화면에 안 나간다.** 세 규칙은 부분 시점정확으로
    #   실제로 재고 있고(PARTIAL_PIT_SIDS · 바로 아래), 잰 것은 excluded 에서 뺀다.
    #   문장은 지우지 않고 남긴다 — 「생존 채널이 왜 막혔나」는 여전히 사실이고,
    #   그 사실이 부분 레그의 이름(«완전» 이 아닌 이유)을 설명하는 근거다.
    "x-revdrift": "편출 종목 투자의견 이력 부재 — yfinance 의 upgrades_downgrades 는 지금 "
                  "상장돼 있는 종목만 준다. 나중에 받아 채울 수 있는 종류가 아니다(보완 불가). "
                  "🚨 단 이것은 **생존 채널만** 막는다 — 선견은 2026-08-19 부터 보정한다.",
    "x-revdrift-q": "편출 종목 투자의견 이력 부재 — 자료 원천이 생존자만 준다(생존 채널 보완 불가). "
                    "선견 채널은 2026-08-19 부터 보정한다.",
    "x-revdrift-sn": "편출 종목 투자의견 이력 부재 — 자료 원천이 생존자만 준다(생존 채널 보완 불가). "
                     "선견 채널은 2026-08-19 부터 보정한다.",
}

# 🚨 2026-08-19 사용자 지적 — 「보완 불가」는 **절반만 맞다.**
#   이 랩은 유니버스 편향을 두 채널로 나눠 놓았다(build/style_pit.py 머리말):
#       선견(lookahead)   그때 지수에 없던 종목을 오늘 명단으로 미리 고른 것
#       생존(survivorship) 그 뒤 편출된 종목이 오늘 명단에서 빠져 있는 것
#   위 세 규칙이 막힌 것은 **생존 채널뿐**이다(편출 종목의 투자의견을 원천이 안 준다 —
#   ATVI·TWTR·XLNX·CERN·DISCA 를 직접 받아 보면 404 에 0건이다). 그런데 **선견 채널은
#   막혀 있지 않다** — 그때 지수에 없던 종목을 «빼는» 것뿐이라 사라진 종목의 자료가
#   전혀 필요 없고, 편입 이력(data/index_history.json · 147개월)은 이미 있다.
#   크기: 오늘 518종 중 2016-08 에 지수에 없던 것이 179종(35%)이다. 즉 소급 레그는
#   후보의 3분의 1을 미리 알고 골랐다.
# → 그래서 세 번째 레그를 만든다: 후보를 «그때 편입 ∩ 오늘 유니버스» 로 제한한다.
#   선견은 사라지고 생존은 남는다. 그래서 이름이 «부분 시점정확» 이다 — 완전 PIT 이라
#   부르면 안 되는 것을, 소급이라 부르고 마는 것도 틀리다.
#   ⚠ 새로 지어낸 구성이 아니다. 스타일 랩이 이미 같은 것을 «mask» 레그로 쓰고 있다
#     (build/style_pit.py: "mask … 선정 시점 멤버 ∩ 오늘 → base 대비 차이가 선견").
#     같은 구성에 두 이름을 붙이지 않도록 여기 그 대응을 적어 둔다 — 채점기 한 벌 규약.
PARTIAL_PIT_SIDS = {"x-revdrift", "x-revdrift-q", "x-revdrift-sn"}
# 고가·저가 캐시를 받아 두면 그 사유가 사라진다. 손으로 지우게 두지 않고 **파일 유무로 정한다** —
# 사람이 지우는 것을 잊으면 규칙이 영영 검정을 안 받고, 그건 오늘 하루 내내 잡은 사고 유형이다.
if os.path.exists(HLCACHE):
    try:
        _hl = json.load(io.open(HLCACHE, encoding="utf-8"))
    except Exception:
        _hl = {}
    if len(_hl) >= 100:            # 편출 종목 대부분이 있어야 후보가 생존자로 좁혀지지 않는다
        EXCLUDED_SIDS.pop("x-52wh", None)
        EXCLUDED_SIDS.pop("x-52wh-n155", None)     # 2026-09-02 QUANTILE4 — 짝과 같이 푼다


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
    import index_members as _IM                     # noqa: E402  같은 build/ 안
    mem, carried = _IM.load(START)
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


def cik_aliases(missing, have, px=None, MEMBER_SPAN=None, tried=None):
    """결손 티커 → **같은 CIK** 의 다른 티커(가격이 있는 것). 개명만 잇고 인수는 안 잇는다.

    🚨 왜 있는가. 종전에는 가격을 못 받은 티커를 전부 "인수·상폐로 보인다"고 단정했다
      (fetch_cache 의 마지막 줄 · 전형적인 fail-open 이다). 그런데 그중 상당수는 **개명**이고,
      승계 티커에 그 회사의 이력이 통째로 남아 있다 — yfinance 는 심볼이 바뀌면 새 심볼
      아래로 과거를 그대로 준다. 랩은 승계 티커를 한 번도 시도한 적이 없었다.
      자료는 이미 저장소에 있었다: data/index_history.json 의 cik(티커→CIK)와 cik_hist
      (CIK→티커목록). 수집해 두고 **가격 해석에는 안 쓰고** 있었을 뿐이다.

    🚨 CIK 가 다르면 절대 잇지 않는다. 다른 CIK = 인수다(실측: DRE 0000783280 ≠ PLD
      0001045609 · INFO 0001598014 ≠ SPGI 0000064040 · WRK 0001732845 ≠ SW 0002005951).
      피인수 주주는 프리미엄을 받고 나갔고, 인수기업 가격을 피인수 이력에 얹으면 없는 가격을
      지어내는 것이다. CIK 로 잇기 때문에 티커 재사용(FB → ProShares ETF)도 자동으로 막힌다 —
      재사용은 CIK 가 다르다.

    ⚠ 세 갈래를 막는다.
      · cik_conflicts 에 실린 CIK — 그 파일 스스로 파싱 사고라 적어 두고 '조인에 쓰지 말 것'
        이라 한 묶음이다(JCI/TYC · CB/ACE · BKNG/PCLN …).
      · **복수 클래스** — 같은 CIK 라도 같은 달에 함께 멤버인 짝(GOOGL/GOOG, FOX/FOXA)은
        서로 다른 증권이다. 한쪽 가격을 다른 쪽에 얹는 것은 개명이 아니라 날조다. 판정은
        refresh_index_history.py 와 같은 기준(같은 달 공존 여부)으로 하고, 공존 판정은
        창이 아니라 **파일 전체 월**로 본다(넓게 볼수록 안전한 쪽이다).
      · CIK 이 둘 이상으로 갈리는 티커(VIAC 은 0000813828 과 0001339947 에 함께 나온다) —
        어느 법인인지 이 자료로 못 정한다. 안 잇는다.

    ⚠ cik_hist 만 보면 안 된다. 그 지도는 '이번 파싱에서 이름을 관측한 CIK' 만 담아서
      구멍이 있다(실측: cik_hist['0000849399'] = [GEN, SYMC] 인데 NLOK 이 빠져 있다.
      NLOK 은 cik 지도에는 0000849399 로 제대로 있다). 두 지도를 **합쳐서** 뒤집는다 —
      한쪽만 봤다면 NLOK·PEAK 2종 48멤버-월을 그냥 놓쳤다.

    ⚠ tried = '가격을 실제로 시도해 본 티커' 집합. 없으면 사유 문장이 '형제에도 가격이 없다'로
      뭉개지는데, 그것은 이 함수가 없애려는 단정("못 받음 = 없음")의 축소판이다. 실측으로
      걸렸다: 캐시가 비어 있는 상태에서 LB 의 사유가 '형제 BBWI 에도 가격이 없다' 였는데
      BBWI 는 그냥 **아직 안 받은** 것이었고, 캐시를 채우자 LB→BBWI 로 정상 승계됐다.

    돌려주는 것: (alias {결손티커: 승계티커}, rows [승계 근거], skip {결손티커: 사유}).
    """
    tried = set(tried or ()) | set(have)
    p = os.path.join(DATA, "index_history.json")
    if not os.path.exists(p):
        return {}, [], {}
    ih = json.load(io.open(p, encoding="utf-8"))
    conf = {str(x.get("cik")) for x in (ih.get("cik_conflicts") or [])}
    ck = {t: str(c).zfill(10) for t, c in (ih.get("cik") or {}).items() if c}
    hist = {str(c).zfill(10): list(ts) for c, ts in (ih.get("cik_hist") or {}).items()}
    inv, of = {}, {}                       # CIK → 티커집합 · 티커 → CIK집합
    for t, c in ck.items():
        inv.setdefault(c, set()).add(t); of.setdefault(t, set()).add(c)
    for c, ts in hist.items():
        for t in ts:
            inv.setdefault(c, set()).add(t); of.setdefault(t, set()).add(c)
    where = {}                             # 티커 → 등장한 달 집합(복수 클래스 판정용)
    for mk, rec in (ih.get("months") or {}).items():
        for t in (rec.get("spx") or []) + (rec.get("ndx") or []):
            where.setdefault(t, set()).add(mk)

    alias, rows, skip = {}, [], {}
    for t in sorted(missing):
        cs = {c for c in of.get(t, set()) if c not in conf}
        if not cs:
            skip[t] = "CIK 없음(NDX 표에는 CIK 컬럼이 없다) 또는 cik_conflicts"
            continue
        if len(cs) > 1:
            skip[t] = "CIK 이 %d개로 갈린다(%s) — 어느 법인인지 못 정한다" % (len(cs), ",".join(sorted(cs)))
            continue
        c = cs.pop()
        sib = [a for a in sorted(inv.get(c, set())) if a != t]
        cand = [a for a in sib if a in have and not (where.get(t, set()) & where.get(a, set()))]
        if not cand:
            co = [a for a in sib if a in have]
            if co:
                skip[t] = "같은 CIK 형제가 같은 달에 공존한다(복수 클래스) — %s" % ",".join(co)
            elif not sib:
                skip[t] = "같은 CIK 에 다른 티커가 없다(형제 없음)"
            else:
                # 🚨 '시도했지만 못 받음' 과 '아직 안 받음' 을 가른다. 뭉치면 고칠 수 있는 것이
                #   고칠 수 없는 것처럼 보인다 — 이 파일이 방금 없앤 단정과 같은 모양이다.
                _t1 = [a for a in sib if a in tried]
                _t0 = [a for a in sib if a not in tried]
                skip[t] = ("같은 CIK 형제에도 가격이 없다 — 시도했지만 못 받음 %s · "
                           "**아직 안 받음** %s(받아 오면 이어질 수 있다)"
                           % (",".join(_t1) or "없음", ",".join(_t0) or "없음"))
            continue
        # 후보가 둘 이상이면 **멤버 기간을 실제로 덮는 쪽**을 고른다(개명 사슬 SYMC→NLOK→GEN).
        lo, hi = (MEMBER_SPAN or {}).get(t, (None, None))
        def _cov(a):
            if not px or a not in px or not lo:
                return 0
            return sum(1 for d in px[a] if lo <= d[:7] <= hi)

        def _covm(a):
            """멤버 기간 중 **월** 몇 개를 덮나. 거래일 수로만 보면 1일짜리도 승계로 통과한다."""
            if not px or a not in px or not lo:
                return 0
            return len({d[:7] for d in px[a] if lo <= d[:7] <= hi})
        a = sorted(cand, key=lambda x: (-_cov(x), x))[0]
        # 창 안 멤버 기간의 월 수(근사: first~last 연속 월). 부분 승계를 드러내는 분모다.
        _sm = 0
        if lo:
            _y0, _m0 = int(lo[:4]), int(lo[5:7])
            _y1, _m1 = int(hi[:4]), int(hi[5:7])
            _sm = (_y1 - _y0) * 12 + (_m1 - _m0) + 1
        alias[t] = a
        rows.append({"t": t, "via": a, "cik": c, "first": lo, "last": hi,
                     "n_days_in_span": _cov(a),
                     # ⚠ 문턱이 n_days_in_span>0 하나뿐이면 계열이 멤버 기간의 앞 10%만 덮어도
                     #   같은 문구로 통과한다. 덮은 월 비율을 함께 싣고 부르는 쪽이 경고한다.
                     "months_in_span": _covm(a), "span_months": _sm,
                     "span_ratio": round(_covm(a) / _sm, 4) if _sm else 0.0})
    return alias, rows, skip


def load_prices(need, MEMBER_SPAN, MEM=None):
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
    bad_reuse, cut, bad_scale = [], [], []
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
        # ③ 🚨 **크기 검사** — ①②를 다 통과하고도 값 자체가 다른 상장물인 계열이 있다.
        #   실측(2026-08-17): PARA 는 멤버 기간(2022-02~2025-07) 안에서 57.80 ~ 113,900 으로
        #   **1,971배** 움직인다. ①은 기간이 겹쳐서 통과하고, ②는 꼬리가 아니라 전 구간이라
        #   못 자른다. 그 상태로 2024년 12개월 수익률이 **−98.4%** 로 계산됐다(실제
        #   파라마운트는 −40% 안팎). 되돌림·손실주 계열 규칙이 이것을 «싼 종목» 으로 집으면
        #   그 달의 PIT 수익이 통째로 거짓이 된다 — 생존편향을 재려고 만든 레그가 다른
        #   오염으로 흔들리는 것이라 조용히 두면 안 된다.
        # ⚠ 문턱 100배는 «주식이 그럴 수 있는 범위» 가 아니라 «자료 사고를 가르는 선» 이다.
        #   10년에 100배는 NVDA 급이고 그마저 이 캐시엔 없다(편출 종목이므로). 실측으로
        #   100배를 넘는 계열은 PARA 하나뿐이다 — 문턱이 실제로 무엇을 자르는지 세어 봤다.
        _mv = [v for d, v in ser.items()
               if v and v > 0 and MEMBER_SPAN.get(t, ("9999", "0000"))[0] <= d[:7]
               <= MEMBER_SPAN.get(t, ("9999", "0000"))[1]]
        if len(_mv) >= 30 and max(_mv) / min(_mv) > 100.0:
            bad_scale.append((t, min(_mv), max(_mv), max(_mv) / min(_mv)))
            continue
        px[t] = ser
    n_cache = len(px) - n_lab

    # ── CIK 승계로 결손 메우기 ─────────────────────────────────────────
    # 🚨 여기까지 와도 가격이 없는 멤버가 남는다. 종전에는 그것을 전부 '인수·상폐'로 두고
    #   끝냈는데, 그 안에 **개명**이 섞여 있다(BK→BNY 58개월 · MMC→MRSH 54개월 …).
    #   개명은 같은 법인이라 승계 티커에 그 회사의 이력이 통째로 있다 — 잇는 것이 맞다.
    #   인수는 CIK 가 달라 아래 함수가 애초에 후보로 삼지 않는다(자세한 것은 그 주석).
    _mmc = {}                                   # 티커 → 창 안 멤버-월 수(결손 크기를 가중해서 센다)
    for _ym, _lst in (MEM or {}).items():
        for _t in _lst:
            _mmc[_t] = _mmc.get(_t, 0) + 1
    alias, arows, askip = cik_aliases(sorted(need - set(px)), set(px), px, MEMBER_SPAN,
                                      tried=set(cache) | set(px) | set(bad_reuse))
    spliced, thin = [], []
    for r in arows:
        t, a = r["t"], r["via"]
        # 🚨 승계 티커 자신이 **재배정 티커**면 잇지 않는다. 오늘 그 심볼을 가진 주체가 다른
        #   법인이라는 뜻이고, 그 계열을 얹는 것은 개명 승계가 아니라 남의 가격이다. 지금
        #   창에서는 0건이지만 검사가 아예 없었다 — 없는 관문은 아무 신호도 내지 않는다.
        if a in reassigned:
            askip[t] = "승계 후보 %s 가 SEC 대조에서 재배정 티커다 — 오늘 그 심볼은 다른 법인이다" % a
            continue
        if not r["n_days_in_span"]:
            # 승계 티커 계열이 그 티커의 멤버 기간을 안 덮으면 이을 것이 없다. 조용히 넘기지
            # 않고 사유로 남긴다 — '이었는데 아무것도 안 채워졌다' 를 화면이 구별할 수 있어야 한다.
            askip[t] = "승계 후보 %s 의 계열이 멤버 기간(%s~%s)을 안 덮는다" % (a, r["first"], r["last"])
            continue
        # ⚠ 여기서는 재배정 절단을 적용하지 않는다. 재배정 판정(pit_reuse.json)은 '그 티커가
        #   오늘 남의 것' 이라는 뜻인데, 우리가 쓰는 계열은 **승계 법인의 다른 티커**라 그
        #   오염 경로가 아니다. 그래서 다른 편출 종목과 같이 월말 리밸런스분 +1개월을 준다
        #   (이 창에서는 LB→BBWI 1건이 해당한다).
        cm = cutoff_month(t, MEMBER_SPAN, set())
        ser = {d: v for d, v in px[a].items() if not cm or d[:7] <= cm}
        if not ser:
            askip[t] = "승계 후보 %s 를 마지막 멤버월(%s)에서 자르니 남는 구간이 없다" % (a, cm)
            continue
        px[t] = ser
        r["n_member_months"] = _mmc.get(t, 0)
        # 부분 승계 — 계열이 멤버 기간을 다 안 덮으면 '이었다' 로 뭉뚱그리지 않는다.
        if (r.get("span_ratio") or 0) < 0.9:
            thin.append(r)
        spliced.append(r)
    CIK_SPLICE_MAP.update({r["t"]: r["via"] for r in spliced})
    if thin:
        print("  ⚠ 부분 승계 %d종(계열이 멤버 기간의 90%% 미만을 덮는다): %s"
              % (len(thin), ", ".join("%s→%s(%.0f%%)" % (r["t"], r["via"], 100 * r["span_ratio"])
                                      for r in thin)))
    if spliced:
        print("  🔗 CIK 승계로 이은 결손 %d종 · %d멤버-월: %s"
              % (len(spliced), sum(r.get("n_member_months", 0) for r in spliced),
                 ", ".join("%s→%s" % (r["t"], r["via"]) for r in spliced)))
    if askip:
        print("  · 승계로 못 메운 결손 %d종(사유별 내역은 pit_strategies.json coverage.splice)"
              % len(askip))
    if bad_reuse:
        print("  ⚠ 티커 재사용 의심 %d종 제외(계열 기간이 멤버 기간과 안 겹침): %s"
              % (len(bad_reuse), ", ".join(sorted(bad_reuse))))
    if bad_scale:
        # 조용히 버리지 않는다 — 몇 배였는지까지 찍어야 «문턱이 무엇을 잘랐나» 를 볼 수 있다.
        print("  🚨 크기 검사 탈락 %d종(멤버 기간 안 최고/최저 100배 초과 — 다른 상장물로 본다): %s"
              % (len(bad_scale),
                 ", ".join("%s %.2f~%.0f(×%.0f)" % x for x in sorted(bad_scale))))
    if cut:
        _re = [c for c in cut if c[3]]
        print("  ✂ 편출 계열 꼬리 절단 %d종(멤버 종료 뒤 구간 %d거래일) · 그중 SEC 대조로 "
              "재배정 확인 %d종: %s"
              % (len(cut), sum(c[1] for c in cut), len(_re),
                 ", ".join("%s→%s" % (c[0], c[2]) for c in sorted(_re)) or "없음"))
    print("  가격 %d종 (랩 %d + 편출캐시 %d + CIK승계 %d)"
          % (len(px), n_lab, n_cache, len(spliced)))
    return px, {"n_cut": len(cut), "n_reassigned": sum(1 for c in cut if c[3]),
                "reassigned": sorted(c[0] for c in cut if c[3]),
                "n_dropped": len(bad_reuse), "dropped": sorted(bad_reuse),
                # 크기 검사 탈락 — 산출물에 남겨야 다음 감사가 «왜 이 종목이 없나» 를 안다.
                "n_bad_scale": len(bad_scale),
                "bad_scale": [{"t": x[0], "lo": round(x[1], 2), "hi": round(x[2]), "x": round(x[3])}
                              for x in sorted(bad_scale)],
                # 🚨 이은 구간은 반드시 **명시**한다. 조용히 좋아지면 다음 감사가 이 수치를
                #   원자료로 오인한다 — 여기 실린 종목의 가격은 그 티커의 계열이 아니라
                #   같은 CIK 의 승계 티커에서 온 것이다.
                # 🚨 그리고 생성기와 그 산출물은 **같은 커밋**에 넣는다. 승계를 도입한 커밋
                #   (3b524b16)은 이 파일과 validate_site·pit_fetch_report·pit_universe 만
                #   담고 data/pit_strategies.json 을 안 담았다. 그래서 코드는 승계본인데
                #   게시 산출물은 승계 이전본인 채로 하루가 갔고, 그 다음 재생성에서 t 가
                #   움직인 지배 원인은 그날의 다른 수정이 아니라 이 커밋이 이제야 반영된
                #   것이었다 — 무엇이 무엇을 움직였는지 읽을 수 없게 된다.
                #   (그때그때의 회수 종수·커버리지는 아래 reuse_rep 이 그 자리에서 말한다.
                #    여기에 숫자를 박아 두면 다음 실행에서 조용히 낡는다.)
                "cik_splice": {
                    "n": len(spliced),
                    "n_member_months": sum(r.get("n_member_months", 0) for r in spliced),
                    "map": {r["t"]: r["via"] for r in spliced},
                    "rows": spliced,
                    "n_partial": len(thin),
                    "partial": {r["t"]: r["span_ratio"] for r in thin},
                    "n_unresolved": len(askip), "unresolved": askip,
                    "note": ("같은 CIK(=같은 법인)의 다른 티커로 결손 가격을 해석한 것. 개명만 "
                             "잇고 인수는 안 잇는다 — CIK 가 다르면 후보로 삼지 않는다. "
                             "복수 클래스(같은 달 공존)와 cik_conflicts 도 제외한다."),
                }}


def load_hilo(need, dates, MEMBER_SPAN=None, which=0, alias=None):
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
    # CIK 승계 — 종가와 **같은 지도**로 고저가도 잇는다. 한쪽만 이으면 같은 종목이 규칙마다
    # 다른 이력을 갖게 되고, 그 어긋남은 예외를 안 내고 지나간다(이 파일이 세 번 겪은 유형이다).
    for t, a in (alias or {}).items():
        if t in hi or a not in hi:
            continue
        cm = cutoff_month(t, MEMBER_SPAN or {}, set())
        hi[t] = [v if (not cm or dates[j][:7] <= cm) else None for j, v in enumerate(hi[a])]
    return hi, n_lab, len(hi) - n_lab


def load_vol(need, dates, MEMBER_SPAN=None, alias=None):
    """티커 → 거래량 배열(dates 와 같은 길이). load_hilo 와 **한 글자도 다르지 않은 규약**이다.

    🚨 2026-08-14 추가. 그 전에는 편출 종목 거래량이 아예 없어서 거래량 규칙 7종
      (x-volsurge · x-amihud · x-turn · x-turnchg · x-mfi · x-adslope · x-volconc)이
      EXCLUDED_SIDS 로 빠져 있었다. 자료가 없어서가 아니라 **yf.download 응답의 Volume 열을
      안 꺼내 쓰고 있었다** — load_hilo 첫머리가 적은 것과 같은 유형이다(HL 캐시는 값을
      갖고 있었는데 배선이 없었다).
    ⚠ 꼬리 절단(cutoff_month)과 CIK 승계(alias)를 **여기서도 똑같이** 한다. 한쪽만 하면
      같은 종목이 규칙마다 다른 이력을 갖고, 그 어긋남은 예외를 안 내고 지나간다.
    ⚠ 단위는 천주 — 랩 vd 와 같다(fetch_cache 가 1000 으로 나눠 저장한다). 축이 다르면
      vol_resolved 해상도 게이트가 편출 종목에서만 다르게 물어 후보가 조용히 갈린다.
    """
    vl = {}
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
        a = json.load(io.open(fp, encoding="utf-8")).get("vd") or []
        if len(a) != len(pd_):
            continue
        arr = [None] * len(dates)
        for k, d in enumerate(pd_):
            j = pos.get(d)
            if j is not None:
                arr[j] = a[k]
        vl[t] = arr
    n_lab = len(vl)
    if os.path.exists(VOLCACHE):
        try:
            vc = json.load(io.open(VOLCACHE, encoding="utf-8"))
        except Exception:
            vc = {}
        reassigned = load_reuse()
        for t, ser in vc.items():
            if t not in need or t in vl or not ser:
                continue
            cm = cutoff_month(t, MEMBER_SPAN or {}, reassigned)
            arr = [None] * len(dates)
            for d, v in ser.items():
                if cm and d[:7] > cm:
                    continue
                j = pos.get(d)
                if j is not None:
                    arr[j] = v
            vl[t] = arr
    for t, a in (alias or {}).items():
        if t in vl or a not in vl:
            continue
        cm = cutoff_month(t, MEMBER_SPAN or {}, set())
        vl[t] = [v if (not cm or dates[j][:7] <= cm) else None for j, v in enumerate(vl[a])]
    return vl, n_lab, len(vl) - n_lab


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
        # ⚠ CIK 승계로 가격을 얻은 티커도 여기 들어온다(그래서 명단이 72 → 87종으로 늘었다).
        #   러너(build/pit_facts.py)는 index_history 의 '당시 CIK' 를 우선 조회하므로 구 티커라도
        #   같은 법인의 재무를 받는다 — 오염이 아니다. 다만 **왜 늘었는지**가 파일에 남아야
        #   다음 사람이 명단 증가를 데이터 사고로 오인하지 않는다.
        "cik_spliced": {t: a for t, a in sorted((CIK_SPLICE_MAP or {}).items()) if t in set(gone)},
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
    px_map, reuse_rep = load_prices(need, span, mem)
    ALIAS = (reuse_rep.get("cik_splice") or {}).get("map") or {}
    dump_universe(mem, span, px_map)
    if "--universe-only" in sys.argv:
        return 0

    # 거래일 격자 — 랩과 같은 격자를 쓴다(랩이 이미 yfinance 거래일로 만들어 둔 것).
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    # 🚨 2026-08-23 — 랩 본편과 **같은 설계**로 바꿨다(TB.ASOF_N 머리말). 격자는 오늘까지
    #   그대로 쓰고 **지표만** 전월말에서 자른다. 두 레그의 창은 여전히 같아야 한다 —
    #   어긋나면 그 어긋남이 곧 '생존편향' 으로 적혀 나가므로, 자르는 자리도 같은 함수다.
    dates = [d for d in st["pxd_dates"]]
    n = len(dates)
    tickers = sorted(px_map)
    px = {t: [px_map[t].get(d) for d in dates] for t in tickers}
    # 거래량 — 랩 유니버스는 data/sd, **편출 종목은 _pit_vol_cache.json**(2026-08-14 추가).
    # 🚨 종전에는 편출분이 아예 없어서 거래량 규칙 7종이 EXCLUDED 였다. 후보가 100%
    #   생존자로 좁혀지는데 대조군에는 편출 종목이 들어가 비교가 성립하지 않았기 때문이다.
    # 🚨 **load_hilo 와 같은 규약으로 잇는다.** 처음에 여기서 캐시를 그냥 읽었더니
    #   ⓐ 멤버 종료 뒤 꼬리를 안 자르고 ⓑ CIK 승계(BK→BNY · MMC→MRSH)를 안 따라가서,
    #   PIT 창 멤버-월 커버가 95.8% 에서 멈추고 그 결손 51종이 하필 **지수에서 빠진
    #   종목들**에 몰렸다(BK 58개월 · MMC 54개월 …). 결손이 편출 쪽에 몰리면 그것이
    #   바로 이 레그가 없애려던 생존편향이다. 고가·저가가 이미 푼 문제를 다시 풀지 않는다.
    # ⚠ 두 출처의 단위를 맞춘다 — 랩 vd 는 천주이고 캐시도 천주로 저장한다(fetch_cache).
    vlm, _v_lab, _v_pit = load_vol(set(px), dates, span, ALIAS)
    print("  거래량 %d종 (랩 %d + 편출캐시·승계 %d)" % (len(vlm), _v_lab, _v_pit))
    for t in tickers:
        vlm.setdefault(t, None)

    # ── 시점별 주식수(x-small 용) ──────────────────────────────────────
    # 오늘의 유니버스는 랩이 SEC XBRL 로 이미 갖고 있고(data/fx), 편출 종목만 yfinance 캐시에서.
    # ⚠ 두 출처는 정의가 미세하게 다르다(실측: yfinance 가 0.3~2.3% 낮다). 시총이 자릿수로
    #   벌어지는 횡단면이라 순위 영향은 거의 없지만, 민감도를 재서 limits 에 싣는다.
    SH = {}
    # 재무는 오늘의 유니버스(data/fx)와 편출 종목(data/fx_pit)을 함께 훑는다 — 후자가 있어야
    # 펀더멘털 규칙을 PIT 로 잴 수 있다. 없으면 그 규칙들은 후보가 생존자로만 좁혀진다.
    _FXP = os.path.join(DATA, "fx_pit")
    _fu = TB.load_fund(extra_dirs=[_FXP] if os.path.isdir(_FXP) else [])
    # CIK 승계는 **같은 법인**이므로 재무·주식수도 같은 지도로 잇는다. 가격만 이으면 그 종목은
    # 가격 규칙에서만 후보가 되고 펀더멘털 규칙에서는 여전히 생존자 쪽으로 좁혀진다 —
    # 반쪽만 이으면 두 규칙군이 서로 다른 유니버스를 보게 된다.
    _fu_spl = 0
    for _t, _a in ALIAS.items():
        if _t not in _fu and _fu.get(_a):
            _fu[_t] = _fu[_a]; _fu_spl += 1
    if _fu_spl:
        print("  🔗 재무도 CIK 승계로 %d종 연결(같은 법인)" % _fu_spl)
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
    # 규칙별 리밸 주기. me 는 멤버십 스냅샷(월별)과 i0 결정이 계속 쓰므로 그대로 둔다 —
    # 명단은 월 단위로만 있으므로 주간 리밸이라도 그 주가 속한 달의 명단을 쓴다.
    # ⚠ 그래서 주간 리밸 규칙의 PIT 레그는 **달 안에서는 같은 후보 명단**을 본다. 실제로도
    #   위키 리비전이 월 단위라 그보다 잘게 알 수 없다 — 못 하는 것을 하는 척하지 않는다.
    REB_SET = {k: set(TB.reb_index(k, dates)) for k in TB.REB_KINDS}
    # ⚠ i0 를 START 직후 아무 날로 잡으면 안 된다. 전략은 첫 월말 리밸까지 보유가 없어 수익 0인데
    #   대조군은 그날부터 만기 투자다 — 그 20거래일에 대조군이 −2.77% 빠지면서 16종 전부가
    #   공짜 초과수익을 얻는다(대조군 CAGR 도 0.76%p 낮게 잡힌다). 첫 월말에서 같이 출발시킨다.
    _s0 = next(i for i in range(n) if dates[i] >= START)
    i0 = min(i for i in me if i >= _s0)

    def members_at(i):
        # 🚨 2026-09-03 — **꼬리 이월을 여기서도 받는다(index_members.at).**
        #   종전에는 `mem.get(dates[i][:7]) or set()` 이라 지도의 마지막 키 뒤가 빈 집합이었다.
        #   그 결과 같은 파일 안에서 **비대칭**이 생겨 있었다 —
        #     · 대조군 루프(아래 `if m: cur = m`)는 빈 달에 **직전 달을 유지**해 계속 굴러가고
        #     · 전략 쪽(:1444 pool_at)은 그대로 써서 min_pool 게이트에 걸려 **무보유**가 된다.
        #   즉 새 달 첫 거래일부터 그 주 토요일까지(지도는 주 1회 갱신) 전략만 멈추고 대조군만
        #   복리로 가는데, **그 차이가 그대로 「생존편향」 칸에 적힌다.** 편향이 아니라 결손이다.
        #   ⚠ 안쪽 결손은 여전히 빈 집합이다 — 이월은 꼬리에만 건다(index_members 머리말).
        return _IM.at(mem, dates[i][:7], label="지수 멤버십")

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
    # 🚨 2026-08-29 — 여기 있던 «바스켓 승자 N 적용» 을 걷었다
    #   (PREREG-2026-08-29-ASWRITTEN.md §0 · 사용자 지시로 전수 시험 자체를 폐기).
    #   종전에는 ① `~n` 변형을 STRATS 에서 걷고 ② 랩 산출물(tech_strategies.json)의
    #   `nsel.n` 을 읽어 승자가 쓴 N 을 PIT 레그에 되먹였다. 그 되먹임이 필요했던 이유는
    #   «화면은 20종인데 PIT 은 10종을 재고, 그 차이가 생존편향으로 잘못 읽힌다» 였는데,
    #   이제 두 레그가 처음부터 같은 N(규칙의 topn 아니면 TOPN)을 든다.
    # ⚠ **이 파일이 랩 산출물을 읽어 자기 설정을 바꾸던 유일한 고리였다.** 그 고리가
    #   사라졌으므로 PIT 레그는 tech_strategies.json 의 존재에 더는 안 매인다 — 순서가
    #   뒤바뀌어 낡은 파일을 읽고 조용히 다른 N 을 재던 경로도 같이 없어졌다.
    BY = {s["sid"]: s for s in TB.STRATS}
    # 🚨 투자의견 이력을 **이 프로세스에도 올린다.** 랩 본편은 run() 안에서 load_ratings()
    #   를 부르는데(TB._RAT), 이 파일은 TB.STRATS 만 빌려 쓰고 그 초기화를 안 거친다.
    #   안 올리면 revdrift 3종은 점수가 0종이라 매달 무보유가 되고, 그 평평한 곡선이
    #   «성적» 인 척 실린다 — 「못 쟀다」와 「못했다」가 뒤바뀌는 자리다.
    if getattr(TB, "_RAT", None) is None:
        TB._RAT = TB.load_ratings()
        print("  투자의견 이력 %d종 · %d건 (부분 시점정확 레그용)"
              % (len(TB._RAT), sum(len(v[0]) for v in TB._RAT.values())))
        if not TB._RAT:
            sys.exit("투자의견 캐시(data/_ratings_cache.json)가 없다 — revdrift 3종의 부분 "
                     "시점정확 레그가 조용히 무보유로 실린다. build/fetch_ratings.py 를 먼저 돌릴 것.")
    # 🚨 완결성 관문 — 랩의 **모든 횡단면 규칙**은 셋 중 하나여야 한다:
    #     ① PRICE_SIDS 나 FUND_SIDS 에 있어 PIT 을 돈다
    #     ② EXCLUDED_SIDS 에 **사유와 함께** 있다
    #     ③ 여기서 죽는다
    #   2026-08-11 이전에는 넷째 길이 있었다 — 아무 데도 없어서 조용히 안 도는 것.
    #   그렇게 13종이 생존편향 검사를 한 번도 안 받은 채 소급 t 로만 판정되고 있었다
    #   (그중 x-hlspread 는 소급 t 5.00 이었다). 목록에 없다는 것은 아무 신호도 안 낸다 —
    #   그래서 사람이 알아챌 방법이 없었고, 그것이 이 관문이 막는 것이다.
    _listed = (set(PRICE_SIDS) | set(NEW_PRICE_SIDS) | set(FUND_SIDS) | set(NEW_FUND_SIDS)
               | set(EVENT_SIDS) | set(EXCLUDED_SIDS))
    # 🚨 2026-08-24 — 관문을 **이벤트 규칙까지** 넓혔다. 종전에는 kind=="xsec" 만 봐서
    #   새로 만든 event 규칙 6종이 이 관문 **밖**에 있었다 — 목록에 없어도 아무 신호가 안
    #   나므로, 그 여섯이 생존편향 검사를 한 번도 안 받은 채 소급 t 로만 판정될 뻔했다.
    #   이 관문이 막으려던 실패 모양 그대로이고, 관문 자체가 낡아서 놓칠 뻔한 것이다.
    _orphan = sorted(s["sid"] for s in TB.STRATS
                     if s.get("kind") in ("xsec", "event")
                     # 🚨 2026-08-25 — _BASE_SID 봐주기를 걷었다. 밑동이 목록에 있으면
                     #   변형까지 통과시켰는데, PIT 루프는 목록의 sid 만 돈다 — 그래서
                     #   밴드 12종이 «통과» 라 적힌 채 레그 없이 게시되고 있었다.
                     #   ⚠ 이 검사는 일부러 부숴서 확인했다: 밴드 하나를 목록에서 빼면
                     #     이제 죽는다(전에는 조용히 통과했다).
                     and s["sid"] not in _listed)
    # ⚠ 2026-08-29 — 여기 `and "~n" not in s["sid"]` 가 붙어 있었다. 바스켓 크기 전수 시험의
    #   변형을 이 완결성 검사에서 빼 주던 면제인데, 그 시험이 폐기돼(PREREG-2026-08-29-
    #   ASWRITTEN.md §0) 면제할 대상이 없다. **면제를 남겨 두면 언젠가 `~n` 이 든 새 sid 가
    #   조용히 검사를 빠져나간다** — 이 검사가 막으려던 바로 그 사고다.
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
    # 🚨 CIK 승계분의 섹터도 **같은 지도로** 잇는다. 가격과 재무만 잇고 섹터를 안 이으면
    #   ① 섹터로 묶는 규칙(x-indmom·x-valcomp-sn)에서 승계 종목이 통째로 빠지고
    #   ② 금융업 제외 규칙(x-fscore·x-gpa·x-ocfp·x-aci)의 `sector == 'Financials'` 가
    #      빈 메타에서 False 라 **은행·보험이 후보로 들어온다**(BK·MMC·RE 실측).
    #   이 파일이 재무 승계 주석에 적어 둔 '반쪽만 이으면 규칙군마다 다른 유니버스를 본다'가
    #   섹터에서 그대로 재발했던 자리다. 적대감사가 잡았다(2026-08-12).
    _nsec3 = 0
    for _t, _a in ALIAS.items():
        if _t not in _meta and _meta.get(_a):
            _meta[_t] = dict(_meta[_a]); _nsec3 += 1
    _amiss = sorted(t for t in ALIAS if not (_meta.get(t) or {}).get("sector"))
    print("  섹터 %d종 (랩 %d + 편출 %d + CIK승계 %d)"
          % (len(_meta), len(_meta) - _nsec2 - _nsec3, _nsec2, _nsec3))
    if _amiss:
        print("  ⚠ 승계했는데 섹터가 없는 %d종: %s (섹터 규칙에서 빠지고 금융 제외가 안 걸린다)"
              % (len(_amiss), ", ".join(_amiss)))
    X = {"FACP": TB.load_factor_proxies(dates), "FU": _fu, "R": R, "dates": dates,
         "hid": {}, "lod": {}, "ixr": ixr, "ixvol": ixvol, "me": me,
         "me_list": sorted(me), "meta": _meta, "px": px, "vlm": vlm,
         "tickers": tickers,
         # 🚨 거시 요인 일간 변화(6차 배치). **여기 안 실으면 그 규칙들이 조용히 후보 0 이 된다** —
         #   채점기는 X 에서 읽고, 없으면 빈 리스트라 macro_beta 가 늘 None 을 낸다.
         #   그러면 PIT 레그가 '돌았는데 아무것도 안 샀다'가 되어 t 가 안 나온다.
         #   전 종목이 공유하는 계열이라 편출분을 따로 받을 필요가 없다(랩과 같은 값).
         "macd10": TB.macro_daily("DGS10", dates),
         "macfx": TB.macro_daily("DTWEXBGS", dates),
         # 🚨 국면 서술형 규칙의 게이트가 쓰는 **수준** 계열. 랩 본편에만 싣고 여기 빠뜨렸다가
         #   PIT 이 죽었다(2026-08-24). 위 macd10/macfx 는 «변화» 라 게이트에 못 쓴다.
         #   ⚠ 이 셋이 없으면 _narrative_state 가 죽는다 — 조용히 «게이트 늘 꺼짐» 으로
         #     넘어가지 않게 그렇게 만들어 뒀다.
         "mac_real": TB.macro_level("DFII10", dates),
         "mac_curve": TB.macro_level("T10Y2Y", dates),
         "mac_usd": TB.macro_level("DTWEXBGS", dates),
         # 이벤트 규칙(src="me")이 진입일로 쓰는 월말 격자.
         "me_list": TB.month_ends(dates)}
    # 고가·저가 — x-52wh(고가) · x-lshock·x-ongapd(둘 다) 가 쓴다. 편출 종목분은 HLCACHE 에서
    # 온다. 🚨 종전에는 조건이 `x-52wh 가 제외 목록에 없으면` 이었다. HL 캐시가 있어도
    #   x-52wh 하나의 사정으로 저가·고가 전체가 안 실릴 수 있는 배선이었고, 그 탓에 고저가를
    #   쓰는 다른 규칙은 아예 후보에 오르지도 못했다. 파일이 있으면 싣는다 — 쓰는 쪽이 정한다.
    # 🚨 이 분기는 **침묵하면 안 된다**(적대감사 2026-08-12). 파일이 없으면 hid/lod 가 빈 채로
    #   진행하고, 고저가를 쓰는 규칙 4종(x-lshock·x-ongapd·x-hlspread·x-clv)이 5년 내내 한 주도
    #   보유하지 않은 채 'CAGR 0.00 · 초과 −9.71 · t −1.44' 라는 **측정값으로** 산출물에 실렸다
    #   (실측: 배포본은 같은 4종이 5.86·4.56·4.85·10.72 다). 커버리지는 종가 채널만 보므로
    #   ok=true 였다 — 조용한 실패의 교과서다. 이제 사유를 남기고 커버리지를 내린다.
    # 🚨 채널이 없을 때 **조용히 값이 바뀌는** 규칙도 있다. x-52wh 는 무보유가 되지 않고
    #   고가 대신 종가 최대로 채점돼 정의가 바뀐 채 계속 돈다(실측 CAGR 9.11 → 8.01, 경고 0줄).
    #   무보유 관문으로는 절대 못 잡는 유형이라 이름으로 뺀다.
    #   ⚠ 이 목록은 손으로 유지한다 — 고저가를 쓰는 규칙을 새로 만들면 여기에 적을 것.
    HL_SIDS = ("x-52wh", "x-52wh-n155",      # ← 2026-09-02 QUANTILE4. 위 머리말대로 적는다 —
                                             #   안 적으면 고가 대신 종가 최대로 조용히 채점된다.
               "x-lshock", "x-ongapd", "x-hlspread", "x-clv")
    _hl_warn = None
    if os.path.exists(HLCACHE):
        X["hid"], _nl, _nx = load_hilo(set(px), dates, span, 0, ALIAS)
        X["lod"], _nl2, _nx2 = load_hilo(set(px), dates, span, 1, ALIAS)
        print("  고가 %d종 (랩 %d + 편출캐시 %d) · 저가 %d종 (랩 %d + 편출캐시 %d)"
              % (len(X["hid"]), _nl, _nx, len(X["lod"]), _nl2, _nx2))
        if not X["hid"] or not X["lod"]:
            _hl_warn = "고저가 채널이 비어 있다(%s 는 있는데 실린 종목이 0종)" % HLCACHE
    else:
        _hl_warn = ("고저가 채널 부재 — %s 가 없다. 고저가를 쓰는 규칙은 전 구간 무보유가 되고, "
                    "그것은 '측정값 0' 이 아니라 **안 돈 것**이다(`--fetch-cache` 로 받을 것)"
                    % HLCACHE)
        print("  🚨 " + _hl_warn)
    if _hl_warn:
        for _s in HL_SIDS:
            EXCLUDED_SIDS.setdefault(
                _s, "고저가 채널 부재 — 이 규칙은 고가·저가로 채점한다. 없이 돌리면 무보유가 "
                    "되거나(x-lshock 계열) 종가 최대로 대체돼 정의가 조용히 바뀐다(x-52wh 실측 "
                    "9.11 → 8.01). 수치를 내지 않는다: `--fetch-cache` 로 %s 를 받을 것." % HLCACHE)

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

    # 🚨 결손을 **멤버-월로 가중해서** 센다. 종수로만 세면 1개월짜리와 61개월짜리가 같은
    #   무게가 된다 — 실측으로 결손 60종 중 상위 10종이 결손의 3분의 1을 차지했다.
    #   그리고 '어떻게 채워졌나'를 세 갈래로 나눈다. 못 받은 것을 한 덩어리로 두고
    #   "인수·상폐로 보인다"고 단정하던 것이 이 파일의 fail-open 이었다.
    _wym = sorted(ym for ym in mem if ym >= dates[i0][:7])
    mm_tot = mm_direct = mm_spl = 0
    mm_gap = {}
    for ym in _wym:
        for t in mem[ym]:
            mm_tot += 1
            if t in ALIAS:
                mm_spl += 1
            elif t in px:
                mm_direct += 1
            else:
                mm_gap[t] = mm_gap.get(t, 0) + 1
    mm_miss = sum(mm_gap.values())
    # 🚨 연도별 커버리지 — 2026-08-14 에 창을 10년으로 내리면서 **앞구간이 얇아졌다.**
    #   전체 한 숫자로만 내면 "96%" 처럼 보이지만 2016년은 77% 다. 구간별로 실어
    #   화면이 "앞구간은 이만큼 빠진 채로 골랐다" 를 말하게 한다.
    cov_by_year = {}
    for _mk in sorted(mem):
        if _mk < START[:7]:
            continue
        _ms = set(mem.get(_mk) or [])
        if not _ms:
            continue
        _y = _mk[:4]
        _a, _b = cov_by_year.get(_y, (0, 0))
        _have = sum(1 for _t in _ms if _t in px)
        cov_by_year[_y] = (_a + len(_ms), _b + _have)
    cov_by_year = {y: round(100.0 * h / max(1, n), 1) for y, (n, h) in cov_by_year.items()}
    if cov_by_year:
        print("  연도별 후보 커버리지 " + " · ".join(
            "%s %.0f%%" % (y, v) for y, v in sorted(cov_by_year.items())))
    COV_MIN_REQ = 0.90        # 사전등록 문턱과 같은 값 — 여기서 흔들지 않는다
    print("  멤버-월 커버리지 %.2f%% (총 %d · 직접 %d · CIK승계 %d · 결손 %d / %d종)"
          % (100 * (mm_tot - mm_miss) / max(1, mm_tot), mm_tot, mm_direct, mm_spl,
             mm_miss, len(mm_gap)))
    # 수집기 진단(build/pit_backtest.py --fetch-cache 가 남긴다) — 없으면 없다고 적는다.
    _frp = os.path.join(DATA, "pit_fetch_report.json")
    _fetch_rep = None
    if os.path.exists(_frp):
        try:
            _fr = json.load(io.open(_frp, encoding="utf-8"))
            _fetch_rep = {"as_of": _fr.get("as_of"), "n_want": _fr.get("n_want"),
                          "n_cached": _fr.get("n_cached"),
                          "batch_fail": (_fr.get("batch_fail") or {}).get("n"),
                          "missing": (_fr.get("missing") or {}).get("n"),
                          "short_threshold": (_fr.get("short_threshold") or {}).get("n"),
                          "zero_rows": len(_fr.get("zero_rows") or []),
                          "no_column": len(_fr.get("no_column") or [])}
        except Exception as _e:
            _fetch_rep = {"error": str(_e)[:80]}

    _cov_warn = []
    if _fetch_rep and _fetch_rep.get("batch_fail"):
        # 요청이 죽은 배치가 있었다면 결손 통계는 아직 확정이 아니다 — 조용히 넘기지 않는다.
        _cov_warn.append("마지막 수집에서 요청이 죽은 배치 %d종 — 결손 통계가 확정이 아니다"
                         % _fetch_rep["batch_fail"])
    if cov_min < COV_MIN_REQ:
        _cov_warn.append("월별 보유율 최저 %.1f%% < %.0f%%" % (100 * cov_min, 100 * COV_MIN_REQ))
    if mm_tot and (mm_tot - mm_miss) / mm_tot < COV_MIN_REQ:
        _cov_warn.append("멤버-월 커버리지 %.1f%% < %.0f%%"
                         % (100 * (mm_tot - mm_miss) / mm_tot, 100 * COV_MIN_REQ))
    # 커버리지는 종가 채널 밖으로도 나가야 한다 — 채널이 하나 통째로 비면 그 규칙들은
    # '나쁜 성과' 가 아니라 **안 돈 것**이고, 그 사실이 여기 안 실리면 아무 데도 안 남는다.
    if _hl_warn:
        _cov_warn.append(_hl_warn)
    if (reuse_rep.get("cik_splice") or {}).get("n_partial"):
        _cov_warn.append("부분 승계 %d종(계열이 멤버 기간의 90%% 미만을 덮는다)"
                         % reuse_rep["cik_splice"]["n_partial"])
    if _cov_warn:
        # 죽이지는 않는다 — 커버리지가 낮아도 '얼마나 낮은지'를 실은 표는 쓸모가 있다.
        # 대신 조용히 통과시키지 않는다. 로그와 limits 맨 앞에 같은 문장을 박는다.
        print("\n" + "🚨" * 12)
        print("🚨 커버리지 문턱 미달 — %s" % " · ".join(_cov_warn))
        print("🚨 이 표의 후보는 그만큼 '오늘까지 살아남은 종목' 쪽으로 좁혀져 있다. "
              "`--fetch-cache` 로 편출 가격을 더 받고 다시 돌릴 것.")
        print("🚨" * 12 + "\n")

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

    # ── 부분 시점정확(선견만 보정) 전용 대조군 ────────────────────────────
    # 🚨 이 파일이 바로 위에서 «대조군과 ixr 은 유니버스에 딸린 값이라 레그별로 따로
    #   만든다» 고 적어 놓았다. 부분 레그는 **세 번째 유니버스**(그때 편입 ∩ 오늘)를 쓰므로
    #   대조군도 세 번째가 있어야 한다. 처음에 ixr(완전 PIT 대조군)을 그대로 붙였는데,
    #   그러면 전략은 생존자만 들고 대조군은 편출까지 드는 짝이 되어 «반쪽만 소급» 이
    #   된다 — 초과수익이 전략의 생존편향만큼 공짜로 부풀어 오른다.
    #   ⚠ 이 자리는 돌리기 전에 잡았다. 잡지 못했으면 세 규칙의 초과수익이 그만큼 틀린 채로
    #     게시됐을 것이다.
    ixr_par = [None] * n
    _cur_par = (members_at(i0) & set(tickers) & _today)
    for i in range(1, n):
        if (i - 1) in me:
            _m = members_at(i - 1) & set(tickers) & _today
            if _m:
                _cur_par = _m
        _rs = [R[t][i] for t in _cur_par if R[t][i] is not None]
        ixr_par[i] = sum(_rs) / len(_rs) if _rs else 0.0
    ixvol_par = [TB.vol(ixr_par, i, 20) for i in range(n)]

    # ── 타이밍 계열 두 벌 ──────────────────────────────────────────────────
    # 🚨 2026-08-14 — 타이밍 규칙이 읽는 계열(disp·mclv·brd·ixgap)은 **유니버스에 딸린다.**
    #   그래서 레그마다 따로 만든다. 랩 본편과 **같은 함수**(TB.timing_ctx)를 쓰되
    #   PIT 은 members_at 을, 소급은 오늘 명단(lab_uni)을 준다.
    # ⚠ 둘을 한 벌로 공유하면 반쪽만 PIT 이 된다 — 이 파일이 ixr 을 레그별로 나눠 둔 것과
    #   똑같은 사유다(x-ivol·x-lowbeta·x-minvar 에서 이미 겪었다).
    # 현금 몫의 무위험 — **랩 본편과 같은 식**이다(tech_backtest 의 rfd_d).
    # ⚠ 상수 하나로 뭉개지 않는다. 10년 구간의 실제 3M 금리는 0.02~5.60% 라, 현금을 쥐는
    #   방어형 규칙이 구간 초반에 가공의 이자를 받게 된다. 랩이 이미 그 이유로 월별을 쓴다 —
    #   여기만 상수를 쓰면 그 차이가 고스란히 '생존편향' 으로 찍힌다.
    _rfd0 = (sum(rf.values()) / len(rf) / 21) if rf else 0.0
    _rfd_d = [((rf.get(d[:7]) / 21) if rf.get(d[:7]) is not None else _rfd0) for d in dates]

    _lab_set = set(lab_uni)
    _TC_PIT = TB.timing_ctx(dates, R, px, X["hid"], X["lod"], ixr, ixvol, tickers,
                            members_at=lambda i: members_at(i) & set(tickers))
    _TC_LAB = TB.timing_ctx(dates, R, px, X["hid"], X["lod"], ixr_lab, ixvol_lab,
                            tickers, members_at=lambda i: _lab_set)

    def run_timing(S, TC, IXR):
        """타이밍 규칙 한 종. **노출 계산은 랩과 같은 함수**(TB.timing_weights)다.

        ⚠ 여기서 신호를 다시 구현하지 않는다. 두 레그의 차이가 '생존편향' 이려면 신호가
          한 벌이어야 하고, 이 파일이 채점기 사본을 지운 것과 같은 규약이다.
        ⚠ 랩 본편(tech_backtest)의 수익 식을 그대로 옮긴다:
              r = e·ixr + (1−e)·rf   (e = 전날 노출 — 선견 없음)
          현금 몫에 그 시점 무위험을 주는 것까지 같다. 한쪽만 상수 rf 를 쓰면 방어형
          규칙이 레그마다 다른 이자를 받아 그 차이가 '편향' 으로 찍힌다.
        """
        w = TB.timing_weights(S, TC, i0, n)
        nav, srets, turns = [100.0], [], 0
        for i in range(i0 + 1, n):
            e = w[i - 1]
            r = e * (IXR[i] or 0.0) + (1 - e) * _rfd_d[i]
            srets.append(r)
            nav.append(nav[-1] * (1 + r))
        bnav = [100.0]
        for i in range(i0 + 1, n):
            bnav.append(bnav[-1] * (1 + (IXR[i] or 0.0)))
        turns = sum(abs(w[i] - w[i - 1]) for i in range(i0 + 1, n))
        # 타이밍은 첫날부터 '무언가를 한다'(노출 0 도 규칙의 답이다) — 보유시작 지연이 없다.
        return {"nav": nav, "bnav": bnav, "srets": srets, "turns": turns,
                "first": i0 + 1, "hold": [], "IXR": IXR,
                "expo": sum(w[i0:]) / max(1, n - i0), "w_now": w[n - 1]}

    def run(S, pool_at, IXR, IXVOL):
        """한 전략을 한 유니버스로 돌린다. pool_at 이 None 이면 제한 없음(소급)."""
        # 🚨 2026-08-11 — 이 파일이 갖고 있던 **두 번째 채점기**(score())를 지웠다.
        #   랩 본편의 xsec_score_at()/xsec_pick_at() 을 그대로 부른다. 두 레그의 차이가
        #   '생존편향' 이려면 채점도 선택도 같은 코드여야 한다. 사본이 있는 한 어긋난다 —
        #   하루에 넷을 그렇게 잡았다(x-52wh · ttm2 · 편향 문장 · x-debtiss 선견).
        #   그리고 사본으로 옮기기 어려운 2단 규칙 7종이 아예 PIT 을 못 돌고 있었다.
        XX = dict(X, ixr=IXR, ixvol=IXVOL)
        # ── 이벤트 규칙(kind="event") — 2026-08-24 ────────────────────────────
        # 🚨 랩 본편의 event_weights 를 **그대로** 부른다. 사본을 만들면 두 레그의 차이가
        #   생존편향이 아니라 구현 차이가 된다 — 이 파일이 2026-08-11 에 두 번째 채점기를
        #   지운 것과 같은 이유다.
        # ⚠ 종목마다 진입·청산일이 달라 «리밸 날 바스켓 교체» 가 없다. 회전율도 Σ|Δw| 로
        #   센다(랩 본편과 같은 눈금).
        if S.get("kind") == "event":
            XX["pool_at"] = pool_at
            _pos = TB.event_weights(S, dates, tickers, XX, i0, n, pool_at)
            nav, srets, turns = [100.0], [], 0.0
            first, prev = None, set()
            for i in range(i0 + 1, n):
                cur = set(_pos[i - 1])
                if pool_at is not None:
                    cur &= pool_at(i - 1)
                else:
                    cur &= _today
                if cur and first is None:
                    first = i
                rs = [R[t][i] for t in cur if R[t][i] is not None]
                srets.append(sum(rs) / len(rs) if rs else 0.0)
                _a = (1.0 / len(cur)) if cur else 0.0
                _b = (1.0 / len(prev)) if prev else 0.0
                turns += sum(abs((_a if t in cur else 0.0) - (_b if t in prev else 0.0))
                             for t in (cur | prev))
                nav.append(nav[-1] * (1 + srets[-1]))
                prev = cur
            bnav = [100.0]
            for i in range(i0 + 1, n):
                bnav.append(bnav[-1] * (1 + (IXR[i] or 0.0)))
            return {"nav": nav, "bnav": bnav, "srets": srets, "turns": turns,
                    "first": first, "hold": sorted(prev), "IXR": IXR}
        hold, hw, nav, srets, turns = [], None, [100.0], [], 0
        first = None                       # 실제로 무언가를 보유하기 시작한 시점
        # 🚨 규칙이 스스로 내건 리밸 주기를 그대로 쓴다(PREREG-2026-08-13-REBAL).
        #   두 레그(PIT·소급)가 **같은 주기**여야 한다 — 한쪽만 월말이면 그 차이가
        #   생존편향이 아니라 리밸 주기 차이가 되어 편향 측정이 통째로 못 쓰게 된다.
        _rebset = REB_SET[S.get("reb") or TB.REB_DEFAULT]
        for i in range(i0 + 1, n):
            if (i - 1) in _rebset:
                # 소급 레그도 **명단으로** 준다 — 종전에는 pool=None 으로 두고 채점 루프
                # 안에서 오늘 유니버스를 걸렀는데, 그러면 사전패스(x-hlspread 변동성
                # 회귀 · x-clv/x-volvol 잔차 · E30 합성 · 산업 모멘텀)는 전 종목을 보게
                # 되어 두 레그가 다른 모집단을 쓴다.
                # ⚠ 2026-08-18 — 예시가 '모멘텀 5분위'였는데 그 사전패스는 x-fip 전용이라
                #   그 규칙이 삭제되면서 함께 없어졌다. 짝인 tech_backtest.xsec_score_at
                #   머리주석의 목록과 같게 맞춘 것이다 — 두 파일이 갈리면 여기가 먼저 낡는다.
                pool = pool_at(i - 1) if pool_at else _today
                sc, ind_raw, _cr = TB.xsec_score_at(S, i, XX, pool)
                if len(sc) < TB.min_pool(S["sid"]):             # 소급 레그와 같은 커버리지 게이트
                    hold, hw = [], None
                else:
                    # 🚨 held 를 넘긴다(2026-08-25). 안 넘기면 밴드 변형이 매달 held=None
                    #   으로 들어가 **이력현상 없는 그냥 상위 N** 이 된다 — 「밴드」라 적힌
                    #   레그가 밴드가 아닌 것이라, 성적이 틀린 것보다 나쁘다.
                    new, new_w = TB.xsec_pick_at(S, i, XX, sc, ind_raw, held=hold)
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

    # 지수(S&P 500·NASDAQ 100 PR) 곡선 — 카드 그림에 '살 수 있는 대안' 으로 같이 깐다.
    # ⚠ 판정 대조군이 아니다. 판정은 위의 동일가중 PIT 지수(bench)로 한다.
    _IXPR = TB.load_index_tr(dates)

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
        # 지표는 전월말까지 · 곡선은 오늘까지(TB.ASOF_N 머리말)
        _mc = TB.mcut(d2)
        _d2M, _navM, _bnavM = d2[:_mc], nav[:_mc], bnav[:_mc]
        _sretsM = srets[:max(0, _mc - 1)]
        stt, bs = TB.ann_stats(_navM, _d2M, rf), TB.ann_stats(_bnavM, _d2M, rf)
        return {
            "metrics": stt, "bench": bs,
            "excess_cagr": round(stt.get("cagr", 0) - bs.get("cagr", 0), 2),
            "d_sharpe": round((stt.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
            "t": TB.tstat(_sretsM, raw["IXR"][i0 + 1 + k:][:max(0, _mc - 1)]),
            # ⚠ 회전율은 분모만 창에 맞춘다. 분자(turns)는 전 구간 누적이라 절단 뒤 리밸이
            #   한 번 더 있으면 그만큼 높게 나온다 — 랩 본편은 스냅샷으로 막았는데 여기는
            #   raw 가 이미 접혀 온 뒤라 못 막는다. **PIT 회전율은 판정에 안 쓰는 진단값**
            #   이라 이대로 두되, 값이 살짝 높을 수 있다는 사실을 여기 적어 둔다.
            "turnover": round(raw["turns"] / max(1, (_mc - 1) / 252), 2),
            "start": d2[0], "n_days": len(_d2M),
            # 기준일 둘 — perf_end 는 지표, px_end 는 곡선(랩 본편과 같은 이름 규약).
            "perf_end": (_d2M[-1] if _d2M else None),
            "px_end": (d2[-1] if d2 else None),
            "hold": raw["hold"],
            # 🚨 2026-08-14 — **곡선을 여기서 만든다.** 화면이 소급 레그만 그리고 있었다:
            #   카드 머리 숫자는 PIT 인데 그 밑 그림(누적수익·낙폭·연도별)은 랩 본편 소급
            #   곡선이라, 한 카드 안에서 숫자와 그림이 다른 유니버스를 말하고 있었다.
            # ⚠ 낙폭은 **줄이기 전 전체 계열에서** 재야 한다. 그래서 randomly 줄인 월말
            #   계열을 넘기지 않고 tech_backtest.curve_pack 에 일계열을 그대로 넘긴다 —
            #   랩 곡선과 같은 함수를 써야 두 그림의 눈금이 같다.
            "chart": TB.curve_pack(d2, nav, bnav, idx_rets=_IXPR, i0=i0 + k),
        }

    out = []
    # 🚨 EXCLUDED_SIDS 를 **여기서 실제로 읽는다.** 종전에는 정의만 있고 저장소 어디에서도
    #   참조되지 않는 죽은 변수였다(적대감사 실측: 참조 1건 = 정의 그 자체). 사유까지 적어 둔
    #   딕셔너리인데 아무 코드도 안 봐서, 목록에 도로 넣어도 막는 것이 없었다.
    _PRICE_SET = set(PRICE_SIDS)
    _retired = []
    _nohold = {}                 # sid → 사유. 전 구간 무보유는 '측정값' 이 아니다.
    # 🚨 타이밍 22종을 **같은 표에 넣는다**(2026-08-14). 종전에는 이 목록에 없어서
    #   "해당 없음" 으로 빠져 있었고, 그 사유가 사실이 아니었다(TIMING_SIDS 머리말).
    # 부분 시점정확 대상은 EXCLUDED 에 있어도 **돌린다**(선견만 보정 · 위 PARTIAL_PIT_SIDS 주석).
    # 🚨 부분 시점정확 대상은 **어느 목록에도 없다** — 처음부터 EXCLUDED_SIDS 에만 있었다.
    #   그래서 `not in EXCLUDED_SIDS or in PARTIAL` 만으로는 루프가 이름을 볼 일이 없다.
    #   (첫 시도가 그렇게 조용히 아무것도 안 돌았다. 없는 이름은 아무 신호도 안 낸다 —
    #    이 파일 985줄의 완결성 관문이 막으려던 바로 그 실패 모양이다.)
    for sid in [s for s in PRICE_SIDS + NEW_PRICE_SIDS + FUND_SIDS + NEW_FUND_SIDS
                + EVENT_SIDS + TIMING_SIDS + sorted(PARTIAL_PIT_SIDS)
                if s not in EXCLUDED_SIDS or s in PARTIAL_PIT_SIDS]:
        S = BY.get(sid)
        if not S:
            # 🚨 조용히 넘어가지 않는다. 랩 본편에서 은퇴한 규칙은 BY 에 없어 여기서 빠지는데,
            #   그동안 limits 는 PRICE_SIDS+FUND_SIDS 를 세어 '48종' 이라 적고 있었다.
            #   목록에 이름이 남아 있는 한 아무도 안 돈 줄 모른다.
            _retired.append(sid)
            continue
        if S.get("kind") == "timing":
            # 타이밍은 종목을 안 고른다 — 노출을 계산하고, 계열만 레그별로 다르다.
            _p = run_timing(S, _TC_PIT, ixr)         # PIT
            _b = run_timing(S, _TC_LAB, ixr_lab)     # 같은 창·소급 유니버스
        else:
            # 🚨 ML6 은 «과거 학습 행을 어느 풀로 거를 것인가» 가 레그를 가른다.
            #   ⚠ 바깥 X 에 실어야 한다. run() 이 XX = dict(X, …) 로 **복사본**을 만들므로
            #     XX 를 여기서 건드리면 이름이 없어 죽는다(실제로 NameError 로 죽었다).
            # 🚨 부분 시점정확 — 후보를 «그때 편입 ∩ 오늘 유니버스» 로 제한한다.
            #   완전 PIT(members_at)은 편출 종목까지 후보로 두는데, 이 규칙들은 그 종목의
            #   투자의견이 원천에 없어 어차피 점수가 안 난다. 그래서 «오늘 갖고 있는 종목만»
            #   으로 좁히되 **그때 지수에 있었는지는 지킨다** — 선견은 사라지고 생존은 남는다.
            _partial = sid in PARTIAL_PIT_SIDS
            _pool_fn = (lambda i, _m=members_at: _m(i) & _today) if _partial else members_at
            # 대조군도 같은 유니버스여야 한다(바로 위 ixr_par 주석).
            _IXR, _IXV = (ixr_par, ixvol_par) if _partial else (ixr, ixvol)
            X["ml_leg"], X["pool_at"] = "pit", _pool_fn
            _p = run(S, _pool_fn, _IXR, _IXV)          # PIT(부분이면 선견만 보정)
            X["ml_leg"], X["pool_at"] = "retro", None
            _b = run(S, None, ixr_lab, ixvol_lab)        # 같은 창·소급 유니버스
        # 🚨 **전 구간 무보유를 결과로 내보내지 않는다**(적대감사 2026-08-12). 한 주도 안 들면
        #   first=None → k=0 → 수익률이 전부 0 이 되고, 그것이 'CAGR 0.00 · 초과 −9.71 · t −1.44'
        #   라는 측정값으로 t_max·편향 중앙값·판정 표에 섞여 들어간다. 실제로 고저가 캐시가 없는
        #   실행에서 4종이 그 상태로 실렸다(배포본에서는 같은 규칙이 CAGR 5~11%다).
        #   '안 돈 것' 은 EXCLUDED_SIDS 와 같은 취급으로, **사유와 함께** 뺀다.
        if _p["first"] is None or _b["first"] is None:
            _leg = "PIT" if _p["first"] is None else "소급"
            _nohold[sid] = ("%s 레그가 전 구간 무보유 — 입력 채널이 비었거나 후보가 커버리지 "
                            "게이트(%d종)를 한 번도 못 넘겼다. 성과가 나쁜 것이 아니라 **안 돈 것**이라 "
                            "수치를 싣지 않는다.%s"
                            % (_leg, TB.XSEC_MIN_POOL, (" " + _hl_warn) if _hl_warn else ""))
            print("  %-24s ⚠ 전 구간 무보유 — 수치 없이 뺀다(%s)" % (S["name"][:24], _leg))
            continue
        # 두 레그를 **늦은 쪽** 보유시작에 함께 맞춘다. 각자 맞추면 창이 갈려 편향에 구간 차이가
        # 섞인다(x-season 은 두 레그가 같지만 커버리지 게이트 탓에 갈릴 수 있다).
        _k = max(max(0, (_p["first"] or (i0 + 1)) - 1 - i0),
                 max(0, (_b["first"] or (i0 + 1)) - 1 - i0))
        P_, B_ = fin(_p, _k), fin(_b, _k)
        out.append({
            "sid": sid, "name": S["name"],
            # 레그 성격 — 화면이 «완전» 과 «부분» 을 같은 말로 부르지 않게 한다
            "pit_kind": ("partial" if sid in PARTIAL_PIT_SIDS else "full"),
            # ⚠ 이 문장은 화면이 esc() 로 그릴 수 있는 자리다 — 마크다운 굵게(**)를 쓰지 않는다.
            "pit_kind_note": (("선견만 보정한 「부분 시점정확」이다 — 그때 지수에 있던 종목만 "
                               "후보로 뒀지만, 그 뒤 편출된 종목은 여전히 빠져 있다"
                               "(투자의견 원천이 생존자만 준다). 완전 시점정확이 아니다.")
                              if sid in PARTIAL_PIT_SIDS else None),
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
            # 타이밍은 '무엇을 들었나' 가 아니라 '얼마나 들었나' 가 구성이다 —
            # 랩 본편(hold_now)과 같은 모양으로 낸다. 종목 목록을 빈 채로 내보내면
            # 화면이 '보유 0종' 으로 읽어 규칙이 안 돈 것처럼 보인다.
            "holdings": ({"kind": "timing", "as_of": dates[-1],
                          "exposure_now": round(_p["w_now"] * 100, 1),
                          "note": "노출 %d%%는 그때 지수에 있던 종목 전체를 그 비율로 "
                                  "보유한다는 뜻이다. 나머지는 무위험(현금)."
                                  % round(_p["w_now"] * 100)}
                         if S.get("kind") == "timing" else
                         {"kind": "xsec", "as_of": dates[-1],
                          "n": len(P_["hold"]), "tickers": P_["hold"]}),
            # 시점정확 곡선. 소급 곡선(B_)은 싣지 않는다 — 화면에서 걷은 레그다.
            "chart": P_["chart"],
        })
        print("  %-24s CAGR 소급 %+7.2f → PIT %+7.2f (편향 %+6.2f) · 초과 %+7.2f → %+7.2f "
              "(t %5.2f → %5.2f)"
              % (S["name"][:24], B_["metrics"].get("cagr") or 0,
                 P_["metrics"].get("cagr") or 0, out[-1]["bias_cagr"],
                 B_["excess_cagr"], P_["excess_cagr"], B_["t"] or 0, P_["t"] or 0))

    if _nohold:
        # 무보유로 빠진 것은 커버리지 결함이다 — ok 를 내리고 로그에 크게 남긴다.
        _cov_warn.append("전 구간 무보유로 뺀 규칙 %d종(%s) — 입력 채널 부재"
                         % (len(_nohold), ", ".join(sorted(_nohold))))
        print("\n" + "🚨" * 12)
        print("🚨 전 구간 무보유 %d종을 표에서 뺐다: %s" % (len(_nohold), ", ".join(sorted(_nohold))))
        print("🚨 이것은 '성과 0' 이 아니라 **안 돈 것**이다. 사유는 coverage.warn 과 excluded 에 있다.")
        print("🚨" * 12 + "\n")

    # 🚨 다중검정 문턱(t_crit·t_crit_lab·t_max)을 걷었다 — 2026-08-16 사용자 지시
    #   "관문, 문턱 다 없애". 랩 본편이 임계를 안 긋기로 했으므로 이 표만 그을 이유가 없다.
    # ⚠ 규칙 수는 남긴다(n_family_lab). 그건 선이 아니라 **몇 개 중 하나인지**를 말하는
    #   표본 크기다 — 없으면 이 표의 t 하나가 몇 개를 돌려 나온 것인지 알 길이 없다.
    _NLAB = len(TB.STRATS)

    doc = {
        "n_family_lab": _NLAB,
        "note": "매월말 실제 지수 편입 종목만 후보로 두고 다시 돌린 결과. 같은 창에서 소급 "
                "유니버스(오늘 518종)로도 한 번 더 돌려 retro 에 담았고, 그 차이(bias_excess)가 "
                "유니버스 편향의 크기다 — 랩 본편(더 긴 창)과 직접 빼면 구간 차이가 섞여 편향이 "
                "아니게 된다. 채점은 종목별로 독립이라(z 표준화 없음) 후보집합이 점수를 바꾸지 "
                "않으므로, 스타일 측정에서 필요했던 '채점 모집단 좁히기' 가 여기서는 불필요하다.",
        "start": dates[i0], "as_of": dates[-1], "n_days": n - i0,
        "span_years": round((n - i0) / 252.0, 1),
        # 🚨 2026-08-18 신설 — **이 파일을 굽는 워크플로가 없다.** .github/workflows 에
        #   pit_backtest.py 를 부르는 잡이 하나도 없어서(refresh-tech.yml 은 tech 부터
        #   시작한다), 산출물은 누군가 손으로 돌려 커밋할 때만 갱신된다. 그래서 **소스를
        #   고쳐도 PIT 열은 옛 코드로 잰 값인 채 남는다** — 실제로 그날 _fscore 의 선견
        #   버그(_shift 음수 7줄)를 고쳤는데 랩 열만 바뀌고 PIT 열은 버그 판 그대로였다.
        #   그 상태가 화면에서 '생존편향이 크다'로 읽힌다(실제로는 두 열이 다른 코드다).
        #   → 코드 판을 산출물에 새긴다. tech_backtest 가 이 값이 없거나 낡으면 그 사실을
        #     limits 에 적는다. 값이 여기 있으면 캐비엇은 저절로 사라진다(손으로 지울 것이
        #     남지 않게 한다 — 손으로 지우는 캐비엇은 반드시 낡는다).
        "code_rev": CODE_REV,
        "universe": "SPX ∪ NDX · 매월말 실제 편입(위키백과 과거 리비전 · data/index_history.json) · 가격은 yfinance",
        # 🚨 커버리지는 **필수 필드**다(빈칸을 허용하지 않는다). 종수가 아니라 멤버-월로
        #   가중해서 싣고, 결손을 세 갈래로 나눈다: 직접 받은 것 · CIK 승계로 이은 것 ·
        #   끝내 못 구한 것. 못 구한 것을 한 덩어리로 두고 "인수·상폐로 보인다"고 단정하던
        #   것이 이 파일의 fail-open 이었고, 그 단정 때문에 개명을 아예 안 찾았다
        #   (실측 2026-08-12: 그 덩어리 안에 개명 15종·335멤버-월이 있었다).
        "coverage": {
            "min": round(cov_min, 4), "median": round(cov_med, 4),
            "lookback_first_month": round(cov0_look, 4),
            "threshold": COV_MIN_REQ, "ok": not _cov_warn, "warn": _cov_warn,
            # 연도별 후보 커버리지(%). 앞구간이 얇다는 사실을 화면이 그대로 적게 한다 —
            # 전체 한 숫자로 내면 2016년의 77% 가 최근의 99% 에 묻힌다.
            "by_year": cov_by_year,
            "member_months": {
                "total": mm_tot, "direct": mm_direct, "cik_spliced": mm_spl,
                "missing": mm_miss,
                "covered_ratio": round((mm_tot - mm_miss) / max(1, mm_tot), 4),
                "spliced_ratio": round(mm_spl / max(1, mm_tot), 4),
                "missing_ratio": round(mm_miss / max(1, mm_tot), 4),
            },
            "missing_tickers": [{"t": t, "n_member_months": v, "first": span[t][0],
                                 "last": span[t][1]}
                                for t, v in sorted(mm_gap.items(), key=lambda kv: (-kv[1], kv[0]))],
            "splice": reuse_rep.get("cik_splice"),
            # 수집기가 남긴 진단(있으면). 캐시는 gitignore 라 러너에 없지만 이 요약은 커밋된다 —
            # '왜 이 종목이 없나' 를 다음 사람이 처음부터 다시 재지 않게.
            "fetch_report": _fetch_rep,
            # ⚠ n_gone 은 '가격이 있는' 편출뿐이고 n_gone_union 은 가격 유무를 안 따진
            #   편출 전체다. 둘을 섞어 적었다가 창을 바꾸자 문장이 거짓이 된 적이 있다.
            "fund_gone": {"n_gone": len(_gone), "n_with_fund": len(_fx_gone),
                          "ratio": round(fx_cov, 4), "n_gone_union": len(_gone_all)},
        },
        # 티커 재사용 방어가 실제로 무엇을 했는지 — 숫자로 남긴다. 방어를 넣고 아무것도
        # 안 걸리는 것과 16종을 잘라 낸 것은 다른 이야기이고, 화면이 그것을 인용할 수 있어야 한다.
        "reuse_guard": reuse_rep,
        # 🚨 PIT 을 **안 도는** 규칙과 그 사유. 화면이 빈칸 대신 사유를 말할 수 있어야 한다 —
        #   빈칸은 '해당 없음' 과 '아직 안 쟀다' 와 '못 잰다' 를 구별하지 못하고, 그 셋을
        #   구별 못 한 탓에 13종이 검사를 안 받은 채 소급 t 로만 판정되고 있었다(2026-08-11).
        # ⚠ 여기에는 사전에 사유를 적어 뺀 것(EXCLUDED_SIDS)과 **돌려 보니 전 구간 무보유라**
        #   뺀 것이 함께 들어간다. 뒤쪽은 종전에 0 으로 채워진 측정값으로 실리던 자리다.
        # 🚨 부분 시점정확으로 «잰» 규칙은 excluded 에서 뺀다. 안 빼면 카드가 숫자를 띄우면서
        #   동시에 «못 쟀다» 는 줄도 그린다 — 한 카드가 두 말을 하게 된다.
        "excluded": dict({k: v for k, v in EXCLUDED_SIDS.items()
                          if k not in {r["sid"] for r in out}}, **_nohold),
        "excluded_nohold": dict(_nohold),
        # 🚨 2026-08-14 — 이 칸은 두 번 고쳤다. 기록을 남긴다.
        #   ① 종전 문구: "타이밍·오버레이 규칙은 지수·ETF 를 매매하므로 '그때 지수에 있던
        #      종목' 이라는 개념 자체가 없다. 생존편향이 걸리는 자리가 아니라서 안 재는
        #      것이고, 못 재는 것이 아니다." — **거짓이었다.** 타이밍이 매매하는 것은 ixr,
        #      곧 동일가중 바스켓이고 그것은 실제 동일가중 S&P 500 보다 연 +6.58%p 앞선다.
        #   ② 그래서 "아직 안 쟀다" 로 고쳤다가, 같은 날 **실제로 쟀다**(TIMING_SIDS).
        #      랩의 timing_ctx·timing_weights 를 그대로 부르므로 신호는 한 벌이고,
        #      레그 차이는 계열을 만든 유니버스뿐이다.
        # ⚠ 이 칸을 지우지 않고 남긴다 — 화면·문서가 아직 이 키를 읽을 수 있고, 무엇보다
        #   "해당 없음" 이라고 적혀 있던 기간이 있었다는 사실 자체가 기록할 값어치가 있다.
        "na_timing": ("타이밍 22종도 시점정확으로 잰다(2026-08-14부터). 그전에는 이 칸에 "
                      "'지수·ETF 를 매매하므로 생존편향이 걸리는 자리가 아니다' 라고 적혀 "
                      "있었는데 사실이 아니었다 — 타이밍이 매매하는 것은 동일가중 바스켓이고 "
                      "그것은 실제 동일가중 S&P 500 보다 연 +6.58%p 앞선다. 신호 계산은 랩 "
                      "본편과 같은 함수(timing_ctx·timing_weights)를 쓰고, 두 레그의 차이는 "
                      "그 계열을 만든 유니버스뿐이다."),
        "limits": ([
            "🚨 커버리지 문턱(%.0f%%) 미달: %s. 이 표의 후보는 그만큼 '오늘까지 살아남은 종목' "
            "쪽으로 좁혀져 있고, 그 방향은 초과수익을 **키우는** 쪽이다. 수치를 인용하기 전에 "
            "편출 가격 캐시를 다시 받을 것(--fetch-cache)."
            % (100 * COV_MIN_REQ, " · ".join(_cov_warn)),
        ] if _cov_warn else []) + ([
            # 🚨 버린 계열을 화면이 말하게 한다. 잰 것을 산출물에만 넣고 화면에 안 이으면
            #   이 저장소의 되풀이 결함 1번(수집만 하고 안 배선)이 그대로 된다.
            "🚨 편출 가격 캐시에서 %d종을 **다른 상장물로 보고 버렸다** — %s. 멤버 기간 안에서 "
            "최고/최저가 100배를 넘는 계열이라 그 티커의 주가일 수 없다. 실측 사례: PARA 는 "
            "2021~2023 내내 10만 달러 근처에 있다가 1달러대로 끝나는데, 그대로 두면 2024년 "
            "12개월 수익률이 −98%% 로 계산돼 되돌림 계열 규칙이 «싼 종목» 으로 집는다. "
            "⚠ 버린 만큼 그 달의 후보가 줄어든다 — 커버리지 수치에 이미 반영돼 있다."
            % (reuse_rep["n_bad_scale"], " · ".join("%s(×%d)" % (x["t"], x["x"])
                                              for x in reuse_rep["bad_scale"])),
        ] if reuse_rep.get("n_bad_scale") else []) + [
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
            "🚨 결손을 한 덩어리로 두지 않는다 — 종전에는 못 받은 것을 전부 '인수·상폐로 보인다'고 "
            "단정했고(fail-open), 그 단정 때문에 **개명**을 5년 동안 안 찾았다. 멤버-월 %d 중 "
            "직접 %d · CIK 승계 %d · 끝내 결손 %d(%.2f%%)다. 승계는 %d종 — 같은 CIK(=같은 법인)의 "
            "다른 티커에 이력이 온전해 그것으로 해석했고, 그 구간 가격은 그 티커가 아니라 승계 "
            "티커에서 온 것이다(명단은 coverage.splice.map). ⚠ CIK 가 다르면 잇지 않았다 — "
            "다른 CIK 는 인수이고(DRE≠PLD · INFO≠SPGI · WRK≠SW), 피인수 주주는 프리미엄을 받고 "
            "나갔으므로 인수기업 가격을 얹으면 없는 가격을 지어내는 것이다. 같은 달에 함께 멤버인 "
            "복수 클래스(GOOGL/GOOG)도 잇지 않는다. 남은 결손 %d종은 실제 소멸이거나 승계 티커에도 "
            "가격이 없는 것이고 사유는 coverage.splice.unresolved 에 종목별로 적었다."
            % (100 * cov_min, 100 * cov_med, mm_tot, mm_direct, mm_spl, mm_miss,
               100 * mm_miss / max(1, mm_tot), len(ALIAS), len(mm_gap)),
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
            # 🚨 문턱 문장을 걷었다(2026-08-16 "관문, 문턱 다 없애"). 종전에는 여기서
            #   "|t|≥3.74 가 필요하고 그것을 넘는 규칙은 N종" 이라고 적었다.
            # ⚠ 다중검정이라는 **사실 자체**는 남긴다. 선을 안 긋는 것과 여러 개를 돌렸다는
            #   사실을 숨기는 것은 다르다 — 후자는 거짓이 된다.
            "t 는 이 표본(%d거래일)에서 계산한 값이다. 이 랩은 같은 자료로 규칙 %d종을 "
            "돌렸으므로 그중 최고는 우연히도 좋아 보인다 — t 하나만 떼어 읽으면 안 된다. "
            "이 표는 넘고 말고를 가르지 않는다. '소급 대비 t 가 얼마나 무너지는가' 로 "
            "읽는 것이 이 표를 만든 이유다."
            % (n - i0, _NLAB),
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
    # 🚨 경고를 **기계가 읽게** 한다. 종전에는 커버리지 미달이 콘솔과 접힌 <details> 에서
    #   끝나서, 사람이 로그를 안 보면 아무 일도 없었던 것이 된다(적대감사 2026-08-12).
    #   산출물은 그대로 쓴다 — '얼마나 낮은지' 를 실은 표는 쓸모가 있다 — 대신 종료코드로
    #   드러낸다. 이 스크립트는 사람이 손으로 돌리는 것이라 잡을 파이프라인을 안 깨뜨린다.
    #   (build/validate_site.py 도 커밋된 산출물의 coverage.ok 를 본다.)
    if _cov_warn:
        print("🚨 종료코드 2 — 커버리지 경고가 있다: %s" % " · ".join(_cov_warn))
        return 2
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
    아직 상장돼 있어 대부분 받아진다.

    🚨 못 받은 것을 "인수·상폐로 보인다"고 **단정하지 않는다**(2026-08-12). 종전 마지막 줄이
      그 단정이었고, 그 안에 개명이 섞여 있어 승계 티커를 시도조차 안 하게 만들었다. 지금은
      받음 / CIK 승계로 해결 가능 / 진짜 못 받음 으로 나눠 종수와 **멤버-월**을 함께 찍는다.
      200봉 문턱과 '열이 아예 안 온 종목'도 따로 드러낸다 — 둘 다 조용히 버려지던 자리다.

    ⚠ 이 함수는 오늘의 유니버스(data/sd)에 없는 멤버만 받는데, 그 명단은 **가장 최근 달의
      편출까지** 포함해야 한다. 지수에서 방금 빠진 종목은 data/sd 에서도 지워지므로,
      --fetch-cache 를 다시 안 돌리면 '오늘의 유니버스에도 없고 캐시에도 없는' 사각지대로
      떨어진다(실측: EA 는 2026-07 까지 멤버였는데 캐시에 없었다). 멤버십을 갱신하면
      이것도 같이 돌릴 것.
    """
    import datetime as _dt
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
    # 🚨 SEC 호출(write_reuse)은 사내 PC 화이트리스트 밖이라 **기본으로 건너뛴다**(2026-08-12).
    #   판정은 저장소에 커밋된 data/pit_reuse.json(러너 산출물)을 그대로 쓴다.
    #   ⚠ 건너뛴 것을 조용히 '재배정 아님' 으로 취급하면 이 파일이 막으려는 사고가 그대로 난다 —
    #     판정이 **없는** 티커를 반드시 찍는다. 갱신은 러너에서 돌거나 PIT_SEC=1 로 켠다.
    if os.environ.get("PIT_SEC") == "1":
        write_reuse(want, span)
    else:
        _ru = json.load(io.open(REUSE, encoding="utf-8")) if os.path.exists(REUSE) else {}
        _known = set()
        for _k in ("reassigned", "unknown", "match"):
            _v = _ru.get(_k)
            _known |= set(_v.keys() if isinstance(_v, dict) else (_v or []))
        _nov = sorted(t for t in want if t not in _known)
        print("  SEC 재사용 판정: 건너뜀(PIT_SEC=1 로 켠다) — 기존 pit_reuse.json(as_of %s) 사용"
              % _ru.get("as_of", "?"))
        if _nov:
            print("  ⚠ 재사용 판정이 없는 %d종 — 이 종목은 티커 재배정 검사를 못 받았다: %s"
                  % (len(_nov), ", ".join(_nov[:12]) + (" …" if len(_nov) > 12 else "")))
    out = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    hlout = json.load(io.open(HLCACHE, encoding="utf-8")) if os.path.exists(HLCACHE) else {}
    vlout = json.load(io.open(VOLCACHE, encoding="utf-8")) if os.path.exists(VOLCACHE) else {}
    # 🚨 --rebuild 가 필요한 이유. 아래 루프는 '이미 있는 티커는 건너뛴다'가 기본이고
    #   저장도 setdefault 다 — 재수집 시점이 달라 값이 미세하게 흔들리면 그 위에서 잰 PIT
    #   수치가 조용히 바뀌기 때문이다. 그런데 그 보호가 **창을 앞으로 늘릴 때는 정반대로
    #   작동한다** — 캐시가 2015-01 에서 시작하는 채로 영원히 굳는다. 창을 바꾸는 실행에서만
    #   깃발로 푼다. 값이 바뀐다는 것을 알고 하는 것과 모르고 굳는 것은 다르다.
    rebuild = "--rebuild" in sys.argv
    if rebuild:
        print("  --rebuild: 기존 %d종을 %s 부터 다시 받는다(값이 바뀐다)" % (len(out), CACHE_START))
    got = 0
    # 🚨 조용한 탈락을 드러낸다. 아래 두 자리에서 종목이 말없이 사라진다:
    #   ① yfinance 가 그 티커 열을 아예 안 준다(스로틀링일 수도, 상폐일 수도 있다)
    #   ② 열은 왔는데 `len(ser) > 200` 문턱에 걸린다 — 갓 상장·거의 안 거래된 계열
    #   종전에는 둘 다 '못 받은 N종' 한 덩어리로 뭉쳐졌고, 그 N 을 다시 "인수·상폐로 보인다"고
    #   단정했다. 세 가지가 한 문장에 뭉쳐 있으면 어느 것도 고칠 수 없다.
    short, empty, batch_fail = {}, [], {}
    for i in range(0, len(want), 25):
        # 🚨 2026-08-05 — 종전에는 `t not in out`(종가 캐시)만 봤다. 그래서 고가·저가를
        #   같은 배치에 얹었더니 **이미 종가가 있는 147종은 아예 안 받아** HL 캐시가 0종으로
        #   남았다(실행은 성공으로 끝났다 — 전형적인 '조용한 미수집'이다).
        #   둘 중 하나라도 없으면 받는다.
        # 🚨 2026-08-14 — 거래량 캐시를 더하면서 **같은 자리에 vlout 도 넣는다.** 안 넣으면
        #   이미 종가·고저가가 있는 종목은 배치에서 통째로 빠져 거래량 캐시가 0종으로 남고,
        #   실행은 성공으로 끝난다 — 08-05 에 HL 이 겪은 그 '조용한 미수집'이 그대로 재현된다.
        #   조건을 세 벌로 늘리는 것이 이 주석이 경계하던 바로 그 일의 유일한 예방이다.
        ch = want[i:i + 25] if rebuild else [t for t in want[i:i + 25]
                                             if t not in out or t not in hlout
                                             or t not in vlout]
        if not ch:
            continue
        try:
            _raw = yf.download(ch, start=CACHE_START, auto_adjust=True, progress=False,
                               threads=False)
            d = _raw["Close"]
            _hi, _lo = _raw.get("High"), _raw.get("Low")
            _vo = _raw.get("Volume")
        except Exception as e:
            # 🚨 여기서 `continue` 만 하면 그 배치의 티커가 아무 버킷에도 안 들어가고, 아래
            #   분류에서 **'진짜 결손'** 으로 보고된다(스로틀링 전량 실패 실측: '결손 116종/
            #   3301멤버-월 — 승계로도 못 메운다' + 종료코드 0). 방금 없앤 fail-open 과 같은
            #   모양이라 같은 자리에서 막는다 — 고칠 수 있는 것(재시도)과 못 고치는 것(소멸)을
            #   한 덩어리로 두지 않는다.
            print("  [yf] 배치 실패:", str(e)[:60])
            for _t in ch:
                batch_fail[_t] = str(e)[:80]
            continue
        # ⚠ 배치가 정확히 1종이면 yfinance 는 열이 없는 **Series** 를 준다. 그대로 두면
        #   `t not in d` 가 날짜 인덱스 검사가 되어 그 종목이 '열 자체를 안 준' 것으로
        #   잘못 보고된다(동작은 종전과 같지만 사유가 거짓이 된다).
        if len(ch) == 1 and getattr(d, "ndim", 2) == 1:
            d = {ch[0]: d}
            if _hi is not None and getattr(_hi, "ndim", 2) == 1:
                _hi = {ch[0]: _hi}
            if _lo is not None and getattr(_lo, "ndim", 2) == 1:
                _lo = {ch[0]: _lo}
            if _vo is not None and getattr(_vo, "ndim", 2) == 1:
                _vo = {ch[0]: _vo}
        for t in ch:
            if t not in d:
                empty.append(t)
            else:
                ser = d[t].dropna()
                if len(ser) <= 200:
                    short[t] = len(ser)
                else:
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
                    # 거래량 — 랩의 vd 와 같은 **천주** 단위로 맞춘다(랩은 2026-08-04 에
                    # 백만주 정수에서 천주로 고쳤다. 두 축이 다르면 vol_resolved 해상도
                    # 게이트가 편출 종목에서만 다르게 물어 후보가 조용히 갈린다).
                    if _vo is not None and t in _vo:
                        _v = _vo[t].dropna()
                        vlout[t] = {str(k.date()): round(float(_v[k]) / 1000.0, 3)
                                    for k in ser.index if k in _v.index and _v[k] > 0}
                    got += 1
        time.sleep(2)
    json.dump(out, io.open(CACHE, "w", encoding="utf-8"), separators=(",", ":"))

    # ── 못 받은 것을 **분류한다** (종전에는 "인수·상폐로 보인다" 한 줄이었다) ──────────
    # 🚨 그 한 줄이 이 파일의 fail-open 이었다. 못 받은 것을 전부 소멸로 단정하니
    #   ⓐ 개명(같은 CIK 의 다른 티커에 이력이 온전하다) ⓑ 스로틀링·빈 응답 ⓒ 200봉 문턱
    #   ⓓ 진짜 소멸 이 한 덩어리가 되어, 고칠 수 있는 것과 없는 것이 구별되지 않았다.
    #   실측으로 그 덩어리 안에 개명이 여럿 있었고 랩은 승계 티커를 시도한 적조차 없었다.
    _mm = {}                                    # 티커 → 창 안 멤버-월(결손을 가중해서 센다)
    for _ym, _lst in mem.items():
        for _t in _lst:
            _mm[_t] = _mm.get(_t, 0) + 1
    miss = [t for t in want if t not in out]
    _alias, _rows, _skip = cik_aliases(miss, set(out) | lab, out, span,
                                       tried=set(want) - set(batch_fail))
    _mmw = lambda ts: sum(_mm.get(t, 0) for t in ts)          # noqa: E731
    _bf = [t for t in miss if t in batch_fail]
    real = [t for t in miss if t not in _alias and t not in batch_fail]
    print("→ %s · %d종 (이번에 %d종 추가)" % (CACHE, len(out), got))
    print("  받음  %4d종 / %5d멤버-월" % (len(want) - len(miss), _mmw(set(want) - set(miss))))
    print("  승계  %4d종 / %5d멤버-월 — 같은 CIK 의 다른 티커로 해석 가능: %s"
          % (len(_alias), _mmw(_alias),
             ", ".join("%s→%s" % (k, v) for k, v in sorted(_alias.items())) or "없음"))
    if _bf:
        print("  요청실패 %4d종 / %5d멤버-월 — **배치가 죽어 시도 자체가 안 끝났다**(스로틀링 등). "
              "결손이 아니다 · 다시 돌리면 메워질 수 있다: %s"
              % (len(_bf), _mmw(_bf), ", ".join(sorted(_bf)[:20])))
    print("  결손  %4d종 / %5d멤버-월 — 승계로도 못 메운다(요청실패 제외 · 상위: %s)"
          % (len(real), _mmw(real),
             ", ".join("%s(%d개월)" % (t, _mm.get(t, 0))
                       for t in sorted(real, key=lambda x: -_mm.get(x, 0))[:10]) or "없음"))
    # 🚨 0봉과 '짧아서 버림'을 **가르지 않으면 안 된다**. yfinance 는 실패한 티커도 열은
    #   주고 전부 NaN 을 채운다 — 그래서 응답이 아예 없는 것까지 200봉 문턱 탓으로 보인다.
    #   실측(2026-08-12): 54종이 문턱에 걸린 것처럼 보였지만 53종은 0봉(응답 없음)이고
    #   문턱이 실제로 버린 것은 SATS 1종(1봉)뿐이었다.
    _zero = sorted(t for t, v in short.items() if t not in out and not v)
    _sh_new = {t: v for t, v in short.items() if t not in out and v}
    if _sh_new:
        # 이 문턱은 조용히 버린다 — 몇 종이 걸렸는지 반드시 남긴다.
        print("  ⚠ 200봉 문턱(`len(ser) > 200`)이 실제로 버린 %d종: %s"
              % (len(_sh_new), ", ".join("%s(%d봉)" % (t, v) for t, v in sorted(_sh_new.items()))))
    if _zero:
        print("  ⚠ 응답 0봉 %d종(열은 왔는데 전부 NaN — 상폐일 수도, 스로틀링일 수도 있다. "
              "⚠ 원인 모른 채 재실행하면 스로틀링을 키운다): %s" % (len(_zero), ", ".join(_zero)))
    _em_new = sorted(t for t in set(empty) if t not in out)
    if _em_new:
        print("  ⚠ yfinance 가 열 자체를 안 준 %d종(상폐일 수도, 스로틀링일 수도 있다 — "
              "⚠ 원인 모른 채 재실행하면 스로틀링을 키운다): %s"
              % (len(_em_new), ", ".join(_em_new[:20])))
    if hlout:
        json.dump(hlout, io.open(HLCACHE, "w", encoding="utf-8"), separators=(",", ":"))
        print("→ %s · %d종 — 이 파일이 있어야 고가·저가 규칙(x-52wh 등)의 PIT 레그가 돈다"
              % (HLCACHE, len(hlout)))
    if vlout:
        json.dump(vlout, io.open(VOLCACHE, "w", encoding="utf-8"), separators=(",", ":"))
        print("→ %s · %d종 — 이 파일이 있어야 거래량 규칙 7종의 PIT 레그가 돈다"
              % (VOLCACHE, len(vlout)))

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

    # 🚨 진단을 **파일로 남긴다**. 종전에는 위의 분류가 전부 print 뿐이라 콘솔을 닫으면
    #   사라졌고, 다음 감사는 '왜 이 종목이 없나' 를 처음부터 다시 재야 했다. 캐시(gitignore)와
    #   달리 이 파일은 작아서 커밋된다 — 러너와 다음 사람이 같은 것을 본다.
    rep = {
        "as_of": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "start": START, "cache_start": CACHE_START,
        "n_want": len(want), "n_cached": len(out), "n_new": got,
        "batch_fail": {"n": len(_bf), "tickers": sorted(_bf),
                       "note": "배치 요청이 죽어 시도가 안 끝난 것 — 결손이 아니다. 다시 돌릴 것."},
        "splice": {"n": len(_alias), "map": _alias},
        "missing": {"n": len(real), "member_months": _mmw(real),
                    "top": sorted(real, key=lambda x: -_mm.get(x, 0))[:20]},
        "short_threshold": {"n": len(_sh_new), "rule": "len(ser) > 200", "tickers": _sh_new},
        "zero_rows": _zero, "no_column": _em_new,
        "skip_reasons": _skip,
    }
    json.dump(rep, io.open(os.path.join(DATA, "pit_fetch_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("→ %s" % os.path.join(DATA, "pit_fetch_report.json"))
    if _bf:
        # 종료코드로 드러낸다 — 전량 쓰로틀 실패가 exit 0 으로 끝나면 '결손' 으로 굳는다.
        print("🚨 종료코드 3 — 요청이 죽은 배치가 있다(%d종). 결손 통계를 인용하기 전에 다시 받을 것."
              % len(_bf))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(fetch_cache() if "--fetch-cache" in sys.argv else main())
