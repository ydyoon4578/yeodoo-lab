# -*- coding: utf-8 -*-
"""build/style_pit.py — 스타일 백테스트의 **유니버스 편향 크기를 실제로 잰다** → data/style_pit.json

## 🚨 이름부터 — '생존편향' 하나로 부르면 안 된다

채널이 둘이고 **스타일마다 지배 채널이 다르다**. 하나의 이름으로 부르면 원인을 잘못 짚는다
(적대감사가 잡은 결함). 실측 요약(2026-07-29 기준, 채점 모집단까지 좁힌 값):
    선견 지배 … 고베타 86.3%p · 모멘텀 68.5%p · 성장 26.2%p
    생존 지배 … 가치 9.5%p
    무영향   … 저변동 0 · 퀄리티 −0.1
⚠ 크기는 점추정으로 읽지 말 것. 구간이 12개월뿐이라 상위 2달이 총편향의 34~53% 를 차지한다
  (가치 42%). 방향은 견고하지만 크기는 표본오차와 섞여 있다 — |채널| 2%p 미만은 잡음이다.

## 퀄리티·저변동의 0 은 측정 실패가 아니라 **스크린 성질**이다(2026-07-30 규명)

0 을 보고 '마스크가 안 걸렸나' 의심할 사람을 위해 남긴다. 퀄리티는 실측으로 이렇다.
  · 12개 월말 중 상위10 **명단(집합)이 실제로 바뀐 달은 1개**뿐이다(2025-07-31 MCO→ADBE
    한 자리). 나머지 5개월의 '차이' 는 순서뿐이고 동일가중이라 수익률에 영향이 0 이다.
    그 한 자리가 −0.09%p 전부다(그래서 concentration 이 100% 로 나온다 = 사실상 한 달).
  · 유니버스 변동은 **양쪽 끝**에서 일어나고 퀄리티는 그 양쪽 끝을 구조적으로 배제한다.
      ① 채점 관문 — 이익변동성 축이 EPS yoy 8쌍(≈3년치 분기 EPS)을 요구한다. 신규편입
         30종 중 14종은 **채점 자체가 안 된다**(CRWV·CVNA·NBIS·SNDK·SPCX·HONA·FDXF·Q·PSKY
         등 신규상장·분사라 분기 EPS 가 0~7개). '많이 올라서 새로 편입된 종목' 은 정의상
         이력이 짧다 — 모멘텀·고베타가 가격만으로 채점되는 것과 결정적으로 다르다.
      ② 순위 — 채점돼도 후보 약 325종 중 10위 문턱을 못 넘는다. 신규편입 최고 FIX 20위·
         EME 30위, 편출 최고 POOL 25위. 3축 백분위로 보면 이유가 보인다: HOOD 이익변동성
         11%ile · RKLB ROE 0%ile(적자) · CZR 저D/E 12%ile · KMX 이익변동성 5%ile ·
         CAG·CPB·EMN 은 40~50%ile 로 평범해서 못 든다.
  · 실제로 뽑히는 것은 창 내내 멤버였던 대형 우량주(NVDA·AAPL·KLAC·MA·IDXX·LII·LRCX·
    FTNT·SPG·HD·TSCO)다. 저변동도 같은 성질이다(EVRG·WEC·DUK·ATO·CMS·KO 류 전 기간 멤버).
  → 즉 퀄리티·저변동의 편향 0 은 '유니버스 소급이 이 스크린의 선택을 바꾸지 못한다' 는
    **결과**이고, 스크린이 무엇을 고르는지에서 예측되는 바다.

  선견(lookahead)   … 그때 지수에 없던 종목을 미리 고른 것. **이쪽이 거의 전부다.**
                       오늘 518종 중 30종은 창 시작 시점에 아직 비멤버였다. 지수는 많이 오른
                       종목을 편입하므로, 소급 유니버스는 '오를 것'을 미리 아는 셈이 된다.
  생존(survivorship) … 그때 멤버였는데 뒤에 빠진 종목이 후보에 없던 것. 창 시작 멤버 517종 중
                       29종이 오늘 유니버스에 없다. 기여는 작다.

## 무엇을 어떻게 재나

같은 backtest() 코드에 pool_of 만 갈아 끼워 **하나의 패널에서** 네 번 돌린다.

  published … 주입 전 518 패널·마스크 없음 = 지금 화면에 나가는 수치. **앵커 전용**
  base      … 주입 후 패널·오늘 518종으로만 제한 = 편향의 기준선
  mask      … 주입 후 패널·선정 시점 멤버 ∩ 오늘  → base 대비 차이가 **선견**
  pit       … 주입 후 패널·선정 시점 멤버 전부    → mask 대비 차이가 **생존**

🚨 base 를 따로 두는 이유(적대감사가 잡은 결함). 처음엔 published 를 기준선으로 썼는데,
  published 는 518 패널이고 pit 은 538 패널이다. sc_mom 은 zs() 로 표준화하므로 모집단이
  바뀌면 평균·표준편차·윈저 경계가 같이 움직여 **마스크를 걸지 않아도** 순위가 달라진다 —
  실측 5.56%p 가 편향이 아니라 하니스 산물이었다(538 패널 무마스크 131.75 vs 518 패널 137.31).
  sc_lowvol·sc_hbeta 는 zs 를 쓰지 않아 이 효과가 정확히 0 이라 모멘텀에만 생겼고 눈에 안 띈다.
  그 크기는 channel.harness_zpop 으로 계속 낸다 — 숨기지 않고 세어 둔다.

## 여섯 스타일 전부 잰다 — 채널이 스타일마다 다르다

처음엔 셋(모멘텀·저변동·고베타)만 됐다. 편출 종목의 재무가 0건이었기 때문이다. 그래서
build/pit_facts.py 로 SEC 재무를 받아(러너) data/fx_pit/ 에 넣고 여섯 전부로 늘렸다.
그러고 나서야 보인 것이 있다 — **가치는 유일하게 생존편향이 지배한다.**
편출 종목(CAG·CPB·EMN·MHK·LKQ 류)은 전형적인 값싼 주식이고 지수에서 빠진 이유가 부진이다.
가치 스크린은 그들을 골랐어야 했는데 후보에 없었다. 재무를 받기 전에는 이 11%p 가 안 보였다.
반대로 성장·고베타·모멘텀은 사후편입 선견이 지배한다. 하나의 이름으로 부르면 둘 다 놓친다.

⚠ 뒤 셋의 채점 커버리지는 완전하지 않다. 편출 20종 중 채점되는 것이 퀄리티 13 · 가치 17 ·
  성장 20 이다(AZN·GFS 는 sh 결손, LKQ·LW·MTCH 는 liab 결손 — 외국 신고인·태그 차이).
  퀄리티·가치의 생존 채널은 그만큼 과소측정 쪽이다. 실행 로그가 이 수를 매번 찍는다.

## 남은 불확실성 — '하한'이라고 단정하지 않는다

창 편출 32티커 중 가격이 있는 것은 20개다. 없는 12개 중
  · 5개는 **티커 개명**이다(BK→BNY · MMC→MRSH · FI→FISV · PARA→PSKY · SATS→ECHO).
    회사가 살아 있고 후임 티커 가격이 이미 패널에 있다. 후임을 전임 멤버기간의 후보로
    인정해 재실행해 봤더니 세 스타일 모두 **0.00%p** 변화였다(상위 10에 못 든다).
    그래서 코드에 짝을 넣지 않았다 — 값어치가 없고, 손으로 적은 짝은 틀릴 위험만 남는다.
  · SOLS 는 2025-10 상장으로 이력이 짧아 sc_mom(주간 100개)·_vol_beta(252중 200일) 어디서도
    **채점 자체가 안 된다**. 가격이 있어도 결과가 안 바뀐다.
  · 남는 6개(CTRA·DAY·HOLX·IPG·K·WBA)가 실효 미검증분이다. 대부분 인수·비상장화 편출이라
    '누락 = 못 살아남은 쪽'이라는 근거가 이 표본에는 그대로 적용되지 않는다 — 방향을 단정하지
    않는다. 다만 **저변동은 과소측정 쪽이 유력하다**: 딜가에 고정된 저변동 종목은 상위 10
    문턱(실현변동성 16~18%) 아래라 들어갔을 것이고, 그 수익은 전략 +15% 보다 낮다.

## 다른 한계

· 상장폐지 처리 — 보유 중 가격이 끊기면 그 종목은 그날부터 수익 계산에서 빠지고 남은 종목이
  비중을 나눠 갖는다(=마지막 종가에 빠져나온 것으로 본다). 파산 손실은 그만큼 덜 잡힌다.
· 멤버십은 SPX∪NDX 합집합이고 월 해상도다. 스냅샷은 그 달의 위키 리비전이므로
  월말 선정과 시점이 맞는다. 지수별 명단·결손 기록은 data/index_history.json 의
  months·gaps 에 그대로 남아 저장소만으로 감사할 수 있다.
· 가격 캐시는 2026-07-27 까지라 창 마지막 하루는 편출 종목이 비어 있다.

## 실행

  python build/style_pit.py

가격 캐시(data/_pit_px_cache.json)만 gitignore 라
러너에 없다. 산출물 data/style_pit.json 만 커밋한다(build/pit_backtest.py 와 같은 방식).
자료가 없으면 **크게 죽는다** — 'PIT' 라고 적힌 생존자 백테스트를 내보내는 것이 최악이다.
"""
from __future__ import annotations
import datetime as dt
import io, json, math, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "style_pit.json")
# ⚠ pit_members.json(사내 DB 산출) 은 2026-08-03 에 걷어냈다 — 멤버십은 index_members 가
#   data/index_history.json(위키 과거 리비전)에서 읽는다. 그 파일은 저장소에 커밋된다.
CACHE = os.path.join(DATA, "_pit_px_cache.json")

