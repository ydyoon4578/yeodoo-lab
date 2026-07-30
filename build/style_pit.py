# -*- coding: utf-8 -*-
"""build/style_pit.py — 스타일 백테스트의 **유니버스 편향 크기를 실제로 잰다** → data/style_pit.json

## 🚨 이름부터 — 이것은 '생존편향'이 아니다

재 보니 편향의 94~100% 가 **사후편입 선견(look-ahead)** 이었다. 교과서적 생존편향(편출·폐지
종목이 후보에 없던 것)은 모멘텀 4.3%p, 나머지 0 이다. 두 채널을 반드시 갈라 적을 것 —
지배 채널을 작은 채널 이름으로 부르면 원인을 잘못 짚게 된다(적대감사가 잡은 결함).

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

## 왜 여섯 스타일이 아니라 셋인가

가격만으로 정의되는 규칙만 다룬다 — 모멘텀·저변동·고베타. 퀄리티·가치·성장은 시점별 재무가
필요한데 편출 종목의 재무가 **0건**이다(data/fx 는 전부 오늘의 유니버스). 반쪽만 PIT 로 바꾸면
비교가 성립하지 않는다. build/pit_backtest.py 가 가격 규칙 16종만 다루는 이유가 정확히 같다.

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
· 멤버십은 SPX∪NDX 합집합이고 월 해상도다. 스냅샷은 그 달 마지막 dt 이므로(pit_backtest.py
  의 SQL 이 월별 max(dt) 를 잡는다) 월말 선정과 시점이 맞는다. 다만 파일에 dt·지수 라벨이
  남지 않아 저장소만으로는 그 규약을 감사할 수 없다 — 재수집 때 함께 저장할 것.
· 가격 캐시는 2026-07-27 까지라 창 마지막 하루는 편출 종목이 비어 있다.

## 실행

  python build/style_pit.py

로컬 전용이다 — data/pit_members.json(사내 DB 원천)과 data/_pit_px_cache.json 은 gitignore 라
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
MEMB = os.path.join(DATA, "pit_members.json")
CACHE = os.path.join(DATA, "_pit_px_cache.json")

sys.path.insert(0, HERE)
import style_top_pdf as ST

# 가격만으로 정의되는 스타일. 여기 손대려면 위 독스트링의 '왜 셋인가'를 먼저 읽을 것.
STYLES = [("mom", "모멘텀", ST.sc_mom), ("lowvol", "저변동", ST.sc_lowvol),
          ("hbeta", "고베타", ST.sc_hbeta)]


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit("%s 가 없다(%s) — 이 스크립트는 사내망 PC 에서만 돈다. "
                         "자료 없이 돌려 'PIT' 라고 적힌 생존자 백테스트를 내보내지 않는다."
                         % (what, path))
    return json.load(io.open(path, encoding="utf-8"))


def perf(nav):
    """**ST.metrics 를 그대로 쓴다.** 산식을 두 벌 두면 어긋난다 — 실측으로 걸렸다:
    직접 짠 ret 은 단순 누적(134.08%)이었는데 배포의 metrics['ret'] 은 **연율화**
    (137.31%)였다. 앵커 검증이 그 차이를 '편향'으로 오인하게 만들 뻔했다.
    창이 정확히 1년이 아닐 때 둘을 구분해 읽을 수 있게 total 만 덧붙인다.
    """
    x = np.asarray(nav, float)
    m = ST.metrics(x)
    m["total"] = (x[-1] / x[0] - 1) * 100
    return m


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
    mem = need(MEMB, "선정 시점 멤버십")["members"]
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
    # 🚨 적대감사가 잡은 결함. 앵커(518종)와 PIT(538종)를 각각 다른 패널에서 재고 그 차이를
    #   전부 '편향'이라 적었더니, 모멘텀에서 5.56%p 가 편향이 아니라 **하니스 산물**이었다.
    #   sc_mom 은 zs() 로 표준화하는데 모집단이 518→538 로 바뀌면 평균·표준편차·윈저 경계가
    #   같이 움직여 **마스크를 걸지 않아도** 기존 종목의 점수와 순위가 달라진다(실측: 538 패널에
    #   마스크 없이 재면 137.31 이 아니라 131.75). sc_lowvol·sc_hbeta 는 zs 를 쓰지 않아
    #   이 효과가 정확히 0 이다 — 그래서 모멘텀에만 생겼고 눈에 잘 안 띄었다.
    #   고침: 편향은 **패널을 고정하고** base(마스크 없음) 대비로 잰다. published 는 앵커 전용.
    for t, a in inject.items():
        P.px[t] = a
    cov = []
    for i in win_me:
        m = members_at(i)
        if m:
            cov.append(len([t for t in m if t in P.px]) / len(m))
    print("멤버 대비 가격 보유율: 최저 %.1f%% · 중앙 %.1f%%"
          % (100 * min(cov), 100 * sorted(cov)[len(cov) // 2]))

    LEGS = (("base", lambda i: today),                      # 마스크 없음 = 오늘의 유니버스
            ("mask", lambda i: members_at(i) & today),      # 그때 멤버였던 오늘 종목만
            ("pit", members_at))                            # 그때 멤버 전부(편출 포함)
    for key, label, fn in STYLES:
        for tag, po in LEGS:
            R = ST.backtest(P, fn, pool_of=po)
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
            "harness_zpop": round(v["published"]["ret"] - v["base"]["ret"], 2),
        }
        print("  %-5s 배포 %+8.2f · 기준선 %+8.2f · 마스크 %+8.2f · PIT %+8.2f "
              "→ 총편향 %+7.2f%%p (선견 %+.2f · 생존 %+.2f · 하니스 %+.2f)"
              % (label, v["published"]["ret"], v["base"]["ret"], v["mask"]["ret"],
                 v["pit"]["ret"], v["bias"]["ret"], v["channel"]["lookahead"],
                 v["channel"]["survivorship"], v["channel"]["harness_zpop"]))

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

    doc = {
        "as_of": P.dates[end], "start": P.dates[start],
        "n_days": end - start + 1, "n_month_ends": len([j for j in P.me if start <= j <= end]),
        "note": ("같은 백테스트 코드에 pool_of 만 갈아 끼워 유니버스 편향을 잰 것이다. "
                 "published = 지금 화면에 나가는 수치(앵커 전용) · base = 같은 패널·마스크 없음"
                 "(편향의 기준선) · mask = 선정 시점 멤버 ∩ 오늘 · pit = 선정 시점 멤버 전부. "
                 "base→mask 가 사후편입 선견, mask→pit 가 교과서적 생존편향이다. "
                 "가격만으로 정의되는 스타일 셋만 다룬다 — 편출 종목의 재무가 0건이라 "
                 "퀄리티·가치·성장은 반쪽만 PIT 가 되고 그러면 비교가 성립하지 않는다."),
        "headline": ("편향의 대부분은 생존편향이 아니라 **사후편입 선견**이다. 오늘 유니버스에는 "
                     "창 시작 시점에 아직 지수 비멤버였던 종목이 %d종 있고, 지수는 많이 오른 "
                     "종목을 편입하므로 소급 유니버스는 '오를 것'을 미리 아는 셈이 된다. "
                     "거울 방향(창 시작 멤버 %d종 중 %d종이 오늘 유니버스에 없음)의 기여는 "
                     "훨씬 작다." % (len(not_yet), len(m0), len(m0 - today))),
        "limits": ("'하한'이라고 단정하지 않는다. 창 편출 %d티커 중 가격 확보 %d개, 미확보 %d개인데 "
                   "그중 개명 5개(BK→BNY·MMC→MRSH·FI→FISV·PARA→PSKY·SATS→ECHO)는 후임 티커로 "
                   "재실행해 영향 0.00%%p 를 확인했고, SOLS 는 이력이 짧아 어느 스타일에서도 채점 "
                   "자체가 안 된다. 실효 미검증은 6개(CTRA·DAY·HOLX·IPG·K·WBA)이고 대부분 인수·"
                   "비상장화 편출이라 방향을 단정하지 않는다 — 다만 저변동은 딜가에 고정된 저변동 "
                   "종목이 상위10 문턱(실현변동성 16~18%%) 아래라 과소측정 쪽이 유력하다. "
                   "모멘텀 편향에는 하니스 산물이 섞이지 않게 base 를 같은 패널에서 따로 쟀다"
                   "(그 크기는 channel.harness_zpop 에 남긴다). "
                   "보유 중 가격이 끊긴 종목은 마지막 종가에 빠져나온 것으로 보아 파산 손실을 "
                   "덜 잡는다. 멤버십은 SPX∪NDX 합집합·월 해상도(그 달 마지막 스냅샷)다."
                   % (len(gone), len(inject), len(missing))),
        "universe": {"today": len(today), "n_members_at_start": len(m0),
                     # ⚠ 두 기준을 섞지 말 것 — gone 은 창 12개월 **합집합**이고
                     #   gone_at_start 는 창 시작 **스냅샷**이다. 517 과 짝이 맞는 것은 후자다.
                     "gone": len(gone), "gone_at_start": len(m0 - today),
                     "filled": len(inject),
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
