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
OUT = os.path.join(DATA, "pit_strategies.json")

START = "2015-01-01"      # 2026-08-04: 2020-09-01 → 여기로 (사용자 결정 — 아래 주석 참조)
TOPN = TB.TOPN

# 가격·거래량만으로 정의되는 규칙. 펀더멘털 규칙은 시점별 재무·주식수가 없어 제외한다 —
# 반쪽만 PIT 로 바꾸면 비교가 성립하지 않는다.
PRICE_SIDS = ["x-mom12", "x-lowvol", "x-rev1m", "x-52wh", "x-dist200",
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
              "x-lowvol-n100", "x-maxlow-n52", "x-max5low-n52"]

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
             "x-btp-n155", "x-payout-n50", "x-agrow-n52"]
# x-volsurge 는 뺐다. 거래량이 랩 파일(오늘의 유니버스)에만 있어 편출 85종의 채점률이 정확히
# 0%다 — 후보가 100% 생존자인 채로 편출종목을 포함한 대조군과 겨루게 되어, 이 파일이 없애려는
# 바로 그 선견이 규칙 하나에만 남는다. 거래량을 편출종목까지 받으면 되살릴 수 있다.
EXCLUDED_SIDS = {
    "x-volsurge": "편출 종목 거래량 부재 — 후보가 생존자로만 좁혀져 PIT 이 성립 안 함",
    # 🚨 2026-08-04. 랩 본편의 x-52wh 는 이날 버그를 고쳤다 — 52주 최고가 창이 신호일을
    #   포함해 신고가 종목의 점수가 정확히 1.0 이 되고(천장), 199개 월말 중 149개(75%)에서
    #   10칸 전부가 티커 알파벳 역순으로 채워지고 있었다. 고친 방향은 규칙문 그대로
    #   '최고가' = **일중 고가(hd)** 를 쓰는 것이다.
    #   그런데 여기서는 같은 고침을 할 수 없다 — data/_pit_px_cache.json 이 편출 종목의
    #   **종가만** 갖고 있어(147종·값이 스칼라) 고가가 없다. 랩 종목만 고가를 쓰고 편출 종목은
    #   종가를 쓰면 같은 횡단면 안에서 두 자로 채점하는 것이라 더 나쁘다.
    #   → 캐시가 OHLC 로 넓어질 때까지 PIT 에서 뺀다. **틀린 채로 재느니 안 재는 것이 낫다.**
    #   (이 항목이 '채점기가 두 벌이면 한쪽만 고쳐진다'의 실례다 — 본편을 고친 그 자리에서
    #    이쪽을 안 고쳤고, 적대감사가 build/pit_backtest.py:647 로 잡아냈다.)
    "x-52wh": "편출 종목 고가 부재 — 랩 본편이 쓰는 일중 고가를 PIT 캐시가 안 갖고 있다",
    # 🚨 2026-08-10. 투자의견 리비전 3종(사전등록 PREREG-2026-08-10-REVDRIFT.md)은 PIT 을
    #   돌 수 **없다**. yfinance 의 upgrades_downgrades 는 지금 상장돼 있는 종목만 주므로
    #   편출 종목의 등급 이력이 아예 없다 — 가격 캐시처럼 나중에 받아 채울 수 있는 종류가
    #   아니다. 위 x-52wh 는 파일이 오면 사유가 사라지지만 이쪽은 사라지지 않는다.
    #   그래서 이 셋은 **생존편향이 얼마인지 측정되지 않은 채로** 판정된다. 게시 기준 ④
    #   (PIT 레그 t > 0)를 적용 제외하고, 그 사실을 카드와 결과 문서에 싣는다.
    "x-revdrift": "편출 종목 투자의견 이력 부재 — 자료 원천이 생존자만 준다(보완 불가)",
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
      '생존편향 측정 창이 짧다'로 옮겨갔다. PIT 창 5.8년으로 17년짜리 규칙을 판정하는
      것은 짧은 쪽이 결론을 지배한다는 뜻이다. 게시 수치가 바뀐다 — 그게 목적이다.
      ⚠ 2015-01 이 한계다. index_history.json 이 거기서 시작한다(위키 리비전 보존 범위).
    """
    import index_members                            # noqa: E402  같은 build/ 안
    mem, carried = index_members.load(START)
    print("  멤버십 %d개월 (위키 과거 리비전 · data/index_history.json)" % len(mem))
    for ym, ix, n in carried:
        print("  ⚠ %s %s 결손 — 직전 달 %d종 이월" % (ym, ix.upper(), n))
    return mem


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
    bad_reuse = []
    for t, ser in cache.items():
        if t not in need or t in px or not ser:
            continue
        # 티커 재사용 방어 — 캐시 계열이 '그 티커가 멤버였던 기간'과 안 겹치면 다른 회사다.
        # 실측 사례: FB 캐시는 ProShares ETF(2025-06~), 멤버십의 FB 는 2020~2022 의 메타.
        ks = sorted(ser)
        lo, hi = MEMBER_SPAN.get(t, ("9999-99", "0000-00"))
        if ks[-1][:7] < lo or ks[0][:7] > hi:
            bad_reuse.append(t); continue
        px[t] = ser
    if bad_reuse:
        print("  ⚠ 티커 재사용 의심 %d종 제외(계열 기간이 멤버 기간과 안 겹침): %s"
              % (len(bad_reuse), ", ".join(sorted(bad_reuse))))
    print("  가격 %d종 (랩 %d + 편출캐시 %d)" % (len(px), n_lab, len(px) - n_lab))
    return px


def load_highs(need, dates):
    """티커 → 고가 배열(dates 와 같은 길이). 랩 종목은 data/sd, 편출 종목은 HL 캐시.

    🚨 두 출처를 섞는 것이 이 함수의 전부이고, 섞이지 **않으면** 후보가 생존자로만 좁혀진다 —
      그러면 생존편향을 재려는 표가 오히려 그 편향을 갖는다(x-volsurge 를 뺀 것과 같은 사유).
      그래서 편출 종목 커버리지를 함께 돌려주고, 낮으면 부르는 쪽이 규칙을 뺀다.
    """
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
        a = json.load(io.open(fp, encoding="utf-8")).get("hd") or []
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
        for t, ser in hl.items():
            if t not in need or t in hi or not ser:
                continue
            arr = [None] * len(dates)
            for d, v in ser.items():
                j = pos.get(d)
                if j is not None and isinstance(v, list) and v:
                    arr[j] = v[0]
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
    px_map = load_prices(need, span)
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
    C = {"px": px, "vlm": vlm, "R": R, "ixr": ixr, "ixvol": ixvol,
         "SH": C_SH, "dates": dates, "FU": _fu,
         # x-gpa·x-ocfp·x-aci 가 금융업을 뺀다 — 랩과 같은 섹터 라벨을 써야 정의가 같다.
         "sector": {t: (m or {}).get("sector") for t, m in (_lab_meta() or {}).items()},
         # x-season 이 월말 격자를 쓴다 — 랩과 같은 거래일 월말이어야 같은 시점을 본다.
         "me": sorted(me)}
    # 고가 — x-52wh 가 쓴다. 편출 종목분은 HLCACHE 에서 온다(없으면 그 규칙이 EXCLUDED_SIDS 다).
    if "x-52wh" not in EXCLUDED_SIDS:
        C["hi"], _nl, _nx = load_highs(set(px), dates)
        print("  고가 %d종 (랩 %d + 편출캐시 %d)" % (len(C["hi"]), _nl, _nx))

    # 편출 종목의 재무 커버리지 — 펀더멘털 규칙의 PIT 가 얼마나 성립하는지의 눈금.
    # 낮으면 그 규칙은 '후보가 생존자로 좁혀진' 쪽이므로 숫자와 함께 적어 둔다.
    _st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    _today = {s["t"] for s in _st["stocks"]}
    _gone = [t for t in tickers if t not in _today]
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

    # ── 같은 창의 소급 레그 ────────────────────────────────────────────────
    # 🚨 편향은 **같은 창**에서 재야 한다. 랩 본편은 2252일이고 여기는 1461일이라, 두 수치를
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
        CC = dict(C, ixr=IXR, ixvol=IXVOL)
        hold, nav, srets, turns = [], [100.0], [], 0
        first = None                       # 실제로 무언가를 보유하기 시작한 시점
        for i in range(i0 + 1, n):
            if (i - 1) in me:
                pool = pool_at(i - 1) if pool_at else None
                sc = []
                for t in tickers:
                    if pool is not None and t not in pool:      # ★ PIT 마스킹
                        continue
                    if pool is None and t not in _today:        # 소급 레그 = 오늘의 유니버스
                        continue
                    v = score(S, t, i - 1, CC)
                    if v is not None and v == v:
                        sc.append((v, t))
                sc.sort(reverse=True)
                if len(sc) < TB.XSEC_MIN_POOL:                  # 소급 레그와 같은 커버리지 게이트
                    hold = []
                else:
                    # 🚨 소급 레그와 **같은 선택 규칙**을 써야 한다 — 한 회사는 한 번만
                    #   (TB.pick_top). 여기만 두 클래스를 담으면 두 레그의 차이가
                    #   생존편향이 아니라 '바스켓 구성 규칙이 달라서'가 된다.
                    # 🚨 topn 을 넘겨야 소급 레그와 **바스켓 크기까지** 같아진다(2026-08-11).
                    #   안 넘기면 소급은 155종, PIT 은 10종이 되어 두 레그의 차이가
                    #   생존편향이 아니라 바스켓 크기가 된다 — 위 주석이 경계하는 그것이다.
                    new = TB.pick_top(sc, S["sid"], S.get("topn"))
                    if new:
                        # 분모도 바스켓 크기로 일반화한다(랩 본편 2026-08-08 과 같은 식).
                        # topn 이 없는 34종은 len(new)+len(hold) = 2×TOPN 이라 값이 그대로다.
                        turns += (len(set(new) ^ set(hold)) / (len(new) + len(hold))) if hold else 1.0
                        hold = new
            if hold and first is None:
                first = i
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
        """🚨 보유시작 재기준 — 소급 레그(tech_backtest)에는 있는데 여기엔 없었다. 적대감사 실측:
        x-season 은 same_month_avg 가 월말 61개를 요구해 PIT 창 시작보다 231거래일 늦게 첫 보유가
        생긴다. 그 231일간 전략 NAV 는 100 에 고정인데 대조군은 복리로 올라 PIT 초과수익이 음(−)
        쪽으로 5.27%p 과대, |t| 가 1.8배 과대, 화면에 적히는 생존편향 크기는 4.5%p 과소로 나왔다.
        이 파일이 스스로 주석에 적어 둔 i0 이음매 함정과 같은 것으로, i0 조정이 20일은 막았지만
        231일은 못 막았다. 창 길이가 전략마다 다르므로 start·n_days 도 전략별로 돌려준다
        (전역 라벨 1463일/5.8년은 그런 전략에 대해 거짓이다)."""
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
    for sid in [s for s in PRICE_SIDS + FUND_SIDS if s not in EXCLUDED_SIDS]:
        S = BY.get(sid)
        if not S:
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
            #     벤치에 실린 편향(실측 5.25%p)이 **상쇄된다** — 그래서 이 값은 항상
            #     bias_cagr − 5.25 이고 하한이 −5.25 다. 즉 '편향 0' 과 'PIT 가 유리' 를
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
                "유니버스 편향의 크기다 — 랩 본편(2252일)과 직접 빼면 구간 차이가 섞여 편향이 "
                "아니게 된다. 채점은 종목별로 독립이라(z 표준화 없음) 후보집합이 점수를 바꾸지 "
                "않으므로, 스타일 측정에서 필요했던 '채점 모집단 좁히기' 가 여기서는 불필요하다.",
        "start": dates[i0], "as_of": dates[-1], "n_days": n - i0,
        "span_years": round((n - i0) / 252.0, 1),
        "universe": "SPX ∪ NDX · 매월말 실제 편입(위키백과 과거 리비전 · data/index_history.json) · 가격은 yfinance",
        "coverage": {"min": round(cov_min, 4), "median": round(cov_med, 4)},
        "limits": [
            "구간이 %s부터다 — SPX 멤버십이 그때부터만 있어 합집합을 거기 맞췄다." % START,
            "🚨 위의 start·n_days 는 **전역 라벨**이고 규칙마다 실효 창이 다르다 — 각 규칙의 "
            "start·n_days 를 볼 것. 신호가 늦게 채워지는 규칙은 무보유 구간을 잘라내고 시작한다"
            "(동월 계절성은 월말 61개를 요구해 231거래일 늦다). 재기준이 없던 동안 그 구간에서 "
            "전략 NAV 는 100 에 고정인데 대조군만 복리로 올라, PIT 초과수익이 5.27%p 과대 음수·"
            "|t| 1.8배 과대·화면의 편향 크기가 4.5%p 과소로 나갔다(적대감사가 잡았다). "
            "두 레그는 늦은 쪽에 함께 맞춘다 — 각자 맞추면 창이 갈려 구간 차이가 편향으로 위장한다.",
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
            "생존편향을 완전히 걷어내지 못했고, 남은 방향은 여전히 낙관 쪽이다."
            % (100 * cov_min, 100 * cov_med),
            "'거래량 급증' 규칙은 아예 뺐다 — 거래량이 오늘의 유니버스에만 있어 후보가 100%% "
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
            % (len(PRICE_SIDS) + len(FUND_SIDS), len(PRICE_SIDS), len(FUND_SIDS),
               len(_gone), len(_fx_gone), 100 * fx_cov, len(_gone) - len(_fx_gone)),
            "비용 0(gross) · 신호는 당일 종가로 계산해 다음 거래일부터 적용(선견 없음).",
        ],
        "strategies": out,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("\n→ %s · %d종 · %s ~ %s (%s년)"
          % (OUT, len(out), doc["start"], doc["as_of"], doc["span_years"]))
    return 0


def score(S, t, j, C):
    # 🚨 2026-08-05 — 여기 ttm() 을 쓰면 랩 본편(ttm2)과 **다른 규칙**이 된다. 하루 전에
    #   tech_backtest 만 ttm2(q, a) 로 바꾸고 이 파일을 안 고쳐서 정확히 그 일이 있었다.
    #   같은 사고가 오늘만 두 번째다(x-52wh 도 tech 에서만 고쳐졌었다). 채점기가 두 벌인 한
    #   구조적으로 다시 난다 — 아래 갈래를 고칠 때 반드시 tech_backtest 와 나란히 볼 것.
    """tech_backtest 의 횡단면 점수 갈래를 그대로 옮긴 것(가격·거래량 + 펀더멘털).

    ⚠ 정의를 여기서 새로 쓰면 안 된다 — tech_backtest.py:1232-1281 과 **같은 산식**이어야
      '소급 대비 PIT' 비교가 성립한다. 옮길 때 접근자(asof_fund·ttm·_shift)도 그쪽 것을 쓴다.
    """
    # 🚨 랩 본편(tech_backtest.py) 과 **같은 자리에 같은 처리**다 — 바스켓 크기만 다른
    #   규칙(x-btp-n155 등)은 점수 함수가 짝과 완전히 같아야 하므로 접미사를 떼고 갈래를 탄다.
    #   여기만 안 떼면 그 셋이 어느 갈래에도 안 걸려 점수 None → 후보 0 이 되고,
    #   PIT 레그가 '무보유'로 조용히 채워진다.
    sid = TB._BASE_SID(S["sid"])
    P = C["px"][t]
    R, ixr, ixvol = C["R"], C["ixr"], C["ixvol"]

    # ── 펀더멘털 ─────────────────────────────────────────────────────────
    if sid in ("x-sue", "x-epsacc") or sid in FUND_SIDS:
        f = (C.get("FU") or {}).get(t) or {}
        dt_ = C["dates"][j]
        p0 = P[j]
        if sid == "x-sue":
            return TB.sue(f.get("eps") or [], dt_)
        if sid == "x-epsacc":
            e = TB.eps_accel(f.get("eps") or [], dt_)
            return (e / p0) if (e is not None and p0 and p0 > 0) else None
        sn = TB.asof_fund(f.get("sh"), dt_)
        mcap = (sn * p0) if (sn and p0 and sn > 0 and p0 > 0) else None
        if sid == "x-btp":
            e = TB.asof_fund(f.get("eq"), dt_)
            return (e / sn / p0) if (e is not None and mcap) else None
        if sid == "x-fcfy":
            fc = TB.ttm2(f.get("fcf"), f.get("fcf_a"), dt_)
            return (fc / mcap) if (fc is not None and mcap) else None
        if sid == "x-payout":
            dp = TB.ttm2(f.get("dps"), f.get("dps_a"), dt_)
            bbv = TB.ttm2(f.get("bb"), f.get("bb_a"), dt_)
            if not (mcap and (dp is not None or bbv is not None)):
                return None
            tot = (dp * sn if dp is not None else 0.0) + (bbv or 0.0)
            return (tot / mcap) if tot >= 0 else None
        if sid == "x-poacc":
            cut_ = TB._shift(dt_, TB.FUND_LAG_DAYS)
            nim = dict(f.get("ni_a") or []); cfm = dict(f.get("cfo_a") or [])
            rvm = dict(f.get("rev_a") or [])
            d_ = next((d for d, _x in (f.get("ni_a") or []) if d <= cut_ and d in cfm), None)
            if not d_:
                return None
            ni_, cf_, rv_ = nim[d_], cfm[d_], rvm.get(d_)
            if not (rv_ and rv_ > 0 and abs(ni_) >= 0.01 * rv_):
                return None
            return -((ni_ - cf_) / abs(ni_))
        if sid in ("x-gpa", "x-ocfp", "x-aci"):
            if (C.get("sector") or {}).get(t) == "Financials":
                return None
            at = TB.asof_fund(f.get("asset"), dt_)
            if sid == "x-ocfp":
                cf_ = TB.ttm2(f.get("cfo"), f.get("cfo_a"), dt_)
                return (cf_ / at) if (cf_ is not None and at and at > 0) else None
            if sid == "x-gpa":
                g = TB.ttm2(f.get("gp"), f.get("gp_a"), dt_)
                rv_ = TB.ttm2(f.get("rev"), f.get("rev_a"), dt_)
                cg = TB.ttm2(f.get("cogs"), f.get("cogs_a"), dt_)
                if g is not None and cg is not None and rv_ and rv_ > 0:
                    if abs(g + cg - rv_) / rv_ > 0.01:
                        g = None
                if g is None and rv_ is not None and cg is not None:
                    g = rv_ - cg
                return (g / at) if (g is not None and at and at > 0) else None
            cx = [(d, x) for d, x in (f.get("capex_a") or [])
                  if d <= TB._shift(dt_, TB.FUND_LAG_DAYS)]
            rvm = dict(f.get("rev_a") or [])
            rat = []
            for d, x in cx[:4]:
                r_ = rvm.get(d)
                if r_ and r_ > 0 and x is not None:
                    rat.append(x / r_)
            if len(rat) == 4 and sum(rat[1:]) > 0:
                ci = rat[0] / (sum(rat[1:]) / 3.0) - 1.0
                return -ci if abs(ci) <= 3.0 else None
            return None
        if sid == "x-ep":
            v = TB.ttm2(f.get("eps"), f.get("eps_a"), dt_)
            return (v / p0) if (v is not None and p0 and p0 > 0) else None
        if sid == "x-sp":
            rv = TB.ttm2(f.get("rev"), f.get("rev_a"), dt_)
            return (rv / mcap) if (rv is not None and mcap) else None
        if sid == "x-roe":
            nn, e = TB.ttm2(f.get("ni"), f.get("ni_a"), dt_), TB.asof_fund(f.get("eq"), dt_)
            return (nn / e) if (nn is not None and e and e > 0) else None
        if sid == "x-npm":
            nn, rv = TB.ttm2(f.get("ni"), f.get("ni_a"), dt_), TB.ttm2(f.get("rev"), f.get("rev_a"), dt_)
            return (nn / rv) if (nn is not None and rv and rv > 0) else None
        if sid == "x-rgrow":
            a1 = TB.ttm2(f.get("rev"), f.get("rev_a"), dt_)
            a0 = TB.ttm2(f.get("rev"), f.get("rev_a"), TB._shift(dt_, 365))
            return (a1 / a0 - 1) if (a1 is not None and a0 and a0 > 0) else None
        if sid == "x-lowde":
            e = TB.asof_fund(f.get("eq"), dt_)
            lb = TB.asof_fund(f.get("liab"), dt_)
            if lb is None:
                at = TB.asof_fund(f.get("asset"), dt_)
                lb = (at - e) if (at is not None and e is not None) else None
            return -(lb / e) if (lb is not None and e and e > 0) else None
        if sid == "x-dy":
            dp = TB.ttm2(f.get("dps"), f.get("dps_a"), dt_)
            return (dp / p0) if (dp is not None and p0 and p0 > 0) else None
        if sid == "x-agrow":
            pr = TB.yoy_pair(f.get("asset"), dt_)
            if not pr or pr[1] <= 0 or pr[3] <= 0:
                return None
            g = pr[1] / pr[3] - 1.0
            return -max(-2.0, min(2.0, g))
        if sid == "x-shiss":
            # 소급 레그와 문자 그대로 같아야 한다 — 다르면 '편향'이라 부른 값이 정의 차이다.
            pr = TB.yoy_pair(f.get("sh_u") or f.get("sh"), dt_, seam=f.get("sh_seam"))
            if not pr or pr[1] <= 0 or pr[3] <= 0:
                return None
            g = pr[1] / pr[3] - 1.0
            return -g if abs(g) <= 0.5 else None
        if sid == "x-custconc":
            return TB.custconc_asof(t, dt_)           # 소급 레그와 문자 그대로 같다
        if sid == "x-cash":
            ch = TB.asof_fund(f.get("cash"), dt_)
            at = TB.asof_fund(f.get("asset"), dt_)
            return (ch / at) if (ch is not None and at and at > 0) else None
        # 🚨 FUND_SIDS 에 넣어 놓고 여기 갈래를 안 만들면 **조용히 무보유**가 되고, 표에는
        #   '열위'라는 성적이 붙는다. 실제로 그렇게 한 번 틀렸다 — 2026-08-04 에 후보 규칙
        #   하나를 FUND_SIDS 에만 넣고 돌렸더니 CAGR 0.00 · 초과 −17.59 · t −3.32 가 나왔는데
        #   규칙의 성적이 아니라 갈래 누락이었다.
        #   채점기가 두 벌이라(tech_backtest 와 여기) 한쪽만 고쳐지는 사고는 구조적으로 난다.
        #   그러니 조용히 None 을 돌려주지 말고 여기서 죽는다.
        raise SystemExit("pit_backtest.score: FUND_SIDS 에 %s 가 있는데 채점 갈래가 없다 — "
                         "tech_backtest 의 같은 갈래를 그대로 옮겨 적을 것" % sid)
    if sid == "x-echo":
        return TB.ret(P, j - 126, 126)
    if sid == "x-coskew":
        ck = TB.coskew(R[t], ixr, j, 252)
        return -ck if ck is not None else None
    if sid == "x-lowcorr":
        cr = TB.mkt_corr(R[t], ixr, j, 252)
        return -cr if cr is not None else None
    if sid == "x-cntd":
        return TB.updown(R[t], j, 231)
    if sid == "x-season":
        return TB.same_month_avg(P, j, C["dates"], C["me"])
    if sid == "x-52wh":
        # 🚨 EXCLUDED_SIDS 로 빠진 규칙이다(2026-08-04). 창이 신호일 j 를 포함해 신고가
        #   종목의 점수가 정확히 1.0 이 되고, 그 동점이 티커 알파벳 역순으로 갈린다 —
        #   랩 본편에서 고친 그 버그가 여기 그대로 남아 있었다. 본편은 일중 고가로 고쳤지만
        #   PIT 가격 캐시에는 고가가 없다. 갈래를 지우지 않고 **죽게** 둔다: 누가 목록에
        #   되돌려 넣으면 조용히 틀린 값을 내는 대신 여기서 멈춘다.
        H = (C.get("hi") or {}).get(t)
        if H is None:
            # 캐시가 없거나 그 종목이 없다 — 조용히 종가로 대체하지 않는다. 랩 종목만 고가를
            # 쓰고 편출 종목은 종가를 쓰면 한 횡단면을 두 자로 채점하는 것이라 더 나쁘다.
            return None
        win = [x for x in H[max(0, j - 251):j + 1] if x]
        h = max(win) if win else None
        return (P[j] / h) if (h and P[j]) else None
    if sid == "x-dist200":
        m = TB.sma(P, j, 200)
        return (P[j] / m - 1) if (m and P[j]) else None
    if sid == "x-mom-trend":
        m200 = TB.sma(P, j, 200)
        if not m200 or not P[j] or P[j] <= m200:
            return None
        return (TB.ret(P, j, 252) or -9) - (TB.ret(P, j, 21) or 0)
    if sid == "x-rev1w":
        return -(TB.ret(P, j, 5) or 9)
    if sid == "x-minvar":
        sv, mv = TB.vol(R[t], j, 120), ixvol[j]
        return -(0.5 * sv + 0.5 * mv) if (sv and mv) else None
    if sid == "x-riskbudget":
        sv = TB.vol(R[t], j, 60)
        return (1.0 / sv) if sv and sv > 0 else None
    if sid == "x-lowbeta":
        b = TB.beta(R[t], ixr, j, 120)
        return -b if b is not None else None
    if sid == "x-ivol":
        iv = TB.idio_vol(R[t], ixr, j, 120)
        return -iv if iv is not None else None
    if sid == "x-snapback":
        m200 = TB.sma(P, j, 200)
        if not m200 or not P[j] or P[j] <= m200:
            return None
        rv = TB.rsi(P, j)
        return -rv if rv is not None else None
    if sid == "x-volsurge":
        V = C["vlm"].get(t)
        m200 = TB.sma(P, j, 200)
        if not V or not m200 or not P[j] or P[j] <= m200:
            return None
        a, b = TB.sma(V, j, 20), TB.sma(V, j, 60)
        return (a / b) if (a and b and b > 0) else None
    if sid == "x-small":
        # 랩과 같은 정의 — 시가총액 = 그 시점 주식수 × 종가. 작을수록 위(음수로 뒤집는다).
        a = (C.get("SH") or {}).get(t)
        if not a:
            return None
        sn = TB.asof_fund(a, C["dates"][j])
        p0 = P[j]
        return -(sn * p0) if (sn and p0 and sn > 0 and p0 > 0) else None
    return S["fn"](t, j, P, R[t], TB.vol(R[t], j, 60))


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
    out = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    hlout = json.load(io.open(HLCACHE, encoding="utf-8")) if os.path.exists(HLCACHE) else {}
    got = 0
    for i in range(0, len(want), 25):
        # 🚨 2026-08-05 — 종전에는 `t not in out`(종가 캐시)만 봤다. 그래서 고가·저가를
        #   같은 배치에 얹었더니 **이미 종가가 있는 147종은 아예 안 받아** HL 캐시가 0종으로
        #   남았다(실행은 성공으로 끝났다 — 전형적인 '조용한 미수집'이다).
        #   둘 중 하나라도 없으면 받는다.
        ch = [t for t in want[i:i + 25] if t not in out or t not in hlout]
        if not ch:
            continue
        try:
            _raw = yf.download(ch, start=START, auto_adjust=True, progress=False, threads=False)
            d = _raw["Close"]
            _hi, _lo = _raw.get("High"), _raw.get("Low")
        except Exception as e:
            print("  [yf] 배치 실패:", str(e)[:60]); continue
        for t in ch:
            if t in d:
                ser = d[t].dropna()
                if len(ser) > 200:
                    # 이미 있는 종가는 덮어쓰지 않는다 — 재수집 시점이 달라 값이 미세하게
                    # 흔들리면 그 위에서 잰 PIT 수치가 조용히 바뀐다.
                    out.setdefault(t, {str(k.date()): round(float(v), 4) for k, v in ser.items()})
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
          % (CACHE, len(out), got, len(want) - len(out)))
    if hlout:
        json.dump(hlout, io.open(HLCACHE, "w", encoding="utf-8"), separators=(",", ":"))
        print("→ %s · %d종 — 이 파일이 있어야 고가·저가 규칙(x-52wh 등)의 PIT 레그가 돈다"
              % (HLCACHE, len(hlout)))

    # 시점별 주식수 — x-small(시가총액) 을 PIT 로 재려면 필요하다.
    # 오늘의 유니버스는 랩이 SEC XBRL 로 이미 갖고 있고(data/fx), 편출 종목만 여기서 받는다.
    # ⚠ 두 출처는 정의가 미세하게 다르다(실측 yfinance 가 0.3~2.3% 낮다). 시총이 자릿수로
    #   벌어지는 횡단면에서는 순위에 거의 영향이 없지만, limits 에 적고 민감도도 재 둔다.
    sh = json.load(io.open(SHCACHE, encoding="utf-8")) if os.path.exists(SHCACHE) else {}
    tgt = [t for t in sorted(out) if t not in sh]
    print("주식수 수집 %d종 (이미 %d종)" % (len(tgt), len(sh)))
    for k, t in enumerate(tgt):
        try:
            ser = yf.Ticker(t).get_shares_full(start=START)
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