sys.path.insert(0, HERE)
import style_top_pdf as ST

# 여섯 스타일 전부. 앞 셋은 가격만, 뒤 셋은 시점별 재무가 필요하다 — 편출 종목 재무를
# data/fx_pit/ 로 받아(build/pit_facts.py, 러너) 뒤 셋도 잴 수 있게 됐다.
#   ⚠ 뒤 셋의 채점 함수는 P.px 가 아니라 **P.uni** 를 순회한다(sc_qual:331·sc_val:350·
#     sc_grow:368). 그래서 주입할 때 P.px 만으로는 후보가 되지 않고 P.uni 도 채워야 한다.
STYLES = [("mom", "모멘텀", ST.sc_mom), ("lowvol", "저변동", ST.sc_lowvol),
          ("hbeta", "고베타", ST.sc_hbeta),
          ("qual", "퀄리티", ST.sc_qual), ("val", "가치", ST.sc_val),
          ("grow", "성장", ST.sc_grow)]
FX_PIT = os.path.join(DATA, "fx_pit")


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit("%s 가 없다(%s) — 이 스크립트는 사내망 PC 에서만 돈다. "
                         "자료 없이 돌려 'PIT' 라고 적힌 생존자 백테스트를 내보내지 않는다."
                         % (what, path))
    return json.load(io.open(path, encoding="utf-8"))


def concentr(nav_a, nav_b, P, start):
    """편향이 몇 달에 실려 있나 — 월별 기여와 상위 2달 몫.

    두 nav 의 **월별 수익률 차**를 낸다. 상위 2달이 총합의 대부분이면 그 편향은 점추정으로
    읽을 것이 아니라 '그 몇 달 이야기' 다. 재실행이 필요 없다(nav 만 쓴다).
    """
    a, b = np.asarray(nav_a, float), np.asarray(nav_b, float)
    if len(a) != len(b) or len(a) < 2:
        return {"months": [], "top2_share": None}
    ends = [k for k in range(1, len(a))
            if P.dates[start + k][:7] != P.dates[start + k - 1][:7]] + [len(a) - 1]
    out, prev = [], 0
    for e in ends:
        if e <= prev:
            continue
        d = ((a[e] / a[prev]) - (b[e] / b[prev])) * 100
        out.append([P.dates[start + e][:7], round(float(d), 2)])
        prev = e
    tot = sum(abs(x[1]) for x in out)
    top2 = sum(sorted((abs(x[1]) for x in out), reverse=True)[:2])
    return {"months": out, "top2_share": (round(top2 / tot, 3) if tot > 0 else None)}


def perf(nav):
    """**ST.metrics 를 그대로 쓴다.** 산식을 두 벌 두면 어긋난다 — 실측으로 걸렸다:
    직접 짠 ret 은 단순 누적(134.08%)이었는데 배포의 metrics['ret'] 은 **연율화**
    (137.31%)였다. 앵커 검증이 그 차이를 '편향'으로 오인하게 만들 뻔했다.
    창이 정확히 1년이 아닐 때 둘을 구분해 읽을 수 있게 total 만 덧붙인다.
    """
    x = np.asarray(nav, float)
    m = ST.metrics(x)
    m["total"] = (x[-1] / x[0] - 1) * 100
    m["nav"] = x                      # concentr 가 쓰고, JSON 에 싣기 전에 지운다
    return m


def narrowed(fn, pool_of):
    """채점 모집단까지 그 시점 후보로 좁힌 채점 함수.

    🚨 이것이 'PIT' 의 정확한 뜻이다(적대감사가 잡은 결함). backtest 의 마스크는 **채점 뒤**에
      걸리므로, 좁히지 않으면 세 레그가 모두 538종으로 z 표준화·윈저화를 한다. 실제로 그때
      규칙을 돌렸다면 모집단도 그 시점 후보였다. 좁히면 두 가지가 동시에 해결된다 —
        ① pit 레그가 진짜 PIT 가 된다(실측: 가치 생존채널 11.34 → 9.49%p).
        ② base 레그를 today 로 좁히면 538 패널이 518 패널과 같아져 **하니스 채널이 0 이 된다**.
           즉 앞서 5.56%p 를 따로 빼서 세던 것을 애초에 만들지 않는다. base==published 로
           확인할 수 있고, 그 등식이 이 방식이 옳다는 증거다.
    P.uni·P.px 를 임시로 좁혀 부르고 반드시 되돌린다(finally).
    """
    def g(P, i):
        pool = pool_of(i)
        su, sp = P.uni, P.px
        P.uni = {t: v for t, v in su.items() if t in pool}
        P.px = {t: v for t, v in sp.items() if t in pool}
        try:
            return fn(P, i)
        finally:
            P.uni, P.px = su, sp
    return g


def ew_nav(P, pool_at, start, end):
    """대조군 — 매 시점 후보 전체를 동일가중으로 담았을 때. 전략과 같은 유니버스를 쓴다.

    ⚠ 대조군도 같은 규칙으로 좁혀야 한다. 전략만 PIT 이고 대조군이 소급이면 초과수익이
      엉뚱해진다(pit_backtest.py:200 이 같은 이유로 벤치를 PIT 로 만든다).
    """
    nav = np.ones(end - start + 1)
    cur = None
    for k, i in enumerate(range(start + 1, end + 1), start=1):
        if (i - 1) in P.me or cur is None:
            m = pool_at(i - 1)
            m = [t for t in m if t in P.px]
            if m:
                cur = m
        rs = []
        for t in cur:
            a = P.px[t]
            if not np.isnan(a[i]) and not np.isnan(a[i - 1]) and a[i - 1] > 0:
                rs.append(a[i] / a[i - 1])
        nav[k] = nav[k - 1] * (float(np.mean(rs)) if rs else 1.0)
    return nav


def main() -> int:
    # ⚠ 2026-08-03: 사내 DB 산출(pit_members.json) → 위키 과거 리비전(index_history.json).
    #   그 파일은 저장소에 커밋되므로 이 스크립트가 더 이상 사내망 PC 에 묶이지 않는다.
    import index_members                          # noqa: E402  같은 build/ 안
    mem, _carried = index_members.load()
    for _ym, _ix, _n in _carried:
        print("  ⚠ %s %s 결손 — 직전 달 %d종 이월" % (_ym, _ix.upper(), _n))
    cache = need(CACHE, "편출 종목 가격 캐시")
    P = ST.Panel()
    end = len(P.dates) - 1
    start = next((i for i in P.me if i >= max(0, end - ST.WINDOW)), max(0, end - ST.WINDOW))
    di = {d: k for k, d in enumerate(P.dates)}
    today = set(P.uni)

    def members_at(i):
        """그 달 멤버 — pit_backtest.py:197 과 같은 정의(월 키 조회)."""
        return set(mem.get(P.dates[i][:7]) or [])

    # 멤버십이 창을 덮는지 먼저 본다. 한 달이라도 비면 그 달은 마스크가 통째로 풀려
    # 조용히 생존자 백테스트로 되돌아간다 — 그것이 이 파일이 막아야 할 실패다.
    gapless = [i for i in P.me if start - 252 * 3 <= i <= end and not members_at(i)]
    if gapless:
        raise SystemExit("멤버십이 빈 월말 %d개(%s …) — 마스크가 풀려 PIT 이 성립하지 않는다"
                         % (len(gapless), P.dates[gapless[0]]))

    # 창 안에서 한 번이라도 멤버였던 것 중 오늘 유니버스에 없는 것 = 주입 대상.
    #   ⚠ 3년(모멘텀 창) 합집합으로 넓히면 안 된다. 창 전에 이미 빠진 종목은 창 안에서
    #     **후보였던 적이 없다**. 넣으면 후보는 안 늘고 z 표준화 모집단만 바뀌어 규칙 자체가
    #     달라진다(실측: 그렇게 했더니 survivor 가 배포 수치 137.31 대신 126.47 이 나왔다).
    #     후보의 3년 이력은 그 후보 자신의 캐시로 충분하다.
    win_me = [j for j in P.me if start <= j <= end]
    union = set()
    for i in win_me:
        union |= members_at(i)
    gone = sorted(union - today)
    # 거울 수치 — **이쪽이 편향의 지배 채널이다.** 창 시작 시점에 아직 멤버가 아니었던
    # 오늘 종목들. 지수는 많이 오른 종목을 편입하므로 이 종목들을 소급으로 고를 수 있다는 것은
    # '오를 것'을 미리 아는 것과 같다. 편출(gone)만 세어 적으면 작은 채널만 계량하게 된다.
    m0 = members_at(start)
    not_yet = sorted(today - m0)

    def load_series(t):
        c = cache.get(t) or {}
        a = np.full(len(P.dates), np.nan)
        n = 0
        for d, v in c.items():
            j = di.get(d)
            if j is not None and v is not None:
                a[j] = float(v); n += 1
        return (a, n)

    inject, missing, gap = {}, [], []
    for t in gone:
        a, n = load_series(t)
        if n < 200:                      # 채점 자체가 안 되는 조각은 넣지 않는다
            missing.append(t); continue
        # 티커 재사용 가드 — **일간 점프로 판정하면 안 된다.** 실측: ±80% 규칙이 First
        # Republic 파산(-90.5%)과 Insmed 임상 발표(+118.5%)를 잡아냈다. 둘 다 진짜 사건이고,
        # 특히 파산은 생존편향이 감추는 바로 그 사건이라 버리면 편향을 과소평가한다.
        # 재사용의 실제 지문은 **긴 공백 뒤 재개**다(상장폐지 후 티커가 남에게 넘어간다).
        idx = np.flatnonzero(~np.isnan(a))
        if len(idx) > 1 and int(np.max(np.diff(idx))) >= 60:
            gap.append(t); continue
        inject[t] = a
    print("창 편출 %d종 · 주입 가능 %d종 · 가격 부재 %d종: %s"
          % (len(gone), len(inject), len(missing), missing))
    if gap:
        print("  ⚠ 60거래일 이상 공백 뒤 재개(티커 재사용 의심) 제외: %s" % gap)

    # ── ① 앵커 레그 — **주입 전** 깨끗한 518 패널 ───────────────────────────
    #   published 는 배포 수치를 그대로 재현해야 한다. 그것이 이 측정의 앵커다 —
    #   재현되지 않으면 '편향'이 아니라 내가 계산을 바꾼 것이다.
    #   ⚠ 하지만 **이것을 편향의 기준선으로 쓰면 안 된다**(아래 참조).
    res = {}
    for key, label, fn in STYLES:
        R = ST.backtest(P, fn, pool_of=None)
        if not R:
            raise SystemExit("%s 의 앵커 레그가 실패했다" % label)
        m = perf(R["nav"]); m["n_rebal"] = R["n_rebal"]
        res[key] = {"label": label, "published": m}

    # ── ② 주입 후 — 세 레그를 **같은 패널**에서 잰다 ────────────────────────
    # 주입은 세 축을 같이 해야 한다:
    #   px  … 가격(sc_mom·_vol_beta 가 P.px 를 순회)
    #   uni … 후보 명부(sc_qual·sc_val·sc_grow 가 P.uni 를 순회 — 이것 없으면 뒤 셋은 주입이
    #         아무 효과가 없고 '편출 기여 0' 이 자료 부재 때문인지 진짜인지 구별이 안 된다)
    #   fx  … 시점별 재무(data/fx_pit, build/pit_facts.py 가 러너에서 받은 것)
    # 🚨 적대감사가 잡은 결함. 앵커(518종)와 PIT(538종)를 각각 다른 패널에서 재고 그 차이를
    #   전부 '편향'이라 적었더니, 모멘텀에서 5.56%p 가 편향이 아니라 **하니스 산물**이었다.
    #   sc_mom 은 zs() 로 표준화하는데 모집단이 518→538 로 바뀌면 평균·표준편차·윈저 경계가
    #   같이 움직여 **마스크를 걸지 않아도** 기존 종목의 점수와 순위가 달라진다(실측: 538 패널에
    #   마스크 없이 재면 137.31 이 아니라 131.75). sc_lowvol·sc_hbeta 는 zs 를 쓰지 않아
    #   이 효과가 정확히 0 이다 — 그래서 모멘텀에만 생겼고 눈에 잘 안 띄었다.
    #   고침: 편향은 **패널을 고정하고** base(마스크 없음) 대비로 잰다. published 는 앵커 전용.
    for t, a in inject.items():
        P.px[t] = a
    # 재무 — data/fx 와 data/fx_pit 를 함께 훑어 다시 만든다(load_fund 이 한 벌이라 어긋날 일 없다).
    if os.path.isdir(FX_PIT):
        import importlib.util
        _sp = importlib.util.spec_from_file_location("_tb2", os.path.join(HERE, "tech_backtest.py"))
        _tb = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_tb)
        P.fx = _tb.load_fund(extra_dirs=[FX_PIT])
        n_fx = len([t for t in inject if t in P.fx])
        print("편출 재무 주입 %d/%d종(data/fx_pit %d개)"
              % (n_fx, len(inject), len(os.listdir(FX_PIT))))
    else:
        n_fx = 0
        print("⚠ data/fx_pit 없음 — 퀄리티·가치·성장은 편출 후보 없이 측정된다"
              "(러너에서 pit-facts 워크플로를 돌릴 것)")
    # 명부 — 뒤 셋이 순회하는 축. 이름은 재무 파일에서 가져오고 없으면 티커로 둔다
    # (이름은 build_issuer 의 발행사 키에 쓰인다 — 없으면 티커가 곧 발행사가 된다).
    nm = {}
    if os.path.isdir(FX_PIT):
        for f in os.listdir(FX_PIT):
            try:
                d = json.load(io.open(os.path.join(FX_PIT, f), encoding="utf-8"))
                nm[d.get("t") or f[:-5]] = d.get("nm") or ""
            except Exception:
                pass
    for t in inject:
        if t not in P.uni:
            P.uni[t] = {"t": t, "name": nm.get(t) or t, "idx": []}
    # 🚨 발행사 맵은 P._iss 에 **캐시된다**(iss_of). 앵커 레그에서 이미 채워졌으므로 지워야
    #   새 명부가 반영된다. 안 지우면 주입 종목이 발행사 중복제거에서 조용히 빠진다.
    if hasattr(P, "_iss"):
        del P._iss
    cov = []
    for i in win_me:
        m = members_at(i)
        if m:
            cov.append(len([t for t in m if t in P.px]) / len(m))
    print("멤버 대비 가격 보유율: 최저 %.1f%% · 중앙 %.1f%%"
          % (100 * min(cov), 100 * sorted(cov)[len(cov) // 2]))

    # 주입 종목이 스타일별로 **실제 채점되는지** 센다. 이것 없이 '편출 기여 0' 을 적으면
    # 자료가 없어서 0 인지 진짜 0 인지 구별이 안 된다(적대감사가 짚은 함정).
    scored = {}
    for key, label, fn in STYLES:
        s, _tie = fn(P, win_me[0])
        scored[key] = len([t for t in inject if t in s])
    print("주입 %d종 중 채점되는 수: %s"
          % (len(inject), " · ".join("%s %d" % (STYLES[k][1], scored[STYLES[k][0]])
                                     for k in range(len(STYLES)))))

    LEGS = (("base", lambda i: today),                      # 마스크 없음 = 오늘의 유니버스
            ("mask", lambda i: members_at(i) & today),      # 그때 멤버였던 오늘 종목만
            ("pit", members_at))                            # 그때 멤버 전부(편출 포함)
    for key, label, fn in STYLES:
        for tag, po in LEGS:
            # 채점 모집단까지 좁힌다 — narrowed() 의 주석 참조. 이것이 PIT 의 정확한 뜻이고,
            # base 가 published 와 같아지는 것으로 검증된다(하니스 채널이 구조적으로 0).
            R = ST.backtest(P, narrowed(fn, po), pool_of=po)
            if not R:
                raise SystemExit("%s 의 %s 레그가 실패했다" % (label, tag))
            m = perf(R["nav"]); m["n_rebal"] = R["n_rebal"]
            res[key][tag] = m
        v = res[key]
        # 두 채널을 분해한다. 합이 총편향이고, 어느 쪽이 지배하는지가 이 측정의 결론이다.
        #   lookahead  … 그때 지수에 없던 종목을 미리 고른 것(base → mask)
        #   survivorship … 그때 있었는데 뒤에 빠진 종목이 후보에 없던 것(mask → pit)
        v["bias"] = {k: (None if (v["base"].get(k) is None or v["pit"].get(k) is None)
                         else round(v["base"][k] - v["pit"][k], 2))
                     for k in ("ret", "total", "sharpe", "mdd")}
        v["channel"] = {
            "lookahead": round(v["base"]["ret"] - v["mask"]["ret"], 2),
            "survivorship": round(v["mask"]["ret"] - v["pit"]["ret"], 2),
            # 좁히기 전에는 이 자리에 5~7%p 가 있었다. 지금은 0 이어야 한다 — 0 이 아니면
            # 좁히기가 어딘가 새고 있다는 뜻이므로 그대로 세어 둔다(0 을 확인하려고 남긴다).
            "harness_zpop": round(v["published"]["ret"] - v["base"]["ret"], 2),
        }
        # 🚨 집중도 — 이것 없이 점추정만 내면 안 된다(적대감사). 총편향이 몇 달에 실려
        #   있는지를 nav 에서 바로 센다(재실행 없음). 한두 달이 대부분이면 그 수치는
        #   '측정' 이라기보다 '그 달 이야기' 다. 가치가 정확히 그런 경우로 나왔다.
        v["concentration"] = concentr(v["base"]["nav"], v["pit"]["nav"], P, start)
        c = v["concentration"]
        print("  %-5s 배포 %+8.2f · 기준선 %+8.2f · 마스크 %+8.2f · PIT %+8.2f "
              "→ 총편향 %+7.2f%%p (선견 %+.2f · 생존 %+.2f · 잔여하니스 %+.2f) "
              "· 상위2달 %.0f%%"
              % (label, v["published"]["ret"], v["base"]["ret"], v["mask"]["ret"],
                 v["pit"]["ret"], v["bias"]["ret"], v["channel"]["lookahead"],
                 v["channel"]["survivorship"], v["channel"]["harness_zpop"],
                 100 * (c["top2_share"] or 0)))
        for lg in ("published", "base", "mask", "pit"):      # nav 는 JSON 에 싣지 않는다
            v[lg].pop("nav", None)

    # ── 앵커 검증 — survivor 가 배포 수치와 같은가 ──────────────────────────
    # 같지 않으면 '편향을 쟀다'고 말할 수 없다. data/style_perf.json 의 metrics.ret 과 대조한다.
    anchor, bad = {}, []
    try:
        pub = {s["key"]: s for s in json.load(
            io.open(os.path.join(DATA, "style_perf.json"), encoding="utf-8"))["styles"]}
    except Exception as e:
        raise SystemExit("배포 수치(style_perf.json)를 못 읽어 앵커 검증을 못 한다: %s" % e)
    for key, label, _fn in STYLES:
        got = (res.get(key, {}).get("published") or {}).get("ret")
        want = ((pub.get(key) or {}).get("metrics") or {}).get("ret")
        anchor[key] = {"measured": None if got is None else round(got, 2), "published": want}
        if got is None or want is None or abs(got - want) > 0.02:
            bad.append("%s 측정 %s vs 배포 %s" % (label, got, want))
    if bad:
        raise SystemExit("앵커 불일치 — 배포 수치를 재현하지 못했다(%s). "
                         "차이는 편향이 아니라 계산 변경이다. style_perf.json 을 먼저 "
                         "다시 만들었는지 확인할 것." % " · ".join(bad))
    print("앵커 확인 — 배포 수치와 일치(%s)"
          % ", ".join("%s %.2f%%" % (k, v["published"]) for k, v in anchor.items()))

    # ── 대조군 ─────────────────────────────────────────────────────────────
    # 동일가중은 z 표준화를 쓰지 않으므로 패널 확장 효과가 없다 — base 와 published 가 같다.
    bench = {}
    for tag, po in (("base", lambda i: today), ("pit", members_at)):
        bench[tag] = perf(ew_nav(P, po, start, end))
    bench["bias"] = {k: (None if (bench["base"].get(k) is None or bench["pit"].get(k) is None)
                         else round(bench["base"][k] - bench["pit"][k], 2))
                     for k in ("ret", "total", "sharpe", "mdd")}
    print("  대조군 동일가중 기준선 %+.2f%% · PIT %+.2f%% → 편향 %+.2f%%p"
          % (bench["base"]["ret"], bench["pit"]["ret"], bench["bias"]["ret"]))
    bench["concentration"] = concentr(bench["base"]["nav"], bench["pit"]["nav"], P, start)
    for lg in ("base", "pit"):
        bench[lg].pop("nav", None)

    doc = {
        "as_of": P.dates[end], "start": P.dates[start],
        "n_days": end - start + 1, "n_month_ends": len([j for j in P.me if start <= j <= end]),
        "note": ("같은 백테스트 코드에 pool_of 만 갈아 끼워 유니버스 편향을 잰 것이다. "
                 "채점 모집단까지 그 시점 후보로 좁힌다 — 그것이 PIT 의 정확한 뜻이고, "
                 "그래서 base 가 published 와 정확히 일치한다(잔여 하니스 0). "
                 "published = 지금 화면에 나가는 수치(앵커) · base = 오늘 유니버스 · "
                 "mask = 선정 시점 멤버 ∩ 오늘 · pit = 선정 시점 멤버 전부. "
                 "base→mask 가 사후편입 선견, mask→pit 가 교과서적 생존편향이다. "
                 "여섯 스타일 전부 다룬다 — 편출 종목 재무를 data/fx_pit 로 받아(build/pit_facts.py, "
                 "러너) 퀄리티·가치·성장도 잴 수 있게 됐다. 채점되는 편출 종목 수는 scored 에 있다."),
        "headline": ("편향에는 채널이 둘이고 스타일마다 지배 채널이 다르다. "
                     "(1) 사후편입 선견 — 오늘 %d종목 중 %d종은 구간 시작 시점에 아직 지수 "
                     "비멤버였다. 지수는 많이 오른 종목을 편입하므로 소급 유니버스는 '오를 것'을 "
                     "미리 아는 셈이 된다. 고베타·모멘텀·성장이 여기에 걸린다. "
                     "(2) 생존편향 — 구간 시작 멤버 %d종 중 %d종이 오늘 유니버스에 없다. "
                     "가치가 여기에 걸린다(편출 종목은 전형적인 값싼 주식이고 지수에서 빠진 "
                     "이유가 부진이라, 가치 스크린이 골랐어야 할 후보가 없었다). "
                     "채널별 크기는 styles[*].channel 에 있다."
                     % (len(today), len(not_yet), len(m0), len(m0 - today))),
        "scored": {STYLES[k][0]: scored[STYLES[k][0]] for k in range(len(STYLES))},
        "limits": ("'하한'이라고 단정하지 않는다. 창 편출 %d티커 중 가격 확보 %d개, 미확보 %d개인데 "
                   "그중 개명 5개(BK→BNY·MMC→MRSH·FI→FISV·PARA→PSKY·SATS→ECHO)는 후임 티커로 "
                   "재실행해 영향 0.00%%p 를 확인했고, SOLS 는 이력이 짧아 어느 스타일에서도 채점 "
                   "자체가 안 된다. 실효 미검증은 6개(CTRA·DAY·HOLX·IPG·K·WBA)이고 대부분 인수·"
                   "비상장화 편출이라 방향을 단정하지 않는다 — 다만 저변동은 딜가에 고정된 저변동 "
                   "종목이 상위10 문턱(실현변동성 16~18%%) 아래라 과소측정 쪽이 유력하다. "
                   "🚨 **크기를 점추정으로 읽지 말 것** — 구간이 12개월뿐이라 편향이 몇 달에 "
                   "몰려 있다(concentration.top2_share 참조). 특히 가치의 생존 채널은 교체가 "
                   "9개월·18슬롯에 불과하고 상당 부분이 한계슬롯에서 밀려난 생존 종목의 그 달 "
                   "큰 수익에서 나온다 — 방향은 신뢰할 만하지만 크기는 표본오차와 구별하기 어렵다. "
                   "|채널| 2%%p 미만(퀄리티·성장의 생존 채널)은 잡음으로 읽을 것. "
                   "재무 커버리지도 완전하지 않다 — 편출 20종 중 채점되는 것이 퀄리티 13·가치 17·"
                   "성장 20 이다. 사유는 태그로 메울 수 있는 것(LKQ·LW 의 liab, LW 의 rev)과 "
                   "그렇지 않은 것(AZN·GFS 는 IFRS 라 분기 프레임이 없다 · MTCH·INSM 은 평균 "
                   "자기자본이 음수 · ENPH 는 분기 eps 프레임이 희소)이 섞여 있고, 오늘 유니버스도 "
                   "같은 규칙으로 빠지는 종목이 많아(퀄리티 채점률 오늘 62%% vs 편출 65%%) "
                   "차별적 불리함은 아니다. 가치만 격차가 있다(오늘 92%% vs 편출 85%%). "
                   "채점 모집단까지 좁혀 하니스 산물을 애초에 만들지 않았다"
                   "(channel.harness_zpop 이 0 인지로 확인할 수 있다). "
                   "sc_val·sc_grow 는 성분이 결손이면 0.0 으로 채우는데(for/else) 이는 배포 "
                   "수치에도 같이 있는 성질이라 여기서 바꾸지 않았다. "
                   "비율의 분모가 배당수정가라 고배당 종목이 싸게 잡힌다(가치 생존채널에 약 0.3%%p). "
                   "보유 중 가격이 끊긴 종목은 마지막 종가에 빠져나온 것으로 보아 파산 손실을 "
                   "덜 잡는다. 멤버십은 SPX∪NDX 합집합·월 해상도(그 달 마지막 스냅샷)다."
                   % (len(gone), len(inject), len(missing))),
        "universe": {"today": len(today), "n_members_at_start": len(m0),
                     # ⚠ 두 기준을 섞지 말 것 — gone 은 창 12개월 **합집합**이고
                     #   gone_at_start 는 창 시작 **스냅샷**이다. 517 과 짝이 맞는 것은 후자다.
                     "gone": len(gone), "gone_at_start": len(m0 - today),
                     "filled": len(inject),
                     # 러너가 읽는다 — build/pit_facts.py 가 이 명단으로 SEC 재무를 받아
                     # data/fx_pit/ 에 넣는다. 멤버십(index_history.json)은 커밋되므로
                     # 러너가 스스로 계산할 수 없으므로 여기 실어 보내는 것이 유일한 경로다.
                     "gone_tickers": gone,
                     "not_yet_member_at_start": len(not_yet), "not_yet": not_yet,
                     "missing": sorted(missing), "reused_ticker_suspect": sorted(gap),
                     "cov_min": round(min(cov), 4), "cov_med": round(sorted(cov)[len(cov) // 2], 4)},
        "anchor": anchor, "styles": res, "bench": bench,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("→ %s (%dB)" % (OUT, os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
